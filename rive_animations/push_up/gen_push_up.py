#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive 7.3 scene for Push Up (id: 'push_up').

Matches the 2-panel 3/4 front-right Push-Up anatomical reference chart (media_1793717492936_c3726de1.jpg):
  - Top Panel (r = 0.0, High-Plank Top Lockout):
    * Athlete holds a rigid straight-body high plank from dorsiflexed toes on the left (`x ~ 124..148`)
      through sculpted calves, quadriceps, dark compression shorts, braced torso, and extended arms
      to wide-planted hands on the floor (`NEAR_WRIST = (352, 290)`, `FAR_WRIST = (466, 264)`).
    * Volumetric 3/4 head looks down-right ahead of the hands with neutral cervical alignment.
  - Bottom Panel (r = 1.0, Bottom of Push-Up / Chest Hover):
    * Entire body pivots down as a rigid unit toward the floor (`hip_near` drops from `y = 196` to `y = 224`,
      `sh_near` drops from `(380, 164)` to `(378, 218)`).
    * Near (Right) elbow flexes to ~90 degrees (`elbow_near = (328, 214)`), placing the upper arm nearly
      horizontal and the forearm vertical above the planted hand.
  - Highlighted Target Muscle Groups (all 4 labeled muscles from the reference chart):
    1. Pectoralis major (lower) (Primary — sternocostal chest head on near & far chest, `scale = 1.00`)
    2. Pectoralis major (upper) (Primary — clavicular chest head below clavicle/neck, `scale = 0.96`)
    3. Anterior deltoid (Primary/Synergist — front shoulder cap on near & far deltoids, `scale = 0.92`)
    4. Triceps brachii (Primary/Synergist — lateral & long head along dorsal upper arm, `scale = 0.94`)

Run:
    python3 gen_push_up.py            # writes scene.rml
    python3 gen_push_up.py --publish  # compiles assets/animations/push_up.riv + 256x256 thumbnail
"""
import math
import pathlib
import struct
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "scene.rml"
BUILD = HERE / "build"
ASSET_RIV = REPO / "assets/animations/push_up.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/push_up.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s @ 60fps smooth push-up cycle
STEP = 2

# Stationary Planted Wrists on Floor (wide 3/4 push-up stance matching reference)
NEAR_WRIST = (352.0, 290.0)
FAR_WRIST = (452.0, 264.0)

# Reference Limb Lengths for 3D Foreshortened Arm Solver
UPPER_ARM_NEAR, FOREARM_NEAR = 66.0, 68.0
UPPER_ARM_FAR, FOREARM_FAR = 60.0, 58.0

# Segment Lengths for Exact 2-Bone IK (Hip -> Knee -> Ankle)
L_THIGH_NEAR, L_SHIN_NEAR = 72.0, 70.0
L_THIGH_FAR, L_SHIN_FAR = 70.0, 68.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "4D0F172A"

# Target Muscle Heat Colors: warm orange (#FFF97316) -> intense crimson (#FFF43F5E)
MUSCLE_LOW = (0xD9, 0xF9, 0x73, 0x16)
MUSCLE_HIGH = (0xFF, 0xF4, 0x3F, 0x5E)
MUSCLE_LINE_LOW = (0x80, 0x9A, 0x34, 0x12)
MUSCLE_LINE_HIGH = (0xE6, 0x88, 0x13, 0x37)


def cubic_bezier(x1, y1, x2, y2):
    def bez(t, a, b):
        return 3.0 * a * t * (1.0 - t) ** 2 + 3.0 * b * t * t * (1.0 - t) + t ** 3

    def ease(x):
        if x <= 0.0:
            return 0.0
        if x >= 1.0:
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            if bez(mid, x1, x2) < x:
                lo = mid
            else:
                hi = mid
        return bez(0.5 * (lo + hi), y1, y2)

    return ease


EASE_DOWN = cubic_bezier(0.42, 0.0, 0.58, 1.0)
EASE_PUSH = cubic_bezier(0.32, 0.0, 0.24, 1.0)


def push_up_progress(frame):
    """0.0 at top lockout (Top Panel), 1.0 at bottom chest hover (Bottom Panel):
    - 0..14:    Top high-plank lockout hold (r = 0.0)
    - 14..70:   Controlled eccentric descent to bottom hover (r: 0.0 -> 1.0)
    - 70..88:   Bottom stretch & chest/triceps pause just above floor (r = 1.0)
    - 88..144:  Explosive concentric press back to lockout (r: 1.0 -> 0.0)
    - 144..160: Top high-plank lockout hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 14:
        return 0.0
    if fr <= 70:
        return EASE_DOWN((fr - 14) / 56.0)
    if fr <= 88:
        return 1.0
    if fr <= 144:
        return 1.0 - EASE_PUSH((fr - 88) / 56.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def quad_interp_pt(p0, p_mid, p1, r):
    l0 = (1.0 - r) * (1.0 - 2.0 * r)
    l1 = 4.0 * r * (1.0 - r)
    l2 = r * (2.0 * r - 1.0)
    return (
        l0 * p0[0] + l1 * p_mid[0] + l2 * p1[0],
        l0 * p0[1] + l1 * p_mid[1] + l2 * p1[1],
    )


def solve_foreshortened_arm(sh, el, wrist, l1, l2):
    """3D-foreshortened Shoulder -> Elbow -> Stationary Planted Wrist solver in world space."""
    dx1, dy1 = el[0] - sh[0], el[1] - sh[1]
    d1 = math.hypot(dx1, dy1)
    ua_rot = math.atan2(dy1, dx1)
    ua_sx = max(0.45, d1 / l1)

    dx2, dy2 = wrist[0] - el[0], wrist[1] - el[1]
    d2 = math.hypot(dx2, dy2)
    fa_rot = math.atan2(dy2, dx2)
    fa_sx = max(0.45, d2 / l2)
    return ua_rot, ua_sx, fa_rot, fa_sx


def solve_plank_leg_ik(hip, ankle, l1, l2):
    """2-bone IK from hip -> knee -> ankle in a rightward-facing (+X) push-up plank."""
    dx = ankle[0] - hip[0]
    dy = ankle[1] - hip[1]
    d = max(1.0, min(l1 + l2 - 0.6, math.hypot(dx, dy)))
    base_ang = math.atan2(dy, dx)
    cos_a = max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2.0 * l1 * d)))
    thigh_ang = base_ang - math.acos(cos_a)
    knee = (hip[0] + l1 * math.cos(thigh_ang), hip[1] + l1 * math.sin(thigh_ang))
    shin_ang = math.atan2(ankle[1] - knee[1], ankle[0] - knee[0])
    return thigh_ang, knee, shin_ang


