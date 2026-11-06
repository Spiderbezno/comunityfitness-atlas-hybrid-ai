#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360, FLOOR = 300.0) procedural Rive 7.3 scene for Russian Twist (id: 'russian_twist').

Uses our canonical 3/4 front-right CommunityFitness mannequin seated on a beveled studio exercise mat in a V-sit
posture (pelvis/glutes resting on the mat at FLOOR = 300.0, torso reclined back ~45 deg, knees flexed with bare
feet elevated off the floor):
  - At r = 0.0 (Near / Right Hip Rotation):
    * Torso, shoulders, head, and clasped hands holding a sculpted dark cast-iron weight plate / medicine ball
      rotate toward the near right hip (`(282, 248)`), while the elevated V-sit legs counter-stabilize.
  - At r = 1.0 (Far / Left Hip Rotation):
    * Torso, shoulders, and hands sweep across the abdominal midline in a smooth arc to the far left hip (`(334, 188)`),
      showcasing dynamic rotational core contraction across the obliques and 6-pack rectus abdominis.
  - Highlighted Target Muscle Groups (pulsing from warm orange #FFF97316 to intense crimson #FFF43F5E):
    1. External & Internal obliques (Primary rotational core movers)
    2. Rectus abdominis (6-pack abdominal wall with tendinous inscriptions)
    3. Hip flexors / Rectus femoris (V-sit leg elevation & counter-stabilization)

Run:
    python3 rive_animations/russian_twist/gen_russian_twist.py            # writes scene.rml
    python3 rive_animations/russian_twist/gen_russian_twist.py --publish  # compiles .riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/russian_twist.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/russian_twist.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps rotational V-sit loop
STEP = 2

UPPER_ARM_LEN = 42.0
FOREARM_LEN = 38.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
PLATE_DARK = ("FF334155", "FF1E293B", "FF090D16")
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


EASE_TWIST = cubic_bezier(0.38, 0.0, 0.26, 1.0)
EASE_RETURN = cubic_bezier(0.40, 0.0, 0.34, 1.0)


def twist_progress(frame):
    """Returns rotational twist progress r in [0.0, 1.0] across 160 frames:
    - 0..12:   Near/Right hip rotation hold (r = 0.0)
    - 12..68:  Concentric cross-body sweep over midline to Far/Left hip (r: 0.0 -> 1.0)
    - 68..88:  Far/Left hip peak rotational hold (r = 1.0)
    - 88..148: Controlled rotational sweep back to Near/Right hip (r: 1.0 -> 0.0)
    - 148..160: Near/Right hip hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 68:
        return EASE_TWIST((fr - 12) / 56.0)
    if fr <= 88:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_RETURN((fr - 88) / 60.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def quad_interp_pt(p0, p_mid, p1, r):
    """Smooth quadratic Lagrange interpolation through p0 (r=0), p_mid (r=0.5), and p1 (r=1.0)."""
    l0 = (1.0 - r) * (1.0 - 2.0 * r)
    l1 = 4.0 * r * (1.0 - r)
    l2 = r * (2.0 * r - 1.0)
    return (
        l0 * p0[0] + l1 * p_mid[0] + l2 * p1[0],
        l0 * p0[1] + l1 * p_mid[1] + l2 * p1[1],
    )


def seg_xform(p0, p1, base_len):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ang = math.atan2(dy, dx)
    if ang < 0:
        ang += 2.0 * math.pi
    sc = max(0.40, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute 3/4 V-Sit Russian Twist kinematics at progress r in [0.0, 1.0]."""
    # 1. Axial Torso Twist & Ribcage Shift (pivoting around the lumbar/pelvic anchor at (306, 266)):
    #    At r = 0.0 (turned toward Near/Right hip): torso leans slightly down-left (+3.5 deg), chest faces viewer
    #    At r = 1.0 (turned toward Far/Left hip): torso rotates across midline (-4.5 deg), ribcage shifts +8 px right
    torso_rot = math.radians(lerp(3.5, -4.5, r))
    torso_dx = lerp(-3.0, 6.0, r)
    torso_dy = lerp(2.0, -3.0, r)

    # Core abdominal & oblique group shifts & shears slightly across the torso midline to sell 3D axial twist
    core_dx = lerp(-4.0, 7.0, r)
    core_dy = lerp(2.0, -3.5, r)
    core_rot = math.radians(lerp(4.0, -5.0, r))
    core_sx = lerp(1.04, 0.94, r)

    # Head tracks the upper torso rotation smoothly
    head_rot = math.radians(lerp(5.0, -6.0, r))
    head_dx = lerp(-3.0, 5.0, r)

    # 2. Elevated V-Sit Legs Counter-Stabilization (pivoting around pelvis (308, 268)):
    #    As torso twists from near-right (r=0) to far-left (r=1), elevated knees & feet counter-stabilize
    leg_near_rot = math.radians(lerp(2.8, -2.8, r))
    leg_far_rot = math.radians(lerp(-2.2, 2.5, r))

    # 3. Sculpted Weight Plate / Medicine Ball Arc Across the Midline:
    #    - r = 0.0 (Near/Right Hip): lowered beside the near right hip at (280.0, 246.0)
    #    - r = 0.5 (Midline Crest): lifted in an arc over the 6-pack abs at (308.0, 198.0)
    #    - r = 1.0 (Far/Left Hip): swept across the midline to the far left hip/flank at (332.0, 188.0)
    weight_center = quad_interp_pt((280.0, 246.0), (308.0, 198.0), (332.0, 188.0), r)
    weight_rot = math.radians(lerp(24.0, -28.0, r))

    # 4. Near (Right) & Far (Left) Shoulders, Elbows, and Hands Gripping the Weight:
    sh_near = quad_interp_pt((234.0, 196.0), (244.0, 188.0), (258.0, 182.0), r)
    elb_near = quad_interp_pt((236.0, 242.0), (266.0, 224.0), (298.0, 214.0), r)
    hand_near = (weight_center[0] - 8.0, weight_center[1] + 5.0)

    sh_far = quad_interp_pt((272.0, 174.0), (270.0, 170.0), (264.0, 168.0), r)
    elb_far = quad_interp_pt((286.0, 214.0), (308.0, 184.0), (324.0, 162.0), r)
    hand_far = (weight_center[0] + 8.0, weight_center[1] - 5.0)

    ua_near_ang, ua_near_sc = seg_xform(sh_near, elb_near, UPPER_ARM_LEN)
    fa_near_ang, fa_near_sc = seg_xform(elb_near, hand_near, FOREARM_LEN)
    ua_far_ang, ua_far_sc = seg_xform(sh_far, elb_far, UPPER_ARM_LEN)
    fa_far_ang, fa_far_sc = seg_xform(elb_far, hand_far, FOREARM_LEN)

    delt_near_ang = math.radians(lerp(18.0, -22.0, r))
    delt_far_ang = math.radians(lerp(8.0, -28.0, r))

    return {
        "r": r,
        "torso_rot": torso_rot,
        "torso_dx": torso_dx,
        "torso_dy": torso_dy,
        "core_dx": core_dx,
        "core_dy": core_dy,
        "core_rot": core_rot,
        "core_sx": core_sx,
        "head_rot": head_rot,
        "head_dx": head_dx,
        "leg_near_rot": leg_near_rot,
        "leg_far_rot": leg_far_rot,
        "weight_center": weight_center,
        "weight_rot": weight_rot,
        "sh_near": sh_near,
        "elb_near": elb_near,
        "hand_near": hand_near,
        "ua_near_ang": ua_near_ang,
        "ua_near_sc": ua_near_sc,
        "fa_near_ang": fa_near_ang,
        "fa_near_sc": fa_near_sc,
        "delt_near_ang": delt_near_ang,
        "sh_far": sh_far,
        "elb_far": elb_far,
        "hand_far": hand_far,
        "ua_far_ang": ua_far_ang,
        "ua_far_sc": ua_far_sc,
        "fa_far_ang": fa_far_ang,
        "fa_far_sc": fa_far_sc,
        "delt_far_ang": delt_far_ang,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(twist_progress(fr)) for fr in FRAMES}

_ANGLE_KEYS = (
    "torso_rot",
    "core_rot",
    "head_rot",
    "leg_near_rot",
    "leg_far_rot",
    "weight_rot",
    "ua_near_ang",
    "fa_near_ang",
    "delt_near_ang",
    "ua_far_ang",
    "fa_far_ang",
    "delt_far_ang",
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


def skin_fill_outlined(name, y0, y1, tones, x0=0, x1=0, line=1.1, stroke_col="4D0F172A"):
    return (
        f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *tones, x0=x0, x1=x1)}</Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{stroke_col}" name="{name}EdgeCol"/></Stroke>'
    )


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


