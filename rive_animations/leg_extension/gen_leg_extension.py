#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive 7.3 scene for Seated Leg Extension (id: 'leg_extension').

Uses our canonical 3/4 front-left CommunityFitness mannequin (volumetric 3/4 head with hair/ear/brow/eye/mouth,
muscular neck, sculpted pectorals, 6-pack abs, deltoids/biceps/forearms gripping the seat side handles, dark
athletic compression shorts, sculpted quadriceps, and bare feet) seated in a commercial Leg Extension Machine.

Matches the 2-panel 3/4 front-left Seated Leg Extension Machine reference illustration:
  - Left Panel (f = 0 & f = 160, r = 0.0):
    * Athlete sits tall against the angled black backrest pad, hands gripping the seat side handles.
    * Both knees are flexed (~90 deg), lower legs hanging vertically behind the black cylindrical shin roller
      pad with the toes peeking out below the roller.
  - Right Panel (f = 72, r = 1.0):
    * Both knees extend upward through a smooth ~66 deg screen arc (full anatomical knee extension), lifting
      the cylindrical shin roller pad on top of the distal shins with dorsiflexed bare feet in front while
      the weight stack rises inside the rear frame.
  - Highlighted Target Muscle Groups (pulsing from warm orange #FFF97316 to intense crimson #FFF43F5E):
    1. Rectus femoris (Primary — central anterior head of the quadriceps femoris)
    2. Vastus lateralis (Primary — outer lateral sweep of the quadriceps femoris)
    3. Vastus medialis / VMO (Primary — medial teardrop head above the knee)

Run:
    python3 gen_leg_extension.py            # writes scene.rml
    python3 gen_leg_extension.py --publish  # compiles assets/animations/leg_extension.riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/leg_extension.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/leg_extension.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps loop
STEP = 2

# Canonical Seated Knee Pivot Anchors & Lower-Leg Lengths (3/4 front-left view)
KNEE_FAR = (248.0, 162.0)   # Right (far / screen-left) knee hinge
KNEE_NEAR = (274.0, 172.0)  # Left (near / screen-right) knee hinge
SHIN_LEN_FAR = 76.0
SHIN_LEN_NEAR = 80.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
FRAME_SILVER = ("FFF1F5F9", "FFCBD5E1", "FF64748B")
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


EASE_EXTEND = cubic_bezier(0.36, 0.0, 0.22, 1.0)
EASE_LOWER = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def extension_progress(frame):
    """Returns seated leg-extension progress r in [0.0, 1.0] across 160 frames:
    - 0..12:   Bottom flexed hold (r = 0.0: knees bent ~90 deg, shins behind roller)
    - 12..64:  Concentric quadriceps extension (r: 0.0 -> 1.0: legs extend straight out)
    - 64..84:  Peak top contraction hold (r = 1.0)
    - 84..148: Controlled eccentric lowering (r: 1.0 -> 0.0)
    - 148..160: Bottom flexed hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 64:
        return EASE_EXTEND((fr - 12) / 52.0)
    if fr <= 84:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_LOWER((fr - 84) / 64.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def pose(r):
    """Compute Seated Leg Extension transforms at progress r in [0.0, 1.0] using true circular knee extension."""
    # In screen coordinates (0 rad = +X right, pi/2 rad = +Y down, pi rad = -X left):
    # - Flexed start (r = 0.0): shins hang down-left (~99 deg = 1.73 rad)
    # - Extended peak (r = 1.0): shins extend straight out forward-left (~164 deg = 2.86 rad)
    ang_near = math.radians(lerp(99.0, 164.0, r))
    ang_far = math.radians(lerp(101.0, 165.0, r))

    ankle_near = (
        KNEE_NEAR[0] + SHIN_LEN_NEAR * math.cos(ang_near),
        KNEE_NEAR[1] + SHIN_LEN_NEAR * math.sin(ang_near),
    )
    ankle_far = (
        KNEE_FAR[0] + SHIN_LEN_FAR * math.cos(ang_far),
        KNEE_FAR[1] + SHIN_LEN_FAR * math.sin(ang_far),
    )

    # Cylindrical Shin Roller Pad rests ON TOP / ANTERIOR to the distal shins (above the ankle):
    # Note: For ang in [99 deg, 164 deg], ang + 90 deg points toward (-X, -Y), which is the ANTERIOR/TOP shin surface!
    perp_ant = ang_near + math.radians(90.0)
    roller_near = (
        KNEE_NEAR[0] + (SHIN_LEN_NEAR - 14.0) * math.cos(ang_near) + 10.5 * math.cos(perp_ant),
        KNEE_NEAR[1] + (SHIN_LEN_NEAR - 14.0) * math.sin(ang_near) + 10.5 * math.sin(perp_ant),
    )

    # Weight stack rises inside the rear tower as the knees extend upward (r: 0 -> 1)
    stack_dy = lerp(0.0, -34.0, r)

    return {
        "r": r,
        "ang_near": ang_near,
        "ang_far": ang_far,
        "ankle_near": ankle_near,
        "ankle_far": ankle_far,
        "roller_near": roller_near,
        "stack_dy": stack_dy,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(extension_progress(fr)) for fr in FRAMES}


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


# ---------------------------------------------------------------- 1. Commercial Seated Leg Extension Machine Frame & Weight Stack
def machine_background_frame():
    """Open commercial weight stack tower, animated active weight stack block, cam assembly,
    angled backrest with adjustment pin, seat pad, side grip handles, and base runners."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    frame_paint = (
        f'<Fill name="FrameFill">{grad3("FrameGrad", 45, 296, *FRAME_SILVER, x0=165, x1=395)}</Fill>'
        '<Stroke thickness="1.15" join="round" name="FrameStroke"><SolidColor colorValue="FF475569" name="FrameStrokeCol"/></Stroke>'
    )
    cam_paint = (
        f'<Fill name="CamFill">{grad("CamGrad", -20, -20, 20, 20, "FFF8FAFC", "FF94A3B8")}</Fill>'
        '<Stroke thickness="1.2" join="round" name="CamStroke"><SolidColor colorValue="FF475569" name="CamStrokeCol"/></Stroke>'
    )
    stack_paint = (
        '<Fill name="StackFill"><SolidColor colorValue="FF1E293B" name="StackCol"/></Fill>'
        '<Stroke thickness="0.95" join="round" name="StackStroke"><SolidColor colorValue="FF475569" name="StackStrokeCol"/></Stroke>'
    )
    backrest_paint = (
        f'<Fill name="BackrestFill">{grad3("BackrestGrad", 82, 192, *PAD_DARK, x0=330, x1=402)}</Fill>'
        '<Stroke thickness="1.2" join="round" name="BackrestStroke"><SolidColor colorValue="FF475569" name="BackrestStrokeCol"/></Stroke>'
    )
    seat_paint = (
        f'<Fill name="SeatFill">{grad3("SeatGrad", 178, 214, *PAD_DARK, x0=248, x1=362)}</Fill>'
        '<Stroke thickness="1.2" join="round" name="SeatStroke"><SolidColor colorValue="FF475569" name="SeatStrokeCol"/></Stroke>'
    )
    grip_paint = (
        '<Fill name="GripFill"><SolidColor colorValue="FF090D16" name="GripCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="GripStroke"><SolidColor colorValue="FF334155" name="GripStrokeCol"/></Stroke>'
    )

    stack_id = nid()
    key_double(stack_id, 14, lambda p: p["stack_dy"])

    out = [f'{ind}<Node name="MachineBackgroundFrame">']

    # Note: In Rive RML, earlier children in a <Node> render ON TOP of later children.
    # Layer A (Foreground of Machine): Seat Pad, Backrest Pad, Adjustment Pin & Side Stabilizer Handle
    out.append(poly_shape(i2, "NearSideGrip", [(312, 196), (332, 198), (332, 205), (312, 203)], grip_paint, radius=2.0))
    out.append(
        poly_shape(
            i2,
            "SeatPad",
            [(248, 182), (356, 192), (362, 212), (244, 200)],
            seat_paint,
            radius=4.0,
        )
    )
    out.append(poly_shape(i2, "BackrestAdjustGrip", [(402, 107), (418, 113), (416, 118), (400, 112)], grip_paint, radius=1.5))
    out.append(poly_shape(i2, "BackrestAdjustBar", [(388, 102), (404, 108), (402, 112), (386, 106)], frame_paint, radius=1.0))
    out.append(
        poly_shape(
            i2,
            "BackrestPad",
            [(348, 82), (396, 94), (364, 194), (324, 184)],
            backrest_paint,
            radius=4.5,
        )
    )

    # Layer B: Floor Rubber End-Caps & Base Runners (matching reference 3-point base)
    out.append(poly_shape(i2, "FootCapFrontRight", [(262, 286), (276, 290), (274, 300), (258, 296)], grip_paint, radius=2.0))
    out.append(poly_shape(i2, "FootCapFrontLeft", [(178, 250), (192, 254), (190, 264), (174, 260)], grip_paint, radius=2.0))
    out.append(poly_shape(i2, "FootCapRearRight", [(372, 252), (386, 256), (384, 266), (368, 262)], grip_paint, radius=2.0))

    # Front-right angled floor leg & vertical seat columns
    out.append(poly_shape(i2, "FrontRightBaseLeg", [(266, 288), (376, 252), (380, 260), (270, 296)], frame_paint, radius=2.0))
    out.append(poly_shape(i2, "FrontSeatPost", [(292, 202), (308, 204), (308, 280), (292, 280)], frame_paint, radius=2.0))
    out.append(poly_shape(i2, "RearSeatPost", [(346, 198), (360, 200), (368, 258), (354, 258)], frame_paint, radius=2.0))
    out.append(poly_shape(i2, "CrossBraceRunner", [(196, 246), (296, 274), (292, 282), (192, 254)], frame_paint, radius=2.0))
    out.append(poly_shape(i2, "LeftCamPost", [(184, 174), (198, 176), (198, 256), (184, 254)], frame_paint, radius=2.0))

    # Side Cam Wheel & Counterweight Knob on Left
    out.append(ellipse_shape(i2, "CounterweightBall", 204.0, 142.0, 15.0, 15.0, cam_paint))
    out.append(poly_shape(i2, "CounterweightArm", [(184, 168), (202, 144), (206, 148), (188, 172)], frame_paint, radius=1.5))
    out.append(ellipse_shape(i2, "SideCamWheel", 184.0, 172.0, 28.0, 36.0, cam_paint, rot_deg=-10.0))

    # Layer C: Weight Stack Tower Posts, Top Header, Guide Rods & Animated Active Weight Stack
    # Front-left and rear-right vertical tower uprights
    out.append(poly_shape(i2, "TowerPostLeft", [(212, 54), (222, 54), (222, 252), (212, 252)], frame_paint, radius=2.0))
    out.append(poly_shape(i2, "TowerPostRight", [(266, 42), (276, 42), (276, 240), (266, 240)], frame_paint, radius=2.0))
    out.append(poly_shape(i2, "TowerTopHeader", [(210, 50), (278, 36), (278, 48), (210, 62)], frame_paint, radius=2.5))
    out.append(poly_shape(i2, "TowerTopShield", [(220, 56), (268, 46), (268, 76), (220, 86)], cam_paint, radius=2.0))

    # Animated Active Weight Stack Block (rises as knees extend r: 0 -> 1)
    out.append(f'{i2}<Node y="{f(POSES[0]["stack_dy"])}" name="ActiveWeightStack" id="{stack_id}">')
    out.append(ellipse_shape(i3, "SelectorPin", 246.0, 186.0, 4.2, 4.2, solid("Pin", "FFF97316")))
    for idx in range(6):
        y_top = 154 + idx * 6.5
        out.append(
            poly_shape(
                i3,
                f"ActivePlate{idx + 1}",
                [(224, y_top), (264, y_top - 8), (264, y_top - 3), (224, y_top + 5)],
                stack_paint,
                radius=1.0,
            )
        )
    out.append(f"{i2}</Node>")

    # Resting Weight Stack Plates at Bottom of Tower
    for idx in range(5):
        y_top = 196 + idx * 6.5
        out.append(
            poly_shape(
                i2,
                f"RestPlate{idx + 1}",
                [(224, y_top), (264, y_top - 8), (264, y_top - 3), (224, y_top + 5)],
                stack_paint,
                radius=1.0,
            )
        )

    # Guide Rods & Lift Cable
    out.append(polyline_stroke_shape(i2, "LiftCable", [(244, 52), (244, 190)], 1.6, "FF94A3B8"))
    out.append(polyline_stroke_shape(i2, "GuideRod1", [(234, 56), (234, 232)], 1.8, "FFCBD5E1"))
    out.append(polyline_stroke_shape(i2, "GuideRod2", [(254, 52), (254, 226)], 1.8, "FFCBD5E1"))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 2. Foreground Shin Roller Assembly & Dynamic Lower Legs
