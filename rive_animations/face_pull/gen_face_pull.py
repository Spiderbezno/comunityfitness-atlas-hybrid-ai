#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive scene for Cable Face Pull (id: 'face_pull').

Matches the 2-panel 3/4 rear-left Cable Face Pull anatomical reference illustration:
  - Left Panel (Start / Full Extension, r = 0.0):
    * Muscular male athlete standing upright in a stable split/athletic stance on FLOOR = 300.0, facing the
      high cable pulley machine on the left.
    * Both arms extended straight forward-left at shoulder height toward the high pulley (L_SH = (308, 78) ->
      L_EL = (268, 82) -> L_HAND = (232, 76)), hands close together gripping the dual braided rope attachment,
      weight stack resting low on the vertical chrome guide rods.
  - Right Panel (Peak Contraction + External Rotation, r = 1.0):
    * Elbows pulled high and flared wide at shoulder level (L_EL = (272, 62), R_EL = (398, 68)), shoulders
      externally rotated so forearms angle upward and hands pull the dual rope ends apart beside the temples/ears
      (L_HAND = (312, 44), R_HAND = (366, 46)) with black cylindrical rope stoppers visible.
    * Taut cable stretches from the angled overhead boom pulley to the rope center, and the weight stack lifts up
      along the guide rods.
  - Stationary Body Rule:
    * Feet, calves, hamstrings/quads, glutes/shorts, V-tapered torso/spine, lats, neck, and head remain 100%
      stationary throughout the entire repetition (zero torso sway or hip displacement).
  - All 7 Labeled Target Muscle Groups (pulsing from warm orange #FFF97316 at r = 0.0 to vivid crimson #FFF43F5E at r = 1.0):
    1. Posterior deltoid (scale = 1.00 — Primary Mover)
    2. Trapezius (middle and lower) (scale = 0.98 — Primary Mover)
    3. Lateral deltoid (scale = 0.95 — Primary Mover)
    4. Infraspinatus (scale = 0.92 — Primary Rotator Cuff)
    5. Teres minor (scale = 0.92 — Primary External Rotator)
    6. Brachioradialis (scale = 0.88 — Secondary Forearm Flexor/Stabilizer)
    7. Brachialis (scale = 0.86 — Secondary Elbow Flexor)

Run:
    python3 gen_face_pull.py            # writes scene.rml
    python3 gen_face_pull.py --publish  # compiles assets/animations/face_pull.riv + 256x256 thumbnail
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

# Fixed Machine & Segment Rest Constants
PULLEY_EXIT = (198.0, 96.0)
PULLEY_TOP = (218.0, 34.0)
PULLEY_REDIRECT = (168.0, 82.0)

UA_L_LEN, FA_L_LEN = 40.0, 42.0
UA_R_LEN, FA_R_LEN = 38.0, 40.0
CABLE_BASE_LEN = 50.0
ROPE_BASE_LEN = 32.0

# Palette — matches existing 16:9 procedural catalog (dumbbell_row, decline_bench_press, dips, deadlift)
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

# Muscle activation colors: warm orange (#FFF97316) at Extension (r=0.0) -> intense crimson (#FFF43F5E) at Peak Contraction (r=1.0)
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


EASE_PULL = cubic_bezier(0.36, 0.0, 0.24, 1.0)
EASE_RETURN = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def pull_progress(frame):
    """Returns cable face pull progress r in [0.0, 1.0] across 160 frames:
    - 0..12:   Start / Full Extension hold (r = 0.0, Left panel)
    - 12..64:  Concentric face pull + external shoulder rotation (r: 0.0 -> 1.0)
    - 64..84:  Peak Contraction hold beside temples/ears (r = 1.0, Right panel)
    - 84..148: Controlled eccentric return to full forward extension (r: 1.0 -> 0.0)
    - 148..160: Start / Full Extension hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 64:
        return EASE_PULL((fr - 12) / 52.0)
    if fr <= 84:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_RETURN((fr - 84) / 64.0)
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
    sc = max(0.25, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute Cable Face Pull transforms at progress r in [0.0, 1.0].
    Torso, head, pelvis, and legs remain 100% stationary; only the arms, dual rope, cable, and weight stack move."""
    # 1. Near (Left) Arm Trajectory (L_SH -> L_EL -> L_HAND):
    #    - Start (r=0.0): extended forward-left toward pulley: L_SH=(308,78), L_EL=(268,82), L_HAND=(232,76)
    #    - Peak (r=1.0): elbow flared high-left, forearm externally rotated up beside left temple: L_SH=(306,76), L_EL=(272,62), L_HAND=(312,44)
    l_sh = (lerp(308.0, 306.0, r), lerp(78.0, 76.0, r))
    l_el = quad_interp_pt((268.0, 82.0), (266.0, 71.0), (272.0, 62.0), r)
    l_hand = quad_interp_pt((232.0, 76.0), (268.0, 56.0), (312.0, 44.0), r)

    ua_l_ang, ua_l_sc = seg_xform(l_sh, l_el, UA_L_LEN)
    fa_l_ang, fa_l_sc = seg_xform(l_el, l_hand, FA_L_LEN)

    # 2. Far (Right) Arm Trajectory (R_SH -> R_EL -> R_HAND):
    #    - Start (r=0.0): tucked behind torso/left arm with right hand & stopper peeking out at (242, 74)
    #    - Peak (r=1.0): elbow flared wide-right, forearm externally rotated up beside right temple: R_SH=(368,78), R_EL=(398,68), R_HAND=(366,46)
    r_sh = (lerp(360.0, 368.0, r), lerp(79.0, 78.0, r))
    r_el = quad_interp_pt((284.0, 81.0), (346.0, 66.0), (398.0, 68.0), r)
    r_hand = quad_interp_pt((242.0, 74.0), (306.0, 55.0), (366.0, 46.0), r)

    ua_r_ang, ua_r_sc = seg_xform(r_sh, r_el, UA_R_LEN)
    fa_r_ang, fa_r_sc = seg_xform(r_el, r_hand, FA_R_LEN)
    delt_r_ang = math.radians(lerp(12.0, -18.0, r))

    # 3. Rope Split Collar & Taut Steel Cable from PULLEY_EXIT = (198, 96):
    rope_center = quad_interp_pt((216.0, 84.0), (254.0, 72.0), (294.0, 60.0), r)
    cable_ang, cable_sc = seg_xform(PULLEY_EXIT, rope_center, CABLE_BASE_LEN)
    rope_l_ang, rope_l_sc = seg_xform(rope_center, l_hand, ROPE_BASE_LEN)
    rope_r_ang, rope_r_sc = seg_xform(rope_center, r_hand, ROPE_BASE_LEN)

    # 4. Weight Stack Vertical Lift (r=0.0: 0.0 -> r=1.0: -44.0 px upward along guide rods):
    stack_lift_y = lerp(0.0, -44.0, r)

    return {
        "r": r,
        "l_sh": l_sh,
        "l_el": l_el,
        "l_hand": l_hand,
        "ua_l_ang": ua_l_ang,
        "ua_l_sc": ua_l_sc,
        "fa_l_ang": fa_l_ang,
        "fa_l_sc": fa_l_sc,
        "r_sh": r_sh,
        "r_el": r_el,
        "r_hand": r_hand,
        "ua_r_ang": ua_r_ang,
        "ua_r_sc": ua_r_sc,
        "fa_r_ang": fa_r_ang,
        "fa_r_sc": fa_r_sc,
        "delt_r_ang": delt_r_ang,
        "rope_center": rope_center,
        "cable_ang": cable_ang,
        "cable_sc": cable_sc,
        "rope_l_ang": rope_l_ang,
        "rope_l_sc": rope_l_sc,
        "rope_r_ang": rope_r_ang,
        "rope_r_sc": rope_r_sc,
        "stack_lift_y": stack_lift_y,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(pull_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = (
    "ua_l_ang",
    "fa_l_ang",
    "ua_r_ang",
    "fa_r_ang",
    "delt_r_ang",
    "cable_ang",
    "rope_l_ang",
    "rope_r_ang",
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
            f"f{_fr:3d} r={_p['r']:.3f} l_el=({_p['l_el'][0]:.1f},{_p['l_el'][1]:.1f}) "
            f"l_hand=({_p['l_hand'][0]:.1f},{_p['l_hand'][1]:.1f}) "
            f"r_el=({_p['r_el'][0]:.1f},{_p['r_el'][1]:.1f}) "
            f"r_hand=({_p['r_hand'][0]:.1f},{_p['r_hand'][1]:.1f})"
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
    """Cable Face Pull muscle activation intensity in [0.42, 1.0] peaking at Peak Contraction (r = 1.0)."""
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


# ---------------------------------------------------------------- 1. High Cable Pulley Machine & Animated Weight Stack (Left Side)
def high_cable_pulley_machine():
    """High cable pulley tower on the left (x = 128..232, y = 24..300) matching the reference illustration:
    - White steel base frame, angled front stabilizer brace, and dual foam knee-hold rollers
    - Twin vertical chrome guide rods & animated multi-plate black weight stack (lifts by -44 px at r = 1.0)
    - Angled overhead pulley boom arm with 3 pulley wheels & internal lift cable."""
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

    # Machine frame geometry
    base_left = [(126, 290), (186, 286), (188, 294), (128, 298)]
    base_front = [(182, 286), (232, 294), (230, 300), (180, 294)]
    angled_brace = [(192, 224), (202, 226), (226, 294), (214, 294)]
    rear_post = [(134, 58), (144, 58), (144, 292), (134, 292)]
    main_column = [(182, 58), (195, 58), (195, 292), (182, 292)]
    mid_collar = [(132, 118), (198, 120), (198, 142), (132, 140)]
    lower_collar = [(132, 198), (198, 200), (198, 220), (132, 218)]
    top_cap = [(124, 52), (198, 56), (196, 62), (122, 58)]
    boom_arm = [(186, 134), (212, 26), (224, 30), (198, 138)]

    # Weight stack block (at rest y = 206..278; lifts by -44 px at r = 1.0 to y = 162..234)
    stack_block = [(146, 206), (180, 206), (180, 278), (146, 278)]
    plate_lines = [
        stroke_shape(i3, f"StackGroove{idx}", [(147, y), (179, y)], 1.1, "FF020617", 0.0)
        for idx, y in enumerate(range(212, 276, 6))
    ]

    return "\n".join([
        f'{ind}<Node name="HighCablePulleyMachine">',

        # 1. Foreground Machine Elements: Overhead Angled Pulley Boom, Collar Brackets & Foam Knee Rollers
        ellipse_shape(i2, "RollerPadNearEnd", 184, 214, 10, 12, solid("RollerCap1", "FF020617")),
        poly_shape(i2, "RollerPadNear", [(184, 208), (206, 212), (204, 222), (182, 218)], pad_paint("RollerN", 182, 208, 206, 222), radius=4.0),
        poly_shape(i2, "RollerPadFar", [(204, 210), (224, 204), (226, 214), (206, 220)], pad_paint("RollerF", 204, 204, 226, 220), radius=4.0),
        ellipse_shape(i2, "TopPulleyHub", PULLEY_TOP[0], PULLEY_TOP[1], 4.5, 4.5, hub_paint),
        ellipse_shape(i2, "TopPulleyWheel", PULLEY_TOP[0], PULLEY_TOP[1], 14.0, 14.0, pulley_paint),
        ellipse_shape(i2, "ExitPulleyHub", PULLEY_EXIT[0], PULLEY_EXIT[1], 4.0, 4.0, hub_paint),
        ellipse_shape(i2, "ExitPulleyWheel", PULLEY_EXIT[0], PULLEY_EXIT[1], 12.0, 12.0, pulley_paint),
        stroke_shape(i2, "BoomArmHi", [(190, 130), (215, 30)], 2.0, "FFFFFFFF", 0.4),
        poly_shape(i2, "OverheadBoomArm", boom_arm, frame_paint("BoomArm", 186, 26, 224, 138), radius=3.0),
        poly_shape(i2, "TowerMidCollar", mid_collar, frame_paint("MidCollar", 132, 118, 198, 142), radius=1.5),
        poly_shape(i2, "TowerLowerCollar", lower_collar, frame_paint("LowCollar", 132, 198, 198, 220), radius=1.5),

        # 2. Main Upright Column, Angled Stabilizer Brace & Base Feet on FLOOR = 300.0
        poly_shape(i2, "FrontRubberFoot", [(220, 293), (234, 294), (233, 300), (219, 300)], pad_paint("FrontFootCap", 219, 293, 234, 300), radius=1.5),
        poly_shape(i2, "FrontStabilizerBase", base_front, frame_paint("BaseFront", 180, 286, 232, 300), radius=1.5),
        poly_shape(i2, "AngledStabilizerBrace", angled_brace, frame_paint("AngledBrace", 192, 224, 226, 294), radius=2.0),
        stroke_shape(i2, "MainColumnHi", [(185, 62), (185, 288)], 2.2, "FFFFFFFF", 0.4),
        poly_shape(i2, "MainUprightColumn", main_column, frame_paint("MainCol", 182, 58, 195, 292), radius=1.5),
        poly_shape(i2, "TopHeaderCap", top_cap, frame_paint("TopCap", 122, 52, 198, 62), radius=2.0),

        # 3. Animated Weight Stack & Vertical Lift Cable (slides up along the guide rods as r: 0.0 -> 1.0)
        f'{i2}<Node x="0" y="0" name="WeightStackGroup" id="{stack_id}">',
        polyline_stroke_shape(i3, "StackLiftRod", [(163, 140), (163, 206)], 2.2, "FF0F172A", radius=0.0),
        *plate_lines,
        poly_shape(i3, "WeightStackPlates", stack_block, pad_paint("WeightStack", 146, 206, 180, 278), radius=2.0),
        f"{i2}</Node>",

        # 4. Fixed Upper Internal Cable Routing & Chrome Guide Rods
        polyline_stroke_shape(
            i2,
            "InternalTowerCable",
            [(163, 206), (163, 82), PULLEY_TOP, PULLEY_EXIT],
            1.7,
            "FF0F172A",
            radius=1.0,
        ),
        ellipse_shape(i2, "RedirectPulleyWheel", PULLEY_REDIRECT[0], PULLEY_REDIRECT[1], 11.0, 11.0, pulley_paint),
        polyline_stroke_shape(i2, "GuideRodLeft", [(152, 58), (152, 290)], 3.2, "FF94A3B8", radius=0.0),
        polyline_stroke_shape(i2, "GuideRodRight", [(172, 58), (172, 290)], 3.2, "FF94A3B8", radius=0.0),
        poly_shape(i2, "RearUprightPost", rear_post, frame_paint("RearPost", 134, 58, 144, 292, far=True), radius=1.5),
        poly_shape(i2, "RearBasePlate", base_left, frame_paint("BaseLeft", 126, 286, 188, 298, far=True), radius=1.5),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 2. Taut Cable & Dual Braided Rope Attachment
def cable_and_dual_rope():
    """Taut steel cable from PULLEY_EXIT (198, 96) to ROPE_CENTER, plus the V-shaped dual braided black rope strands
    connecting ROPE_CENTER to L_HAND and R_HAND."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    cab_id, rl_id, rr_id, col_id = nid(), nid(), nid(), nid()

    key_double(cab_id, 15, lambda p: p["cable_ang"])
    key_double(cab_id, 16, lambda p: p["cable_sc"])

    key_double(rl_id, 13, lambda p: p["rope_center"][0])
    key_double(rl_id, 14, lambda p: p["rope_center"][1])
    key_double(rl_id, 15, lambda p: p["rope_l_ang"])
    key_double(rl_id, 16, lambda p: p["rope_l_sc"])

    key_double(rr_id, 13, lambda p: p["rope_center"][0])
    key_double(rr_id, 14, lambda p: p["rope_center"][1])
    key_double(rr_id, 15, lambda p: p["rope_r_ang"])
    key_double(rr_id, 16, lambda p: p["rope_r_sc"])

    key_double(col_id, 13, lambda p: p["rope_center"][0])
    key_double(col_id, 14, lambda p: p["rope_center"][1])
    p0 = POSES[0]

    return "\n".join([
        f'{ind}<Node name="CableAndDualRopeGroup">',

        # 1. Chrome Swivel Collar at ROPE_CENTER
        f'{i2}<Node x="{f(p0["rope_center"][0])}" y="{f(p0["rope_center"][1])}" name="RopeSwivelCollar" id="{col_id}">',
        ellipse_shape(i3, "SwivelEyelet", 0.0, 0.0, 6.5, 6.5, skin_fill_outlined("Swivel", -3, 3, ("FFE2E8F0", "FF94A3B8", "FF334155"), line=0.9)),
        f"{i2}</Node>",

        # 2. Left Braided Rope Strand (ROPE_CENTER -> L_HAND)
        f'{i2}<Node x="{f(p0["rope_center"][0])}" y="{f(p0["rope_center"][1])}" '
        f'rotation="{f(p0["rope_l_ang"])}" scaleX="{f(p0["rope_l_sc"])}" name="LeftRopeStrand" id="{rl_id}">',
        polyline_stroke_shape(i3, "LeftRopeBraidHi", [(2.0, -0.8), (ROPE_BASE_LEN, -0.8)], 1.2, "FF475569", radius=0.0),
        polyline_stroke_shape(i3, "LeftRopeCore", [(0.0, 0.0), (ROPE_BASE_LEN, 0.0)], 4.2, "FF090D16", radius=0.0),
        f"{i2}</Node>",

        # 3. Right Braided Rope Strand (ROPE_CENTER -> R_HAND)
        f'{i2}<Node x="{f(p0["rope_center"][0])}" y="{f(p0["rope_center"][1])}" '
        f'rotation="{f(p0["rope_r_ang"])}" scaleX="{f(p0["rope_r_sc"])}" name="RightRopeStrand" id="{rr_id}">',
        polyline_stroke_shape(i3, "RightRopeBraidHi", [(2.0, -0.8), (ROPE_BASE_LEN, -0.8)], 1.2, "FF475569", radius=0.0),
        polyline_stroke_shape(i3, "RightRopeCore", [(0.0, 0.0), (ROPE_BASE_LEN, 0.0)], 4.0, "FF090D16", radius=0.0),
        f"{i2}</Node>",

        # 4. Taut Working Steel Cable (PULLEY_EXIT -> ROPE_CENTER)
        f'{i2}<Node x="{f(PULLEY_EXIT[0])}" y="{f(PULLEY_EXIT[1])}" '
        f'rotation="{f(p0["cable_ang"])}" scaleX="{f(p0["cable_sc"])}" name="TautWorkingCable" id="{cab_id}">',
        polyline_stroke_shape(i3, "CableSheen", [(0.0, -0.5), (CABLE_BASE_LEN, -0.5)], 0.7, "FF94A3B8", radius=0.0),
        polyline_stroke_shape(i3, "CableWire", [(0.0, 0.0), (CABLE_BASE_LEN, 0.0)], 1.8, "FF0F172A", radius=0.0),
        f"{i2}</Node>",

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 3. Far (Right) Arm & Right Shoulder Cap
def far_right_arm():
    """Far (Right) arm (R_SH -> R_EL -> R_HAND) with activated Posterior deltoid, Lateral deltoid, Brachialis,
    and Brachioradialis (clearly visible on the right at Peak Contraction r = 1.0)."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    ua_id, fa_id, delt_id = nid(), nid(), nid()

    key_double(ua_id, 13, lambda p: p["r_sh"][0])
    key_double(ua_id, 14, lambda p: p["r_sh"][1])
    key_double(ua_id, 15, lambda p: p["ua_r_ang"])
    key_double(ua_id, 16, lambda p: p["ua_r_sc"])

    key_double(fa_id, 13, lambda p: p["r_el"][0])
    key_double(fa_id, 14, lambda p: p["r_el"][1])
    key_double(fa_id, 15, lambda p: p["fa_r_ang"])
    key_double(fa_id, 16, lambda p: p["fa_r_sc"])

    key_double(delt_id, 13, lambda p: p["r_sh"][0])
    key_double(delt_id, 14, lambda p: p["r_sh"][1])
    key_double(delt_id, 15, lambda p: p["delt_r_ang"])
    p0 = POSES[0]

    # 1. Right Shoulder Cap at R_SH = (368, 79) with Lateral deltoid (upper cap) & Posterior deltoid (lower/dorsal cap)
    delt_r_pts = [
        (-10, -2), (-6, -11.5), (6, -11.5), (17, -7.5), (19, 0),
        (16, 8.5), (5, 11.0), (-7, 9.5),
    ]
    lat_delt_r_pts = [
        (-6, -3.0), (-4, -10.8), (6, -11.0), (16, -7.0), (16, -1.5), (4, -1.5),
    ]
    post_delt_r_pts = [
        (-6, -1.5), (5, -1.5), (17, -1.0), (15, 7.8), (5, 10.2), (-6, 8.2),
    ]

    # 2. Right Upper Arm (R_SH -> R_EL, UA_R_LEN = 38) with Target Muscle #7: Brachialis (scale = 0.86)
    ua_r_pts = [
        (-8, 0), (-4, -9.8), (UA_R_LEN * 0.45, -10.2), (UA_R_LEN - 4, -6.5),
        (UA_R_LEN + 3, 0), (UA_R_LEN - 4, 6.5), (UA_R_LEN * 0.45, 9.8), (-4, 9.2),
    ]
    brachialis_r_pts = [
        (12, -8.5), (24, -8.8), (34, -4.5), (32, -0.5), (20, -1.0), (12, -3.5),
    ]

    # 3. Right Forearm & Hand (R_EL -> R_HAND, FA_R_LEN = 40) with Target Muscle #6: Brachioradialis (scale = 0.88)
    fa_r_pts = [
        (-6, 0), (-3, -7.8), (FA_R_LEN * 0.35, -8.5), (FA_R_LEN - 5, -5.0),
        (FA_R_LEN + 3, 0), (FA_R_LEN - 5, 5.0), (FA_R_LEN * 0.35, 8.8), (-3, 7.8),
    ]
    brachioradialis_r_pts = [
        (0, 1.0), (12, 1.5), (25, 2.5), (24, 6.5), (12, 8.0), (0, 6.5),
    ]
    hand_r_pts = [
        (FA_R_LEN - 5, -5.8), (FA_R_LEN + 5, -5.5), (FA_R_LEN + 7, 0.0),
        (FA_R_LEN + 5, 5.8), (FA_R_LEN - 5, 5.5),
    ]
    stopper_paint = skin_fill_outlined("StopperR", -4, 4, PAD_DARK, line=1.0, stroke_col="FF475569")

    return "\n".join([
        f'{ind}<Node name="FarRightArmGroup">',

        # 1. Right Shoulder Cap (Posterior Deltoid & Lateral Deltoid)
        f'{i2}<Node x="{f(p0["r_sh"][0])}" y="{f(p0["r_sh"][1])}" '
        f'rotation="{f(p0["delt_r_ang"])}" name="RightDeltoidCap" id="{delt_id}">',
        stroke_shape(i3, "PostDeltRFiber", [(-2, 4.0), (12, 3.8)], 1.0, "667F1D1D", 0.3),
        smooth_shape(i3, "PosteriorDeltoidR", post_delt_r_pts, muscle_paint("PostDeltR", scale=1.00, line=1.0)),
        smooth_shape(i3, "LateralDeltoidR", lat_delt_r_pts, muscle_paint("LatDeltR", scale=0.95, line=1.0)),
        smooth_shape(i3, "RightDeltoidBase", delt_r_pts, skin_fill_outlined("RightDeltBase", -11, 11, SKIN_FAR, line=1.1)),
        f"{i2}</Node>",

        # 2. Right Upper Arm with Target Muscle #7: Brachialis (labeled on the right arm in the reference image!)
        f'{i2}<Node x="{f(p0["r_sh"][0])}" y="{f(p0["r_sh"][1])}" '
        f'rotation="{f(p0["ua_r_ang"])}" scaleX="{f(p0["ua_r_sc"])}" name="RightUpperArm" id="{ua_id}">',
        stroke_shape(i3, "BrachialisRFiber", [(15, -4.5), (30, -3.5)], 0.95, "667F1D1D", 0.3),
        smooth_shape(i3, "BrachialisR", brachialis_r_pts, muscle_paint("BrachialisR", scale=0.86, line=0.95)),
        stroke_shape(i3, "RightTricepsLine", [(10, 3.5), (UA_R_LEN - 6, 3.0)], 1.15, ANATOMY_LINE, 0.2),
        smooth_shape(i3, "RightUpperArmShape", ua_r_pts, skin_fill_outlined("RightUpperArm", -10, 10, SKIN_FAR, line=1.1)),
        f"{i2}</Node>",

        # 3. Right Forearm, Brachioradialis (labeled at top-right of reference image!), Right Hand & Black Rope Stopper
        f'{i2}<Node x="{f(p0["r_el"][0])}" y="{f(p0["r_el"][1])}" '
        f'rotation="{f(p0["fa_r_ang"])}" scaleX="{f(p0["fa_r_sc"])}" name="RightForearmAndHand" id="{fa_id}">',
        ellipse_shape(i3, "RightRopeStopper", FA_R_LEN + 3.5, 4.5, 8.5, 8.5, stopper_paint),
        stroke_shape(i3, "RightKnuckle1", [(FA_R_LEN - 2, -2.5), (FA_R_LEN + 4, -2.5)], 0.9, ANATOMY_LINE, 0.0),
        stroke_shape(i3, "RightKnuckle2", [(FA_R_LEN - 2, 1.5), (FA_R_LEN + 4, 1.5)], 0.9, ANATOMY_LINE, 0.0),
        smooth_shape(i3, "RightGrippingHand", hand_r_pts, skin_fill_outlined("RightHand", -6, 6, SKIN_FAR, line=1.05)),
        stroke_shape(i3, "BrachioradialisRFiber", [(4, 4.2), (21, 4.5)], 0.95, "667F1D1D", 0.3),
        smooth_shape(i3, "BrachioradialisR", brachioradialis_r_pts, muscle_paint("BrachioradialisR", scale=0.88, line=0.95)),
        stroke_shape(i3, "RightForearmLine", [(5, -2.5), (FA_R_LEN - 8, -2.0)], 1.1, ANATOMY_LINE, 0.2),
        smooth_shape(i3, "RightForearmShape", fa_r_pts, skin_fill_outlined("RightForearm", -9, 9, SKIN_FAR, line=1.1)),
        f"{i2}</Node>",

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 4. Stationary 3/4 Rear-Left Athlete Body (Legs, Shorts, Back, Head)
def stationary_athlete_body():
    """100% stationary 3/4 rear-left standing male athlete (zero torso lean or hip shift during the face pull):
    - Planted left & right legs with sculpted hamstrings, vastus lateralis, diamond gastrocnemius calves, and bare feet on FLOOR = 300.0
    - Dark compression shorts over pelvis/glutes
    - V-tapered upper back with Trapezius (middle & lower), Infraspinatus, and Teres minor strictly inside TorsoSilhouette
    - Volumetric 3/4 rear-left head, ear, hairline, and muscular neck."""
    ind = "        "
    i2 = ind + "    "

    # 1. Far (Right) Standing Leg (planted slightly back-right at y = 290)
    far_foot = [(338, 286), (356, 276), (370, 278), (372, 288), (340, 290)]
    far_calf = [
        (352, 206), (368, 206), (378, 232), (372, 258), (368, 280),
        (358, 280), (354, 256), (348, 232),
    ]
    far_thigh = [
        (342, 152), (374, 152), (376, 182), (370, 210), (352, 210), (344, 184),
    ]

    # 2. Near (Left) Standing Leg (planted in foreground-left on FLOOR = 300.0 facing the cable machine)
    near_foot = [
        (276, 295), (296, 284), (314, 282), (318, 294), (314, 299), (278, 299),
    ]
    near_calf = [
        (298, 210), (318, 210), (328, 236), (322, 262), (315, 286),
        (301, 286), (298, 262), (294, 236),
    ]
    near_thigh = [
        (296, 150), (338, 154), (334, 186), (322, 214), (298, 214), (294, 184),
    ]

    # 3. Compression Shorts (Pelvis & Sculpted Glutes)
    shorts_pts = [
        (306, 128), (362, 128), (376, 148), (374, 168),
        (342, 170), (338, 164), (296, 164), (298, 144),
    ]

    # 4. V-Tapered Dorsal Torso Silhouette (100% stationary, encloses all dorsal muscles cleanly)
    torso_pts = [
        (300, 76),   # left shoulder acromion
        (322, 66),   # left base of neck / upper trapezius
        (354, 66),   # right base of neck / upper trapezius
        (372, 76),   # right shoulder acromion
        (378, 96),   # right teres / upper lat flare
        (366, 118),  # right mid-lat taper
        (358, 136),  # right waist / iliac crest
        (310, 136),  # left waist / iliac crest
        (304, 116),  # left mid-lat / serratus
        (296, 96),   # left teres / axillary border
    ]

    # 5. Stationary Dorsal & Scapular Target Muscles (strictly inside torso_pts, bridging seamlessly to both deltoids!):
    #    - Target Muscle #2: Trapezius (middle and lower) (scale = 0.98 — diamond/kite shape along the spine)
    trap_mid_low_pts = [
        (322, 67), (354, 67), (368, 76), (354, 98),
        (341, 128), (336, 128), (324, 98), (310, 76),
    ]
    #    - Target Muscle #4: Infraspinatus (Left & Right scapulae, scale = 0.92)
    infra_l_pts = [
        (304, 75), (328, 75), (330, 95), (308, 94),
    ]
    infra_r_pts = [
        (350, 75), (371, 75), (368, 94), (348, 95),
    ]
    #    - Target Muscle #5: Teres minor (Left & Right scapulae, scale = 0.92 — narrow oblique rotator-cuff band)
    teres_min_l_pts = [
        (299, 85), (316, 85), (324, 98), (305, 99),
    ]
    teres_min_r_pts = [
        (360, 85), (375, 85), (371, 99), (356, 98),
    ]

    # 6. Volumetric 3/4 Rear-Left Head & Neck (facing left toward the high pulley)
    neck_pts = [
        (327, 52), (348, 52), (350, 61), (352, 71), (324, 71), (326, 61),
    ]
    head_pts = [
        (322, 61),  # left jaw / chin angle
        (318, 56),  # left cheek
        (317, 49),  # left zygoma / orbital rim
        (319, 41),  # left temple / forehead
        (327, 33),  # front-left crown
        (341, 31),  # cranial dome
        (353, 37),  # posterior parietal crown
        (356, 48),  # occiput
        (351, 58),  # nape / mastoid
        (336, 61),  # lower skull base
    ]
    hair_pts = [
        (320, 42), (327, 32), (341, 30), (354, 36), (357, 48),
        (351, 56), (342, 52), (334, 48), (326, 44),
    ]
    hair_paint = (
        f'<Fill name="HairFill">{grad("HairGrad", 320, 30, 357, 56, "FF334155", "FF0F172A")}</Fill>'
        '<Stroke thickness="0.95" join="round" name="HairStroke"><SolidColor colorValue="FF090D16" name="HairStrokeCol"/></Stroke>'
    )

    return "\n".join([
        f'{ind}<Node name="AthleteBodyTorsoHeadAndLegs">',

        # A. Volumetric 3/4 Rear-Left Head
        ellipse_shape(i2, "LeftEar", 326, 51, 4.6, 7.2, skin_fill_outlined("Ear", -4, 4, SKIN_FAR, line=0.85), rot_deg=-8.0),
        smooth_shape(i2, "HairCap", hair_pts, hair_paint),
        stroke_shape(i2, "LeftBrowHint", [(318, 45), (322, 45)], 1.2, "FF1E293B", 0.0),
        stroke_shape(i2, "LeftJawShadow", [(321, 59), (327, 57)], 1.3, CORE_SHADOW, 1.0),
        smooth_shape(i2, "HeadShape", head_pts, skin_fill_outlined("Head", 31, 61, SKIN, line=1.1)),

        # B. V-Tapered Upper Back & Target Dorsal/Scapular Muscles (strictly inside TorsoSilhouette!)
        #    1. Trapezius (middle and lower) with median spine raphe & diagonal fiber striations
        stroke_shape(i2, "TrapSpineRaphe", [(339, 68), (339, 126)], 1.3, "807F1D1D", 0.2),
        stroke_shape(i2, "TrapFiberL1", [(318, 78), (337, 82)], 1.0, "667F1D1D", 0.3),
        stroke_shape(i2, "TrapFiberL2", [(324, 92), (338, 102)], 1.0, "667F1D1D", 0.3),
        stroke_shape(i2, "TrapFiberR1", [(360, 78), (341, 82)], 1.0, "667F1D1D", 0.3),
        stroke_shape(i2, "TrapFiberR2", [(354, 92), (340, 102)], 1.0, "667F1D1D", 0.3),
        smooth_shape(i2, "TrapeziusMidLow", trap_mid_low_pts, muscle_paint("TrapMidLow", scale=0.98, line=1.05)),
        #    2. Infraspinatus (Left & Right scapulae)
        stroke_shape(i2, "InfraLFiber", [(312, 86), (326, 89)], 0.95, "667F1D1D", 0.3),
        smooth_shape(i2, "InfraspinatusL", infra_l_pts, muscle_paint("InfraL", scale=0.92, line=1.0)),
        smooth_shape(i2, "InfraspinatusR", infra_r_pts, muscle_paint("InfraR", scale=0.92, line=1.0)),
        #    3. Teres minor (Left & Right scapulae)
        smooth_shape(i2, "TeresMinorL", teres_min_l_pts, muscle_paint("TeresMinL", scale=0.92, line=1.0)),
        smooth_shape(i2, "TeresMinorR", teres_min_r_pts, muscle_paint("TeresMinR", scale=0.92, line=1.0)),
        #    4. Sculpted Latissimus Dorsi, Teres Major & Thoracolumbar Fascia Contours on TorsoSilhouette
        stroke_shape(i2, "TeresMajorCreaseL", [(300, 99), (324, 102)], 1.35, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "TeresMajorCreaseR", [(374, 99), (354, 102)], 1.35, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "LatSweepLineL", [(306, 108), (328, 120)], 1.25, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "LatSweepLineR", [(368, 108), (350, 120)], 1.25, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "LumbarGroove", [(338, 118), (338, 134)], 1.8, CORE_SHADOW, 1.5),
        stroke_shape(i2, "BackLeftSh", [(302, 102), (310, 128)], 4.0, CORE_SHADOW, 3.8),
        smooth_shape(i2, "TorsoSilhouette", torso_pts, skin_fill_outlined("Torso", 66, 138, SKIN, line=1.15)),
        stroke_shape(i2, "NeckTendonL", [(332, 55), (330, 67)], 1.2, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "NeckTendonR", [(344, 55), (346, 67)], 1.2, ANATOMY_LINE, 0.2),
        smooth_shape(i2, "NeckShape", neck_pts, skin_fill_outlined("Neck", 52, 70, SKIN_FAR, line=1.0)),

        # C. Compression Shorts (Pelvis & Sculpted Glutes)
        stroke_shape(i2, "ShortsWaistband", [(305, 130), (338, 131), (363, 130)], 2.2, "CC020617", 0.0),
        stroke_shape(i2, "GluteCleftLine", [(344, 138), (342, 164)], 1.6, "CC020617", 0.2),
        stroke_shape(i2, "GluteFoldL", [(304, 158), (334, 162)], 1.4, "CC020617", 0.2),
        stroke_shape(i2, "GluteFoldR", [(344, 162), (370, 160)], 1.4, "CC020617", 0.2),
        smooth_shape(i2, "PelvisShorts", shorts_pts, skin_fill_outlined("PelvisShorts", 128, 170, SHORTS, line=1.15, stroke_col="CC020617")),

        # D. Near (Left) Standing Leg (Foreground Left, planted at FLOOR = 300.0)
        stroke_shape(i2, "NearAnkleBone", [(306, 282), (310, 287)], 1.1, ANATOMY_LINE, 0.0),
        smooth_shape(i2, "NearStandingFoot", near_foot, skin_fill_outlined("NearFoot", 282, 299, SKIN, line=1.15)),
        stroke_shape(i2, "NearGastrocSplit", [(312, 218), (314, 248), (308, 276)], 1.35, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "NearSoleusLine", [(301, 226), (303, 272)], 1.2, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "NearCalfHi", [(316, 220), (316, 260)], 3.0, HIGHLIGHT, 2.8),
        smooth_shape(i2, "NearStandingCalf", near_calf, skin_fill_outlined("NearCalf", 210, 286, SKIN, line=1.15)),
        stroke_shape(i2, "NearBicepsFemorisLine", [(314, 162), (312, 206)], 1.35, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "NearVastusLatLine", [(302, 164), (302, 204)], 1.3, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "NearThighHi", [(318, 164), (316, 202)], 3.4, HIGHLIGHT, 3.2),
        stroke_shape(i2, "NearThighSh", [(299, 166), (299, 204)], 3.8, CORE_SHADOW, 3.6),
        smooth_shape(i2, "NearStandingThigh", near_thigh, skin_fill_outlined("NearThigh", 150, 214, SKIN, line=1.15)),

        # E. Far (Right) Standing Leg (Mid-Background Right)
        smooth_shape(i2, "FarStandingFoot", far_foot, skin_fill_outlined("FarFoot", 276, 290, SKIN_FAR, line=1.1)),
        stroke_shape(i2, "FarGastrocSplit", [(364, 214), (366, 244), (362, 272)], 1.25, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "FarCalfHi", [(368, 218), (368, 254)], 2.6, HIGHLIGHT, 2.5),
        smooth_shape(i2, "FarStandingCalf", far_calf, skin_fill_outlined("FarCalf", 206, 280, SKIN_FAR, line=1.1)),
        stroke_shape(i2, "FarHamstringLine", [(358, 160), (358, 202)], 1.25, ANATOMY_LINE, 0.2),
        smooth_shape(i2, "FarStandingThigh", far_thigh, skin_fill_outlined("FarThigh", 152, 210, SKIN_FAR, line=1.1)),

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 5. Near (Left) Arm & Left Shoulder Cap (Foreground)
def near_left_arm():
    """Near (Left) arm (L_SH -> L_EL -> L_HAND) in the foreground with activated Posterior deltoid (scale=1.00),
    Lateral deltoid (scale=0.95), Brachialis (scale=0.86), and Brachioradialis (scale=0.88), plus left hand & rope stopper."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    ua_id, fa_id = nid(), nid()

    key_double(ua_id, 13, lambda p: p["l_sh"][0])
    key_double(ua_id, 14, lambda p: p["l_sh"][1])
    key_double(ua_id, 15, lambda p: p["ua_l_ang"])
    key_double(ua_id, 16, lambda p: p["ua_l_sc"])

    key_double(fa_id, 13, lambda p: p["l_el"][0])
    key_double(fa_id, 14, lambda p: p["l_el"][1])
    key_double(fa_id, 15, lambda p: p["fa_l_ang"])
    key_double(fa_id, 16, lambda p: p["fa_l_sc"])
    p0 = POSES[0]

    # Note on NearLeftUpperArm local coordinates (ua_l_ang is ~174 deg at r=0.0 -> ~202 deg at r=1.0):
    #   - Local +X (0 -> UA_L_LEN = 40) points LEFT from L_SH toward L_EL.
    #   - Local +Y (y > 0) points UP on screen (superior border: Lateral deltoid & Biceps peak).
    #   - Local -Y (y < 0) points DOWN on screen (posterior-inferior border: Posterior deltoid, Brachialis & Triceps).
    ua_l_pts = [
        (-10, 0), (-6, -10.5), (10, -11.0), (24, -9.8), (UA_L_LEN - 4, -6.5),
        (UA_L_LEN + 3, 0), (UA_L_LEN - 4, 6.8), (24, 10.2), (10, 11.0), (-6, 10.5),
    ]
    delt_l_pts = [
        (-11, 0), (-7, -10.8), (6, -11.2), (18, -7.5), (20, 0),
        (18, 8.2), (6, 11.2), (-7, 10.5),
    ]
    # Target Muscle #3: Lateral deltoid (scale = 0.95 — superior cap, y > 0)
    lat_delt_l_pts = [
        (-7, 1.5), (5, 1.5), (17, 1.5), (16, 7.8), (6, 10.5), (-6, 9.5),
    ]
    # Target Muscle #1: Posterior deltoid (scale = 1.00 — posterior/dorsal cap, y <= 1.5)
    post_delt_l_pts = [
        (-8, 1.5), (-6, -9.8), (6, -10.5), (17, -7.0), (18, 1.0), (5, 2.0),
    ]
    # Target Muscle #7: Brachialis (scale = 0.86 — outer lateral groove between biceps and triceps, x = 18..36)
    brachialis_l_pts = [
        (18, -1.0), (24, -4.5), (34, -4.0), (36, 0.0), (32, 2.5), (22, 2.0),
    ]

    # NearLeftForearm along +X (0 -> FA_L_LEN = 42):
    #   - At r=0.0 (+189 deg) and r=1.0 (+336 deg), local +Y (y > 0) is the radial/Brachioradialis border!
    fa_l_pts = [
        (-7, 0), (-3, -8.2), (FA_L_LEN * 0.35, -8.8), (FA_L_LEN - 5, -5.2),
        (FA_L_LEN + 3, 0), (FA_L_LEN - 5, 5.2), (FA_L_LEN * 0.35, 8.8), (-3, 8.0),
    ]
    brachioradialis_l_pts = [
        (1, 0.5), (13, 1.2), (27, 2.2), (25, 6.2), (13, 7.8), (1, 6.2),
    ]
    hand_l_pts = [
        (FA_L_LEN - 5, -6.0), (FA_L_LEN + 5, -5.8), (FA_L_LEN + 7, 0.0),
        (FA_L_LEN + 5, 6.0), (FA_L_LEN - 5, 5.8),
    ]
    stopper_paint = skin_fill_outlined("StopperL", -4, 4, PAD_DARK, line=1.0, stroke_col="FF475569")

    return "\n".join([
        f'{ind}<Node name="NearLeftArmGroup">',

        # 1. Left Upper Arm & Integrated Left Deltoid Cap (drawn in front of the left forearm since shoulder/elbow are closer to viewer)
        f'{i2}<Node x="{f(p0["l_sh"][0])}" y="{f(p0["l_sh"][1])}" '
        f'rotation="{f(p0["ua_l_ang"])}" scaleX="{f(p0["ua_l_sc"])}" name="NearLeftUpperArm" id="{ua_id}">',
        # Posterior deltoid (scale = 1.00) & Lateral deltoid (scale = 0.95)
        stroke_shape(i3, "PostDeltLFiber1", [(-3, -5.5), (14, -4.5)], 1.0, "667F1D1D", 0.3),
        stroke_shape(i3, "PostDeltLFiber2", [(-3, -2.2), (14, -1.8)], 1.0, "667F1D1D", 0.3),
        smooth_shape(i3, "PosteriorDeltoidL", post_delt_l_pts, muscle_paint("PostDeltL", scale=1.00, line=1.05)),
        stroke_shape(i3, "LatDeltLFiber", [(-2, 5.5), (13, 5.0)], 0.95, "667F1D1D", 0.3),
        smooth_shape(i3, "LateralDeltoidL", lat_delt_l_pts, muscle_paint("LatDeltL", scale=0.95, line=1.0)),
        smooth_shape(i3, "LeftDeltoidBase", delt_l_pts, skin_fill_outlined("LeftDeltBase", -11, 11, SKIN, line=1.1)),
        # Brachialis (scale = 0.86) + Biceps/Triceps contour
        stroke_shape(i3, "BrachialisLFiber", [(20, -1.2), (33, -1.0)], 0.95, "667F1D1D", 0.3),
        smooth_shape(i3, "BrachialisL", brachialis_l_pts, muscle_paint("BrachialisL", scale=0.86, line=0.95)),
        stroke_shape(i3, "LeftBicepsCrease", [(18, 4.8), (35, 4.2)], 1.2, ANATOMY_LINE, 0.2),
        stroke_shape(i3, "LeftTricepsCrease", [(18, -5.8), (35, -4.8)], 1.2, ANATOMY_LINE, 0.2),
        stroke_shape(i3, "LeftUpperArmHi", [(16, 6.8), (35, 5.5)], 2.4, HIGHLIGHT, 2.4),
        smooth_shape(i3, "LeftUpperArmShape", ua_l_pts, skin_fill_outlined("LeftUpperArm", -11, 11, SKIN, line=1.15)),
        f"{i2}</Node>",

        # 2. Left Forearm, Brachioradialis (scale = 0.88), Gripping Left Hand & Black Rope Stopper
        f'{i2}<Node x="{f(p0["l_el"][0])}" y="{f(p0["l_el"][1])}" '
        f'rotation="{f(p0["fa_l_ang"])}" scaleX="{f(p0["fa_l_sc"])}" name="NearLeftForearm" id="{fa_id}">',
        ellipse_shape(i3, "LeftRopeStopper", FA_L_LEN + 3.5, 4.2, 9.0, 9.0, stopper_paint),
        stroke_shape(i3, "LeftKnuckle1", [(FA_L_LEN - 2, -2.8), (FA_L_LEN + 4, -2.8)], 0.95, ANATOMY_LINE, 0.0),
        stroke_shape(i3, "LeftKnuckle2", [(FA_L_LEN - 2, 1.5), (FA_L_LEN + 4, 1.5)], 0.95, ANATOMY_LINE, 0.0),
        smooth_shape(i3, "LeftGrippingHand", hand_l_pts, skin_fill_outlined("LeftHand", -6, 6, SKIN, line=1.1)),
        stroke_shape(i3, "BrachioradialisLFiber", [(4, 3.8), (22, 4.2)], 0.95, "667F1D1D", 0.3),
        smooth_shape(i3, "BrachioradialisL", brachioradialis_l_pts, muscle_paint("BrachioradialisL", scale=0.88, line=0.95)),
        stroke_shape(i3, "LeftForearmExtensorLine", [(5, -2.8), (FA_L_LEN - 8, -2.2)], 1.2, ANATOMY_LINE, 0.2),
        stroke_shape(i3, "LeftForearmHi", [(5, -4.8), (FA_L_LEN - 8, -3.8)], 2.4, HIGHLIGHT, 2.4),
        smooth_shape(i3, "LeftForearmShape", fa_l_pts, skin_fill_outlined("LeftForearm", -9, 9, SKIN, line=1.15)),
        f"{i2}</Node>",

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 6. Scene Assembly (RML First Child = Topmost Layer)
def build_rml():
    global _id
    _id = 0
    KEYED.clear()

    machine_xml = high_cable_pulley_machine()
    cable_rope_xml = cable_and_dual_rope()
    right_arm_xml = far_right_arm()
    body_xml = stationary_athlete_body()
    left_arm_xml = near_left_arm()

    grouped = {}
    for oid, kxml in KEYED:
        grouped.setdefault(oid, []).append(kxml)
    keyed_objects_xml = "\n".join(
        f'        <KeyedObject objectId="{oid}">\n' + "\n".join(props) + "\n        </KeyedObject>"
        for oid, props in grouped.items()
    )

    # Layer order from front (first child) to back (last child):
    #   1. NearLeftArmGroup (foreground left deltoid, upper arm, forearm, hand & rope stopper)
    #   2. AthleteBodyTorsoHeadAndLegs (stationary 3/4 rear-left head, V-tapered back, glutes/shorts & planted legs)
    #   3. FarRightArmGroup (right deltoid, right upper arm with Brachialis, right forearm with Brachioradialis & right hand)
    #   4. CableAndDualRopeGroup (taut steel cable & V-shaped dual braided rope strands)
    #   5. HighCablePulleyMachine (high pulley tower, guide rods, lifting weight stack & overhead boom)
    #   6. FloorShadow, FloorLine & Backdrop
    return f"""<Rive version="7.3">
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="FacePull" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Left) Arm, Left Deltoid Cap & Left Rope Stopper -->
{left_arm_xml}

        <!-- 2. Mid-Foreground: Stationary 3/4 Rear-Left Athlete Body (Head, Back, Shorts & Legs) -->
{body_xml}

        <!-- 3. Midground Right: Far (Right) Arm, Right Deltoid Cap & Right Rope Stopper -->
{right_arm_xml}

        <!-- 4. Mid-Background: Taut Working Cable & Dual Braided Rope Attachment -->
{cable_rope_xml}

        <!-- 5. Background Equipment: High Cable Pulley Tower & Animated Weight Stack -->
{machine_xml}

        <!-- 6. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="268" y="{f(FLOOR - 4.0)}" name="FloorShadow">
            <Ellipse width="340" height="22" name="ShadowEllipse"/>
            <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="170" endY="0" name="ShadowGrad">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="FacePull" id="0:60">
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
    riv_out = HERE / "face_pull.riv"
    riv_out.write_bytes(riv_bytes)

    repo = HERE.parent.parent
    riv_dest = repo / "assets/animations/face_pull.riv"
    thumb_dest = repo / "assets/animations/thumbnails/face_pull.png"
    riv_dest.write_bytes(riv_bytes)

    legacy_mk = repo / "assets/animations/face_pull.movekit"
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
