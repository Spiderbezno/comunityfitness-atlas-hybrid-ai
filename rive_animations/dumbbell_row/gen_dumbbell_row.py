#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive scene for One-Arm Dumbbell Row (id: 'dumbbell_row').

Matches the 2-panel 3/4 front-left One-Arm Dumbbell Row reference illustration:
  - Left Panel (Bottom Stretch, r = 0.0):
    * Right hand planted flat on the front-left of the bench pad (FAR_HAND = (218, 206)), right knee & shin
      kneeling on the rear-right of the bench pad (FAR_KNEE = (312, 194)), left leg standing planted on the floor
      (NEAR_FOOT = (376, 294) on FLOOR = 300.0).
    * Working left arm extended straight down beside the bench (NEAR_SH = (284, 122) -> NEAR_EL = (280, 174) ->
      NEAR_HAND = (276, 224)) holding a heavy 3D double-plate dumbbell in neutral grip.
  - Right Panel (Top Contraction, r = 1.0):
    * Left shoulder retracts slightly upward-right (NEAR_SH = (290, 110)), left elbow drives high above the back
      (NEAR_EL = (336, 96)), and the heavy 3D dumbbell is pulled tight beside the lateral ribcage/hip
      (NEAR_HAND = (324, 152)), exposing the sculpted Pectoralis major underneath the chest.
  - All 8 Labeled Target Muscle Groups (pulsing from warm orange #FFF97316 at r = 0.0 to vivid crimson #FFF43F5E at r = 1.0):
    1. Latissimus dorsi (scale = 1.00 — Primary Mover!)
    2. Teres major (scale = 0.96)
    3. Teres minor (scale = 0.90)
    4. Infraspinatus (scale = 0.90)
    5. Trapezius (middle and lower) (scale = 0.88)
    6. Posterior deltoid (scale = 0.95)
    7. Brachialis (scale = 0.90)
    8. Brachioradialis (scale = 0.90)
    + Synergist Pectoralis major (scale = 0.68, warm chest plate exposed under the arm as the elbow rows high)

Run:
    python3 gen_dumbbell_row.py            # writes scene.rml
    python3 gen_dumbbell_row.py --publish  # compiles assets/animations/dumbbell_row.riv + 256x256 thumbnail
"""
import math
import pathlib
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "scene.rml"
BUILD = HERE / "build"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps loop
STEP = 2

# Stationary 3-Point Support Anchors (Planted Right Hand on Bench, Kneeling Right Knee on Bench, Standing Left Foot on Floor)
FAR_HAND = (218.0, 206.0)
FAR_KNEE = (312.0, 194.0)
FAR_ANKLE = (358.0, 190.0)
NEAR_HIP = (368.0, 148.0)
NEAR_KNEE = (368.0, 214.0)
NEAR_ANKLE = (376.0, 282.0)

# Base rest lengths for 3D-foreshortened sibling-node arm segments
UA_FAR_LEN, FA_FAR_LEN = 42.0, 40.0
UA_NEAR_LEN, FA_NEAR_LEN = 50.0, 52.0

# Palette — matches existing 16:9 procedural catalog (decline_bench_press, dips, concentration_curl, deadlift)
SKIN = ("FFF8FAFC", "FFCBD5E1", "FF64748B")
SKIN_FAR = ("FFE2E8F0", "FF94A3B8", "FF475569")
SHORTS = ("FF334155", "FF1E293B", "FF0F172A")
FRAME_WHITE = ("FFFFFFFF", "FFE2E8F0", "FF94A3B8")
FRAME_FAR = ("FFF1F5F9", "FFCBD5E1", "FF64748B")
PAD_DARK = ("FF334155", "FF1E293B", "FF090D16")
PLATE_DARK = ("FF334155", "FF182232", "FF090D16")
ANATOMY_LINE = "66475569"
OUTLINE = "990F172A"
HIGHLIGHT = "59FFFFFF"
CORE_SHADOW = "400F172A"

# Muscle activation colors: warm orange (#FFF97316) at Bottom Stretch (r=0.0) -> intense crimson (#FFF43F5E) at Top Contraction (r=1.0)
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


EASE_ROW = cubic_bezier(0.36, 0.0, 0.24, 1.0)
EASE_LOWER = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def row_progress(frame):
    """Returns dumbbell row progress r in [0.0, 1.0] across 160 frames:
    - 0..12:   Bottom Stretch hold (r = 0.0, Left panel)
    - 12..64:  Concentric row pulling elbow high above the back (r: 0.0 -> 1.0)
    - 64..84:  Top Contraction hold (r = 1.0, Right panel)
    - 84..148: Controlled eccentric lowering back to full stretch (r: 1.0 -> 0.0)
    - 148..160: Bottom Stretch hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 64:
        return EASE_ROW((fr - 12) / 52.0)
    if fr <= 84:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_LOWER((fr - 84) / 64.0)
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
    if ang < 0:
        ang += 2.0 * math.pi
    sc = max(0.45, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute One-Arm Dumbbell Row transforms at progress r in [0.0, 1.0].
    Torso, head, pelvis, legs, bench, and supporting arm remain 100% stationary;
    only the working left arm and 3D dumbbell row smoothly from stretch to peak contraction."""
    # 1. Stationary Far (Right) Support Arm (Planted hand locked at FAR_HAND = (218.0, 206.0)):
    far_sh = (232.0, 126.0)
    far_el = (225.0, 168.0)
    ua_far_ang, ua_far_sc = seg_xform(far_sh, far_el, UA_FAR_LEN)
    fa_far_ang, fa_far_sc = seg_xform(far_el, FAR_HAND, FA_FAR_LEN)

    # 2. Working Near (Left) Shoulder, Elbow & Hand / Dumbbell Trajectory:
    #    - NEAR_SH: subtle 4-6 px shoulder socket retraction on the stationary upper torso
    near_sh = quad_interp_pt((286.0, 118.0), (288.0, 115.0), (290.0, 112.0), r)
    #    - NEAR_EL: hanging straight down at r=0.0 (282, 174) -> pulled high above the back at r=1.0 (340, 96)
    near_el = quad_interp_pt((282.0, 174.0), (314.0, 134.0), (340.0, 96.0), r)
    #    - NEAR_HAND (Dumbbell Grip Center): hanging low beside bench at r=0.0 (276, 224) -> pulled below ribcage/waist at r=1.0 (326, 156)
    near_hand = quad_interp_pt((276.0, 224.0), (304.0, 190.0), (326.0, 156.0), r)

    ua_near_ang, ua_near_sc = seg_xform(near_sh, near_el, UA_NEAR_LEN)
    fa_near_ang, fa_near_sc = seg_xform(near_el, near_hand, FA_NEAR_LEN)

    # 3. Dumbbell tilt (stays aligned with the isometric bench axis ~ -10 deg -> -6 deg)
    db_rot = math.radians(lerp(-10.0, -6.0, r))

    return {
        "r": r,
        "far_sh": far_sh,
        "far_el": far_el,
        "ua_far_ang": ua_far_ang,
        "ua_far_sc": ua_far_sc,
        "fa_far_ang": fa_far_ang,
        "fa_far_sc": fa_far_sc,
        "near_sh": near_sh,
        "near_el": near_el,
        "near_hand": near_hand,
        "ua_near_ang": ua_near_ang,
        "ua_near_sc": ua_near_sc,
        "fa_near_ang": fa_near_ang,
        "fa_near_sc": fa_near_sc,
        "db_rot": db_rot,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(row_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = (
    "ua_near_ang",
    "fa_near_ang",
    "db_rot",
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

if __name__ == "__main__":
    for _fr in (0, 38, 72, 116, DURATION):
        _p = POSES[_fr if _fr in POSES else min(POSES.keys(), key=lambda k: abs(k - _fr))]
        print(
            f"f{_fr:3d} r={_p['r']:.3f} near_sh=({_p['near_sh'][0]:.1f},{_p['near_sh'][1]:.1f}) "
            f"near_el=({_p['near_el'][0]:.1f},{_p['near_el'][1]:.1f}) "
            f"near_hand=({_p['near_hand'][0]:.1f},{_p['near_hand'][1]:.1f})"
        )


# ---------------------------------------------------------------- RML & Paint Helpers
_id = 0
KEYED = []


def nid():
    global _id
    _id += 1
    return f"o{_id}"


def f(v):
    return f"{v:.4f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


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


def stroke_shape(indent, name, pts, width, color, feather=0.0, cap="round", cid=None):
    idattr = f' id="{cid}"' if cid else ""
    f_xml = f'<Feather strength="{f(float(feather))}" name="{name}Feather"/>' if feather > 0 else ""
    return (
        f'{indent}<Shape name="{name}">\n'
        f'{indent}    <PointsPath isClosed="false" name="{name}Path">\n'
        f"{smooth_vertices(pts, False, indent + '        ')}\n"
        f"{indent}    </PointsPath>\n"
        f'{indent}    <Stroke thickness="{f(float(width))}" cap="{cap}" join="round" name="{name}Stroke">'
        f'<SolidColor colorValue="{color}" name="{name}Color"{idattr}/>{f_xml}</Stroke>\n'
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


def muscle_t(p):
    """Dumbbell-row muscle activation intensity in [0.42, 1.0] peaking at Top Contraction (r = 1.0)."""
    return 0.42 + 0.58 * (p["r"] ** 0.80)


def muscle_paint(name, scale=1.0, line=1.1):
    """Animated SolidColor muscle fill & edge pulsing from warm orange (r=0.0) to vivid crimson (r=1.0)."""
    fid, lid = nid(), nid()
    key_color(fid, 37, lambda p, s=scale: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, muscle_t(p) * s))
    key_color(lid, 37, lambda p, s=scale: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, muscle_t(p) * s))
    t0 = muscle_t(POSES[0]) * scale
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


def skin_fill_outlined(name, y0, y1, pal=SKIN, line=1.15, x0=0, x1=0, stroke_col=OUTLINE):
    return (
        f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *pal, x0=x0, x1=x1)}</Fill>'
        f'<Stroke thickness="{f(line)}" cap="round" join="round" name="{name}Outline">'
        f'<SolidColor colorValue="{stroke_col}" name="{name}OutlineCol"/></Stroke>'
    )


# ---------------------------------------------------------------- 1. 3D Flat Utility Bench (FLOOR = 300.0)
def flat_utility_bench():
    """3/4 front-left flat utility bench with white tubular steel frame and black upholstered vinyl pad."""
    ind = "        "
    i2 = ind + "    "

    def frame_paint(name, x0, y0, x1, y1, far=False):
        pal = FRAME_FAR if far else FRAME_WHITE
        return skin_fill_outlined(name, y0, y1, pal, line=1.1, x0=x0, x1=x1, stroke_col="99334155")

    def pad_paint(name, x0, y0, x1, y1):
        return skin_fill_outlined(name, y0, y1, PAD_DARK, line=1.15, x0=x0, x1=x1, stroke_col="FF020617")

    # Black upholstered flat bench pad (sloping gently in 3/4 perspective from front-left (156, 212) to rear-right (362, 188))
    pad_top = [(154, 210), (168, 200), (356, 182), (366, 190), (164, 214)]
    pad_side = [(154, 210), (164, 214), (366, 190), (366, 203), (164, 228), (154, 223)]

    # White tubular steel frame under the bench pad
    top_rail = [(174, 225), (348, 202), (349, 213), (175, 236)]
    lower_stretcher = [(178, 266), (342, 245), (343, 255), (179, 276)]
    front_leg = [(168, 294), (178, 224), (193, 222), (183, 294)]
    front_foot = [(152, 294), (192, 291), (194, 298), (154, 300)]
    rear_leg = [(334, 204), (348, 202), (355, 271), (341, 272)]
    rear_base = [(308, 265), (382, 274), (380, 282), (306, 272)]

    return "\n".join([
        f'{ind}<Node name="FlatUtilityBench">',
        # 1. Upholstered Black Vinyl Bench Pad (top surface + 3D side skirt + seam highlight)
        stroke_shape(i2, "BenchPadSeamHi", [(164, 213), (264, 201), (362, 190)], 1.4, "FF475569", 0.2),
        poly_shape(i2, "BenchPadTop", pad_top, pad_paint("PadTop", 154, 182, 366, 214), radius=5.0),
        poly_shape(i2, "BenchPadSide", pad_side, solid("PadSide", "FF090D16"), radius=4.5),

        # 2. Front-Left Angled Steel Leg & Foot (resting at FLOOR = 300.0)
        poly_shape(i2, "FrontRubberCap", [(148, 295), (162, 294), (163, 300), (149, 300)], pad_paint("FrontCap", 148, 294, 163, 300), radius=1.5),
        poly_shape(i2, "FrontFootPlate", front_foot, frame_paint("FrontFoot", 152, 291, 194, 300), radius=1.5),
        stroke_shape(i2, "FrontLegHi", [(181, 228), (172, 290)], 2.2, "FFFFFFFF", 0.5),
        poly_shape(i2, "FrontMainLeg", front_leg, frame_paint("FrontLeg", 168, 222, 193, 294), radius=1.5),

        # 3. Upper Support Rail & Lower Stretcher Crossbar
        poly_shape(i2, "UpperSupportRail", top_rail, frame_paint("TopRail", 174, 202, 349, 236, far=True), radius=1.5),
        poly_shape(i2, "LowerStretcherBar", lower_stretcher, frame_paint("Stretcher", 178, 245, 343, 276, far=True), radius=1.5),

        # 4. Rear-Right Steel Leg & T-Stabilizer Base
        poly_shape(i2, "RearRubberCapR", [(374, 273), (385, 274), (384, 283), (373, 282)], pad_paint("RearCapR", 373, 273, 385, 283), radius=1.5),
        poly_shape(i2, "RearRubberCapL", [(302, 264), (312, 265), (311, 273), (301, 272)], pad_paint("RearCapL", 301, 264, 312, 273), radius=1.5),
        poly_shape(i2, "RearStabilizerBase", rear_base, frame_paint("RearBase", 306, 265, 382, 282, far=True), radius=1.5),
        poly_shape(i2, "RearMainLeg", rear_leg, frame_paint("RearLeg", 334, 202, 355, 272, far=True), radius=1.5),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 2. Far (Right) Kneeling Leg Resting on Bench Pad
def far_kneeling_leg():
    """Right thigh descending from right hip (336, 146) to kneeling knee (312, 194) and horizontal shin on the bench pad."""
    ind = "        "
    i2 = ind + "    "

    # Right thigh (kneeling): from right hip (336, 144) down-left to right knee (312, 194)
    thigh_pts = [
        (324, 138), (348, 144), (336, 178), (324, 198), (304, 196), (304, 178), (314, 154),
    ]
    shorts_pts = [
        (322, 136), (350, 142), (342, 168), (312, 162),
    ]
    # Right lower leg / shin resting horizontally back-right along the bench pad (312, 194) -> (358, 190)
    shin_pts = [
        (306, 190), (332, 180), (358, 182), (362, 192), (334, 198), (308, 198),
    ]

    return "\n".join([
        f'{ind}<Node name="FarRightKneelingLeg">',
        smooth_shape(i2, "FarKneelingShorts", shorts_pts, skin_fill_outlined("FarKneeShorts", 136, 168, SHORTS, line=1.1, stroke_col="CC020617")),
        ellipse_shape(i2, "FarKneeCap", 312, 192, 14.0, 12.0, skin_fill_outlined("FarKnee", -6, 6, SKIN_FAR, line=0.95)),
        stroke_shape(i2, "FarThighQuadLine", [(328, 158), (316, 184)], 1.25, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "FarThighHi", [(322, 156), (312, 184)], 2.8, HIGHLIGHT, 2.8),
        smooth_shape(i2, "FarKneelingThigh", thigh_pts, skin_fill_outlined("FarThigh", 138, 198, SKIN_FAR, line=1.15)),
        stroke_shape(i2, "FarShinCalfLine", [(320, 188), (350, 186)], 1.15, ANATOMY_LINE, 0.2),
        smooth_shape(i2, "FarKneelingShin", shin_pts, skin_fill_outlined("FarShin", 180, 198, SKIN_FAR, line=1.1)),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 3. Far (Right) Support Arm Planted on Bench Pad
def far_support_arm():
    """Stationary planted right hand (218, 206) on the left end of the bench pad + extended right forearm, upper arm & shoulder cap."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    p0 = POSES[0]

    # Planted palm & spread fingers resting flat on the bench pad at FAR_HAND = (218, 206)
    palm_pts = [
        (224, 201), (226, 207), (214, 210), (196, 210), (195, 206), (208, 203), (216, 200),
    ]
    # Upper arm extends from x = -12 (deep inside the front-left shoulder socket) to UA_FAR_LEN + 3
    ua_pts = [
        (-12, 0), (-8, -10.5), (8, -11.0), (UA_FAR_LEN * 0.55, -9.8), (UA_FAR_LEN - 3, -6.8),
        (UA_FAR_LEN + 3, 0), (UA_FAR_LEN - 3, 6.8), (UA_FAR_LEN * 0.55, 9.8), (8, 11.0), (-8, 10.5),
    ]
    far_delt_pts = [
        (-12, 0), (-8, -10.8), (6, -11.2), (16, -7.5), (18, 0), (16, 7.8), (6, 11.2), (-8, 10.8),
    ]
    fa_pts = [
        (-6, 0), (-3, -8.2), (FA_FAR_LEN * 0.38, -9.0), (FA_FAR_LEN - 4, -5.5),
        (FA_FAR_LEN + 3, 0), (FA_FAR_LEN - 4, 5.5), (FA_FAR_LEN * 0.38, 8.2), (-3, 7.5),
    ]

    return "\n".join([
        f'{ind}<Node name="FarRightSupportArm">',
        # 1. Stationary Planted Hand & Fingers on Bench Pad (zero drift!)
        stroke_shape(i2, "PlantedFinger1", [(200, 208), (210, 207)], 1.0, ANATOMY_LINE, 0.0),
        stroke_shape(i2, "PlantedFinger2", [(204, 209.5), (214, 208.5)], 1.0, ANATOMY_LINE, 0.0),
        ellipse_shape(i2, "PlantedWristCrease", 219, 202, 11.5, 4.5, skin_fill_outlined("WristBand", -2, 2, SKIN_FAR, line=0.9)),
        smooth_shape(i2, "PlantedRightHand", palm_pts, skin_fill_outlined("PlantedHand", 200, 211, SKIN_FAR, line=1.1)),

        # 2. Stationary Extended Right Forearm (FAR_EL -> FAR_HAND)
        f'{i2}<Node x="{f(p0["far_el"][0])}" y="{f(p0["far_el"][1])}" '
        f'rotation="{f(p0["fa_far_ang"])}" scaleX="{f(p0["fa_far_sc"])}" name="FarSupportForearm">',
        stroke_shape(i3, "FarForearmExtensorLine", [(6, 1.5), (FA_FAR_LEN - 8, 1.2)], 1.2, ANATOMY_LINE, 0.2),
        stroke_shape(i3, "FarForearmHi", [(5, 4.2), (FA_FAR_LEN - 8, 3.2)], 2.4, HIGHLIGHT, 2.4),
        smooth_shape(i3, "FarSupportForearmShape", fa_pts, skin_fill_outlined("FarForearm", -9, 9, SKIN_FAR, line=1.15)),
        f"{i2}</Node>",

        # 3. Stationary Extended Right Upper Arm & Anterior/Lateral Shoulder Cap (FAR_SH -> FAR_EL)
        f'{i2}<Node x="{f(p0["far_sh"][0])}" y="{f(p0["far_sh"][1])}" '
        f'rotation="{f(p0["ua_far_ang"])}" scaleX="{f(p0["ua_far_sc"])}" name="FarSupportUpperArm">',
        stroke_shape(i3, "FarDeltLine", [(-2, 3.5), (14, 3.0)], 1.15, ANATOMY_LINE, 0.2),
        smooth_shape(i3, "FarShoulderCap", far_delt_pts, skin_fill_outlined("FarDeltCap", -11, 11, SKIN_FAR, line=1.1)),
        stroke_shape(i3, "FarUpperArmLine", [(10, 2.0), (UA_FAR_LEN - 6, 1.8)], 1.25, ANATOMY_LINE, 0.2),
        stroke_shape(i3, "FarUpperArmHi", [(6, 4.8), (UA_FAR_LEN - 8, 3.8)], 2.6, HIGHLIGHT, 2.5),
        smooth_shape(i3, "FarSupportUpperArmShape", ua_pts, skin_fill_outlined("FarUpperArm", -11, 11, SKIN_FAR, line=1.15)),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 4. Near (Left) Standing Leg Planted on Floor (FLOOR = 300.0)
def near_standing_leg():
    """Planted left standing leg on the studio floor (x = 368..376, y = 148..298) with sculpted quads, patella, shin, and bare foot."""
    ind = "        "
    i2 = ind + "    "

    # Sculpted Left Quadriceps (Vastus Lateralis, Rectus Femoris, Vastus Medialis teardrop) from hip (368, 148) to knee (368, 214)
    thigh_pts = [
        (350, 146), (384, 144), (388, 174), (382, 202), (376, 216),
        (360, 216), (354, 200), (348, 174),
    ]
    shorts_leg_pts = [
        (348, 138), (386, 136), (388, 166), (348, 168),
    ]
    # Sculpted Left Shin & Gastrocnemius/Soleus Calf from knee (368, 214) to ankle (376, 282)
    shin_pts = [
        (360, 212), (376, 212), (384, 234), (382, 260), (381, 282),
        (371, 282), (366, 260), (360, 236),
    ]
    # Bare Left Foot planted flat on FLOOR = 300.0 facing forward-left (5 toes visible!)
    foot_pts = [
        (371, 280), (381, 280), (385, 292), (383, 298),
        (365, 298), (364, 292), (368, 284),
    ]

    return "\n".join([
        f'{ind}<Node name="NearLeftStandingLeg">',
        # 1. Bare Left Foot & 5 Sculpted Toes on FLOOR = 300.0
        stroke_shape(i2, "NearToe1", [(368, 293), (368, 297)], 0.95, ANATOMY_LINE, 0.0),
        stroke_shape(i2, "NearToe2", [(372, 293), (372, 297)], 0.95, ANATOMY_LINE, 0.0),
        stroke_shape(i2, "NearToe3", [(376, 293), (376, 297)], 0.95, ANATOMY_LINE, 0.0),
        stroke_shape(i2, "NearToe4", [(380, 293), (380, 297)], 0.95, ANATOMY_LINE, 0.0),
        smooth_shape(i2, "NearStandingFoot", foot_pts, skin_fill_outlined("NearFoot", 280, 299, SKIN, line=1.15)),

        # 2. Sculpted Left Shin (Tibialis Anterior & Gastrocnemius)
        stroke_shape(i2, "NearTibialisLine", [(369, 222), (372, 250), (375, 276)], 1.3, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "NearCalfLine", [(377, 224), (379, 248), (378, 272)], 1.2, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "NearShinHi", [(366, 222), (370, 272)], 2.8, HIGHLIGHT, 2.8),
        stroke_shape(i2, "NearShinSh", [(379, 224), (379, 274)], 3.4, CORE_SHADOW, 3.2),
        smooth_shape(i2, "NearStandingShin", shin_pts, skin_fill_outlined("NearShin", 212, 282, SKIN, line=1.15)),

        # 3. Patella, Quadriceps & Compression Shorts Leg
        ellipse_shape(i2, "NearPatella", 368, 213, 14.5, 13.5, skin_fill_outlined("NearPatella", -7, 7, SKIN, line=1.0)),
        smooth_shape(i2, "NearStandingShorts", shorts_leg_pts, skin_fill_outlined("NearShortsLeg", 136, 168, SHORTS, line=1.15, stroke_col="CC020617")),
        stroke_shape(i2, "NearRectusFemorisLine", [(366, 166), (366, 202)], 1.35, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "NearVastusLateralisLine", [(376, 166), (375, 200)], 1.3, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "NearVastusMedialisLine", [(357, 176), (359, 202)], 1.25, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "NearThighHi", [(362, 166), (363, 200)], 3.4, HIGHLIGHT, 3.2),
        stroke_shape(i2, "NearThighSh", [(380, 166), (378, 200)], 4.2, CORE_SHADOW, 4.0),
        smooth_shape(i2, "NearStandingThigh", thigh_pts, skin_fill_outlined("NearThigh", 144, 216, SKIN, line=1.15)),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 5. Hinged Torso, 5 Dorsal/Scapular Target Muscles, Pectorals & 3/4 Head
def hinged_torso_back_and_head():
    """Stationary hinged torso anchored firmly to the pelvis/hip with 5 labeled dorsal/scapular muscles (Latissimus dorsi,
    Teres major, Teres minor, Infraspinatus, Trapezius middle & lower), exposed Pectoralis major, and volumetric 3/4 head."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    torso_id = nid()
    scap_id = nid()

    # 1. Pelvic Compression Shorts (anchored over the hips at (332..386, 118..164))
    pelvis_shorts = [
        (328, 138), (346, 118), (374, 120), (388, 140), (384, 162), (350, 164), (328, 154),
    ]

    # 2. Hinged Torso Base Silhouette (smoothly encloses the entire dorsal arch & both shoulder sockets)
    torso_pts = [
        (228, 122),  # front-left supporting shoulder socket
        (246, 89),   # base of neck / upper trapezius
        (276, 85),   # upper-middle thoracic / trapezius arch
        (308, 89),   # mid-thoracic dorsal arch
        (336, 101),  # lower-thoracic dorsal arch
        (356, 120),  # lumbar / iliac crest transition into pelvis shorts
        (348, 152),  # lower waist / hip
        (318, 156),  # abdominal wall
        (282, 154),  # lower chest / xiphoid
        (248, 144),  # anterior pectoral border
        (228, 134),  # anterior axillary fold of supporting arm
    ]

    # Upper-shoulder / clavicular / scapular skin shading bridging the neck and dorsal muscles seamlessly
    upper_shoulder_pts = [
        (248, 92), (274, 88), (294, 96), (288, 118), (262, 122), (242, 114),
    ]

    # 3. Exposed Pectoralis Major on the ventral underside of the chest (strictly below y = 120 so it never floats on the shoulder)
    pec_left_pts = [
        (254, 126), (276, 120), (296, 124), (296, 146), (276, 152), (254, 142),
    ]
    pec_right_pts = [
        (232, 122), (254, 122), (256, 142), (242, 142), (230, 132),
    ]

    # 4. Five Labeled Dorsal & Scapular Target Muscles (strictly inside torso_pts dorsal contour, zero protruding spikes!):
    #    (a) Target Muscle #1: Latissimus dorsi (scale = 1.00 — Primary Mover!)
    lat_pts = [
        (290, 119), (314, 118), (344, 124), (338, 142), (314, 144), (292, 132),
    ]
    #    (b) Target Muscle #2: Teres major (scale = 0.96 — thick cylindrical belly immediately above Latissimus dorsi)
    teres_major_pts = [
        (288, 113), (310, 112), (328, 116), (324, 123), (304, 122), (288, 119),
    ]
    #    (c) Target Muscle #3: Teres minor (scale = 0.90 — narrow rotator-cuff band above Teres major)
    teres_minor_pts = [
        (286, 107), (306, 106), (322, 110), (318, 115), (300, 114), (286, 112),
    ]
    #    (d) Target Muscle #4: Infraspinatus (scale = 0.90 — triangular infraspinous fossa plate above Teres minor)
    infraspinatus_pts = [
        (282, 100), (302, 98), (318, 103), (314, 109), (296, 108), (282, 106),
    ]
    #    (e) Target Muscle #5: Trapezius (middle and lower) (scale = 0.88 — dorsal ridge arching along the upper spine inside torso_pts)
    trap_mid_low_pts = [
        (256, 92), (280, 89), (306, 93), (324, 101), (306, 100), (282, 98), (258, 98),
    ]

    # 5. Volumetric 3/4 Male Head & Neck at the front-left of the hinged torso (looking forward-down toward the bench!)
    neck_pts = [(232, 94), (258, 90), (266, 116), (238, 122)]
    head_pts = [
        (216, 116),  # sculpted chin tip pointing down-left
        (209, 110),  # lower lip / chin cleft
        (206, 103),  # upper lip / philtrum
        (203, 96),   # nose tip pointing down-left
        (204, 86),   # brow ridge / forehead
        (211, 75),   # anterior frontal crown
        (225, 70),   # cranial dome
        (239, 74),   # posterior parietal crown
        (245, 86),   # occiput
        (241, 100),  # mastoid / behind ear
        (231, 111),  # mandible angle (jawline)
    ]
    hair_pts = [
        (205, 84), (212, 74), (226, 69), (240, 74), (246, 86),
        (242, 97), (237, 89), (231, 82), (218, 82),
    ]
    hair_paint = (
        f'<Fill name="HairFill">{grad("HairGrad", 205, 69, 246, 97, "FF334155", "FF0F172A")}</Fill>'
        '<Stroke thickness="0.95" join="round" name="HairStroke"><SolidColor colorValue="FF090D16" name="HairStrokeCol"/></Stroke>'
    )

    return "\n".join([
        f'{ind}<Node name="HingedTorsoBackAndHead">',
        # 1. Stationary Pelvic Compression Shorts (anchored over FAR_HIP and NEAR_HIP)
        stroke_shape(i2, "ShortsWaistband", [(330, 140), (346, 120), (374, 122)], 2.2, "CC020617", 0.0),
        smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill_outlined("PelvisShorts", 118, 164, SHORTS, line=1.15, stroke_col="CC020617")),

        # 2. Animated Hinged Upper Torso, 5 Dorsal Muscles, Exposed Chest & 3/4 Head
        f'{i2}<Node x="0" y="0" rotation="0" name="TorsoMotionGroup" id="{torso_id}">',

        # A. Volumetric 3/4 Head & Neck (in front of the collarbones/trapezius)
        smooth_shape(i3, "HairCap", hair_pts, hair_paint),
        ellipse_shape(i3, "LeftEar", 234, 94, 5.4, 7.8, skin_fill_outlined("Ear", -4, 4, SKIN, line=0.85), rot_deg=18.0),
        stroke_shape(i3, "BrowLine", [(205, 90), (212, 91)], 1.35, "FF1E293B", 0.0),
        ellipse_shape(i3, "EyeDot", 209.5, 93.2, 2.2, 1.6, solid("Eye", "FF0F172A")),
        stroke_shape(i3, "NoseLine", [(204, 96), (208, 98)], 1.1, ANATOMY_LINE, 0.0),
        stroke_shape(i3, "MouthLine", [(207, 105), (213, 105)], 1.1, ANATOMY_LINE, 0.0),
        stroke_shape(i3, "JawLine", [(216, 115), (229, 110), (235, 101)], 1.4, CORE_SHADOW, 1.2),
        stroke_shape(i3, "HeadHi", [(208, 84), (220, 74), (232, 74)], 2.8, HIGHLIGHT, 2.8),
        smooth_shape(i3, "HeadShape", head_pts, skin_fill_outlined("Head", 70, 116, SKIN, line=1.1)),
        stroke_shape(i3, "NeckSCMCrease", [(238, 100), (256, 114)], 1.35, ANATOMY_LINE, 0.2),
        stroke_shape(i3, "ClavicleCollarLine", [(236, 120), (262, 118), (284, 114)], 1.35, ANATOMY_LINE, 0.2),
        smooth_shape(i3, "NeckShape", neck_pts, skin_fill_outlined("Neck", 90, 122, SKIN, line=1.0)),

        # B. Crisp Dorsal Spine Outline & Retracting Dorsal/Scapular Target Muscles (strictly inside TorsoSilhouette!)
        stroke_shape(i3, "DorsalBackOutline", [(248, 89), (276, 85), (308, 89), (336, 101), (354, 118)], 1.5, OUTLINE, 0.0),
        f'{i3}<Node x="0" y="0" name="ScapulaBackGroup" id="{scap_id}">',
        # Fiber striations on Latissimus dorsi, Teres major & Infraspinatus
        stroke_shape(i3 + "    ", "LatStriation1", [(296, 124), (318, 123), (338, 127)], 1.05, "667F1D1D", 0.3),
        stroke_shape(i3 + "    ", "LatStriation2", [(296, 130), (316, 131), (334, 135)], 1.05, "667F1D1D", 0.3),
        stroke_shape(i3 + "    ", "InfraStriation", [(288, 103), (310, 103)], 1.0, "667F1D1D", 0.3),
        # 1. Latissimus dorsi (scale = 1.00 — Primary Mover!)
        smooth_shape(i3 + "    ", "LatissimusDorsi", lat_pts, muscle_paint("LatDorsi", scale=1.00, line=1.1)),
        # 2. Teres major (scale = 0.96)
        smooth_shape(i3 + "    ", "TeresMajor", teres_major_pts, muscle_paint("TeresMajor", scale=0.96, line=1.05)),
        # 3. Teres minor (scale = 0.90)
        smooth_shape(i3 + "    ", "TeresMinor", teres_minor_pts, muscle_paint("TeresMinor", scale=0.90, line=1.0)),
        # 4. Infraspinatus (scale = 0.90)
        smooth_shape(i3 + "    ", "Infraspinatus", infraspinatus_pts, muscle_paint("Infraspinatus", scale=0.90, line=1.0)),
        # 5. Trapezius (middle and lower) (scale = 0.88)
        smooth_shape(i3 + "    ", "TrapeziusMidLow", trap_mid_low_pts, muscle_paint("TrapMidLow", scale=0.88, line=1.0)),
        f"{i3}</Node>",

        # C. Upper Shoulder / Scapular Spine Contour & Exposed Pectoralis Major on the Ventral Chest Wall
        stroke_shape(i3, "ScapularSpineCrease", [(260, 98), (276, 98), (290, 104)], 1.25, ANATOMY_LINE, 0.2),
        stroke_shape(i3, "AcromionCrease", [(256, 108), (274, 108), (288, 112)], 1.2, ANATOMY_LINE, 0.2),
        smooth_shape(i3, "UpperShoulderBridge", upper_shoulder_pts, skin_fill_outlined("UpperShoulder", 88, 122, SKIN, line=0.9)),
        stroke_shape(i3, "PecLeftStriation1", [(260, 134), (276, 135), (292, 130)], 1.05, "667F1D1D", 0.3),
        stroke_shape(i3, "PecLeftStriation2", [(260, 141), (276, 142), (292, 138)], 1.05, "667F1D1D", 0.3),
        smooth_shape(i3, "PectoralisMajorLeft", pec_left_pts, muscle_paint("PecLeft", scale=0.58, line=1.0)),
        smooth_shape(i3, "PectoralisMajorRight", pec_right_pts, skin_fill_outlined("PecRight", 122, 144, SKIN_FAR, line=1.0)),
        # Serratus anterior & external oblique ribs between chest and pelvis
        stroke_shape(i3, "SerratusRib1", [(302, 143), (318, 143)], 1.25, ANATOMY_LINE, 0.2),
        stroke_shape(i3, "SerratusRib2", [(300, 149), (318, 149)], 1.25, ANATOMY_LINE, 0.2),
        stroke_shape(i3, "ObliqueFlankLine", [(316, 145), (334, 149)], 1.3, ANATOMY_LINE, 0.2),
        stroke_shape(i3, "TorsoSh", [(270, 150), (314, 152), (342, 146)], 4.5, CORE_SHADOW, 4.2),
        smooth_shape(i3, "TorsoSilhouette", torso_pts, skin_fill_outlined("Torso", 85, 156, SKIN, line=1.15)),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 6. Working Near (Left) Arm & Heavy 3D Double-Plate Dumbbell
def working_arm_and_dumbbell():
    """Working left arm (NEAR_SH -> NEAR_EL -> NEAR_HAND) with integrated Deltoid Cap + Posterior deltoid (scale=0.95),
    Brachialis (scale=0.90), and Brachioradialis (scale=0.90), plus the heavy 3D double-plate cast-iron dumbbell."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    ua_id, fa_id, db_id = nid(), nid(), nid()

    key_double(ua_id, 13, lambda p: p["near_sh"][0])
    key_double(ua_id, 14, lambda p: p["near_sh"][1])
    key_double(ua_id, 15, lambda p: p["ua_near_ang"])
    key_double(ua_id, 16, lambda p: p["ua_near_sc"])

    key_double(fa_id, 13, lambda p: p["near_el"][0])
    key_double(fa_id, 14, lambda p: p["near_el"][1])
    key_double(fa_id, 15, lambda p: p["fa_near_ang"])
    key_double(fa_id, 16, lambda p: p["fa_near_sc"])

    key_double(db_id, 13, lambda p: p["near_hand"][0])
    key_double(db_id, 14, lambda p: p["near_hand"][1])
    key_double(db_id, 15, lambda p: p["db_rot"])
    p0 = POSES[0]

    # 1. NearWorkingUpperArm along +X (0 -> UA_NEAR_LEN = 50):
    #    - Integrated Deltoid Cap wraps (-11..22) and rotates seamlessly with the humerus (zero detachment!)
    #    - Target Muscle #6: Posterior deltoid (scale = 0.95) sits in the proximal dorsal-lateral deltoid (-5..20, y = -10.5..-0.5)
    #    - Target Muscle #7: Brachialis (scale = 0.90) sits in the distal lateral groove (22..45, y = -5.5..+2.0) strictly inside ua_pts!
    ua_pts = [
        (-11, 0), (-7, -11.5), (10, -12.0), (28, -10.5), (45, -6.8),
        (52, 0), (45, 6.8), (28, 10.5), (10, 11.8), (-7, 11.2),
    ]
    delt_cap_pts = [
        (-11, 0), (-7, -11.5), (7, -12.0), (20, -8.5), (23, 0),
        (20, 9.0), (7, 11.8), (-7, 11.2),
    ]
    post_delt_pts = [
        (-5, -1.0), (-3, -10.2), (7, -11.0), (18, -7.8), (20, -1.2), (7, -0.2),
    ]
    brachialis_pts = [
        (22, -1.2), (28, -5.2), (41, -4.5), (45, -0.5), (41, 2.2), (28, 1.8),
    ]

    # 2. NearWorkingForearm along +X (0 -> FA_NEAR_LEN = 52):
    #    - Target Muscle #8: Brachioradialis (scale = 0.90) sits strictly inside the radial-anterior border (y = 0..+8.2)
    fa_pts = [
        (-8, 0), (-4, -8.8), (FA_NEAR_LEN * 0.35, -9.5), (FA_NEAR_LEN - 6, -5.8),
        (FA_NEAR_LEN + 3, 0), (FA_NEAR_LEN - 6, 5.8), (FA_NEAR_LEN * 0.35, 9.5), (-4, 8.5),
    ]
    brachioradialis_pts = [
        (2, 0.0), (14, 0.8), (33, 2.2), (31, 6.5), (14, 8.2), (2, 6.2),
    ]
    # Neutral-grip hand & knuckles wrapped around the dumbbell handle at x = FA_NEAR_LEN
    hand_pts = [
        (FA_NEAR_LEN - 7, -6.8), (FA_NEAR_LEN + 6, -6.5), (FA_NEAR_LEN + 8, 0.0),
        (FA_NEAR_LEN + 6, 6.8), (FA_NEAR_LEN - 6, 6.5),
    ]

    # 3. Heavy 3D Double-Plate Cast-Iron Dumbbell (centered at NEAR_HAND, tilted by db_rot):
    plate_face = (
        f'<Fill name="PlateFaceFill">{grad3("PlateFaceGrad", -22, 22, *PLATE_DARK, x0=-14, x1=14)}</Fill>'
        '<Stroke thickness="1.2" name="PlateFaceStroke"><SolidColor colorValue="FF475569" name="PlateFaceStrokeCol"/></Stroke>'
    )
    plate_rim = (
        '<Fill name="PlateRimFill"><SolidColor colorValue="FF020617" name="PlateRimCol"/></Fill>'
        '<Stroke thickness="1.0" name="PlateRimStroke"><SolidColor colorValue="FF1E293B" name="PlateRimStrokeCol"/></Stroke>'
    )
    plate_groove = (
        '<Stroke thickness="1.1" name="PlateGrooveStroke"><SolidColor colorValue="FF334155" name="PlateGrooveCol"/></Stroke>'
    )
    hub_paint = (
        f'<Fill name="HubFill">{grad("HubGrad", -5, -7, 5, 7, "FFE2E8F0", "FF475569")}</Fill>'
        '<Stroke thickness="0.9" name="HubStroke"><SolidColor colorValue="FF0F172A" name="HubStrokeCol"/></Stroke>'
    )

    return "\n".join([
        f'{ind}<Node name="WorkingLeftArmAndDumbbell">',

        # 1. Foreground: Front-Left Double Plates + Spinlock Collar Nut
        f'{i2}<Node x="{f(p0["near_hand"][0])}" y="{f(p0["near_hand"][1])}" '
        f'rotation="{f(p0["db_rot"])}" name="DumbbellFrontPlates" id="{db_id}">',
        ellipse_shape(i3, "FrontCollarNut", -21.5, 0.0, 7.5, 11.5, hub_paint),
        ellipse_shape(i3, "FrontOuterPlateGroove", -18.0, 0.0, 19.0, 31.0, plate_groove),
        ellipse_shape(i3, "FrontOuterPlateFace", -18.0, 0.0, 27.0, 43.0, plate_face),
        ellipse_shape(i3, "FrontOuterPlateRim", -15.5, 0.0, 27.0, 43.0, plate_rim),
        ellipse_shape(i3, "FrontInnerPlateFace", -12.0, 0.0, 25.0, 40.0, plate_face),
        ellipse_shape(i3, "FrontInnerPlateRim", -9.8, 0.0, 25.0, 40.0, plate_rim),
        f"{i2}</Node>",

        # 2. Working Left Forearm (NEAR_EL -> NEAR_HAND) with Target Muscle #8: Brachioradialis & Gripping Hand
        f'{i2}<Node x="{f(p0["near_el"][0])}" y="{f(p0["near_el"][1])}" '
        f'rotation="{f(p0["fa_near_ang"])}" scaleX="{f(p0["fa_near_sc"])}" name="NearWorkingForearm" id="{fa_id}">',
        stroke_shape(i3, "NearFingerKnuckle1", [(FA_NEAR_LEN - 2, -4.0), (FA_NEAR_LEN + 4, -3.8)], 1.0, ANATOMY_LINE, 0.0),
        stroke_shape(i3, "NearFingerKnuckle2", [(FA_NEAR_LEN - 2, 0.0), (FA_NEAR_LEN + 5, 0.0)], 1.0, ANATOMY_LINE, 0.0),
        stroke_shape(i3, "NearFingerKnuckle3", [(FA_NEAR_LEN - 2, 4.0), (FA_NEAR_LEN + 4, 3.8)], 1.0, ANATOMY_LINE, 0.0),
        ellipse_shape(i3, "NearWristBand", FA_NEAR_LEN - 6.0, 0.0, 5.5, 13.0, skin_fill_outlined("NearWrist", -6, 6, SKIN, line=0.9)),
        smooth_shape(i3, "NearGrippingHand", hand_pts, skin_fill_outlined("NearHand", -7, 7, SKIN, line=1.15)),
        # Target Muscle #8: Brachioradialis (scale = 0.90 — strictly inside forearm contour)
        stroke_shape(i3, "BrachioradialisFiber", [(5, 3.8), (28, 4.2)], 1.05, "667F1D1D", 0.3),
        smooth_shape(i3, "Brachioradialis", brachioradialis_pts, muscle_paint("Brachioradialis", scale=0.90, line=1.0)),
        stroke_shape(i3, "NearForearmExtensorLine", [(6, -3.5), (FA_NEAR_LEN - 10, -2.5)], 1.25, ANATOMY_LINE, 0.2),
        stroke_shape(i3, "NearForearmHi", [(6, -5.5), (FA_NEAR_LEN - 10, -4.0)], 2.6, HIGHLIGHT, 2.5),
        smooth_shape(i3, "NearForearmShape", fa_pts, skin_fill_outlined("NearForearm", -10, 10, SKIN, line=1.15)),
        f"{i2}</Node>",

        # 3. Working Left Upper Arm & Integrated Deltoid Cap (NEAR_SH -> NEAR_EL) with Posterior Deltoid & Brachialis
        f'{i2}<Node x="{f(p0["near_sh"][0])}" y="{f(p0["near_sh"][1])}" '
        f'rotation="{f(p0["ua_near_ang"])}" scaleX="{f(p0["ua_near_sc"])}" name="NearWorkingUpperArm" id="{ua_id}">',
        # Target Muscle #6: Posterior deltoid (scale = 0.95) + Anterior/Lateral Deltoid Cap
        stroke_shape(i3, "PostDeltFiber1", [(-1, -6.2), (15, -5.2)], 1.05, "667F1D1D", 0.3),
        stroke_shape(i3, "PostDeltFiber2", [(-1, -3.2), (15, -2.5)], 1.05, "667F1D1D", 0.3),
        smooth_shape(i3, "PosteriorDeltoid", post_delt_pts, muscle_paint("PostDelt", scale=0.95, line=1.05)),
        stroke_shape(i3, "LatDeltCrease", [(-2, 4.2), (16, 3.8)], 1.2, ANATOMY_LINE, 0.2),
        stroke_shape(i3, "AntDeltHi", [(-2, 7.2), (14, 6.5)], 2.4, HIGHLIGHT, 2.4),
        smooth_shape(i3, "NearDeltoidBase", delt_cap_pts, skin_fill_outlined("NearDeltoid", -12, 12, SKIN, line=1.1)),
        # Target Muscle #7: Brachialis (scale = 0.90 — strictly inside distal upper arm contour)
        stroke_shape(i3, "BrachialisFiber", [(25, -1.8), (41, -1.2)], 1.0, "667F1D1D", 0.3),
        smooth_shape(i3, "Brachialis", brachialis_pts, muscle_paint("Brachialis", scale=0.90, line=1.0)),
        stroke_shape(i3, "NearTricepsHorseshoe", [(22, -6.8), (44, -5.2)], 1.25, ANATOMY_LINE, 0.2),
        stroke_shape(i3, "NearBicepsCrease", [(22, 5.2), (44, 4.5)], 1.25, ANATOMY_LINE, 0.2),
        stroke_shape(i3, "NearUpperArmHi", [(18, -7.8), (44, -5.8)], 2.6, HIGHLIGHT, 2.5),
        smooth_shape(i3, "NearUpperArmShape", ua_pts, skin_fill_outlined("NearUpperArm", -12, 12, SKIN, line=1.15)),
        f"{i2}</Node>",

        # 4. Rear-Right Double Plates & Chrome Handle Shaft (drawn behind the gripping hand & forearm)
        f'{i2}<Node x="{f(p0["near_hand"][0])}" y="{f(p0["near_hand"][1])}" '
        f'rotation="{f(p0["db_rot"])}" name="DumbbellRearPlates" id="{ {k: v for k, v in [(0, nid())]}[0] }">',
        polyline_stroke_shape(i3, "DumbbellHandleHi", [(-12, -1.2), (14, -1.2)], 1.6, "FFFFFFFF", radius=0.5),
        polyline_stroke_shape(i3, "DumbbellHandleShaft", [(-14, 0.0), (16, 0.0)], 5.5, "FF94A3B8", radius=1.0),
        ellipse_shape(i3, "RearInnerPlateFace", 13.0, 0.0, 24.0, 38.0, plate_face),
        ellipse_shape(i3, "RearInnerPlateRim", 15.0, 0.0, 24.0, 38.0, plate_rim),
        ellipse_shape(i3, "RearOuterPlateFace", 18.5, 0.0, 26.0, 41.0, plate_face),
        ellipse_shape(i3, "RearOuterPlateRim", 20.8, 0.0, 26.0, 41.0, plate_rim),
        f"{i2}</Node>",

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 7. Scene Assembly (RML First Child = Topmost Layer)
def build_rml():
    global _id
    _id = 0
    KEYED.clear()

    bench_xml = flat_utility_bench()
    far_leg_xml = far_kneeling_leg()
    far_arm_xml = far_support_arm()
    torso_head_xml = hinged_torso_back_and_head()
    near_leg_xml = near_standing_leg()
    working_arm_xml = working_arm_and_dumbbell()

    # Bind DumbbellRearPlates to the exact same (near_hand, db_rot) track as DumbbellFrontPlates
    rear_db_id = f"o{_id}"
    key_double(rear_db_id, 13, lambda p: p["near_hand"][0])
    key_double(rear_db_id, 14, lambda p: p["near_hand"][1])
    key_double(rear_db_id, 15, lambda p: p["db_rot"])

    grouped = {}
    for oid, kxml in KEYED:
        grouped.setdefault(oid, []).append(kxml)
    keyed_objects_xml = "\n".join(
        f'        <KeyedObject objectId="{oid}">\n' + "\n".join(props) + "\n        </KeyedObject>"
        for oid, props in grouped.items()
    )

    # Note: In Rive RML, FIRST child of Artboard is drawn IN FRONT (topmost); LAST child is drawn BEHIND (bottommost)!
    # Layer order from front to back:
    #   1. WorkingLeftArmAndDumbbell (Posterior deltoid, Brachialis, Brachioradialis, gripping left hand & 3D dumbbell)
    #   2. NearLeftStandingLeg (planted on FLOOR = 300.0 in front of the right end of the bench)
    #   3. HingedTorsoBackAndHead (Latissimus dorsi, Teres major, Teres minor, Infraspinatus, Trapezius, Pectorals, 3/4 Head)
    #   4. FarRightSupportArm (planted right palm on the front-left of the bench pad)
    #   5. FarRightKneelingLeg (kneeling right knee & horizontal shin on the rear-right of the bench pad)
    #   6. FlatUtilityBench (black upholstered bench pad & white powder-coated steel frame)
    #   7. Studio Floor Shadow & Ambient Backdrop
    return f"""<Rive version="7.3">
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="DumbbellRow" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Working Near (Left) Arm & Heavy 3D Double-Plate Dumbbell -->
{working_arm_xml}

        <!-- 2. Mid-Foreground Right: Planted Near (Left) Standing Leg on Floor -->
{near_leg_xml}

        <!-- 3. Midground: Hinged Torso, 5 Dorsal/Scapular Target Muscles, Exposed Chest & 3/4 Head -->
{torso_head_xml}

        <!-- 4. Mid-Background Left: Planted Far (Right) Support Arm on Bench Pad -->
{far_arm_xml}

        <!-- 5. Mid-Background Right: Kneeling Far (Right) Leg on Bench Pad -->
{far_leg_xml}

        <!-- 6. Background Equipment: 3D Flat Utility Bench on Floor -->
{bench_xml}

        <!-- 7. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="284" y="{f(FLOOR - 4.0)}" name="FloorShadow">
            <Ellipse width="320" height="22" name="ShadowEllipse"/>
            <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="160" endY="0" name="ShadowGrad">
                <GradientStop colorValue="8C020617" position="0"/>
                <GradientStop colorValue="00020617" position="1"/>
            </RadialGradient></Fill>
        </Shape>
        <Shape name="FloorLine">
            <PointsPath isClosed="false" name="FloorLinePath">
                <StraightVertex x="20" y="{f(FLOOR)}" radius="0"/>
                <StraightVertex x="620" y="{f(FLOOR)}" radius="0"/>
            </PointsPath>
            <Stroke thickness="1.2" name="FloorStroke"><LinearGradient startX="20" startY="{f(FLOOR)}" endX="620" endY="{f(FLOOR)}" name="FloorGrad">
                <GradientStop colorValue="00475569" position="0"/>
                <GradientStop colorValue="8864748B" position="0.5"/>
                <GradientStop colorValue="00475569" position="1"/>
            </LinearGradient></Stroke>
        </Shape>
        <Shape x="{W // 2}" y="{H // 2}" name="Backdrop">
            <Rectangle width="{W}" height="{H}" name="BgRect"/>
            <Fill name="BgFill"><RadialGradient startX="-40" startY="-40" endX="380" endY="250" name="BgGrad">
                <GradientStop colorValue="FF1E293B" position="0"/>
                <GradientStop colorValue="FF0F172A" position="0.65"/>
                <GradientStop colorValue="FF090D16" position="1"/>
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="DumbbellRow" id="0:60">
{keyed_objects_xml}
        </LinearAnimation>
    </Artboard>
</Rive>
"""


# ---------------------------------------------------------------- Verbatim Rive 7.3 Binary Compiler (52-byte TOC)
def _compile_rml_bytes(rml_path):
    """Byte-for-byte Rive 7.3 binary compiler matching `~/.rive/bin/rive . --once`."""
    import struct

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
    riv_out = HERE / "dumbbell_row.riv"
    riv_out.write_bytes(riv_bytes)

    repo = HERE.parent.parent
    riv_dest = repo / "assets/animations/dumbbell_row.riv"
    thumb_dest = repo / "assets/animations/thumbnails/dumbbell_row.png"
    riv_dest.write_bytes(riv_bytes)

    legacy_mk = repo / "assets/animations/dumbbell_row.movekit"
    if legacy_mk.exists():
        legacy_mk.unlink()

    print("published", riv_dest, thumb_dest)


if __name__ == "__main__":
    import sys
    xml = build_rml()
    OUT.write_text(xml)
    print("keyed props:", len(KEYED), "bytes:", len(xml))
    if "--publish" in sys.argv:
        publish()