def pose(r):
    """Compute 3/4 Push-Up transforms at progress r in [0.0, 1.0]:
    - r = 0.0: Top Panel (extended arms, straight plank inclined at -22 deg)
    - r = 1.0: Bottom Panel (90-deg bent elbows, straight plank lowered close to floor at -9 deg)
    """
    # 1. Stationary Dorsiflexed Ankles on the Left
    ankle_near = (144.0, 264.0)
    ankle_far = (160.0, 252.0)

    # 2. Hip Positions pivoting along a constant-radius arc around the ankles so knees stay locked straight!
    leg_span_near = L_THIGH_NEAR + L_SHIN_NEAR - 1.2  # 140.8 px (locked straight leg)
    leg_span_far = L_THIGH_FAR + L_SHIN_FAR - 1.2     # 136.8 px
    leg_ang_near = math.radians(lerp(-25.5, -18.0, r))
    leg_ang_far = math.radians(lerp(-25.5, -18.0, r))

    hip_near = (
        ankle_near[0] + leg_span_near * math.cos(leg_ang_near),
        ankle_near[1] + leg_span_near * math.sin(leg_ang_near),
    )
    hip_far = (
        ankle_far[0] + leg_span_far * math.cos(leg_ang_far),
        ankle_far[1] + leg_span_far * math.sin(leg_ang_far),
    )

    thigh_near_ang, knee_near, shin_near_ang = solve_plank_leg_ik(
        hip_near, ankle_near, L_THIGH_NEAR, L_SHIN_NEAR
    )
    thigh_far_ang, knee_far, shin_far_ang = solve_plank_leg_ik(
        hip_far, ankle_far, L_THIGH_FAR, L_SHIN_FAR
    )
    foot_near_rot = math.radians(lerp(4.0, 10.0, r))
    foot_far_rot = math.radians(lerp(4.0, 10.0, r))

    # 3. Torso Pivot & Rotation aligned seamlessly with the rising/lowering hips & shoulders
    torso_x = lerp(346.0, 352.0, r)
    torso_y = lerp(176.0, 212.0, r)
    torso_rot = math.radians(lerp(-14.5, -2.5, r))

    # 4. World-Space Shoulder Positions & Elbow Trajectories
    sh_near = (lerp(382.0, 386.0, r), lerp(164.0, 198.0, r))
    sh_far = (lerp(420.0, 420.0, r), lerp(156.0, 206.0, r))

    # Near (Right) Elbow:
    # - r = 0.0 (Top Panel): (365, 228) along the extended arm line from (382, 164) to (352, 290)
    # - r = 1.0 (Bottom Panel): (328, 214) flexed ~90 deg down-left from sh_near=(386, 198) and above NEAR_WRIST=(352, 290)
    elbow_near = quad_interp_pt((365.0, 228.0), (343.0, 221.0), (328.0, 214.0), r)

    # Far (Left) Elbow:
    # - r = 0.0 (Top Panel): (436, 210) along the extended arm line from (420, 156) to (452, 264)
    # - r = 1.0 (Bottom Panel): (444, 214) tucked behind the head/neck above FAR_WRIST=(452, 264)
    elbow_far = quad_interp_pt((436.0, 210.0), (440.0, 212.0), (444.0, 214.0), r)

    ua_near, ua_near_sx, fa_near, fa_near_sx = solve_foreshortened_arm(
        sh_near, elbow_near, NEAR_WRIST, UPPER_ARM_NEAR, FOREARM_NEAR
    )
    ua_far, ua_far_sx, fa_far, fa_far_sx = solve_foreshortened_arm(
        sh_far, elbow_far, FAR_WRIST, UPPER_ARM_FAR, FOREARM_FAR
    )
    delt_near_rot = lerp(ua_near, math.radians(136.0), 0.55 * r)
    delt_far_rot = lerp(ua_far, math.radians(45.0), 0.55 * r)

    shd_sx = lerp(1.75, 1.92, r)

    return {
        "r": r,
        "torso_x": torso_x,
        "torso_y": torso_y,
        "torso_rot": torso_rot,
        "hip_near": hip_near,
        "hip_far": hip_far,
        "ankle_near": ankle_near,
        "knee_near": knee_near,
        "thigh_near_ang": thigh_near_ang,
        "shin_near_ang": shin_near_ang,
        "foot_near_rot": foot_near_rot,
        "ankle_far": ankle_far,
        "knee_far": knee_far,
        "thigh_far_ang": thigh_far_ang,
        "shin_far_ang": shin_far_ang,
        "foot_far_rot": foot_far_rot,
        "sh_near": sh_near,
        "sh_far": sh_far,
        "elbow_near": elbow_near,
        "elbow_far": elbow_far,
        "ua_near": ua_near,
        "ua_near_sx": ua_near_sx,
        "fa_near": fa_near,
        "fa_near_sx": fa_near_sx,
        "ua_far": ua_far,
        "ua_far_sx": ua_far_sx,
        "fa_far": fa_far,
        "fa_far_sx": fa_far_sx,
        "delt_near_rot": delt_near_rot,
        "delt_far_rot": delt_far_rot,
        "shd_sx": shd_sx,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(push_up_progress(fr)) for fr in FRAMES}

_ANGLE_KEYS = (
    "torso_rot",
    "thigh_near_ang",
    "shin_near_ang",
    "foot_near_rot",
    "thigh_far_ang",
    "shin_far_ang",
    "foot_far_rot",
    "ua_near",
    "fa_near",
    "ua_far",
    "fa_far",
    "delt_near_rot",
    "delt_far_rot",
)
for _k in _ANGLE_KEYS:
    _prev = None
    for _fr in FRAMES:
        _v = POSES[_fr][_k]
        if _prev is not None:
            while _v - _prev > math.pi:
                _v -= 2.0 * math.pi
            while _v - _prev < -math.pi:
                _v += 2.0 * math.pi
            POSES[_fr][_k] = _v
        _prev = _v
    assert abs(POSES[0][_k] - POSES[DURATION][_k]) < 1e-6, f"Angle jump on {_k}"


# ---------------------------------------------------------------- RML & Paint Helpers
_id = 0
KEYED = []


def nid():
    global _id
    _id += 1
    return f"o{_id}"


def f(v):
    if isinstance(v, float):
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(v)


def smooth_vertices(pts, closed=True, indent="            "):
    n = len(pts)
    out = []
    for i, (x, y) in enumerate(pts):
        if closed:
            p0, p2 = pts[(i - 1) % n], pts[(i + 1) % n]
        else:
            p0 = pts[max(i - 1, 0)]
            p2 = pts[min(i + 1, n - 1)]
        tx, ty = p2[0] - p0[0], p2[1] - p0[1]
        dist = math.hypot(tx, ty) / 6.0
        if not closed and (i == 0 or i == n - 1):
            dist *= 2.0
        ang = math.atan2(ty, tx)
        out.append(
            f'{indent}<CubicMirroredVertex x="{f(float(x))}" y="{f(float(y))}" '
            f'rotation="{f(ang)}" distance="{f(dist)}"/>'
        )
    return "\n".join(out)


def grad3(name, y0, y1, c0, c1, c2, x0=0, x1=0):
    return (
        f'<LinearGradient startX="{f(float(x0))}" startY="{f(float(y0))}" '
        f'endX="{f(float(x1))}" endY="{f(float(y1))}" name="{name}">'
        f'<GradientStop colorValue="{c0}" position="0"/>'
        f'<GradientStop colorValue="{c1}" position="0.5"/>'
        f'<GradientStop colorValue="{c2}" position="1"/></LinearGradient>'
    )


def grad(name, x0, y0, x1, y1, c0, c1):
    return (
        f'<LinearGradient startX="{f(float(x0))}" startY="{f(float(y0))}" '
        f'endX="{f(float(x1))}" endY="{f(float(y1))}" name="{name}">'
        f'<GradientStop colorValue="{c0}" position="0"/>'
        f'<GradientStop colorValue="{c1}" position="1"/></LinearGradient>'
    )


