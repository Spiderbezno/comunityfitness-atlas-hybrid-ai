#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive 7.3 scene for Diamond Push Up (id: 'push_up_diamond').

Matches the 2-panel 3/4 front-right Diamond Push-Up anatomical reference chart (media_1793717534080_d7510f11.webp):
  - Top-Left Panel (r = 0.0, Close-Grip Diamond High-Plank Lockout):
    * Athlete holds a rigid straight-body high plank from dorsiflexed toes on the left (`x ~ 138..164`)
      through sculpted calves, quadriceps, dark compression shorts, and braced torso.
    * Both hands are planted close together directly beneath the sternum (`NEAR_WRIST = (368, 290)`,
      `FAR_WRIST = (398, 282)`), angled inward so the thumbs and index fingers touch to form the classic
      diamond/triangle shape on the floor.
  - Bottom-Right Panel (r = 1.0, Bottom Chest-Over-Diamond Hover):
    * Body pivots forward and down as a rigid plank (`sh_near` moves from `(376, 162)` to `(400, 200)`
      directly over the diamond hands).
    * Near (Right) elbow drives backward along the ribcage (`elbow_near = (318, 232)`), creating the
      signature acute triceps-loading angle where the forearm slopes forward-down from `(318, 232)` to
      the diamond hand at `(368, 290)` while the chest hovers just above the diamond hands.
  - Highlighted Target Muscle Groups (all 5 labeled muscles from the reference chart):
    1. Triceps brachii (Primary — intense crimson-red lateral & long head crescent on upper arm, `scale = 1.00`)
    2. Lower pectoralis major (Primary/Synergist — sternocostal inner/lower chest head, `scale = 0.90`)
    3. Upper pectoralis major (Primary/Synergist — clavicular upper/inner chest head, `scale = 0.88`)
    4. Anterior deltoid (Primary/Synergist — front shoulder cap on near & far shoulders, `scale = 0.88`)
    5. Biceps brachii, short head (Dynamic Stabilizer — inner/ventral upper arm stabilizer, `scale = 0.78`)

Run:
    python3 gen_push_up_diamond.py            # writes scene.rml
    python3 gen_push_up_diamond.py --publish  # compiles assets/animations/push_up_diamond.riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/push_up_diamond.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/push_up_diamond.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s @ 60fps smooth diamond push-up cycle
STEP = 2

# Stationary Close-Grip Diamond Wrists on Floor (thumbs & index fingers converging under the chest)
NEAR_WRIST = (368.0, 290.0)
FAR_WRIST = (398.0, 282.0)

# Reference Limb Lengths for 3D Foreshortened Arm Solver
UPPER_ARM_NEAR, FOREARM_NEAR = 68.0, 72.0
UPPER_ARM_FAR, FOREARM_FAR = 64.0, 64.0

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


