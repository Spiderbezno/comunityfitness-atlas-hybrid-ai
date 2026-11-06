#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive 7.3 scene for 45-Degree Plate-Loaded Leg Press (id: 'leg_press').

Uses our canonical 3/4 CommunityFitness mannequin (volumetric 3/4 head with hair/ear/brow/eye/mouth,
muscular neck, sculpted pectorals, 6-pack abs, deltoids/biceps/forearms gripping the seat stabilizer
handles, dark athletic compression shorts, sculpted quadriceps/glutes/calves, and athletic training
shoes planted shoulder-width apart on the angled sled platform) reclined in a 45-degree Plate-Loaded
Leg Press Machine.

Matches the 45-Degree Plate-Loaded Leg Press reference illustration (top green-check biomechanical row):
  - Left Panel (f = 0 & f = 160, r = 0.0 — Full Range of Motion / Bottom Flexed Position):
    * Athlete sits firmly braced in the angled bucket seat with neutral spine against the backrest pad,
      hands gripping the side hip stabilizer handles.
    * Feet are planted shoulder-width apart on the 45-degree sled footplate; knees are flexed (~86 deg)
      toward the chest in a deep, controlled eccentric bottom position.
  - Right Panel (f = 72, r = 1.0 — Top Pressed Position, Knees NOT Locked Out):
    * Both legs drive the weighted sled carriage up the 36-degree steel guide rails to a strong extension
      While keeping a safe athletic soft bend in the knees (~156 deg interior angle — never hyperextended).
  - Highlighted Target Muscle Groups (pulsing from warm orange #FFF97316 to intense crimson #FFF43F5E):
    1. Quadriceps femoris (Primary — Rectus femoris, Vastus lateralis, Vastus medialis / VMO)
    2. Gluteus maximus (Primary/Synergist — hip extension drive at the base of the pelvis)
    3. Hamstrings & Gastrocnemius (Secondary — dynamic knee/ankle stabilization)

Run:
    python3 gen_leg_press.py            # writes scene.rml
    python3 gen_leg_press.py --publish  # compiles assets/animations/leg_press.riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/leg_press.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/leg_press.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps loop
STEP = 2

# 45-Degree Angled Guide Rail Geometry (36 deg incline in screen space: +X right, -Y up)
RAIL_DEG = -36.0
RAIL_RAD = math.radians(RAIL_DEG)
RAIL_COS = math.cos(RAIL_RAD)  # +0.8090
RAIL_SIN = math.sin(RAIL_RAD)  # -0.5878

# Fixed Hip Anchors in the Reclined Bucket Seat (3/4 front-right view, feet shoulder-width apart)
HIP_NEAR = (254.0, 212.0)  # Right (near / foreground) hip joint
HIP_FAR = (242.0, 198.0)   # Left (far / background) hip joint

# Segment Lengths for Exact 2-Bone Inverse Kinematics (HIP -> KNEE -> ANKLE)
L_THIGH_NEAR = 92.0
L_SHIN_NEAR = 90.0
L_THIGH_FAR = 90.0
L_SHIN_FAR = 88.0

# Ankle Anchors on the Sled Footplate at Bottom Position (r = 0.0) & Sled Travel Distance
ANKLE_NEAR_0 = (348.0, 134.0)
ANKLE_FAR_0 = (334.0, 120.0)
SLED_TRAVEL = 52.0  # Travels 52 px along the -36 deg guide rails (knees remain safely unlocked at r=1.0)

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
FRAME_SILVER = ("FFF1F5F9", "FFCBD5E1", "FF64748B")
RAIL_CHROME = ("FFF8FAFC", "FFCBD5E1", "FF475569")
PAD_DARK = ("FF334155", "FF182232", "FF090D16")
PLATE_DARK = ("FF334155", "FF1E293B", "FF0F172A")
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


EASE_PRESS = cubic_bezier(0.34, 0.0, 0.20, 1.0)
EASE_LOWER = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def press_progress(frame):
    """Returns leg-press progress r in [0.0, 1.0] across 160 frames:
    - 0..14:   Bottom flexed hold (r = 0.0: knees flexed ~86 deg, full range of motion)
    - 14..66:  Concentric leg press drive (r: 0.0 -> 1.0: sled pushed up rails, knees NOT locked out)
    - 66..86:  Top controlled hold (r = 1.0: soft knee bend maintained)
    - 86..148: Controlled eccentric lowering (r: 1.0 -> 0.0)
    - 148..160: Bottom flexed hold (r = 0.0)
    """
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


def solve_leg_ik(hip, ankle, l_thigh, l_shin):
    """Exact 2-bone IK from fixed hip to moving ankle on the sled footplate.
    Knee bends upward/leftward (-Y, -X side of the hip->ankle vector)."""
    dx = ankle[0] - hip[0]
    dy = ankle[1] - hip[1]
    d = max(1.0, min(l_thigh + l_shin - 0.5, math.hypot(dx, dy)))
    base_ang = math.atan2(dy, dx)
    cos_a = max(-1.0, min(1.0, (l_thigh ** 2 + d ** 2 - l_shin ** 2) / (2.0 * l_thigh * d)))
    alpha = math.acos(cos_a)
    thigh_ang = base_ang - alpha
    knee = (
        hip[0] + l_thigh * math.cos(thigh_ang),
        hip[1] + l_thigh * math.sin(thigh_ang),
    )
    shin_ang = math.atan2(ankle[1] - knee[1], ankle[0] - knee[0])
    return thigh_ang, knee, shin_ang


def pose(r):
    """Compute 45-Degree Plate-Loaded Leg Press transforms at progress r in [0.0, 1.0]."""
    dist = SLED_TRAVEL * r
    sled_dx = dist * RAIL_COS
    sled_dy = dist * RAIL_SIN

    ankle_near = (ANKLE_NEAR_0[0] + sled_dx, ANKLE_NEAR_0[1] + sled_dy)
    ankle_far = (ANKLE_FAR_0[0] + sled_dx, ANKLE_FAR_0[1] + sled_dy)

    thigh_ang_near, knee_near, shin_ang_near = solve_leg_ik(
        HIP_NEAR, ankle_near, L_THIGH_NEAR, L_SHIN_NEAR
    )
    thigh_ang_far, knee_far, shin_ang_far = solve_leg_ik(
        HIP_FAR, ankle_far, L_THIGH_FAR, L_SHIN_FAR
    )

    return {
        "r": r,
        "sled_dx": sled_dx,
        "sled_dy": sled_dy,
        "ankle_near": ankle_near,
        "ankle_far": ankle_far,
        "knee_near": knee_near,
        "knee_far": knee_far,
        "thigh_ang_near": thigh_ang_near,
        "thigh_ang_far": thigh_ang_far,
        "shin_ang_near": shin_ang_near,
        "shin_ang_far": shin_ang_far,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(press_progress(fr)) for fr in FRAMES}


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


# ---------------------------------------------------------------- 1. 45-Degree Leg Press Machine Frame & Sliding Sled
def machine_frame_and_sled():
    """Commercial 45-degree Plate-Loaded Leg Press frame:
    - Reclined padded backrest + angled bucket seat pad with neutral-spine lumbar support
    - Twin 36-degree inclined steel guide rails + heavy base frame & vertical support columns
    - Animated sliding Sled Carriage (`SledNode`) with heavy angled footplate, side frame cheeks,
      and 45 lb Olympic weight plates mounted on the sled weight horn."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    frame_paint = (
        f'<Fill name="FrameFill">{grad3("FrameGrad", 95, 296, *FRAME_SILVER, x0=150, x1=510)}</Fill>'
        '<Stroke thickness="1.2" join="round" name="FrameStroke"><SolidColor colorValue="FF475569" name="FrameStrokeCol"/></Stroke>'
    )
    rail_paint = (
        f'<Fill name="RailFill">{grad3("RailGrad", 80, 260, *RAIL_CHROME, x0=270, x1=505)}</Fill>'
        '<Stroke thickness="1.15" join="round" name="RailStroke"><SolidColor colorValue="FF334155" name="RailStrokeCol"/></Stroke>'
    )
    pad_paint = (
        f'<Fill name="PadFill">{grad3("PadGrad", 155, 250, *PAD_DARK, x0=145, x1=290)}</Fill>'
        '<Stroke thickness="1.2" join="round" name="PadStroke"><SolidColor colorValue="FF475569" name="PadStrokeCol"/></Stroke>'
    )
    footplate_paint = (
        f'<Fill name="FootplateFill">{grad("FootplateGrad", 320, 68, 392, 168, "FF334155", "FF0F172A")}</Fill>'
        '<Stroke thickness="1.3" join="round" name="FootplateStroke"><SolidColor colorValue="FF64748B" name="FootplateStrokeCol"/></Stroke>'
    )
    footplate_side_paint = (
        f'<Fill name="FootSideFill">{grad("FootSideGrad", 340, 60, 412, 156, "FF475569", "FF1E293B")}</Fill>'
        '<Stroke thickness="1.2" join="round" name="FootSideStroke"><SolidColor colorValue="FF94A3B8" name="FootSideStrokeCol"/></Stroke>'
    )
    plate_paint = (
        f'<Fill name="PlateFill">{grad3("PlateGrad", 70, 145, *PLATE_DARK, x0=375, x1=435)}</Fill>'
        '<Stroke thickness="1.2" join="round" name="PlateStroke"><SolidColor colorValue="FF64748B" name="PlateStrokeCol"/></Stroke>'
    )
    grip_paint = (
        '<Fill name="GripFill"><SolidColor colorValue="FF090D16" name="GripCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="GripStroke"><SolidColor colorValue="FF334155" name="GripStrokeCol"/></Stroke>'
    )

    sled_id = nid()
    key_double(sled_id, 13, lambda p: p["sled_dx"])
    key_double(sled_id, 14, lambda p: p["sled_dy"])

    out = [f'{ind}<Node name="LegPressMachine">']

    # Note: In Rive RML, earlier children in a <Node> render ON TOP of later children.
    # Layer A (Foreground of Machine): Near Guide Rail & Sliding Sled Carriage
    # Near (foreground) 36-deg inclined guide rail from (276, 256) to (502, 92)
    out.append(
        poly_shape(
            i2,
            "NearGuideRail",
            [(272, 250), (498, 86), (506, 97), (280, 261)],
            rail_paint,
            radius=2.0,
        )
    )
    out.append(
        polyline_stroke_shape(
            i2, "NearRailHighlight", [(276, 251), (500, 89)], 1.6, "D9FFFFFF"
        )
    )

    # Animated Sled Assembly (slides along RAIL_RAD = -36 deg by (sled_dx, sled_dy))
    out.append(
        f'{i2}<Node x="{f(POSES[0]["sled_dx"])}" y="{f(POSES[0]["sled_dy"])}" name="SlidingSledNode" id="{sled_id}">'
    )
    # Linear bearing carriage sleeves riding on the guide rails
    out.append(
        poly_shape(
            i3,
            "SledBearingSleeve",
            [(346, 194), (410, 147), (420, 160), (356, 207)],
            frame_paint,
            radius=2.5,
        )
    )
    # 3D Angled Sled Footplate Box (perpendicular to the -36 deg rail: tilted at -126 deg / +54 deg)
    # Front contact face where the athlete's shoes press (from (318, 92) to (372, 166))
    out.append(
        poly_shape(
            i3,
            "SledFootplateFace",
            [(316, 88), (336, 74), (390, 148), (370, 162)],
            footplate_paint,
            radius=3.0,
        )
    )
    # 3D Side/Rear thickness block of the sled platform (matching reference thick angled block)
    out.append(
        poly_shape(
            i3,
            "SledFootplateDepthBlock",
            [(336, 74), (362, 55), (416, 129), (390, 148)],
            footplate_side_paint,
            radius=3.5,
        )
    )
    out.append(
        polyline_stroke_shape(
            i3, "SledEdgeCrease", [(336, 75), (390, 147)], 1.4, "99CBD5E1"
        )
    )
    # Under-frame steelgusset connecting the footplate block down to the rail bearing sleeve
    out.append(
        poly_shape(
            i3,
            "SledUnderGusset",
            [(366, 156), (404, 128), (412, 149), (356, 196)],
            frame_paint,
            radius=2.0,
        )
    )
    # Plate-Loaded Olympic Weight Horn & Stacked 45 lb Plates on the back of the Sled
    out.append(
        poly_shape(
            i3,
            "WeightHornSleeve",
            [(388, 102), (424, 76), (428, 82), (392, 108)],
            rail_paint,
            radius=1.5,
        )
    )
    out.append(
        ellipse_shape(i3, "OlympicPlateOuter", 404.0, 96.0, 18.0, 48.0, plate_paint, rot_deg=-36.0)
    )
    out.append(
        ellipse_shape(i3, "OlympicPlateHub", 404.0, 96.0, 5.5, 13.0, rail_paint, rot_deg=-36.0)
    )
    out.append(
        ellipse_shape(i3, "OlympicPlateInner", 396.0, 102.0, 18.0, 50.0, plate_paint, rot_deg=-36.0)
    )
    out.append(f"{i2}</Node>")

    # Layer B: Reclined Backrest Pad, Angled Bucket Seat Pad & Side Stabilizer Handles
    # Bucket Seat Pad (angled up-right from (242, 236) to (282, 204) to lock the pelvis)
    out.append(
        poly_shape(
            i2,
            "BucketSeatPad",
            [(238, 228), (276, 198), (286, 210), (246, 242)],
            pad_paint,
            radius=4.0,
        )
    )
    # Reclined Backrest Pad (extending up behind the neck and head from (136, 130) to (242, 228))
    out.append(
        poly_shape(
            i2,
            "ReclinedBackrestPad",
            [(138, 128), (242, 228), (232, 240), (128, 140)],
            pad_paint,
            radius=4.5,
        )
    )
    # Structural steel cradle under the backrest and seat
    out.append(
        poly_shape(
            i2,
            "SeatSteelCradle",
            [(136, 144), (244, 246), (288, 212), (294, 220), (244, 258), (130, 150)],
            frame_paint,
            radius=2.5,
        )
    )

    # Layer C: Far Guide Rail, Safety Stopper Catch & Heavy Floor Support Columns
    out.append(
        poly_shape(
            i2,
            "FarGuideRail",
            [(260, 238), (486, 74), (493, 83), (267, 247)],
            frame_paint,
            radius=2.0,
        )
    )
    # Racking safety catch handle along the rail
    out.append(
        poly_shape(
            i2,
            "SafetyStopCatch",
            [(322, 212), (332, 205), (340, 222), (330, 228)],
            grip_paint,
            radius=1.5,
        )
    )
    # Support pillars down to the floor (FLOOR = 300)
    out.append(
        poly_shape(
            i2,
            "RearRailSupportColumn",
            [(446, 122), (460, 112), (484, 292), (468, 292)],
            frame_paint,
            radius=2.0,
        )
    )
    out.append(
        poly_shape(
            i2,
            "CenterFrameColumn",
            [(298, 228), (314, 216), (332, 292), (314, 292)],
            frame_paint,
            radius=2.0,
        )
    )
    out.append(
        poly_shape(
            i2,
            "BackrestSupportLeg",
            [(192, 206), (206, 218), (182, 292), (166, 292)],
            frame_paint,
            radius=2.0,
        )
    )
    # Horizontal Floor Base Beam & Rubber Feet
    out.append(
        poly_shape(
            i2,
            "MainFloorBaseBeam",
            [(156, 286), (496, 286), (496, 296), (156, 296)],
            frame_paint,
            radius=2.5,
        )
    )
    out.append(poly_shape(i2, "RubberFootLeft", [(150, 292), (176, 292), (176, 300), (150, 300)], grip_paint, radius=2.0))
    out.append(poly_shape(i2, "RubberFootMid", [(308, 292), (338, 292), (338, 300), (308, 300)], grip_paint, radius=2.0))
    out.append(poly_shape(i2, "RubberFootRight", [(466, 292), (498, 292), (498, 300), (466, 300)], grip_paint, radius=2.0))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 2. Dynamic Legs (2-Bone IK: Thighs, Shins, Feet & Target Muscles)
def build_leg_assemblies():
    """Builds the Near (Right) and Far (Left) leg assemblies driven by exact 2-bone IK:
    - Each Thigh Node is anchored at HIP and rotates by thigh_ang(r), carrying sculpted Quadriceps
      femoris (Rectus femoris, Vastus lateralis, Vastus medialis / VMO) and Hamstrings.
    - Each Shin Node is anchored at KNEE(r) and rotates by shin_ang(r), carrying Gastrocnemius & Tibialis.
    - Each Shoe/Foot Node is anchored at ANKLE(r) and stays planted flat against the -126 deg sled footplate!"""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    near_thigh_id, near_shin_id, near_foot_id = nid(), nid(), nid()
    far_thigh_id, far_shin_id, far_foot_id = nid(), nid(), nid()

    key_double(near_thigh_id, 15, lambda p: p["thigh_ang_near"])
    key_double(near_shin_id, 13, lambda p: p["knee_near"][0])
    key_double(near_shin_id, 14, lambda p: p["knee_near"][1])
    key_double(near_shin_id, 15, lambda p: p["shin_ang_near"])
    key_double(near_foot_id, 13, lambda p: p["ankle_near"][0])
    key_double(near_foot_id, 14, lambda p: p["ankle_near"][1])

    key_double(far_thigh_id, 15, lambda p: p["thigh_ang_far"])
    key_double(far_shin_id, 13, lambda p: p["knee_far"][0])
    key_double(far_shin_id, 14, lambda p: p["knee_far"][1])
    key_double(far_shin_id, 15, lambda p: p["shin_ang_far"])
    key_double(far_foot_id, 13, lambda p: p["ankle_far"][0])
    key_double(far_foot_id, 14, lambda p: p["ankle_far"][1])

    p0 = POSES[0]

    # Muscle activation curves (pulsing from warm orange to intense crimson as the sled is pressed)
    def quad_primary_t(p):
        return 0.45 + 0.55 * (p["r"] ** 0.75)

    def glute_primary_t(p):
        return 0.42 + 0.56 * (p["r"] ** 0.78)

    def secondary_t(p):
        return 0.28 + 0.44 * (p["r"] ** 0.85)

    shoe_near_paint = (
        f'<Fill name="ShoeNearFill">{grad("ShoeNearGrad", -14, -22, 16, 12, "FF334155", "FF0F172A")}</Fill>'
        '<Stroke thickness="1.2" join="round" name="ShoeNearStroke"><SolidColor colorValue="FF475569" name="ShoeNearStrokeCol"/></Stroke>'
    )
    shoe_far_paint = (
        f'<Fill name="ShoeFarFill">{grad("ShoeFarGrad", -14, -22, 16, 12, "FF1E293B", "FF090D16")}</Fill>'
        '<Stroke thickness="1.1" join="round" name="ShoeFarStroke"><SolidColor colorValue="FF334155" name="ShoeFarStrokeCol"/></Stroke>'
    )

    # Local Thigh Geometry: (0,0) = HIP, +X = toward KNEE (length L_THIGH).
    # Since thigh_ang is in [-1.35 rad, -0.82 rad] (-77 deg to -47 deg),
    # local -Y points UP-LEFT (anterior/top surface of the thigh: Quadriceps femoris!)
    # and local +Y points DOWN-RIGHT (posterior/bottom surface of the thigh: Hamstrings & Glute insertion!).
    def make_thigh_pts(l_t):
        return [
            (-10.0, -10.0), (14.0, -19.5), (46.0, -18.5), (74.0, -13.5),
            (l_t + 4.0, -8.5), (l_t + 6.0, 2.0), (l_t - 2.0, 10.5),
            (64.0, 14.5), (32.0, 18.5), (6.0, 17.5), (-12.0, 8.0),
        ]

    # Anterior Quadriceps heads in local Thigh coordinates (-Y side):
    def make_rectus_pts(l_t):
        return [
            (12.0, -13.5), (36.0, -18.8), (64.0, -16.8), (l_t - 6.0, -10.5),
            (l_t - 8.0, -4.5), (56.0, -7.5), (26.0, -7.8),
        ]

    def make_vastus_lat_pts(l_t):
        return [
            (16.0, -7.5), (44.0, -9.8), (72.0, -7.8), (l_t - 8.0, -2.5),
            (68.0, 3.8), (38.0, 4.2), (16.0, 1.0),
        ]

    def make_vmo_pts(l_t):
        return [
            (62.0, -12.0), (78.0, -12.5), (l_t - 2.0, -6.5),
            (l_t - 4.0, 1.5), (72.0, 1.0), (60.0, -4.5),
        ]

    def make_hamstring_pts(l_t):
        return [
            (14.0, 5.5), (44.0, 5.0), (72.0, 4.5), (l_t - 8.0, 8.5),
            (62.0, 13.8), (32.0, 16.5), (12.0, 13.5),
        ]

    def make_shorts_leg_pts():
        return [
            (-14.0, -13.0), (24.0, -19.8), (32.0, -18.5),
            (30.0, 18.5), (4.0, 18.5), (-14.0, 10.0),
        ]

    # Local Shin Geometry: (0,0) = KNEE, +X = toward ANKLE (length L_SHIN).
    # Local -Y is ANTERIOR/TOP shin crest; local +Y is POSTERIOR/BOTTOM calf (Gastrocnemius).
    def make_shin_pts(l_s):
        return [
            (-7.0, -7.5), (14.0, -9.0), (48.0, -7.2), (l_s - 4.0, -5.5),
            (l_s + 3.0, 0.0), (l_s - 4.0, 6.2), (56.0, 8.8),
            (28.0, 15.2), (10.0, 12.8), (-6.0, 6.5),
        ]

    def make_calf_pts():
        return [
            (10.0, 2.0), (30.0, 1.8), (52.0, 3.5),
            (46.0, 9.8), (26.0, 14.2), (10.0, 11.0),
        ]

    # Athletic Shoe / Foot planted flat against the -126 deg sled footplate:
    # In world space, the footplate surface goes from Up-Left (-0.5878, -0.8090) to Down-Right (+0.5878, +0.8090),
    # and the shoe sole presses into the footplate toward Up-Right (+0.8090, -0.5878).
    # Relative to ANKLE (0,0), the heel rests at (+7, +9) and the toe points Up-Left to (-12, -22) along the footplate!
    shoe_pts = [
        (-6.0, 6.0), (6.5, 9.5), (11.5, 5.5),
        (-6.5, -19.5), (-14.5, -21.0), (-16.5, -13.5), (-9.5, -2.0),
    ]
    sole_pts = [
        (7.5, 9.0), (12.0, 5.5), (-6.0, -19.5), (-9.5, -17.0),
    ]

    out = [f'{ind}<Node name="DynamicLegsGroup">']

    # Note: In Rive RML, earlier children in a <Node> render ON TOP of later children.
    # ==================== 1. FOREGROUND: NEAR (RIGHT) LEG ====================
    # 1A. Near Athletic Shoe (planted flat against the sled footplate at ankle_near)
    out.append(
        f'{i2}<Node x="{f(p0["ankle_near"][0])}" y="{f(p0["ankle_near"][1])}" name="NearFootNode" id="{near_foot_id}">'
    )
    out.append(poly_shape(i3, "NearShoeSole", sole_pts, solid("NearSole", "FFCBD5E1"), radius=1.2))
    out.append(stroke_shape(i3, "NearShoeLaces", [(-11.0, -11.0), (-6.5, -5.0)], 1.3, "FF94A3B8", 0.0))
    out.append( smooth_shape(i3, "NearShoeBody", shoe_pts, shoe_near_paint))
    out.append(f"{i2}</Node>")

    # 1B. Near Lower Leg / Shin (anchored at knee_near, rotating by shin_ang_near)
    out.append(
        f'{i2}<Node x="{f(p0["knee_near"][0])}" y="{f(p0["knee_near"][1])}" '
        f'rotation="{f(p0["shin_ang_near"])}" name="NearShinNode" id="{near_shin_id}">'
    )
    out.append(stroke_shape(i3, "NearTibialisCrest", [(12.0, -3.5), (46.0, -3.2), (76.0, -2.0)], 1.25, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, "NearShinHi", [(10.0, -6.2), (46.0, -5.2), (76.0, -3.5)], 2.5, HIGHLIGHT, 2.6))
    out.append(smooth_shape(i3, "NearGastrocnemius", make_calf_pts(), muscle_paint_fn("NearCalf", secondary_t, 0.95)))
    out.append(stroke_shape(i3, "NearCalfShadow", [(12.0, 10.5), (30.0, 13.5), (54.0, 7.5)], 2.8, CORE_SHADOW, 2.8))
    out.append(smooth_shape(i3, "NearShinBase", make_shin_pts(L_SHIN_NEAR), skin_fill("NearShin", -9, 15, SKIN)))
    out.append(f"{i2}</Node>")

    # 1C. Near Thigh & Glowing Quadriceps / Glutes / Shorts Cuff (anchored at HIP_NEAR)
    out.append(
        f'{i2}<Node x="{f(HIP_NEAR[0])}" y="{f(HIP_NEAR[1])}" '
        f'rotation="{f(p0["thigh_ang_near"])}" name="NearThighNode" id="{near_thigh_id}">'
    )
    # Compression shorts leg cuff at the proximal hip end of the thigh (drawn on top of proximal thigh muscles)
    out.append(stroke_shape(i3, "NearShortsHem", [(29.0, -17.5), (30.0, 0.0), (28.0, 17.5)], 1.5, "800F172A", 0.5))
    out.append(
        smooth_shape(
            i3,
            "NearGluteMax",
            [(-10.0, 0.0), (18.0, 2.0), (26.0, 15.5), (4.0, 17.8), (-12.0, 9.5)],
            muscle_paint_fn("NearGlute", glute_primary_t, 1.0),
        )
    )
    out.append(smooth_shape(i3, "NearShortsCuff", make_shorts_leg_pts(), skin_fill("NearShorts", -19, 19, SHORTS)))
    # Quadriceps bipennate fiber striations & specular highlight
    out.append(stroke_shape(i3, "NearQuadStria1", [(34.0, -13.0), (56.0, -12.0), (76.0, -8.5)], 1.05, "807F1D1D", 0.3))
    out.append(stroke_shape(i3, "NearQuadStria2", [(36.0, -4.0), (58.0, -3.5), (76.0, -1.5)], 1.05, "807F1D1D", 0.3))
    out.append(stroke_shape(i3, "NearQuadHi", [(32.0, -15.5), (56.0, -14.5), (78.0, -10.0)], 2.4, HIGHLIGHT, 2.5))
    # 3 Superficial Quadriceps Heads + Posterior Hamstrings
    out.append(smooth_shape(i3, "NearVMO", make_vmo_pts(L_THIGH_NEAR), muscle_paint_fn("NearVMO", quad_primary_t, 1.0)))
    out.append(smooth_shape(i3, "NearVastusLateralis", make_vastus_lat_pts(L_THIGH_NEAR), muscle_paint_fn("NearVL", quad_primary_t, 1.05)))
    out.append(smooth_shape(i3, "NearRectusFemoris", make_rectus_pts(L_THIGH_NEAR), muscle_paint_fn("NearRF", quad_primary_t, 1.1)))
    out.append(smooth_shape(i3, "NearHamstrings", make_hamstring_pts(L_THIGH_NEAR), muscle_paint_fn("NearHam", secondary_t, 0.95)))
    out.append(smooth_shape(i3, "NearThighBase", make_thigh_pts(L_THIGH_NEAR), skin_fill("NearThigh", -19, 19, SKIN)))
    out.append(f"{i2}</Node>")

    # ==================== 2. BACKGROUND: FAR (LEFT) LEG ====================
    # 2A. Far Athletic Shoe (planted at ankle_far, showing shoulder-width stance)
    out.append(
        f'{i2}<Node x="{f(p0["ankle_far"][0])}" y="{f(p0["ankle_far"][1])}" name="FarFootNode" id="{far_foot_id}">'
    )
    out.append(poly_shape(i3, "FarShoeSole", sole_pts, solid("FarSole", "FF94A3B8"), radius=1.2))
    out.append(smooth_shape(i3, "FarShoeBody", shoe_pts, shoe_far_paint))
    out.append(f"{i2}</Node>")

    # 2B. Far Lower Leg / Shin (anchored at knee_far)
    out.append(
        f'{i2}<Node x="{f(p0["knee_far"][0])}" y="{f(p0["knee_far"][1])}" '
        f'rotation="{f(p0["shin_ang_far"])}" name="FarShinNode" id="{far_shin_id}">'
    )
    out.append(stroke_shape(i3, "FarShinHi", [(10.0, -5.8), (44.0, -4.8), (72.0, -3.2)], 2.0, HIGHLIGHT, 2.2))
    out.append(smooth_shape(i3, "FarGastrocnemius", make_calf_pts(), muscle_paint_fn("FarCalf", secondary_t, 0.9)))
    out.append(smooth_shape(i3, "FarShinBase", make_shin_pts(L_SHIN_FAR), skin_fill("FarShin", -9, 15, SKIN_FAR)))
    out.append(f"{i2}</Node>")

    # 2C. Far Thigh & Glowing Quadriceps (anchored at HIP_FAR)
    out.append(
        f'{i2}<Node x="{f(HIP_FAR[0])}" y="{f(HIP_FAR[1])}" '
        f'rotation="{f(p0["thigh_ang_far"])}" name="FarThighNode" id="{far_thigh_id}">'
    )
    out.append(smooth_shape(i3, "FarShortsCuff", make_shorts_leg_pts(), skin_fill("FarShorts", -19, 19, SHORTS_FAR)))
    out.append(smooth_shape(i3, "FarVMO", make_vmo_pts(L_THIGH_FAR), muscle_paint_fn("FarVMO", quad_primary_t, 0.95)))
    out.append(smooth_shape(i3, "FarRectusFemoris", make_rectus_pts(L_THIGH_FAR), muscle_paint_fn("FarRF", quad_primary_t, 1.0)))
    out.append(smooth_shape(i3, "FarThighBase", make_thigh_pts(L_THIGH_FAR), skin_fill("FarThigh", -19, 19, SKIN_FAR)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. Reclined Upper Body, Neutral Spine & Stabilizer Grip Arms
def reclined_upper_body():
    """Canonical 3/4 CommunityFitness upper body reclined at 45 degrees against the backrest pad:
    - Pelvis & glutes seated deeply in the angled bucket seat with dark athletic shorts
    - Neutral spine with sculpted pectorals, 6-pack abs, and external obliques
    - Volumetric 3/4 head facing up-right toward the footplate
    - Foreground arm & hand extending down along the hip to grip the seat side stabilizer handle"""
    ind = "        "
    i2 = ind + "    "

    # Near (Right) Arm gripping the lower seat stabilizer handle at (236, 248)
    grip_paint = (
        '<Fill name="SideGripFill"><SolidColor colorValue="FF090D16" name="SideGripCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="SideGripStroke"><SolidColor colorValue="FF475569" name="SideGripStrokeCol"/></Stroke>'
    )
    near_delt_pts = [
        (182.0, 152.0), (196.0, 148.0), (206.0, 158.0),
        (202.0, 174.0), (188.0, 176.0), (178.0, 164.0),
    ]
    near_ua_pts = [
        (186.0, 166.0), (202.0, 168.0), (214.0, 206.0),
        (198.0, 210.0), (188.0, 188.0),
    ]
    near_fa_pts = [
        (200.0, 202.0), (214.0, 202.0), (236.0, 238.0),
        (224.0, 244.0), (208.0, 224.0),
    ]
    near_hand_pts = [
        (226.0, 236.0), (240.0, 238.0), (240.0, 250.0), (226.0, 248.0),
    ]

    # Pelvis & Athletic Compression Shorts seated deeply in the bucket seat corner
    pelvis_shorts_pts = [
        (224.0, 188.0), (248.0, 184.0), (272.0, 198.0),
        (266.0, 228.0), (242.0, 234.0), (218.0, 210.0),
    ]

    # Reclined Torso (neutral spine from shoulder (186, 154) down-right to pelvis (246, 214))
    torso_pts = [
        (178.0, 154.0), (198.0, 138.0), (222.0, 152.0),
        (242.0, 172.0), (254.0, 192.0), (238.0, 218.0),
        (212.0, 206.0), (190.0, 182.0),
    ]
    pec_near_pts = [
        (188.0, 152.0), (206.0, 140.0), (222.0, 152.0),
        (216.0, 168.0), (200.0, 170.0), (188.0, 162.0),
    ]
    pec_paint = (
        '<Fill name="PecFill"><SolidColor colorValue="140F172A" name="PecCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="PecStroke"><SolidColor colorValue="380F172A" name="PecStrokeCol"/></Stroke>'
    )
    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1A0F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="AbsEdge"><SolidColor colorValue="400F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        [(214.0, 156.0), (224.0, 164.0), (217.0, 172.0), (207.0, 164.0)],
        [(224.0, 166.0), (234.0, 174.0), (227.0, 182.0), (217.0, 174.0)],
        [(234.0, 176.0), (244.0, 184.0), (237.0, 192.0), (227.0, 184.0)],
    ]

    # Volumetric 3/4 Head & Muscular Neck resting in neutral alignment at top-left of backrest
    head_pts = [
        (154.0, 114.0), (164.0, 110.0), (176.0, 114.0), (182.0, 122.0),
        (180.0, 130.0), (174.0, 138.0), (164.0, 142.0), (154.0, 138.0),
        (148.0, 128.0), (149.0, 119.0),
    ]
    hair_pts = [
        (150.0, 130.0), (147.5, 120.0), (153.0, 111.5), (165.0, 109.0),
        (173.0, 112.5), (166.0, 116.5), (158.0, 121.0), (154.0, 128.0),
    ]
    neck_pts = [
        (166.0, 136.0), (178.0, 132.0), (194.0, 142.0),
        (184.0, 158.0), (164.0, 146.0),
    ]

    out = [f'{ind}<Node name="ReclinedUpperBody">']

    # 1. Foreground: Near (Right) Arm & Hand Gripping Seat Stabilizer Handle
    out.append(poly_shape(i2, "SeatStabilizerHandle", [(230, 248), (244, 232), (249, 236), (235, 252)], grip_paint, radius=2.0))
    out.append(stroke_shape(i2, "NearKnuckles", [(230.0, 242.0), (238.0, 243.0)], 1.0, SOFT_SHADOW, 0.0))
    out.append(smooth_shape(i2, "NearHand", near_hand_pts, skin_fill("NearHand", 236, 250, SKIN)))
    out.append(stroke_shape(i2, "NearForearmHi", [(208.0, 206.0), (220.0, 222.0), (230.0, 236.0)], 2.2, HIGHLIGHT, 2.4))
    out.append(smooth_shape(i2, "NearForearm", near_fa_pts, skin_fill("NearFA", 202, 244, SKIN)))
    out.append(stroke_shape(i2, "NearBicepsHi", [(196.0, 172.0), (204.0, 188.0), (208.0, 202.0)], 2.4, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i2, "NearUpperArm", near_ua_pts, skin_fill("NearUA", 166, 210, SKIN)))
    out.append(stroke_shape(i2, "NearDeltHi", [(188.0, 154.0), (198.0, 158.0), (196.0, 170.0)], 2.4, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i2, "NearDeltoid", near_delt_pts, skin_fill("NearDelt", 148, 176, SKIN)))

    # 2. Midground: Pelvis Shorts, Reclined Torso, Pectorals & 6-Pack Abs
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts_pts, skin_fill("PelvisShorts", 184, 234, SHORTS, x0=218, x1=272)))
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "ChestHighlight", [(198.0, 144.0), (214.0, 152.0)], 2.4, HIGHLIGHT, 2.8))
    out.append(smooth_shape(i2, "PectoralNear", pec_near_pts, pec_paint))
    out.append(stroke_shape(i2, "TorsoRibShadow", [(196.0, 176.0), (214.0, 192.0), (232.0, 206.0)], 3.0, CORE_SHADOW, 3.0))
    out.append(stroke_shape(i2, "TorsoAnteriorHi", [(204.0, 144.0), (224.0, 160.0), (242.0, 178.0)], 3.5, HIGHLIGHT, 4.0))
    out.append(smooth_shape(i2, "ReclinedTorso", torso_pts, skin_fill("Torso", 138, 218, SKIN, x0=178, x1=254)))

    # 3. Volumetric 3/4 Head & Muscular Neck
    out.append(smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 148, 109, 173, 130, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i2, "Ear", 162.0, 132.0, 5.2, 7.8, solid("Ear", "FFA3B1C4"), rot_deg=-28.0))
    out.append(stroke_shape(i2, "BrowShade", [(172.0, 116.5), (176.5, 118.5)], 1.4, "590F172A", 0.6))
    out.append(stroke_shape(i2, "EyeLine", [(171.0, 118.8), (174.5, 120.2)], 1.1, "730F172A", 0.4))
    out.append(stroke_shape(i2, "MouthLine", [(175.0, 128.5), (178.5, 130.0)], 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i2, "JawShadow", [(164.0, 139.0), (173.0, 137.5), (178.5, 132.0)], 2.4, CORE_SHADOW, 2.2))
    out.append(stroke_shape(i2, "HeadHi", [(158.0, 114.0), (168.0, 113.0), (175.0, 117.0)], 2.8, HIGHLIGHT, 3.2))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill("Head", 110, 142, SKIN, x0=148, x1=182)))
    out.append(stroke_shape(i2, "SCMLine", [(166.0, 136.0), (178.0, 144.0), (188.0, 150.0)], 1.5, SOFT_SHADOW, 1.4))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", 132, 158, SKIN)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    legs_xml = build_leg_assemblies()
    upper_body_xml = reclined_upper_body()
    machine_xml = machine_frame_and_sled()

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
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="LegPress" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Dynamic 2-Bone IK Legs (Shoes on Sled, Shins, Thighs & Glowing Quadriceps/Glutes) -->
{legs_xml}

        <!-- 2. Midground: Reclined Athlete Upper Body (Neutral Spine, Head, Pectorals, Abs & Stabilizer Grip Arm) -->
{upper_body_xml}

        <!-- 3. 45-Degree Plate-Loaded Leg Press Machine Frame, Guide Rails & Sliding Sled Carriage -->
{machine_xml}

        <!-- 4. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="326" y="{f(FLOOR - 2)}" scaleX="1.65" scaleY="0.10" name="MachineShadow">
            <Ellipse width="230" height="230" name="MachineShadowEllipse"/>
            <Fill name="MachineShadowFill"><RadialGradient startX="0" startY="0" endX="115" endY="0" name="MachineShadowGrad">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="LegPress" id="0:60">
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
    (BUILD / "leg_press.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (40, "frame_mid"), (72, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(716, 2, 272))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
