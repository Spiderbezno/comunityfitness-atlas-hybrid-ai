#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive 7.3 scene for Incline Dumbbell Press (id: 'incline_dumbbell_press').

Uses our canonical 3/4 athletic male mannequin reclined at ~38 deg on a 3D isometric incline weight bench
(matching `chest_fly/gen_chest_fly.py`, `front_raise/gen_front_raise.py`, and `hammer_curl/gen_hammer_curl.py`):
  - Volumetric 3/4 head with cropped dark hair, ear, brow, eye, nose, and mouth resting on the backrest.
  - Sculpted pectorals, 6-pack rectus abdominis, serratus anterior, external obliques, and dark athletic
    compression shorts, with both legs straddling the bench and planted on `FLOOR = 300.0`.
  - Matches the 2-panel 3/4 front-left Incline Dumbbell Press reference illustration:
    * Left Panel (f = 0 & f = 160, r = 0.0 — Bottom Stretch Position):
      - Elbows are deeply bent (~90 deg) down and out below shoulder level (`elbow_near = (392, 166)`,
        `elbow_far = (272, 96)`) while the forearms remain angled vertically up-left holding a pair of
        heavy 3D double-plate black dumbbells in a PRONATED (overhand) press grip right outside the shoulders.
    * Right Panel (f = 74, r = 1.0 — Top Lockout Contraction):
      - Both arms press smoothly upward along a converging linear press path to full elbow extension above
        the upper clavicular chest (`hand_near = (334, 52)`, `hand_far = (284, 30)`), bringing the two
        pronated-grip dumbbells close together at lockout without colliding.
  - All 3 Labeled Target Muscle Groups from the reference illustration, glowing from warm orange (#FFF97316)
    at the bottom stretch to intense crimson (#FFF43F5E) at top lockout:
    1. Upper pectoralis major (clavicular head band across the upper chest below the clavicles; lower
       sternocostal chest remains in canonical unhighlighted skin/shadow tone so the upper chest isolation
       is unmistakable)
    2. Anterior deltoid (front shoulder cap on both shoulders)
    3. Triceps brachii (lateral & long head along the outer/posterior aspect of both upper arms, with
       dynamic lockout bulge)

Run:
    python3 gen_incline_dumbbell_press.py            # writes scene.rml
    python3 gen_incline_dumbbell_press.py --publish  # compiles assets/animations/incline_dumbbell_press.riv + thumbnail
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
ASSET_RIV = REPO / "assets/animations/incline_dumbbell_press.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/incline_dumbbell_press.png"

# 16:9 standard canvas
W, H = 640, 360
FLOOR = 300.0
FPS = 60

# Shoulder anchors in world space (athlete reclined ~38 deg on the incline backrest)
SHOULDER_FAR = (304.0, 114.0)   # Right (far / upper-left) shoulder
SHOULDER_NEAR = (350.0, 134.0)  # Left (near / lower-right) shoulder

# Timeline (160 frames / 2.67s @ 60fps):
#   0..14:   Bottom press stretch hold (r = 0.0: Left Panel)
#   14..66:  Concentric incline press up to lockout (r: 0.0 -> 1.0)
#   66..86:  Top lockout isometric squeeze (r = 1.0: Right Panel)
#   86..148: Controlled eccentric lowering to bottom stretch (r: 1.0 -> 0.0)
#   148..160: Bottom press stretch hold (r = 0.0)
DURATION = 160
STEP = 2


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


EASE_PRESS = cubic_bezier(0.38, 0.0, 0.24, 1.0)
EASE_LOWER = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def press_progress(frame):
    """Returns incline press progress r in [0.0, 1.0] across 160 frames."""
    fr = frame % (DURATION + 1)
    if fr <= 14:
        return 0.0
    if fr <= 66:
        return EASE_PRESS((fr - 14) / 52.0)
    if fr <= 86:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_LOWER((fr - 86) / 62.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def quad_interp_pt(p0, p_mid, p1, t):
    """Smooth quadratic Lagrange interpolation through p0 (t=0), p_mid (t=0.5), and p1 (t=1.0)."""
    l0 = (1.0 - t) * (1.0 - 2.0 * t)
    l1 = 4.0 * t * (1.0 - t)
    l2 = t * (2.0 * t - 1.0)
    return (
        l0 * p0[0] + l1 * p_mid[0] + l2 * p1[0],
        l0 * p0[1] + l1 * p_mid[1] + l2 * p1[1],
    )


def seg_xform(p0, p1, base_len):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ang = math.atan2(dy, dx)
    sc = max(0.65, math.hypot(dx, dy) / base_len)
    return ang, sc


UPPER_ARM_FAR, FOREARM_FAR = 40.0, 40.0
UPPER_ARM_NEAR, FOREARM_NEAR = 45.0, 42.0


def pose(r):
    """Compute Incline Dumbbell Press pose at progress r in [0.0, 1.0]."""
    # 1. Far (Right) Arm Kinematics (`SHOULDER_FAR = (304, 114)`):
    #    - Bottom Stretch (r = 0.0, Left Panel):
    #        elbow_far = (268.0, 96.0), hand_far = (258.0, 56.0)
    #    - Mid-Press (r = 0.5):
    #        elbow_far = (279.0, 82.0), hand_far = (271.0, 42.0)
    #    - Top Lockout (r = 1.0, Right Panel):
    #        elbow_far = (294.0, 74.0), hand_far = (284.0, 34.0)
    elbow_far = quad_interp_pt((268.0, 96.0), (279.0, 82.0), (294.0, 74.0), r)
    hand_far = quad_interp_pt((258.0, 56.0), (271.0, 42.0), (284.0, 34.0), r)
    ua_far, ua_far_sc = seg_xform(SHOULDER_FAR, elbow_far, UPPER_ARM_FAR)
    fa_far_world, fa_far_sc = seg_xform(elbow_far, hand_far, FOREARM_FAR)

    # 2. Near (Left) Arm Kinematics (`SHOULDER_NEAR = (350, 134)`):
    #    - Bottom Stretch (r = 0.0, Left Panel):
    #        elbow_near = (392.0, 165.0), hand_near = (382.0, 124.0)
    #    - Mid-Press (r = 0.5):
    #        elbow_near = (368.0, 128.0), hand_near = (358.0, 87.0)
    #    - Top Lockout (r = 1.0, Right Panel):
    #        elbow_near = (343.0, 94.0), hand_near = (333.0, 53.0)
    elbow_near = quad_interp_pt((392.0, 165.0), (368.0, 128.0), (343.0, 94.0), r)
    hand_near = quad_interp_pt((382.0, 124.0), (358.0, 87.0), (333.0, 53.0), r)
    ua_near, ua_near_sc = seg_xform(SHOULDER_NEAR, elbow_near, UPPER_ARM_NEAR)
    fa_near_world, fa_near_sc = seg_xform(elbow_near, hand_near, FOREARM_NEAR)

    # 3. Dynamic Upper Pectoralis Major & Triceps Brachii contraction
    pec_near_dx = lerp(1.2, -2.2, r)
    pec_near_dy = lerp(0.8, -2.0, r)
    pec_far_dx = lerp(-1.0, 1.8, r)
    pec_far_dy = lerp(0.6, -1.8, r)
    chest_lift = lerp(0.6, -1.5, r)
    triceps_bulge = lerp(1.00, 1.16, r ** 0.9)

    # 4. World-space pronated (overhand) press dumbbell orientation (~ +24 deg along the shoulder line)
    db_far_world = math.radians(lerp(26.0, 23.0, r))
    db_near_world = math.radians(lerp(28.0, 24.0, r))

    return {
        "r": r,
        "hand_far": hand_far,
        "hand_near": hand_near,
        "elbow_far": elbow_far,
        "elbow_near": elbow_near,
        "ua_far": ua_far,
        "ua_far_sc": ua_far_sc,
        "fa_far_world": fa_far_world,
        "fa_far_sc": fa_far_sc,
        "ua_near": ua_near,
        "ua_near_sc": ua_near_sc,
        "fa_near_world": fa_near_world,
        "fa_near_sc": fa_near_sc,
        "pec_near_dx": pec_near_dx,
        "pec_near_dy": pec_near_dy,
        "pec_far_dx": pec_far_dx,
        "pec_far_dy": pec_far_dy,
        "chest_lift": chest_lift,
        "triceps_bulge": triceps_bulge,
        "db_far_world": db_far_world,
        "db_near_world": db_near_world,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(press_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = ("ua_far", "fa_far_world", "ua_near", "fa_near_world", "db_far_world", "db_near_world")
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

if __name__ == "__main__":
    for _fr in (0, 38, 74, 118, DURATION):
        _p = POSES[_fr if _fr in POSES else min(POSES.keys(), key=lambda k: abs(k - _fr))]
        print(
            f"f{_fr:3d} r={_p['r']:.3f} far_w=({_p['hand_far'][0]:.1f},{_p['hand_far'][1]:.1f}) "
            f"near_w=({_p['hand_near'][0]:.1f},{_p['hand_near'][1]:.1f}) "
            f"ua_near={math.degrees(_p['ua_near']):+.1f}"
        )


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


def poly_shape(indent, name, pts, paint_xml, radius=1.5):
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


# ---------------------------------------------------------------- Canonical Palette & Muscle Activation
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF334155", "FF1E293B", "FF0F172A")
SHORTS_FAR = ("FF263142", "FF151E2E", "FF090D16")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "520F172A"

# Target Muscle Heat Colors: warm orange (#FFF97316) at bottom stretch -> intense crimson (#FFF43F5E) at top lockout
MUSCLE_LOW = (0xE6, 0xF9, 0x73, 0x16)
MUSCLE_HIGH = (0xFF, 0xF4, 0x3F, 0x5E)
MUSCLE_LINE_LOW = (0x80, 0x9A, 0x34, 0x12)
MUSCLE_LINE_HIGH = (0xE6, 0x88, 0x13, 0x37)


def argb_lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return "".join(f"{round(lerp(x, y, t)):02X}" for x, y in zip(a, b))


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


def muscle_paint_fn(name, fn_t, line=0.95):
    fid, lid = nid(), nid()
    key_color(fid, 37, lambda p: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, fn_t(p)))
    key_color(lid, 37, lambda p: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, fn_t(p)))
    t0 = fn_t(POSES[0])
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- 1. 3D Incline Weight Bench (from chest_fly)
def front_bench_arch_rig():
    """Foreground white arched front stabilizer leg (drawn in front of FarRightLeg ankle and behind NearLeftLeg)."""
    ind = "        "
    i2 = ind + "    "
    steel_top = f'<Fill name="ArchTopFill">{grad("ArchTopGrad", 155, 240, 238, 300, "FFF8FAFC", "FFCBD5E1")}</Fill>'
    steel_side = f'<Fill name="ArchSideFill">{grad("ArchSideGrad", 155, 244, 238, 300, "FFCBD5E1", "FF64748B")}</Fill>'
    steel_edge = '<Stroke thickness="0.9" join="round" name="ArchRim"><SolidColor colorValue="FF94A3B8" name="ArchRimCol"/></Stroke>'
    rubber_foot = solid("ArchRubberFoot", "FF0F172A")

    return "\n".join([
        f'{ind}<Node name="FrontBenchArch">',
        poly_shape(
            i2, "FrontArchSide",
            [(158, 266), (186, 244), (210, 248), (234, 298), (222, 299), (202, 258), (184, 256), (164, 270)],
            steel_side + steel_edge, radius=3.5,
        ),
        poly_shape(
            i2, "FrontArchTop",
            [(156, 262), (184, 240), (212, 244), (236, 295), (226, 297), (204, 253), (186, 251), (162, 266)],
            steel_top + steel_edge, radius=3.5,
        ),
        poly_shape(i2, "FrontFootCapNear", [(220, 294), (237, 294), (238, 300), (219, 300)], rubber_foot, radius=1.5),
        poly_shape(i2, "FrontFootCapFar", [(152, 261), (166, 264), (165, 270), (151, 267)], rubber_foot, radius=1.5),
        f"{ind}</Node>",
    ])


def incline_bench_rig():
    """3D Isometric Incline Weight Bench with white/silver steel frame on FLOOR = 300.0 and dark upholstered pads."""
    ind = "        "
    i2 = ind + "    "

    steel_top = f'<Fill name="SteelTopFill">{grad("SteelTopGrad", 170, 200, 410, 300, "FFF8FAFC", "FFCBD5E1")}</Fill>'
    steel_side = f'<Fill name="SteelSideFill">{grad("SteelSideGrad", 170, 200, 410, 300, "FFCBD5E1", "FF64748B")}</Fill>'
    steel_edge = '<Stroke thickness="0.9" join="round" name="SteelRim"><SolidColor colorValue="FF94A3B8" name="SteelRimCol"/></Stroke>'

    pad_top = f'<Fill name="PadTopFill">{grad("PadTopGrad", 240, 95, 385, 225, "FF334155", "FF1E293B")}</Fill>'
    pad_side = f'<Fill name="PadSideFill">{grad("PadSideGrad", 240, 100, 390, 232, "FF1E293B", "FF090D16")}</Fill>'
    pad_rim = '<Stroke thickness="0.9" join="round" name="PadRim"><SolidColor colorValue="FF475569" name="PadRimCol"/></Stroke>'
    rubber_foot = solid("RubberFoot", "FF0F172A")

    return "\n".join([
        f'{ind}<Node name="InclineBench">',
        stroke_shape(i2, "SeatPadEdgeHi", [(232, 212), (264, 224), (294, 206)], 1.2, "5994A3B8", 0.5),
        poly_shape(i2, "SeatPadFrontSkirt", [(228, 204), (264, 220), (264, 231), (228, 214)], pad_side, radius=2.5),
        poly_shape(i2, "SeatPadRightSkirt", [(264, 220), (296, 202), (296, 212), (264, 231)], pad_side, radius=2.5),
        poly_shape(i2, "SeatPadTop", [(228, 204), (260, 188), (296, 202), (264, 220)], pad_top + pad_rim, radius=3.0),
        stroke_shape(i2, "BackrestHighlight", [(298, 204), (340, 152), (380, 102)], 1.4, "5994A3B8", 0.5),
        poly_shape(i2, "BackrestRightSide", [(296, 208), (382, 100), (390, 108), (304, 217)], pad_side + pad_rim, radius=3.0),
        poly_shape(i2, "BackrestBottomSkirt", [(274, 196), (296, 208), (304, 217), (282, 204)], pad_side, radius=2.5),
        poly_shape(i2, "BackrestTopFace", [(274, 196), (360, 88), (382, 100), (296, 208)], pad_top + pad_rim, radius=4.0),
        poly_shape(i2, "SeatSupportPost", [(256, 218), (268, 214), (268, 236), (256, 240)], steel_side + steel_edge, radius=1.5),
        poly_shape(i2, "BackrestLadderBracket", [(308, 210), (336, 226), (334, 232), (306, 216)], steel_side + steel_edge, radius=1.5),
        poly_shape(i2, "BackrestSupportStrut", [(318, 174), (327, 170), (340, 230), (331, 234)], steel_top + steel_edge, radius=1.5),
        poly_shape(i2, "MainSpineSide", [(196, 254), (296, 206), (296, 216), (196, 264)], steel_side + steel_edge, radius=2.0),
        poly_shape(i2, "MainSpineTop", [(194, 248), (294, 200), (298, 206), (198, 254)], steel_top + steel_edge, radius=2.0),
        poly_shape(i2, "RearStabilizerSide", [(292, 208), (396, 288), (393, 297), (290, 216)], steel_side + steel_edge, radius=2.5),
        poly_shape(i2, "RearStabilizerTop", [(294, 202), (398, 282), (396, 288), (292, 208)], steel_top + steel_edge, radius=2.5),
        poly_shape(i2, "RearFootCap", [(388, 288), (400, 290), (399, 300), (387, 300)], rubber_foot, radius=2.0),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 2. Straddled Legs in 3/4 Perspective (from chest_fly)
def far_right_leg_rig():
    """Far (Right) Leg extending left from right hip (256, 186) to knee (188, 202) and foot behind front stabilizer arch."""
    ind = "        "
    i2 = ind + "    "

    shorts_pts = [
        (264, 174), (234, 172), (218, 178), (226, 204), (258, 198),
    ]
    thigh_pts = [
        (254, 176), (224, 175), (196, 185), (182, 198),
        (188, 214), (212, 211), (242, 202), (258, 194),
    ]
    shin_pts = [
        (182, 204), (186, 226), (194, 248), (200, 260),
        (210, 256), (212, 234), (208, 214), (196, 202),
    ]
    foot_pts = [
        (196, 254), (168, 256), (144, 263), (146, 270),
        (170, 268), (204, 262), (206, 256),
    ]

    return "\n".join([
        f'{ind}<Node name="FarRightLeg">',
        stroke_shape(i2, "FarShortsHem", [(220, 178), (222, 192), (227, 203)], 1.3, "80090D16", 0.4),
        smooth_shape(i2, "FarThighShorts", shorts_pts, skin_fill("FarShorts", 172, 204, SHORTS_FAR, x0=260, x1=218)),
        stroke_shape(i2, "FarQuadGroove1", [(232, 182), (208, 189), (190, 198)], 1.2, CORE_SHADOW, 0.7),
        stroke_shape(i2, "FarQuadGroove2", [(236, 192), (212, 199), (194, 205)], 1.2, CORE_SHADOW, 0.7),
        stroke_shape(i2, "FarVastusMedialisLine", [(208, 195), (198, 203), (204, 210)], 1.1, SOFT_SHADOW, 0.6),
        stroke_shape(i2, "FarThighHi", [(238, 180), (212, 184), (190, 194)], 3.2, HIGHLIGHT, 3.0),
        stroke_shape(i2, "FarThighSh", [(240, 199), (214, 207), (192, 211)], 3.8, CORE_SHADOW, 3.5),
        smooth_shape(i2, "FarThigh", thigh_pts, skin_fill("FarThigh", 175, 214, SKIN_FAR, x0=254, x1=182)),
        ellipse_shape(i2, "FarKneeCap", 187, 204, 14, 15, skin_fill("FarKnee", -7, 7, SKIN_FAR)),
        stroke_shape(i2, "FarCalfGroove", [(198, 214), (204, 232), (204, 248)], 1.2, CORE_SHADOW, 0.7),
        stroke_shape(i2, "FarShinHi", [(188, 212), (194, 234), (200, 252)], 2.4, HIGHLIGHT, 2.5),
        smooth_shape(i2, "FarShin", shin_pts, skin_fill("FarShin", 202, 260, SKIN_FAR, x0=212, x1=182)),
        stroke_shape(i2, "FarFootSoleSh", [(148, 268), (174, 266), (200, 261)], 1.6, CORE_SHADOW, 1.0),
        smooth_shape(i2, "FarFoot", foot_pts, skin_fill("FarFoot", 254, 270, SKIN_FAR, x0=206, x1=144)),
        f"{ind}</Node>",
    ])


def near_left_leg_rig():
    """Near (Left) Leg in foreground from left hip (284, 198) to knee (252, 232) and planted foot on FLOOR = 300.0."""
    ind = "        "
    i2 = ind + "    "

    shorts_pts = [
        (264, 188), (298, 194), (300, 216), (282, 224), (258, 212),
    ]
    thigh_pts = [
        (268, 196), (294, 204), (288, 222), (272, 238),
        (252, 240), (244, 228), (252, 210),
    ]
    shin_pts = [
        (244, 232), (264, 234), (266, 254), (258, 274),
        (252, 290), (240, 290), (240, 268), (241, 248),
    ]
    foot_pts = [
        (240, 286), (253, 286), (254, 296), (244, 301),
        (230, 300), (228, 295), (235, 290),
    ]

    return "\n".join([
        f'{ind}<Node name="NearLeftLeg">',
        stroke_shape(i2, "NearShortsHem", [(259, 211), (272, 218), (284, 223)], 1.4, "80090D16", 0.4),
        smooth_shape(i2, "NearThighShorts", shorts_pts, skin_fill("NearShorts", 188, 224, SHORTS, x0=258, x1=300)),
        stroke_shape(i2, "NearRectusFemorisL", [(272, 204), (260, 218), (251, 230)], 1.3, CORE_SHADOW, 0.8),
        stroke_shape(i2, "NearRectusFemorisR", [(284, 210), (272, 224), (261, 234)], 1.3, CORE_SHADOW, 0.8),
        stroke_shape(i2, "NearVastusMedialis", [(256, 216), (248, 224), (252, 233)], 1.1, SOFT_SHADOW, 0.6),
        stroke_shape(i2, "NearThighHi", [(276, 205), (264, 219), (254, 231)], 3.8, HIGHLIGHT, 3.5),
        stroke_shape(i2, "NearThighSh", [(288, 214), (276, 229), (264, 237)], 4.2, CORE_SHADOW, 3.8),
        smooth_shape(i2, "NearThigh", thigh_pts, skin_fill("NearThigh", 196, 240, SKIN, x0=250, x1=294)),
        ellipse_shape(i2, "NearKneeCap", 252, 235, 16, 15, skin_fill("NearKnee", -8, 8, SKIN)),
        stroke_shape(i2, "NearPatellaLine", [(246, 238), (252, 242), (258, 238)], 1.1, SOFT_SHADOW, 0.5),
        stroke_shape(i2, "NearTibialisLine", [(250, 244), (248, 266), (246, 285)], 1.3, CORE_SHADOW, 0.8),
        stroke_shape(i2, "NearCalfFlareLine", [(258, 246), (261, 262), (254, 278)], 1.2, SOFT_SHADOW, 0.7),
        stroke_shape(i2, "NearShinHi", [(246, 244), (245, 266), (244, 284)], 2.8, HIGHLIGHT, 2.8),
        stroke_shape(i2, "NearShinSh", [(260, 248), (259, 266), (252, 284)], 3.2, CORE_SHADOW, 3.0),
        smooth_shape(i2, "NearShin", shin_pts, skin_fill("NearShin", 232, 290, SKIN, x0=240, x1=266)),
        stroke_shape(i2, "NearToeLine1", [(234, 295), (238, 299)], 0.9, SOFT_SHADOW, 0.3),
        stroke_shape(i2, "NearToeLine2", [(239, 295), (243, 300)], 0.9, SOFT_SHADOW, 0.3),
        stroke_shape(i2, "NearFootHi", [(244, 289), (238, 294)], 2.0, HIGHLIGHT, 1.8),
        smooth_shape(i2, "NearFoot", foot_pts, skin_fill("NearFoot", 286, 301, SKIN, x0=230, x1=254)),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 3. Reclined Torso, Isolated Upper Pectoralis Major, 6-Pack Abs & 3/4 Head
def reclined_torso_and_head_rig():
    """Reclined torso (~38 deg), sculpted 6-pack abs, serratus anterior, isolated glowing Upper Pectoralis Major
    (clavicular head) above canonical sternocostal pec plates, and volumetric 3/4 Head."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "

    chest_id, pec_far_id, pec_near_id = nid(), nid(), nid()
    key_double(chest_id, 14, lambda p: p["chest_lift"])
    key_double(pec_far_id, 13, lambda p: p["pec_far_dx"])
    key_double(pec_far_id, 14, lambda p: p["pec_far_dy"])
    key_double(pec_near_id, 13, lambda p: p["pec_near_dx"])
    key_double(pec_near_id, 14, lambda p: p["pec_near_dy"])
    p0 = POSES[0]

    def upper_pec_t(p):
        return 0.48 + 0.52 * (p["r"] ** 0.78)

    pelvis_shorts_pts = [
        (246, 174), (268, 174), (298, 190),
        (300, 212), (274, 216), (244, 196),
    ]
    torso_pts = [
        (256, 176), (272, 156), (288, 136), (302, 114),
        (326, 112), (350, 128), (352, 148), (334, 168),
        (314, 184), (296, 196), (274, 190),
    ]

    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1F0F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.95" join="round" name="AbsEdge"><SolidColor colorValue="470F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        [(292, 144), (302, 135), (311, 141), (301, 151)],
        [(281, 156), (291, 146), (300, 153), (290, 163)],
        [(270, 168), (280, 158), (289, 165), (279, 175)],
        [(303, 152), (313, 142), (322, 149), (312, 159)],
        [(292, 164), (302, 154), (311, 161), (301, 171)],
        [(281, 176), (291, 166), (300, 173), (290, 183)],
    ]

    # Canonical unhighlighted sternocostal pec paint (so ONLY the Upper Pectoralis Major clavicular head glows,
    # matching the reference illustration where lower chest is neutral grey/skin!)
    sternal_pec_paint = (
        '<Fill name="SternalPecFill"><SolidColor colorValue="140F172A" name="SternalPecCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="SternalPecStroke"><SolidColor colorValue="3D0F172A" name="SternalPecEdge"/></Stroke>'
    )
    pec_right_sternal_pts = [
        (296, 126), (304, 116), (322, 120),
        (320, 134), (308, 139), (295, 134),
    ]
    # Target Muscle #1: Upper pectoralis major (Clavicular Head)
    pec_right_clavicular_pts = [
        (298, 118), (307, 110), (325, 116),
        (322, 125), (305, 123),
    ]

    pec_left_sternal_pts = [
        (322, 134), (332, 124), (348, 134),
        (344, 150), (328, 154), (315, 144),
    ]
    pec_left_clavicular_pts = [
        (323, 123), (330, 116), (349, 127),
        (345, 138), (328, 131),
    ]

    neck_pts = [
        (322, 116), (334, 98), (350, 108), (336, 124),
    ]
    head_pts = [
        (332, 99), (326, 92), (327, 85), (329, 79),
        (334, 74), (345, 70), (357, 73), (363, 83),
        (360, 95), (351, 102), (340, 102),
    ]
    hair_pts = [
        (337, 73), (347, 69.5), (358, 72.5), (364, 82),
        (361, 95), (354, 99), (355, 89), (350, 80), (342, 76),
    ]

    out = [f'{ind}<Node name="ReclinedTorsoAndHead">']

    # --- 1. Animated Chest Group (Glowing Upper Clavicular Pectorals + Canonical Sternocostal Pectorals) ---
    out.append(f'{i2}<Node y="{f(p0["chest_lift"])}" name="ChestGroup" id="{chest_id}">')
    out.append(stroke_shape(i3, "SternalCleavage", [(326, 117), (321, 130), (315, 140)], 1.5, CORE_SHADOW, 0.5))

    # Near (Left) Pectoralis Major
    out.append(f'{i3}<Node x="{f(p0["pec_near_dx"])}" y="{f(p0["pec_near_dy"])}" name="PecLeftNode" id="{pec_near_id}">')
    out.append(stroke_shape(i4, "UpperPecLeftHi", [(328, 122), (338, 126), (345, 132)], 2.0, "66FFFFFF", 1.8))
    out.append(stroke_shape(i4, "UpperPecLeftFiber", [(326, 126), (336, 130), (345, 134)], 1.0, "737F1D1D", 0.4))
    out.append(smooth_shape(i4, "UpperPecLeftActivation", pec_left_clavicular_pts, muscle_paint_fn("UpperPecLeft", upper_pec_t, 1.0)))
    out.append(stroke_shape(i4, "PecLeftUnderFold", [(315, 145), (328, 154), (343, 150)], 2.0, CORE_SHADOW, 1.2))
    out.append(stroke_shape(i4, "PecLeftHi", [(322, 138), (334, 142), (342, 144)], 2.4, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i4, "PecLeftSternal", pec_left_sternal_pts, sternal_pec_paint))
    out.append(f"{i3}</Node>")

    # Far (Right) Pectoralis Major
    out.append(f'{i3}<Node x="{f(p0["pec_far_dx"])}" y="{f(p0["pec_far_dy"])}" name="PecRightNode" id="{pec_far_id}">')
    out.append(stroke_shape(i4, "UpperPecRightHi", [(303, 115), (313, 116), (322, 119)], 1.8, "66FFFFFF", 1.6))
    out.append(stroke_shape(i4, "UpperPecRightFiber", [(301, 119), (312, 120), (322, 122)], 0.95, "737F1D1D", 0.4))
    out.append(smooth_shape(i4, "UpperPecRightActivation", pec_right_clavicular_pts, muscle_paint_fn("UpperPecRight", upper_pec_t, 0.95)))
    out.append(stroke_shape(i4, "PecRightUnderFold", [(295, 134), (308, 139), (320, 134)], 1.8, CORE_SHADOW, 1.0))
    out.append(smooth_shape(i4, "PecRightSternal", pec_right_sternal_pts, sternal_pec_paint))
    out.append(f"{i3}</Node>")

    out.append(f"{i2}</Node>")

    # --- 2. Sculpted 6-Pack Rectus Abdominis, Linea Alba, Serratus Anterior & External Obliques ---
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "LineaAlba", [(315, 139), (296, 160), (277, 180)], 1.4, CORE_SHADOW, 0.8))
    out.append(stroke_shape(i2, "SerratusRib1", [(324, 156), (334, 154)], 1.2, CORE_SHADOW, 0.6))
    out.append(stroke_shape(i2, "SerratusRib2", [(316, 164), (326, 162)], 1.2, CORE_SHADOW, 0.6))
    out.append(stroke_shape(i2, "SerratusRib3", [(308, 172), (318, 170)], 1.2, CORE_SHADOW, 0.6))
    out.append(stroke_shape(i2, "ObliqueLineLeft", [(322, 152), (308, 168), (294, 184)], 1.3, SOFT_SHADOW, 0.7))
    out.append(stroke_shape(i2, "ObliqueLineRight", [(290, 142), (278, 158), (266, 172)], 1.3, SOFT_SHADOW, 0.7))

    # --- 3. Pelvis Compression Shorts & Torso Base ---
    out.append(stroke_shape(i2, "ShortsWaistband", [(250, 174), (274, 180), (297, 191)], 1.5, "99020617", 0.4))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts_pts, skin_fill("PelvisShorts", 174, 216, SHORTS, x0=246, x1=300)))
    out.append(stroke_shape(i2, "TorsoHi", [(298, 134), (284, 152), (270, 168)], 4.0, HIGHLIGHT, 3.8))
    out.append(stroke_shape(i2, "TorsoSh", [(340, 156), (320, 176), (298, 192)], 5.0, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i2, "TorsoBase", torso_pts, skin_fill("Torso", 112, 196, SKIN, x0=270, x1=350)))

    # --- 4. Canonical Volumetric 3/4 Head & Neck ---
    out.append(f'{i2}<Node name="HeadAndNeck">')
    out.append(smooth_shape(i3, "HairCap", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 336, 70, 364, 98, "FF334155", "FF0F172A")}</Fill>'))
    out.append(ellipse_shape(i3, "LeftEar", 348.5, 96.5, 6.5, 5.0, solid("Ear", "FFCBD5E1"), rot_deg=-25.0))
    out.append(stroke_shape(i3, "EarHelix", [(347.5, 95.5), (349.5, 97.0)], 0.9, SOFT_SHADOW, 0.2))
    out.append(stroke_shape(i3, "BrowAndEye", [(334.5, 78.5), (338.0, 80.5)], 1.3, CORE_SHADOW, 0.5))
    out.append(stroke_shape(i3, "MouthLine", [(328.0, 87.5), (332.0, 89.0)], 1.0, SOFT_SHADOW, 0.3))
    out.append(stroke_shape(i3, "JawlineShadow", [(328.0, 95.0), (338.0, 100.5), (346.0, 99.0)], 1.8, CORE_SHADOW, 1.2))
    out.append(stroke_shape(i3, "HeadHighlight", [(331.0, 82.0), (337.0, 75.0), (348.0, 72.5)], 2.8, HIGHLIGHT, 2.8))
    out.append(smooth_shape(i3, "HeadShape", head_pts, skin_fill("Head", 70, 102, SKIN, x0=326, x1=363)))
    out.append(stroke_shape(i3, "NeckSCMLeft", [(344.0, 102.0), (334.0, 114.0), (326.0, 120.0)], 1.4, CORE_SHADOW, 0.8))
    out.append(stroke_shape(i3, "NeckSCMRight", [(332.0, 99.0), (325.0, 110.0), (322.0, 118.0)], 1.2, SOFT_SHADOW, 0.7))
    out.append(smooth_shape(i3, "NeckShape", neck_pts, skin_fill("Neck", 98, 124, SKIN_FAR, x0=322, x1=350)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 4. Pronated 3D Dumbbells & Press Arms (Anterior Deltoid + Triceps Brachii)
def pronated_dumbbell_3d(indent, prefix, is_near):
    """3D Cast-Iron Double-Plate Dumbbell in PRONATED (overhand) press grip (`+X` = down-right toward camera, `-X` = up-left)."""
    i2 = indent + "    "
    plate_face = (
        f'<Fill name="{prefix}PlateFace">{grad(prefix + "PFG", -9, -15, 9, 15, "FF334155", "FF090D16")}</Fill>'
        f'<Stroke thickness="1.0" name="{prefix}PlateRim"><SolidColor colorValue="FF64748B" name="{prefix}PRCol"/></Stroke>'
    )
    plate_edge = (
        f'<Fill name="{prefix}PlateEdge"><SolidColor colorValue="FF0F172A" name="{prefix}PECol"/></Fill>'
        f'<Stroke thickness="0.9" name="{prefix}PlateEdgeRim"><SolidColor colorValue="FF475569" name="{prefix}PERCol"/></Stroke>'
    )
    chrome_bar = f'<Fill name="{prefix}BarFill">{grad(prefix + "BarG", -14, -3, 14, 3, "FFF8FAFC", "FF475569")}</Fill>'
    skin = SKIN if is_near else SKIN_FAR

    # Pronated (overhand) 4 fingers & thumb wrapped around the chrome handle bar
    fingers_pts = [
        (-5.2, -4.5), (5.2, -4.5), (6.0, 0.5), (5.0, 4.5), (-5.2, 4.5),
    ]
    thumb_pts = [
        (-5.8, 0.5), (-1.2, 4.8), (3.8, 3.8), (2.5, 0.5), (-4.0, -0.5),
    ]

    out = [f'{indent}<Node name="{prefix}DumbbellGeometry">']
    # 1. Foreground: Front-Right Double Plate Stack (`+X` in dumbbell local space, closest to camera in 3/4 view)
    out.append(ellipse_shape(i2, f"{prefix}FrontCollar", 13.8, 0.0, 4.8, 8.0, chrome_bar))
    out.append(ellipse_shape(i2, f"{prefix}FrontOuterPlateFace", 12.2, 0.0, 12.5, 22.5, plate_face))
    out.append(ellipse_shape(i2, f"{prefix}FrontOuterPlateEdge", 10.8, 0.0, 12.5, 22.5, plate_edge))
    out.append(ellipse_shape(i2, f"{prefix}FrontInnerPlateFace", 8.6, 0.0, 15.0, 27.0, plate_face))
    out.append(ellipse_shape(i2, f"{prefix}FrontInnerPlateEdge", 7.0, 0.0, 15.0, 27.0, plate_edge))

    # 2. Midground: Pronated Gripping Fingers, Thumb & Chrome Handle Bar
    out.append(smooth_shape(i2, f"{prefix}Thumb", thumb_pts, skin_fill(prefix + "Thumb", -1, 5, skin)))
    out.append(stroke_shape(i2, f"{prefix}Knuckle1", [(-2.2, -3.5), (-2.0, 3.5)], 0.9, SOFT_SHADOW, 0.3))
    out.append(stroke_shape(i2, f"{prefix}Knuckle2", [(1.0, -3.5), (1.2, 3.5)], 0.9, SOFT_SHADOW, 0.3))
    out.append(stroke_shape(i2, f"{prefix}KnuckleHi", [(-3.8, -2.5), (3.8, -2.5)], 1.3, HIGHLIGHT, 1.0))
    out.append(smooth_shape(i2, f"{prefix}Fingers", fingers_pts, skin_fill(prefix + "Fingers", -5, 5, skin)))
    handle_pts = [(-13.0, -1.8), (13.0, -1.8), (13.0, 1.8), (-13.0, 1.8)]
    out.append(poly_shape(i2, f"{prefix}HandleBar", handle_pts, chrome_bar, radius=1.2))

    # 3. Background: Rear-Left Double Plate Stack (`-X` in dumbbell local space, further from camera)
    out.append(ellipse_shape(i2, f"{prefix}RearInnerPlateFace", -7.2, 0.0, 15.0, 27.0, plate_face))
    out.append(ellipse_shape(i2, f"{prefix}RearInnerPlateEdge", -8.8, 0.0, 15.0, 27.0, plate_edge))
    out.append(ellipse_shape(i2, f"{prefix}RearOuterPlateFace", -11.0, 0.0, 12.5, 22.5, plate_face))
    out.append(ellipse_shape(i2, f"{prefix}RearOuterPlateEdge", -12.4, 0.0, 12.5, 22.5, plate_edge))
    out.append(ellipse_shape(i2, f"{prefix}RearCollar", -13.8, 0.0, 4.5, 7.5, chrome_bar))
    out.append(f"{indent}</Node>")
    return "\n".join(out)


def press_arm_rig(prefix, is_near):
    """Arm + Pronated 3D Dumbbell with glowing Anterior Deltoid & Triceps Brachii (Lateral + Long Head)."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "

    skin = SKIN if is_near else SKIN_FAR
    sx, sy = SHOULDER_NEAR if is_near else SHOULDER_FAR
    ua_len = UPPER_ARM_NEAR if is_near else UPPER_ARM_FAR
    fa_len = FOREARM_NEAR if is_near else FOREARM_FAR
    ua_key = "ua_near" if is_near else "ua_far"
    ua_sc_key = "ua_near_sc" if is_near else "ua_far_sc"
    el_key = "elbow_near" if is_near else "elbow_far"
    hand_key = "hand_near" if is_near else "hand_far"
    fa_key = "fa_near_world" if is_near else "fa_far_world"
    fa_sc_key = "fa_near_sc" if is_near else "fa_far_sc"
    db_key = "db_near_world" if is_near else "db_far_world"

    ua_id, tri_id, fa_id, db_id = nid(), nid(), nid(), nid()
    key_double(ua_id, 15, lambda p: p[ua_key])
    key_double(ua_id, 16, lambda p: p[ua_sc_key])
    key_double(tri_id, 17, lambda p: p["triceps_bulge"])

    key_double(fa_id, 13, lambda p: p[el_key][0])
    key_double(fa_id, 14, lambda p: p[el_key][1])
    key_double(fa_id, 15, lambda p: p[fa_key])
    key_double(fa_id, 16, lambda p: p[fa_sc_key])

    key_double(db_id, 13, lambda p: p[hand_key][0])
    key_double(db_id, 14, lambda p: p[hand_key][1])
    key_double(db_id, 15, lambda p: p[db_key])

    p0 = POSES[0]

    def front_delt_t(p):
        return 0.46 + 0.54 * (p["r"] ** 0.80)

    def triceps_t(p):
        return 0.48 + 0.52 * (p["r"] ** 0.78)

    # Local Y orientation of UpperArm (+X points from shoulder to elbow):
    # - Near (Left) Arm: `in_sign = -1.0` -> Anterior Deltoid on `-Y_local`, Triceps Brachii on `+Y_local`
    # - Far (Right) Arm: `in_sign = +1.0` -> Anterior Deltoid on `+Y_local`, Triceps Brachii on `-Y_local`
    in_sign = -1.0 if is_near else 1.0
    out_sign = -in_sign

    # 1. Sculpted Upper Arm Silhouette (0 .. ua_len)
    ua_pts = [
        (-8.0, 0.0), (-5.0, -9.8), (8.0, -11.2), (ua_len * 0.55, -10.5), (ua_len - 4.0, -7.4),
        (ua_len + 4.5, 0.0), (ua_len - 4.0, 7.4), (ua_len * 0.55, 10.5), (8.0, 11.2), (-5.0, 9.8),
    ]

    # 2. Target Muscle #3: Triceps brachii (Lateral Head + Long Head along the `out_sign` posterior/outer border of UpperArm)
    triceps_lateral_pts = [
        (11.0, out_sign * 0.8),
        (ua_len * 0.48, out_sign * 0.5),
        (ua_len - 5.0, out_sign * 2.0),
        (ua_len - 6.0, out_sign * 7.2),
        (ua_len * 0.50, out_sign * 9.5),
        (12.0, out_sign * 7.8),
    ]
    triceps_long_pts = [
        (8.0, out_sign * 4.5),
        (ua_len * 0.46, out_sign * 5.8),
        (ua_len - 7.5, out_sign * 5.5),
        (ua_len - 8.5, out_sign * 9.2),
        (ua_len * 0.45, out_sign * 11.2),
        (10.0, out_sign * 9.8),
    ]

    # 3. Sculpted Deltoid Cap + Target Muscle #2: Anterior Deltoid (along `in_sign` anterior/inner shoulder cap)
    delt_pts = [
        (-11.5, 0.0), (-7.5, -10.5), (4.0, -12.0), (15.5, -8.5),
        (18.0, 0.0), (15.5, 8.5), (4.0, 12.0), (-7.5, 10.5),
    ]
    front_delt_pts = [
        (-7.5, in_sign * 1.2),
        (3.5, in_sign * 11.0),
        (15.5, in_sign * 8.2),
        (17.0, in_sign * 1.0),
        (4.5, -in_sign * 2.0),
    ]

    # 4. Sculpted Forearm from elbow (0,0) to wrist (fa_len, 0)
    fa_pts = [
        (-5.5, 0.0), (-3.5, -7.8), (fa_len * 0.35, -9.0), (fa_len - 4.0, -5.2),
        (fa_len + 4.0, 0.0), (fa_len - 4.0, 5.2), (fa_len * 0.35, 9.0), (-3.5, 7.8),
    ]

    out = [f'{ind}<Node name="{prefix}PressArmGroup">']

    # --- Layer 1 (Topmost on Arm): 3D Pronated Dumbbell at Hand ---
    out.append(
        f'{i2}<Node x="{f(p0[hand_key][0])}" y="{f(p0[hand_key][1])}" '
        f'rotation="{f(p0[db_key])}" name="{prefix}DumbbellPivot" id="{db_id}">'
    )
    out.append(pronated_dumbbell_3d(i3, prefix, is_near))
    out.append(f"{i2}</Node>")

    # --- Layer 2: Forearm (elbow -> hand) ---
    out.append(
        f'{i2}<Node x="{f(p0[el_key][0])}" y="{f(p0[el_key][1])}" '
        f'rotation="{f(p0[fa_key])}" scaleX="{f(p0[fa_sc_key])}" name="{prefix}Forearm" id="{fa_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}ForearmGroove", [(5.0, in_sign * 1.0), (fa_len * 0.5, in_sign * 1.4), (fa_len - 6.0, in_sign * 0.8)], 1.2, CORE_SHADOW, 0.7))
    out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(5.0, in_sign * 4.2), (fa_len - 8.0, in_sign * 3.0)], 2.6, HIGHLIGHT, 2.8))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(5.0, out_sign * 4.5), (fa_len - 8.0, out_sign * 3.2)], 3.0, CORE_SHADOW, 2.8))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -9, 9, skin)))
    out.append(f"{i2}</Node>")

    # --- Layer 3: Upper Arm, Glowing Anterior Deltoid & Glowing Triceps Brachii ---
    out.append(
        f'{i2}<Node x="{f(sx)}" y="{f(sy)}" rotation="{f(p0[ua_key])}" scaleX="{f(p0[ua_sc_key])}" name="{prefix}UpperArm" id="{ua_id}">'
    )
    # Deltoid Cap & Target Muscle #2: Anterior Deltoid
    out.append(stroke_shape(i3, f"{prefix}FrontDeltHi", [(0.0, in_sign * 5.5), (11.0, in_sign * 5.0)], 2.0, "66FFFFFF", 1.8))
    out.append(stroke_shape(i3, f"{prefix}DeltFiber", [(-2.0, in_sign * 4.0), (12.0, in_sign * 4.5)], 0.95, "737F1D1D", 0.3))
    out.append(smooth_shape(i3, f"{prefix}FrontDeltActivation", front_delt_pts, muscle_paint_fn(prefix + "FrontDelt", front_delt_t, 0.95)))
    out.append(stroke_shape(i3, f"{prefix}LateralDeltGroove", [(0.0, out_sign * 2.5), (13.0, out_sign * 2.0)], 1.2, CORE_SHADOW, 0.7))
    out.append(smooth_shape(i3, f"{prefix}DeltoidCap", delt_pts, skin_fill(prefix + "Deltoid", -12, 12, skin)))

    # Target Muscle #3: Triceps brachii (Lateral Head + Long Head with dynamic lockout bulge)
    out.append(f'{i3}<Node scaleY="{f(p0["triceps_bulge"])}" name="{prefix}TricepsNode" id="{tri_id}">')
    out.append(stroke_shape(i4, f"{prefix}TricepsHorseshoeGroove", [(14.0, out_sign * 4.8), (ua_len * 0.52, out_sign * 5.5), (ua_len - 7.0, out_sign * 4.5)], 1.1, "807F1D1D", 0.4))
    out.append(stroke_shape(i4, f"{prefix}TricepsHi", [(15.0, out_sign * 3.2), (ua_len - 10.0, out_sign * 3.5)], 1.8, "59FFFFFF", 1.8))
    out.append(smooth_shape(i4, f"{prefix}TricepsLateralHead", triceps_lateral_pts, muscle_paint_fn(prefix + "TricepsLat", triceps_t, 0.95)))
    out.append(smooth_shape(i4, f"{prefix}TricepsLongHead", triceps_long_pts, muscle_paint_fn(prefix + "TricepsLong", triceps_t, 0.9)))
    out.append(f"{i3}</Node>")

    # Biceps / Anterior Upper Arm contour (unhighlighted canonical skin)
    out.append(stroke_shape(i3, f"{prefix}BicepsLine", [(11.0, in_sign * 1.2), (ua_len - 6.0, in_sign * 1.5)], 1.2, SOFT_SHADOW, 0.7))
    out.append(stroke_shape(i3, f"{prefix}UpperArmHi", [(12.0, in_sign * 5.2), (ua_len - 8.0, in_sign * 4.8)], 2.8, HIGHLIGHT, 2.8))
    out.append(stroke_shape(i3, f"{prefix}UpperArmSh", [(10.0, out_sign * 7.5), (ua_len - 8.0, out_sign * 6.0)], 3.4, CORE_SHADOW, 3.0))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UpperArm", -11, 11, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 5. Scene Assembly (RML First Child = Topmost Layer)