def solid(name, color, cid=None):
    idattr = f' id="{cid}"' if cid else ""
    return f'<Fill name="{name}Fill"><SolidColor colorValue="{color}" name="{name}Color"{idattr}/></Fill>'


def skin_fill(name, y0, y1, tones, x0=0, x1=0):
    return f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *tones, x0=x0, x1=x1)}</Fill>'


def smooth_shape(indent, name, pts, paint_xml, x=0.0, y=0.0):
    pos = f' x="{f(float(x))}" y="{f(float(y))}"' if (x or y) else ""
    return (
        f'{indent}<Shape{pos} name="{name}">\n'
        f'{indent}    <PointsPath isClosed="true" name="{name}Path">\n'
        f"{smooth_vertices(pts, True, indent + '        ')}\n"
        f"{indent}    </PointsPath>\n"
        f"{indent}    {paint_xml}\n"
        f"{indent}</Shape>"
    )


def stroke_shape(indent, name, pts, width, color, feather=0.0, cap="round"):
    f_xml = f'<Feather strength="{f(float(feather))}" name="{name}Feather"/>' if feather > 0 else ""
    return (
        f'{indent}<Shape name="{name}">\n'
        f'{indent}    <PointsPath isClosed="false" name="{name}Path">\n'
        f"{smooth_vertices(pts, False, indent + '        ')}\n"
        f"{indent}    </PointsPath>\n"
        f'{indent}    <Stroke thickness="{f(float(width))}" cap="{cap}" join="round" name="{name}Stroke">'
        f'<SolidColor colorValue="{color}" name="{name}Color"/>{f_xml}</Stroke>\n'
        f"{indent}</Shape>"
    )


def ellipse_shape(indent, name, x, y, w, h, paint_xml, rot_deg=0.0):
    rot_attr = f' rotation="{f(math.radians(rot_deg))}"' if rot_deg else ""
    return (
        f'{indent}<Shape x="{f(float(x))}" y="{f(float(y))}"{rot_attr} name="{name}">\n'
        f'{indent}    <Ellipse width="{f(float(w))}" height="{f(float(h))}" name="{name}Ellipse"/>\n'
        f"{indent}    {paint_xml}\n"
        f"{indent}</Shape>"
    )


def key_double(oid, pkey, fn):
    kfs = "\n".join(
        f'                <KeyFrameDouble frame="{fr}" value="{f(fn(POSES[fr]))}"/>'
        for fr in FRAMES
    )
    KEYED.append((oid, f'            <KeyedProperty propertyKey="{pkey}">\n{kfs}\n            </KeyedProperty>'))


def key_color(oid, pkey, fn):
    kfs = "\n".join(
        f'                <KeyFrameColor frame="{fr}" value="{fn(POSES[fr])}"/>'
        for fr in FRAMES
    )
    KEYED.append((oid, f'            <KeyedProperty propertyKey="{pkey}">\n{kfs}\n            </KeyedProperty>'))


def argb_lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return "".join(f"{round(lerp(x, y, t)):02X}" for x, y in zip(a, b))


