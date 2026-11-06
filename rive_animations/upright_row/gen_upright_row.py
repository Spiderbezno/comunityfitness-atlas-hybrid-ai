#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive 7.3 scene for Barbell Upright Row (id: 'upright_row').

Uses our canonical standing 3/4 front-left CommunityFitness anatomical mannequin (volumetric 3/4 head
with cropped dark hair, ear, brow, eye, nose/jawline; muscular neck; sculpted pectorals, 6-pack rectus
abdominis, serratus/obliques; dark athletic compression shorts; quadriceps, gastrocnemius calves, and
planted bare feet).

Biomechanics & Visual Choreography (Standing Barbell Upright Row):
  - Bottom Hang (f = 0 & f = 160, r = 0.0):
    * Athlete stands tall in a balanced 3/4 front-left stance holding a loaded 3-plate Olympic barbell
      with a pronated shoulder-width grip across the upper thighs (`bar_center = (310, 186)`).
  - Peak Upright Pull (f = 72, r = 1.0):
    * Athlete pulls the barbell vertically close to the torso up to upper-chest / clavicle height
      (`bar_center = (310, 108)`), driving both elbows high and wide (`elbow_near = (388, 78)`,
      `elbow_far = (246, 75)` — well above the wrists and shoulders in the classic V-shaped upright row posture).
  - Highlighted Target & Synergist Muscle Groups (pulsing warm orange #FFF97316 -> crimson #FFF43F5E):
    1. Lateral deltoid (Primary — multipennate middle head of left & right shoulder caps)
    2. Anterior deltoid (Primary — front clavicular head of left & right shoulder caps)
    3. Upper trapezius (Primary/Synergist — bilateral collar-to-neck muscular wedges elevating the shoulder girdle)
    4. Brachioradialis & Biceps brachii (Synergists — pronated-grip elbow flexors on both forearms and upper arms)

Run:
    python3 rive_animations/upright_row/gen_upright_row.py            # writes scene.rml
    python3 rive_animations/upright_row/gen_upright_row.py --publish  # compiles assets/animations/upright_row.riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/upright_row.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/upright_row.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps loop
STEP = 2

# Canonical Limb Lengths (3/4 front-left hero stance)
UPPER_ARM_LEN = 47.0
FOREARM_LEN = 44.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
PLATE_DARK = ("FF334155", "FF182232", "FF090D16")
STEEL_BAR = ("FFF8FAFC", "FF94A3B8", "FF475569")
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


EASE_PULL_UP = cubic_bezier(0.36, 0.0, 0.24, 1.0)
EASE_LOWER_DOWN = cubic_bezier(0.42, 0.0, 0.36, 1.0)


def pull_progress(frame):
    """Returns upright-row progress r in [0.0, 1.0] across 160 frames:
    - 0..12:   Bottom hang hold across upper thighs (r = 0.0)
    - 12..64:  Concentric vertical pull (r: 0.0 -> 1.0: elbows drive high & wide, bar rises to clavicles)
    - 64..84:  Peak contraction hold at clavicle height (r = 1.0)
    - 84..148: Controlled eccentric lowering (r: 1.0 -> 0.0)
    - 148..160: Bottom hang hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 64:
        return EASE_PULL_UP((fr - 12) / 52.0)
    if fr <= 84:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_LOWER_DOWN((fr - 84) / 64.0)
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
    sc = max(0.60, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute Standing Barbell Upright Row transforms at progress r in [0.0, 1.0]."""
    # 1. Shoulder Girdle & Upper Trapezius Elevation (subtle 6 px upward scapular rotation at peak pull)
    sh_near = (lerp(348.0, 349.0, r), lerp(100.0, 94.0, r))
    sh_far = (lerp(288.0, 287.0, r), lerp(98.0, 92.0, r))
    traps_dy = lerp(0.0, -5.5, r)
    traps_sy = lerp(1.0, 1.24, r)

    # 2. Vertical Close-to-Torso Barbell Path & Pronated Shoulder-Width Hands
    bar_x = lerp(310.0, 309.0, r)
    bar_y = lerp(186.0, 115.0, r)
    bar_rot = math.radians(3.8)
    cs, sn = math.cos(bar_rot), math.sin(bar_rot)

    # Hands placed at +/- 21 px from bar center along the 3/4 barbell shaft
    grip_half = 21.0
    hand_near = (bar_x + grip_half * cs, bar_y + grip_half * sn)
    hand_far = (bar_x - grip_half * cs, bar_y - grip_half * sn)

    # 3. Near (Left / Screen-Right) Arm High-Elbow Upright Pull Trajectory:
    #    - r = 0.0 (Bottom Hang): elbow=(345, 144), hand=(331, 187.4)
    #    - r = 0.5 (Mid Pull):    elbow=(376, 114), hand=(330.5, 151.9)
    #    - r = 1.0 (Peak Pull):   elbow=(388, 79),  hand=(330, 116.4) -> elbow is 37.4 px ABOVE wrist!
    elbow_near = quad_interp_pt((345.0, 144.0), (376.0, 114.0), (388.0, 79.0), r)
    ua_near_ang, ua_near_sc = seg_xform(sh_near, elbow_near, UPPER_ARM_LEN)
    fa_near_ang, fa_near_sc = seg_xform(elbow_near, hand_near, FOREARM_LEN)
    delt_near_ang = math.radians(lerp(0.0, -64.0, r))

    # 4. Far (Right / Screen-Left) Arm High-Elbow Upright Pull Trajectory:
    #    - r = 0.0 (Bottom Hang): elbow=(281, 141), hand=(289, 184.6)
    #    - r = 0.5 (Mid Pull):    elbow=(254, 111), hand=(288.5, 149.1)
    #    - r = 1.0 (Peak Pull):   elbow=(246, 76),  hand=(288, 113.6) -> elbow is 37.6 px ABOVE wrist!
    elbow_far = quad_interp_pt((281.0, 141.0), (254.0, 111.0), (246.0, 76.0), r)
    ua_far_ang, ua_far_sc = seg_xform(sh_far, elbow_far, UPPER_ARM_LEN)
    fa_far_ang, fa_far_sc = seg_xform(elbow_far, hand_far, FOREARM_LEN)
    delt_far_ang = math.radians(lerp(0.0, 58.0, r))

    return {
        "r": r,
        "sh_near": sh_near,
        "sh_far": sh_far,
        "traps_dy": traps_dy,
        "traps_sy": traps_sy,
        "bar_x": bar_x,
        "bar_y": bar_y,
        "bar_rot": bar_rot,
        "elbow_near": elbow_near,
        "hand_near": hand_near,
        "ua_near_ang": ua_near_ang,
        "ua_near_sc": ua_near_sc,
        "fa_near_ang": fa_near_ang,
        "fa_near_sc": fa_near_sc,
        "delt_near_ang": delt_near_ang,
        "elbow_far": elbow_far,
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
POSES = {fr: pose(pull_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = (
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


# ---------------------------------------------------------------- 1. 3D Loaded Olympic Barbell & Pronated Grip Hands
def build_olympic_barbell():
    """Builds the 3D Loaded Olympic Barbell with 3 stepped black cast-iron weight plates on both ends,
    chrome sleeves, knurled shaft, and pronated gripping hands at +/- 21 px."""
    ind = "        "
    i2 = ind + "    "
    bar_id = nid()
    key_double(bar_id, 13, lambda p: p["bar_x"])
    key_double(bar_id, 14, lambda p: p["bar_y"])
    p0 = POSES[0]

    plate_face = (
        '<Fill name="BarPlateFaceFill">' + grad3("BarPlateFaceGrad", -26, 26, *PLATE_DARK, x0=-12, x1=12) + "</Fill>"
        '<Stroke thickness="1.15" name="BarPlateFaceStroke"><SolidColor colorValue="FF475569" name="BarPlateFaceStrokeCol"/></Stroke>'
    )
    plate_rim = (
        '<Fill name="BarPlateRimFill"><SolidColor colorValue="FF020617" name="BarPlateRimCol"/></Fill>'
        '<Stroke thickness="0.95" name="BarPlateRimStroke"><SolidColor colorValue="FF1E293B" name="BarPlateRimStrokeCol"/></Stroke>'
    )
    plate_groove = (
        '<Stroke thickness="1.0" name="BarPlateGrooveStroke"><SolidColor colorValue="FF334155" name="BarPlateGrooveCol"/></Stroke>'
    )
    hub_paint = (
        '<Fill name="BarHubFill">' + grad("BarHubGrad", -4, -6, 4, 6, "FFE2E8F0", "FF475569") + "</Fill>"
        '<Stroke thickness="0.85" name="BarHubStroke"><SolidColor colorValue="FF0F172A" name="BarHubStrokeCol"/></Stroke>'
    )

    near_fist_pts = [
        (14.5, -5.5), (27.5, -5.5), (28.5, 0.5), (27.0, 6.2), (14.5, 6.2), (13.5, 0.5),
    ]
    far_fist_pts = [
        (-27.5, -5.2), (-14.5, -5.2), (-13.5, 0.5), (-14.5, 5.8), (-27.0, 5.8), (-28.5, 0.5),
    ]

    out = [
        f'{ind}<Node x="{f(p0["bar_x"])}" y="{f(p0["bar_y"])}" '
        f'rotation="{f(p0["bar_rot"])}" name="OlympicBarbellNode" id="{bar_id}">'
    ]

    # 1. Near (Left / Screen-Right `+X`) 3 Stepped Olympic Weight Plates & Outer Sleeve Tip
    out.append(ellipse_shape(i2, "NearSleeveCap", 76.5, 0.0, 5.5, 9.5, hub_paint))
    out.append(polyline_stroke_shape(i2, "NearSleeveTip", [(69.0, 0.0), (76.0, 0.0)], 6.5, "FF94A3B8"))
    # Outer 3rd Plate
    out.append(ellipse_shape(i2, "NearPlate3Face", 67.5, 0.0, 17.5, 32.0, plate_face))
    out.append(ellipse_shape(i2, "NearPlate3Rim", 65.5, 0.0, 17.5, 32.0, plate_rim))
    # Middle 2nd Plate
    out.append(ellipse_shape(i2, "NearPlate2Groove", 61.5, 0.0, 15.5, 29.0, plate_groove))
    out.append(ellipse_shape(i2, "NearPlate2Face", 61.5, 0.0, 21.0, 39.0, plate_face))
    out.append(ellipse_shape(i2, "NearPlate2Rim", 59.5, 0.0, 21.0, 39.0, plate_rim))
    # Inner 1st Plate
    out.append(ellipse_shape(i2, "NearPlate1Groove", 55.0, 0.0, 18.5, 35.0, plate_groove))
    out.append(ellipse_shape(i2, "NearPlate1Face", 55.0, 0.0, 24.5, 46.0, plate_face))
    out.append(ellipse_shape(i2, "NearPlate1Rim", 52.8, 0.0, 24.5, 46.0, plate_rim))
    out.append(ellipse_shape(i2, "NearInnerCollar", 49.0, 0.0, 6.5, 11.5, hub_paint))

    # 2. Pronated Gripping Hands Wrapped Over Barbell Shaft (`x = +21` and `x = -21`)
    out.append(stroke_shape(i2, "NearKnuckle1", [(17.5, -4.5), (17.5, 4.8)], 0.95, SOFT_SHADOW, 0.2))
    out.append(stroke_shape(i2, "NearKnuckle2", [(21.0, -4.8), (21.0, 5.0)], 0.95, SOFT_SHADOW, 0.2))
    out.append(stroke_shape(i2, "NearKnuckle3", [(24.5, -4.5), (24.5, 4.8)], 0.95, SOFT_SHADOW, 0.2))
    out.append(stroke_shape(i2, "NearFistHi", [(16.0, -3.0), (26.0, -3.0)], 1.8, HIGHLIGHT, 1.5))
    out.append(smooth_shape(i2, "NearGripFist", near_fist_pts, skin_fill("NearFist", -6, 6, SKIN)))

    out.append(stroke_shape(i2, "FarKnuckle1", [(-24.5, -4.2), (-24.5, 4.5)], 0.95, SOFT_SHADOW, 0.2))
    out.append(stroke_shape(i2, "FarKnuckle2", [(-21.0, -4.5), (-21.0, 4.8)], 0.95, SOFT_SHADOW, 0.2))
    out.append(stroke_shape(i2, "FarKnuckle3", [(-17.5, -4.2), (-17.5, 4.5)], 0.95, SOFT_SHADOW, 0.2))
    out.append(stroke_shape(i2, "FarFistHi", [(-26.0, -2.8), (-16.0, -2.8)], 1.6, HIGHLIGHT, 1.4))
    out.append(smooth_shape(i2, "FarGripFist", far_fist_pts, skin_fill("FarFist", -6, 6, SKIN_FAR)))

    # 3. Chrome Olympic Barbell Shaft (`x = -52..+52`)
    out.append(polyline_stroke_shape(i2, "BarbellShaftHi", [(-49.0, -1.2), (49.0, -1.2)], 1.4, "FFFFFFFF", radius=0.4))
    out.append(polyline_stroke_shape(i2, "BarbellKnurlL", [(-38.0, 0.0), (-8.0, 0.0)], 4.8, "FF64748B", radius=0.4))
    out.append(polyline_stroke_shape(i2, "BarbellKnurlR", [(8.0, 0.0), (38.0, 0.0)], 4.8, "FF64748B", radius=0.4))
    out.append(polyline_stroke_shape(i2, "BarbellShaftCore", [(-52.0, 0.0), (52.0, 0.0)], 4.6, "FFCBD5E1", radius=0.8))

    # 4. Far (Right / Screen-Left `-X`) 3 Stepped Olympic Weight Plates
    out.append(ellipse_shape(i2, "FarInnerCollar", -49.0, 0.0, 6.2, 11.0, hub_paint))
    out.append(ellipse_shape(i2, "FarPlate1Groove", -54.0, 0.0, 17.5, 33.5, plate_groove))
    out.append(ellipse_shape(i2, "FarPlate1Face", -54.0, 0.0, 23.0, 44.0, plate_face))
    out.append(ellipse_shape(i2, "FarPlate1Rim", -56.0, 0.0, 23.0, 44.0, plate_rim))
    out.append(ellipse_shape(i2, "FarPlate2Groove", -60.0, 0.0, 14.5, 27.5, plate_groove))
    out.append(ellipse_shape(i2, "FarPlate2Face", -60.0, 0.0, 19.5, 37.5, plate_face))
    out.append(ellipse_shape(i2, "FarPlate2Rim", -62.0, 0.0, 19.5, 37.5, plate_rim))
    out.append(ellipse_shape(i2, "FarPlate3Face", -65.5, 0.0, 16.5, 30.5, plate_face))
    out.append(ellipse_shape(i2, "FarPlate3Rim", -67.5, 0.0, 16.5, 30.5, plate_rim))
    out.append(polyline_stroke_shape(i2, "FarSleeveTip", [(-74.0, 0.0), (-67.0, 0.0)], 6.0, "FF64748B"))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 2. Upright Row Arm + Shoulder Cap (Lateral & Anterior Deltoid + Biceps/Brachioradialis)
def upright_row_arm_rig(prefix, far):
    """Builds the Near (Left) or Far (Right) arm with highlighted Lateral Deltoid, Anterior Deltoid,
    Biceps Brachii, and Brachioradialis."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    sh_k = "sh_far" if far else "sh_near"
    ua_ang_k = "ua_far_ang" if far else "ua_near_ang"
    ua_sc_k = "ua_far_sc" if far else "ua_near_sc"
    el_k = "elbow_far" if far else "elbow_near"
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

    def lat_delt_t(p):
        return 0.46 + 0.54 * (p["r"] ** 0.74)

    def ant_delt_t(p):
        return 0.42 + 0.54 * (p["r"] ** 0.78)

    def arm_flex_t(p):
        return 0.38 + 0.54 * (p["r"] ** 0.80)

    if not far:
        delt_base_pts = [
            (-14.5, -3.5), (-6.5, -11.0), (5.0, -10.5), (13.5, -3.5),
            (14.5, 6.5), (9.0, 16.5), (-2.0, 17.5), (-11.5, 10.5),
        ]
        ant_delt_pts = [
            (-14.0, -3.5), (-6.0, -10.2), (2.2, -9.2), (0.8, 5.0), (-8.5, 12.0), (-13.2, 4.5),
        ]
        lat_delt_pts = [
            (1.2, -9.5), (10.5, -6.8), (14.2, 3.0), (9.5, 15.8), (0.0, 16.8), (-2.5, 5.0),
        ]
        biceps_pts = [
            (8.0, 0.5), (24.0, 0.2), (38.0, 2.0),
            (35.0, 8.2), (21.0, 10.0), (8.0, 8.8),
        ]
        brachio_pts = [
            (0.0, -5.8), (14.0, -6.8), (28.0, -4.8),
            (32.0, -1.2), (22.0, 2.0), (6.0, 1.5),
        ]
    else:
        delt_base_pts = [
            (-16.0, -3.5), (-8.5, -10.5), (4.5, -9.5), (10.5, -1.5),
            (9.5, 9.0), (0.5, 13.5), (-12.5, 9.5),
        ]
        ant_delt_pts = [
            (-15.5, -3.5), (-8.0, -10.0), (3.0, -8.5), (2.0, 5.0), (-9.5, 9.5), (-14.5, 3.5),
        ]
        lat_delt_pts = [
            (-14.5, -5.0), (-5.5, -10.2), (6.5, -6.5), (9.5, 3.5), (2.5, 11.0), (-8.5, 8.5),
        ]
        biceps_pts = [
            (8.0, -0.5), (24.0, -0.2), (38.0, -2.0),
            (35.0, -7.8), (21.0, -9.2), (8.0, -8.2),
        ]
        brachio_pts = [
            (0.0, 5.5), (14.0, 6.4), (28.0, 4.5),
            (32.0, 1.2), (22.0, -1.8), (6.0, -1.2),
        ]

    ua_pts = [
        (-8, 0), (-6, 8.5), (8, 10.2), (24, 10.5), (38, 8.5), (44, 5.8),
        (49, 0), (44, -5.8), (32, -9.2), (16, -9.8), (3, -9.2), (-6, -7.2),
    ]
    fa_pts = [
        (-5, 0), (-3, 6.8), (10, 8.2), (24, 6.8), (35, 4.8), (41, 3.8),
        (45, 0), (41, -3.8), (33, -4.8), (19, -6.5), (5, -7.2), (-3, -5.8),
    ]

    out = [f'{ind}<Node name="{prefix}UprightRowArmGroup">']

    # Layer A: Deltoid Cap at SHOULDER (Lateral deltoid + Anterior deltoid)
    out.append(
        f'{i2}<Node x="{f(p0[sh_k][0])}" y="{f(p0[sh_k][1])}" rotation="{f(p0[delt_ang_k])}" name="{prefix}DeltoidCap" id="{delt_id}">'
    )
    if not far:
        out.append(stroke_shape(i3, f"{prefix}DeltSplitLine", [(-1, -8.0), (0, 3.0), (-3, 11.5)], 1.15, "807F1D1D", 0.3))
        out.append(stroke_shape(i3, f"{prefix}AntDeltFiber", [(-8.5, -4.5), (-5.5, 6.0)], 1.0, "667F1D1D", 0.3))
        out.append(stroke_shape(i3, f"{prefix}LatDeltFiber1", [(4.5, -5.5), (6.5, 9.5)], 1.0, "667F1D1D", 0.3))
        out.append(stroke_shape(i3, f"{prefix}LatDeltFiber2", [(8.5, -2.5), (9.5, 10.5)], 0.95, "667F1D1D", 0.3))
        out.append(stroke_shape(i3, f"{prefix}LatDeltHi", [(4.0, -4.0), (8.5, 4.5)], 2.2, HIGHLIGHT, 2.0))
    out.append(smooth_shape(i3, f"{prefix}LateralDeltoid", lat_delt_pts, muscle_paint_fn(prefix + "LatDelt", lat_delt_t, 1.05)))
    out.append(smooth_shape(i3, f"{prefix}AnteriorDeltoid", ant_delt_pts, muscle_paint_fn(prefix + "AntDelt", ant_delt_t, 1.0)))
    out.append(smooth_shape(i3, f"{prefix}DeltoidBase", delt_base_pts, skin_fill(prefix + "DeltBase", -11, 17, skin)))
    out.append(f"{i2}</Node>")

    # Layer B: Forearm with Highlighted Brachioradialis (ELBOW -> HAND)
    out.append(
        f'{i2}<Node x="{f(p0[el_k][0])}" y="{f(p0[el_k][1])}" '
        f'rotation="{f(p0[fa_ang_k])}" scaleX="{f(p0[fa_sc_k])}" name="{prefix}Forearm" id="{fa_id}">'
    )
    hi_y = 3.2 if far else -3.2
    sh_y = -4.2 if far else 4.2
    out.append(stroke_shape(i3, f"{prefix}BrachioFiber", [(6, hi_y * 0.7), (24, hi_y * 0.5)], 1.0, "737F1D1D", 0.3))
    out.append(smooth_shape(i3, f"{prefix}Brachioradialis", brachio_pts, muscle_paint_fn(prefix + "Brachio", arm_flex_t, 0.92)))
    out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(8, hi_y), (22, hi_y * 0.9), (34, hi_y * 0.65)], 2.2, HIGHLIGHT, 2.6))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(6, sh_y), (22, sh_y * 0.95), (34, sh_y * 0.7)], 3.4, CORE_SHADOW, 3.5))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -7, 8, skin)))
    out.append(f"{i2}</Node>")

    # Layer C: Upper Arm with Highlighted Biceps Brachii (SHOULDER -> ELBOW)
    out.append(
        f'{i2}<Node x="{f(p0[sh_k][0])}" y="{f(p0[sh_k][1])}" rotation="{f(p0[ua_ang_k])}" scaleX="{f(p0[ua_sc_k])}" name="{prefix}UpperArm" id="{ua_id}">'
    )
    ua_hi_y = 5.2 if far else -5.2
    ua_sh_y = -6.5 if far else 6.5
    out.append(smooth_shape(i3, f"{prefix}BicepsBrachii", biceps_pts, muscle_paint_fn(prefix + "Biceps", arm_flex_t, 0.92)))
    out.append(stroke_shape(i3, f"{prefix}BicepsLine", [(14, 0.5), (28, 0.5), (40, 0.2)], 1.2, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}UpperArmHi", [(14, ua_hi_y), (28, ua_hi_y), (40, ua_hi_y * 0.8)], 2.6, HIGHLIGHT, 2.8))
    out.append(stroke_shape(i3, f"{prefix}UpperArmSh", [(12, ua_sh_y), (28, ua_sh_y), (40, ua_sh_y * 0.8)], 3.8, CORE_SHADOW, 3.8))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UpperArm", -10, 11, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. Canonical Standing 3/4 Athlete Body with Activated Upper Trapezius
def torso_and_head():
    """Standing 3/4 front-left torso, activated Upper Trapezius wedges, sculpted pectorals,
    6-pack abs, dark athletic compression shorts, and volumetric 3/4 head."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    traps_id = nid()
    key_double(traps_id, 14, lambda p: 92.0 + p["traps_dy"])
    key_double(traps_id, 17, lambda p: p["traps_sy"])
    p0 = POSES[0]

    def upper_trap_t(p):
        return 0.44 + 0.54 * (p["r"] ** 0.74)

    head_pts = [
        (304.0, 50.0), (301.5, 56.5), (300.0, 62.5), (301.2, 67.5),
        (301.8, 73.5), (307.5, 76.5), (316.5, 75.0), (323.5, 71.0),
        (328.5, 63.0), (328.0, 52.0), (321.0, 45.0), (311.0, 45.0),
    ]
    hair_pts = [
        (303.5, 52.0), (309.0, 44.5), (320.5, 44.2), (328.5, 50.5),
        (329.0, 61.5), (324.5, 65.5), (323.0, 57.5), (318.0, 52.5),
        (310.5, 51.0),
    ]
    head_hi = [(304.5, 54.0), (308.5, 49.0), (317.0, 48.0)]
    cheek_hi = [(303.5, 61.5), (309.5, 63.0), (315.0, 62.0)]
    jaw_sh = [(304.0, 75.5), (313.0, 76.2), (320.5, 72.5)]

    neck_pts = [
        (306.5, 73.0), (322.5, 70.0), (328.5, 86.0),
        (328.0, 94.0), (301.0, 93.0), (304.5, 83.0),
    ]
    scm_line = [(320.0, 72.5), (315.5, 82.0), (312.5, 90.5)]

    # Target Muscle #3: Bilateral Upper Trapezius Collar Wedges (local to (316, 92))
    near_upper_trap_pts = [
        (4.5, -17.5), (14.5, -12.0), (30.5, -2.0),
        (31.5, 5.5), (16.0, 4.5), (2.5, 0.5),
    ]
    far_upper_trap_pts = [
        (-9.5, -16.0), (-18.0, -10.5), (-28.5, -2.0),
        (-28.0, 4.5), (-15.5, 3.5), (-8.0, 0.5),
    ]

    torso_pts = [
        (287.0, 91.0), (313.0, 88.5), (347.0, 93.0),
        (350.0, 113.0), (342.5, 134.0), (335.5, 154.0),
        (338.0, 174.0), (315.0, 182.0), (293.0, 174.0),
        (296.0, 152.0), (294.0, 132.0), (286.0, 111.0),
    ]
    torso_hi = [(299.0, 98.0), (301.0, 122.0), (303.0, 146.0)]
    torso_sh = [(340.0, 116.0), (334.5, 138.0), (330.5, 154.0)]

    pec_near_pts = [
        (313.5, 92.5), (339.5, 95.0), (345.5, 108.0),
        (339.5, 119.5), (325.0, 121.5), (313.0, 117.5),
    ]
    pec_far_pts = [
        (289.5, 93.0), (312.5, 92.5), (312.0, 117.0),
        (298.5, 119.0), (288.0, 112.0), (287.5, 100.5),
    ]
    pec_paint = (
        '<Fill name="PecFill"><SolidColor colorValue="120F172A" name="PecCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="PecStroke"><SolidColor colorValue="380F172A" name="PecStrokeCol"/></Stroke>'
    )

    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1A0F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="AbsEdge"><SolidColor colorValue="400F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        [(313.0, 121.0), (325.0, 121.5), (325.5, 130.0), (312.8, 129.5)],
        [(312.6, 131.5), (324.8, 132.0), (324.2, 140.5), (312.4, 140.0)],
        [(312.2, 142.0), (323.5, 142.5), (322.0, 151.5), (312.0, 151.0)],
        [(301.5, 121.0), (310.5, 121.0), (310.3, 129.5), (301.2, 129.0)],
        [(301.2, 131.0), (310.2, 131.5), (310.0, 140.0), (301.2, 139.5)],
        [(301.5, 141.5), (309.8, 142.0), (309.5, 151.0), (302.0, 150.5)],
    ]

    pelvis_shorts = [
        (296.0, 153.0), (313.0, 155.0), (336.0, 154.0),
        (341.0, 176.0), (322.0, 186.0), (311.0, 184.0), (292.0, 176.0),
    ]

    out = [f'{ind}<Node name="TorsoAndHead">']

    # 1. Volumetric 3/4 Head
    out.append(smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 304, 44, 329, 65, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i2, "Ear", 321.5, 64.5, 5.5, 8.5, solid("Ear", "FFA3B1C4"), rot_deg=12.0))
    out.append(stroke_shape(i2, "BrowShade", [(301.5, 56.8), (306.0, 57.2)], 1.4, "590F172A", 0.8))
    out.append(stroke_shape(i2, "EyeLine", [(303.2, 58.6), (306.2, 58.8)], 1.1, "730F172A", 0.4))
    out.append(stroke_shape(i2, "MouthLine", [(301.5, 68.5), (305.0, 68.8)], 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i2, "HeadHi", head_hi, 3.0, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i2, "CheekHi", cheek_hi, 2.2, "80FFFFFF", 2.5))
    out.append(stroke_shape(i2, "JawShadow", jaw_sh, 2.6, CORE_SHADOW, 2.5))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill("Head", 45, 77, SKIN, x0=300, x1=328)))

    # 2. Activated Upper Trapezius Collar
    out.append(
        f'{i2}<Node x="316" y="{f(92.0 + p0["traps_dy"])}" scaleY="{f(p0["traps_sy"])}" name="UpperTrapeziusNode" id="{traps_id}">'
    )
    out.append(stroke_shape(i3, "NearTrapHi", [(7.0, -12.0), (18.0, -6.5), (27.0, -1.0)], 2.2, HIGHLIGHT, 2.0))
    out.append(stroke_shape(i3, "NearTrapFiber", [(5.5, -10.5), (17.5, -4.5), (28.0, 1.0)], 1.0, "807F1D1D", 0.3))
    out.append(smooth_shape(i3, "NearUpperTrapezius", near_upper_trap_pts, muscle_paint_fn("NearUpperTrap", upper_trap_t, 1.05)))
    out.append(stroke_shape(i3, "FarTrapHi", [(-11.0, -11.0), (-20.0, -6.0), (-25.0, -1.0)], 1.8, HIGHLIGHT, 1.8))
    out.append(smooth_shape(i3, "FarUpperTrapezius", far_upper_trap_pts, muscle_paint_fn("FarUpperTrap", upper_trap_t, 1.0)))
    out.append(f"{i2}</Node>")

    # 3. Muscular Neck & Clavicles
    out.append(stroke_shape(i2, "UnderChinShadow", [(306.5, 76.5), (313.5, 77.5), (320.0, 74.5)], 3.2, CORE_SHADOW, 2.5))
    out.append(stroke_shape(i2, "SCMLine", scm_line, 1.5, SOFT_SHADOW, 1.5))
    out.append(stroke_shape(i2, "ClavicleLine", [(296.0, 92.5), (312.5, 92.0), (336.0, 94.5)], 1.5, SOFT_SHADOW, 1.2))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", 70, 94, SKIN)))

    # 4. Pelvis Shorts & Waistband
    out.append(stroke_shape(i2, "WaistbandLine", [(296.5, 155.5), (314.0, 157.5), (335.5, 156.5)], 1.8, "660F172A", 0.8))
    out.append(stroke_shape(i2, "ShortsFlyLine", [(312.0, 157.5), (311.5, 176.0)], 1.3, "660F172A", 0.8))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill("PelvisShorts", 153, 186, SHORTS)))

    # 5. 6-Pack Abs, Obliques & Sculpted Pectorals
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "LineaAlba", [(312.0, 118.0), (311.5, 136.0), (311.0, 153.0)], 1.3, "470F172A", 0.8))
    out.append(stroke_shape(i2, "ObliqueLine1", [(336.0, 134.0), (330.0, 140.0), (326.0, 145.0)], 1.3, "380F172A", 1.0))
    out.append(stroke_shape(i2, "ObliqueLine2", [(334.0, 142.0), (328.0, 148.0), (324.0, 152.0)], 1.3, "380F172A", 1.0))

    out.append(stroke_shape(i2, "PecNearLowerSh", [(312.5, 118.0), (324.5, 122.0), (338.0, 119.5)], 2.4, CORE_SHADOW, 2.0))
    out.append(stroke_shape(i2, "PecFarLowerSh", [(293.0, 113.0), (301.0, 119.5), (311.0, 117.5)], 2.2, CORE_SHADOW, 2.0))
    out.append(stroke_shape(i2, "PecNearHi", [(316.0, 105.0), (328.0, 106.5), (337.0, 109.0)], 2.6, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i2, "PecNear", pec_near_pts, pec_paint))
    out.append(smooth_shape(i2, "PecFar", pec_far_pts, pec_paint))

    # 6. Torso Base
    out.append(stroke_shape(i2, "TorsoHi", torso_hi, 4.5, HIGHLIGHT, 4.5))
    out.append(stroke_shape(i2, "TorsoSh", torso_sh, 6.0, CORE_SHADOW, 5.5))
    out.append(smooth_shape(i2, "Torso", torso_pts, skin_fill("Torso", 89, 182, SKIN, x0=294, x1=346)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def near_leg():
    """Near (left) leg planted on FLOOR=300 in 3/4 view."""
    ind = "        "
    i2 = ind + "    "

    shorts_pts = [
        (313.0, 168.0), (339.5, 166.0), (344.5, 192.0),
        (315.5, 194.0), (312.0, 178.0),
    ]
    thigh_pts = [
        (315.0, 174.0), (340.0, 172.0), (346.5, 196.0),
        (343.0, 218.0), (338.0, 232.0), (322.0, 232.0),
        (317.5, 214.0), (314.5, 194.0),
    ]
    thigh_hi = [(324.0, 192.0), (325.0, 210.0), (326.0, 224.0)]
    thigh_sh = [(341.0, 192.0), (340.0, 212.0), (336.0, 228.0)]
    quad_med_line = [(324.0, 200.0), (321.0, 214.0), (324.0, 225.0)]
    quad_lat_line = [(335.0, 194.0), (336.5, 212.0), (333.5, 226.0)]

    shin_pts = [
        (322.5, 230.0), (338.0, 230.0), (346.5, 248.0),
        (345.0, 266.0), (339.5, 288.0), (328.5, 289.0),
        (325.0, 268.0), (322.0, 248.0),
    ]
    shin_hi = [(327.0, 240.0), (328.5, 262.0), (330.0, 282.0)]
    shin_sh = [(342.0, 246.0), (341.5, 264.0), (337.5, 284.0)]
    calf_cut = [(334.0, 246.0), (338.5, 258.0), (335.5, 270.0)]

    foot_pts = [
        (328.5, 286.0), (340.0, 286.0), (343.5, 297.5),
        (334.0, 300.5), (314.0, 301.5), (309.5, 297.5),
        (316.0, 292.5),
    ]

    return "\n".join([
        f'{ind}<Node name="NearLeg">',
        stroke_shape(i2, "NearShortsHem", [(315.5, 192.5), (329.5, 193.0), (344.0, 190.5)], 1.6, "660F172A", 0.6),
        smooth_shape(i2, "NearThighShorts", shorts_pts, skin_fill("NearThighShorts", 166, 194, SHORTS)),
        stroke_shape(i2, "NearQuadMedLine", quad_med_line, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearQuadLatLine", quad_lat_line, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearThighHi", thigh_hi, 4.0, HIGHLIGHT, 4.0),
        stroke_shape(i2, "NearThighSh", thigh_sh, 5.2, CORE_SHADOW, 5.0),
        smooth_shape(i2, "NearThigh", thigh_pts, skin_fill("NearThigh", 172, 232, SKIN)),
        ellipse_shape(i2, "NearKnee", 329.5, 231.0, 16.5, 15.0, skin_fill("NearKnee", -8, 8, SKIN)),
        stroke_shape(i2, "NearFootHi", [(329.0, 290.0), (319.0, 295.0), (312.5, 298.0)], 2.2, HIGHLIGHT, 2.5),
        smooth_shape(i2, "NearFoot", foot_pts, skin_fill("NearFoot", 286, 302, SKIN)),
        stroke_shape(i2, "NearCalfCut", calf_cut, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearShinHi", shin_hi, 3.2, HIGHLIGHT, 3.5),
        stroke_shape(i2, "NearShinSh", shin_sh, 4.5, CORE_SHADOW, 4.5),
        smooth_shape(i2, "NearShin", shin_pts, skin_fill("NearShin", 230, 289, SKIN)),
        f"{ind}</Node>",
    ])


def far_leg():
    """Far (right) leg planted slightly further back-left in 3/4 perspective."""
    ind = "        "
    i2 = ind + "    "

    shorts_pts = [
        (292.0, 166.0), (315.0, 168.0), (314.0, 190.0),
        (289.5, 188.0),
    ]
    thigh_pts = [
        (291.0, 172.0), (314.0, 174.0), (313.0, 198.0),
        (309.5, 224.0), (294.5, 224.0), (289.5, 204.0),
        (288.0, 186.0),
    ]
    thigh_hi = [(294.5, 188.0), (295.5, 206.0), (297.0, 220.0)]
    thigh_sh = [(309.0, 190.0), (308.0, 208.0), (306.0, 222.0)]
    quad_line = [(302.5, 192.0), (303.5, 208.0), (301.5, 220.0)]

    shin_pts = [
        (295.0, 222.0), (309.5, 222.0), (316.0, 242.0),
        (314.5, 260.0), (309.5, 281.0), (299.0, 282.0),
        (296.5, 260.0), (294.5, 242.0),
    ]
    shin_hi = [(298.5, 232.0), (299.5, 254.0), (301.0, 274.0)]
    shin_sh = [(312.0, 240.0), (311.0, 258.0), (307.5, 276.0)]

    foot_pts = [
        (299.0, 279.0), (310.0, 279.0), (313.0, 289.5),
        (303.0, 292.5), (284.0, 293.5), (279.5, 289.5),
        (286.5, 285.0),
    ]

    return "\n".join([
        f'{ind}<Node name="FarLeg">',
        smooth_shape(i2, "FarThighShorts", shorts_pts, skin_fill("FarThighShorts", 166, 190, SHORTS_FAR)),
        stroke_shape(i2, "FarQuadLine", quad_line, 1.2, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "FarThighHi", thigh_hi, 3.4, HIGHLIGHT, 3.5),
        stroke_shape(i2, "FarThighSh", thigh_sh, 4.6, CORE_SHADOW, 4.5),
        smooth_shape(i2, "FarThigh", thigh_pts, skin_fill("FarThigh", 172, 224, SKIN_FAR)),
        ellipse_shape(i2, "FarKnee", 301.5, 223.5, 15.5, 14.0, skin_fill("FarKnee", -7, 7, SKIN_FAR)),
        smooth_shape(i2, "FarFoot", foot_pts, skin_fill("FarFoot", 279, 294, SKIN_FAR)),
        stroke_shape(i2, "FarShinHi", shin_hi, 2.8, HIGHLIGHT, 3.0),
        stroke_shape(i2, "FarShinSh", shin_sh, 4.0, CORE_SHADOW, 4.0),
        smooth_shape(i2, "FarShin", shin_pts, skin_fill("FarShin", 222, 282, SKIN_FAR)),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 4. Scene Assembly & Verbatim Rive 7.3 Compiler
def build_rml():
    barbell_xml = build_olympic_barbell()
    near_arm_xml = upright_row_arm_rig("Near", far=False)
    far_arm_xml = upright_row_arm_rig("Far", far=True)
    torso_xml = torso_and_head()
    near_leg_xml = near_leg()
    far_leg_xml = far_leg()

    by_obj = {}
    for oid, kp_xml in KEYED:
        by_obj.setdefault(oid, []).append(kp_xml)
    keyed_objects_xml = "\n".join(
        f'        <KeyedObject objectId="{oid}">\n' + "\n".join(kps) + "\n        </KeyedObject>"
        for oid, kps in by_obj.items()
    )

    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"

    return f"""<Rive version="7.3">
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="UprightRow" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: 3D Loaded Olympic Barbell & Pronated Grip Hands -->
{barbell_xml}

        <!-- 2. Near (Left) High-Elbow Upright Row Arm, Lateral/Anterior Deltoid, Biceps & Brachioradialis -->
{near_arm_xml}

        <!-- 3. Far (Right) High-Elbow Upright Row Arm (in front of chest/thighs as it pulls the barbell) -->
{far_arm_xml}

        <!-- 4. Standing 3/4 Torso, Activated Upper Trapezius Collar & Volumetric Head -->
{torso_xml}

        <!-- 5. Near (Left) Leg -->
{near_leg_xml}

        <!-- 6. Far (Right) Leg -->
{far_leg_xml}

        <!-- 7. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="315" y="{f(FLOOR - 2)}" scaleX="1.18" scaleY="0.10" name="AthleteShadow">
            <Ellipse width="160" height="160" name="AthleteShadowEllipse"/>
            <Fill name="AthleteShadowFill"><RadialGradient startX="0" startY="0" endX="80" endY="0" name="AthleteShadowGrad">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="UprightRow" id="0:60">
{keyed_objects_xml}
        </LinearAnimation>
    </Artboard>
</Rive>
"""


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
    (BUILD / "upright_row.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/4e7c145c-8979-4261-8c65-b2223a6aa784/scratch")
    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (38, "frame_mid"), (72, "frame_peak")):
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
