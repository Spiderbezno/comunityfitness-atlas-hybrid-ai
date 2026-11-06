#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive 7.3 scene for Preacher Curl (id: 'preacher_curl').

Uses our canonical 3/4 front-right CommunityFitness mannequin (volumetric 3/4 head with hair/ear/brow/eye/mouth,
muscular neck, sculpted deltoids, pectorals, ribcage & 6-pack abs, dark athletic compression shorts, quadriceps,
gastrocnemius calves, and planted bare feet) seated at a 3D Preacher Curl Bench holding a loaded EZ-Curl Barbell.

Matches the 2-panel 3/4 front-right Seated EZ-Bar Preacher Curl reference illustration (media_1793715234106_6602fc62.jpg):
  - 3D Seated Preacher Curl Bench:
    * White/silver powder-coated steel frame with rear seat post, horizontal base rails, front vertical upright post
      (`x = 294..306`) with black barbell catch cradle (`(296, 198)`), and forward-right barbell catch upright (`x = 408..418`)
      with black J-hook cradle (`(412, 184)`).
    * Dark padded seat cushion (`(224, 196)` to `(292, 204)`) and 3D angled preacher arm pad (`(248, 134)` to `(368, 174)`).
  - Left Panel (f = 0 & f = 160, r = 0.0 — Full Arm Extension on Preacher Pad):
    * Both upper arms and triceps rest firmly down the sloped preacher pad (`SHOULDER_NEAR = (262, 102) -> ELBOW_NEAR = (318, 152)`,
      `SHOULDER_FAR = (316, 100) -> ELBOW_FAR = (352, 148)`).
    * Forearms extend forward-downward along the pad slope holding the cambered EZ-curl barbell (`WRIST_NEAR = (350, 171)`,
      `WRIST_FAR = (383, 168)`) with a supinated (underhand) grip and large 3D dark weight plates on both sleeves.
  - Right Panel (f = 72, r = 1.0 — Peak Biceps Contraction):
    * With the upper arms strictly immobilized on the preacher pad (preventing shoulder momentum), both forearms curl the
      EZ-bar upward in a clean arc (`WRIST_NEAR = (330, 113)`, `WRIST_FAR = (363, 109)`) up to chin/shoulder height.
  - Highlighted Target Muscle Groups (pulsing from warm orange #FFF97316 to intense crimson #FFF43F5E):
    1. Biceps brachii — short head & long head (Primary — prominent two-headed anterior upper-arm belly on both arms)
    2. Brachialis (Primary — deep distal-lateral elbow flexor wedged beneath the biceps on the preacher pad)
    3. Brachioradialis (Secondary/Synergist — radial forearm belly extending across the elbow crease onto the forearm)

Run:
    python3 gen_preacher_curl.py            # writes scene.rml
    python3 gen_preacher_curl.py --publish  # compiles assets/animations/preacher_curl.riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/preacher_curl.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/preacher_curl.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps preacher curl loop
STEP = 2

# Canonical Preacher-Braced Shoulder & Elbow Anchors (3/4 front-right seated view)
SHOULDER_NEAR = (262.0, 102.0)    # Right (near / screen-left) shoulder
ELBOW_NEAR_BASE = (318.0, 152.0)  # Right (near) elbow braced on preacher pad
SHOULDER_FAR = (316.0, 100.0)     # Left (far / screen-right) shoulder
ELBOW_FAR_BASE = (352.0, 148.0)   # Left (far) elbow braced on preacher pad
FOREARM_LEN = 38.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
PLATE_DARK = ("FF334155", "FF182232", "FF090D16")
PAD_TOP = ("FF334155", "FF1E293B", "FF0F172A")
PAD_SIDE = ("FF1E293B", "FF0F172A", "FF020617")
STEEL_FRONT = ("FFF8FAFC", "FFE2E8F0", "FFCBD5E1")
STEEL_SIDE = ("FFCBD5E1", "FF94A3B8", "FF64748B")
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


EASE_CURL = cubic_bezier(0.38, 0.0, 0.24, 1.0)
EASE_LOWER = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def curl_progress(frame):
    """Returns bilateral preacher-curl progress r in [0.0, 1.0] across 160 frames:
    - 0..12:   Bottom full-extension hold on preacher pad (r = 0.0, Left Panel)
    - 12..64:  Concentric EZ-bar preacher curl (r: 0.0 -> 1.0)
    - 64..84:  Peak biceps contraction hold (r = 1.0, Right Panel)
    - 84..148: Controlled eccentric lowering back to full extension (r: 1.0 -> 0.0)
    - 148..160: Bottom hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 64:
        return EASE_CURL((fr - 12) / 52.0)
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
    sc = max(0.55, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute Seated EZ-Bar Preacher Curl transforms at progress r in [0.0, 1.0].

    Matches the 2-panel reference illustration (media_1793715234106_6602fc62.jpg):
      - Upper arms remain strictly braced against the angled preacher cushion (`ELBOW_NEAR = (318, 152)`,
        `ELBOW_FAR = (352, 148)` with <= 1.0 px micro-compression).
      - Near (Right) Forearm pivots from `+32 deg` extended along the pad (`WRIST_NEAR = (349.6, 170.5)`)
        through `-20 deg` mid-curl up to `-74 deg` peak flexion (`WRIST_NEAR = (329.0, 112.5)`).
      - Far (Left) Forearm pivots in parallel keeping the EZ-curl bar along the constant 3/4 perspective
        offset `(+33.0, -3.5)`!
    """
    elbow_near = (ELBOW_NEAR_BASE[0], ELBOW_NEAR_BASE[1] - 1.0 * r)
    elbow_far = (ELBOW_FAR_BASE[0], ELBOW_FAR_BASE[1] - 1.0 * r)

    fa_near_deg = lerp(32.0, -74.0, r)
    fa_near_rad = math.radians(fa_near_deg)

    # Slight 3D foreshortening when forearm points forward-right at bottom (r=0) vs upright at top (r=1)
    len_near = FOREARM_LEN * lerp(0.92, 1.04, r)

    wrist_near = (
        elbow_near[0] + len_near * math.cos(fa_near_rad),
        elbow_near[1] + len_near * math.sin(fa_near_rad),
    )
    # Lock wrist_far to wrist_near + (33.0, -3.5) so the rigid EZ-curl barbell never stretches or skews!
    wrist_far = (
        wrist_near[0] + 33.0,
        wrist_near[1] - 3.5,
    )

    fa_near_ang, fa_near_sc = seg_xform(elbow_near, wrist_near, FOREARM_LEN)
    fa_far_ang, fa_far_sc = seg_xform(elbow_far, wrist_far, FOREARM_LEN)

    # Dynamic Biceps Brachii & Brachialis peak swelling on both braced upper arms as r -> 1.0
    biceps_swell = 1.0 + 0.16 * (r ** 0.85)
    bar_center = (0.5 * (wrist_near[0] + wrist_far[0]), 0.5 * (wrist_near[1] + wrist_far[1]))
    bar_rot = math.atan2(wrist_far[1] - wrist_near[1], wrist_far[0] - wrist_near[0])

    return {
        "r": r,
        "elbow_near": elbow_near,
        "elbow_far": elbow_far,
        "wrist_near": wrist_near,
        "wrist_far": wrist_far,
        "fa_near_ang": fa_near_ang,
        "fa_near_sc": fa_near_sc,
        "fa_far_ang": fa_far_ang,
        "fa_far_sc": fa_far_sc,
        "biceps_swell": biceps_swell,
        "bar_center": bar_center,
        "bar_rot": bar_rot,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(curl_progress(fr)) for fr in FRAMES}

_ANGLE_KEYS = (
    "fa_near_ang",
    "fa_far_ang",
    "bar_rot",
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


def polyline_stroke_shape(indent, name, pts, width, color, radius=0.8, cap="round"):
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
    fid, lid = nid(), nid()
    key_color(fid, 37, lambda p: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, fn_t(p)))
    key_color(lid, 37, lambda p: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, fn_t(p)))
    t0 = fn_t(POSES[0])
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- 1. Loaded EZ-Curl Barbell & Supinated Hands (3/4 Perspective)
def ez_barbell_and_hands_rig():
    """Renders the cambered EZ-curl barbell with large 3D dark weight plates on both ends and supinated gripping hands:
    - Split into Foreground (Near/Left Weight Plate + Gripping Hands + Cambered EZ Shaft) and Background (Far/Right Weight Plate)
      so the 3/4 depth occlusion is 100% realistic."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    bar_fg_id, bar_bg_id = nid(), nid()
    for bid in (bar_fg_id, bar_bg_id):
        key_double(bid, 13, lambda p: p["bar_center"][0])
        key_double(bid, 14, lambda p: p["bar_center"][1])
        key_double(bid, 15, lambda p: p["bar_rot"])

    p0 = POSES[0]

    plate_face = (
        f'<Fill name="EZPlateFaceFill">{grad3("EZPlateFaceGrad", -28, 28, *PLATE_DARK, x0=-18, x1=18)}</Fill>'
        '<Stroke thickness="1.25" name="EZPlateFaceStroke"><SolidColor colorValue="FF475569" name="EZPlateFaceStrokeCol"/></Stroke>'
    )
    plate_rim = (
        '<Fill name="EZPlateRimFill"><SolidColor colorValue="FF020617" name="EZPlateRimCol"/></Fill>'
        '<Stroke thickness="1.0" name="EZPlateRimStroke"><SolidColor colorValue="FF1E293B" name="EZPlateRimStrokeCol"/></Stroke>'
    )
    plate_groove = (
        '<Stroke thickness="1.1" name="EZPlateGrooveStroke"><SolidColor colorValue="FF334155" name="EZPlateGrooveCol"/></Stroke>'
    )
    collar_paint = (
        f'<Fill name="EZCollarFill">{grad("EZCollarGrad", -6, -8, 6, 8, "FFE2E8F0", "FF475569")}</Fill>'
        '<Stroke thickness="0.95" name="EZCollarStroke"><SolidColor colorValue="FF0F172A" name="EZCollarStrokeCol"/></Stroke>'
    )

    # Local coordinates relative to bar_center (midpoint of wrist_near at x=-16.6 and wrist_far at x=+16.6):
    # - Near (left-foreground) weight plate sits at x = -54.0
    # - Near (right hand) grips at x = -16.6, Far (left hand) grips at x = +16.6
    # - Cambered W-zig-zag EZ shaft runs from x = -48.0 to x = +52.0
    # - Far (right-background) weight plate sits at x = +56.0
    ez_shaft_pts = [
        (-48.0, 0.0),
        (-34.0, 0.0),
        (-24.0, 3.2),
        (-11.0, -3.5),
        (0.0, 2.8),
        (11.0, -3.5),
        (24.0, 3.2),
        (36.0, 0.0),
        (52.0, 0.0),
    ]
    hand_near_pts = [
        (-22.5, -4.8), (-11.0, -5.2), (-9.5, 0.8), (-11.5, 6.2), (-22.0, 5.5),
    ]
    hand_far_pts = [
        (11.0, -5.0), (22.0, -4.6), (23.2, 1.0), (21.0, 6.0), (11.2, 5.4),
    ]

    fg_xml = "\n".join([
        f'{ind}<Node x="{f(p0["bar_center"][0])}" y="{f(p0["bar_center"][1])}" rotation="{f(p0["bar_rot"])}" name="EZBarForeground" id="{bar_fg_id}">',
        # 1. Near (Left-Foreground) Sleeve End, Collar & Large 3D Cast-Iron Weight Plate (drawn topmost)
        polyline_stroke_shape(i2, "NearSleeveTipHi", [(-74.0, -1.0), (-54.0, -1.0)], 1.6, "FFFFFFFF", radius=0.4),
        polyline_stroke_shape(i2, "NearSleeveTip", [(-75.0, 0.0), (-53.0, 0.0)], 5.6, "FF94A3B8", radius=0.8),
        ellipse_shape(i2, "NearOuterCollar", -60.5, 0.0, 7.5, 11.5, collar_paint),
        ellipse_shape(i2, "NearPlateSpoke1", -54.0, 0.0, 26.0, 42.0, plate_groove),
        ellipse_shape(i2, "NearPlateFace", -54.0, 0.0, 37.0, 58.0, plate_face),
        ellipse_shape(i2, "NearPlateRim", -50.2, 0.0, 37.0, 58.0, plate_rim),
        ellipse_shape(i2, "NearInnerCollar", -44.5, 0.0, 7.0, 11.0, collar_paint),
        # 2. Supinated Gripping Hands & Curled Fingers on the EZ-Bar Camber
        stroke_shape(i2, "NearFinger1", [(-19.5, -4.5), (-19.0, 4.5)], 0.95, CORE_SHADOW, 0.2),
        stroke_shape(i2, "NearFinger2", [(-16.5, -4.8), (-16.0, 4.8)], 0.95, CORE_SHADOW, 0.2),
        stroke_shape(i2, "NearFinger3", [(-13.5, -4.5), (-13.0, 4.5)], 0.95, CORE_SHADOW, 0.2),
        stroke_shape(i2, "NearHandHi", [(-20.5, -2.5), (-16.0, -3.2), (-12.0, -2.2)], 1.8, HIGHLIGHT, 1.5),
        smooth_shape(i2, "NearGrippingHand", hand_near_pts, skin_fill("NearEZHand", -5, 6, SKIN)),
        stroke_shape(i2, "FarFinger1", [(13.8, -4.5), (14.2, 4.5)], 0.9, CORE_SHADOW, 0.2),
        stroke_shape(i2, "FarFinger2", [(16.8, -4.8), (17.2, 4.8)], 0.9, CORE_SHADOW, 0.2),
        stroke_shape(i2, "FarFinger3", [(19.8, -4.5), (20.2, 4.5)], 0.9, CORE_SHADOW, 0.2),
        stroke_shape(i2, "FarHandHi", [(13.0, -2.5), (17.0, -3.0), (20.8, -2.2)], 1.6, HIGHLIGHT, 1.4),
        smooth_shape(i2, "FarGrippingHand", hand_far_pts, skin_fill("FarEZHand", -5, 6, SKIN_FAR)),
        # 3. Cambered Chrome/Steel EZ-Curl Bar Shaft
        polyline_stroke_shape(i2, "EZShaftHi", ez_shaft_pts, 1.5, "FFFFFFFF", radius=2.2),
        polyline_stroke_shape(i2, "EZShaftCore", ez_shaft_pts, 4.8, "FF64748B", radius=2.2),
        f"{ind}</Node>",
    ])

    bg_xml = "\n".join([
        f'{ind}<Node x="{f(p0["bar_center"][0])}" y="{f(p0["bar_center"][1])}" rotation="{f(p0["bar_rot"])}" name="EZBarBackground" id="{bar_bg_id}">',
        # Far (Right-Background) Large 3D Cast-Iron Weight Plate & Outer Sleeve Tip
        ellipse_shape(i2, "FarInnerCollar", 47.0, 0.0, 6.5, 10.5, collar_paint),
        ellipse_shape(i2, "FarPlateSpoke1", 55.0, 0.0, 24.5, 39.0, plate_groove),
        ellipse_shape(i2, "FarPlateFace", 55.0, 0.0, 35.0, 54.0, plate_face),
        ellipse_shape(i2, "FarPlateRim", 58.5, 0.0, 35.0, 54.0, plate_rim),
        ellipse_shape(i2, "FarOuterCollar", 62.5, 0.0, 7.0, 11.0, collar_paint),
        polyline_stroke_shape(i2, "FarSleeveTipHi", [(58.0, -0.8), (68.0, -0.8)], 1.3, "FFE2E8F0", radius=0.4),
        polyline_stroke_shape(i2, "FarSleeveTip", [(57.0, 0.0), (69.0, 0.0)], 4.8, "FF64748B", radius=0.8),
        f"{ind}</Node>",
    ])

    return fg_xml, bg_xml


# ---------------------------------------------------------------- 2. Preacher-Braced Arms (Biceps Short/Long Head, Brachialis & Brachioradialis)
def build_preacher_arm(prefix, is_far):
    """Builds either the Near (Right, screen-left) or Far (Left, screen-right) Preacher Curl arm:
    - Braced Upper Arm resting along the sloped preacher cushion with glowing 2-headed Biceps Brachii
      (Short Head & Long Head) and deep Brachialis.
    - Pivoting Forearm with glowing Brachioradialis along its radial (-Y) upper border."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if is_far else SKIN
    sx, sy = SHOULDER_FAR if is_far else SHOULDER_NEAR
    ex, ey = ELBOW_FAR_BASE if is_far else ELBOW_NEAR_BASE
    el_k = "elbow_far" if is_far else "elbow_near"
    fa_ang_k = "fa_far_ang" if is_far else "fa_near_ang"
    fa_sc_k = "fa_far_sc" if is_far else "fa_near_sc"

    ua_ang = math.atan2(ey - sy, ex - sx)
    ua_len = math.hypot(ex - sx, ey - sy)

    fa_id, bic_id = nid(), nid()
    key_double(fa_id, 13, lambda p: p[el_k][0])
    key_double(fa_id, 14, lambda p: p[el_k][1])
    key_double(fa_id, 15, lambda p: p[fa_ang_k])
    key_double(fa_id, 16, lambda p: p[fa_sc_k])
    key_double(bic_id, 17, lambda p: p["biceps_swell"])

    p0 = POSES[0]

    # Target Muscle Activation Curves (already highlighted in warm orange at full extension r=0 as in Left Panel,
    # pulsing to intense crimson at peak contraction r=1 as in Right Panel!)
    def biceps_t(p):
        return 0.48 + 0.52 * (p["r"] ** 0.78)

    def brachialis_t(p):
        return 0.44 + 0.54 * (p["r"] ** 0.80)

    def brachiorad_t(p):
        return 0.42 + 0.54 * (p["r"] ** 0.82)

    # 1. Pivoting Forearm (0 .. FOREARM_LEN = 38.0) with Activated Brachioradialis along radial (-Y) border
    fa_pts = [
        (-5.0, 0.0), (-3.0, -7.2), (10.0, -8.5), (24.0, -6.8), (34.0, -4.8),
        (FOREARM_LEN + 2.0, 0.0), (34.0, 4.8), (24.0, 6.8), (10.0, 8.2), (-3.0, 6.8),
    ]
    brachiorad_pts = [
        (-2.0, -6.8), (8.0, -8.2), (21.0, -6.8), (31.0, -4.2),
        (28.0, -0.5), (15.0, -1.2), (2.0, -1.8),
    ]

    # 2. Braced Upper Arm (0 .. ua_len) resting on Preacher Pad:
    #    Local +X is SHOULDER -> ELBOW (~+41 deg down-right).
    #    Local -Y is ANTERIOR/TOP (facing up-right: Biceps Brachii Long & Short Heads!).
    #    Local +Y is POSTERIOR/BOTTOM (resting flat on the preacher pad: Brachialis & Triceps!).
    ua_pts = [
        (-8.0, 0.0), (-5.0, -10.5), (12.0, -12.8), (ua_len * 0.55, -12.5), (ua_len - 6.0, -7.8),
        (ua_len + 3.0, 0.0), (ua_len - 5.0, 7.5), (ua_len * 0.55, 10.5), (12.0, 11.2), (-5.0, 8.8),
    ]
    # Biceps Brachii Short Head & Long Head (two-bellied anterior muscle along local -Y, swelling via scaleY = biceps_swell)
    biceps_short_pts = [
        (6.0, -10.2), (ua_len * 0.42, -12.8), (ua_len * 0.78, -10.5), (ua_len - 4.0, -5.2),
        (ua_len * 0.72, -2.5), (ua_len * 0.36, -3.2), (6.0, -4.5),
    ]
    biceps_long_pts = [
        (8.0, -4.8), (ua_len * 0.44, -6.2), (ua_len * 0.76, -5.0), (ua_len - 5.0, -1.2),
        (ua_len * 0.70, 2.2), (ua_len * 0.35, 2.2), (8.0, 0.5),
    ]
    # Brachialis (deep distal-lateral wedge below Biceps Long Head, exactly matching the lower red strip in Left Panel!)
    brachialis_pts = [
        (12.0, 1.2), (ua_len * 0.48, 1.8), (ua_len * 0.82, 0.8), (ua_len - 4.0, 4.2),
        (ua_len * 0.68, 7.2), (ua_len * 0.34, 6.8), (12.0, 4.8),
    ]

    # Deltoid Cap at SHOULDER (sx, sy)
    if not is_far:
        delt_pts = [
            (sx - 15.0, sy - 6.0), (sx - 4.0, sy - 14.0), (sx + 12.0, sy - 10.0),
            (sx + 18.0, sy + 2.0), (sx + 10.0, sy + 14.0), (sx - 6.0, sy + 14.0), (sx - 15.0, sy + 5.0),
        ]
    else:
        delt_pts = [
            (sx - 10.0, sy - 10.0), (sx + 2.0, sy - 13.0), (sx + 14.0, sy - 6.0),
            (sx + 16.0, sy + 6.0), (sx + 6.0, sy + 13.0), (sx - 8.0, sy + 10.0),
        ]

    out = [f'{ind}<Node name="{prefix}PreacherArmGroup">']

    # Layer A (Top of Arm): Pivoting Forearm & Glowing Brachioradialis
    out.append(
        f'{i2}<Node x="{f(p0[el_k][0])}" y="{f(p0[el_k][1])}" '
        f'rotation="{f(p0[fa_ang_k])}" scaleX="{f(p0[fa_sc_k])}" name="{prefix}ForearmNode" id="{fa_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}BrachioradFiber", [(4.0, -5.0), (16.0, -5.2), (27.0, -3.5)], 0.95, "807F1D1D", 0.3))
    out.append(stroke_shape(i3, f"{prefix}BrachioradHi", [(4.0, -6.2), (16.0, -6.5), (26.0, -4.8)], 1.8, "66FFFFFF", 1.6))
    out.append(smooth_shape(i3, f"{prefix}Brachioradialis", brachiorad_pts, muscle_paint_fn(prefix + "Brachiorad", brachiorad_t, 0.95)))
    out.append(stroke_shape(i3, f"{prefix}ForearmTendon", [(8.0, 0.8), (22.0, 1.0), (33.0, 0.5)], 1.15, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(8.0, -1.5), (22.0, -1.2), (33.0, -0.8)], 2.2, HIGHLIGHT, 2.4))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(6.0, 4.2), (20.0, 4.5), (32.0, 3.2)], 3.0, CORE_SHADOW, 3.0))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -8, 8, skin)))
    out.append(f"{i2}</Node>")

    # Layer B: Unscaled Rounded Elbow Joint Cap on Preacher Pad
    out.append(ellipse_shape(i2, f"{prefix}ElbowCap", ex, ey, 15.0, 13.5, skin_fill(prefix + "Elbow", -7, 7, skin)))

    # Layer C: Sculpted Deltoid Cap at Shoulder
    if not is_far:
        out.append(stroke_shape(i2, "NearDeltGroove1", [(sx - 2.0, sy - 8.0), (sx + 6.0, sy + 6.0)], 1.15, SOFT_SHADOW, 0.7))
        out.append(stroke_shape(i2, "NearDeltGroove2", [(sx + 4.0, sy - 9.0), (sx + 12.0, sy + 4.0)], 1.15, SOFT_SHADOW, 0.7))
        out.append(stroke_shape(i2, "NearDeltHi", [(sx - 4.0, sy - 10.0), (sx + 8.0, sy - 6.0), (sx + 12.0, sy + 4.0)], 2.8, HIGHLIGHT, 2.8))
    out.append(smooth_shape(i2, f"{prefix}DeltoidCap", delt_pts, skin_fill(prefix + "Delt", sy - 14, sy + 14, skin)))

    # Layer D: Braced Upper Arm with Swelling Biceps Brachii (Short & Long Heads) & Brachialis
    out.append(
        f'{i2}<Node x="{f(sx)}" y="{f(sy)}" rotation="{f(ua_ang)}" name="{prefix}UpperArmNode">'
    )
    out.append(
        f'{i3}<Node scaleY="{f(p0["biceps_swell"])}" name="{prefix}BicepsSwellNode" id="{bic_id}">'
    )
    out.append(stroke_shape(i3 + "    ", f"{prefix}BicepsSeptum", [(10.0, -4.5), (ua_len * 0.45, -5.8), (ua_len * 0.78, -4.2)], 1.15, "997F1D1D", 0.3))
    out.append(stroke_shape(i3 + "    ", f"{prefix}BicepsHi", [(12.0, -9.2), (ua_len * 0.45, -10.8), (ua_len * 0.75, -8.5)], 2.2, "66FFFFFF", 1.8))
    out.append(smooth_shape(i3 + "    ", f"{prefix}Brachialis", brachialis_pts, muscle_paint_fn(prefix + "Brachialis", brachialis_t, 0.95)))
    out.append(smooth_shape(i3 + "    ", f"{prefix}BicepsLongHead", biceps_long_pts, muscle_paint_fn(prefix + "BicLong", biceps_t, 1.0)))
    out.append(smooth_shape(i3 + "    ", f"{prefix}BicepsShortHead", biceps_short_pts, muscle_paint_fn(prefix + "BicShort", biceps_t, 1.05)))
    out.append(f"{i3}</Node>")
    out.append(stroke_shape(i3, f"{prefix}TricepsUnderSh", [(10.0, 7.5), (ua_len * 0.5, 8.2), (ua_len - 8.0, 5.8)], 3.2, CORE_SHADOW, 3.0))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UA", -13, 11, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. 3D Preacher Curl Bench (Pad, Seat & Steel Frame with Barbell Catch Uprights)
