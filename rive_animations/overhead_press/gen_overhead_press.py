#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive scene for Dumbbell Overhead Press (id: 'overhead_press').

Uses our canonical standing 3/4 front-left CommunityFitness mannequin (volumetric 3/4 head with
hair/ear/brow/eye/mouth, muscular neck, sculpted pectorals, 6-pack rectus abdominis, slender waist,
dark athletic compression shorts, quadriceps, gastrocnemius calves, and planted bare feet).

Matches the 2-panel 3/4 Standing Dumbbell Overhead Press reference illustration (1999 Herculean Fit):
  - Left Panel (f = 0 & f = 160, r = 0.0 — Goalpost / Shoulder-Rack Position):
    * Athlete stands tall in a balanced 3/4 stance with feet planted on FLOOR = 300.0.
    * Upper arms are abducted outward near shoulder height (~80-85 deg from torso, elbows slightly
      below shoulder height), forearms angled vertically upward (~90 deg elbow bend) so the two heavy
      3D double-plate black dumbbells are held just above shoulder/ear height with a pronated grip.
  - Right Panel (f = 72, r = 1.0 — Full Overhead Lockout):
    * Both arms press the dumbbells vertically overhead until the arms are fully extended upward
      alongside the head/ears and the inner dumbbell plates converge above the crown of the head.
  - All 4 Labeled Target Muscle Groups (pulsing from warm orange #FFF97316 to intense crimson #FFF43F5E):
    1. Lateral deltoids (Primary — multipennate middle head of left & right shoulder caps)
    2. Anterior deltoids (Primary — front clavicular head of left & right shoulder caps)
    3. Triceps brachii (Primary/Synergist — lateral/long head on the outer-posterior aspect of both
       upper arms, extending the elbows overhead)
    4. Serratus anterior (Secondary/Stabilizer — 3 sculpted finger-like digitations on the lateral
       ribcage below the outer border of the pectoralis major, upwardly rotating the scapulae)

Run:
    python3 gen_overhead_press.py            # writes scene.rml
    python3 gen_overhead_press.py --publish  # compiles assets/animations/overhead_press.riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/overhead_press.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/overhead_press.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps loop
STEP = 2

# Canonical Standing 3/4 Athlete Scale for Overhead Press:
# Positioned slightly lower than Lateral Raise via (x, 300.0 - 0.90*(300.0 - y)) so that at full
# overhead lockout (r = 1.0) the top of the heavy double-plate dumbbells stays cleanly inside y >= 18.
BODY_SCALE_Y = 0.90


def pt_y(p):
    return (p[0], FLOOR - BODY_SCALE_Y * (FLOOR - p[1]))


def pts_y(pts):
    return [pt_y(p) for p in pts]


SHOULDER_FAR = pt_y((288.0, 98.0))    # (288.0, 118.2) — Right (far / screen-left) shoulder
SHOULDER_NEAR = pt_y((348.0, 100.0))  # (348.0, 120.0) — Left (near / screen-right) shoulder
UPPER_ARM_LEN = 39.0
FOREARM_LEN = 36.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
PLATE_DARK = ("FF334155", "FF182232", "FF090D16")
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


EASE_PRESS = cubic_bezier(0.36, 0.0, 0.24, 1.0)
EASE_LOWER = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def press_progress(frame):
    """Returns simultaneous bilateral overhead-press progress r in [0.0, 1.0] across 160 frames:
    - 0..12:   Bottom rack hold at shoulder goalpost position (r = 0.0)
    - 12..64:  Concentric overhead press drive (r: 0.0 -> 1.0: both arms extend overhead)
    - 64..84:  Top overhead lockout hold above crown of head (r = 1.0)
    - 84..148: Controlled eccentric lowering back to shoulder goalpost rack (r: 1.0 -> 0.0)
    - 148..160: Bottom rack hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 64:
        return EASE_PRESS((fr - 12) / 52.0)
    if fr <= 84:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_LOWER((fr - 84) / 64.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def seg_xform(p0, p1, base_len):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ang = math.atan2(dy, dx)
    sc = max(0.60, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute Simultaneous Bilateral Dumbbell Overhead Press transforms at progress r in [0.0, 1.0].

    Matches the 2-panel reference illustration:
      - At r = 0.0 (Goalpost Rack):
        * Near upper arm extends outward-right (+15 deg slightly below horizontal), forearm points
          nearly straight up (-95 deg) so the near dumbbell is held at (382.5, 94.2).
        * Far upper arm extends outward-left (+165 deg slightly below horizontal), forearm points
          nearly straight up (-85 deg) so the far dumbbell is held at (257.1, 91.6).
      - At r = 1.0 (Full Overhead Lockout):
        * Near upper arm rotates upward to -96 deg and forearm aligns to -102 deg, converging the
          near dumbbell to (336.5, 46.1) above the head.
        * Far upper arm rotates upward to -84 deg and forearm aligns to -78 deg, converging the
          far dumbbell to (298.8, 44.3) so the inner plates nearly meet above the crown of the head!
    """
    # 1. Near (Left / Screen-Right) Arm Overhead Press Arc (SHOULDER_NEAR = (348.0, 120.0)):
    ua_near_deg = lerp(14.0, -96.0, r)
    fa_near_deg = lerp(-95.0, -102.0, r)
    ua_near_rad = math.radians(ua_near_deg)
    fa_near_rad = math.radians(fa_near_deg)

    elbow_near = (
        SHOULDER_NEAR[0] + UPPER_ARM_LEN * math.cos(ua_near_rad),
        SHOULDER_NEAR[1] + UPPER_ARM_LEN * math.sin(ua_near_rad),
    )
    hand_near = (
        elbow_near[0] + FOREARM_LEN * math.cos(fa_near_rad),
        elbow_near[1] + FOREARM_LEN * math.sin(fa_near_rad),
    )
    ua_near_ang, ua_near_sc = seg_xform(SHOULDER_NEAR, elbow_near, UPPER_ARM_LEN)
    fa_near_ang, fa_near_sc = seg_xform(elbow_near, hand_near, FOREARM_LEN)
    delt_near_ang = math.radians(lerp(-35.0, -78.0, r))
    db_near_rot = math.radians(lerp(-5.0, -4.0, r))

    # 2. Far (Right / Screen-Left) Arm Overhead Press Arc (SHOULDER_FAR = (288.0, 118.2)):
    persp_x = 0.88
    ua_far_deg = lerp(166.0, 276.0, r)  # 166 deg (outward-left) -> 276 deg (-84 deg overhead)
    fa_far_deg = lerp(-85.0, -78.0, r)
    ua_far_rad = math.radians(ua_far_deg)
    fa_far_rad = math.radians(fa_far_deg)

    elbow_far = (
        SHOULDER_FAR[0] + UPPER_ARM_LEN * persp_x * math.cos(ua_far_rad),
        SHOULDER_FAR[1] + UPPER_ARM_LEN * math.sin(ua_far_rad),
    )
    hand_far = (
        elbow_far[0] + FOREARM_LEN * persp_x * math.cos(fa_far_rad),
        elbow_far[1] + FOREARM_LEN * math.sin(fa_far_rad),
    )
    ua_far_ang, ua_far_sc = seg_xform(SHOULDER_FAR, elbow_far, UPPER_ARM_LEN)
    fa_far_ang, fa_far_sc = seg_xform(elbow_far, hand_far, FOREARM_LEN)
    delt_far_ang = math.radians(lerp(32.0, 74.0, r))
    db_far_rot = math.radians(lerp(-5.0, -4.0, r))

    return {
        "r": r,
        "elbow_near": elbow_near,
        "hand_near": hand_near,
        "ua_near_ang": ua_near_ang,
        "ua_near_sc": ua_near_sc,
        "fa_near_ang": fa_near_ang,
        "fa_near_sc": fa_near_sc,
        "delt_near_ang": delt_near_ang,
        "db_near_rot": db_near_rot,
        "elbow_far": elbow_far,
        "hand_far": hand_far,
        "ua_far_ang": ua_far_ang,
        "ua_far_sc": ua_far_sc,
        "fa_far_ang": fa_far_ang,
        "fa_far_sc": fa_far_sc,
        "delt_far_ang": delt_far_ang,
        "db_far_rot": db_far_rot,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(press_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = (
    "ua_near_ang",
    "fa_near_ang",
    "delt_near_ang",
    "db_near_rot",
    "ua_far_ang",
    "fa_far_ang",
    "delt_far_ang",
    "db_far_rot",
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
    """Catmull-Rom -> CubicMirroredVertex list with organic curved contours."""
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


def polyline_stroke_shape(indent, name, pts, width, color, radius=0.2, cap="round"):
    vxml = "\n".join(
        f'{indent}        <StraightVertex x="{f(float(x))}" y="{f(float(y))}" radius="{f(float(radius))}"/>'
        for x, y in pts
    )
    return (
        f'{indent}<Shape name="{name}">\n'
        f'{indent}    <PointsPath isClosed="false" name="{name}Path">\n'
        f"{vxml}\n"
        f"{indent}    </PointsPath>\n"
        f'{indent}    <Stroke thickness="{f(float(width))}" cap="{cap}" join="round" name="{name}Stroke">'
        f'<SolidColor colorValue="{color}" name="{name}Color"/></Stroke>\n'
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


# ---------------------------------------------------------------- 1. Heavy 3D Double-Plate Black Dumbbell & Overhead Press Arm
def dumbbell_and_arm_rig(prefix, far):
    """Arm + Shoulder Cap (Lateral deltoid, Anterior deltoid) + Activated Triceps Brachii + 3D Double-Plate Black Dumbbell."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    sx, sy = SHOULDER_FAR if far else SHOULDER_NEAR
    ua_ang_k = "ua_far_ang" if far else "ua_near_ang"
    ua_sc_k = "ua_far_sc" if far else "ua_near_sc"
    el_k = "elbow_far" if far else "elbow_near"
    hand_k = "hand_far" if far else "hand_near"
    fa_ang_k = "fa_far_ang" if far else "fa_near_ang"
    fa_sc_k = "fa_far_sc" if far else "fa_near_sc"
    delt_ang_k = "delt_far_ang" if far else "delt_near_ang"
    db_rot_k = "db_far_rot" if far else "db_near_rot"

    ua_id, fa_id, delt_id, db_front_id, db_back_id = nid(), nid(), nid(), nid(), nid()
    key_double(ua_id, 15, lambda p: p[ua_ang_k])
    key_double(ua_id, 16, lambda p: p[ua_sc_k])

    key_double(fa_id, 13, lambda p: p[el_k][0])
    key_double(fa_id, 14, lambda p: p[el_k][1])
    key_double(fa_id, 15, lambda p: p[fa_ang_k])
    key_double(fa_id, 16, lambda p: p[fa_sc_k])

    key_double(delt_id, 15, lambda p: p[delt_ang_k])

    for db_id in (db_front_id, db_back_id):
        key_double(db_id, 13, lambda p: p[hand_k][0])
        key_double(db_id, 14, lambda p: p[hand_k][1])
        key_double(db_id, 15, lambda p: p[db_rot_k])

    p0 = POSES[0]

    # Target Muscle Activation Curves (matching the 4 labeled muscles in the reference image)
    def ant_delt_t(p):
        return 0.44 + 0.56 * (p["r"] ** 0.78)

    def lat_delt_t(p):
        return 0.42 + 0.58 * (p["r"] ** 0.80)

    def triceps_t(p):
        return 0.36 + 0.62 * (p["r"] ** 0.84)

    # 1. Sculpted Deltoid Cap at SHOULDER:
    if not far:
        delt_base_pts = [
            (-13.5, -3.2), (-6.0, -10.2), (4.8, -9.8), (12.8, -3.2),
            (13.8, 6.0), (8.5, 15.2), (-1.8, 16.2), (-10.8, 9.8),
        ]
        # Target Muscle #1: Anterior deltoid (front-left clavicular head of the deltoid)
        ant_delt_pts = [
            (-13.0, -3.2), (-5.5, -9.5), (2.0, -8.5), (0.8, 4.6), (-8.0, 11.2), (-12.4, 4.2),
        ]
        # Target Muscle #2: Lateral deltoid (broad multipennate middle head of the deltoid)
        lat_delt_pts = [
            (1.0, -8.8), (9.8, -6.2), (13.2, 2.8), (8.8, 14.6), (0.0, 15.6), (-2.2, 4.6),
        ]
    else:
        delt_base_pts = [
            (-15.0, -3.2), (-8.0, -9.8), (4.2, -8.8), (9.8, -1.4),
            (8.8, 8.4), (0.5, 12.6), (-11.6, 8.8),
        ]
        ant_delt_pts = [
            (-14.5, -3.2), (-7.5, -9.2), (2.8, -7.8), (1.8, 4.6), (-8.8, 8.8), (-13.5, 3.2),
        ]
        lat_delt_pts = [
            (-13.5, -4.6), (-5.2, -9.5), (6.0, -6.0), (8.8, 3.2), (2.2, 10.2), (-8.0, 7.8),
        ]

    # 2. Upper Arm & Forearm Contours (UPPER_ARM_LEN = 39.0, FOREARM_LEN = 36.0)
    ua_pts = [
        (-7, 0), (-5, 8.0), (7, 9.6), (20, 9.8), (31, 8.0), (36, 5.4),
        (41, 0), (36, -5.4), (26, -8.6), (13, -9.2), (2, -8.6), (-5, -6.8),
    ]
    # Target Muscle #3: Triceps Brachii (lateral & long head along the inferior/outer border of the upper arm
    # during overhead pressing: +Y side on the Near arm, -Y side on the Far arm)
    if not far:
        triceps_pts = [
            (6.0, 2.2), (18.5, 2.8), (30.5, 2.2), (36.5, 4.4),
            (31.0, 8.2), (19.0, 9.6), (7.5, 9.0),
        ]
        triceps_fiber = [(10.0, 5.8), (21.0, 6.6), (31.0, 5.5)]
    else:
        triceps_pts = [
            (6.0, -2.2), (18.5, -2.8), (30.5, -2.2), (36.5, -4.4),
            (31.0, -8.0), (19.0, -9.0), (7.5, -8.4),
        ]
        triceps_fiber = [(10.0, -5.6), (21.0, -6.2), (31.0, -5.2)]

    fa_pts = [
        (-4, 0), (-2, 6.2), (8, 7.5), (20, 6.2), (30, 4.4), (35, 3.4),
        (38, 0), (35, -3.4), (28, -4.4), (16, -6.0), (4, -6.6), (-2, -5.2),
    ]
    hand_pts = [
        (FOREARM_LEN - 4.5, -5.0), (FOREARM_LEN + 4.5, -4.8), (FOREARM_LEN + 6.5, 0.5),
        (FOREARM_LEN + 3.5, 5.2), (FOREARM_LEN - 4.5, 4.8),
    ]

    # 3. Heavy 3D Double-Plate Black Dumbbell (proportioned for overhead press)
    plate_face = (
        f'<Fill name="{prefix}PlateFaceFill">{grad3(prefix + "PlateFaceGrad", -18, 18, *PLATE_DARK, x0=-11, x1=11)}</Fill>'
        f'<Stroke thickness="1.15" name="{prefix}PlateFaceStroke"><SolidColor colorValue="FF475569" name="{prefix}PlateFaceStrokeCol"/></Stroke>'
    )
    plate_rim = (
        f'<Fill name="{prefix}PlateRimFill"><SolidColor colorValue="FF020617" name="{prefix}PlateRimCol"/></Fill>'
        f'<Stroke thickness="0.95" name="{prefix}PlateRimStroke"><SolidColor colorValue="FF1E293B" name="{prefix}PlateRimStrokeCol"/></Stroke>'
    )
    plate_groove = (
        f'<Stroke thickness="1.0" name="{prefix}PlateGrooveStroke"><SolidColor colorValue="FF334155" name="{prefix}PlateGrooveCol"/></Stroke>'
    )
    hub_paint = (
        f'<Fill name="{prefix}HubFill">{grad(prefix + "HubGrad", -4, -6, 4, 6, "FFE2E8F0", "FF475569")}</Fill>'
        f'<Stroke thickness="0.85" name="{prefix}HubStroke"><SolidColor colorValue="FF0F172A" name="{prefix}HubStrokeCol"/></Stroke>'
    )

    out = [f'{ind}<Node name="{prefix}ArmAndDumbbellGroup">']

    # Layer A (Foreground of Arm): Outer/Front Double Plates of Dumbbell (drawn in front of the gripping hand)
    out.append(
        f'{i2}<Node x="{f(p0[hand_k][0])}" y="{f(p0[hand_k][1])}" '
        f'rotation="{f(p0[db_rot_k])}" name="{prefix}DumbbellFrontPlates" id="{db_front_id}">'
    )
    out.append(ellipse_shape(i3, f"{prefix}FrontCollarHub", -13.5, 2.0, 6.0, 9.2, hub_paint))
    out.append(ellipse_shape(i3, f"{prefix}FrontOuterGroove", -11.2, 1.6, 15.0, 25.0, plate_groove))
    out.append(ellipse_shape(i3, f"{prefix}FrontOuterPlateFace", -11.2, 1.6, 21.0, 34.5, plate_face))
    out.append(ellipse_shape(i3, f"{prefix}FrontOuterPlateRim", -9.5, 1.4, 21.0, 34.5, plate_rim))
    out.append(ellipse_shape(i3, f"{prefix}FrontInnerPlateFace", -7.0, 1.0, 19.5, 32.5, plate_face))
    out.append(ellipse_shape(i3, f"{prefix}FrontInnerPlateRim", -5.4, 0.8, 19.5, 32.5, plate_rim))
    out.append(f"{i2}</Node>")

    # Layer B: Deltoid Cap at SHOULDER (Lateral deltoid + Anterior deltoid)
    out.append(
        f'{i2}<Node x="{f(sx)}" y="{f(sy)}" rotation="{f(p0[delt_ang_k])}" name="{prefix}DeltoidCap" id="{delt_id}">'
    )
    if not far:
        out.append(stroke_shape(i3, f"{prefix}DeltSplitLine", [(-1, -7.5), (0, 2.8), (-3, 10.5)], 1.15, "807F1D1D", 0.3))
        out.append(stroke_shape(i3, f"{prefix}AntDeltFiber", [(-8.0, -4.2), (-5.0, 5.5)], 1.0, "667F1D1D", 0.3))
        out.append(stroke_shape(i3, f"{prefix}LatDeltFiber1", [(4.2, -5.0), (6.0, 8.8)], 1.0, "667F1D1D", 0.3))
        out.append(stroke_shape(i3, f"{prefix}LatDeltFiber2", [(8.0, -2.2), (8.8, 9.8)], 0.95, "667F1D1D", 0.3))
        out.append(stroke_shape(i3, f"{prefix}LatDeltHi", [(3.8, -3.8), (8.0, 4.2)], 2.2, HIGHLIGHT, 2.0))
    out.append(smooth_shape(i3, f"{prefix}LateralDeltoid", lat_delt_pts, muscle_paint_fn(prefix + "LatDelt", lat_delt_t, 1.05)))
    out.append(smooth_shape(i3, f"{prefix}AnteriorDeltoid", ant_delt_pts, muscle_paint_fn(prefix + "AntDelt", ant_delt_t, 1.0)))
    out.append(smooth_shape(i3, f"{prefix}DeltoidBase", delt_base_pts, skin_fill(prefix + "DeltBase", -10, 16, skin)))
    out.append(f"{i2}</Node>")

    # Layer C: Forearm & Pronated Gripping Hand
    out.append(
        f'{i2}<Node x="{f(p0[el_k][0])}" y="{f(p0[el_k][1])}" '
        f'rotation="{f(p0[fa_ang_k])}" scaleX="{f(p0[fa_sc_k])}" name="{prefix}Forearm" id="{fa_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}Knuckle1", [(FOREARM_LEN - 2, -2.2), (FOREARM_LEN + 3.5, -2.2)], 0.95, SOFT_SHADOW, 0.0))
    out.append(stroke_shape(i3, f"{prefix}Knuckle2", [(FOREARM_LEN - 2, 1.2), (FOREARM_LEN + 3.5, 1.2)], 0.95, SOFT_SHADOW, 0.0))
    out.append(smooth_shape(i3, f"{prefix}GrippingHand", hand_pts, skin_fill(prefix + "Hand", -5, 5, skin)))
    hi_y = 2.8 if far else -2.8
    sh_y = -3.8 if far else 3.8
    out.append(stroke_shape(i3, f"{prefix}ForearmExtensorLine", [(7, 0.0), (20, 0.0), (30, 0.0)], 1.15, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(7, hi_y), (19, hi_y * 0.9), (29, hi_y * 0.65)], 2.2, HIGHLIGHT, 2.6))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(5, sh_y), (19, sh_y * 0.95), (29, sh_y * 0.7)], 3.2, CORE_SHADOW, 3.2))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -7, 8, skin)))
    out.append(f"{i2}</Node>")

    # Layer D: Upper Arm (SHOULDER -> ELBOW) with Activated Triceps Brachii
    out.append(
        f'{i2}<Node x="{f(sx)}" y="{f(sy)}" rotation="{f(p0[ua_ang_k])}" scaleX="{f(p0[ua_sc_k])}" name="{prefix}UpperArm" id="{ua_id}">'
    )
    ua_hi_y = 4.6 if far else -4.6
    ua_sh_y = -5.8 if far else 5.8
    out.append(stroke_shape(i3, f"{prefix}TricepsFiber", triceps_fiber, 1.0, "737F1D1D", 0.3))
    out.append(smooth_shape(i3, f"{prefix}TricepsBrachii", triceps_pts, muscle_paint_fn(prefix + "Triceps", triceps_t, 0.95)))
    out.append(stroke_shape(i3, f"{prefix}BicepsLine", [(11, 0.4), (23, 0.4), (33, 0.2)], 1.15, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}UpperArmHi", [(11, ua_hi_y), (23, ua_hi_y), (33, ua_hi_y * 0.8)], 2.4, HIGHLIGHT, 2.6))
    out.append(stroke_shape(i3, f"{prefix}UpperArmSh", [(10, ua_sh_y), (23, ua_sh_y), (33, ua_sh_y * 0.8)], 3.4, CORE_SHADOW, 3.5))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UpperArm", -9, 10, skin)))
    out.append(f"{i2}</Node>")

    # Layer E (Background of Arm): Inner/Back Double Plates & Chrome Handle Shaft (drawn behind the gripping hand)
    out.append(
        f'{i2}<Node x="{f(p0[hand_k][0])}" y="{f(p0[hand_k][1])}" '
        f'rotation="{f(p0[db_rot_k])}" name="{prefix}DumbbellBackPlates" id="{db_back_id}">'
    )
    out.append(polyline_stroke_shape(i3, f"{prefix}HandleHi", [(-8.5, 0.5), (8.5, -1.6)], 1.35, "FFFFFFFF", radius=0.4))
    out.append(polyline_stroke_shape(i3, f"{prefix}HandleShaft", [(-9.5, 1.4), (9.5, -1.4)], 4.5, "FF94A3B8", radius=0.8))
    out.append(ellipse_shape(i3, f"{prefix}BackInnerPlateFace", 7.2, -1.1, 19.0, 31.5, plate_face))
    out.append(ellipse_shape(i3, f"{prefix}BackInnerPlateRim", 8.8, -1.4, 19.0, 31.5, plate_rim))
    out.append(ellipse_shape(i3, f"{prefix}BackOuterGroove", 11.2, -1.7, 14.5, 24.0, plate_groove))
    out.append(ellipse_shape(i3, f"{prefix}BackOuterPlateFace", 11.2, -1.7, 20.5, 34.0, plate_face))
    out.append(ellipse_shape(i3, f"{prefix}BackOuterPlateRim", 12.8, -1.9, 20.5, 34.0, plate_rim))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 2. Canonical Standing 3/4 Athlete Body
def torso_and_head():
    """Standing 3/4 front-left torso, sculpted pectorals, activated Serratus Anterior,
    sculpted 6-pack abs, dark athletic compression shorts, and volumetric 3/4 head."""
    ind = "        "
    i2 = ind + "    "

    head_pts = pts_y([
        (304.0, 50.0), (301.5, 56.5), (300.0, 62.5), (301.2, 67.5),
        (301.8, 73.5), (307.5, 76.5), (316.5, 75.0), (323.5, 71.0),
        (328.5, 63.0), (328.0, 52.0), (321.0, 45.0), (311.0, 45.0),
    ])
    hair_pts = pts_y([
        (303.5, 52.0), (309.0, 44.5), (320.5, 44.2), (328.5, 50.5),
        (329.0, 61.5), (324.5, 65.5), (323.0, 57.5), (318.0, 52.5),
        (310.5, 51.0),
    ])
    head_hi = pts_y([(304.5, 54.0), (308.5, 49.0), (317.0, 48.0)])
    cheek_hi = pts_y([(303.5, 61.5), (309.5, 63.0), (315.0, 62.0)])
    jaw_sh = pts_y([(304.0, 75.5), (313.0, 76.2), (320.5, 72.5)])

    neck_pts = pts_y([
        (306.5, 73.0), (322.5, 70.0), (334.0, 86.0),
        (338.0, 94.0), (296.0, 92.0), (304.0, 83.0),
    ])
    scm_line = pts_y([(320.0, 72.5), (315.5, 82.0), (312.5, 90.5)])

    torso_pts = pts_y([
        (287.0, 91.0), (313.0, 88.5), (347.0, 93.0),
        (350.0, 113.0), (342.5, 134.0), (335.5, 154.0),
        (338.0, 174.0), (315.0, 182.0), (293.0, 174.0),
        (296.0, 152.0), (294.0, 132.0), (286.0, 111.0),
    ])
    torso_hi = pts_y([(299.0, 98.0), (301.0, 122.0), (303.0, 146.0)])
    torso_sh = pts_y([(340.0, 116.0), (334.5, 138.0), (330.5, 154.0)])

    # Sculpted Near (left) and Far (right) Pectoralis Major plates in hero 3/4 view
    pec_near_pts = pts_y([
        (313.5, 92.5), (339.5, 95.0), (345.5, 108.0),
        (339.5, 119.5), (325.0, 121.5), (313.0, 117.5),
    ])
    pec_far_pts = pts_y([
        (289.5, 93.0), (312.5, 92.5), (312.0, 117.0),
        (298.5, 119.0), (288.0, 112.0), (287.5, 100.5),
    ])
    pec_paint = (
        '<Fill name="PecFill"><SolidColor colorValue="120F172A" name="PecCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="PecStroke"><SolidColor colorValue="380F172A" name="PecStrokeCol"/></Stroke>'
    )

    # Target Muscle #4: Serratus anterior (3 prominent saw-toothed slips on the lateral ribcage below the outer pectoral)
    serratus_list = [
        pts_y([(327.0, 118.2), (344.0, 115.5), (344.5, 121.2), (326.5, 122.5)]),
        pts_y([(326.2, 123.5), (342.0, 121.8), (342.2, 126.8), (325.6, 127.5)]),
        pts_y([(325.4, 128.5), (339.8, 127.5), (339.5, 132.5), (324.8, 132.4)]),
    ]

    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1A0F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="AbsEdge"><SolidColor colorValue="400F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        pts_y([(313.0, 121.0), (325.0, 121.5), (325.5, 130.0), (312.8, 129.5)]),
        pts_y([(312.6, 131.5), (324.8, 132.0), (324.2, 140.5), (312.4, 140.0)]),
        pts_y([(312.2, 142.0), (323.5, 142.5), (322.0, 151.5), (312.0, 151.0)]),
        pts_y([(301.5, 121.0), (310.5, 121.0), (310.3, 129.5), (301.2, 129.0)]),
        pts_y([(301.2, 131.0), (310.2, 131.5), (310.0, 140.0), (301.2, 139.5)]),
        pts_y([(301.5, 141.5), (309.8, 142.0), (309.5, 151.0), (302.0, 150.5)]),
    ]

    pelvis_shorts = pts_y([
        (296.0, 153.0), (313.0, 155.0), (336.0, 154.0),
        (341.0, 176.0), (322.0, 186.0), (311.0, 184.0), (292.0, 176.0),
    ])

    out = [f'{ind}<Node name="TorsoAndHead">']

    # 1. Volumetric 3/4 Head
    _, h_y0 = pt_y((0, 44))
    _, h_y1 = pt_y((0, 77))
    _, ear_y = pt_y((0, 64.5))
    out.append(smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 304, h_y0, 329, pt_y((0, 65))[1], "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i2, "Ear", 321.5, ear_y, 5.2, 7.8, solid("Ear", "FFA3B1C4"), rot_deg=12.0))
    out.append(stroke_shape(i2, "BrowShade", pts_y([(301.5, 56.8), (306.0, 57.2)]), 1.4, "590F172A", 0.8))
    out.append(stroke_shape(i2, "EyeLine", pts_y([(303.2, 58.6), (306.2, 58.8)]), 1.1, "730F172A", 0.4))
    out.append(stroke_shape(i2, "MouthLine", pts_y([(301.5, 68.5), (305.0, 68.8)]), 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i2, "HeadHi", head_hi, 3.0, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i2, "CheekHi", cheek_hi, 2.2, "80FFFFFF", 2.5))
    out.append(stroke_shape(i2, "JawShadow", jaw_sh, 2.6, CORE_SHADOW, 2.5))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill("Head", h_y0, h_y1, SKIN, x0=300, x1=328)))

    # 2. Muscular Neck & Clavicles
    out.append(stroke_shape(i2, "UnderChinShadow", pts_y([(306.5, 76.5), (313.5, 77.5), (320.0, 74.5)]), 3.0, CORE_SHADOW, 2.5))
    out.append(stroke_shape(i2, "SCMLine", scm_line, 1.4, SOFT_SHADOW, 1.5))
    out.append(stroke_shape(i2, "ClavicleLine", pts_y([(296.0, 92.5), (312.5, 92.0), (336.0, 94.5)]), 1.4, SOFT_SHADOW, 1.2))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", pt_y((0, 70))[1], pt_y((0, 94))[1], SKIN)))

    # 3. Pelvis Shorts & Waistband
    out.append(stroke_shape(i2, "WaistbandLine", pts_y([(296.5, 155.5), (314.0, 157.5), (335.5, 156.5)]), 1.8, "660F172A", 0.8))
    out.append(stroke_shape(i2, "ShortsFlyLine", pts_y([(312.0, 157.5), (311.5, 176.0)]), 1.3, "660F172A", 0.8))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill("PelvisShorts", pt_y((0, 153))[1], pt_y((0, 186))[1], SHORTS)))

    # 4. Activated Serratus Anterior, 6-Pack Abs, Obliques & Sculpted Pectorals
    for idx, spts in enumerate(serratus_list):
        out.append(
            smooth_shape(
                i2,
                f"SerratusAnterior{idx + 1}",
                spts,
                muscle_paint_fn(f"Serratus{idx + 1}", lambda p: 0.38 + 0.56 * (p["r"] ** 0.82), 0.90),
            )
        )
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "LineaAlba", pts_y([(312.0, 118.0), (311.5, 136.0), (311.0, 153.0)]), 1.3, "470F172A", 0.8))
    out.append(stroke_shape(i2, "ObliqueLine1", pts_y([(336.0, 134.0), (330.0, 140.0), (326.0, 145.0)]), 1.3, "380F172A", 1.0))
    out.append(stroke_shape(i2, "ObliqueLine2", pts_y([(334.0, 142.0), (328.0, 148.0), (324.0, 152.0)]), 1.3, "380F172A", 1.0))

    out.append(stroke_shape(i2, "PecNearLowerSh", pts_y([(312.5, 118.0), (324.5, 122.0), (338.0, 119.5)]), 2.4, CORE_SHADOW, 2.0))
    out.append(stroke_shape(i2, "PecFarLowerSh", pts_y([(293.0, 113.0), (301.0, 119.5), (311.0, 117.5)]), 2.2, CORE_SHADOW, 2.0))
    out.append(stroke_shape(i2, "PecNearHi", pts_y([(316.0, 105.0), (328.0, 106.5), (337.0, 109.0)]), 2.6, HIGHLIGHT, 3.0))

    # Clavicular Anterior Deltoid caps on both upper chest/shoulder borders (prominent in both panels of reference image)
    far_clav_delt_pts = pts_y([
        (285.5, 95.5), (294.5, 91.5), (303.5, 92.8),
        (300.5, 99.5), (291.5, 103.5), (285.0, 100.5),
    ])
    near_clav_delt_pts = pts_y([
        (327.0, 93.5), (338.5, 93.0), (347.5, 96.5),
        (345.5, 103.5), (335.5, 103.0), (327.5, 98.5),
    ])
    out.append(
        smooth_shape(
            i2,
            "FarClavicularAnteriorDeltoid",
            far_clav_delt_pts,
            muscle_paint_fn("FarClavAntDelt", lambda p: 0.40 + 0.56 * (p["r"] ** 0.80), 0.95),
        )
    )
    out.append(
        smooth_shape(
            i2,
            "NearClavicularAnteriorDeltoid",
            near_clav_delt_pts,
            muscle_paint_fn("NearClavAntDelt", lambda p: 0.42 + 0.56 * (p["r"] ** 0.80), 0.95),
        )
    )
    out.append(smooth_shape(i2, "PecNear", pec_near_pts, pec_paint))
    out.append(smooth_shape(i2, "PecFar", pec_far_pts, pec_paint))

    # 5. Torso Base
    out.append(stroke_shape(i2, "TorsoHi", torso_hi, 4.5, HIGHLIGHT, 4.5))
    out.append(stroke_shape(i2, "TorsoSh", torso_sh, 6.0, CORE_SHADOW, 5.5))
    out.append(smooth_shape(i2, "Torso", torso_pts, skin_fill("Torso", pt_y((0, 89))[1], pt_y((0, 182))[1], SKIN, x0=294, x1=346)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def near_leg():
    """Near (left) leg planted on FLOOR=300 in 3/4 view."""
    ind = "        "
    i2 = ind + "    "

    shorts_pts = pts_y([
        (313.0, 168.0), (339.5, 166.0), (344.5, 192.0),
        (315.5, 194.0), (312.0, 178.0),
    ])
    thigh_pts = pts_y([
        (315.0, 174.0), (340.0, 172.0), (346.5, 196.0),
        (343.0, 218.0), (338.0, 232.0), (322.0, 232.0),
        (317.5, 214.0), (314.5, 194.0),
    ])
    thigh_hi = pts_y([(324.0, 192.0), (325.0, 210.0), (326.0, 224.0)])
    thigh_sh = pts_y([(341.0, 192.0), (340.0, 212.0), (336.0, 228.0)])
    quad_med_line = pts_y([(324.0, 200.0), (321.0, 214.0), (324.0, 225.0)])
    quad_lat_line = pts_y([(335.0, 194.0), (336.5, 212.0), (333.5, 226.0)])

    shin_pts = pts_y([
        (322.5, 230.0), (338.0, 230.0), (346.5, 248.0),
        (345.0, 266.0), (339.5, 288.0), (328.5, 289.0),
        (325.0, 268.0), (322.0, 248.0),
    ])
    shin_hi = pts_y([(327.0, 240.0), (328.5, 262.0), (330.0, 282.0)])
    shin_sh = pts_y([(342.0, 246.0), (341.5, 264.0), (337.5, 284.0)])
    calf_cut = pts_y([(334.0, 246.0), (338.5, 258.0), (335.5, 270.0)])

    foot_pts = pts_y([
        (328.5, 286.0), (340.0, 286.0), (343.5, 297.5),
        (334.0, 300.5), (314.0, 301.5), (309.5, 297.5),
        (316.0, 292.5),
    ])

    return "\n".join([
        f'{ind}<Node name="NearLeg">',
        stroke_shape(i2, "NearShortsHem", pts_y([(315.5, 192.5), (329.5, 193.0), (344.0, 190.5)]), 1.6, "660F172A", 0.6),
        smooth_shape(i2, "NearThighShorts", shorts_pts, skin_fill("NearThighShorts", pt_y((0, 166))[1], pt_y((0, 194))[1], SHORTS)),
        stroke_shape(i2, "NearQuadMedLine", quad_med_line, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearQuadLatLine", quad_lat_line, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearThighHi", thigh_hi, 4.0, HIGHLIGHT, 4.0),
        stroke_shape(i2, "NearThighSh", thigh_sh, 5.2, CORE_SHADOW, 5.0),
        smooth_shape(i2, "NearThigh", thigh_pts, skin_fill("NearThigh", pt_y((0, 172))[1], pt_y((0, 232))[1], SKIN)),
        ellipse_shape(i2, "NearKnee", 329.5, pt_y((0, 231.0))[1], 16.0, 14.0, skin_fill("NearKnee", -7, 7, SKIN)),
        stroke_shape(i2, "NearFootHi", pts_y([(329.0, 290.0), (319.0, 295.0), (312.5, 298.0)]), 2.2, HIGHLIGHT, 2.5),
        smooth_shape(i2, "NearFoot", foot_pts, skin_fill("NearFoot", pt_y((0, 286))[1], pt_y((0, 302))[1], SKIN)),
        stroke_shape(i2, "NearCalfCut", calf_cut, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearShinHi", shin_hi, 3.2, HIGHLIGHT, 3.5),
        stroke_shape(i2, "NearShinSh", shin_sh, 4.5, CORE_SHADOW, 4.5),
        smooth_shape(i2, "NearShin", shin_pts, skin_fill("NearShin", pt_y((0, 230))[1], pt_y((0, 289))[1], SKIN)),
        f"{ind}</Node>",
    ])


def far_leg():
    """Far (right) leg planted slightly further back-left in 3/4 perspective."""
    ind = "        "
    i2 = ind + "    "

    shorts_pts = pts_y([
        (292.0, 166.0), (315.0, 168.0), (314.0, 190.0),
        (289.5, 188.0),
    ])
    thigh_pts = pts_y([
        (291.0, 172.0), (314.0, 174.0), (313.0, 198.0),
        (309.5, 224.0), (294.5, 224.0), (289.5, 204.0),
        (288.0, 186.0),
    ])
    thigh_hi = pts_y([(294.5, 188.0), (295.5, 206.0), (297.0, 220.0)])
    thigh_sh = pts_y([(309.0, 190.0), (308.0, 208.0), (306.0, 222.0)])
    quad_line = pts_y([(302.5, 192.0), (303.5, 208.0), (301.5, 220.0)])

    shin_pts = pts_y([
        (295.0, 222.0), (309.5, 222.0), (316.0, 242.0),
        (314.5, 260.0), (309.5, 281.0), (299.0, 282.0),
        (296.5, 260.0), (294.5, 242.0),
    ])
    shin_hi = pts_y([(298.5, 232.0), (299.5, 254.0), (301.0, 274.0)])
    shin_sh = pts_y([(312.0, 240.0), (311.0, 258.0), (307.5, 276.0)])

    foot_pts = pts_y([
        (299.0, 279.0), (310.0, 279.0), (313.0, 289.5),
        (303.0, 292.5), (284.0, 293.5), (279.5, 289.5),
        (286.5, 285.0),
    ])

    return "\n".join([
        f'{ind}<Node name="FarLeg">',
        smooth_shape(i2, "FarThighShorts", shorts_pts, skin_fill("FarThighShorts", pt_y((0, 166))[1], pt_y((0, 190))[1], SHORTS_FAR)),
        stroke_shape(i2, "FarQuadLine", quad_line, 1.2, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "FarThighHi", thigh_hi, 3.4, HIGHLIGHT, 3.5),
        stroke_shape(i2, "FarThighSh", thigh_sh, 4.6, CORE_SHADOW, 4.5),
        smooth_shape(i2, "FarThigh", thigh_pts, skin_fill("FarThigh", pt_y((0, 172))[1], pt_y((0, 224))[1], SKIN_FAR)),
        ellipse_shape(i2, "FarKnee", 301.5, pt_y((0, 223.5))[1], 15.0, 13.5, skin_fill("FarKnee", -7, 7, SKIN_FAR)),
        smooth_shape(i2, "FarFoot", foot_pts, skin_fill("FarFoot", pt_y((0, 279))[1], pt_y((0, 294))[1], SKIN_FAR)),
        stroke_shape(i2, "FarShinHi", shin_hi, 2.8, HIGHLIGHT, 3.0),
        stroke_shape(i2, "FarShinSh", shin_sh, 4.0, CORE_SHADOW, 4.0),
        smooth_shape(i2, "FarShin", shin_pts, skin_fill("FarShin", pt_y((0, 222))[1], pt_y((0, 282))[1], SKIN_FAR)),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 3. Scene Assembly (RML First Child = Topmost Layer)
def build_rml():
    global _id
    _id = 0
    KEYED.clear()

    near_arm_xml = dumbbell_and_arm_rig("Near", False)
    torso_head_xml = torso_and_head()
    near_leg_xml = near_leg()
    far_leg_xml = far_leg()
    far_arm_xml = dumbbell_and_arm_rig("Far", True)

    grouped = {}
    for oid, kxml in KEYED:
        grouped.setdefault(oid, []).append(kxml)
    keyed_objects_xml = "\n".join(
        f'        <KeyedObject objectId="{oid}">\n' + "\n".join(props) + "\n        </KeyedObject>"
        for oid, props in grouped.items()
    )

    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"

    return f"""<Rive version="7.3">
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="OverheadPress" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Left) Arm, Near Deltoid Cap, Activated Triceps Brachii & Near Black Dumbbell -->
{near_arm_xml}

        <!-- 2. Standing 3/4 Athlete Torso, Serratus Anterior, Sculpted Pectorals, 6-Pack Abs & Volumetric Head -->
{torso_head_xml}

        <!-- 3. Near (Left) Standing Leg on Floor -->
{near_leg_xml}

        <!-- 4. Far (Right) Standing Leg in 3/4 Depth -->
{far_leg_xml}

        <!-- 5. Background: Far (Right) Arm, Far Deltoid Cap, Activated Triceps Brachii & Far Black Dumbbell -->
{far_arm_xml}

        <!-- 6. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="314" y="{f(FLOOR - 2)}" scaleX="0.86" scaleY="0.09" name="BodyShadow">
            <Ellipse width="190" height="190" name="BodyShadowEllipse"/>
            <Fill name="BodyShadowFill"><RadialGradient startX="0" startY="0" endX="95" endY="0" name="BodyShadowGrad">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="OverheadPress" id="0:60">
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
    (BUILD / "overhead_press.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (38, "frame_mid"), (72, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(680, 14, 300))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