def build_rml():
    global _id
    _id = 0
    KEYED.clear()

    near_arm_xml = press_arm_rig("Near", True)
    near_leg_xml = near_left_leg_rig()
    front_arch_xml = front_bench_arch_rig()
    torso_xml = reclined_torso_and_head_rig()
    far_arm_xml = press_arm_rig("Far", False)
    far_leg_xml = far_right_leg_rig()
    bench_xml = incline_bench_rig()

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
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="InclineDumbbellPress" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Left) Press Arm (Anterior Deltoid, Triceps Brachii) & Pronated 3D Dumbbell -->
{near_arm_xml}

        <!-- 2. Mid-Foreground: Near (Left) Leg Planted on FLOOR = 300.0 + Front Bench Stabilizer Arch -->
{near_leg_xml}
{front_arch_xml}

        <!-- 3. Midground: Reclined Canonical Torso, Isolated Glowing Upper Pectoralis Major, 6-Pack Abs & 3/4 Head -->
{torso_xml}

        <!-- 4. Mid-Background: Far (Right) Press Arm & Pronated 3D Dumbbell + Far (Right) Leg -->
{far_arm_xml}
{far_leg_xml}

        <!-- 5. Background Equipment: 3D Isometric Incline Weight Bench -->
{bench_xml}

        <!-- 6. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="292" y="{f(FLOOR - 2)}" scaleX="1.38" scaleY="0.08" name="BenchAndAthleteShadow">
            <Ellipse width="220" height="220" name="ShadowEl"/>
            <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="110" endY="0" name="ShadowGrad">
                <GradientStop colorValue="B3000000" position="0"/>
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="InclineDumbbellPress" id="0:60">
{keyed_objects_xml}
        </LinearAnimation>
    </Artboard>
</Rive>
"""


# ---------------------------------------------------------------- Verbatim Rive 7.3 Binary Compiler (52-byte TOC)
def _compile_rml_bytes(rml_path):
    """Byte-for-byte Rive 7.3 binary compiler matching `~/.rive/bin/rive . --once`."""
    def varuint(v):
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
    riv_out = HERE / "incline_dumbbell_press.riv"
    riv_out.write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    legacy_mk = REPO / "assets/animations/incline_dumbbell_press.movekit"
    if legacy_mk.exists():
        legacy_mk.unlink()

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png

    for fr, tag in ((0, "frame_start"), (38, "frame_mid"), (74, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_start":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(680, 16, 240))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes)} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