def preacher_bench_rig():
    """Renders the 3D Preacher Curl Bench split into:
    - Front Catch Uprights (`x = 294..306` and `x = 408..418`) & Base Rails drawn in front of the legs
    - Angled 3D Preacher Arm Pad (`(248, 134)` to `(368, 174)`) supporting the upper arms
    - Padded Seat Cushion & Rear Frame Post drawn behind the seated thighs."""
    ind = "        "
    i2 = ind + "    "

    pad_top_paint = (
        f'<Fill name="PreacherPadTopFill">{grad3("PreacherPadTopGrad", 132, 176, *PAD_TOP, x0=248, x1=370)}</Fill>'
        '<Stroke thickness="1.0" join="round" name="PreacherPadTopEdge"><SolidColor colorValue="FF475569" name="PreacherPadTopEdgeCol"/></Stroke>'
    )
    pad_side_paint = (
        f'<Fill name="PreacherPadSideFill">{grad3("PreacherPadSideGrad", 136, 184, *PAD_SIDE, x0=246, x1=370)}</Fill>'
        '<Stroke thickness="1.0" join="round" name="PreacherPadSideEdge"><SolidColor colorValue="FF1E293B" name="PreacherPadSideEdgeCol"/></Stroke>'
    )
    steel_front_paint = (
        f'<Fill name="BenchSteelFrontFill">{grad3("BenchSteelFrontGrad", 170, 300, *STEEL_FRONT, x0=220, x1=420)}</Fill>'
        '<Stroke thickness="0.95" join="round" name="BenchSteelFrontEdge"><SolidColor colorValue="FF64748B" name="BenchSteelFrontEdgeCol"/></Stroke>'
    )
    steel_side_paint = (
        f'<Fill name="BenchSteelSideFill">{grad3("BenchSteelSideGrad", 170, 300, *STEEL_SIDE, x0=220, x1=420)}</Fill>'
        '<Stroke thickness="0.95" join="round" name="BenchSteelSideEdge"><SolidColor colorValue="FF475569" name="BenchSteelSideEdgeCol"/></Stroke>'
    )
    rubber_paint = solid("BenchRubber", "FF090D16")

    # 1. Angled 3D Preacher Arm Pad (supports elbows (318, 152) and (352, 148) from underneath!)
    #    Top surface spans from chest edge ((252, 134) -> (314, 128)) down-right to ((370, 168) -> (306, 175))
    pad_top_pts = [
        (252.0, 134.0), (314.0, 128.0), (370.0, 168.0), (306.0, 175.0),
    ]
    pad_skirt_pts = [
        (252.0, 134.0), (306.0, 175.0), (370.0, 168.0),
        (368.0, 178.0), (304.0, 185.0), (248.0, 144.0),
    ]

    # 2. Foreground Barbell Catch Uprights & Slanted Floor Base Frame (matching reference image!)
    #    Near Upright Post at x = 292..304 rising from floor base (296, 298) to J-hook cradle at (296, 198)
    near_post_front = [(291.0, 200.0), (300.0, 200.0), (300.0, 296.0), (291.0, 296.0)]
    near_post_side = [(300.0, 200.0), (306.0, 198.0), (306.0, 294.0), (300.0, 296.0)]
    near_cradle_pts = [
        (287.0, 193.0), (293.0, 193.0), (294.0, 199.0), (302.0, 198.0),
        (304.0, 192.0), (309.0, 192.0), (307.0, 204.0), (289.0, 204.0),
    ]
    #    Far Upright Post at x = 408..418 rising from floor base (412, 280) to J-hook cradle at (412, 184)
    far_post_front = [(407.0, 186.0), (415.0, 186.0), (415.0, 278.0), (407.0, 278.0)]
    far_post_side = [(415.0, 186.0), (420.0, 184.0), (420.0, 276.0), (415.0, 278.0)]
    far_cradle_pts = [
        (404.0, 179.0), (409.0, 179.0), (410.0, 185.0), (417.0, 184.0),
        (419.0, 178.0), (423.0, 178.0), (421.0, 189.0), (405.0, 189.0),
    ]
    #    Front Diagonal Base Rail connecting (290, 296) -> (422, 276)
    front_base_top = [(286.0, 292.0), (420.0, 272.0), (424.0, 276.0), (290.0, 297.0)]
    front_base_side = [(290.0, 297.0), (424.0, 276.0), (424.0, 283.0), (290.0, 303.0)]

    # 3. Background Preacher Pedestal Post, Padded Seat Cushion & Rear Base Frame
    pad_post_front = [(316.0, 176.0), (327.0, 175.0), (327.0, 286.0), (316.0, 288.0)]
    pad_post_side = [(327.0, 175.0), (333.0, 173.0), (333.0, 284.0), (327.0, 286.0)]
    seat_top_pts = [(222.0, 196.0), (254.0, 192.0), (292.0, 196.0), (264.0, 202.0)]
    seat_side_pts = [
        (222.0, 196.0), (264.0, 202.0), (292.0, 196.0),
        (292.0, 205.0), (264.0, 211.0), (222.0, 205.0),
    ]
    rear_post_front = [(250.0, 208.0), (260.0, 208.0), (260.0, 280.0), (250.0, 280.0)]
    rear_base_rail = [(216.0, 276.0), (296.0, 290.0), (296.0, 297.0), (216.0, 282.0)]
    mid_base_rail = [(258.0, 272.0), (392.0, 282.0), (392.0, 288.0), (258.0, 278.0)]

    pad_xml = "\n".join([
        f'{ind}<Node name="PreacherArmPadNode">',
        stroke_shape(i2, "PreacherPadCrease", [(254.0, 135.0), (306.0, 174.5), (368.0, 168.0)], 1.3, "9964748B", 0.3),
        poly_shape(i2, "PreacherPadTop", pad_top_pts, pad_top_paint, radius=3.5),
        poly_shape(i2, "PreacherPadSkirt", pad_skirt_pts, pad_side_paint, radius=3.5),
        f"{ind}</Node>",
    ])

    fg_frame_xml = "\n".join([
        f'{ind}<Node name="PreacherFrontFrameNode">',
        # Near Upright Barbell Catch Post (x ~ 296)
        poly_shape(i2, "NearCatchCradle", near_cradle_pts, rubber_paint, radius=1.2),
        poly_shape(i2, "NearPostFront", near_post_front, steel_front_paint, radius=1.0),
        poly_shape(i2, "NearPostSide", near_post_side, steel_side_paint, radius=1.0),
        # Far Upright Barbell Catch Post (x ~ 412)
        poly_shape(i2, "FarCatchCradle", far_cradle_pts, rubber_paint, radius=1.2),
        poly_shape(i2, "FarPostFront", far_post_front, steel_front_paint, radius=1.0),
        poly_shape(i2, "FarPostSide", far_post_side, steel_side_paint, radius=1.0),
        # Front Diagonal Steel Base Rail & Rubber Feet
        poly_shape(i2, "FrontBaseCapNear", [(284.0, 296.0), (298.0, 296.0), (298.0, 303.5), (284.0, 303.5)], rubber_paint, radius=1.2),
        poly_shape(i2, "FrontBaseCapFar", [(416.0, 275.0), (428.0, 275.0), (428.0, 283.0), (416.0, 283.0)], rubber_paint, radius=1.2),
        poly_shape(i2, "FrontBaseTop", front_base_top, steel_front_paint, radius=1.2),
        poly_shape(i2, "FrontBaseSide", front_base_side, steel_side_paint, radius=1.2),
        f"{ind}</Node>",
    ])

    bg_frame_xml = "\n".join([
        f'{ind}<Node name="PreacherSeatAndRearFrameNode">',
        poly_shape(i2, "PreacherSeatTop", seat_top_pts, pad_top_paint, radius=2.5),
        poly_shape(i2, "PreacherSeatSide", seat_side_pts, pad_side_paint, radius=2.5),
        poly_shape(i2, "PadPedestalFront", pad_post_front, steel_front_paint, radius=1.0),
        poly_shape(i2, "PadPedestalSide", pad_post_side, steel_side_paint, radius=1.0),
        poly_shape(i2, "RearSeatPost", rear_post_front, steel_front_paint, radius=1.0),
        poly_shape(i2, "RearBaseCap", [(212.0, 275.0), (224.0, 275.0), (224.0, 283.0), (212.0, 283.0)], rubber_paint, radius=1.2),
        poly_shape(i2, "RearBaseRail", rear_base_rail, steel_front_paint, radius=1.0),
        poly_shape(i2, "MidBaseRail", mid_base_rail, steel_side_paint, radius=1.0),
        f"{ind}</Node>",
    ])

    return fg_frame_xml, pad_xml, bg_frame_xml