def shin_roller_and_legs():
    """In Leg Extension, the black cylindrical shin roller pad rests ON TOP of the distal shins,
    while the dorsiflexed bare feet project out in front of the roller at full extension!"""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    near_leg_id, far_leg_id, near_foot_id, far_foot_id, pad_id, lever_id = (
        nid(), nid(), nid(), nid(), nid(), nid()
    )
    key_double(near_leg_id, 15, lambda p: p["ang_near"])
    key_double(far_leg_id, 15, lambda p: p["ang_far"])
    key_double(near_foot_id, 13, lambda p: p["ankle_near"][0])
    key_double(near_foot_id, 14, lambda p: p["ankle_near"][1])
    key_double(near_foot_id, 15, lambda p: p["ang_near"])
    key_double(far_foot_id, 13, lambda p: p["ankle_far"][0])
    key_double(far_foot_id, 14, lambda p: p["ankle_far"][1])
    key_double(far_foot_id, 15, lambda p: p["ang_far"])
    key_double(pad_id, 13, lambda p: p["roller_near"][0])
    key_double(pad_id, 14, lambda p: p["roller_near"][1])
    key_double(lever_id, 15, lambda p: p["ang_far"])

    p0 = POSES[0]

    pad_body_paint = (
        f'<Fill name="RollerBodyFill">{grad("RollerBodyGrad", -34, -18, 8, 14, "FF334155", "FF090D16")}</Fill>'
        '<Stroke thickness="1.2" join="round" name="RollerBodyStroke"><SolidColor colorValue="FF1E293B" name="RollerBodyStrokeCol"/></Stroke>'
    )
    cap_paint = (
        f'<Fill name="RollerCapFill">{grad("RollerCapGrad", -6, -8, 6, 8, "FFF8FAFC", "FF94A3B8")}</Fill>'
        '<Stroke thickness="1.3" name="RollerCapStroke"><SolidColor colorValue="FF0F172A" name="RollerCapStrokeCol"/></Stroke>'
    )
    frame_paint = (
        f'<Fill name="LeverFill">{grad3("LeverGrad", -5, 5, *FRAME_SILVER)}</Fill>'
        '<Stroke thickness="1.1" join="round" name="LeverStroke"><SolidColor colorValue="FF475569" name="LeverStrokeCol"/></Stroke>'
    )

    def make_shin_pts(shin_len):
        # Local coordinates: (0,0) = KNEE, +X = toward ANKLE.
        # Since ang in [99 deg, 164 deg], local +Y is ANTERIOR/TOP shin, local -Y is POSTERIOR/BOTTOM calf!
        return [
            (-8.0, 0.0), (6.0, 9.2), (30.0, 8.2), (56.0, 6.0),
            (shin_len - 4.0, 4.8), (shin_len + 2.0, 0.0), (shin_len - 4.0, -5.0),
            (54.0, -6.8), (28.0, -13.2), (10.0, -11.0), (-6.0, -6.5),
        ]

    # Dorsiflexed bare foot local to ANKLE (0,0), perpendicular to shin (+Y local = anterior/upward):
    # At r=0 (ang=99 deg), +Y local points forward-left (-X) so toes peek out beneath the roller;
    # At r=1 (ang=164 deg), +Y local points upright (-Y) so the foot stands vertically in front of the roller!
    foot_pts = [
        (-4.5, -5.5), (4.5, -5.0), (6.5, 4.0),
        (6.0, 21.5), (1.0, 24.5), (-4.0, 20.0), (-5.0, 6.0),
    ]

    out = [f'{ind}<Node name="LegsAndRollerGroup">']

    # 1. Foreground: Dorsiflexed Bare Feet (drawn IN FRONT of the shin roller pad so the soles/toes
    #    project cleanly in front of the roller at full extension and peek out below at start!)
    out.append(
        f'{i2}<Node x="{f(p0["ankle_near"][0])}" y="{f(p0["ankle_near"][1])}" '
        f'rotation="{f(p0["ang_near"])}" name="NearBareFootNode" id="{near_foot_id}">'
    )
    out.append(stroke_shape(i3, "NearToeLine1", [(1.5, 22.0), (4.8, 20.5)], 0.95, SOFT_SHADOW, 0.0))
    out.append(stroke_shape(i3, "NearToeLine2", [(0.5, 19.5), (4.2, 18.0)], 0.95, SOFT_SHADOW, 0.0))
    out.append(stroke_shape(i3, "NearFootArch", [(0.0, -2.0), (2.5, 9.0), (2.5, 19.5)], 1.15, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, "NearFootHi", [(-1.5, 4.0), (0.5, 16.5)], 2.2, HIGHLIGHT, 2.0))
    out.append(smooth_shape(i3, "NearBareFoot", foot_pts, skin_fill("NearFoot", -6, 24, SKIN)))
    out.append(f"{i2}</Node>")

    out.append(
        f'{i2}<Node x="{f(p0["ankle_far"][0])}" y="{f(p0["ankle_far"][1])}" '
        f'rotation="{f(p0["ang_far"])}" name="FarBareFootNode" id="{far_foot_id}">'
    )
    out.append(stroke_shape(i3, "FarToeLine1", [(1.5, 21.5), (4.5, 20.0)], 0.95, SOFT_SHADOW, 0.0))
    out.append(stroke_shape(i3, "FarFootArch", [(0.0, -2.0), (2.2, 8.5), (2.2, 19.0)], 1.1, SOFT_SHADOW, 0.8))
    out.append(smooth_shape(i3, "FarBareFoot", foot_pts, skin_fill("FarFoot", -6, 24, SKIN_FAR)))
    out.append(f"{i2}</Node>")

    # 2. Mid-Foreground: 3D Black Cylindrical Shin Roller Pad (resting ON TOP of the distal shins)
    out.append(
        f'{i2}<Node x="{f(p0["roller_near"][0])}" y="{f(p0["roller_near"][1])}" name="ShinRollerPad" id="{pad_id}">'
    )
    out.append(ellipse_shape(i3, "RollerCenterBolt", 0.0, 0.0, 6.5, 8.5, cap_paint, rot_deg=-12.0))
    out.append(ellipse_shape(i3, "RollerEndFace", 0.0, 0.0, 16.5, 21.5, solid("RollerEnd", "FF090D16"), rot_deg=-12.0))
    out.append(
        smooth_shape(
            i3,
            "RollerCylinderBody",
            [
                (3.0, -10.5), (-32.0, -24.5), (-40.0, -14.5),
                (-34.0, -1.5), (-2.0, 11.0), (6.5, 0.0),
            ],
            pad_body_paint,
        )
    )
    out.append(f"{i2}</Node>")

    # 3. Near (Left) Lower Leg (KNEE_NEAR -> ANKLE_NEAR, drawn behind the shin roller pad)
    out.append(
        f'{i2}<Node x="{f(KNEE_NEAR[0])}" y="{f(KNEE_NEAR[1])}" rotation="{f(p0["ang_near"])}" name="NearShinNode" id="{near_leg_id}">'
    )
    out.append(stroke_shape(i3, "NearTibialisLine", [(10.0, 3.8), (38.0, 3.5), (64.0, 2.2)], 1.25, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, "NearGastrocLine", [(14.0, -6.5), (34.0, -8.5), (52.0, -4.5)], 1.15, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, "NearShinHi", [(10.0, 6.5), (38.0, 5.8), (64.0, 3.5)], 2.6, HIGHLIGHT, 2.8))
    out.append(stroke_shape(i3, "NearShinSh", [(12.0, -9.5), (34.0, -11.5), (56.0, -5.0)], 3.2, CORE_SHADOW, 3.2))
    out.append(smooth_shape(i3, "NearShinShape", make_shin_pts(SHIN_LEN_NEAR), skin_fill("NearShin", -13, 10, SKIN)))
    out.append(f"{i2}</Node>")

    # 4. Far (Right) Lower Leg (KNEE_FAR -> ANKLE_FAR)
    out.append(
        f'{i2}<Node x="{f(KNEE_FAR[0])}" y="{f(KNEE_FAR[1])}" rotation="{f(p0["ang_far"])}" name="FarShinNode" id="{far_leg_id}">'
    )
    out.append(stroke_shape(i3, "FarTibialisLine", [(10.0, 3.5), (36.0, 3.2), (60.0, 2.0)], 1.15, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, "FarShinHi", [(10.0, 6.2), (36.0, 5.5), (60.0, 3.2)], 2.2, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i3, "FarShinShape", make_shin_pts(SHIN_LEN_FAR), skin_fill("FarShin", -13, 10, SKIN_FAR)))
    out.append(f"{i2}</Node>")

    # 5. Pivoting Machine Swing Arm behind Far Leg
    out.append(
        f'{i2}<Node x="{f(KNEE_FAR[0] - 24.0)}" y="{f(KNEE_FAR[1] + 4.0)}" rotation="{f(p0["ang_far"])}" name="SwingLeverArm" id="{lever_id}">'
    )
    out.append(poly_shape(i3, "SwingBeam", [(-6, -4.5), (64, -4.0), (64, 4.0), (-6, 4.5)], frame_paint, radius=2.0))
    out.append(ellipse_shape(i3, "SwingHub", 0.0, 0.0, 14.0, 14.0, frame_paint))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. Seated Thighs with Glowing 3-Head Quadriceps Femoris
