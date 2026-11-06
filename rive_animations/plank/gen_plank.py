#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive 7.3 scene for Forearm Plank (id: 'plank').

Uses our canonical 3/4 front-right CommunityFitness mannequin (volumetric 3/4 head with hair/ear/brow/eye/mouth,
muscular neck, sculpted deltoids/biceps/triceps/forearms with elbows planted directly under the shoulders and
forearms flat on FLOOR = 300.0, braced ribcage with serratus anterior, 6-pack rectus abdominis & external obliques,
dark athletic compression shorts with posterior pelvic tilt / glute squeeze, sculpted quadriceps/calves, and
dorsiflexed toes planted on FLOOR = 300.0).

Demonstrates textbook Forearm Plank biomechanics (avoiding the 4 compensations in the reference chart:
no lumbar hyperextension/sagging, no dropped pelvis, no flared ribs, and no thoracic hyperkyphosis):
  - Athlete transitions smoothly between a relaxed setup hover and a locked-in hollow-body isometric plank brace
    with active diaphragmatic core breathing, scapular protraction, and full abdominal/glute/quadriceps tension.
  - Highlighted Target Muscle Groups (pulsing from warm orange #FFF97316 to intense crimson #FFF43F5E):
    1. Rectus abdominis & Transverse abdominis (Primary Core — anti-extension abdominal wall)
    2. External & Internal obliques (Primary Core — lateral waist & ribcage anti-rotation/rib-down control)
    3. Serratus anterior & Anterior deltoid (Secondary — active forearm-plank scapular protraction against floor)
    4. Gluteus maximus & Quadriceps / Rectus femoris (Secondary — posterior pelvic tilt & knee lock)

Run:
    python3 gen_plank.py            # writes scene.rml
    python3 gen_plank.py --publish  # compiles assets/animations/plank.riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/plank.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/plank.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps isometric forearm-plank brace & breathing loop
STEP = 2

# Segment Lengths for Exact 2-Bone IK (Hip -> Knee -> Ankle)
L_THIGH_NEAR = 78.0
L_SHIN_NEAR = 76.0
L_THIGH_FAR = 76.0
L_SHIN_FAR = 74.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "4D0F172A"

# Target Muscle Heat Colors: warm orange (#FFF97316) -> intense crimson (#FFF43F5E)
MUSCLE_LOW = (0xE6, 0xF9, 0x73, 0x16)
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


EASE_BRACE = cubic_bezier(0.36, 0.0, 0.24, 1.0)
EASE_RELEASE = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def plank_progress(frame):
    """Returns forearm-plank core-brace progress r in [0.0, 1.0] + subtle breathing wave across 160 frames:
    - 0..14:   Low setup posture before full hollow-body lock (r = 0.0)
    - 14..52:  Concentric core & glute engagement lifting into textbook neutral forearm plank (r: 0.0 -> 1.0)
    - 52..116: Peak isometric forearm plank hold with 2 controlled diaphragmatic breathing pulses (r ~ 1.0)
    - 116..150: Controlled release back to baseline hover (r: 1.0 -> 0.0)
    - 150..160: Baseline hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 14:
        return 0.0, 0.0
    if fr <= 52:
        return EASE_BRACE((fr - 14) / 38.0), 0.0
    if fr <= 116:
        breath = math.sin(2.0 * math.pi * (fr - 52) / 64.0)
        return 1.0, breath
    if fr <= 150:
        return 1.0 - EASE_RELEASE((fr - 116) / 34.0), 0.0
    return 0.0, 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def solve_plank_leg_ik(hip, ankle, l1, l2):
    """2-bone IK from hip -> knee -> ankle in a rightward-facing (+X) forearm plank.
    Using -acos(cos_a) keeps the knee anatomically oriented (slight bend at r=0, locked straight at r=1)."""
    dx = ankle[0] - hip[0]
    dy = ankle[1] - hip[1]
    d = max(1.0, min(l1 + l2 - 0.8, math.hypot(dx, dy)))
    base_ang = math.atan2(dy, dx)
    cos_a = max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2.0 * l1 * d)))
    thigh_ang = base_ang - math.acos(cos_a)
    knee = (hip[0] + l1 * math.cos(thigh_ang), hip[1] + l1 * math.sin(thigh_ang))
    shin_ang = math.atan2(ankle[1] - knee[1], ankle[0] - knee[0])
    return thigh_ang, knee, shin_ang


def pose(r_breath):
    """Compute 3/4 Forearm Plank transforms at (r, breath).
    - At r = 0.0: Hips sit slightly lower (`y + 11` px) with softer knees before full anti-extension lock.
    - At r = 1.0: Textbook straight forearm plank line from head (`452, 212`) through protracted shoulders
      (`412, 222`), ribs-down core (`346, 224`), posterior-tilted pelvis (`282, 226`), locked knees (`210, 248`),
      to dorsiflexed ankles (`136, 268`) with toes planted on `FLOOR = 300.0`!
    """
    r, breath = r_breath
    # Vertical anti-extension core lift (eliminating pelvic drop & rib flare) + subtle breathing micro-motion
    brace_lift = lerp(11.0, 0.0, r) - 1.6 * breath
    torso_rot = math.radians(lerp(3.2, 0.0, r) - 0.35 * breath)

    hip_near = (282.0, 226.0 + brace_lift)
    hip_far = (270.0, 216.0 + brace_lift)

    ankle_near = (136.0, 268.0)
    ankle_far = (126.0, 258.0)

    # At r = 0.0, shorten effective thigh+shin target slightly so knees have a soft 14 deg bend;
    # at r = 1.0, quadriceps contract to lock the knees into a rigid straight plank line!
    knee_soft = lerp(5.5, 0.0, r)
    thigh_near_ang, knee_near, shin_near_ang = solve_plank_leg_ik(
        hip_near, (ankle_near[0] + knee_soft, ankle_near[1] - 0.5 * knee_soft), L_THIGH_NEAR, L_SHIN_NEAR
    )
    thigh_far_ang, knee_far, shin_far_ang = solve_plank_leg_ik(
        hip_far, (ankle_far[0] + knee_soft, ankle_far[1] - 0.5 * knee_soft), L_THIGH_FAR, L_SHIN_FAR
    )

    foot_near_rot = math.radians(lerp(4.0, 8.0, r))
    foot_far_rot = math.radians(lerp(4.0, 8.0, r))
    ua_rot = math.radians(lerp(-3.5, 0.0, r) + 0.3 * breath)

    return {
        "r": r,
        "breath": breath,
        "brace_lift": brace_lift,
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
        "ua_rot": ua_rot,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(plank_progress(fr)) for fr in FRAMES}

_ANGLE_KEYS = (
    "torso_rot",
    "thigh_near_ang",
    "shin_near_ang",
    "foot_near_rot",
    "thigh_far_ang",
    "shin_far_ang",
    "foot_far_rot",
    "ua_rot",
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
    """Animated SolidColor muscle fill & edge driven by custom activation function fn_t(pose)."""
    fid, lid = nid(), nid()
    key_color(fid, 37, lambda p: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, fn_t(p)))
    key_color(lid, 37, lambda p: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, fn_t(p)))
    t0 = fn_t(POSES[0])
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- 1. Forearm-Plank Posting Arms (Elbows Under Shoulders, Forearms Flat on Floor)
def build_forearm_plank_arm(indent, prefix, is_far):
    """Builds the Near (Right) or Far (Left) Forearm-Plank arm:
    - Vertical upper arm from Shoulder (`408, 224`) down to Elbow (`408, 294`) on FLOOR = 300.0
    - Horizontal forearm resting flat along the floor (`408, 294` -> `462, 295`) with a closed neutral fist
      exactly matching the forearm plank in the reference diagram."""
    i2 = indent + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if is_far else SKIN
    dx = 22.0 if is_far else 0.0
    dy = -14.0 if is_far else 0.0

    elbow_x, elbow_y = 408.0 + dx, 294.0 + dy
    ua_id = nid()
    key_double(ua_id, 15, lambda p: p["ua_rot"])
    p0 = POSES[0]

    def delt_t(p):
        return 0.42 + 0.54 * (p["r"] ** 0.8) + 0.06 * abs(p["breath"])

    # Horizontal Forearm & Neutral Fist resting flat on the floor (static anchor on FLOOR = 300.0)
    fa_pts = [
        (400.0 + dx, 286.0 + dy), (424.0 + dx, 284.0 + dy), (448.0 + dx, 287.0 + dy),
        (456.0 + dx, 294.0 + dy), (448.0 + dx, 300.0 + dy), (422.0 + dx, 300.5 + dy),
        (400.0 + dx, 298.5 + dy),
    ]
    fist_pts = [
        (448.0 + dx, 284.0 + dy), (464.0 + dx, 283.5 + dy), (468.0 + dx, 291.5 + dy),
        (464.0 + dx, 300.0 + dy), (448.0 + dx, 299.5 + dy),
    ]

    # Upper Arm & Deltoid Cap pivoting slightly around the planted Elbow (`elbow_x, elbow_y`) as the core braces
    ua_pts = [
        (-10.0, -72.0), (10.0, -72.0), (12.5, -42.0),
        (9.5, -6.0), (5.5, 4.0), (-6.5, 4.0),
        (-10.5, -10.0), (-12.0, -44.0),
    ]
    delt_pts = [
        (-13.5, -78.0), (0.0, -85.0), (14.5, -76.0),
        (13.5, -52.0), (-1.0, -46.0), (-13.5, -56.0),
    ]
    ant_delt_pts = [
        (0.0, -82.0), (13.5, -75.0), (11.5, -54.0), (1.0, -56.0),
    ]

    out = [f'{indent}<Node name="{prefix}ForearmPlankArm">']

    # 1. Planted Horizontal Forearm & Fist on Floor
    if not is_far:
        out.append(stroke_shape(i2, "NearFistKnuckle1", [(454.0, 287.5), (463.0, 287.5)], 0.95, SOFT_SHADOW, 0.0))
        out.append(stroke_shape(i2, "NearFistKnuckle2", [(454.0, 292.0), (463.0, 292.0)], 0.95, SOFT_SHADOW, 0.0))
        out.append(stroke_shape(i2, "NearForearmCrest", [(408.0, 291.0), (430.0, 291.0), (448.0, 292.0)], 1.2, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i2, "NearForearmHi", [(408.0, 287.5), (430.0, 287.0), (448.0, 289.0)], 2.4, HIGHLIGHT, 2.5))
        out.append(stroke_shape(i2, "NearForearmSh", [(406.0, 297.5), (428.0, 298.0), (448.0, 298.0)], 3.0, CORE_SHADOW, 3.0))
    out.append(smooth_shape(i2, f"{prefix}PlantedFist", fist_pts, skin_fill(prefix + "Fist", 283 + dy, 300 + dy, skin)))
    out.append(smooth_shape(i2, f"{prefix}PlantedForearm", fa_pts, skin_fill(prefix + "FA", 284 + dy, 301 + dy, skin)))

    # 2. Vertical Upper Arm & Protracted Shoulder Cap (pivoting at planted Elbow)
    out.append(
        f'{i2}<Node x="{f(elbow_x)}" y="{f(elbow_y)}" rotation="{f(p0["ua_rot"])}" name="{prefix}UpperArmNode" id="{ua_id}">'
    )
    if not is_far:
        out.append(stroke_shape(i3, "NearDeltGroove", [(-2.0, -76.0), (-1.0, -54.0)], 1.15, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i3, "NearDeltHi", [(-4.0, -80.0), (6.0, -72.0), (5.0, -56.0)], 2.6, HIGHLIGHT, 2.8))
        out.append(smooth_shape(i3, "NearAnteriorDeltoid", ant_delt_pts, muscle_paint_fn("NearAntDelt", delt_t, 0.95)))
    out.append(smooth_shape(i3, f"{prefix}DeltoidCap", delt_pts, skin_fill(prefix + "Delt", -85, -46, skin)))
    if not is_far:
        out.append(stroke_shape(i3, "NearTricepsLine", [(-4.0, -50.0), (-3.0, -26.0), (-2.0, -10.0)], 1.2, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i3, "NearUpperArmHi", [(5.0, -50.0), (6.0, -26.0), (5.0, -10.0)], 2.6, HIGHLIGHT, 2.8))
        out.append(stroke_shape(i3, "NearUpperArmSh", [(-7.0, -48.0), (-7.0, -24.0), (-5.0, -8.0)], 3.4, CORE_SHADOW, 3.4))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UA", -72, 4, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{indent}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 2. Locked Isometric Plank Legs (Quadriceps & Glute Tension)
def build_plank_leg(indent, prefix, is_far):
    """Builds the Near (Right) or Far (Left) Forearm-Plank leg:
    - Highlights the Rectus femoris & Vastus lateralis quadriceps heads that lock the knees to prevent
      pelvic drop (Compensation #2 in the reference diagram)."""
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

    def quad_t(p):
        return 0.44 + 0.54 * (p["r"] ** 0.80) + 0.05 * abs(p["breath"])

    thigh_pts = [
        (-14.0, -11.5), (10.0, -16.8), (38.0, -16.5), (62.0, -12.5),
        (l_thigh + 2.0, -5.2), (l_thigh + 2.0, 5.2), (60.0, 11.2),
        (34.0, 15.2), (8.0, 16.5), (-14.0, 12.0),
    ]
    shorts_cuff_pts = [
        (-16.0, -12.5), (22.0, -17.2), (24.0, 16.8), (-16.0, 13.0),
    ]
    rectus_pts = [
        (16.0, -16.0), (40.0, -15.8), (62.0, -12.2), (l_thigh - 5.0, -7.2),
        (l_thigh - 7.0, -2.8), (48.0, -6.2), (20.0, -7.8),
    ]
    vastus_pts = [
        (20.0, -6.8), (44.0, -5.5), (64.0, -3.2), (l_thigh - 6.0, 1.2),
        (58.0, 5.8), (34.0, 6.2), (18.0, 2.2),
    ]

    shin_pts = [
        (-7.0, -6.2), (18.0, -6.5), (46.0, -5.5), (l_shin - 3.0, -4.0),
        (l_shin + 2.0, 0.0), (l_shin - 4.0, 4.5), (52.0, 7.2),
        (32.0, 13.8), (14.0, 13.5), (-6.0, 6.8),
    ]
    foot_pts = [
        (-7.5, -3.5), (4.5, -2.0), (7.5, 10.0),
        (9.5, 28.0), (5.5, 33.5), (-0.5, 31.5),
        (-3.5, 18.0), (-8.5, 3.5),
    ]

    out = [f'{indent}<Node name="{prefix}PlankLegGroup">']

    # 1. Dorsiflexed Bare Foot braced on FLOOR = 300.0
    out.append(
        f'{i2}<Node x="{f(p0[ankle_key][0])}" y="{f(p0[ankle_key][1])}" '
        f'rotation="{f(p0[foot_rot_key])}" name="{prefix}FootNode" id="{foot_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}FootArch", [(-2.0, 4.0), (1.0, 18.0), (3.5, 28.0)], 1.15, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}FootHi", [(2.5, 4.0), (5.5, 18.0), (7.0, 27.0)], 2.0, HIGHLIGHT, 2.2))
    out.append(smooth_shape(i3, f"{prefix}BareFoot", foot_pts, skin_fill(prefix + "Foot", -4, 34, skin)))
    out.append(f"{i2}</Node>")

    # 2. Lower Leg / Calf
    out.append(
        f'{i2}<Node x="{f(p0[knee_key][0])}" y="{f(p0[knee_key][1])}" '
        f'rotation="{f(p0[shin_ang_key])}" name="{prefix}ShinNode" id="{shin_id}">'
    )
    out.append(ellipse_shape(i3, f"{prefix}KneeCap", 0.0, -1.0, 17.0, 15.0, skin_fill(prefix + "Knee", -8, 8, skin)))
    out.append(stroke_shape(i3, f"{prefix}GastrocLine", [(12.0, 6.2), (30.0, 8.5), (48.0, 4.5)], 1.2, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}ShinHi", [(12.0, -4.0), (38.0, -3.6), (62.0, -2.4)], 2.4, HIGHLIGHT, 2.5))
    out.append(stroke_shape(i3, f"{prefix}CalfSh", [(12.0, 10.8), (30.0, 11.8), (50.0, 5.8)], 3.0, CORE_SHADOW, 3.0))
    out.append(smooth_shape(i3, f"{prefix}ShinShape", shin_pts, skin_fill(prefix + "Shin", -7, 14, skin)))
    out.append(f"{i2}</Node>")

    # 3. Thigh with Activated Quadriceps (Rectus femoris + Vastus lateralis)
    out.append(
        f'{i2}<Node x="{f(p0[hip_key][0])}" y="{f(p0[hip_key][1])}" '
        f'rotation="{f(p0[thigh_ang_key])}" name="{prefix}ThighNode" id="{thigh_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}ShortsHem", [(22.0, -16.5), (23.0, 0.0), (22.0, 16.0)], 1.4, "800F172A", 0.6))
    out.append(smooth_shape(i3, f"{prefix}ShortsCuff", shorts_cuff_pts, skin_fill(prefix + "Shorts", -17, 17, shorts)))
    out.append(stroke_shape(i3, f"{prefix}TendonStrip", [(20.0, -7.2), (44.0, -5.8), (64.0, -3.8)], 2.0, HIGHLIGHT, 1.6))
    out.append(stroke_shape(i3, f"{prefix}QuadHi", [(24.0, -13.0), (46.0, -12.0), (62.0, -8.0)], 2.2, HIGHLIGHT, 2.4))
    out.append(smooth_shape(i3, f"{prefix}VastusQuad", vastus_pts, muscle_paint_fn(prefix + "Vastus", quad_t, 0.95)))
    out.append(smooth_shape(i3, f"{prefix}RectusFemoris", rectus_pts, muscle_paint_fn(prefix + "Rectus", quad_t, 1.0)))
    out.append(stroke_shape(i3, f"{prefix}ThighPostSh", [(14.0, 12.0), (36.0, 11.0), (56.0, 7.6)], 3.4, CORE_SHADOW, 3.4))
    out.append(smooth_shape(i3, f"{prefix}ThighShape", thigh_pts, skin_fill(prefix + "Thigh", -17, 17, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{indent}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. Braced Forearm-Plank Torso, Glowing Core & Neutral Head
def build_plank_torso_and_head():
    """Canonical 3/4 front-right CommunityFitness torso in a horizontal Forearm Plank:
    - Neutral cervical & thoracic spine (no hyperkyphosis or lumbar arch)
    - Ribcage locked down into the pelvis with glowing Rectus Abdominis (4 sculpted abdominal blocks along
      the ventral belly wall), External Obliques, and Serratus Anterior digitations
    - Posterior-tilted pelvis in dark athletic compression shorts with active Gluteus Maximus engagement."""
    ind = "        "
    i2 = ind + "    "

    torso_id = nid()
    key_double(torso_id, 14, lambda p: 224.0 + p["brace_lift"])
    key_double(torso_id, 15, lambda p: p["torso_rot"])
    p0 = POSES[0]

    def abs_t(p):
        return 0.48 + 0.52 * (p["r"] ** 0.75) + 0.08 * abs(p["breath"])

    def oblique_t(p):
        return 0.45 + 0.53 * (p["r"] ** 0.78) + 0.07 * abs(p["breath"])

    def serratus_t(p):
        return 0.42 + 0.52 * (p["r"] ** 0.80) + 0.06 * abs(p["breath"])

    # Local coordinates relative to Torso Pivot `(350.0, 224.0)`:
    # Pelvis & Shorts sit at x in [-96..-52], Torso spans x in [-66..+64], Head sits at x in [+70..+122]
    pelvis_shorts_pts = [
        (-96.0, -8.0), (-82.0, -24.0), (-54.0, -23.0),
        (-44.0, -10.0), (-48.0, 20.0), (-74.0, 22.0), (-94.0, 12.0),
    ]
    # Subtle Gluteus Maximus activation window along the upper-posterior hip border of the shorts
    glute_med_pts = [
        (-86.0, -21.0), (-64.0, -22.0), (-56.0, -12.0), (-76.0, -10.0),
    ]

    torso_pts = [
        (-56.0, -21.0), (-12.0, -23.0), (34.0, -20.0), (64.0, -10.0),
        (68.0, 12.0), (46.0, 24.0), (4.0, 23.0), (-34.0, 20.0),
        (-54.0, 18.0),
    ]

    # Primary Core Target Muscle #1: Rectus Abdominis (sculpted 6-pack ventral wall along lower border of torso)
    abs_wall_pts = [
        (-46.0, 6.0), (-8.0, 8.0), (32.0, 11.0), (42.0, 21.0),
        (2.0, 22.5), (-36.0, 19.5), (-48.0, 16.5),
    ]
    # Primary Core Target Muscle #2: External Obliques (lateral waist & lower ribcage)
    oblique_pts = [
        (-48.0, -6.0), (-14.0, -6.0), (14.0, 2.0),
        (10.0, 13.0), (-22.0, 11.0), (-48.0, 7.0),
    ]
    # Secondary Target Muscle #3: Serratus Anterior (3 saw-toothed slips on the lateral ribcage behind shoulder)
    serratus_pts = [
        (8.0, -10.0), (36.0, -6.0), (34.0, 11.0), (6.0, 6.0),
    ]

    neck_pts = [
        (56.0, -12.0), (78.0, -8.0), (84.0, 12.0),
        (60.0, 14.0), (52.0, 2.0),
    ]
    head_pts = [
        (78.0, -8.0), (92.0, -16.0), (108.0, -14.0), (120.0, -4.0),
        (122.0, 10.0), (114.0, 22.0), (102.0, 28.0), (90.0, 28.0),
        (80.0, 22.0), (72.0, 10.0), (72.0, 0.0),
    ]
    hair_pts = [
        (84.0, -10.0), (98.0, -16.5), (112.0, -13.0), (121.5, -2.0),
        (121.0, 12.0), (112.0, 20.0), (109.0, 12.0), (102.0, 2.0),
        (90.0, -5.0),
    ]

    out = [
        f'{ind}<Node x="350" y="{f(224.0 + p0["brace_lift"])}" rotation="{f(p0["torso_rot"])}" '
        f'name="PlankTorsoAndHeadNode" id="{torso_id}">'
    ]

    # 1. Volumetric 3/4 Head & Neutral Neck (gaze directed at floor between fists)
    out.append(smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 84, -16, 122, 20, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i2, "Ear", 90.0, 8.0, 5.5, 7.8, solid("Ear", "FFA3B1C4"), rot_deg=32.0))
    out.append(stroke_shape(i2, "BrowShade", [(104.0, 21.0), (109.0, 17.5)], 1.3, "590F172A", 0.6))
    out.append(stroke_shape(i2, "EyeLine", [(101.5, 21.5), (105.5, 19.0)], 1.05, "730F172A", 0.4))
    out.append(stroke_shape(i2, "MouthLine", [(89.5, 24.5), (93.5, 22.5)], 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i2, "HeadCrownHi", [(86.0, -8.0), (100.0, -9.0), (110.0, -2.0)], 2.8, HIGHLIGHT, 3.2))
    out.append(stroke_shape(i2, "JawShadow", [(76.0, 15.0), (86.0, 24.5), (98.0, 25.5)], 2.4, CORE_SHADOW, 2.4))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill("Head", -16, 28, SKIN, x0=72, x1=122)))
    out.append(stroke_shape(i2, "NeckMuscleLine", [(62.0, -2.0), (74.0, 4.0), (82.0, 10.0)], 1.5, SOFT_SHADOW, 1.2))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", -12, 14, SKIN)))

    # 2. Dark Athletic Compression Shorts & Posterior Pelvic Tilt Glute Line
    out.append(stroke_shape(i2, "ShortsWaistSeam", [(-48.0, -18.0), (-45.0, 0.0), (-48.0, 18.0)], 1.5, "800F172A", 0.8))
    out.append(smooth_shape(i2, "GluteBraceAccent", glute_med_pts, muscle_paint_fn("GluteBrace", oblique_t, 0.85)))
    out.append(stroke_shape(i2, "ShortsGluteHi", [(-82.0, -16.0), (-64.0, -17.0), (-52.0, -10.0)], 2.6, "40FFFFFF", 2.8))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts_pts, skin_fill("PelvisShorts", -24, 22, SHORTS, x0=-96, x1=-44)))

    # 3. Braced Forearm-Plank Torso, Serratus Anterior, External Obliques & Rectus Abdominis (with tendinous inscriptions)
    out.append(stroke_shape(i2, "SerratusRib1", [(12.0, -6.0), (28.0, 2.0)], 1.2, "807F1D1D", 0.4))
    out.append(stroke_shape(i2, "SerratusRib2", [(8.0, 0.0), (24.0, 8.0)], 1.2, "807F1D1D", 0.4))
    out.append(stroke_shape(i2, "ObliqueRib1", [(-32.0, -3.0), (-14.0, 6.0)], 1.2, "807F1D1D", 0.4))
    out.append(stroke_shape(i2, "ObliqueRib2", [(-18.0, -3.0), (0.0, 6.0)], 1.2, "807F1D1D", 0.4))
    out.append(stroke_shape(i2, "AbInscription1", [(-28.0, 8.0), (-30.0, 20.0)], 1.25, "8C7F1D1D", 0.3))
    out.append(stroke_shape(i2, "AbInscription2", [(-8.0, 9.0), (-10.0, 21.5)], 1.25, "8C7F1D1D", 0.3))
    out.append(stroke_shape(i2, "AbInscription3", [(12.0, 10.5), (10.0, 22.0)], 1.25, "8C7F1D1D", 0.3))
    out.append(stroke_shape(i2, "AbsVentralHi", [(-36.0, 14.5), (-6.0, 16.5), (24.0, 18.0)], 2.0, "66FFFFFF", 1.8))

    out.append(smooth_shape(i2, "SerratusAnterior", serratus_pts, muscle_paint_fn("Serratus", serratus_t, 0.95)))
    out.append(smooth_shape(i2, "ExternalObliques", oblique_pts, muscle_paint_fn("Obliques", oblique_t, 1.0)))
    out.append(smooth_shape(i2, "RectusAbdominis", abs_wall_pts, muscle_paint_fn("RectusAbs", abs_t, 1.05)))

    out.append(stroke_shape(i2, "LatDorsiCrest", [(-38.0, -11.0), (4.0, -10.0), (42.0, -2.0)], 1.4, SOFT_SHADOW, 1.2))
    out.append(stroke_shape(i2, "TorsoBackHi", [(-44.0, -17.0), (0.0, -18.0), (44.0, -11.0)], 3.8, HIGHLIGHT, 4.2))
    out.append(smooth_shape(i2, "PlankTorso", torso_pts, skin_fill("Torso", -23, 24, SKIN, x0=-56, x1=68)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    near_arm_xml = build_forearm_plank_arm("        ", "Near", False)
    near_leg_xml = build_plank_leg("        ", "Near", False)
    torso_xml = build_plank_torso_and_head()
    far_leg_xml = build_plank_leg("        ", "Far", True)
    far_arm_xml = build_forearm_plank_arm("        ", "Far", True)

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
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="Plank" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Right) Forearm & Elbow Braced on Floor -->
{near_arm_xml}

        <!-- 2. Near (Right) Plank Leg (Locked Quadriceps, Calf & Dorsiflexed Bare Foot) -->
{near_leg_xml}

        <!-- 3. Forearm-Plank Torso, Pelvis Shorts, Glowing Core (Rectus Abdominis/Obliques/Serratus) & 3/4 Head -->
{torso_xml}

        <!-- 4. Far (Left) Plank Leg in 3/4 Depth -->
{far_leg_xml}

        <!-- 5. Background: Far (Left) Forearm & Elbow Braced on Floor -->
{far_arm_xml}

        <!-- 6. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="304" y="{f(FLOOR - 2)}" scaleX="1.85" scaleY="0.10" name="AthleteShadow">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="Plank" id="0:60">
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
    (BUILD / "plank.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (34, "frame_mid"), (70, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(720, 0, 240))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