# ---------------------------------------------------------------- 4. Seated 3/4 Athlete Torso, Volumetric Head & Legs
def seated_torso_and_head():
    """Seated 3/4 front-right athlete torso leaning chest-first against the preacher pad,
    with volumetric 3/4 head looking forward-right at the curling EZ-bar."""
    ind = "        "
    i2 = ind + "    "

    # Volumetric 3/4 Head facing front-right (+X) at (272..306, 40..78)
    head_pts = [
        (274.0, 48.0), (282.0, 40.0), (295.0, 40.5), (303.5, 47.0),
        (304.5, 55.5), (306.2, 61.5), (304.2, 67.5), (302.5, 73.5),
        (295.5, 76.5), (285.5, 74.5), (277.5, 69.0), (273.0, 59.5),
    ]
    hair_pts = [
        (273.5, 57.5), (273.5, 47.0), (281.5, 39.5), (295.5, 39.8),
        (303.5, 46.5), (296.5, 46.5), (288.0, 49.0), (281.5, 54.0),
        (278.5, 61.0),
    ]
    neck_pts = [
        (272.0, 68.0), (294.0, 72.0), (304.0, 90.0),
        (264.0, 92.0), (268.0, 78.0),
    ]

    # Torso & Chest leaning against the preacher pad (from shoulders (262, 102)..(316, 100) down to hips (236, 174)..(286, 182))
    torso_pts = [
        (252.0, 92.0), (286.0, 86.0), (318.0, 94.0),
        (316.0, 128.0), (296.0, 158.0), (284.0, 180.0),
        (240.0, 182.0), (242.0, 152.0), (244.0, 122.0),
    ]
    pec_near_pts = [
        (262.0, 96.0), (290.0, 96.0), (292.0, 120.0),
        (276.0, 126.0), (258.0, 116.0),
    ]
    pec_far_pts = [
        (290.0, 96.0), (314.0, 98.0), (314.0, 122.0),
        (298.0, 125.0), (292.0, 120.0),
    ]
    pec_paint = (
        '<Fill name="PreacherPecFill"><SolidColor colorValue="160F172A" name="PreacherPecCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="PreacherPecStroke"><SolidColor colorValue="3D0F172A" name="PreacherPecStrokeCol"/></Stroke>'
    )
    pelvis_shorts_pts = [
        (238.0, 160.0), (284.0, 164.0), (294.0, 184.0),
        (272.0, 202.0), (236.0, 198.0), (232.0, 178.0),
    ]

    return "\n".join([
        f'{ind}<Node name="SeatedTorsoAndHead">',
        # 1. Volumetric 3/4 Head (facing front-right)
        smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 273, 40, 304, 60, "FF475569", "FF1E293B")}</Fill>'),
        ellipse_shape(i2, "Ear", 280.5, 61.5, 5.2, 8.0, solid("Ear", "FFA3B1C4"), rot_deg=-12.0),
        stroke_shape(i2, "BrowShade", [(296.0, 54.8), (303.0, 54.2)], 1.4, "590F172A", 0.8),
        stroke_shape(i2, "EyeLine", [(296.5, 56.8), (300.5, 56.5)], 1.1, "730F172A", 0.4),
        stroke_shape(i2, "MouthLine", [(298.5, 68.5), (303.0, 68.2)], 1.0, "590F172A", 0.4),
        stroke_shape(i2, "HeadHi", [(284.0, 44.0), (295.0, 44.5), (301.5, 50.0)], 3.0, HIGHLIGHT, 3.2),
        stroke_shape(i2, "CheekHi", [(290.0, 60.5), (297.0, 61.5), (302.5, 60.0)], 2.2, "80FFFFFF", 2.4),
        stroke_shape(i2, "JawShadow", [(282.5, 71.5), (292.0, 75.5), (300.5, 74.0)], 2.6, CORE_SHADOW, 2.5),
        smooth_shape(i2, "Head", head_pts, skin_fill("Head", 40, 77, SKIN, x0=305, x1=273)),
        # 2. Muscular Neck & Trapezius
        stroke_shape(i2, "UnderChinSh", [(284.0, 74.5), (293.5, 76.5), (299.5, 74.5)], 3.0, CORE_SHADOW, 2.4),
        stroke_shape(i2, "SCMLine", [(282.0, 72.0), (288.0, 82.0), (292.0, 91.0)], 1.4, SOFT_SHADOW, 1.2),
        smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", 68, 92, SKIN)),
        # 3. Pelvis Compression Shorts & Sculpted Torso
        smooth_shape(i2, "PelvisShorts", pelvis_shorts_pts, skin_fill("PelvisShorts", 160, 202, SHORTS, x0=294, x1=232)),
        stroke_shape(i2, "SternumLine", [(290.0, 94.0), (291.0, 122.0), (286.0, 148.0)], 1.4, CORE_SHADOW, 0.8),
        stroke_shape(i2, "RibLatLine1", [(254.0, 132.0), (270.0, 138.0)], 1.2, SOFT_SHADOW, 0.8),
        stroke_shape(i2, "RibLatLine2", [(250.0, 144.0), (268.0, 150.0)], 1.2, SOFT_SHADOW, 0.8),
        stroke_shape(i2, "PecNearHi", [(266.0, 102.0), (280.0, 104.0), (286.0, 114.0)], 2.6, HIGHLIGHT, 2.8),
        smooth_shape(i2, "PecNear", pec_near_pts, pec_paint),
        smooth_shape(i2, "PecFar", pec_far_pts, pec_paint),
        stroke_shape(i2, "TorsoBackHi", [(248.0, 108.0), (246.0, 138.0), (244.0, 164.0)], 3.8, HIGHLIGHT, 4.0),
        smooth_shape(i2, "TorsoShape", torso_pts, skin_fill("Torso", 86, 182, SKIN, x0=318, x1=240)),
        f"{ind}</Node>",
    ])