def seated_thighs_and_quadriceps():
    """Seated Far and Near Thighs with all 3 superficial Quadriceps Femoris heads (Rectus femoris,
    Vastus lateralis, Vastus medialis / VMO) pulsing from warm orange to intense crimson."""
    ind = "        "
    i2 = ind + "    "

    def rectus_t(p):
        return 0.44 + 0.56 * (p["r"] ** 0.75)

    def vastus_t(p):
        return 0.40 + 0.56 * (p["r"] ** 0.78)

    # Near (Left) Thigh base contour from Hip (330, 178) to KNEE_NEAR (274, 172)
    near_thigh_pts = [
        (264.0, 166.0), (278.0, 150.0), (308.0, 148.0), (332.0, 158.0),
        (336.0, 184.0), (312.0, 190.0), (274.0, 182.0),
    ]
    # Near Quadriceps Heads:
    # 1. Vastus lateralis (broad outer/lower-lateral sweep on the near left thigh)
    near_vl_pts = [
        (278.0, 162.0), (304.0, 156.0), (326.0, 163.0),
        (320.0, 177.0), (294.0, 176.0), (276.0, 170.0),
    ]
    # 2. Rectus femoris (central fusiform head along the top crest of the thigh)
    near_rf_pts = [
        (274.0, 156.0), (298.0, 148.5), (324.0, 154.5),
        (322.0, 165.0), (296.0, 164.0), (274.0, 162.0),
    ]
    # 3. Vastus medialis (VMO teardrop on the upper-medial knee aspect)
    near_vm_pts = [
        (268.0, 156.0), (284.0, 149.5), (296.0, 154.0),
        (286.0, 163.0), (270.0, 162.0),
    ]

    # Far (Right) Thigh base contour from Hip (304, 168) to KNEE_FAR (248, 162)
    far_thigh_pts = [
        (238.0, 156.0), (254.0, 140.0), (284.0, 138.0), (308.0, 148.0),
        (310.0, 172.0), (286.0, 178.0), (248.0, 170.0),
    ]
    far_rf_pts = [
        (248.0, 148.0), (274.0, 139.0), (298.0, 145.0),
        (294.0, 158.0), (268.0, 159.0), (248.0, 155.0),
    ]
    far_vm_pts = [
        (246.0, 152.0), (266.0, 148.0), (282.0, 154.0),
        (272.0, 164.0), (248.0, 161.0),
    ]

    pelvis_shorts = [
        (302.0, 146.0), (332.0, 152.0), (354.0, 162.0),
        (348.0, 192.0), (318.0, 194.0), (298.0, 176.0),
    ]

    out = [f'{ind}<Node name="SeatedThighsAndQuadriceps">']

    # Note: In Rive RML, earlier children in a <Node> render ON TOP of later children.
    # 1. Foreground: Near (Left) Thigh & 3-Head Quadriceps Femoris (Rectus femoris + Vastus lateralis + Vastus medialis)
    out.append(stroke_shape(i2, "NearQuadBipennate1", [(282.0, 156.0), (302.0, 155.0), (320.0, 160.0)], 1.05, "807F1D1D", 0.3))
    out.append(stroke_shape(i2, "NearQuadBipennate2", [(284.0, 166.0), (304.0, 165.0), (318.0, 169.0)], 1.05, "807F1D1D", 0.3))
    out.append(stroke_shape(i2, "NearQuadHi", [(282.0, 153.5), (304.0, 152.5), (320.0, 157.5)], 2.4, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i2, "NearVastusLateralis", near_vl_pts, muscle_paint_fn("NearVL", vastus_t, 1.05)))
    out.append(smooth_shape(i2, "NearRectusFemoris", near_rf_pts, muscle_paint_fn("NearRF", rectus_t, 1.1)))
    out.append(smooth_shape(i2, "NearVastusMedialis", near_vm_pts, muscle_paint_fn("NearVM", vastus_t, 1.0)))
    out.append(stroke_shape(i2, "NearHamUnder", [(278.0, 180.0), (304.0, 185.0), (324.0, 186.0)], 2.8, CORE_SHADOW, 2.8))
    out.append(smooth_shape(i2, "NearThighBase", near_thigh_pts, skin_fill("NearThigh", 148, 190, SKIN)))

    # 2. Midground: Far (Right) Thigh & Quadriceps Femoris (Rectus femoris + Vastus medialis)
    out.append(stroke_shape(i2, "FarQuadBipennate", [(256.0, 147.0), (276.0, 146.0), (292.0, 151.0)], 1.0, "807F1D1D", 0.3))
    out.append(stroke_shape(i2, "FarQuadHi", [(256.0, 144.0), (276.0, 143.0), (292.0, 148.0)], 2.0, HIGHLIGHT, 2.2))
    out.append(smooth_shape(i2, "FarVastusMedialis", far_vm_pts, muscle_paint_fn("FarVM", vastus_t, 1.0)))
    out.append(smooth_shape(i2, "FarRectusFemoris", far_rf_pts, muscle_paint_fn("FarRF", rectus_t, 1.05)))
    out.append(smooth_shape(i2, "FarThighBase", far_thigh_pts, skin_fill("FarThigh", 138, 178, SKIN_FAR)))

    # 3. Background of Pelvis: Dark Athletic Compression Shorts on Seat & Far (Right) Arm behind thigh
    out.append(stroke_shape(i2, "ShortsLegHem", [(314.0, 156.0), (320.0, 174.0), (312.0, 190.0)], 1.6, "660F172A", 0.8))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill("Shorts", 146, 194, SHORTS, x0=298, x1=354)))
    out.append(smooth_shape(i2, "FarForearm", [(292.0, 132.0), (302.0, 136.0), (292.0, 156.0), (282.0, 152.0)], skin_fill("FarFA", 132, 156, SKIN_FAR)))
    out.append(smooth_shape(i2, "FarUpperArm", [(306.0, 98.0), (318.0, 102.0), (304.0, 138.0), (292.0, 134.0)], skin_fill("FarUA", 98, 138, SKIN_FAR)))
    out.append(smooth_shape(i2, "FarDeltoid", [(308.0, 86.0), (320.0, 84.0), (322.0, 104.0), (306.0, 108.0)], skin_fill("FarDelt", 84, 108, SKIN_FAR)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def seated_torso_head_and_arms():
    """Canonical 3/4 front-left CommunityFitness upper body seated upright against the backrest pad,
    with both arms extending down beside the hips to grip the seat side handles (matching reference)."""
    ind = "        "
    i2 = ind + "    "

    # Volumetric 3/4 Head
    head_pts = [
        (332.0, 48.0), (329.0, 54.5), (327.5, 60.5), (328.8, 65.5),
        (329.5, 71.5), (335.5, 74.5), (345.0, 73.0), (352.0, 69.0),
        (357.0, 61.0), (356.5, 50.0), (349.5, 43.0), (339.0, 43.0),
    ]
    hair_pts = [
        (331.5, 50.0), (337.0, 42.5), (349.0, 42.2), (357.0, 48.5),
        (357.5, 59.5), (353.0, 63.5), (351.5, 55.5), (346.0, 50.5),
        (338.5, 49.0),
    ]
    neck_pts = [
        (334.5, 71.0), (351.0, 68.0), (360.0, 84.0),
        (362.0, 92.0), (322.0, 88.0), (331.0, 80.0),
    ]

    # Seated Torso braced against backrest
    torso_pts = [
        (318.0, 86.0), (340.0, 84.0), (370.0, 90.0),
        (370.0, 114.0), (360.0, 138.0), (350.0, 160.0),
        (328.0, 164.0), (306.0, 150.0), (312.0, 126.0), (314.0, 104.0),
    ]
    pec_near_pts = [
        (336.0, 89.0), (362.0, 92.0), (366.0, 108.0),
        (358.0, 119.0), (344.0, 120.0), (333.0, 114.0),
    ]
    pec_far_pts = [
        (318.0, 88.0), (335.0, 88.5), (332.0, 113.5),
        (321.0, 114.5), (314.0, 106.0), (315.0, 95.0),
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
        [(332.0, 117.0), (344.0, 118.0), (342.5, 126.5), (330.5, 125.5)],
        [(330.0, 128.0), (342.0, 129.0), (340.0, 137.5), (328.5, 136.5)],
        [(328.0, 139.0), (339.5, 140.0), (337.5, 148.5), (326.5, 147.5)],
        [(320.0, 116.0), (330.0, 116.8), (328.5, 125.0), (318.5, 124.0)],
        [(318.0, 127.0), (328.0, 127.8), (326.5, 136.0), (316.5, 135.0)],
        [(316.0, 138.0), (326.0, 138.8), (324.5, 147.0), (314.5, 146.0)],
    ]

    # Near (Left) Arm extending down along the side of the backrest/hip to grip NearSideGrip at (326, 200)
    near_delt_pts = [
        (354.0, 90.0), (368.0, 88.0), (378.0, 98.0),
        (374.0, 114.0), (360.0, 118.0), (352.0, 106.0),
    ]
    near_ua_pts = [
        (360.0, 106.0), (374.0, 110.0), (362.0, 152.0),
        (348.0, 148.0), (352.0, 124.0),
    ]
    near_fa_pts = [
        (350.0, 144.0), (362.0, 148.0), (342.0, 196.0),
        (332.0, 192.0), (342.0, 166.0),
    ]
    near_hand_pts = [
        (324.0, 190.0), (340.0, 192.0), (338.0, 204.0), (322.0, 202.0),
    ]

    # Far (Right) Arm tucked naturally behind the right torso/hip (never overlapping the front quadriceps)
    far_delt_pts = [
        (308.0, 86.0), (320.0, 84.0), (322.0, 104.0), (306.0, 108.0),
    ]
    far_ua_pts = [
        (306.0, 98.0), (318.0, 102.0), (308.0, 138.0), (296.0, 134.0),
    ]
    far_fa_pts = [
        (298.0, 132.0), (308.0, 136.0), (300.0, 154.0), (290.0, 150.0),
    ]

    out = [f'{ind}<Node name="SeatedUpperBody">']

    # 1. Near (Left) Arm & Hand gripping seat side handle
    out.append(stroke_shape(i2, "NearKnuckle", [(326.0, 196.0), (336.0, 197.0)], 1.0, SOFT_SHADOW, 0.0))
    out.append(smooth_shape(i2, "NearHand", near_hand_pts, skin_fill("NearHand", 190, 204, SKIN)))
    out.append(stroke_shape(i2, "NearForearmHi", [(354.0, 152.0), (346.0, 172.0), (338.0, 190.0)], 2.2, HIGHLIGHT, 2.4))
    out.append(smooth_shape(i2, "NearForearm", near_fa_pts, skin_fill("NearFA", 144, 196, SKIN)))
    out.append(stroke_shape(i2, "NearBicepsHi", [(364.0, 114.0), (358.0, 132.0), (354.0, 146.0)], 2.4, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i2, "NearUpperArm", near_ua_pts, skin_fill("NearUA", 106, 152, SKIN)))
    out.append(stroke_shape(i2, "NearDeltHi", [(360.0, 94.0), (370.0, 100.0), (366.0, 112.0)], 2.4, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i2, "NearDeltoid", near_delt_pts, skin_fill("NearDelt", 88, 118, SKIN)))

    # 2. Volumetric 3/4 Head & Muscular Neck
    out.append(smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 332, 42, 357, 63, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i2, "Ear", 350.0, 62.5, 5.5, 8.5, solid("Ear", "FFA3B1C4"), rot_deg=12.0))
    out.append(stroke_shape(i2, "BrowShade", [(329.0, 54.8), (333.5, 55.2)], 1.4, "590F172A", 0.8))
    out.append(stroke_shape(i2, "EyeLine", [(330.8, 56.6), (333.8, 56.8)], 1.1, "730F172A", 0.4))
    out.append(stroke_shape(i2, "MouthLine", [(329.0, 66.5), (332.5, 66.8)], 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i2, "HeadHi", [(332.5, 52.0), (336.5, 47.0), (345.0, 46.0)], 3.0, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i2, "JawShadow", [(332.0, 73.5), (341.0, 74.2), (348.5, 70.5)], 2.6, CORE_SHADOW, 2.5))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill("Head", 43, 75, SKIN, x0=328, x1=357)))
    out.append(stroke_shape(i2, "UnderChinShadow", [(334.5, 74.5), (341.5, 75.5), (348.0, 72.5)], 3.2, CORE_SHADOW, 2.5))
    out.append(stroke_shape(i2, "SCMLine", [(348.0, 70.5), (342.5, 80.0), (338.5, 87.5)], 1.5, SOFT_SHADOW, 1.5))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", 68, 92, SKIN)))

    # 3. Sculpted Pectorals, 6-Pack Abs & Reclined Torso
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "LineaAlba", [(333.5, 114.0), (330.0, 131.0), (326.5, 148.0)], 1.3, "470F172A", 0.8))
    out.append(stroke_shape(i2, "PecHiNear", [(338.0, 93.0), (356.0, 95.5)], 2.4, HIGHLIGHT, 2.8))
    out.append(smooth_shape(i2, "PectoralNear", pec_near_pts, pec_paint))
    out.append(smooth_shape(i2, "PectoralFar", pec_far_pts, pec_paint))
    out.append(stroke_shape(i2, "TorsoHi", [(322.0, 96.0), (320.0, 120.0), (316.0, 142.0)], 4.0, HIGHLIGHT, 4.5))
    out.append(smooth_shape(i2, "Torso", torso_pts, skin_fill("Torso", 84, 164, SKIN, x0=306, x1=370)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    legs_and_roller_xml = shin_roller_and_legs()
    upper_body_xml = seated_torso_head_and_arms()
    thighs_xml = seated_thighs_and_quadriceps()
    machine_bg_xml = machine_background_frame()

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
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="LegExtension" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Bare Feet, Cylindrical Shin Roller Pad & Extending Lower Legs -->
{legs_and_roller_xml}

        <!-- 2. Seated Athlete Upper Body (Head, Torso, Pectorals, 6-Pack Abs & Near Arm Gripping Side Handle) -->
{upper_body_xml}

        <!-- 3. Seated Athlete Thighs, Glowing 3-Head Quadriceps Femoris & Far Arm -->
{thighs_xml}

        <!-- 4. Commercial Leg Extension Machine Frame, Cam Wheel & Animated Weight Stack -->
{machine_bg_xml}

        <!-- 5. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="292" y="{f(FLOOR - 2)}" scaleX="1.18" scaleY="0.10" name="MachineShadow">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="LegExtension" id="0:60">
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
    (BUILD / "leg_extension.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (38, "frame_mid"), (72, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(680, 22, 260))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
