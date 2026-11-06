#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360, FLOOR = 300.0) procedural Rive 7.3 scene for Skull Crusher (id: 'skull_crusher').

Uses our canonical 3/4 CommunityFitness mannequin lying supine on a flat padded weight bench (`y ~ 214`, with steel
legs planted on FLOOR = 300.0 and the athlete's feet planted flat on the floor):
  - Both upper arms remain angled slightly back (`~100 deg` from horizontal, locked at the shoulders) while the
    elbows flex and extend in a true circular arc (`FOREARM_LEN = 44.0`):
    * r = 0.0 (Bottom Stretch): Forearms flex back lowering the loaded barbell just above the forehead/crown.
    * r = 1.0 (Top Lockout): Forearms sweep upward in a pure elbow-extension arc into full lockout above the shoulders.
  - Highlighted Target Muscle Groups (pulsing from warm orange #FFF97316 to intense crimson #FFF43F5E):
    1. Triceps brachii — Long head, Lateral head & Medial head (Primary mover on both upper arms)
    2. Forearm stabilizers — Anconeus & wrist extensors (Secondary stabilizers along the forearm)

Run:
    python3 rive_animations/skull_crusher/gen_skull_crusher.py            # writes scene.rml
    python3 rive_animations/skull_crusher/gen_skull_crusher.py --publish  # compiles .riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/skull_crusher.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/skull_crusher.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps loop
STEP = 2

# Shoulder anchors on the flat bench pad (3/4 front-left view: pelvis on left, head on right)
FAR_SH = (318.0, 178.0)   # Right (far / upper-left) shoulder
NEAR_SH = (356.0, 200.0)  # Left (near / lower-right) shoulder

UA_LEN = 52.0
FA_LEN = 44.0

# Isometric barbell axis matching the 3/4 shoulder/elbow offset (+38, +22 -> ~30.07 deg)
BAR_ANGLE = math.atan2(22.0, 38.0)
BAR_COS = math.cos(BAR_ANGLE)
BAR_SIN = math.sin(BAR_ANGLE)
GRIP_HALF = math.hypot(19.0, 11.0)  # 21.95 px from bar_center to each hand

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


EASE_EXTEND = cubic_bezier(0.35, 0.0, 0.22, 1.0)
EASE_LOWER = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def extension_progress(frame):
    """Returns skull-crusher elbow extension progress r in [0.0, 1.0] across 160 frames:
    - 0..12:   Bottom stretch hold above forehead/crown (r = 0.0)
    - 12..66:  Concentric elbow extension arc upward to lockout (r: 0.0 -> 1.0)
    - 66..84:  Top lockout squeeze hold (r = 1.0)
    - 84..148: Controlled eccentric lowering arc back toward forehead (r: 1.0 -> 0.0)
    - 148..160: Bottom stretch hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 66:
        return EASE_EXTEND((fr - 12) / 54.0)
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
    sc = max(0.50, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute Lying Barbell Skull Crusher transforms at progress r in [0.0, 1.0]:
    - Upper arms stay locked at ~ -78 deg (angled ~12 deg back toward the head from vertical, ~102 deg from torso),
      isolating the elbow joint and maintaining stretch on the long head of the triceps.
    - Forearms hinge in a pure circular arc around the fixed elbows (`fa_deg: +18 deg -> -78 deg`), carrying the
      barbell from just above the forehead (`(389, 151)`) at r = 0.0 up to full lockout (`(355, 94)`) at r = 1.0.
    """
    ua_deg = lerp(-76.5, -79.5, r)
    ua_rad = math.radians(ua_deg)

    far_el = (
        FAR_SH[0] + UA_LEN * math.cos(ua_rad),
        FAR_SH[1] + UA_LEN * math.sin(ua_rad),
    )
    near_el = (
        NEAR_SH[0] + UA_LEN * math.cos(ua_rad),
        NEAR_SH[1] + UA_LEN * math.sin(ua_rad),
    )

    # Pure circular elbow extension arc: +18 deg (lowered back over forehead) -> -78 deg (extended overhead)
    fa_deg = lerp(18.0, -78.0, r)
    fa_rad = math.radians(fa_deg)

    far_hand = (
        far_el[0] + FA_LEN * math.cos(fa_rad),
        far_el[1] + FA_LEN * math.sin(fa_rad),
    )
    near_hand = (
        near_el[0] + FA_LEN * math.cos(fa_rad),
        near_el[1] + FA_LEN * math.sin(fa_rad),
    )
    bar_center = (
        0.5 * (far_hand[0] + near_hand[0]),
        0.5 * (far_hand[1] + near_hand[1]),
    )

    ua_far_ang, ua_far_sc = seg_xform(FAR_SH, far_el, UA_LEN)
    fa_far_ang, fa_far_sc = seg_xform(far_el, far_hand, FA_LEN)
    ua_near_ang, ua_near_sc = seg_xform(NEAR_SH, near_el, UA_LEN)
    fa_near_ang, fa_near_sc = seg_xform(near_el, near_hand, FA_LEN)

    delt_far_ang = math.radians(lerp(-74.0, -78.0, r))
    delt_near_ang = math.radians(lerp(-74.0, -78.0, r))

    return {
        "r": r,
        "bar_center": bar_center,
        "far_el": far_el,
        "near_el": near_el,
        "far_hand": far_hand,
        "near_hand": near_hand,
        "ua_far_ang": ua_far_ang,
        "ua_far_sc": ua_far_sc,
        "fa_far_ang": fa_far_ang,
        "fa_far_sc": fa_far_sc,
        "ua_near_ang": ua_near_ang,
        "ua_near_sc": ua_near_sc,
        "fa_near_ang": fa_near_ang,
        "fa_near_sc": fa_near_sc,
        "delt_far_ang": delt_far_ang,
        "delt_near_ang": delt_near_ang,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(extension_progress(fr)) for fr in FRAMES}

_ANGLE_KEYS = (
    "ua_far_ang",
    "fa_far_ang",
    "ua_near_ang",
    "fa_near_ang",
    "delt_far_ang",
    "delt_near_ang",
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


# ---------------------------------------------------------------- 1. 3D Flat Weight Bench on FLOOR = 300.0
def build_flat_bench():
    """3/4 perspective flat padded weight bench (`y ~ 202..226`) with white/silver steel legs planted on FLOOR = 300.0."""
    ind = "        "
    i2 = ind + "    "

    steel_top = (
        f'<Fill name="SteelTopFill">{grad("SteelTopGrad", 220, 210, 420, 300, "FFF8FAFC", "FFCBD5E1")}</Fill>'
        '<Stroke thickness="1.0" join="round" name="SteelTopStroke"><SolidColor colorValue="FF64748B" name="SteelTopCol"/></Stroke>'
    )
    steel_side = (
        f'<Fill name="SteelSideFill">{grad("SteelSideGrad", 220, 210, 420, 300, "FFCBD5E1", "FF64748B")}</Fill>'
        '<Stroke thickness="1.0" join="round" name="SteelSideStroke"><SolidColor colorValue="FF475569" name="SteelSideCol"/></Stroke>'
    )
    pad_top = (
        f'<Fill name="PadTopFill">{grad("PadTopGrad", 230, 192, 415, 224, "FF334155", "FF1E293B")}</Fill>'
        '<Stroke thickness="1.2" join="round" name="PadTopStroke"><SolidColor colorValue="FF0F172A" name="PadTopCol"/></Stroke>'
    )
    pad_side = (
        f'<Fill name="PadSideFill">{grad("PadSideGrad", 230, 206, 415, 236, "FF1E293B", "FF090D16")}</Fill>'
        '<Stroke thickness="1.1" join="round" name="PadSideStroke"><SolidColor colorValue="FF020617" name="PadSideCol"/></Stroke>'
    )
    rubber_foot = solid("RubberFoot", "FF0F172A")

    return "\n".join([
        f'{ind}<Node name="FlatWeightBench">',
        # 1. Upholstered Flat Bench Pad (3/4 top face + front skirt + right end cap)
        stroke_shape(i2, "PadEdgeSeam", [(234, 206), (318, 216), (398, 226)], 1.4, "4DFFFFFF", 0.5),
        poly_shape(i2, "BenchPadTop", [(230, 204), (258, 190), (420, 210), (396, 224)], pad_top, radius=4.5),
        poly_shape(i2, "BenchPadFrontSkirt", [(230, 204), (396, 224), (396, 236), (230, 216)], pad_side, radius=3.5),
        poly_shape(i2, "BenchPadRightEnd", [(396, 224), (420, 210), (420, 222), (396, 236)], pad_side, radius=3.0),
        # 2. Steel Under-Frame, Vertical Bench Legs & Floor Stabilizers on FLOOR = 300.0
        # Left (hip-end) vertical steel post descending to FLOOR = 300.0
        poly_shape(i2, "LeftPostFront", [(256, 216), (268, 218), (268, 294), (256, 292)], steel_top, radius=1.5),
        poly_shape(i2, "LeftPostSide", [(248, 214), (256, 216), (256, 292), (248, 290)], steel_side, radius=1.5),
        poly_shape(i2, "LeftBaseFoot", [(236, 290), (282, 294), (280, 300), (234, 296)], rubber_foot, radius=2.0),
        # Right (head-end) vertical steel post descending to FLOOR = 300.0
        poly_shape(i2, "RightPostFront", [(380, 232), (392, 234), (392, 294), (380, 292)], steel_top, radius=1.5),
        poly_shape(i2, "RightPostSide", [(372, 230), (380, 232), (380, 292), (372, 290)], steel_side, radius=1.5),
        poly_shape(i2, "RightBaseFoot", [(362, 290), (408, 294), (406, 300), (360, 296)], rubber_foot, radius=2.0),
        # Horizontal lower steel tie-bar & upper spine rail connecting the two legs
        poly_shape(i2, "UnderPadSpine", [(256, 216), (384, 232), (384, 240), (256, 224)], steel_side, radius=1.5),
        poly_shape(i2, "FloorTieRailTop", [(262, 282), (384, 284), (384, 290), (262, 288)], steel_top, radius=1.5),
        poly_shape(i2, "FloorTieRailSide", [(262, 288), (384, 290), (384, 295), (262, 293)], steel_side, radius=1.5),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 2. Planted Straddled Legs (Feet Flat on Floor)
def build_far_right_leg():
    """Far (Right) leg straddling the back side of the bench with foot planted flat in 3/4 depth."""
    ind = "        "
    i2 = ind + "    "
    shorts_pts = [(266, 178), (236, 176), (220, 182), (226, 206), (260, 202)]
    thigh_pts = [
        (254, 180), (224, 179), (198, 188), (186, 202),
        (192, 218), (216, 214), (244, 206), (258, 198),
    ]
    shin_pts = [
        (186, 208), (188, 232), (194, 256), (198, 272),
        (208, 270), (210, 246), (208, 222), (198, 206),
    ]
    foot_pts = [
        (196, 268), (174, 270), (158, 275), (160, 281),
        (182, 281), (208, 278), (210, 270),
    ]
    return "\n".join([
        f'{ind}<Node name="FarRightLeg">',
        smooth_shape(i2, "FarFoot", foot_pts, skin_fill_outlined("FarFoot", 268, 281, SKIN_FAR, line=1.05)),
        smooth_shape(i2, "FarShin", shin_pts, skin_fill_outlined("FarShin", 206, 272, SKIN_FAR, line=1.05)),
        ellipse_shape(i2, "FarKneeCap", 190, 208, 14, 14, skin_fill_outlined("FarKnee", -7, 7, SKIN_FAR, line=0.95)),
        smooth_shape(i2, "FarThighShorts", shorts_pts, skin_fill_outlined("FarShorts", 176, 206, SHORTS_FAR, line=1.1)),
        stroke_shape(i2, "FarThighHi", [(238, 184), (214, 188), (194, 198)], 3.0, HIGHLIGHT, 2.8),
        smooth_shape(i2, "FarThigh", thigh_pts, skin_fill_outlined("FarThigh", 179, 218, SKIN_FAR, line=1.1)),
        f"{ind}</Node>",
    ])


def build_near_left_leg():
    """Near (Left) foreground leg straddling the bench with bare foot planted flat on FLOOR = 300.0."""
    ind = "        "
    i2 = ind + "    "
    shorts_pts = [(266, 190), (298, 196), (296, 218), (274, 226), (252, 212)]
    thigh_pts = [
        (266, 196), (292, 206), (282, 226), (262, 240),
        (240, 242), (232, 228), (244, 210),
    ]
    shin_pts = [
        (232, 232), (252, 234), (254, 256), (248, 276),
        (244, 292), (230, 292), (230, 270), (230, 248),
    ]
    foot_pts = [
        (230, 288), (246, 288), (246, 298), (236, 300),
        (206, 300), (204, 294), (218, 290),
    ]
    return "\n".join([
        f'{ind}<Node name="NearLeftLeg">',
        stroke_shape(i2, "NearFootHi", [(212, 294), (228, 291), (240, 291)], 2.0, HIGHLIGHT, 2.0),
        smooth_shape(i2, "NearFoot", foot_pts, skin_fill_outlined("NearFoot", 288, 300, SKIN, line=1.15)),
        stroke_shape(i2, "NearTibialisLine", [(238, 244), (237, 266), (236, 286)], 1.3, SOFT_SHADOW, 0.6),
        stroke_shape(i2, "NearShinHi", [(235, 244), (234, 266), (234, 286)], 2.6, HIGHLIGHT, 2.6),
        stroke_shape(i2, "NearCalfSh", [(248, 248), (248, 268), (243, 286)], 3.2, CORE_SHADOW, 3.0),
        smooth_shape(i2, "NearShin", shin_pts, skin_fill_outlined("NearShin", 232, 292, SKIN, line=1.15)),
        ellipse_shape(i2, "NearKneeCap", 240, 235, 16, 15, skin_fill_outlined("NearKnee", -8, 8, SKIN, line=1.0)),
        smooth_shape(i2, "NearThighShorts", shorts_pts, skin_fill_outlined("NearShorts", 190, 226, SHORTS, line=1.15)),
        stroke_shape(i2, "NearQuadCrease", [(272, 206), (256, 220), (244, 230)], 1.3, SOFT_SHADOW, 0.6),
        stroke_shape(i2, "NearThighHi", [(272, 204), (256, 218), (242, 228)], 3.6, HIGHLIGHT, 3.2),
        stroke_shape(i2, "NearThighSh", [(282, 218), (266, 232), (250, 238)], 4.0, CORE_SHADOW, 3.6),
        smooth_shape(i2, "NearThigh", thigh_pts, skin_fill_outlined("NearThigh", 196, 242, SKIN, line=1.15)),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 3. Supine Torso, 6-Pack Abs, Pectorals & Volumetric 3/4 Head
def build_supine_torso_and_head():
    """Supine torso resting on the flat bench pad (`x ~ 256..368, y ~ 170..216`) with 6-pack abs, sculpted pectorals,
    and volumetric 3/4 supine head (`x ~ 368..406, y ~ 174..208`) looking up at the ceiling."""
    ind = "        "
    i2 = ind + "    "

    pelvis_shorts = [(242, 184), (268, 180), (294, 194), (290, 218), (262, 220), (238, 202)]
    torso_pts = [
        (262, 182), (288, 174), (316, 172), (344, 176),
        (364, 188), (366, 206), (346, 218), (318, 218),
        (290, 216), (264, 210),
    ]

    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="220F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.95" join="round" name="AbsEdge"><SolidColor colorValue="4D0F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        [(306, 179), (318, 178), (320, 186), (308, 187)],
        [(291, 180), (303, 179), (305, 187), (293, 188)],
        [(276, 182), (288, 180), (290, 188), (278, 190)],
        [(309, 189), (321, 188), (323, 196), (311, 197)],
        [(294, 190), (306, 189), (308, 197), (296, 198)],
        [(279, 192), (291, 190), (293, 198), (281, 200)],
    ]

    pec_paint = (
        f'<Fill name="PecFill">{grad3("PecGrad", 172, 210, "FFF8FAFC", "FFDCE4EE", "FFA3B1C4")}</Fill>'
        '<Stroke thickness="1.1" join="round" name="PecStroke"><SolidColor colorValue="4D0F172A" name="PecStrokeCol"/></Stroke>'
    )
    pec_far_pts = [(316, 176), (332, 173), (348, 178), (346, 189), (330, 189), (318, 185)]
    pec_near_pts = [(326, 189), (346, 188), (362, 196), (356, 210), (336, 210), (322, 200)]

    neck_pts = [(352, 186), (368, 182), (376, 196), (358, 204)]
    head_pts = [
        (366, 184),  # anterior throat / under-chin
        (369, 174),  # sculpted chin tip pointing up
        (376, 172),  # lips
        (384, 170),  # sculpted nose tip projecting upward (clear beneath the bottom bar position at y=151!)
        (391, 173),  # brow ridge / forehead
        (400, 177),  # anterior hairline / crown
        (406, 186),  # posterior cranium
        (404, 198),  # occiput resting on bench pad
        (394, 205),  # lower skull behind ear
        (382, 205),  # jaw angle
        (372, 198),  # mandible
    ]
    hair_pts = [
        (392, 173), (401, 176), (407, 185), (405, 198),
        (396, 203), (396, 194), (394, 184), (389, 178),
    ]
    hair_paint = (
        f'<Fill name="HairFill">{grad("HairGrad", 389, 173, 407, 203, "FF334155", "FF0F172A")}</Fill>'
        '<Stroke thickness="0.95" join="round" name="HairStroke"><SolidColor colorValue="FF090D16" name="HairStrokeCol"/></Stroke>'
    )

    out = [f'{ind}<Node name="SupineTorsoAndHead">']

    # 1. Volumetric 3/4 Supine Head & Neck
    out.append(smooth_shape(i2, "HairCap", hair_pts, hair_paint))
    out.append(ellipse_shape(i2, "LeftEar", 388, 197, 6.8, 4.8, skin_fill_outlined("Ear", -3, 3, SKIN, line=0.85), rot_deg=-12.0))
    out.append(stroke_shape(i2, "Eyebrow", [(388, 175), (392, 177)], 1.3, "730F172A", 0.3))
    out.append(stroke_shape(i2, "EyeLine", [(386, 177), (390, 178)], 1.05, "800F172A", 0.2))
    out.append(stroke_shape(i2, "HeadHi", [(374, 175), (385, 172), (395, 176)], 2.6, HIGHLIGHT, 2.5))
    out.append(stroke_shape(i2, "JawLine", [(370, 186), (378, 194), (386, 196)], 1.5, CORE_SHADOW, 1.3))
    out.append(smooth_shape(i2, "HeadShape", head_pts, skin_fill_outlined("Head", 170, 205, SKIN, line=1.1)))
    out.append(smooth_shape(i2, "NeckShape", neck_pts, skin_fill_outlined("Neck", 182, 204, SKIN_FAR, line=1.0)))

    # 2. Sculpted Pectoralis Major & 6-Pack Rectus Abdominis
    out.append(stroke_shape(i2, "PecHi", [(330, 194), (344, 194), (354, 199)], 2.4, HIGHLIGHT, 2.4))
    out.append(smooth_shape(i2, "PecNearLeft", pec_near_pts, pec_paint))
    out.append(smooth_shape(i2, "PecFarRight", pec_far_pts, pec_paint))
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "LineaAlba", [(322, 187), (298, 188), (274, 190)], 1.3, SOFT_SHADOW, 0.4))
    out.append(stroke_shape(i2, "Serratus1", [(320, 204), (310, 201)], 1.2, SOFT_SHADOW, 0.3))
    out.append(stroke_shape(i2, "Serratus2", [(306, 206), (296, 203)], 1.2, SOFT_SHADOW, 0.3))

    # 3. Pelvis Shorts & Supine Torso Silhouette
    out.append(stroke_shape(i2, "ShortsWaistband", [(266, 182), (274, 198), (276, 216)], 2.0, "CC020617", 0.0))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill_outlined("PelvisShorts", 180, 220, SHORTS, line=1.15)))
    out.append(stroke_shape(i2, "TorsoHi", [(276, 180), (304, 176), (332, 178)], 3.8, HIGHLIGHT, 3.8))
    out.append(stroke_shape(i2, "TorsoSh", [(346, 212), (314, 214), (280, 210)], 4.8, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i2, "TorsoSilhouette", torso_pts, skin_fill_outlined("Torso", 172, 218, SKIN, line=1.15)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 4. Skull-Crusher Arms (Glowing 3-Head Triceps Brachii & Forearm Stabilizers)
def build_skull_crusher_arm(prefix, far):
    """Locked Upper Arm (~100 deg) with sculpted Long, Lateral & Medial heads of Triceps Brachii,
    and hinging Forearm with highlighted Anconeus / Forearm Stabilizers."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    sh_pt = FAR_SH if far else NEAR_SH
    el_k = "far_el" if far else "near_el"
    ua_ang_k = "ua_far_ang" if far else "ua_near_ang"
    ua_sc_k = "ua_far_sc" if far else "ua_near_sc"
    fa_ang_k = "fa_far_ang" if far else "fa_near_ang"
    fa_sc_k = "fa_far_sc" if far else "fa_near_sc"
    delt_ang_k = "delt_far_ang" if far else "delt_near_ang"
    m_scale = 0.90 if far else 1.00

    ua_id, fa_id, delt_id = nid(), nid(), nid()
    key_double(ua_id, 15, lambda p: p[ua_ang_k])
    key_double(ua_id, 16, lambda p: p[ua_sc_k])

    key_double(fa_id, 13, lambda p: p[el_k][0])
    key_double(fa_id, 14, lambda p: p[el_k][1])
    key_double(fa_id, 15, lambda p: p[fa_ang_k])
    key_double(fa_id, 16, lambda p: p[fa_sc_k])

    key_double(delt_id, 15, lambda p: p[delt_ang_k])
    p0 = POSES[0]

    def tri_long_t(p):
        return (0.46 + 0.54 * (p["r"] ** 0.76)) * m_scale

    def tri_lat_t(p):
        return (0.44 + 0.56 * (p["r"] ** 0.78)) * m_scale

    def forearm_stab_t(p):
        return (0.38 + 0.50 * (p["r"] ** 0.82)) * m_scale

    # In local UpperArm frame (+X points from Shoulder (0,0) up toward Elbow (52,0) at ~ -78 deg):
    # +Y points screen-right (posterior/triceps side facing the head/barbell arc!).
    # -Y points screen-left (anterior/biceps side facing the torso/legs).
    ua_pts = [
        (-8, 0), (-5, -10.2), (10, -11.2), (28, -10.5), (44, -7.8),
        (55, 0), (46, 8.5), (30, 11.8), (12, 12.2), (-5, 9.5),
    ]
    # Primary Target Muscle #1: Triceps Brachii (Long Head along posterior +Y border + Lateral/Medial Heads)
    triceps_long_pts = [
        (3, 3.2), (18, 4.0), (34, 3.8), (46, 3.0),
        (45, 8.2), (30, 11.6), (13, 12.0), (2, 8.8),
    ]
    triceps_lat_med_pts = [
        (8, -2.5), (24, -2.8), (40, -1.8), (48, 2.5),
        (36, 5.2), (20, 5.2), (7, 3.0),
    ]

    delt_pts = [
        (-12, 0), (-7, -11.5), (5, -12.5), (16, -8.5), (19, 0),
        (16, 9.0), (5, 12.0), (-7, 10.5),
    ]

    fa_pts = [
        (-6, 0), (-3, -7.5), (12, -8.6), (28, -6.8), (39, -4.8),
        (46, 0), (39, 5.2), (28, 7.0), (12, 8.2), (-3, 6.8),
    ]
    # Secondary Target Muscle #2: Forearm Stabilizers (Anconeus & Extensor Carpi Ulnaris along posterior forearm)
    fa_stab_pts = [
        (-2, 0.8), (12, 1.2), (28, 1.5), (27, 6.2), (12, 7.8), (-2, 5.8),
    ]
    hand_pts = [
        (-4, -6.2), (5, -6.8), (10, -2.5), (10, 4.2), (4, 6.5), (-4, 5.5),
    ]

    return "\n".join([
        f'{ind}<Node name="{prefix}SkullCrusherArm">',
        # 1. Shoulder Deltoid Cap
        f'{i2}<Node x="{f(sh_pt[0])}" y="{f(sh_pt[1])}" rotation="{f(p0[delt_ang_k])}" name="{prefix}DeltoidCap" id="{delt_id}">',
        stroke_shape(i3, f"{prefix}DeltHi", [(-4, -6), (5, -6), (12, -2)], 2.4, HIGHLIGHT, 2.4),
        smooth_shape(i3, f"{prefix}DeltoidBase", delt_pts, skin_fill_outlined(prefix + "Delt", -12, 12, skin, line=1.1)),
        f"{i2}</Node>",

        # 2. Locked Upper Arm with Glowing 3-Head Triceps Brachii Horseshoe
        f'{i2}<Node x="{f(sh_pt[0])}" y="{f(sh_pt[1])}" rotation="{f(p0[ua_ang_k])}" scaleX="{f(p0[ua_sc_k])}" name="{prefix}UpperArm" id="{ua_id}">',
        stroke_shape(i3, f"{prefix}TricepsHorseshoeSplit", [(10, 3.8), (26, 4.5), (42, 3.2)], 1.25, "997F1D1D", 0.3),
        stroke_shape(i3, f"{prefix}TricepsLongFiber", [(12, 8.2), (26, 8.8), (39, 7.0)], 1.05, "737F1D1D", 0.3),
        stroke_shape(i3, f"{prefix}TricepsLatFiber", [(14, 0.8), (28, 1.0), (40, 1.2)], 1.0, "737F1D1D", 0.3),
        stroke_shape(i3, f"{prefix}TricepsSpecHi", [(14, 7.8), (28, 8.2), (40, 6.5)], 2.0, "66FFFFFF", 1.8),
        smooth_shape(i3, f"{prefix}TricepsLongHead", triceps_long_pts, muscle_paint_fn(prefix + "TriLong", tri_long_t, 1.1)),
        smooth_shape(i3, f"{prefix}TricepsLatMedHead", triceps_lat_med_pts, muscle_paint_fn(prefix + "TriLat", tri_lat_t, 1.05)),
        stroke_shape(i3, f"{prefix}BicepsAntHi", [(8, -6.5), (24, -6.5), (38, -4.8)], 2.4, HIGHLIGHT, 2.5),
        smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill_outlined(prefix + "UA", -11, 12, skin, line=1.15)),
        f"{i2}</Node>",

        # 3. Hinging Forearm & Hand with Highlighted Anconeus / Forearm Stabilizers
        f'{i2}<Node x="{f(p0[el_k][0])}" y="{f(p0[el_k][1])}" rotation="{f(p0[fa_ang_k])}" scaleX="{f(p0[fa_sc_k])}" name="{prefix}Forearm" id="{fa_id}">',
        smooth_shape(i3, f"{prefix}Hand", hand_pts, skin_fill_outlined(prefix + "Hand", -7, 7, skin, line=1.1), x=FA_LEN - 2.0),
        stroke_shape(i3, f"{prefix}ForearmStabLine", [(2, 4.2), (14, 4.6), (24, 4.0)], 1.0, "737F1D1D", 0.3),
        smooth_shape(i3, f"{prefix}ForearmStabilizer", fa_stab_pts, muscle_paint_fn(prefix + "FAStab", forearm_stab_t, 0.95)),
        stroke_shape(i3, f"{prefix}ForearmHi", [(6, -4.2), (20, -3.8), (34, -2.5)], 2.2, HIGHLIGHT, 2.2),
        smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill_outlined(prefix + "FA", -9, 8, skin, line=1.15)),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 5. 3D Loaded Barbell / EZ-Bar with Weight Plates & Finger Wraps
def build_barbell_rig():
    """Animated 3D Barbell with dark cast-iron plates, chrome sleeves, shaft, and pronated finger wraps."""
    ind = "        "
    i2 = ind + "    "
    bar_id = nid()
    key_double(bar_id, 13, lambda p: p["bar_center"][0])
    key_double(bar_id, 14, lambda p: p["bar_center"][1])
    p0 = POSES[0]

    ux, uy = BAR_COS, BAR_SIN
    nx, ny = -BAR_SIN, BAR_COS

    def bar_pt(along, perp=0.0):
        return (along * ux + perp * nx, along * uy + perp * ny)

    plate_rot_deg = math.degrees(BAR_ANGLE)
    plate_face_near = (
        f'<Fill name="NearPlateFaceFill">{grad3("NearPlateFaceGrad", -28, 28, "FF334155", "FF182232", "FF090D16", x0=-16, x1=16)}</Fill>'
        '<Stroke thickness="1.4" join="round" name="NearPlateRimStroke"><SolidColor colorValue="FF475569" name="NearPlateRimCol"/></Stroke>'
    )
    plate_face_far = (
        f'<Fill name="FarPlateFaceFill">{grad3("FarPlateFaceGrad", -26, 26, "FF263244", "FF111827", "FF060911", x0=-14, x1=14)}</Fill>'
        '<Stroke thickness="1.3" join="round" name="FarPlateRimStroke"><SolidColor colorValue="FF334155" name="FarPlateRimCol"/></Stroke>'
    )
    plate_rim_paint = f'<Fill name="PlateBackFill">{grad("PlateBackGrad", -18, -28, 18, 28, "FF0F172A", "FF020617")}</Fill>'
    plate_ring_paint = (
        '<Fill name="PlateRingFill"><SolidColor colorValue="FF111827" name="PlateRingCol"/></Fill>'
        '<Stroke thickness="1.1" join="round" name="PlateRingStroke"><SolidColor colorValue="FF334155" name="PlateRingStrokeCol"/></Stroke>'
    )
    hub_paint = (
        f'<Fill name="BarHubFill">{grad3("BarHubGrad", -6, 6, "FF94A3B8", "FF475569", "FF1E293B")}</Fill>'
        '<Stroke thickness="1.0" join="round" name="BarHubStroke"><SolidColor colorValue="FFCBD5E1" name="BarHubStrokeCol"/></Stroke>'
    )

    # Compact EZ/Tricep Barbell plate spacing (+/- 58 px along bar axis, clear of head at bottom stretch!)
    npx, npy = bar_pt(58.0)
    nbx, nby = bar_pt(55.0)
    npw, nph = 26.0, 48.0

    fpx, fpy = bar_pt(-58.0)
    fbx, fby = bar_pt(-61.0)
    fpw, fph = 24.0, 45.0

    gf = bar_pt(-GRIP_HALF)
    gn = bar_pt(GRIP_HALF)

    return "\n".join([
        f'{ind}<Node x="{f(p0["bar_center"][0])}" y="{f(p0["bar_center"][1])}" name="BarbellGroup" id="{bar_id}">',
        # 1. Near (bottom-right) outer sleeve & 25-lb plate (in front of shaft)
        ellipse_shape(i2, "NearSleeveEndCap", *bar_pt(82.0), 4.0, 6.0, solid("NearSleeveCap", "FF0F172A"), rot_deg=plate_rot_deg),
        stroke_shape(i2, "NearSleeveOuter", [bar_pt(58.0), bar_pt(82.0)], 6.4, "FF94A3B8", 0.0, cap="round"),
        stroke_shape(i2, "NearSleeveHi", [bar_pt(59.0, -1.0), bar_pt(80.0, -1.0)], 1.8, "FFE2E8F0", 0.2, cap="round"),
        ellipse_shape(i2, "NearPlateHub", npx, npy, 8.0, 12.5, hub_paint, rot_deg=plate_rot_deg),
        ellipse_shape(i2, "NearPlateInnerRing", npx, npy, npw * 0.70, nph * 0.70, plate_ring_paint, rot_deg=plate_rot_deg),
        ellipse_shape(i2, "NearPlateFace", npx, npy, npw, nph, plate_face_near, rot_deg=plate_rot_deg),
        ellipse_shape(i2, "NearPlateRim3D", nbx, nby, npw, nph, plate_rim_paint, rot_deg=plate_rot_deg),
        ellipse_shape(i2, "NearInnerCollar", *bar_pt(51.0), 6.5, 10.2, hub_paint, rot_deg=plate_rot_deg),

        # 2. Pronated finger knuckles wrapping over the barbell shaft at both hands
        ellipse_shape(i2, "NearFingerWrap", gn[0], gn[1], 13.0, 9.5, skin_fill_outlined("NearWrap", -5, 5, SKIN, line=1.0), rot_deg=plate_rot_deg),
        ellipse_shape(i2, "FarFingerWrap", gf[0], gf[1], 12.2, 9.0, skin_fill_outlined("FarWrap", -5, 5, SKIN_FAR, line=0.95), rot_deg=plate_rot_deg),

        # 3. Main chrome barbell shaft (-54 .. +54)
        stroke_shape(i2, "BarShaftHi", [bar_pt(-52.0, -1.0), bar_pt(0.0, -1.0), bar_pt(52.0, -1.0)], 1.4, "FFFFFFFF", 0.2, cap="butt"),
        stroke_shape(i2, "BarShaftCore", [bar_pt(-54.0), bar_pt(0.0), bar_pt(54.0)], 4.0, "FFCBD5E1", 0.0, cap="butt"),
        stroke_shape(i2, "BarShaftShadow", [bar_pt(-54.0), bar_pt(0.0), bar_pt(54.0)], 5.4, "FF334155", 0.0, cap="butt"),

        # 4. Far (top-left) 25-lb plate & outer sleeve (behind main shaft)
        ellipse_shape(i2, "FarInnerCollar", *bar_pt(-51.0), 6.2, 9.8, hub_paint, rot_deg=plate_rot_deg),
        ellipse_shape(i2, "FarPlateHub", fpx, fpy, 7.5, 11.8, hub_paint, rot_deg=plate_rot_deg),
        ellipse_shape(i2, "FarPlateInnerRing", fpx, fpy, fpw * 0.70, fph * 0.70, plate_ring_paint, rot_deg=plate_rot_deg),
        ellipse_shape(i2, "FarPlateFace", fpx, fpy, fpw, fph, plate_face_far, rot_deg=plate_rot_deg),
        ellipse_shape(i2, "FarPlateRim3D", fbx, fby, fpw, fph, plate_rim_paint, rot_deg=plate_rot_deg),
        stroke_shape(i2, "FarSleeveHi", [bar_pt(-59.0, -0.9), bar_pt(-78.0, -0.9)], 1.6, "FFE2E8F0", 0.2, cap="round"),
        stroke_shape(i2, "FarSleeveOuter", [bar_pt(-58.0), bar_pt(-80.0)], 5.8, "FF94A3B8", 0.0, cap="round"),
        f"{ind}</Node>",
    ])


def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    bench_xml = build_flat_bench()
    far_leg_xml = build_far_right_leg()
    near_leg_xml = build_near_left_leg()
    torso_xml = build_supine_torso_and_head()
    far_arm_xml = build_skull_crusher_arm("Far", True)
    near_arm_xml = build_skull_crusher_arm("Near", False)
    barbell_xml = build_barbell_rig()

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
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="SkullCrusher" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Left) Arm with Glowing 3-Head Triceps Brachii & Forearm Stabilizers -->
{near_arm_xml}

        <!-- 2. Loaded Tricep Barbell / EZ-Bar & Finger Wraps -->
{barbell_xml}

        <!-- 3. Near (Left) Straddled Leg Planted on FLOOR = 300.0 -->
{near_leg_xml}

        <!-- 4. Supine Torso, 6-Pack Abs, Pectorals & Volumetric 3/4 Head -->
{torso_xml}

        <!-- 5. Far (Right) Arm with Glowing Triceps Brachii -->
{far_arm_xml}

        <!-- 6. Flat Upholstered Weight Bench & Steel Frame on FLOOR = 300.0 -->
{bench_xml}

        <!-- 7. Far (Right) Straddled Leg in 3/4 Depth -->
{far_leg_xml}

        <!-- 8. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="312" y="295" scaleX="1.55" scaleY="0.09" name="BenchFloorShadow">
            <Ellipse width="260" height="220" name="BenchShadowEllipse"/>
            <Fill name="BenchShadowFill"><RadialGradient startX="0" startY="0" endX="130" endY="0" name="BenchShadowGrad">
                <GradientStop colorValue="CC000000" position="0"/>
                <GradientStop colorValue="59000000" position="0.62"/>
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="SkullCrusher" id="0:60">
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
    (BUILD / "skull_crusher.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/aff6e669-980f-4ec0-a386-c5be528dd2f8/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (38, "frame_mid"), (74, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(620, 40, 310))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