def diamond_progress(frame):
    """0.0 at top close-grip lockout (Top-Left Panel), 1.0 at bottom chest-to-diamond hover (Bottom-Right Panel):
    - 0..14:    Top close-grip lockout hold (r = 0.0)
    - 14..70:   Controlled eccentric descent to diamond hands (r: 0.0 -> 1.0)
    - 70..88:   Bottom peak triceps/inner-chest pause just above diamond hands (r = 1.0)
    - 88..144:  Explosive concentric press back to lockout (r: 1.0 -> 0.0)
    - 144..160: Top close-grip lockout hold (r = 0.0)
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
    """Compute 3/4 Diamond Push-Up transforms at progress r in [0.0, 1.0]:
    - r = 0.0: Top-Left Panel (arms extended to close diamond hands, both near & far arms clearly visible)
    - r = 1.0: Bottom-Right Panel (elbows tucked back along ribs, forearms angled forward-down to diamond hands)
    """
    # 1. Stationary Dorsiflexed Ankles on the Left (pivoting slightly forward at r=1.0 as shoulders travel over diamond)
    ankle_near = (lerp(144.0, 154.0, r), 264.0)
    ankle_far = (lerp(160.0, 170.0, r), 252.0)

    # 2. Hip Positions pivoting along a constant-radius arc around the ankles so knees stay locked straight!
    leg_span_near = L_THIGH_NEAR + L_SHIN_NEAR - 1.2  # 140.8 px
    leg_span_far = L_THIGH_FAR + L_SHIN_FAR - 1.2     # 136.8 px
    leg_ang_near = math.radians(lerp(-25.5, -17.5, r))
    leg_ang_far = math.radians(lerp(-25.5, -17.5, r))

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
    foot_near_rot = math.radians(lerp(4.0, 12.0, r))
    foot_far_rot = math.radians(lerp(4.0, 12.0, r))

    # 3. Torso Pivot & Rotation aligned with the forward-and-down diamond push-up descent
    torso_x = lerp(346.0, 362.0, r)
    torso_y = lerp(176.0, 214.0, r)
    torso_rot = math.radians(lerp(-14.5, -2.0, r))

    # 4. World-Space Shoulder Positions & Diamond Push-Up Elbow Trajectories
    sh_near = (lerp(376.0, 396.0, r), lerp(162.0, 200.0, r))
    sh_far = (lerp(416.0, 428.0, r), lerp(154.0, 206.0, r))

    # Near (Right) Elbow in Diamond Push-Up:
    # - r = 0.0 (Top-Left Panel): (366, 226) along the extended arm from sh_near=(376, 162) to NEAR_WRIST=(368, 290)
    # - r = 1.0 (Bottom-Right Panel): (320, 232) tucked back toward the ribs so the forearm angles forward-down
    #   from (320, 232) to NEAR_WRIST=(368, 290) — exact match to the Bottom-Right reference panel!
    elbow_near = quad_interp_pt((366.0, 226.0), (340.0, 229.0), (320.0, 232.0), r)

    # Far (Left) Elbow in Diamond Push-Up:
    # - r = 0.0 (Top-Left Panel): (410, 218) clearly visible under the chest/far shoulder above FAR_WRIST=(398, 282)
    # - r = 1.0 (Bottom-Right Panel): (376, 222) tucked behind the chest/ribs
    elbow_far = quad_interp_pt((410.0, 218.0), (392.0, 220.0), (376.0, 222.0), r)

    ua_near, ua_near_sx, fa_near, fa_near_sx = solve_foreshortened_arm(
        sh_near, elbow_near, NEAR_WRIST, UPPER_ARM_NEAR, FOREARM_NEAR
    )
    ua_far, ua_far_sx, fa_far, fa_far_sx = solve_foreshortened_arm(
        sh_far, elbow_far, FAR_WRIST, UPPER_ARM_FAR, FOREARM_FAR
    )
    delt_near_rot = lerp(ua_near, math.radians(106.0), 0.70 * r)
    delt_far_rot = lerp(ua_far, math.radians(98.0), 0.65 * r)

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
POSES = {fr: pose(diamond_progress(fr)) for fr in FRAMES}

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


# ---------------------------------------------------------------- 1. 3D-Foreshortened Diamond Push-Up Arms & Converging Diamond Hands
def build_diamond_arm(indent, prefix, is_far):
    """Builds the Near (Right) or Far (Left) Diamond Push-Up Arm:
    - Stationary diamond-grip hands planted close together under the chest (`NEAR_WRIST = (368, 290)`, `FAR_WRIST = (398, 282)`)
      with thumbs & index fingers angled inward to form a diamond on the floor.
    - 3D-foreshortened Forearm (`Elbow -> Wrist`)
    - 3D-foreshortened Upper Arm (`Shoulder -> Elbow`) with primary glowing Triceps brachii (`scale = 1.00`)
      and stabilizing Biceps brachii, short head (`scale = 0.78`)
    - Unscaled Deltoid Cap at `Shoulder` with glowing Anterior deltoid (`scale = 0.88`)."""
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

    # In a Diamond Push-Up, Triceps brachii is the #1 primary mover (glows deep crimson at peak)
    def triceps_t(p):
        return 0.52 + 0.48 * (p["r"] ** 0.75)

    def ant_delt_t(p):
        return 0.40 + 0.50 * (p["r"] ** 0.80)

    def biceps_short_t(p):
        return 0.34 + 0.44 * (p["r"] ** 0.85)

    # 1. Stationary Diamond-Grip Hand on Floor:
    #    - Near (Right) Hand at (368, 290): fingers angled forward-right & inward (`x = 360..404, y = 286..301`),
    #      thumb extending up-right (`(382, 286) -> (396, 288)`) to meet the Far thumb!
    #    - Far (Left) Hand at (398, 282): fingers angled forward-left & inward (`x = 388..420, y = 278..295`)
    #      with darker 3/4 depth contrast so the diamond triangle between the hands is unmistakably clear!
    if not is_far:
        hand_pts = [
            (wx - 8.0, wy - 2.0), (wx + 8.0, wy - 4.0), (wx + 28.0, wy - 2.0),
            (wx + 37.0, wy + 4.5), (wx + 35.0, wy + 9.5), (wx + 18.0, wy + 11.0),
            (wx - 4.0, wy + 9.5), (wx - 9.5, wy + 5.0),
        ]
    else:
        hand_pts = [
            (wx - 8.0, wy - 2.5), (wx + 7.0, wy - 3.0), (wx + 21.0, wy + 4.0),
            (wx + 22.0, wy + 10.5), (wx + 12.0, wy + 12.5), (wx - 4.0, wy + 8.0),
            (wx - 12.0, wy + 5.5), (wx - 10.0, wy + 1.0),
        ]

    # 2. Forearm (0 .. fa_len from Elbow to Wrist)
    fa_pts = [
        (-7.0, 0.0), (-4.0, -9.2), (fa_len * 0.32, -10.5), (fa_len - 5.0, -6.5),
        (fa_len + 4.0, 0.0), (fa_len - 5.0, 6.5), (fa_len * 0.32, 10.5), (-4.0, 9.2),
    ]

    # 3. Upper Arm (0 .. ua_len from Shoulder to Elbow)
    # Near (Right) arm shows its lateral/posterior surface: Triceps brachii (posterior/dorsal, +Y) is highlighted
    # while the anterior/lateral brachialis-biceps border (-Y) is sculpted silver-slate skin.
    # Far (Left) arm shows its medial/anterior surface under the chest: Biceps brachii short head (-Y) is highlighted!
    ua_pts = [
        (-8.0, 0.0), (-5.0, -11.5), (12.0, -12.5), (ua_len * 0.55, -11.0), (ua_len - 4.0, -7.8),
        (ua_len + 5.5, 0.0), (ua_len - 4.0, 8.8), (ua_len * 0.55, 12.8), (12.0, 13.2), (-5.0, 11.5),
    ]
    triceps_pts = [
        (13.5, -1.2),
        (ua_len * 0.48, -0.8),
        (ua_len - 3.5, 1.5),
        (ua_len - 5.5, 8.8),
        (ua_len * 0.52, 12.8),
        (15.0, 12.2),
    ]
    biceps_short_pts = [
        (12.0, -1.0),
        (ua_len * 0.55, -0.8),
        (ua_len - 5.5, -2.2),
        (ua_len - 7.5, -8.0),
        (ua_len * 0.48, -11.0),
        (13.0, -10.2),
    ]

    # 4. Deltoid Cap at Shoulder (`0,0`) with Lateral Deltoid in silver and Anterior Deltoid highlighted on the front (-Y) edge
    delt_pts = [
        (-10.5, 0.0), (-6.5, -12.5), (5.5, -13.5), (16.5, -9.2),
        (19.5, 0.0), (16.0, 9.8), (5.5, 13.5), (-6.5, 12.5),
    ]
    ant_delt_pts = [
        (-4.0, -2.5),
        (5.5, -13.2),
        (16.8, -9.0),
        (18.0, -2.2),
        (6.5, -1.0),
    ]

    out = [f'{indent}<Node name="{prefix}DiamondArmGroup">']

    # 1. Stationary Diamond-Grip Hand & Fingers on Floor (Topmost in Arm Group)
    if not is_far:
        out.append(stroke_shape(i2, "NearThumbIndexDiamond", [(wx + 12.0, wy - 2.2), (wx + 28.0, wy - 0.5)], 1.2, HIGHLIGHT, 0.8))
        out.append(stroke_shape(i2, "NearFinger1", [(wx + 12.0, wy + 1.5), (wx + 33.0, wy + 5.0)], 1.05, SOFT_SHADOW, 0.2))
        out.append(stroke_shape(i2, "NearFinger2", [(wx + 10.0, wy + 4.8), (wx + 31.0, wy + 8.0)], 1.05, SOFT_SHADOW, 0.2))
        out.append(stroke_shape(i2, "NearFinger3", [(wx + 7.0, wy + 7.8), (wx + 22.0, wy + 9.8)], 1.05, SOFT_SHADOW, 0.2))
        out.append(stroke_shape(i2, "NearHandHi", [(wx - 2.0, wy + 1.5), (wx + 18.0, wy + 3.5)], 2.2, HIGHLIGHT, 2.0))
        out.append(smooth_shape(i2, "NearPlantedHand", hand_pts, skin_fill("NearHand", wy - 4, wy + 12, skin)))
    else:
        # Far hand with dark fingerless training glove / 3/4 depth contrast matching reference illustration
        glove_back_pts = [
            (wx - 6.0, wy - 2.0), (wx + 7.0, wy - 2.5), (wx + 16.0, wy + 2.5),
            (wx + 12.0, wy + 8.5), (wx - 3.0, wy + 6.5),
        ]
        out.append(stroke_shape(i2, "FarFinger1", [(wx + 6.0, wy + 3.0), (wx + 19.0, wy + 7.5)], 0.95, SOFT_SHADOW, 0.2))
        out.append(stroke_shape(i2, "FarFinger2", [(wx + 3.0, wy + 5.5), (wx + 16.0, wy + 10.0)], 0.95, SOFT_SHADOW, 0.2))
        out.append(smooth_shape(i2, "FarGloveContrast", glove_back_pts, skin_fill("FarGlove", wy - 3, wy + 9, SHORTS_FAR)))
        out.append(smooth_shape(i2, "FarPlantedHand", hand_pts, skin_fill("FarHand", wy - 3, wy + 13, skin)))

    # 2. Unscaled Deltoid Cap & Glowing Anterior Deltoid at Shoulder Origin
    out.append(
        f'{i2}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" '
        f'rotation="{f(p0[delt_rot_key])}" name="{prefix}DeltoidNode" id="{delt_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}AntDeltHi", [(2.0, -7.5), (15.0, -6.5)], 2.2, HIGHLIGHT, 2.0))
    out.append(smooth_shape(i3, f"{prefix}AnteriorDeltoid", ant_delt_pts, muscle_paint_fn(prefix + "AntDelt", ant_delt_t, 0.95)))
    out.append(stroke_shape(i3, f"{prefix}LatDeltGroove", [(0.0, 2.0), (16.0, 1.5)], 1.2, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}LatDeltHi", [(1.0, 6.5), (15.0, 5.5)], 2.8, HIGHLIGHT, 2.8))
    out.append(smooth_shape(i3, f"{prefix}DeltoidCap", delt_pts, skin_fill(prefix + "Delt", -15, 15, skin)))
    out.append(f"{i2}</Node>")

    # 3. 3D-Foreshortened Upper Arm with Glowing Triceps Brachii (Near & Far) and Biceps Brachii Short Head (Far medial view)
    out.append(
        f'{i2}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" '
        f'rotation="{f(p0[ua_key])}" scaleX="{f(p0[ua_sx_key])}" name="{prefix}UpperArmNode" id="{ua_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}TricepsHi", [(16.0, 6.2), (ua_len - 8.0, 5.2)], 2.8, HIGHLIGHT, 2.5))
    out.append(stroke_shape(i3, f"{prefix}TricepsHeadLine", [(17.0, 3.2), (ua_len * 0.70, 2.6)], 1.05, "807C2D12", 0.3))
    out.append(smooth_shape(i3, f"{prefix}TricepsBrachii", triceps_pts, muscle_paint_fn(prefix + "Triceps", triceps_t, 1.05)))
    if is_far:
        out.append(stroke_shape(i3, f"{prefix}BicepsShortHi", [(15.0, -5.5), (ua_len - 10.0, -5.0)], 1.8, HIGHLIGHT, 1.8))
        out.append(smooth_shape(i3, f"{prefix}BicepsBrachiiShortHead", biceps_short_pts, muscle_paint_fn(prefix + "BicShort", biceps_short_t, 0.88)))
    else:
        out.append(stroke_shape(i3, f"{prefix}BrachialisHi", [(15.0, -5.8), (ua_len - 10.0, -4.8)], 2.2, HIGHLIGHT, 2.0))
    out.append(stroke_shape(i3, f"{prefix}HumerusGroove", [(14.0, -1.0), (ua_len - 6.0, -0.5)], 1.25, CORE_SHADOW, 0.8))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UA", -13, 13, skin)))
    out.append(f"{i2}</Node>")

    # 4. 3D-Foreshortened Forearm (Elbow -> Planted Diamond Wrist)
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
    """Builds the Near (Right) or Far (Left) Diamond Push-Up leg in sculpted silver-slate skin with dark compression shorts."""
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


# ---------------------------------------------------------------- 3. Diamond Push-Up Torso, Inner/Upper/Lower Pectoralis Major & 3/4 Head
def build_diamond_torso_and_head():
    """Canonical 3/4 front-right CommunityFitness torso in a Diamond Push-Up:
    - Shows the 3/4 underside of the chest with glowing Upper pectoralis major (clavicular head)
      and Lower pectoralis major (sternocostal head) squeezed inward over the diamond hands.
    - Sculpted upper back/trapezius, serratus anterior ribs, dark athletic compression shorts,
      and volumetric 3/4 Head looking down-right ahead of the diamond hands."""
    ind = "        "
    i2 = ind + "    "

    torso_id = nid()
    key_double(torso_id, 13, lambda p: p["torso_x"])
    key_double(torso_id, 14, lambda p: p["torso_y"])
    key_double(torso_id, 15, lambda p: p["torso_rot"])
    p0 = POSES[0]

    def pec_lower_t(p):
        return 0.42 + 0.50 * (p["r"] ** 0.80)

    def pec_upper_t(p):
        return 0.40 + 0.48 * (p["r"] ** 0.80)

    pelvis_shorts_pts = [
        (-96.0, -6.0), (-80.0, -24.0), (-52.0, -23.0),
        (-42.0, -10.0), (-46.0, 22.0), (-74.0, 24.0), (-94.0, 12.0),
    ]

    torso_pts = [
        (-54.0, -22.0), (-10.0, -25.0), (36.0, -24.0), (74.0, -14.0),
        (82.0, 8.0), (62.0, 24.0), (26.0, 26.0), (-14.0, 21.0),
        (-52.0, 19.0),
    ]

    # 1. Lower pectoralis major (sternocostal head) — Near (Right) & Far (Left) chest bellies
    pec_lower_near_pts = [
        (8.0, 6.0), (42.0, 2.0), (54.0, 14.0),
        (46.0, 25.0), (16.0, 24.0), (4.0, 15.0),
    ]
    pec_lower_far_pts = [
        (46.0, 12.0), (66.0, 6.0), (78.0, 13.0),
        (68.0, 23.0), (48.0, 24.5),
    ]

    # 2. Upper pectoralis major (clavicular head) — Near (Right) & Far (Left) upper chest bands
    pec_upper_near_pts = [
        (38.0, -4.0), (64.0, -6.0), (66.0, 6.0),
        (54.0, 14.0), (40.0, 4.0),
    ]
    pec_upper_far_pts = [
        (64.0, -5.0), (82.0, -2.0), (84.0, 8.0),
        (76.0, 13.0), (64.0, 6.0),
    ]

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
        f'name="DiamondTorsoAndHeadNode" id="{torso_id}">'
    ]

    # 1. Volumetric 3/4 Head & Muscular Neck
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
    out.append(smooth_shape(i2, "DiamondTorso", torso_pts, skin_fill("Torso", -25, 26, SKIN, x0=-54, x1=82)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    near_arm_xml = build_diamond_arm("        ", "Near", False)
    near_leg_xml = build_push_up_leg("        ", "Near", False)
    torso_xml = build_diamond_torso_and_head()
    far_leg_xml = build_push_up_leg("        ", "Far", True)
    far_arm_xml = build_diamond_arm("        ", "Far", True)

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
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="DiamondPushUp" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Right) Diamond Push-Up Arm (Triceps Brachii, Biceps Short Head, Anterior Deltoid & Near Diamond Hand) -->
{near_arm_xml}

        <!-- 2. Near (Right) Plank Leg -->
{near_leg_xml}

        <!-- 3. Diamond Push-Up Torso, Pectoralis Major (Upper & Lower), Shorts & 3/4 Head -->
{torso_xml}

        <!-- 4. Far (Left) Plank Leg in 3/4 Depth -->
{far_leg_xml}

        <!-- 5. Background: Far (Left) Diamond Push-Up Arm & Far Diamond Hand -->
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="DiamondPushUp" id="0:60">
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
    (BUILD / "push_up_diamond.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (42, "frame_mid"), (78, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(720, 0, 275))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