def poly_shape(indent, name, pts, paint_xml, radius=2.0):
    vxml = "\n".join(
        f'{indent}        <StraightVertex x="{f(float(x))}" y="{f(float(y))}" radius="{f(float(radius))}"/>'
        for x, y in pts
    )
    return (
        f'{indent}<Shape name="{name}">\n'
        f'{indent}    <PointsPath isClosed="true" name="{name}Path">\n'
        f"{vxml}\n"
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


def muscle_paint_fn(name, fn_t, line=1.05):
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


# ---------------------------------------------------------------- 1. Elevated V-Sit Legs & Stationary Pelvis on Mat
def build_vsit_legs_and_pelvis():
    """Returns (far_leg_xml, near_leg_and_pelvis_xml) for the elevated V-sit posture:
    - Ischial tuberosities/glutes in dark compression shorts resting on the studio mat at (308, 274..294)
    - Thighs angled upward-right (~42 deg) with glowing Rectus Femoris / Hip Flexors
    - Knees flexed (~85 deg) at ~(384, 196) with shins & bare feet hovering elevated off the floor at y ~ 248..264!
    """
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    far_leg_id, near_leg_id = nid(), nid()
    key_double(far_leg_id, 15, lambda p: p["leg_far_rot"])
    key_double(near_leg_id, 15, lambda p: p["leg_near_rot"])
    p0 = POSES[0]

    def hip_flexor_t(p):
        return 0.40 + 0.56 * (p["r"] ** 0.80)

    # Pivot at Pelvis Hip Center (312.0, 266.0)
    # Local coordinates relative to (312.0, 266.0):
    # Far (Left) Leg slightly higher/left in 3/4 depth:
    far_shorts_pts = [
        (-8, -26), (22, -46), (44, -62), (56, -40), (30, -14), (2, 8), (-12, 2),
    ]
    far_thigh_pts = [
        (26, -48), (50, -68), (66, -78), (78, -72),
        (72, -52), (48, -28), (28, -14),
    ]
    far_rectus_pts = [
        (22, -44), (46, -64), (64, -74), (68, -64), (46, -46), (26, -32),
    ]
    far_shin_pts = [
        (64, -74), (78, -76), (92, -62), (108, -36), (120, -18),
        (108, -12), (92, -26), (76, -44), (66, -60),
    ]
    far_foot_pts = [
        (114, -22), (126, -24), (142, -16), (150, -12), (148, -6),
        (132, -6), (112, -10), (108, -16),
    ]

    # Near (Right) Foreground Leg:
    near_shorts_pts = [
        (-18, -22), (14, -34), (48, -56), (64, -32),
        (38, -4), (16, 20), (-6, 26), (-22, 22), (-22, 0),
    ]
    near_thigh_pts = [
        (32, -44), (56, -64), (74, -72), (86, -66),
        (80, -44), (58, -20), (36, -8),
    ]
    # Highlighted Target Muscle #3: Hip Flexors / Rectus Femoris along the anterior thigh crest
    near_rectus_pts = [
        (24, -38), (50, -58), (70, -68), (76, -58), (54, -40), (30, -24),
    ]
    near_shin_pts = [
        (72, -68), (86, -70), (100, -56), (116, -30), (128, -10),
        (116, -4), (100, -18), (84, -38), (74, -54),
    ]
    # Bare right foot hovering cleanly in the air at world y ~ 256..264 (36 px above FLOOR = 300.0!)
    near_foot_pts = [
        (122, -14), (134, -16), (150, -8), (160, -4), (158, 3),
        (140, 3), (120, -2), (116, -8),
    ]

    far_xml = "\n".join([
        f'{ind}<Node x="312" y="266" rotation="{f(p0["leg_far_rot"])}" name="FarVSitLeg" id="{far_leg_id}">',
        smooth_shape(i2, "FarFoot", far_foot_pts, skin_fill_outlined("FarFoot", -24, -6, SKIN_FAR)),
        smooth_shape(i2, "FarShin", far_shin_pts, skin_fill_outlined("FarShin", -76, -12, SKIN_FAR)),
        ellipse_shape(i2, "FarKneeCap", 72, -70, 14, 13, skin_fill_outlined("FarKnee", -7, 7, SKIN_FAR)),
        smooth_shape(i2, "FarRectusFemoris", far_rectus_pts, muscle_paint_fn("FarRectusFem", hip_flexor_t, 0.95)),
        smooth_shape(i2, "FarThigh", far_thigh_pts, skin_fill_outlined("FarThigh", -78, -14, SKIN_FAR)),
        smooth_shape(i2, "FarShorts", far_shorts_pts, skin_fill("FarShorts", -62, 8, SHORTS_FAR)),
        f"{ind}</Node>",
    ])

    near_xml = "\n".join([
        f'{ind}<Node x="312" y="266" rotation="{f(p0["leg_near_rot"])}" name="NearVSitLegAndPelvis" id="{near_leg_id}">',
        # 1. Elevated Bare Right Foot
        stroke_shape(i2, "NearAnkleBone", [(124, -13), (126, -7), (131, -5)], 1.3, SOFT_SHADOW, 0.2),
        stroke_shape(i2, "NearFootHi", [(132, -13), (146, -7), (156, -3)], 2.0, HIGHLIGHT, 2.0),
        smooth_shape(i2, "NearFoot", near_foot_pts, skin_fill_outlined("NearFoot", -16, 4, SKIN, line=1.15)),
        # 2. Elevated Right Shin & Gastrocnemius Calf
        stroke_shape(i2, "NearTibialisLine", [(88, -54), (104, -34), (118, -14)], 1.3, SOFT_SHADOW, 0.4),
        stroke_shape(i2, "NearShinHi", [(88, -60), (104, -38), (120, -14)], 2.8, HIGHLIGHT, 2.8),
        stroke_shape(i2, "NearCalfSh", [(82, -42), (98, -22), (114, -8)], 3.6, CORE_SHADOW, 3.5),
        smooth_shape(i2, "NearShin", near_shin_pts, skin_fill_outlined("NearShin", -70, -4, SKIN, line=1.15)),
        # 3. Right Thigh, Patella & Glowing Rectus Femoris / Hip Flexor
        ellipse_shape(i2, "NearKneeCap", 80, -64, 15, 14, skin_fill_outlined("NearKnee", -7, 7, SKIN, line=1.0)),
        stroke_shape(i2, "NearQuadHi", [(34, -42), (54, -56), (70, -64)], 2.4, "80FFFFFF", 2.0),
        smooth_shape(i2, "NearRectusFemoris", near_rectus_pts, muscle_paint_fn("NearRectusFem", hip_flexor_t, 1.05)),
        stroke_shape(i2, "NearHamstringSh", [(42, -14), (60, -26), (76, -42)], 3.8, CORE_SHADOW, 3.6),
        smooth_shape(i2, "NearThigh", near_thigh_pts, skin_fill_outlined("NearThigh", -72, -8, SKIN, line=1.15)),
        # 4. Dark Athletic Compression Shorts Seated on Studio Mat
        stroke_shape(i2, "ShortsHemSeam", [(46, -54), (56, -42), (62, -32)], 1.5, "99090D16", 0.4),
        stroke_shape(i2, "ShortsHipCrease", [(-6, -18), (18, -32), (42, -48)], 1.4, "80090D16", 0.5),
        stroke_shape(i2, "ShortsGluteSh", [(-18, 18), (0, 22), (18, 14)], 4.0, CORE_SHADOW, 3.8),
        smooth_shape(i2, "NearShorts", near_shorts_pts, skin_fill_outlined("NearShorts", -56, 26, SHORTS, line=1.2, stroke_col="80090D16")),
        f"{ind}</Node>",
    ])

    return far_xml, near_xml


# ---------------------------------------------------------------- 2. V-Sit Reclined Torso, Glowing Obliques & 6-Pack Abs, and 3/4 Head
def build_vsit_torso_and_head():
    """Reclined V-sit torso (~45 deg back-left from pelvis `(304, 266)` up to shoulders `(252, 184)` and head `(232, 140)`):
    - Dynamic axial twist (`torso_rot`, `torso_dx`, `torso_dy`)
    - Glowing External & Internal Obliques on both flanks + 6-pack Rectus Abdominis blocks
    - Canonical 3/4 Volumetric Head with dark hair cap, ear, brow, eye, nose, and jaw."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    torso_id, core_id, head_id = nid(), nid(), nid()
    key_double(torso_id, 13, lambda p: 304.0 + p["torso_dx"])
    key_double(torso_id, 14, lambda p: 266.0 + p["torso_dy"])
    key_double(torso_id, 15, lambda p: p["torso_rot"])

    key_double(core_id, 13, lambda p: p["core_dx"])
    key_double(core_id, 14, lambda p: p["core_dy"])
    key_double(core_id, 15, lambda p: p["core_rot"])
    key_double(core_id, 16, lambda p: p["core_sx"])

    key_double(head_id, 13, lambda p: -58.0 + p["head_dx"])
    key_double(head_id, 15, lambda p: p["head_rot"])

    p0 = POSES[0]

    def oblique_t(p):
        return 0.46 + 0.54 * (p["r"] ** 0.75)

    def rectus_t(p):
        return 0.44 + 0.56 * (p["r"] ** 0.78)

    # Local coordinates relative to Lumbar/Pelvic Pivot (304.0, 266.0):
    # Shoulders are around (-52, -82), Neck at (-58, -94), Head at (-66, -124)
    torso_pts = [
        (-68, -74),  # near-right shoulder / deltopectoral border
        (-54, -92),  # clavicular notch / neck base
        (-30, -90),  # far-left upper shoulder / acromion
        (-12, -66),  # far-left chest / serratus border
        (2, -36),    # far-left waist / external oblique flank
        (10, -14),   # far-left iliac crest at shorts waistband
        (-4, 10),    # lower lumbar / sacral base inside shorts
        (-24, 8),    # near-right posterior hip / lumbar curve
        (-44, -16),  # near-right lower lat / external oblique flank
        (-62, -46),  # near-right mid-thoracic ribcage
    ]

    # Sculpted Pectoralis Major Plates (Near Right & Far Left) at upper chest
    pec_near_pts = [
        (-62, -74), (-46, -86), (-30, -76), (-32, -58), (-48, -54), (-62, -60),
    ]
    pec_far_pts = [
        (-44, -86), (-28, -88), (-16, -74), (-20, -60), (-32, -58),
    ]
    pec_paint = (
        f'<Fill name="PecFill">{grad3("PecGrad", -88, -54, "FFF8FAFC", "FFDCE4EE", "FFA3B1C4")}</Fill>'
        '<Stroke thickness="1.15" join="round" name="PecStroke"><SolidColor colorValue="4D0F172A" name="PecStrokeCol"/></Stroke>'
    )

    # Highlighted Core Muscle Group (Relative to Torso Origin):
    # 1. Near (Right) External & Internal Oblique Flank Wall (along lower-left border of torso)
    oblique_near_pts = [
        (-52, -52), (-36, -50), (-22, -32), (-12, -10),
        (-22, 2), (-38, -12), (-50, -34),
    ]
    # 2. Far (Left) External & Internal Oblique Flank Wall (along upper-right border of waist)
    oblique_far_pts = [
        (-18, -62), (-8, -54), (2, -32), (8, -14),
        (-2, -8), (-12, -26), (-20, -46),
    ]
    # 3. Sculpted 6-Pack Rectus Abdominis Blocks (3 Near-Right + 3 Far-Left segments down the inclined belly)
    rectus_blocks = [
        # Near-right column of 6-pack
        [(-42, -54), (-29, -58), (-23, -45), (-36, -41)],
        [(-35, -39), (-22, -43), (-16, -30), (-29, -26)],
        [(-28, -24), (-15, -28), (-9, -14), (-22, -10)],
        # Far-left column of 6-pack
        [(-27, -59), (-15, -62), (-9, -49), (-21, -46)],
        [(-20, -44), (-8, -47), (-2, -34), (-14, -31)],
        [(-13, -29), (-1, -32), (5, -18), (-7, -15)],
    ]

    # Canonical 3/4 Volumetric Head & Neck (anchored at (-58, -90) in Torso space)
    neck_pts = [
        (-10, -14), (8, -16), (16, 4), (-4, 10), (-12, -2),
    ]
    head_pts = [
        (-14, -12),  # back of skull / occiput
        (-22, -26),  # posterior crown
        (-18, -42),  # upper cranial dome
        (-6, -48),   # anterior hairline / forehead top
        (8, -44),    # brow ridge (facing 3/4 right!)
        (11, -36),   # orbital / nose bridge
        (16, -28),   # sculpted nose tip projecting right-down
        (11, -21),   # upper/lower lips
        (10, -13),   # strong chin tip
        (-1, -9),    # mandible / jawline
        (-10, -10),  # mastoid / nape
    ]
    hair_pts = [
        (-4, -48), (8, -44), (2, -39), (-6, -36),
        (-12, -26), (-14, -14), (-22, -20), (-24, -34), (-16, -46),
    ]
    hair_paint = (
        f'<Fill name="HairFill">{grad("HairGrad", -24, -48, 8, -14, "FF334155", "FF0F172A")}</Fill>'
        '<Stroke thickness="1.05" join="round" name="HairStroke"><SolidColor colorValue="FF090D16" name="HairStrokeCol"/></Stroke>'
    )

    out = [
        f'{ind}<Node x="{f(304.0 + p0["torso_dx"])}" y="{f(266.0 + p0["torso_dy"])}" '
        f'rotation="{f(p0["torso_rot"])}" name="VSitTorsoAndHead" id="{torso_id}">'
    ]

    # 1. Dynamic Rotational Core Muscle Group (Obliques + 6-Pack Rectus Abdominis drawn on top of Torso skin)
    out.append(
        f'{i2}<Node x="{f(p0["core_dx"])}" y="{f(p0["core_dy"])}" '
        f'rotation="{f(p0["core_rot"])}" scaleX="{f(p0["core_sx"])}" name="RotationalCoreGroup" id="{core_id}">'
    )
    out.append(stroke_shape(i3, "LineaAlba", [(-28, -58), (-20, -40), (-10, -14)], 1.3, "8C7F1D1D", 0.3))
    for idx, bpts in enumerate(rectus_blocks):
        out.append(smooth_shape(i3, f"RectusBlock{idx + 1}", bpts, muscle_paint_fn(f"Rectus{idx + 1}", rectus_t, 1.05)))
    out.append(stroke_shape(i3, "ObliqueNearSlip1", [(-46, -40), (-32, -30), (-20, -18)], 1.1, "737F1D1D", 0.3))
    out.append(stroke_shape(i3, "ObliqueNearSlip2", [(-42, -26), (-28, -16), (-18, -6)], 1.1, "737F1D1D", 0.3))
    out.append(smooth_shape(i3, "ExternalObliqueNear", oblique_near_pts, muscle_paint_fn("ObliqueNear", oblique_t, 1.1)))
    out.append(smooth_shape(i3, "ExternalObliqueFar", oblique_far_pts, muscle_paint_fn("ObliqueFar", oblique_t, 1.0)))
    out.append(f"{i2}</Node>")

    # 2. Sculpted Pectoralis Major Chest Plates
    out.append(stroke_shape(i2, "PecHi", [(-56, -74), (-44, -80), (-32, -72)], 2.4, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i2, "PecNear", pec_near_pts, pec_paint))
    out.append(smooth_shape(i2, "PecFar", pec_far_pts, pec_paint))

    # 3. Canonical 3/4 Volumetric Head & Neck
    out.append(
        f'{i2}<Node x="{f(-58.0 + p0["head_dx"])}" y="-90" rotation="{f(p0["head_rot"])}" name="HeadAndNeck" id="{head_id}">'
    )
    out.append(smooth_shape(i3, "HairCap", hair_pts, hair_paint))
    out.append(ellipse_shape(i3, "RightEar", -8, -24, 5.2, 7.6, skin_fill_outlined("Ear", -4, 4, SKIN, line=0.9), rot_deg=-18.0))
    out.append(stroke_shape(i3, "Eyebrow", [(4, -38), (10, -37)], 1.35, "730F172A", 0.3))
    out.append(stroke_shape(i3, "EyeLine", [(5, -34), (9, -34)], 1.1, "800F172A", 0.2))
    out.append(stroke_shape(i3, "MouthLine", [(7, -20), (11, -21)], 1.0, "660F172A", 0.2))
    out.append(stroke_shape(i3, "JawShadow", [(-6, -12), (2, -10), (9, -13)], 2.0, CORE_SHADOW, 1.8))
    out.append(stroke_shape(i3, "HeadHi", [(-12, -40), (-2, -44), (7, -38)], 2.6, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i3, "HeadShape", head_pts, skin_fill_outlined("Head", -48, -9, SKIN, line=1.15)))
    out.append(stroke_shape(i3, "NeckMuscle", [(-2, -10), (6, 2)], 1.4, SOFT_SHADOW, 1.0))
    out.append(smooth_shape(i3, "NeckShape", neck_pts, skin_fill_outlined("Neck", -16, 10, SKIN, line=1.05)))
    out.append(f"{i2}</Node>")

    # 4. Torso Base Silhouette
    out.append(stroke_shape(i2, "TorsoBackSh", [(-60, -48), (-42, -18), (-24, 4)], 4.5, CORE_SHADOW, 4.0))
    out.append(stroke_shape(i2, "TorsoFrontHi", [(-28, -82), (-14, -60), (-2, -34)], 3.2, HIGHLIGHT, 3.2))
    out.append(smooth_shape(i2, "TorsoBase", torso_pts, skin_fill_outlined("TorsoBase", -92, 10, SKIN, line=1.15)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. Articulated Arms & 3D Cast-Iron Weight Plate / Medicine Ball
def build_twist_arm(prefix, far):
    """Articulated arm (Shoulder -> Elbow -> Hand) sweeping the weight plate across the core."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    sh_k = "sh_far" if far else "sh_near"
    el_k = "elb_far" if far else "elb_near"
    ua_ang_k = "ua_far_ang" if far else "ua_near_ang"
    ua_sc_k = "ua_far_sc" if far else "ua_near_sc"
    fa_ang_k = "fa_far_ang" if far else "fa_near_ang"
    fa_sc_k = "fa_far_sc" if far else "fa_near_sc"
    delt_ang_k = "delt_far_ang" if far else "delt_near_ang"

    ua_id, fa_id, delt_id = nid(), nid(), nid()
    key_double(ua_id, 13, lambda p: p[sh_k][0])
    key_double(ua_id, 14, lambda p: p[sh_k][1])
    key_double(ua_id, 15, lambda p: p[ua_ang_k])
    key_double(ua_id, 16, lambda p: p[ua_sc_k])

    key_double(fa_id, 13, lambda p: p[el_k][0])
    key_double(fa_id, 14, lambda p: p[el_k][1])
    key_double(fa_id, 15, lambda p: p[fa_ang_k])
    key_double(fa_id, 16, lambda p: p[fa_sc_k])

    key_double(delt_id, 13, lambda p: p[sh_k][0])
    key_double(delt_id, 14, lambda p: p[sh_k][1])
    key_double(delt_id, 15, lambda p: p[delt_ang_k])

    p0 = POSES[0]

    delt_pts = [
        (-11, 0), (-7, -10.5), (4, -12.0), (15, -8.5), (18, 0),
        (15, 8.5), (4, 11.5), (-7, 9.5),
    ]
    ua_pts = [
        (-8, 0), (-5, -9.2), (8, -10.5), (24, -9.8), (36, -7.2),
        (44, 0), (36, 7.2), (24, 9.8), (8, 10.2), (-5, 8.5),
    ]
    fa_pts = [
        (-6, 0), (-3, -7.2), (10, -8.2), (24, -6.5), (34, -4.8),
        (40, 0), (34, 4.8), (24, 6.5), (10, 7.8), (-3, 6.5),
    ]
    hand_pts = [
        (-4, -5.8), (5, -6.5), (11, -3.2), (11, 3.8), (5, 6.5), (-4, 5.2),
    ]

    return "\n".join([
        f'{ind}<Node name="{prefix}TwistArm">',
        # Forearm & Gripping Hand in front so hands wrap onto the weight plate cleanly
        f'{i2}<Node x="{f(p0[el_k][0])}" y="{f(p0[el_k][1])}" '
        f'rotation="{f(p0[fa_ang_k])}" scaleX="{f(p0[fa_sc_k])}" name="{prefix}Forearm" id="{fa_id}">',
        smooth_shape(i3, f"{prefix}Hand", hand_pts, skin_fill_outlined(prefix + "Hand", -7, 7, skin, line=1.1), x=FOREARM_LEN - 2.0),
        stroke_shape(i3, f"{prefix}ForearmHi", [(6, -4.0), (20, -3.5), (32, -2.5)], 2.2, HIGHLIGHT, 2.2),
        stroke_shape(i3, f"{prefix}ForearmSh", [(6, 4.2), (20, 3.8), (32, 2.8)], 3.0, CORE_SHADOW, 2.8),
        smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill_outlined(prefix + "FA", -8, 8, skin, line=1.15)),
        f"{i2}</Node>",
        # Deltoid Cap at Shoulder
        f'{i2}<Node x="{f(p0[sh_k][0])}" y="{f(p0[sh_k][1])}" '
        f'rotation="{f(p0[delt_ang_k])}" name="{prefix}DeltoidCap" id="{delt_id}">',
        stroke_shape(i3, f"{prefix}DeltHi", [(-3, -6), (6, -5), (12, 0)], 2.4, HIGHLIGHT, 2.4),
        smooth_shape(i3, f"{prefix}DeltoidShape", delt_pts, skin_fill_outlined(prefix + "Delt", -12, 12, skin, line=1.1)),
        f"{i2}</Node>",
        # Upper Arm
        f'{i2}<Node x="{f(p0[sh_k][0])}" y="{f(p0[sh_k][1])}" '
        f'rotation="{f(p0[ua_ang_k])}" scaleX="{f(p0[ua_sc_k])}" name="{prefix}UpperArm" id="{ua_id}">',
        stroke_shape(i3, f"{prefix}BicepsLine", [(10, -4.5), (24, -4.2), (34, -2.5)], 1.2, SOFT_SHADOW, 0.5),
        stroke_shape(i3, f"{prefix}UpperArmHi", [(8, -5.8), (22, -5.5), (34, -4.0)], 2.6, HIGHLIGHT, 2.6),
        stroke_shape(i3, f"{prefix}UpperArmSh", [(8, 5.8), (22, 5.5), (34, 4.0)], 3.4, CORE_SHADOW, 3.2),
        smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill_outlined(prefix + "UA", -10, 10, skin, line=1.15)),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


def build_weight_plate():
    """Sculpted 3D dark cast-iron/urethane bumper weight plate / medicine ball held between the hands."""
    ind = "        "
    i2 = ind + "    "
    wt_id = nid()
    key_double(wt_id, 13, lambda p: p["weight_center"][0])
    key_double(wt_id, 14, lambda p: p["weight_center"][1])
    key_double(wt_id, 15, lambda p: p["weight_rot"])
    p0 = POSES[0]

    plate_outer = (
        f'<Fill name="PlateOuterFill">{grad3("PlateOuterGrad", -22, 22, *PLATE_DARK, x0=-22, x1=22)}</Fill>'
        '<Stroke thickness="1.6" join="round" name="PlateOuterRim"><SolidColor colorValue="FF64748B" name="PlateOuterRimCol"/></Stroke>'
    )
    plate_inner = (
        '<Fill name="PlateInnerFill"><SolidColor colorValue="FF111827" name="PlateInnerCol"/></Fill>'
        '<Stroke thickness="1.2" join="round" name="PlateInnerRim"><SolidColor colorValue="FF475569" name="PlateInnerRimCol"/></Stroke>'
    )
    hub_paint = (
        f'<Fill name="PlateHubFill">{grad("PlateHubGrad", -6, -6, 6, 6, "FFCBD5E1", "FF475569")}</Fill>'
        '<Stroke thickness="1.0" name="PlateHubStroke"><SolidColor colorValue="FF0F172A" name="PlateHubStrokeCol"/></Stroke>'
    )
    finger_wrap_near = skin_fill_outlined("FingerWrapNear", -5, 5, SKIN, line=1.0)
    finger_wrap_far = skin_fill_outlined("FingerWrapFar", -5, 5, SKIN_FAR, line=0.95)

    return "\n".join([
        f'{ind}<Node x="{f(p0["weight_center"][0])}" y="{f(p0["weight_center"][1])}" '
        f'rotation="{f(p0["weight_rot"])}" name="WeightPlateGroup" id="{wt_id}">',
        # Finger wraps gripping both edges of the plate
        ellipse_shape(i2, "NearFingerGrip", -11.0, 5.0, 11.0, 8.5, finger_wrap_near, rot_deg=25.0),
        ellipse_shape(i2, "FarFingerGrip", 11.0, -5.0, 10.5, 8.0, finger_wrap_far, rot_deg=25.0),
        # Center chrome hub & inner recessed ring
        ellipse_shape(i2, "WeightCenterHub", 0.0, 0.0, 9.5, 8.0, hub_paint, rot_deg=-15.0),
        stroke_shape(i2, "WeightSpecularArc", [(-12, -11), (-2, -14), (10, -10)], 2.2, "66FFFFFF", 1.5),
        ellipse_shape(i2, "WeightInnerRecess", 0.0, 0.0, 24.0, 20.0, plate_inner, rot_deg=-15.0),
        ellipse_shape(i2, "WeightOuterDisc", 0.0, 0.0, 36.0, 30.0, plate_outer, rot_deg=-15.0),
        ellipse_shape(i2, "WeightBackBevel", -2.5, 2.5, 36.0, 30.0, solid("WeightBack", "FF090D16"), rot_deg=-15.0),
        f"{ind}</Node>",
    ])


def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    far_leg_xml, near_leg_xml = build_vsit_legs_and_pelvis()
    torso_xml = build_vsit_torso_and_head()
    near_arm_xml = build_twist_arm("Near", False)
    far_arm_xml = build_twist_arm("Far", True)
    weight_xml = build_weight_plate()

    grouped = {}
    for oid, kp_xml in KEYED:
        grouped.setdefault(oid, []).append(kp_xml)
    keyed_objects_xml = "\n".join(
        f'        <KeyedObject objectId="{oid}">\n' + "\n".join(props) + "\n        </KeyedObject>"
        for oid, props in grouped.items()
    )

    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"
    mat_fill = (
        f'<Fill name="MatFill">{grad("MatGrad", 170, 291, 470, 300, "FF334155", "FF1E293B")}</Fill>'
        '<Stroke thickness="1.1" join="round" name="MatStroke"><SolidColor colorValue="FF475569" name="MatStrokeCol"/></Stroke>'
    )

    return f"""<Rive version="7.3">
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="RussianTwist" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Right) Arm & Hand Sweeping Across Core -->
{near_arm_xml}

        <!-- 2. Sculpted Cast-Iron Weight Plate / Medicine Ball -->
{weight_xml}

        <!-- 3. Near (Right) Elevated V-Sit Leg & Seated Pelvis Shorts -->
{near_leg_xml}

        <!-- 4. V-Sit Reclined Torso, Glowing Obliques & 6-Pack Rectus Abdominis, and 3/4 Head -->
{torso_xml}

        <!-- 5. Far (Left) Elevated V-Sit Leg in 3/4 Depth -->
{far_leg_xml}

        <!-- 6. Background: Far (Left) Arm -->
{far_arm_xml}

        <!-- 7. Beveled Exercise Mat, Contact Shadow & Studio Backdrop -->
        <Shape x="326" y="293" scaleX="1.45" scaleY="0.09" name="AthleteMatShadow">
            <Ellipse width="190" height="190" name="AthleteMatShadowEllipse"/>
            <Fill name="AthleteMatShadowFill"><RadialGradient startX="0" startY="0" endX="95" endY="0" name="AthleteMatShadowGrad">
                <GradientStop colorValue="CC000000" position="0"/>
                <GradientStop colorValue="59000000" position="0.62"/>
                <GradientStop colorValue="00000000" position="1"/>
            </RadialGradient></Fill>
        </Shape>
        {poly_shape("        ", "ExerciseMat", [(168, 292), (472, 292), (482, 299), (158, 299)], mat_fill, radius=3.0)}
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="RussianTwist" id="0:60">
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
    ASSET_RIV.parent.mkdir(parents=True, exist_ok=True)
    ASSET_THUMB.parent.mkdir(parents=True, exist_ok=True)

    riv_bytes = _compile_rml_bytes(OUT)
    (BUILD / "russian_twist.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/aff6e669-980f-4ec0-a386-c5be528dd2f8/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (40, "frame_mid"), (78, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(600, 60, 368))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
