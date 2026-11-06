#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive 7.3 scene for Seated Leg Curl (id: 'leg_curl').

Uses our canonical 3/4 front-left CommunityFitness mannequin (volumetric 3/4 head with hair/ear/brow/eye/mouth,
muscular neck, sculpted pectorals, 6-pack abs, biceps/forearms gripping the lap-pad handles, dark athletic
compression shorts, sculpted quadriceps, and bare feet) seated in a commercial Seated Leg Curl Machine.

Matches the 2-panel 3/4 front-left Seated Leg Curl Machine reference illustration:
  - Left Panel (f = 0 & f = 160, r = 0.0):
    * Athlete sits braced against the angled black backrest and seat pad, hands gripping the dual vertical
      handles on the thigh hold-down assembly while the upper thighs are locked under the lap pad.
    * Both lower legs are extended forward-left resting atop the black cylindrical ankle roller pad.
  - Right Panel (f = 72, r = 1.0):
    * Both knees flex through a smooth ~72 deg arc downward and backward, driving the ankle roller pad
      beneath the knees while the weight stack rises inside the rear shrouded tower.
  - Labeled/Highlighted Target Muscle Groups (pulsing from warm orange #FFF97316 to intense crimson #FFF43F5E):
    1. Hamstrings (Primary — Biceps femoris, Semitendinosus, Semimembranosus along the posterior/underside
       of both thighs)
    2. Gastrocnemius (Secondary — Medial and lateral calf heads on the lower legs)
    3. Gracilis / Sartorius medial knee-flexor insertion (Secondary — medial aspect of the knee/upper leg)

Run:
    python3 gen_leg_curl.py            # writes scene.rml
    python3 gen_leg_curl.py --publish  # compiles assets/animations/leg_curl.riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/leg_curl.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/leg_curl.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps loop
STEP = 2

# Canonical Seated Knee Pivot Anchors & Lower-Leg Lengths (3/4 front-left view)
KNEE_FAR = (254.0, 166.0)   # Right (far / screen-left) knee hinge
KNEE_NEAR = (278.0, 174.0)  # Left (near / screen-right) knee hinge
SHIN_LEN_FAR = 78.0
SHIN_LEN_NEAR = 82.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
FRAME_SILVER = ("FFE2E8F0", "FF94A3B8", "FF475569")
FRAME_DARK = ("FF475569", "FF1E293B", "FF0F172A")
PAD_DARK = ("FF334155", "FF182232", "FF090D16")
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
EASE_RETURN = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def curl_progress(frame):
    """Returns seated leg-curl progress r in [0.0, 1.0] across 160 frames:
    - 0..12:   Extended hold (r = 0.0: legs extended forward-left on ankle roller)
    - 12..64:  Concentric hamstring curl (r: 0.0 -> 1.0: lower legs curl down/back)
    - 64..84:  Peak hamstring contraction hold at bottom (r = 1.0)
    - 84..148: Controlled eccentric extension (r: 1.0 -> 0.0)
    - 148..160: Extended hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 64:
        return EASE_CURL((fr - 12) / 52.0)
    if fr <= 84:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_RETURN((fr - 84) / 64.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def pose(r):
    """Compute Seated Leg Curl transforms at progress r in [0.0, 1.0] using true circular knee flexion."""
    # In screen coordinates (0 rad = +X right, pi rad = -X left, pi/2 rad = +Y down):
    # - Extended (r = 0.0): lower legs point forward-left (~164 deg = 2.86 rad, slight downward slope)
    # - Curled (r = 1.0):   lower legs flex downward-left (~108 deg = 1.88 rad, ~56 deg screen projection of 75 deg 3D curl)
    ang_near = math.radians(lerp(163.0, 108.0, r))
    ang_far = math.radians(lerp(164.0, 110.0, r))

    ankle_near = (
        KNEE_NEAR[0] + SHIN_LEN_NEAR * math.cos(ang_near),
        KNEE_NEAR[1] + SHIN_LEN_NEAR * math.sin(ang_near),
    )
    ankle_far = (
        KNEE_FAR[0] + SHIN_LEN_FAR * math.cos(ang_far),
        KNEE_FAR[1] + SHIN_LEN_FAR * math.sin(ang_far),
    )

    # Cylindrical Ankle Roller Pad tucked directly behind/under the distal shins/Achilles tendons:
    # Offset perpendicular-downward from the shin angle so the shins rest right on top of the roller
    perp_near = ang_near - math.radians(90.0)
    roller_near = (
        KNEE_NEAR[0] + (SHIN_LEN_NEAR - 10.0) * math.cos(ang_near) + 12.5 * math.cos(perp_near),
        KNEE_NEAR[1] + (SHIN_LEN_NEAR - 10.0) * math.sin(ang_near) + 12.5 * math.sin(perp_near),
    )
    roller_far = (
        roller_near[0] - 24.0,
        roller_near[1] - 10.0,
    )

    # Weight stack rises inside the rear tower as the legs curl down
    stack_dy = lerp(0.0, -28.0, r)

    return {
        "r": r,
        "ang_near": ang_near,
        "ang_far": ang_far,
        "ankle_near": ankle_near,
        "ankle_far": ankle_far,
        "roller_near": roller_near,
        "roller_far": roller_far,
        "stack_dy": stack_dy,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(curl_progress(fr)) for fr in FRAMES}


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


def polyline_stroke_shape(indent, name, pts, width, color, radius=0.5, cap="round"):
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


# ---------------------------------------------------------------- 1. Background Weight Stack Tower & Base Frame
def machine_background_tower():
    """Shrouded weight stack tower in background-left, animated active weight plates, and lower base frame."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    tower_paint = (
        f'<Fill name="TowerFill">{grad3("TowerGrad", 40, 275, "FFCBD5E1", "FF94A3B8", "FF475569", x0=235, x1=325)}</Fill>'
        '<Stroke thickness="1.2" join="round" name="TowerStroke"><SolidColor colorValue="FF334155" name="TowerStrokeCol"/></Stroke>'
    )
    tower_inner_paint = (
        f'<Fill name="TowerInnerFill">{grad("TowerInnerGrad", 245, 50, 315, 265, "FF1E293B", "FF0F172A")}</Fill>'
        '<Stroke thickness="1.0" join="round" name="TowerInnerStroke"><SolidColor colorValue="FF334155" name="TowerInnerStrokeCol"/></Stroke>'
    )
    frame_paint = (
        f'<Fill name="FrameFill">{grad3("FrameGrad", 180, 298, *FRAME_SILVER, x0=210, x1=410)}</Fill>'
        '<Stroke thickness="1.15" join="round" name="FrameStroke"><SolidColor colorValue="FF334155" name="FrameStrokeCol"/></Stroke>'
    )
    stack_paint = (
        '<Fill name="StackFill"><SolidColor colorValue="FF0F172A" name="StackCol"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="StackStroke"><SolidColor colorValue="FF334155" name="StackStrokeCol"/></Stroke>'
    )

    stack_id = nid()
    key_double(stack_id, 14, lambda p: p["stack_dy"])

    out = [f'{ind}<Node name="MachineBackgroundTower">']

    # Note: In Rive RML, earlier children in a <Node> render ON TOP of later children.
    # Layer A (Foreground of Machine): Upholstered Seat Pad, Backrest Pad & Lower Support Frame
    backrest_paint = (
        f'<Fill name="BackrestFill">{grad3("BackrestGrad", 104, 198, *PAD_DARK, x0=336, x1=402)}</Fill>'
        '<Stroke thickness="1.2" join="round" name="BackrestStroke"><SolidColor colorValue="FF475569" name="BackrestStrokeCol"/></Stroke>'
    )
    seat_paint = (
        f'<Fill name="SeatFill">{grad3("SeatGrad", 178, 214, *PAD_DARK, x0=260, x1=372)}</Fill>'
        '<Stroke thickness="1.2" join="round" name="SeatStroke"><SolidColor colorValue="FF475569" name="SeatStrokeCol"/></Stroke>'
    )
    out.append(
        poly_shape(
            i2,
            "SeatPad",
            [(260, 182), (364, 190), (370, 210), (256, 200)],
            seat_paint,
            radius=4.0,
        )
    )
    out.append(
        poly_shape(
            i2,
            "BackrestPad",
            [(364, 104), (402, 112), (366, 194), (332, 186)],
            backrest_paint,
            radius=4.5,
        )
    )

    # Floor Base Skids & Support Pillars under Seat
    out.append(poly_shape(i2, "FootPadFront", [(256, 294), (274, 294), (276, 300), (254, 300)], solid("Foot1", "FF090D16"), radius=1.0))
    out.append(poly_shape(i2, "FootPadLeft", [(204, 266), (220, 266), (222, 272), (202, 272)], solid("Foot2", "FF090D16"), radius=1.0))
    out.append(poly_shape(i2, "FootPadRear", [(384, 272), (402, 272), (404, 278), (382, 278)], solid("Foot3", "FF090D16"), radius=1.0))
    out.append(poly_shape(i2, "BaseRunnerMain", [(258, 286), (396, 268), (400, 276), (262, 296)], frame_paint, radius=2.0))
    out.append(poly_shape(i2, "BaseCrossBar", [(210, 260), (272, 284), (268, 294), (206, 268)], frame_paint, radius=2.0))
    out.append(poly_shape(i2, "RearSeatStrut", [(354, 206), (366, 206), (392, 272), (380, 272)], frame_paint, radius=2.0))
    out.append(poly_shape(i2, "FrontSeatPillar", [(284, 196), (300, 196), (282, 288), (266, 288)], frame_paint, radius=2.0))

    # Layer B (Midground inside Tower): Placard, Animated Active Weight Stack, Rest Plates & Guide Rods
    out.append(poly_shape(i2, "PlacardPanel", [(258, 76), (298, 74), (298, 96), (258, 98)], frame_paint, radius=2.0))

    # Animated Active Weight Stack Block (rises as r: 0 -> 1)
    out.append(f'{i2}<Node y="{f(POSES[0]["stack_dy"])}" name="ActiveWeightStack" id="{stack_id}">')
    out.append(ellipse_shape(i3, "SelectorPin", 278.0, 184.0, 4.5, 4.5, solid("Pin", "FFF97316")))
    for idx in range(5):
        y_top = 156 + idx * 7
        out.append(poly_shape(i3, f"ActivePlate{idx + 1}", [(252, y_top), (302, y_top - 2), (302, y_top + 4), (252, y_top + 6)], stack_paint, radius=1.0))
    out.append(f"{i2}</Node>")

    # Resting Bottom Weight Stack Plates
    for idx in range(5):
        y_top = 212 + idx * 7
        out.append(poly_shape(i2, f"RestPlate{idx + 1}", [(252, y_top), (302, y_top - 2), (302, y_top + 4), (252, y_top + 6)], stack_paint, radius=1.0))

    # Guide Rods & Top Lift Cable
    out.append(polyline_stroke_shape(i2, "LiftCable", [(278, 54), (278, 185)], 1.8, "FFCBD5E1"))
    out.append(polyline_stroke_shape(i2, "GuideRod1", [(264, 56), (264, 250)], 2.2, "FF94A3B8"))
    out.append(polyline_stroke_shape(i2, "GuideRod2", [(292, 54), (292, 248)], 2.2, "FF94A3B8"))

    # Layer C (Background of Tower): Recessed Dark Cavity & Outer Silver Shroud Arch
    out.append(
        poly_shape(
            i2,
            "TowerRecess",
            [(248, 56), (308, 52), (308, 254), (248, 258)],
            tower_inner_paint,
            radius=3.0,
        )
    )
    out.append(
        smooth_shape(
            i2,
            "TowerOuterArch",
            [
                (238, 264), (238, 60), (246, 46), (294, 42),
                (316, 52), (322, 72), (322, 258), (238, 264),
            ],
            tower_paint,
        )
    )

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 2. Dynamic Lower Legs & Pivoting Ankle Roller Assembly
def lower_leg_rig(prefix, far):
    """Pivoting lower leg (KNEE -> ANKLE -> BARE FOOT) with sculpted Tibialis, Gastrocnemius (Secondary),
    and Medial Knee Flexor / Sartorius insertion."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    kx, ky = KNEE_FAR if far else KNEE_NEAR
    ang_k = "ang_far" if far else "ang_near"
    shin_len = SHIN_LEN_FAR if far else SHIN_LEN_NEAR

    leg_id = nid()
    key_double(leg_id, 15, lambda p: p[ang_k])

    p0 = POSES[0]

    # Secondary Target Muscle: Gastrocnemius (calf muscle belly) & Medial Knee Flexor insertion
    def calf_t(p):
        return 0.40 + 0.54 * (p["r"] ** 0.80)

    def med_flex_t(p):
        return 0.36 + 0.50 * (p["r"] ** 0.82)

    # Local coordinates along the shin axis (0,0 = KNEE, +X = toward ANKLE at shin_len):
    # Note: Since ang ~ 163 deg (pointing screen-left) -> 108 deg (pointing screen-down),
    # local +Y is on the UPPER/ANTERIOR shin surface, and local -Y is on the LOWER/POSTERIOR calf surface!
    shin_pts = [
        (-8.0, 0.0), (4.0, 9.5), (26.0, 8.8), (52.0, 6.2),
        (shin_len - 4.0, 4.5), (shin_len + 2.0, 0.0), (shin_len - 4.0, -4.8),
        (54.0, -6.5), (30.0, -13.5), (10.0, -11.5), (-6.0, -6.5),
    ]
    # Gastrocnemius belly on the posterior/medial side of the lower leg (prominently highlighted in reference)
    if far:
        gastroc_pts = [
            (10.0, -1.5), (26.0, 3.2), (46.0, 1.5),
            (50.0, -5.5), (30.0, -13.2), (12.0, -10.5),
        ]
        med_flex_pts = [
            (-4.0, 1.5), (12.0, 7.5), (22.0, 5.5), (8.0, -1.0),
        ]
    else:
        gastroc_pts = [
            (10.0, -3.5), (28.0, -1.5), (48.0, -3.5),
            (52.0, -6.5), (30.0, -13.5), (12.0, -11.2),
        ]
        med_flex_pts = [
            (-3.0, -2.0), (12.0, 2.5), (20.0, 0.5), (8.0, -5.5),
        ]

    # Bare foot at (shin_len, 0) dorsiflexed upward (+Y local = anterior/dorsal side of shin)
    foot_pts = [
        (shin_len - 4.0, -5.5), (shin_len + 6.0, -6.2), (shin_len + 13.0, 2.0),
        (shin_len + 18.0, 18.5), (shin_len + 13.5, 22.5), (shin_len + 5.0, 16.0),
        (shin_len - 3.0, 5.0),
    ]

    out = [
        f'{ind}<Node x="{f(kx)}" y="{f(ky)}" rotation="{f(p0[ang_k])}" name="{prefix}LowerLeg" id="{leg_id}">'
    ]
    # 1. Bare Foot & Toes
    out.append(stroke_shape(i2, f"{prefix}FootArchLine", [(shin_len + 2.0, -2.0), (shin_len + 11.0, 8.0), (shin_len + 15.0, 17.5)], 1.1, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i2, f"{prefix}FootHi", [(shin_len + 1.0, 4.0), (shin_len + 11.0, 14.5)], 2.0, HIGHLIGHT, 2.0))
    out.append(smooth_shape(i2, f"{prefix}BareFoot", foot_pts, skin_fill(prefix + "Foot", -6, 22, skin)))

    # 2. Highlighted Gastrocnemius & Medial Knee-Flexor Band + Anterior Tibialis Definition
    out.append(stroke_shape(i2, f"{prefix}CalfSplitLine", [(16.0, -5.5), (32.0, -7.5), (46.0, -4.5)], 1.05, "737F1D1D", 0.3))
    out.append(smooth_shape(i2, f"{prefix}Gastrocnemius", gastroc_pts, muscle_paint_fn(prefix + "Gastroc", calf_t, 1.0)))
    out.append(smooth_shape(i2, f"{prefix}MedialKneeFlexor", med_flex_pts, muscle_paint_fn(prefix + "MedFlex", med_flex_t, 0.9)))

    # 3. Shin / Tibia Base Contour & Highlights
    out.append(stroke_shape(i2, f"{prefix}TibiaCrestLine", [(8.0, 4.5), (34.0, 4.2), (62.0, 2.5)], 1.2, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i2, f"{prefix}ShinHi", [(10.0, 6.5), (36.0, 5.8), (64.0, 3.5)], 2.6, HIGHLIGHT, 2.8))
    out.append(stroke_shape(i2, f"{prefix}ShinSh", [(12.0, -9.5), (34.0, -11.5), (58.0, -5.0)], 3.2, CORE_SHADOW, 3.2))
    out.append(smooth_shape(i2, f"{prefix}ShinShape", shin_pts, skin_fill(prefix + "Shin", -13, 10, skin)))
    out.append(f"{ind}</Node>")
    return "\n".join(out)


def ankle_roller_assembly():
    """Pivoting machine lever arm and 3D black cylindrical Achilles/ankle roller pad beneath the ankles."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    lever_id, pad_id = nid(), nid()
    key_double(lever_id, 15, lambda p: p["ang_near"])
    key_double(pad_id, 13, lambda p: p["roller_near"][0])
    key_double(pad_id, 14, lambda p: p["roller_near"][1])

    p0 = POSES[0]
    frame_paint = (
        f'<Fill name="LeverFill">{grad3("LeverGrad", -6, 6, *FRAME_SILVER)}</Fill>'
        '<Stroke thickness="1.1" join="round" name="LeverStroke"><SolidColor colorValue="FF334155" name="LeverStrokeCol"/></Stroke>'
    )
    pad_body_paint = (
        f'<Fill name="RollerBodyFill">{grad("RollerBodyGrad", -28, -14, 10, 14, "FF334155", "FF090D16")}</Fill>'
        '<Stroke thickness="1.2" join="round" name="RollerBodyStroke"><SolidColor colorValue="FF1E293B" name="RollerBodyStrokeCol"/></Stroke>'
    )
    cap_paint = (
        f'<Fill name="RollerCapFill">{grad("RollerCapGrad", -8, -10, 8, 10, "FFF1F5F9", "FF94A3B8")}</Fill>'
        '<Stroke thickness="1.5" name="RollerCapStroke"><SolidColor colorValue="FF0F172A" name="RollerCapStrokeCol"/></Stroke>'
    )

    out = [f'{ind}<Node name="AnkleRollerAssembly">']

    # 1. Pivoting Swing Arm behind far leg
    out.append(
        f'{i2}<Node x="{f(KNEE_FAR[0] - 8.0)}" y="{f(KNEE_FAR[1] + 6.0)}" rotation="{f(p0["ang_near"])}" name="RollerSwingArm" id="{lever_id}">'
    )
    out.append(poly_shape(i3, "SwingArmBeam", [(-6, -4.5), (68, -4.0), (68, 4.0), (-6, 4.5)], frame_paint, radius=2.0))
    out.append(ellipse_shape(i3, "SwingPivotHub", 0.0, 0.0, 14.0, 14.0, frame_paint))
    out.append(f"{i2}</Node>")

    # 2. 3D Black Cylindrical Ankle Roller Pad (spanning from roller_far to roller_near with silver bolted end-cap)
    out.append(
        f'{i2}<Node x="{f(p0["roller_near"][0])}" y="{f(p0["roller_near"][1])}" name="AnkleRollerPad" id="{pad_id}">'
    )
    # Near silver circular end-cap with perimeter bolt dots (drawn in front of the cylinder body)
    for b_ang in range(0, 360, 45):
        bx = 6.2 * math.cos(math.radians(b_ang))
        by = 8.2 * math.sin(math.radians(b_ang))
        out.append(ellipse_shape(i3, f"CapBolt{b_ang}", bx, by, 1.8, 1.8, solid(f"Bolt{b_ang}", "FF1E293B")))
    out.append(ellipse_shape(i3, "RollerEndCap", 0.0, 0.0, 17.5, 22.5, cap_paint, rot_deg=-12.0))
    # Cylindrical black foam body extending from (0, 0) back-left to (-28, -12)
    out.append(
        smooth_shape(
            i3,
            "RollerCylinderBody",
            [
                (2.0, -11.0), (-26.0, -22.0), (-34.0, -12.0),
                (-28.0, 0.0), (-2.0, 11.2), (6.5, 0.0),
            ],
            pad_body_paint,
        )
    )
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. Seated Thighs (with Primary Hamstrings), Torso, Head & Arms
def seated_thighs_and_hamstrings():
    """Seated Far and Near Thighs with Primary Target Muscle: Hamstrings (Biceps femoris, Semitendinosus,
    Semimembranosus) glowing along the posterior/underside of both thighs."""
    ind = "        "
    i2 = ind + "    "

    def ham_t(p):
        return 0.44 + 0.56 * (p["r"] ** 0.76)

    # Near (Left) Thigh from Hip (332, 184) to KNEE_NEAR (278, 174):
    near_thigh_pts = [
        (270.0, 162.0), (298.0, 154.0), (330.0, 160.0),
        (338.0, 182.0), (318.0, 194.0), (282.0, 182.0), (268.0, 174.0),
    ]
    # Primary Target Muscle: Near Hamstring belly along the underside of the left thigh
    near_ham_pts = [
        (274.0, 171.0), (302.0, 172.0), (324.0, 179.0),
        (318.0, 193.5), (294.0, 188.0), (274.0, 178.0),
    ]

    # Far (Right) Thigh from Hip (310, 174) to KNEE_FAR (254, 166):
    far_thigh_pts = [
        (246.0, 154.0), (274.0, 146.0), (308.0, 152.0),
        (314.0, 172.0), (294.0, 182.0), (258.0, 174.0), (244.0, 166.0),
    ]
    far_ham_pts = [
        (250.0, 163.0), (278.0, 164.0), (298.0, 170.0),
        (292.0, 181.5), (268.0, 177.0), (250.0, 170.0),
    ]

    pelvis_shorts = [
        (308.0, 152.0), (336.0, 156.0), (358.0, 164.0),
        (352.0, 194.0), (322.0, 196.0), (304.0, 180.0),
    ]

    out = [f'{ind}<Node name="SeatedThighsAndShorts">']

    # 1. Dark Athletic Compression Shorts on Seat
    out.append(stroke_shape(i2, "ShortsLegHem", [(318.0, 160.0), (324.0, 178.0), (316.0, 194.0)], 1.6, "660F172A", 0.8))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill("Shorts", 152, 196, SHORTS, x0=304, x1=358)))

    # 2. Near (Left) Thigh & Activated Hamstrings (Biceps Femoris + Semitendinosus)
    out.append(stroke_shape(i2, "NearHamFiber1", [(280.0, 175.0), (298.0, 181.0), (316.0, 186.0)], 1.1, "807F1D1D", 0.3))
    out.append(stroke_shape(i2, "NearHamFiber2", [(284.0, 179.0), (302.0, 185.0), (314.0, 190.0)], 1.0, "667F1D1D", 0.3))
    out.append(smooth_shape(i2, "NearHamstrings", near_ham_pts, muscle_paint_fn("NearHam", ham_t, 1.1)))
    out.append(stroke_shape(i2, "NearQuadSweep", [(278.0, 165.0), (304.0, 164.0), (326.0, 170.0)], 1.25, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i2, "NearThighHi", [(278.0, 160.0), (304.0, 158.0), (326.0, 164.0)], 3.0, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i2, "NearThigh", near_thigh_pts, skin_fill("NearThigh", 154, 194, SKIN)))

    # 3. Far (Right) Thigh & Activated Hamstrings
    out.append(smooth_shape(i2, "FarHamstrings", far_ham_pts, muscle_paint_fn("FarHam", ham_t, 1.0)))
    out.append(stroke_shape(i2, "FarThighHi", [(256.0, 152.0), (280.0, 150.0), (302.0, 156.0)], 2.4, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i2, "FarThigh", far_thigh_pts, skin_fill("FarThigh", 146, 182, SKIN_FAR)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def thigh_hold_down_and_handles():
    """Pivoted silver hold-down bar, black cushioned thigh lap pad over the lower quads, and dual grip handles."""
    ind = "        "
    i2 = ind + "    "

    frame_paint = (
        f'<Fill name="LapArmFill">{grad3("LapArmGrad", 118, 164, *FRAME_SILVER, x0=216, x1=310)}</Fill>'
        '<Stroke thickness="1.15" join="round" name="LapArmStroke"><SolidColor colorValue="FF334155" name="LapArmStrokeCol"/></Stroke>'
    )
    pad_paint = (
        f'<Fill name="LapPadFill">{grad3("LapPadGrad", 146, 170, *PAD_DARK, x0=248, x1=300)}</Fill>'
        '<Stroke thickness="1.15" join="round" name="LapPadStroke"><SolidColor colorValue="FF475569" name="LapPadStrokeCol"/></Stroke>'
    )
    grip_paint = (
        '<Fill name="GripFill"><SolidColor colorValue="FF090D16" name="GripCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="GripStroke"><SolidColor colorValue="FF334155" name="GripStrokeCol"/></Stroke>'
    )

    out = [f'{ind}<Node name="ThighHoldDownAssembly">']
    # Vertical grip handles (Near left handle at x=292, Far right handle at x=260)
    out.append(poly_shape(i2, "NearGripHandle", [(289, 124), (295, 124), (295, 152), (289, 152)], grip_paint, radius=2.0))
    out.append(poly_shape(i2, "FarGripHandle", [(257, 114), (263, 114), (263, 138), (257, 138)], grip_paint, radius=2.0))

    # Silver hold-down support arm & shield plate (matching reference machine)
    out.append(
        poly_shape(
            i2,
            "HoldDownBracket",
            [(224, 122), (306, 146), (302, 158), (220, 134)],
            frame_paint,
            radius=2.5,
        )
    )
    # Black cushioned thigh hold-down roller/pad resting snug across the distal thighs
    out.append(
        smooth_shape(
            i2,
            "ThighHoldDownPad",
            [
                (250, 146), (298, 154), (302, 166),
                (290, 172), (248, 162), (246, 152),
            ],
            pad_paint,
        )
    )
    out.append(f"{ind}</Node>")
    return "\n".join(out)


def seated_torso_head_and_arms():
    """Canonical 3/4 front-left CommunityFitness upper body seated against the backrest pad,
    with sculpted pectorals, 6-pack abs, deltoids, biceps, and forearms gripping the dual handles."""
    ind = "        "
    i2 = ind + "    "

    # Volumetric 3/4 Head looking forward-left at the movement
    head_pts = [
        (338.0, 56.0), (335.0, 62.5), (333.5, 68.5), (334.8, 73.5),
        (335.5, 79.5), (341.5, 82.5), (351.0, 81.0), (358.0, 77.0),
        (363.0, 69.0), (362.5, 58.0), (355.5, 51.0), (345.0, 51.0),
    ]
    hair_pts = [
        (337.5, 58.0), (343.0, 50.5), (355.0, 50.2), (363.0, 56.5),
        (363.5, 67.5), (359.0, 71.5), (357.5, 63.5), (352.0, 58.5),
        (344.5, 57.0),
    ]
    neck_pts = [
        (340.5, 79.0), (357.0, 76.0), (366.0, 92.0),
        (368.0, 100.0), (328.0, 96.0), (337.0, 88.0),
    ]

    # Seated reclined torso (~15 deg recline against backrest)
    torso_pts = [
        (324.0, 94.0), (346.0, 92.0), (376.0, 98.0),
        (376.0, 120.0), (366.0, 142.0), (356.0, 164.0),
        (334.0, 168.0), (312.0, 156.0), (318.0, 134.0), (320.0, 112.0),
    ]
    pec_near_pts = [
        (342.0, 97.0), (368.0, 100.0), (372.0, 114.0),
        (364.0, 125.0), (350.0, 126.0), (339.0, 121.0),
    ]
    pec_far_pts = [
        (324.0, 96.0), (341.0, 96.5), (338.0, 120.5),
        (327.0, 121.5), (320.0, 114.0), (321.0, 103.0),
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
        [(338.0, 124.0), (350.0, 125.0), (348.5, 133.5), (336.5, 132.5)],
        [(336.0, 135.0), (348.0, 136.0), (346.0, 144.5), (334.5, 143.5)],
        [(334.0, 146.0), (345.5, 147.0), (343.5, 155.5), (332.5, 154.5)],
        [(326.0, 123.0), (336.0, 123.8), (334.5, 132.0), (324.5, 131.0)],
        [(324.0, 134.0), (334.0, 134.8), (332.5, 143.0), (322.5, 142.0)],
        [(322.0, 145.0), (332.0, 145.8), (330.5, 154.0), (320.5, 153.0)],
    ]

    # Near (Left) Arm reaching forward-left to grip NearGripHandle at (292, 138)
    near_delt_pts = [
        (358.0, 98.0), (372.0, 96.0), (382.0, 105.0),
        (378.0, 119.0), (364.0, 123.0), (356.0, 112.0),
    ]
    near_ua_pts = [
        (364.0, 108.0), (376.0, 114.0), (354.0, 144.0),
        (340.0, 142.0), (344.0, 128.0),
    ]
    near_fa_pts = [
        (346.0, 134.0), (348.0, 145.0), (298.0, 144.0),
        (292.0, 135.0), (318.0, 131.0),
    ]
    near_hand_pts = [
        (286.0, 132.0), (298.0, 132.0), (299.0, 145.0), (286.0, 145.0),
    ]

    # Far (Right) Arm reaching forward-left to grip FarGripHandle at (260, 126)
    far_ua_pts = [
        (322.0, 98.0), (332.0, 104.0), (308.0, 130.0),
        (296.0, 126.0), (306.0, 110.0),
    ]
    far_fa_pts = [
        (304.0, 120.0), (304.0, 130.0), (264.0, 131.0),
        (260.0, 122.0), (284.0, 119.0),
    ]
    far_hand_pts = [
        (254.0, 119.0), (266.0, 119.0), (266.0, 131.0), (254.0, 131.0),
    ]

    out = [f'{ind}<Node name="SeatedUpperBody">']

    # 1. Near (Left) Arm & Hand (in front of torso)
    out.append(stroke_shape(i2, "NearKnuckle1", [(288.0, 136.0), (296.0, 136.0)], 1.0, SOFT_SHADOW, 0.0))
    out.append(stroke_shape(i2, "NearKnuckle2", [(288.0, 140.0), (296.0, 140.0)], 1.0, SOFT_SHADOW, 0.0))
    out.append(smooth_shape(i2, "NearHand", near_hand_pts, skin_fill("NearHand", 132, 145, SKIN)))
    out.append(stroke_shape(i2, "NearForearmHi", [(304.0, 134.0), (324.0, 134.0), (342.0, 136.0)], 2.2, HIGHLIGHT, 2.4))
    out.append(smooth_shape(i2, "NearForearm", near_fa_pts, skin_fill("NearFA", 131, 145, SKIN)))
    out.append(stroke_shape(i2, "NearBicepsPeak", [(348.0, 122.0), (356.0, 114.0), (364.0, 110.0)], 2.2, HIGHLIGHT, 2.4))
    out.append(smooth_shape(i2, "NearUpperArm", near_ua_pts, skin_fill("NearUA", 108, 144, SKIN)))
    out.append(stroke_shape(i2, "NearDeltHi", [(364.0, 101.0), (374.0, 106.0), (370.0, 116.0)], 2.4, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i2, "NearDeltoid", near_delt_pts, skin_fill("NearDelt", 96, 123, SKIN)))

    # 2. Volumetric 3/4 Head & Muscular Neck
    out.append(smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 338, 50, 363, 71, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i2, "Ear", 356.0, 70.5, 5.5, 8.5, solid("Ear", "FFA3B1C4"), rot_deg=12.0))
    out.append(stroke_shape(i2, "BrowShade", [(335.0, 62.8), (339.5, 63.2)], 1.4, "590F172A", 0.8))
    out.append(stroke_shape(i2, "EyeLine", [(336.8, 64.6), (339.8, 64.8)], 1.1, "730F172A", 0.4))
    out.append(stroke_shape(i2, "MouthLine", [(335.0, 74.5), (338.5, 74.8)], 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i2, "HeadHi", [(338.5, 60.0), (342.5, 55.0), (351.0, 54.0)], 3.0, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i2, "JawShadow", [(338.0, 81.5), (347.0, 82.2), (354.5, 78.5)], 2.6, CORE_SHADOW, 2.5))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill("Head", 51, 83, SKIN, x0=334, x1=363)))
    out.append(stroke_shape(i2, "UnderChinShadow", [(340.5, 82.5), (347.5, 83.5), (354.0, 80.5)], 3.2, CORE_SHADOW, 2.5))
    out.append(stroke_shape(i2, "SCMLine", [(354.0, 78.5), (348.5, 88.0), (344.5, 95.5)], 1.5, SOFT_SHADOW, 1.5))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", 76, 100, SKIN)))

    # 3. Sculpted Pectorals, 6-Pack Abs & Reclined Torso
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "LineaAlba", [(339.5, 121.0), (336.0, 138.0), (332.5, 155.0)], 1.3, "470F172A", 0.8))
    out.append(stroke_shape(i2, "PecHiNear", [(344.0, 101.0), (362.0, 103.5)], 2.4, HIGHLIGHT, 2.8))
    out.append(smooth_shape(i2, "PectoralNear", pec_near_pts, pec_paint))
    out.append(smooth_shape(i2, "PectoralFar", pec_far_pts, pec_paint))
    out.append(stroke_shape(i2, "TorsoHi", [(328.0, 104.0), (326.0, 128.0), (322.0, 150.0)], 4.0, HIGHLIGHT, 4.5))
    out.append(smooth_shape(i2, "Torso", torso_pts, skin_fill("Torso", 92, 168, SKIN, x0=312, x1=376)))

    # 4. Far (Right) Arm & Hand (behind torso, gripping FarGripHandle)
    out.append(smooth_shape(i2, "FarHand", far_hand_pts, skin_fill("FarHand", 119, 131, SKIN_FAR)))
    out.append(smooth_shape(i2, "FarForearm", far_fa_pts, skin_fill("FarFA", 119, 131, SKIN_FAR)))
    out.append(smooth_shape(i2, "FarUpperArm", far_ua_pts, skin_fill("FarUA", 98, 130, SKIN_FAR)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    near_lower_leg_xml = lower_leg_rig("Near", far=False)
    far_lower_leg_xml = lower_leg_rig("Far", far=True)
    roller_xml = ankle_roller_assembly()
    hold_down_xml = thigh_hold_down_and_handles()
    thighs_xml = seated_thighs_and_hamstrings()
    upper_body_xml = seated_torso_head_and_arms()
    machine_bg_xml = machine_background_tower()

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
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="LegCurl" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Left) Lower Leg (Gastrocnemius + Tibia + Bare Foot) -->
{near_lower_leg_xml}

        <!-- 2. Thigh Hold-Down Pad & Dual Grip Handles -->
{hold_down_xml}

        <!-- 3. Seated Athlete Upper Body (Head, Torso, Pectorals, 6-Pack Abs & Gripping Arms) -->
{upper_body_xml}

        <!-- 4. Seated Athlete Thighs & Primary Activated Hamstrings -->
{thighs_xml}

        <!-- 5. Far (Right) Lower Leg (Medial Gastrocnemius + Medial Knee Flexor + Bare Foot) -->
{far_lower_leg_xml}

        <!-- 6. Pivoting Ankle Roller Pad & Swing Arm (tucked behind/under distal shins) -->
{roller_xml}

        <!-- 7. Commercial Seated Leg Curl Machine Tower, Active Weight Stack & Seat Frame -->
{machine_bg_xml}

        <!-- 8. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="304" y="{f(FLOOR - 2)}" scaleX="1.15" scaleY="0.10" name="MachineShadow">
            <Ellipse width="220" height="220" name="MachineShadowEllipse"/>
            <Fill name="MachineShadowFill"><RadialGradient startX="0" startY="0" endX="110" endY="0" name="MachineShadowGrad">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="LegCurl" id="0:60">
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
    (BUILD / "leg_curl.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (38, "frame_mid"), (72, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(680, 26, 275))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