def muscle_paint_fn(name, fn_t, line=1.0):
    fid, lid = nid(), nid()
    key_color(fid, 37, lambda p: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, fn_t(p)))
    key_color(lid, 37, lambda p: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, fn_t(p)))
    t0 = fn_t(POSES[0])
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- 1. 3D-Foreshortened Push-Up Arms & Spread Hands
def build_push_up_arm(indent, prefix, is_far):
    """Builds the Near (Right) or Far (Left) Push-Up Arm:
    - Stationary spread hand & fingers planted on the floor (`NEAR_WRIST = (352, 290)`, `FAR_WRIST = (466, 264)`)
    - 3D-foreshortened Forearm (`Elbow -> Wrist`) with sculpted Brachioradialis & Extensor ridges
    - 3D-foreshortened Upper Arm (`Shoulder -> Elbow`) with glowing Triceps brachii (lateral & long head)
    - Unscaled Deltoid Cap at `Shoulder` with glowing Anterior deltoid."""
    i2 = indent + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if is_far else SKIN

    sh_key = "sh_far" if is_far else "sh_near"
    el_key = "elbow_far" if is_far else "elbow_near"
    ua_len = UPPER_ARM_FAR if is_far else UPPER_ARM_NEAR
    fa_len = FOREARM_FAR if is_far else FOREARM_NEAR
    ua_key = "ua_far" if is_far else "ua_near"
    ua_sx_key = "ua_far_sx" if is_far else "ua_near_sx"
    fa_key = "fa_far" if is_far else "fa_near"
    fa_sx_key = "fa_far_sx" if is_far else "fa_near_sx"
    delt_rot_key = "delt_far_rot" if is_far else "delt_near_rot"
    wx, wy = FAR_WRIST if is_far else NEAR_WRIST

    delt_id, ua_id, fa_id = nid(), nid(), nid()
    key_double(delt_id, 13, lambda p: p[sh_key][0])
    key_double(delt_id, 14, lambda p: p[sh_key][1])
    key_double(delt_id, 15, lambda p: p[delt_rot_key])

    key_double(ua_id, 13, lambda p: p[sh_key][0])
    key_double(ua_id, 14, lambda p: p[sh_key][1])
    key_double(ua_id, 15, lambda p: p[ua_key])
    key_double(ua_id, 16, lambda p: p[ua_sx_key])

    key_double(fa_id, 13, lambda p: p[el_key][0])
    key_double(fa_id, 14, lambda p: p[el_key][1])
    key_double(fa_id, 15, lambda p: p[fa_key])
    key_double(fa_id, 16, lambda p: p[fa_sx_key])
    p0 = POSES[0]

    def triceps_t(p):
        return 0.44 + 0.56 * (p["r"] ** 0.80)

    def ant_delt_t(p):
        return 0.42 + 0.54 * (p["r"] ** 0.80)

    # 1. Stationary Planted Hand with Spread Fingers (matching reference illustration)
    if not is_far:
        hand_pts = [
            (wx - 9.0, wy - 2.0), (wx + 8.0, wy - 3.5), (wx + 34.0, wy + 2.5),
            (wx + 38.0, wy + 8.5), (wx + 24.0, wy + 12.5), (wx + 2.0, wy + 10.0),
            (wx - 4.0, wy + 16.5), (wx - 9.5, wy + 14.5), (wx - 10.5, wy + 5.0),
        ]
    else:
        hand_pts = [
            (wx - 8.0, wy - 2.0), (wx + 8.0, wy - 3.0), (wx + 32.0, wy + 2.5),
            (wx + 35.0, wy + 7.5), (wx + 18.0, wy + 10.0), (wx - 2.0, wy + 9.0),
            (wx - 7.5, wy + 12.0), (wx - 9.5, wy + 6.0),
        ]

    # 2. Forearm (0 .. fa_len from Elbow to Wrist)
    fa_pts = [
        (-7.0, 0.0), (-4.0, -9.2), (fa_len * 0.32, -10.5), (fa_len - 5.0, -6.5),
        (fa_len + 4.0, 0.0), (fa_len - 5.0, 6.5), (fa_len * 0.32, 10.5), (-4.0, 9.2),
    ]

    # 3. Upper Arm (0 .. ua_len from Shoulder to Elbow)
    # Note on local Y orientation for Near Arm:
    # `sh_near` = (378, 164..218) -> `elbow_near` = (361..326, 228..214).
    # So `ua_near` angle is between +105 deg (down-left) and +175 deg (left).
    # Therefore, local `+Y` points UP-LEFT (the dorsal/superior Triceps brachii border!),
    # and local `-Y` points DOWN-RIGHT (the ventral/inferior Biceps brachii border!).
    ua_pts = [
        (-8.0, 0.0), (-5.0, -11.5), (12.0, -12.8), (ua_len * 0.55, -11.5), (ua_len - 4.0, -8.0),
        (ua_len + 5.5, 0.0), (ua_len - 4.0, 8.5), (ua_len * 0.55, 12.2), (12.0, 12.8), (-5.0, 11.5),
    ]
    triceps_sign = 1.0 if not is_far else -1.0
    biceps_sign = -triceps_sign
    triceps_pts = [
        (8.0, triceps_sign * 0.5),
        (ua_len * 0.45, triceps_sign * 1.0),
        (ua_len - 3.5, triceps_sign * 2.5),
        (ua_len - 5.5, triceps_sign * 8.8),
        (ua_len * 0.48, triceps_sign * 12.2),
        (10.0, triceps_sign * 11.2),
    ]

    # 4. Deltoid Cap at Shoulder (`0,0`) with Lateral Deltoid in silver and Anterior Deltoid highlighted
    delt_pts = [
        (-11.0, 0.0), (-7.0, -13.5), (6.0, -14.8), (19.0, -10.5),
        (23.0, 0.0), (19.0, 10.5), (6.0, 14.8), (-7.0, 13.5),
    ]
    ant_delt_pts = [
        (-5.0, biceps_sign * 1.5),
        (6.0, biceps_sign * 14.5),
        (19.5, biceps_sign * 10.2),
        (21.5, biceps_sign * 1.5),
        (7.0, 0.0),
    ]

    out = [f'{indent}<Node name="{prefix}PushUpArmGroup">']

    # 1. Stationary Planted Hand & Spread Fingers on Floor (Topmost in Arm Group)
    if not is_far:
        out.append(stroke_shape(i2, "NearFinger1", [(wx + 12.0, wy + 1.5), (wx + 33.0, wy + 4.5)], 1.05, SOFT_SHADOW, 0.2))
        out.append(stroke_shape(i2, "NearFinger2", [(wx + 10.0, wy + 4.8), (wx + 32.0, wy + 8.0)], 1.05, SOFT_SHADOW, 0.2))
        out.append(stroke_shape(i2, "NearFinger3", [(wx + 7.0, wy + 7.8), (wx + 24.0, wy + 10.8)], 1.05, SOFT_SHADOW, 0.2))
        out.append(stroke_shape(i2, "NearHandHi", [(wx - 2.0, wy + 1.0), (wx + 18.0, wy + 3.0)], 2.2, HIGHLIGHT, 2.0))
    else:
        out.append(stroke_shape(i2, "FarFinger1", [(wx + 10.0, wy + 1.5), (wx + 30.0, wy + 4.5)], 0.95, SOFT_SHADOW, 0.2))
        out.append(stroke_shape(i2, "FarFinger2", [(wx + 8.0, wy + 4.8), (wx + 26.0, wy + 7.5)], 0.95, SOFT_SHADOW, 0.2))
    out.append(smooth_shape(i2, f"{prefix}PlantedHand", hand_pts, skin_fill(prefix + "Hand", wy - 4, wy + 16, skin)))

    # 2. Unscaled Deltoid Cap & Glowing Anterior Deltoid at Shoulder Origin (drawn above upper arm seam)
    out.append(
        f'{i2}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" '
        f'rotation="{f(p0[delt_rot_key])}" name="{prefix}DeltoidNode" id="{delt_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}AntDeltHi", [(2.0, biceps_sign * 7.5), (15.0, biceps_sign * 6.5)], 2.2, HIGHLIGHT, 2.0))
    out.append(smooth_shape(i3, f"{prefix}AnteriorDeltoid", ant_delt_pts, muscle_paint_fn(prefix + "AntDelt", ant_delt_t, 0.95)))
    out.append(stroke_shape(i3, f"{prefix}LatDeltGroove", [(0.0, triceps_sign * 2.0), (16.0, triceps_sign * 1.5)], 1.2, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}LatDeltHi", [(1.0, triceps_sign * 6.5), (15.0, triceps_sign * 5.5)], 2.8, HIGHLIGHT, 2.8))
    out.append(smooth_shape(i3, f"{prefix}DeltoidCap", delt_pts, skin_fill(prefix + "Delt", -15, 15, skin)))
    out.append(f"{i2}</Node>")

    # 3. 3D-Foreshortened Upper Arm with Glowing Triceps Brachii (Shoulder -> Elbow, drawn over Forearm elbow joint)
    out.append(
        f'{i2}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" '
        f'rotation="{f(p0[ua_key])}" scaleX="{f(p0[ua_sx_key])}" name="{prefix}UpperArmNode" id="{ua_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}TricepsHi", [(12.0, triceps_sign * 6.5), (ua_len - 8.0, triceps_sign * 5.5)], 2.6, HIGHLIGHT, 2.4))
    out.append(stroke_shape(i3, f"{prefix}TricepsHeadLine", [(16.0, triceps_sign * 4.2), (ua_len * 0.65, triceps_sign * 3.5)], 1.0, "807C2D12", 0.3))
    out.append(smooth_shape(i3, f"{prefix}TricepsBrachii", triceps_pts, muscle_paint_fn(prefix + "Triceps", triceps_t, 1.0)))
    out.append(stroke_shape(i3, f"{prefix}HumerusGroove", [(10.0, 0.0), (ua_len - 6.0, 0.0)], 1.25, CORE_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}BicepsSh", [(12.0, biceps_sign * 6.8), (ua_len - 8.0, biceps_sign * 5.2)], 3.2, CORE_SHADOW, 3.0))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UA", -13, 13, skin)))
    out.append(f"{i2}</Node>")

    # 4. 3D-Foreshortened Forearm (Elbow -> Planted Wrist)
    out.append(
        f'{i2}<Node x="{f(p0[el_key][0])}" y="{f(p0[el_key][1])}" '
        f'rotation="{f(p0[fa_key])}" scaleX="{f(p0[fa_sx_key])}" name="{prefix}ForearmNode" id="{fa_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}ForearmGroove", [(6.0, 0.0), (fa_len * 0.72, 0.0)], 1.2, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(6.0, -4.5), (fa_len * 0.45, -5.5), (fa_len - 8.0, -3.5)], 2.6, HIGHLIGHT, 2.6))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(6.0, 5.2), (fa_len * 0.45, 6.2), (fa_len - 8.0, 3.8)], 3.2, CORE_SHADOW, 3.0))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "FA", -11, 11, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{indent}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 2. Straight Plank Legs (Quadriceps, Calves & Planted Feet)
def build_push_up_leg(indent, prefix, is_far):
    """Builds the Near (Right) or Far (Left) Push-Up leg in sculpted silver-slate skin with dark compression shorts."""
    i2 = indent + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if is_far else SKIN
    shorts = SHORTS_FAR if is_far else SHORTS
    l_thigh = L_THIGH_FAR if is_far else L_THIGH_NEAR
    l_shin = L_SHIN_FAR if is_far else L_SHIN_NEAR

    hip_key = "hip_far" if is_far else "hip_near"
    knee_key = "knee_far" if is_far else "knee_near"
    ankle_key = "ankle_far" if is_far else "ankle_near"
    thigh_ang_key = "thigh_far_ang" if is_far else "thigh_near_ang"
    shin_ang_key = "shin_far_ang" if is_far else "shin_near_ang"
    foot_rot_key = "foot_far_rot" if is_far else "foot_near_rot"

    thigh_id, shin_id, foot_id = nid(), nid(), nid()
    key_double(thigh_id, 13, lambda p: p[hip_key][0])
    key_double(thigh_id, 14, lambda p: p[hip_key][1])
    key_double(thigh_id, 15, lambda p: p[thigh_ang_key])

    key_double(shin_id, 13, lambda p: p[knee_key][0])
    key_double(shin_id, 14, lambda p: p[knee_key][1])
    key_double(shin_id, 15, lambda p: p[shin_ang_key])

    key_double(foot_id, 13, lambda p: p[ankle_key][0])
    key_double(foot_id, 14, lambda p: p[ankle_key][1])
    key_double(foot_id, 15, lambda p: p[foot_rot_key])

    p0 = POSES[0]

    thigh_pts = [
        (-14.0, -11.5), (10.0, -16.8), (36.0, -16.2), (58.0, -12.2),
        (l_thigh + 2.0, -5.2), (l_thigh + 2.0, 5.2), (56.0, 11.2),
        (32.0, 15.0), (8.0, 16.5), (-14.0, 12.0),
    ]
    shorts_cuff_pts = [
        (-16.0, -12.5), (22.0, -17.2), (24.0, 16.8), (-16.0, 13.0),
    ]
    shin_pts = [
        (-7.0, -6.2), (18.0, -6.5), (44.0, -5.5), (l_shin - 3.0, -4.0),
        (l_shin + 2.0, 0.0), (l_shin - 4.0, 4.5), (48.0, 7.2),
        (30.0, 13.8), (12.0, 13.5), (-6.0, 6.8),
    ]
    foot_pts = [
        (-7.5, -3.5), (4.5, -2.0), (7.5, 10.0),
        (9.5, 29.0), (5.5, 35.0), (-0.5, 33.0),
        (-3.5, 18.0), (-8.5, 3.5),
    ]

    out = [f'{indent}<Node name="{prefix}PushUpLegGroup">']

    # 1. Dorsiflexed Bare Foot braced on Floor
    out.append(
        f'{i2}<Node x="{f(p0[ankle_key][0])}" y="{f(p0[ankle_key][1])}" '
        f'rotation="{f(p0[foot_rot_key])}" name="{prefix}FootNode" id="{foot_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}FootArch", [(-2.0, 4.0), (1.0, 18.0), (3.5, 29.0)], 1.15, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}FootHi", [(2.5, 4.0), (5.5, 18.0), (7.0, 28.0)], 2.0, HIGHLIGHT, 2.2))
    out.append(smooth_shape(i3, f"{prefix}BareFoot", foot_pts, skin_fill(prefix + "Foot", -4, 35, skin)))
    out.append(f"{i2}</Node>")

    # 2. Lower Leg / Calf
    out.append(
        f'{i2}<Node x="{f(p0[knee_key][0])}" y="{f(p0[knee_key][1])}" '
        f'rotation="{f(p0[shin_ang_key])}" name="{prefix}ShinNode" id="{shin_id}">'
    )
    out.append(ellipse_shape(i3, f"{prefix}KneeCap", 0.0, -1.0, 17.0, 15.0, skin_fill(prefix + "Knee", -8, 8, skin)))
    out.append(stroke_shape(i3, f"{prefix}GastrocLine", [(12.0, 6.2), (28.0, 8.5), (46.0, 4.5)], 1.2, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}ShinHi", [(12.0, -4.0), (36.0, -3.6), (58.0, -2.4)], 2.4, HIGHLIGHT, 2.5))
    out.append(stroke_shape(i3, f"{prefix}CalfSh", [(12.0, 10.8), (28.0, 11.8), (48.0, 5.8)], 3.0, CORE_SHADOW, 3.0))
    out.append(smooth_shape(i3, f"{prefix}ShinShape", shin_pts, skin_fill(prefix + "Shin", -7, 14, skin)))
    out.append(f"{i2}</Node>")

    # 3. Sculpted Silver-Slate Thigh & Dark Compression Shorts
    out.append(
        f'{i2}<Node x="{f(p0[hip_key][0])}" y="{f(p0[hip_key][1])}" '
        f'rotation="{f(p0[thigh_ang_key])}" name="{prefix}ThighNode" id="{thigh_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}ShortsHem", [(22.0, -16.5), (23.0, 0.0), (22.0, 16.0)], 1.4, "800F172A", 0.6))
    out.append(smooth_shape(i3, f"{prefix}ShortsCuff", shorts_cuff_pts, skin_fill(prefix + "Shorts", -17, 17, shorts)))
    out.append(stroke_shape(i3, f"{prefix}QuadGroove", [(20.0, -6.5), (44.0, -5.2), (62.0, -3.2)], 1.3, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}QuadHi", [(22.0, -12.0), (44.0, -11.0), (60.0, -7.5)], 2.6, HIGHLIGHT, 2.6))
    out.append(stroke_shape(i3, f"{prefix}ThighPostSh", [(14.0, 12.0), (34.0, 11.0), (54.0, 7.6)], 3.4, CORE_SHADOW, 3.4))
    out.append(smooth_shape(i3, f"{prefix}ThighShape", thigh_pts, skin_fill(prefix + "Thigh", -17, 17, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{indent}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. Push-Up Torso, Pectoralis Major (Upper & Lower) & 3/4 Head
def build_push_up_torso_and_head():
    """Canonical 3/4 front-right CommunityFitness torso in a Push-Up:
    - Shows the 3/4 underside of the chest with glowing Pectoralis major (upper / clavicular head)
      and Pectoralis major (lower / sternocostal head) on both the Near (Right) and Far (Left) sides
      separated by the midline sternum and clavicular division (matching media_1793717492936_c3726de1.jpg!).
    - Sculpted upper back/trapezius, serratus anterior ribs, dark athletic compression shorts,
      and volumetric 3/4 Head looking down-right ahead of the hands."""
    ind = "        "
    i2 = ind + "    "

    torso_id = nid()
    key_double(torso_id, 13, lambda p: p["torso_x"])
    key_double(torso_id, 14, lambda p: p["torso_y"])
    key_double(torso_id, 15, lambda p: p["torso_rot"])
    p0 = POSES[0]

    def pec_lower_t(p):
        return 0.46 + 0.54 * (p["r"] ** 0.78)

    def pec_upper_t(p):
        return 0.42 + 0.54 * (p["r"] ** 0.80)

    # Local coordinates relative to Torso Pivot `(torso_x, torso_y)`:
    # Pelvis & Shorts sit at x in [-96..-44], Torso spans x in [-56..+82], Head sits at x in [+82..+136]
    pelvis_shorts_pts = [
        (-96.0, -6.0), (-80.0, -24.0), (-52.0, -23.0),
        (-42.0, -10.0), (-46.0, 22.0), (-74.0, 24.0), (-94.0, 12.0),
    ]

    torso_pts = [
        (-54.0, -22.0), (-10.0, -25.0), (36.0, -24.0), (74.0, -14.0),
        (82.0, 8.0), (62.0, 24.0), (26.0, 26.0), (-14.0, 21.0),
        (-52.0, 19.0),
    ]

    # 1. Pectoralis major (lower / sternocostal head) — Near (Right) & Far (Left) chest bellies
    pec_lower_near_pts = [
        (8.0, 6.0), (42.0, 2.0), (54.0, 14.0),
        (46.0, 25.0), (16.0, 24.0), (4.0, 15.0),
    ]
    pec_lower_far_pts = [
        (46.0, 12.0), (66.0, 6.0), (78.0, 13.0),
        (68.0, 23.0), (48.0, 24.5),
    ]

    # Sculpted Dorsal / Lateral Back & Scapular Plates (Trapezius, Infraspinatus, Latissimus Dorsi)
    sculpt_plate = (
        '<Fill name="TorsoSculptFill"><SolidColor colorValue="1F0F172A" name="TorsoSculptCol"/></Fill>'
        '<Stroke thickness="0.95" join="round" name="TorsoSculptEdge"><SolidColor colorValue="420F172A" name="TorsoSculptEdgeCol"/></Stroke>'
    )
    trap_plate_pts = [
        (24.0, -23.0), (62.0, -18.0), (68.0, -4.0), (44.0, -4.0), (20.0, -12.0),
    ]
    scapula_plate_pts = [
        (-8.0, -23.0), (24.0, -22.0), (22.0, -8.0), (-6.0, -8.0),
    ]
    lat_plate_pts = [
        (-46.0, -18.0), (-8.0, -18.0), (-4.0, -2.0), (-44.0, 2.0),
    ]
    pec_upper_near_pts = [
        (38.0, -4.0), (64.0, -6.0), (66.0, 6.0),
        (54.0, 14.0), (40.0, 4.0),
    ]
    pec_upper_far_pts = [
        (64.0, -5.0), (82.0, -2.0), (84.0, 8.0),
        (76.0, 13.0), (64.0, 6.0),
    ]

    neck_pts = [
        (64.0, -16.0), (88.0, -10.0), (94.0, 10.0),
        (68.0, 12.0), (58.0, -2.0),
    ]
    head_pts = [
        (86.0, -14.0), (102.0, -22.0), (118.0, -18.0), (130.0, -6.0),
        (132.0, 8.0), (124.0, 20.0), (112.0, 26.0), (98.0, 25.0),
        (88.0, 18.0), (80.0, 6.0), (80.0, -4.0),
    ]
    hair_pts = [
        (92.0, -16.0), (108.0, -22.5), (122.0, -17.0), (131.5, -4.0),
        (130.0, 10.0), (121.0, 16.0), (118.0, 8.0), (110.0, -2.0),
        (98.0, -10.0),
    ]

    out = [
        f'{ind}<Node x="{f(p0["torso_x"])}" y="{f(p0["torso_y"])}" rotation="{f(p0["torso_rot"])}" '
        f'name="PushUpTorsoAndHeadNode" id="{torso_id}">'
    ]

    # 1. Volumetric 3/4 Head & Muscular Neck (drawn on top of upper chest/clavicle)
    out.append(smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 92, -22, 132, 16, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i2, "Ear", 98.0, 2.0, 5.5, 8.0, solid("Ear", "FFA3B1C4"), rot_deg=28.0))
    out.append(stroke_shape(i2, "BrowShade", [(114.0, 17.0), (120.0, 13.5)], 1.35, "590F172A", 0.6))
    out.append(stroke_shape(i2, "EyeLine", [(111.5, 17.5), (116.0, 15.0)], 1.1, "730F172A", 0.4))
    out.append(stroke_shape(i2, "MouthLine", [(99.5, 21.0), (104.0, 19.0)], 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i2, "HeadCrownHi", [(96.0, -14.0), (110.0, -14.0), (120.0, -6.0)], 2.8, HIGHLIGHT, 3.2))
    out.append(stroke_shape(i2, "JawShadow", [(84.0, 10.0), (94.0, 21.0), (108.0, 23.0)], 2.4, CORE_SHADOW, 2.4))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill("Head", -22, 26, SKIN, x0=80, x1=132)))
    out.append(stroke_shape(i2, "SCMLine", [(68.0, -6.0), (80.0, 0.0), (88.0, 6.0)], 1.5, SOFT_SHADOW, 1.2))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", -16, 12, SKIN)))

    # 2. Dark Athletic Compression Shorts
    out.append(stroke_shape(i2, "ShortsWaistSeam", [(-46.0, -18.0), (-43.0, 0.0), (-46.0, 19.0)], 1.5, "800F172A", 0.8))
    out.append(stroke_shape(i2, "ShortsGluteHi", [(-80.0, -16.0), (-62.0, -17.0), (-50.0, -10.0)], 2.8, "40FFFFFF", 2.8))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts_pts, skin_fill("PelvisShorts", -24, 24, SHORTS, x0=-96, x1=-42)))

    # 3. Activated Pectoralis Major (Upper & Lower Heads) + Sculpted Torso
    out.append(stroke_shape(i2, "SternumCleft", [(46.0, 24.5), (56.0, 12.0), (66.0, 2.0)], 1.5, "A67F1D1D", 0.4))
    out.append(stroke_shape(i2, "PecClavicularGrooveNear", [(38.0, 4.0), (54.0, 13.0)], 1.15, "997F1D1D", 0.3))
    out.append(stroke_shape(i2, "PecClavicularGrooveFar", [(64.0, 6.0), (76.0, 12.0)], 1.1, "997F1D1D", 0.3))
    out.append(stroke_shape(i2, "PecNearHi", [(18.0, 16.0), (36.0, 15.0), (48.0, 19.0)], 2.4, HIGHLIGHT, 2.2))
    out.append(stroke_shape(i2, "PecFarHi", [(54.0, 16.0), (68.0, 15.0)], 2.0, HIGHLIGHT, 1.8))

    out.append(smooth_shape(i2, "PecUpperNear", pec_upper_near_pts, muscle_paint_fn("PecUpNear", pec_upper_t, 0.95)))
    out.append(smooth_shape(i2, "PecUpperFar", pec_upper_far_pts, muscle_paint_fn("PecUpFar", pec_upper_t, 0.90)))
    out.append(smooth_shape(i2, "PecLowerNear", pec_lower_near_pts, muscle_paint_fn("PecLowNear", pec_lower_t, 1.05)))
    out.append(smooth_shape(i2, "PecLowerFar", pec_lower_far_pts, muscle_paint_fn("PecLowFar", pec_lower_t, 0.95)))

    out.append(stroke_shape(i2, "SerratusRib1", [(-8.0, 2.0), (8.0, 10.0)], 1.2, SOFT_SHADOW, 0.6))
    out.append(stroke_shape(i2, "SerratusRib2", [(-20.0, 4.0), (-4.0, 12.0)], 1.2, SOFT_SHADOW, 0.6))
    out.append(smooth_shape(i2, "TrapSculptPlate", trap_plate_pts, sculpt_plate))
    out.append(smooth_shape(i2, "ScapulaSculptPlate", scapula_plate_pts, sculpt_plate))
    out.append(smooth_shape(i2, "LatSculptPlate", lat_plate_pts, sculpt_plate))
    out.append(stroke_shape(i2, "TrapScapulaCrest", [(8.0, -14.0), (38.0, -14.0), (62.0, -8.0)], 1.4, SOFT_SHADOW, 1.0))
    out.append(stroke_shape(i2, "TorsoBackHi", [(-42.0, -18.0), (4.0, -20.0), (50.0, -16.0)], 3.8, HIGHLIGHT, 4.2))
    out.append(smooth_shape(i2, "PushUpTorso", torso_pts, skin_fill("Torso", -25, 26, SKIN, x0=-54, x1=82)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    near_arm_xml = build_push_up_arm("        ", "Near", False)
    near_leg_xml = build_push_up_leg("        ", "Near", False)
    torso_xml = build_push_up_torso_and_head()
    far_leg_xml = build_push_up_leg("        ", "Far", True)
    far_arm_xml = build_push_up_arm("        ", "Far", True)

    shd_id = nid()
    key_double(shd_id, 16, lambda p: p["shd_sx"])
    p0 = POSES[0]

    grouped = {}
    for oid, kp_xml in KEYED:
        grouped.setdefault(oid, []).append(kp_xml)
    keyed_objects_xml = "\n".join(
        f'        <KeyedObject objectId="{oid}">\n' + "\n".join(props) + "\n        </KeyedObject>"
        for oid, props in grouped.items()
    )

    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"

    return f"""<Rive version="7.3">
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="PushUp" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Right) Push-Up Arm (Triceps Brachii, Anterior Deltoid & Planted Hand) -->
{near_arm_xml}

        <!-- 2. Near (Right) Plank Leg -->
{near_leg_xml}

        <!-- 3. Push-Up Torso, Pectoralis Major (Upper & Lower), Shorts & 3/4 Head -->
{torso_xml}

        <!-- 4. Far (Left) Plank Leg in 3/4 Depth -->
{far_leg_xml}

        <!-- 5. Background: Far (Left) Push-Up Arm & Planted Hand -->
{far_arm_xml}

        <!-- 6. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="306" y="{f(FLOOR - 2)}" scaleX="{f(p0['shd_sx'])}" scaleY="0.11" name="AthleteShadow" id="{shd_id}">
            <Ellipse width="230" height="230" name="AthleteShadowEllipse"/>
            <Fill name="AthleteShadowFill"><RadialGradient startX="0" startY="0" endX="115" endY="0" name="AthleteShadowGrad">
                <GradientStop colorValue="BF000000" position="0"/>
                <GradientStop colorValue="59000000" position="0.6"/>
                <GradientStop colorValue="00000000" position="1"/>
            </RadialGradient></Fill>
        </Shape>
        <Shape x="{W / 2}" y="{f(FLOOR + 1)}" name="FloorLine">
            <Rectangle width="{W - 40}" height="2" cornerRadiusTL="1" name="FloorRect"/>
            <Fill name="FloorFill"><LinearGradient startX="{-(W - 40) / 2}" startY="0" endX="{(W - 40) / 2}" endY="0" name="FloorGrad">
                <GradientStop colorValue="00475569" position="0"/>
                <GradientStop colorValue="FF475569" position="0.2"/>
                <GradientStop colorValue="FF475569" position="0.8"/>
                <GradientStop colorValue="00475569" position="1"/>
            </LinearGradient></Fill>
        </Shape>
        <Shape x="{W / 2}" y="{f((FLOOR + H) / 2 + 1)}" name="FloorBand">
            <Rectangle width="{W}" height="{f(band_h)}" name="FloorBandRect"/>
            {band_fill}
        </Shape>
        <Shape x="{W / 2}" y="{H / 2}" name="Backdrop">
            <Rectangle width="{W}" height="{H}" name="BackdropRect"/>
            <Fill name="BackdropFill"><RadialGradient startX="0" startY="-40" endX="0" endY="{H * 0.75}" name="BackdropGrad">
                <GradientStop colorValue="FF1E293B" position="0"/>
                <GradientStop colorValue="FF0F172A" position="1"/>
            </RadialGradient></Fill>
        </Shape>

        <StateMachine name="State Machine 1" id="0:7">
            <StateMachineLayer name="Motion" id="0:8">
                <AnyState x="200" y="-120"/>
                <ExitState x="400" y="-120"/>
                <EntryState>
                    <StateTransition stateToId="0:12"/>
                </EntryState>
                <AnimationState x="200" animationId="0:60" id="0:12"/>
            </StateMachineLayer>
        </StateMachine>

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="PushUp" id="0:60">
{keyed_objects_xml}
        </LinearAnimation>
    </Artboard>
</Rive>
"""


# ---------------------------------------------------------------- Verbatim Rive 7.3 Binary Compiler (52-byte TOC)
def _compile_rml_bytes(rml_path):
    """Byte-for-byte Rive 7.3 binary compiler matching `~/.rive/bin/rive . --once`."""
    def varuint(v):
        v = int(v)
        out = bytearray()
        while True:
            b = v & 0x7F
            v >>= 7
            if v:
                out.append(b | 0x80)
            else:
                out.append(b)
                return bytes(out)

    def prop_u(pk, val):
        return varuint(pk) + varuint(int(val))

    def prop_f(pk, val):
        return varuint(pk) + struct.pack("<f", float(val))

    def prop_s(pk, val):
        b = val.encode("utf-8")
        return varuint(pk) + varuint(len(b)) + b

    def prop_c(pk, hex_str):
        a, r, g, b = (int(hex_str[i : i + 2], 16) for i in (0, 2, 4, 6))
        return varuint(pk) + bytes([b, g, r, a])

    root = ET.parse(rml_path).getroot()
    ab = root.find("Artboard")
    header = bytes([
        82, 73, 86, 69, 7, 3, 0, 196, 1, 236, 1, 238, 3, 229, 4, 230, 4, 231, 4,
        232, 4, 233, 4, 234, 4, 235, 4, 236, 4, 241, 4, 242, 4, 237, 5, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0,
    ])
    assert len(header) == 52
    out = bytearray(header)
    out += varuint(23) + b"\x00"

    comp_idx, id_to_comp, next_comp = {}, {}, [0]

    def reg_comp(el):
        idx = next_comp[0]
        next_comp[0] += 1
        comp_idx[el] = idx
        if "id" in el.attrib:
            id_to_comp[el.attrib["id"]] = idx

    drawables = [c for c in ab if c.tag not in ("StateMachine", "LinearAnimation")]
    anims = [c for c in ab if c.tag == "LinearAnimation"]
    sms = [c for c in ab if c.tag == "StateMachine"]

    reg_comp(ab)
    for d in drawables:
        for el in d.iter():
            reg_comp(el)

    out += varuint(1) + prop_u(236, 0)
    if ab.attrib.get("clip") == "true":
        out += prop_u(196, 1)
    out += prop_f(7, ab.attrib["width"]) + prop_f(8, ab.attrib["height"])
    if "styleId" in ab.attrib:
        out += prop_u(494, id_to_comp[ab.attrib["styleId"]])
    out += prop_s(4, ab.attrib["name"]) + b"\x00"

    cap_map = {"butt": 0, "round": 1, "square": 2}
    join_map = {"miter": 0, "round": 1, "bevel": 2}

    def emit_drawable(el, parent_id):
        tag, at = el.tag, el.attrib
        if tag == "LayoutComponentStyle":
            out.extend(varuint(420))
            for pk in (613, 614, 615, 616, 617, 618, 619, 620, 625, 626):
                out.extend(prop_u(pk, 1))
            out.extend(prop_s(4, at["name"]) + prop_u(5, parent_id) + b"\x00")
        elif tag in ("Node", "Shape", "Ellipse", "Rectangle"):
            out.extend(varuint({"Node": 2, "Shape": 3, "Ellipse": 4, "Rectangle": 7}[tag]))
            if "cornerRadiusTL" in at and float(at["cornerRadiusTL"]) != 0:
                out.extend(prop_f(31, at["cornerRadiusTL"]))
            if "width" in at:
                out.extend(prop_f(20, at["width"]))
            if "height" in at:
                out.extend(prop_f(21, at["height"]))
            if "x" in at and float(at["x"]) != 0:
                out.extend(prop_f(13, at["x"]))
            if "y" in at and float(at["y"]) != 0:
                out.extend(prop_f(14, at["y"]))
            if "rotation" in at and float(at["rotation"]) != 0:
                out.extend(prop_f(15, at["rotation"]))
            if "scaleX" in at and float(at["scaleX"]) != 1:
                out.extend(prop_f(16, at["scaleX"]))
            if "scaleY" in at and float(at["scaleY"]) != 1:
                out.extend(prop_f(17, at["scaleY"]))
            if "name" in at:
                out.extend(prop_s(4, at["name"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag == "PointsPath":
            out.extend(varuint(16))
            if at.get("isClosed") == "true":
                out.extend(prop_u(32, 1))
            if "name" in at:
                out.extend(prop_s(4, at["name"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag == "CubicMirroredVertex":
            out.extend(varuint(35))
            if "rotation" in at and float(at["rotation"]) != 0:
                out.extend(prop_f(82, at["rotation"]))
            if "distance" in at and float(at["distance"]) != 0:
                out.extend(prop_f(83, at["distance"]))
            if "x" in at and float(at["x"]) != 0:
                out.extend(prop_f(24, at["x"]))
            if "y" in at and float(at["y"]) != 0:
                out.extend(prop_f(25, at["y"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag == "StraightVertex":
            out.extend(varuint(5))
            if "radius" in at and float(at["radius"]) != 0:
                out.extend(prop_f(26, at["radius"]))
            if "x" in at and float(at["x"]) != 0:
                out.extend(prop_f(24, at["x"]))
            if "y" in at and float(at["y"]) != 0:
                out.extend(prop_f(25, at["y"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag == "Fill":
            out.extend(varuint(20))
            if "name" in at:
                out.extend(prop_s(4, at["name"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag == "Stroke":
            out.extend(varuint(24))
            if "cap" in at and cap_map.get(at["cap"], 0) != 0:
                out.extend(prop_u(48, cap_map[at["cap"]]))
            if "join" in at and join_map.get(at["join"], 0) != 0:
                out.extend(prop_u(49, join_map[at["join"]]))
            if "thickness" in at and float(at["thickness"]) != 1:
                out.extend(prop_f(47, at["thickness"]))
            if "name" in at:
                out.extend(prop_s(4, at["name"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag == "SolidColor":
            out.extend(varuint(18) + prop_c(37, at["colorValue"]))
            if "name" in at:
                out.extend(prop_s(4, at["name"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag in ("LinearGradient", "RadialGradient"):
            out.extend(varuint(22 if tag == "LinearGradient" else 17))
            for pk, attr in ((42, "startX"), (33, "startY"), (34, "endX"), (35, "endY")):
                if attr in at and float(at[attr]) != 0:
                    out.extend(prop_f(pk, at[attr]))
            if "name" in at:
                out.extend(prop_s(4, at["name"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag == "GradientStop":
            out.extend(varuint(19) + prop_c(38, at["colorValue"]))
            if "position" in at and float(at["position"]) != 0:
                out.extend(prop_f(39, at["position"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag == "Feather":
            out.extend(varuint(533))
            if float(at["strength"]) != 12:
                out.extend(prop_f(749, at["strength"]))
            if "name" in at:
                out.extend(prop_s(4, at["name"]))
            out.extend(prop_u(5, parent_id) + b"\x00")

        my_id = comp_idx[el]
        for ch in el:
            emit_drawable(ch, my_id)

    for d in drawables:
        emit_drawable(d, 0)

    for anim in anims:
        at = anim.attrib
        out.extend(varuint(31) + prop_u(59, 1) + prop_u(56, at["fps"]) + prop_u(57, at["duration"]))
        out.extend(prop_s(55, at["name"]) + b"\x00")
        for ko in anim:
            oid = ko.attrib["objectId"]
            if oid not in id_to_comp:
                continue
            kps = [kp for kp in ko if len(kp) > 0]
            if not kps:
                continue
            out.extend(varuint(25) + prop_u(51, id_to_comp[oid]) + b"\x00")
            for kp in kps:
                out.extend(varuint(26) + prop_u(53, kp.attrib["propertyKey"]) + b"\x00")
                for kf in kp:
                    kat = kf.attrib
                    interp = 1 if kat.get("interpolationType") == "linear" else 0
                    fr = int(kat["frame"])
                    if kf.tag == "KeyFrameDouble":
                        out.extend(varuint(30))
                        if float(kat["value"]) != 0:
                            out.extend(prop_f(70, kat["value"]))
                        if interp != 0:
                            out.extend(prop_u(68, interp))
                        if fr != 0:
                            out.extend(prop_u(67, fr))
                        out.append(0)
                    elif kf.tag == "KeyFrameColor":
                        out.extend(varuint(37) + prop_c(88, kat["value"]))
                        if interp != 0:
                            out.extend(prop_u(68, interp))
                        if fr != 0:
                            out.extend(prop_u(67, fr))
                        out.append(0)

    for sm in sms:
        out.extend(varuint(53) + prop_s(55, sm.attrib["name"]) + b"\x00")
        for layer in sm.findall("StateMachineLayer"):
            out.extend(varuint(57) + prop_s(138, layer.attrib["name"]) + b"\x00")
            out.extend(varuint(62) + b"\x00" + varuint(64) + b"\x00" + varuint(63) + b"\x00")
            out.extend(varuint(65) + prop_u(151, 3) + b"\x00")
            out.extend(varuint(61) + prop_u(149, 0) + b"\x00")

    return bytes(out)


def publish():
    BUILD.mkdir(parents=True, exist_ok=True)
    riv_bytes = _compile_rml_bytes(OUT)
    (BUILD / "push_up.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (42, "frame_mid"), (78, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(720, 0, 265))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