def seated_legs_rig():
    """Renders the Near (Right) and Far (Left) seated legs matching the reference image:
    - Near (Right) leg: thigh (`(244, 176) -> (312, 208)`), vertical shin/calf (`(308, 208) -> (302, 282)`),
      and bare right foot planted at `(304, 290)` just behind the front upright post.
    - Far (Left) leg: thigh (`(276, 174) -> (356, 198)`), sculpted medial gastrocnemius calf (`(354, 198) -> (336, 268)`),
      and bare left foot planted at `(348, 276)` on the lower frame rail."""
    ind = "        "
    i2 = ind + "    "

    # Near (Right) Leg
    near_shorts_pts = [
        (240.0, 166.0), (278.0, 168.0), (294.0, 182.0),
        (282.0, 202.0), (248.0, 196.0), (236.0, 182.0),
    ]
    near_thigh_pts = [
        (248.0, 176.0), (284.0, 176.0), (314.0, 196.0),
        (318.0, 212.0), (302.0, 218.0), (268.0, 206.0), (244.0, 192.0),
    ]
    near_shin_pts = [
        (296.0, 208.0), (316.0, 206.0), (318.0, 232.0),
        (312.0, 260.0), (308.0, 282.0), (294.0, 282.0),
        (292.0, 256.0), (290.0, 230.0),
    ]
    near_foot_pts = [
        (294.0, 278.0), (308.0, 278.0), (322.0, 288.0),
        (320.0, 294.0), (302.0, 294.0), (292.0, 288.0),
    ]

    # Far (Left) Leg
    far_thigh_pts = [
        (280.0, 172.0), (324.0, 176.0), (356.0, 190.0),
        (362.0, 204.0), (344.0, 210.0), (304.0, 200.0), (278.0, 188.0),
    ]
    far_shin_pts = [
        (338.0, 198.0), (360.0, 198.0), (362.0, 222.0),
        (352.0, 248.0), (344.0, 270.0), (330.0, 270.0),
        (326.0, 244.0), (326.0, 218.0),
    ]
    far_foot_pts = [
        (330.0, 266.0), (344.0, 266.0), (368.0, 276.0),
        (366.0, 282.0), (342.0, 280.0), (328.0, 274.0),
    ]

    near_leg_xml = "\n".join([
        f'{ind}<Node name="NearSeatedLeg">',
        smooth_shape(i2, "NearFoot", near_foot_pts, skin_fill("NearFoot", 278, 294, SKIN)),
        stroke_shape(i2, "NearShinHi", [(306.0, 214.0), (305.0, 244.0), (303.0, 274.0)], 2.8, HIGHLIGHT, 2.8),
        stroke_shape(i2, "NearShinSh", [(294.0, 216.0), (294.0, 246.0), (296.0, 274.0)], 3.4, CORE_SHADOW, 3.2),
        smooth_shape(i2, "NearShin", near_shin_pts, skin_fill("NearShin", 206, 282, SKIN)),
        ellipse_shape(i2, "NearKnee", 308.0, 206.0, 16.5, 15.0, skin_fill("NearKnee", -8, 8, SKIN)),
        stroke_shape(i2, "NearQuadLine", [(264.0, 182.0), (288.0, 192.0), (306.0, 202.0)], 1.3, CORE_SHADOW, 0.8),
        stroke_shape(i2, "NearThighHi", [(268.0, 179.0), (292.0, 188.0), (310.0, 198.0)], 3.4, HIGHLIGHT, 3.2),
        stroke_shape(i2, "NearThighSh", [(256.0, 192.0), (280.0, 202.0), (300.0, 212.0)], 3.8, CORE_SHADOW, 3.5),
        smooth_shape(i2, "NearThigh", near_thigh_pts, skin_fill("NearThigh", 176, 218, SKIN)),
        stroke_shape(i2, "NearShortsHem", [(278.0, 172.0), (286.0, 186.0), (278.0, 200.0)], 1.5, "99020617", 0.5),
        smooth_shape(i2, "NearShorts", near_shorts_pts, skin_fill("NearShorts", 166, 202, SHORTS)),
        f"{ind}</Node>",
    ])

    far_leg_xml = "\n".join([
        f'{ind}<Node name="FarSeatedLeg">',
        smooth_shape(i2, "FarFoot", far_foot_pts, skin_fill("FarFoot", 266, 282, SKIN_FAR)),
        stroke_shape(i2, "FarCalfCut", [(334.0, 212.0), (330.0, 232.0), (334.0, 248.0)], 1.3, CORE_SHADOW, 0.8),
        stroke_shape(i2, "FarShinHi", [(350.0, 208.0), (346.0, 236.0), (340.0, 262.0)], 2.6, HIGHLIGHT, 2.5),
        stroke_shape(i2, "FarShinSh", [(332.0, 214.0), (330.0, 238.0), (332.0, 262.0)], 3.2, CORE_SHADOW, 3.0),
        smooth_shape(i2, "FarShin", far_shin_pts, skin_fill("FarShin", 198, 270, SKIN_FAR)),
        ellipse_shape(i2, "FarKnee", 352.0, 198.0, 15.5, 14.0, skin_fill("FarKnee", -7, 7, SKIN_FAR)),
        stroke_shape(i2, "FarQuadLine", [(302.0, 182.0), (328.0, 190.0), (348.0, 196.0)], 1.2, CORE_SHADOW, 0.8),
        stroke_shape(i2, "FarThighHi", [(306.0, 178.0), (332.0, 186.0), (352.0, 192.0)], 3.0, HIGHLIGHT, 2.8),
        smooth_shape(i2, "FarThigh", far_thigh_pts, skin_fill("FarThigh", 172, 210, SKIN_FAR)),
        f"{ind}</Node>",
    ])

    return near_leg_xml, far_leg_xml


