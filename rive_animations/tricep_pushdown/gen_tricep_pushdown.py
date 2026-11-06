#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360, FLOOR = 300.0) procedural Rive 7.3 scene for Tricep Pushdown (id: 'tricep_pushdown').

Uses our canonical 3/4 standing CommunityFitness mannequin facing a high-pulley cable tower on the right (`x ~ 440`):
  - Upper arms stay pinned vertically at the sides of the ribcage with a slight athletic forward torso lean (`~8 deg`),
    while a taut steel cable runs from the overhead high pulley (`(408, 52)`) down to the angled V-bar handle in the
    athlete's hands.
  - r = 0.0 (Top Eccentric Start): Elbows flexed so forearms angle upward toward the cable handle at chest height.
  - r = 1.0 (Bottom Peak Lockout): Forearms sweep downward in a circular arc around the fixed elbows to full vertical
    extension beside the thighs, maximally contracting the triceps horseshoe while the weight stack rises.
  - Highlighted Target Muscle Groups (pulsing from warm orange #FFF97316 to intense crimson #FFF43F5E):
    1. Triceps brachii — Lateral head, Long head & Medial head (Primary mover — prominent horseshoe on upper arm)
    2. Anconeus & Forearm extensors (Secondary — elbow lockout & wrist stabilization)

Run:
    python3 rive_animations/tricep_pushdown/gen_tricep_pushdown.py            # writes scene.rml
    python3 rive_animations/tricep_pushdown/gen_tricep_pushdown.py --publish  # compiles .riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/tricep_pushdown.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/tricep_pushdown.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps loop
STEP = 2

# High-Pulley Cable Machine Constants (Right Side of Artboard)
PULLEY_EXIT = (408.0, 52.0)
PULLEY_TOP = (418.0, 34.0)
PULLEY_REDIRECT = (468.0, 82.0)
CABLE_BASE_LEN = 100.0

# Pinned Shoulder & Arm Segment Constants (Athlete on Left Facing Right)
NEAR_SH = (296.0, 102.0)  # Right (foreground / screen-left) shoulder
FAR_SH = (336.0, 98.0)    # Left (background / screen-right) shoulder
UA_NEAR_LEN, FA_NEAR_LEN = 44.0, 40.0
UA_FAR_LEN, FA_FAR_LEN = 42.0, 38.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
FRAME_WHITE = ("FFFFFFFF", "FFE2E8F0", "FF94A3B8")
FRAME_FAR = ("FFF1F5F9", "FFCBD5E1", "FF64748B")
PAD_DARK = ("FF334155", "FF1E293B", "FF090D16")
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


EASE_PUSH = cubic_bezier(0.35, 0.0, 0.22, 1.0)
EASE_RETURN = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def pushdown_progress(frame):
    """Returns cable tricep pushdown progress r in [0.0, 1.0] across 160 frames:
    - 0..12:   Top eccentric start hold at chest height (r = 0.0)
    - 12..64:  Concentric downward forearm sweep to full triceps lockout (r: 0.0 -> 1.0)
    - 64..84:  Bottom peak lockout squeeze beside thighs (r = 1.0)
    - 84..148: Controlled eccentric return to chest height (r: 1.0 -> 0.0)
    - 148..160: Top hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 64:
        return EASE_PUSH((fr - 12) / 52.0)
    if fr <= 84:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_RETURN((fr - 84) / 64.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def seg_xform(p0, p1, base_len):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ang = math.atan2(dy, dx)
    sc = max(0.30, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute Standing Cable Tricep Pushdown transforms at progress r in [0.0, 1.0]:
    - Upper arms stay pinned vertically at the sides of the ribcage (`ua_deg ~ 88..91 deg`).
    - Forearms sweep downward in a pure circular arc around the fixed elbows (`fa_deg: -26 deg -> +78 deg`),
      driving the V-bar cable attachment from chest height (`y ~ 120`) down to full lockout beside the thighs (`y ~ 175`).
    """
    ua_near_rad = math.radians(lerp(87.0, 91.0, r))
    ua_far_rad = math.radians(lerp(85.0, 89.0, r))

    near_el = (
        NEAR_SH[0] + UA_NEAR_LEN * math.cos(ua_near_rad),
        NEAR_SH[1] + UA_NEAR_LEN * math.sin(ua_near_rad),
    )
    far_el = (
        FAR_SH[0] + UA_FAR_LEN * math.cos(ua_far_rad),
        FAR_SH[1] + UA_FAR_LEN * math.sin(ua_far_rad),
    )

    fa_deg = lerp(-26.0, 78.0, r)
    fa_rad = math.radians(fa_deg)

    near_hand = (
        near_el[0] + FA_NEAR_LEN * math.cos(fa_rad),
        near_el[1] + FA_NEAR_LEN * math.sin(fa_rad),
    )
    far_hand = (
        far_el[0] + FA_FAR_LEN * math.cos(fa_rad),
        far_el[1] + FA_FAR_LEN * math.sin(fa_rad),
    )

    ua_near_ang, ua_near_sc = seg_xform(NEAR_SH, near_el, UA_NEAR_LEN)
    fa_near_ang, fa_near_sc = seg_xform(near_el, near_hand, FA_NEAR_LEN)
    ua_far_ang, ua_far_sc = seg_xform(FAR_SH, far_el, UA_FAR_LEN)
    fa_far_ang, fa_far_sc = seg_xform(far_el, far_hand, FA_FAR_LEN)

    delt_near_ang = math.radians(lerp(2.0, 5.0, r))
    delt_far_ang = math.radians(lerp(2.0, 5.0, r))

    # V-Bar apex / chrome swivel eyelet between the two hands
    swivel = (
        0.5 * (near_hand[0] + far_hand[0]) + 4.0,
        0.5 * (near_hand[1] + far_hand[1]) - 6.0,
    )
    cable_ang, cable_sc = seg_xform(PULLEY_EXIT, swivel, CABLE_BASE_LEN)

    # Weight stack rises by -46 px as cable is pushed down
    stack_lift_y = lerp(0.0, -46.0, r)

    return {
        "r": r,
        "near_el": near_el,
        "far_el": far_el,
        "near_hand": near_hand,
        "far_hand": far_hand,
        "ua_near_ang": ua_near_ang,
        "ua_near_sc": ua_near_sc,
        "fa_near_ang": fa_near_ang,
        "fa_near_sc": fa_near_sc,
        "ua_far_ang": ua_far_ang,
        "ua_far_sc": ua_far_sc,
        "fa_far_ang": fa_far_ang,
        "fa_far_sc": fa_far_sc,
        "delt_near_ang": delt_near_ang,
        "delt_far_ang": delt_far_ang,
        "swivel": swivel,
        "cable_ang": cable_ang,
        "cable_sc": cable_sc,
        "stack_lift_y": stack_lift_y,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(pushdown_progress(fr)) for fr in FRAMES}

_ANGLE_KEYS = (
    "ua_near_ang",
    "fa_near_ang",
    "ua_far_ang",
    "fa_far_ang",
    "delt_near_ang",
    "delt_far_ang",
    "cable_ang",
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


# ---------------------------------------------------------------- 1. High-Pulley Cable Tower on the Right (`x ~ 408..512`)
def build_high_cable_tower():
    """High-pulley cable machine on the right (`x ~ 408..512, y = 26..300`) with animated weight stack."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    stack_id = nid()
    key_double(stack_id, 14, lambda p: p["stack_lift_y"])

    def frame_paint(name, x0, y0, x1, y1, far=False):
        pal = FRAME_FAR if far else FRAME_WHITE
        return skin_fill_outlined(name, y0, y1, pal, line=1.1, x0=x0, x1=x1, stroke_col="99334155")

    def pad_paint(name, x0, y0, x1, y1):
        return skin_fill_outlined(name, y0, y1, PAD_DARK, line=1.1, x0=x0, x1=x1, stroke_col="FF020617")

    pulley_paint = skin_fill_outlined("PulleyWheel", -8, 8, ("FF94A3B8", "FF475569", "FF1E293B"), line=1.0, stroke_col="FF0F172A")
    hub_paint = solid("PulleyHub", "FFE2E8F0")

    base_right = [(448, 286), (510, 290), (508, 298), (446, 294)]
    base_front = [(404, 294), (454, 286), (456, 294), (406, 300)]
    angled_brace = [(434, 226), (444, 224), (422, 294), (410, 294)]
    rear_post = [(492, 58), (502, 58), (502, 292), (492, 292)]
    main_column = [(441, 58), (454, 58), (454, 292), (441, 292)]
    mid_collar = [(438, 120), (504, 118), (504, 140), (438, 142)]
    lower_collar = [(438, 200), (504, 198), (504, 218), (438, 220)]
    top_cap = [(438, 56), (512, 52), (514, 58), (440, 62)]
    boom_arm = [(438, 138), (404, 30), (416, 26), (450, 134)]

    stack_block = [(456, 206), (490, 206), (490, 278), (456, 278)]
    plate_lines = [
        stroke_shape(i3, f"StackGroove{idx}", [(457, y), (489, y)], 1.1, "FF020617", 0.0)
        for idx, y in enumerate(range(212, 276, 6))
    ]

    return "\n".join([
        f'{ind}<Node name="HighCableTowerRight">',
        # 1. Overhead Pulley Boom Arm, Pulley Wheels & Collars
        ellipse_shape(i2, "TopPulleyHub", PULLEY_TOP[0], PULLEY_TOP[1], 4.5, 4.5, hub_paint),
        ellipse_shape(i2, "TopPulleyWheel", PULLEY_TOP[0], PULLEY_TOP[1], 14.0, 14.0, pulley_paint),
        ellipse_shape(i2, "ExitPulleyHub", PULLEY_EXIT[0], PULLEY_EXIT[1], 4.0, 4.0, hub_paint),
        ellipse_shape(i2, "ExitPulleyWheel", PULLEY_EXIT[0], PULLEY_EXIT[1], 12.0, 12.0, pulley_paint),
        stroke_shape(i2, "BoomArmHi", [(444, 130), (413, 30)], 2.0, "FFFFFFFF", 0.4),
        poly_shape(i2, "OverheadBoomArm", boom_arm, frame_paint("BoomArm", 404, 26, 450, 138), radius=3.0),
        poly_shape(i2, "TowerMidCollar", mid_collar, frame_paint("MidCollar", 438, 118, 504, 142), radius=1.5),
        poly_shape(i2, "TowerLowerCollar", lower_collar, frame_paint("LowCollar", 438, 198, 504, 220), radius=1.5),

        # 2. Main Upright Column, Stabilizer Brace & Base Feet on FLOOR = 300.0
        poly_shape(i2, "FrontRubberFoot", [(402, 294), (416, 293), (417, 300), (403, 300)], pad_paint("FrontFootCap", 402, 293, 417, 300), radius=1.5),
        poly_shape(i2, "FrontStabilizerBase", base_front, frame_paint("BaseFront", 404, 286, 456, 300), radius=1.5),
        poly_shape(i2, "AngledStabilizerBrace", angled_brace, frame_paint("AngledBrace", 410, 224, 444, 294), radius=2.0),
        stroke_shape(i2, "MainColumnHi", [(445, 62), (445, 288)], 2.2, "FFFFFFFF", 0.4),
        poly_shape(i2, "MainUprightColumn", main_column, frame_paint("MainCol", 441, 58, 454, 292), radius=1.5),
        poly_shape(i2, "TopHeaderCap", top_cap, frame_paint("TopCap", 438, 52, 514, 62), radius=2.0),

        # 3. Animated Weight Stack (slides up by -46 px as r: 0.0 -> 1.0)
        f'{i2}<Node x="0" y="0" name="WeightStackGroup" id="{stack_id}">',
        polyline_stroke_shape(i3, "StackLiftRod", [(473, 140), (473, 206)], 2.2, "FF0F172A", radius=0.0),
        *plate_lines,
        poly_shape(i3, "WeightStackPlates", stack_block, pad_paint("WeightStack", 456, 206, 490, 278), radius=2.0),
        f"{i2}</Node>",

        # 4. Internal Cable Routing & Twin Chrome Guide Rods
        polyline_stroke_shape(
            i2,
            "InternalTowerCable",
            [(473, 206), (473, 82), PULLEY_TOP, PULLEY_EXIT],
            1.7,
            "FF0F172A",
            radius=1.0,
        ),
        ellipse_shape(i2, "RedirectPulleyWheel", PULLEY_REDIRECT[0], PULLEY_REDIRECT[1], 11.0, 11.0, pulley_paint),
        polyline_stroke_shape(i2, "GuideRodLeft", [(464, 58), (464, 290)], 3.2, "FF94A3B8", radius=0.0),
        polyline_stroke_shape(i2, "GuideRodRight", [(484, 58), (484, 290)], 3.2, "FF94A3B8", radius=0.0),
        poly_shape(i2, "RearUprightPost", rear_post, frame_paint("RearPost", 492, 58, 502, 292, far=True), radius=1.5),
        poly_shape(i2, "RearBasePlate", base_right, frame_paint("BaseRight", 446, 286, 510, 298, far=True), radius=1.5),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 2. Taut Working Cable & Angled V-Bar Pushdown Handle
def build_cable_and_vbar():
    """Taut steel cable from PULLEY_EXIT (408, 52) to the chrome V-bar pushdown handle held between both hands."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    cab_id, bar_id = nid(), nid()

    key_double(cab_id, 15, lambda p: p["cable_ang"])
    key_double(cab_id, 16, lambda p: p["cable_sc"])

    key_double(bar_id, 13, lambda p: p["swivel"][0])
    key_double(bar_id, 14, lambda p: p["swivel"][1])
    p0 = POSES[0]

    swivel_paint = skin_fill_outlined("Swivel", -4, 4, ("FFE2E8F0", "FF94A3B8", "FF334155"), line=0.95)
    stopper_paint = skin_fill_outlined("GripEnd", -5, 5, PAD_DARK, line=1.0, stroke_col="FF475569")

    # Relative to Swivel apex (0,0):
    # Near grip extends to (-23, +6), Far grip extends to (+16, -1)
    return "\n".join([
        f'{ind}<Node name="CableAndPushdownBarGroup">',
        # 1. Chrome Angled V-Bar Pushdown Handle + Rubber End Flanges
        f'{i2}<Node x="{f(p0["swivel"][0])}" y="{f(p0["swivel"][1])}" name="PushdownVBarNode" id="{bar_id}">',
        ellipse_shape(i3, "NearBarEndFlange", -25.0, 7.0, 7.5, 10.5, stopper_paint, rot_deg=15.0),
        ellipse_shape(i3, "FarBarEndFlange", 18.0, -1.5, 7.0, 9.8, stopper_paint, rot_deg=-15.0),
        polyline_stroke_shape(i3, "VBarChromeHi", [(-23.0, 5.2), (0.0, -1.2), (16.0, -2.2)], 1.6, "FFFFFFFF", radius=1.0),
        polyline_stroke_shape(i3, "VBarChromeCore", [(-24.0, 6.2), (0.0, 0.0), (17.0, -1.2)], 4.8, "FF94A3B8", radius=1.5),
        polyline_stroke_shape(i3, "VBarShadow", [(-24.0, 7.2), (0.0, 1.0), (17.0, -0.2)], 5.6, "FF1E293B", radius=1.5),
        ellipse_shape(i3, "SwivelEyelet", 0.0, -2.5, 7.0, 7.0, swivel_paint),
        f"{i2}</Node>",

        # 2. Taut Working Steel Cable from PULLEY_EXIT (408, 52) to Swivel
        f'{i2}<Node x="{f(PULLEY_EXIT[0])}" y="{f(PULLEY_EXIT[1])}" '
        f'rotation="{f(p0["cable_ang"])}" scaleX="{f(p0["cable_sc"])}" name="TautWorkingCable" id="{cab_id}">',
        polyline_stroke_shape(i3, "CableSheen", [(0.0, -0.5), (CABLE_BASE_LEN, -0.5)], 0.8, "FF94A3B8", radius=0.0),
        polyline_stroke_shape(i3, "CableWire", [(0.0, 0.0), (CABLE_BASE_LEN, 0.0)], 2.0, "FF0F172A", radius=0.0),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 3. Standing 3/4 Athlete Body (Legs, Shorts, Torso & Head Facing Right)
def build_standing_athlete_body():
    """Canonical 3/4 front-right standing athlete on FLOOR = 300.0 with ~8 deg forward torso lean facing the cable tower."""
    ind = "        "
    i2 = ind + "    "

    # 1. Far (Left) Standing Leg (slightly forward-right in 3/4 depth)
    far_foot = [(316, 286), (336, 284), (354, 290), (352, 295), (314, 295)]
    far_shin = [
        (312, 224), (328, 224), (334, 248), (332, 272), (328, 288),
        (316, 288), (312, 266), (308, 244),
    ]
    far_thigh = [
        (298, 166), (326, 166), (332, 196), (328, 228), (310, 228), (298, 198),
    ]
    far_shorts = [(296, 158), (328, 158), (332, 186), (300, 188)]

    # 2. Near (Right) Standing Leg (foreground on FLOOR = 300.0)
    near_foot = [(276, 290), (296, 288), (318, 294), (316, 300), (274, 300)]
    near_shin = [
        (276, 228), (294, 228), (298, 252), (294, 274), (290, 292),
        (278, 292), (272, 268), (268, 246),
    ]
    near_thigh = [
        (270, 168), (302, 170), (304, 200), (296, 232), (276, 232), (268, 202),
    ]
    near_shorts = [(268, 160), (304, 162), (304, 192), (268, 190)]

    # 3. Pelvis Compression Shorts
    pelvis_shorts = [
        (272, 148), (324, 148), (328, 170), (304, 182), (268, 176), (268, 158),
    ]

    # 4. Forward-Leaned (~8 deg) 3/4 Torso, Pectoralis Major & 6-Pack Abs
    torso_pts = [
        (284, 88),   # near-right shoulder acromion
        (312, 84),   # clavicular notch / neck base
        (340, 88),   # far-left shoulder acromion
        (344, 108),  # far-left pectoral contour
        (334, 132),  # anterior-right abdominal contour
        (324, 152),  # anterior-right waist at shorts waistband
        (274, 152),  # posterior-left waist at shorts waistband
        (276, 130),  # posterior-left lat / lumbar taper
        (278, 106),  # posterior-left upper lat / teres
    ]
    pec_near_pts = [
        (298, 92), (322, 90), (326, 112), (312, 118), (296, 112),
    ]
    pec_far_pts = [
        (322, 90), (340, 92), (344, 108), (334, 116), (324, 112),
    ]
    pec_paint = (
        f'<Fill name="PecFill">{grad3("PecGrad", 90, 118, "FFF8FAFC", "FFDCE4EE", "FFA3B1C4")}</Fill>'
        '<Stroke thickness="1.05" join="round" name="PecStroke"><SolidColor colorValue="470F172A" name="PecStrokeCol"/></Stroke>'
    )
    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1F0F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="AbsEdge"><SolidColor colorValue="420F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        [(308, 118), (321, 118), (320, 127), (307, 127)],
        [(306, 129), (319, 129), (318, 138), (305, 138)],
        [(304, 140), (317, 140), (316, 149), (303, 149)],
        [(323, 118), (333, 118), (332, 127), (322, 127)],
        [(321, 129), (331, 129), (330, 138), (320, 138)],
        [(319, 140), (329, 140), (328, 149), (318, 149)],
    ]

    # 5. Canonical 3/4 Volumetric Head & Neck (facing right toward the cable handle!)
    neck_pts = [(302, 70), (322, 72), (328, 88), (298, 88)]
    head_pts = [
        (302, 62),  # occiput / back of head
        (302, 48),  # posterior crown
        (312, 42),  # upper cranial dome
        (325, 43),  # anterior hairline / forehead top
        (334, 51),  # brow ridge (facing right!)
        (335, 58),  # nose bridge
        (338, 64),  # sculpted nose tip projecting right
        (334, 70),  # lips
        (331, 76),  # strong chin tip
        (320, 77),  # jawline
        (310, 72),  # mastoid / nape
    ]
    hair_pts = [
        (325, 43), (333, 49), (326, 51), (318, 52),
        (312, 58), (306, 66), (300, 60), (301, 47), (312, 41),
    ]
    hair_paint = (
        f'<Fill name="HairFill">{grad("HairGrad", 300, 41, 333, 66, "FF334155", "FF0F172A")}</Fill>'
        '<Stroke thickness="0.95" join="round" name="HairStroke"><SolidColor colorValue="FF090D16" name="HairStrokeCol"/></Stroke>'
    )

    return "\n".join([
        f'{ind}<Node name="StandingAthleteBody">',
        # A. Far (Left) Leg in 3/4 Depth
        smooth_shape(i2, "FarFoot", far_foot, skin_fill_outlined("FarFoot", 284, 295, SKIN_FAR, line=1.05)),
        smooth_shape(i2, "FarShin", far_shin, skin_fill_outlined("FarShin", 224, 288, SKIN_FAR, line=1.05)),
        ellipse_shape(i2, "FarKneeCap", 322, 226, 14, 14, skin_fill_outlined("FarKnee", -7, 7, SKIN_FAR, line=0.95)),
        smooth_shape(i2, "FarThigh", far_thigh, skin_fill_outlined("FarThigh", 166, 228, SKIN_FAR, line=1.05)),
        smooth_shape(i2, "FarShorts", far_shorts, skin_fill_outlined("FarShorts", 158, 188, SHORTS_FAR, line=1.05)),

        # B. Near (Right) Foreground Leg on FLOOR = 300.0
        stroke_shape(i2, "NearFootHi", [(284, 291), (300, 291), (312, 294)], 1.8, HIGHLIGHT, 1.8),
        smooth_shape(i2, "NearFoot", near_foot, skin_fill_outlined("NearFoot", 288, 300, SKIN, line=1.15)),
        stroke_shape(i2, "NearTibialisLine", [(288, 238), (286, 262), (284, 284)], 1.25, SOFT_SHADOW, 0.5),
        stroke_shape(i2, "NearShinHi", [(291, 238), (290, 262), (288, 284)], 2.4, HIGHLIGHT, 2.4),
        stroke_shape(i2, "NearCalfSh", [(274, 240), (275, 264), (279, 284)], 3.2, CORE_SHADOW, 3.0),
        smooth_shape(i2, "NearShin", near_shin, skin_fill_outlined("NearShin", 228, 292, SKIN, line=1.15)),
        ellipse_shape(i2, "NearKneeCap", 288, 230, 15, 14, skin_fill_outlined("NearKnee", -7, 7, SKIN, line=1.0)),
        stroke_shape(i2, "NearQuadLine", [(288, 188), (290, 208), (288, 222)], 1.3, SOFT_SHADOW, 0.6),
        stroke_shape(i2, "NearThighHi", [(294, 186), (296, 206), (293, 222)], 3.2, HIGHLIGHT, 3.0),
        stroke_shape(i2, "NearThighSh", [(274, 188), (274, 208), (278, 224)], 3.8, CORE_SHADOW, 3.5),
        smooth_shape(i2, "NearThigh", near_thigh, skin_fill_outlined("NearThigh", 168, 232, SKIN, line=1.15)),
        stroke_shape(i2, "NearShortsHem", [(269, 189), (286, 191), (303, 191)], 1.4, "80090D16", 0.4),
        smooth_shape(i2, "NearShorts", near_shorts, skin_fill_outlined("NearShorts", 160, 192, SHORTS, line=1.15)),

        # C. Pelvis Shorts, Torso, 6-Pack Abs & Pectoralis Major
        stroke_shape(i2, "WaistbandSeam", [(272, 151), (298, 152), (324, 151)], 1.6, "80090D16", 0.5),
        smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill_outlined("PelvisShorts", 148, 182, SHORTS, line=1.15)),
        *[smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint) for idx, bpts in enumerate(abs_blocks)],
        stroke_shape(i2, "LineaAlba", [(322, 116), (320, 134), (318, 150)], 1.25, SOFT_SHADOW, 0.4),
        stroke_shape(i2, "PecHi", [(304, 102), (316, 104), (324, 108)], 2.4, HIGHLIGHT, 2.4),
        smooth_shape(i2, "PecNear", pec_near_pts, pec_paint),
        smooth_shape(i2, "PecFar", pec_far_pts, pec_paint),
        stroke_shape(i2, "TorsoBackSh", [(280, 104), (278, 128), (276, 148)], 4.2, CORE_SHADOW, 3.8),
        stroke_shape(i2, "TorsoFrontHi", [(320, 96), (328, 120), (322, 144)], 3.2, HIGHLIGHT, 3.2),
        smooth_shape(i2, "TorsoBase", torso_pts, skin_fill_outlined("Torso", 84, 152, SKIN, line=1.15)),

        # D. Volumetric 3/4 Head & Muscular Neck
        smooth_shape(i2, "HairCap", hair_pts, hair_paint),
        ellipse_shape(i2, "RightEar", 312, 61, 4.8, 7.2, skin_fill_outlined("Ear", -4, 4, SKIN, line=0.85), rot_deg=-10.0),
        stroke_shape(i2, "Eyebrow", [(328, 53), (333, 53)], 1.3, "730F172A", 0.3),
        stroke_shape(i2, "EyeLine", [(328, 56), (332, 56)], 1.05, "800F172A", 0.2),
        stroke_shape(i2, "MouthLine", [(329, 70), (333, 69)], 1.0, "660F172A", 0.2),
        stroke_shape(i2, "JawShadow", [(314, 73), (322, 76), (330, 75)], 2.0, CORE_SHADOW, 1.8),
        stroke_shape(i2, "HeadHi", [(312, 46), (322, 45), (330, 50)], 2.6, HIGHLIGHT, 2.5),
        smooth_shape(i2, "HeadShape", head_pts, skin_fill_outlined("Head", 42, 77, SKIN, line=1.15)),
        stroke_shape(i2, "SCMLine", [(312, 73), (318, 86)], 1.35, SOFT_SHADOW, 0.8),
        smooth_shape(i2, "NeckShape", neck_pts, skin_fill_outlined("Neck", 70, 88, SKIN, line=1.05)),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 4. Pinned Upper Arm (3-Head Triceps Horseshoe) & Pushdown Forearm
def build_pushdown_arm(prefix, far):
    """Pinned vertical Upper Arm with glowing Lateral, Long & Medial heads of Triceps Brachii,
    and sweeping Forearm with highlighted Anconeus & Forearm Extensors."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    sh_pt = FAR_SH if far else NEAR_SH
    ua_len = UA_FAR_LEN if far else UA_NEAR_LEN
    fa_len = FA_FAR_LEN if far else FA_NEAR_LEN
    el_k = "far_el" if far else "near_el"
    ua_ang_k = "ua_far_ang" if far else "ua_near_ang"
    ua_sc_k = "ua_far_sc" if far else "ua_near_sc"
    fa_ang_k = "fa_far_ang" if far else "fa_near_ang"
    fa_sc_k = "fa_far_sc" if far else "fa_near_sc"
    delt_ang_k = "delt_far_ang" if far else "delt_near_ang"
    m_scale = 0.88 if far else 1.00

    ua_id, fa_id, delt_id = nid(), nid(), nid()
    key_double(ua_id, 15, lambda p: p[ua_ang_k])
    key_double(ua_id, 16, lambda p: p[ua_sc_k])

    key_double(fa_id, 13, lambda p: p[el_k][0])
    key_double(fa_id, 14, lambda p: p[el_k][1])
    key_double(fa_id, 15, lambda p: p[fa_ang_k])
    key_double(fa_id, 16, lambda p: p[fa_sc_k])

    key_double(delt_id, 15, lambda p: p[delt_ang_k])
    p0 = POSES[0]

    def tri_lat_t(p):
        return (0.46 + 0.54 * (p["r"] ** 0.74)) * m_scale

    def tri_long_t(p):
        return (0.44 + 0.56 * (p["r"] ** 0.78)) * m_scale

    def anconeus_t(p):
        return (0.40 + 0.54 * (p["r"] ** 0.80)) * m_scale

    # In local UpperArm frame (+X points straight DOWN from Shoulder (0,0) to Elbow (44,0) at +90 deg):
    # +Y points screen-LEFT (posterior/outer aspect of the arm — the Triceps Brachii side!).
    # -Y points screen-RIGHT (anterior/biceps aspect facing the cable).
    ua_pts = [
        (-8, 0), (-5, -9.8), (10, -10.8), (26, -10.0), (ua_len - 4, -7.2),
        (ua_len + 4, 0), (ua_len - 4, 7.8), (26, 11.2), (10, 11.8), (-5, 9.2),
    ]
    # Primary Target Muscle #1: Triceps Brachii — Long Head (posterior +Y border) & Lateral/Medial Horseshoe
    triceps_long_pts = [
        (3, 3.0), (16, 3.8), (30, 3.6), (ua_len - 5, 2.8),
        (ua_len - 6, 7.8), (26, 11.0), (10, 11.5), (2, 8.5),
    ]
    triceps_lat_med_pts = [
        (6, -2.2), (20, -2.5), (34, -1.5), (ua_len - 3, 2.2),
        (30, 5.0), (16, 5.0), (5, 2.8),
    ]

    delt_pts = [
        (-10, -12), (2, -14), (12, -8), (12, 8), (0, 14), (-11, 10), (-12, -2),
    ]

    fa_pts = [
        (-5, 0), (-3, -7.2), (10, -8.2), (24, -6.5), (fa_len - 4, -4.5),
        (fa_len + 4, 0), (fa_len - 4, 4.8), (24, 6.8), (10, 7.8), (-3, 6.5),
    ]
    # Secondary Target Muscle #2: Anconeus & Dorsal Forearm Extensors (along +Y dorsal/outer forearm border)
    anconeus_ext_pts = [
        (-2, 0.8), (10, 1.2), (25, 1.5), (24, 6.0), (10, 7.5), (-2, 5.5),
    ]
    hand_pts = [
        (-4, -5.8), (5, -6.5), (10, -2.5), (10, 4.0), (4, 6.2), (-4, 5.2),
    ]

    return "\n".join([
        f'{ind}<Node name="{prefix}PushdownArm">',
        # 1. Forearm & Pronated Hand Gripping the V-Bar (with highlighted Anconeus & Forearm Extensors)
        f'{i2}<Node x="{f(p0[el_k][0])}" y="{f(p0[el_k][1])}" rotation="{f(p0[fa_ang_k])}" scaleX="{f(p0[fa_sc_k])}" name="{prefix}Forearm" id="{fa_id}">',
        smooth_shape(i3, f"{prefix}Hand", hand_pts, skin_fill_outlined(prefix + "Hand", -7, 7, skin, line=1.1), x=fa_len - 2.0),
        stroke_shape(i3, f"{prefix}AnconeusFiber", [(2, 4.0), (12, 4.4), (22, 3.8)], 1.0, "737F1D1D", 0.3),
        smooth_shape(i3, f"{prefix}AnconeusForearmExt", anconeus_ext_pts, muscle_paint_fn(prefix + "Anconeus", anconeus_t, 0.95)),
        stroke_shape(i3, f"{prefix}ForearmHi", [(6, -4.0), (18, -3.5), (30, -2.4)], 2.2, HIGHLIGHT, 2.2),
        smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill_outlined(prefix + "FA", -8, 8, skin, line=1.15)),
        f"{i2}</Node>",

        # 2. Pinned Vertical Upper Arm with Glowing 3-Head Triceps Brachii Horseshoe
        f'{i2}<Node x="{f(sh_pt[0])}" y="{f(sh_pt[1])}" rotation="{f(p0[ua_ang_k])}" scaleX="{f(p0[ua_sc_k])}" name="{prefix}UpperArm" id="{ua_id}">',
        stroke_shape(i3, f"{prefix}TricepsHorseshoeSplit", [(8, 3.6), (22, 4.2), (36, 3.0)], 1.25, "997F1D1D", 0.3),
        stroke_shape(i3, f"{prefix}TricepsLongFiber", [(10, 8.0), (22, 8.5), (33, 6.8)], 1.05, "737F1D1D", 0.3),
        stroke_shape(i3, f"{prefix}TricepsLatFiber", [(12, 0.8), (24, 1.0), (34, 1.2)], 1.0, "737F1D1D", 0.3),
        stroke_shape(i3, f"{prefix}TricepsSpecHi", [(12, 7.5), (24, 7.8), (34, 6.2)], 2.0, "66FFFFFF", 1.8),
        smooth_shape(i3, f"{prefix}TricepsLongHead", triceps_long_pts, muscle_paint_fn(prefix + "TriLong", tri_long_t, 1.1)),
        smooth_shape(i3, f"{prefix}TricepsLateralMedialHead", triceps_lat_med_pts, muscle_paint_fn(prefix + "TriLat", tri_lat_t, 1.05)),
        stroke_shape(i3, f"{prefix}BicepsAntHi", [(8, -6.2), (22, -6.2), (34, -4.5)], 2.4, HIGHLIGHT, 2.4),
        smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill_outlined(prefix + "UA", -11, 12, skin, line=1.15)),
        f"{i2}</Node>",

        # 3. Neutral Silver-Slate Deltoid Cap on Top of Shoulder Joint
        f'{i2}<Node x="{f(sh_pt[0])}" y="{f(sh_pt[1])}" rotation="{f(p0[delt_ang_k])}" name="{prefix}DeltoidCap" id="{delt_id}">',
        stroke_shape(i3, f"{prefix}DeltGroove", [(0, -8), (2, 8)], 1.15, SOFT_SHADOW, 0.6),
        stroke_shape(i3, f"{prefix}DeltHi", [(-4, -8), (4, -6), (6, 4)], 2.4, HIGHLIGHT, 2.4),
        smooth_shape(i3, f"{prefix}DeltoidBase", delt_pts, skin_fill_outlined(prefix + "Delt", -14, 14, skin, line=1.1)),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    tower_xml = build_high_cable_tower()
    cable_vbar_xml = build_cable_and_vbar()
    body_xml = build_standing_athlete_body()
    near_arm_xml = build_pushdown_arm("Near", False)
    far_arm_xml = build_pushdown_arm("Far", True)

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
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="TricepPushdown" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Right) Pinned Arm with Glowing 3-Head Triceps Horseshoe & Anconeus -->
{near_arm_xml}

        <!-- 2. Taut Steel Cable & Angled Chrome V-Bar Pushdown Handle -->
{cable_vbar_xml}

        <!-- 3. Standing 3/4 Athlete Body (Planted Legs, Shorts, Forward-Leaned Torso & 3/4 Head) -->
{body_xml}

        <!-- 4. Far (Left) Pinned Arm in 3/4 Depth -->
{far_arm_xml}

        <!-- 5. High-Pulley Cable Machine & Animated Weight Stack on Right -->
{tower_xml}

        <!-- 6. Studio Floor Shadows & Ambient Backdrop -->
        <Shape x="304" y="295" scaleX="1.15" scaleY="0.08" name="AthleteFloorShadow">
            <Ellipse width="160" height="160" name="AthleteShadowEllipse"/>
            <Fill name="AthleteShadowFill"><RadialGradient startX="0" startY="0" endX="80" endY="0" name="AthleteShadowGrad">
                <GradientStop colorValue="CC000000" position="0"/>
                <GradientStop colorValue="59000000" position="0.62"/>
                <GradientStop colorValue="00000000" position="1"/>
            </RadialGradient></Fill>
        </Shape>
        <Shape x="462" y="295" scaleX="1.10" scaleY="0.08" name="TowerFloorShadow">
            <Ellipse width="160" height="160" name="TowerShadowEllipse"/>
            <Fill name="TowerShadowFill"><RadialGradient startX="0" startY="0" endX="80" endY="0" name="TowerShadowGrad">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="TricepPushdown" id="0:60">
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
    (BUILD / "tricep_pushdown.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/aff6e669-980f-4ec0-a386-c5be528dd2f8/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (38, "frame_mid"), (74, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(620, 40, 360))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