# ---------------------------------------------------------------- 5. Scene Assembly (RML First Child = Topmost Layer)
def build_rml():
    global _id
    _id = 0
    KEYED.clear()

    ez_fg_xml, ez_bg_xml = ez_barbell_and_hands_rig()
    near_arm_xml = build_preacher_arm("Near", False)
    far_arm_xml = build_preacher_arm("Far", True)
    fg_frame_xml, pad_xml, bg_frame_xml = preacher_bench_rig()
    torso_head_xml = seated_torso_and_head()
    near_leg_xml, far_leg_xml = seated_legs_rig()

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
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="PreacherCurl" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: EZ-Curl Barbell Shaft, Supinated Hands & Near 3D Weight Plate -->
{ez_fg_xml}

        <!-- 2. Near (Right) Preacher-Braced Arm (Biceps Short/Long Head, Brachialis & Brachioradialis) -->
{near_arm_xml}

        <!-- 3. Far (Left) Preacher-Braced Arm -->
{far_arm_xml}

        <!-- 4. EZ-Curl Barbell Far 3D Weight Plate -->
{ez_bg_xml}

        <!-- 5. 3D Angled Preacher Arm Pad (Supporting Both Upper Arms & Elbows) -->
{pad_xml}

        <!-- 6. Foreground Barbell Catch Uprights & Front Diagonal Base Rail -->
{fg_frame_xml}

        <!-- 7. Seated 3/4 Athlete Torso & Volumetric Head -->
{torso_head_xml}

        <!-- 8. Near (Right) Seated Leg -->
{near_leg_xml}

        <!-- 9. Far (Left) Seated Leg -->
{far_leg_xml}

        <!-- 10. Background Preacher Bench Pedestal, Padded Seat & Rear Base Frame -->
{bg_frame_xml}

        <!-- 11. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="324" y="{f(FLOOR - 2)}" scaleX="1.45" scaleY="0.10" name="BenchAndAthleteShadow">
            <Ellipse width="220" height="220" name="ShadowEllipse"/>
            <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="110" endY="0" name="ShadowGrad">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="PreacherCurl" id="0:60">
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
    (BUILD / "preacher_curl.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (38, "frame_mid"), (72, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(680, 20, 290))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
