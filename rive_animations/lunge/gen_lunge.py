#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive 7.3 scene for Dumbbell Lunge (id: 'lunge').

Uses our canonical 3/4 side-left CommunityFitness mannequin (volumetric 3/4 head with hair/ear/brow/eye/mouth,
muscular neck, sculpted pectorals, 6-pack abs, serratus anterior, deltoids/biceps/forearms holding a pair of
cast-iron dumbbells in neutral hammer grip, dark athletic compression shorts, sculpted quadriceps/glutes/
hamstrings/adductors/calves, and bare feet planted on FLOOR = 300.0).

Matches the 2-panel 3/4 side-left Dumbbell Lunge reference illustration (WeightTraining.guide):
  - Left Panel (f = 0 & f = 180, d = 0.0 — Standing Tall Start Position):
    * Athlete stands tall facing left (-X) with feet side-by-side on FLOOR = 300.0, holding dumbbells at his
      sides in a neutral hammer grip.
  - Right Panel (f = 76, d = 1.0 — Deep Forward Dumbbell Lunge):
    * Front (right) leg steps forward-left so the front thigh is horizontal (~90 deg knee flexion) and the
      front shin is vertical with the foot planted flat on the floor.
    * Rear (left) leg pivots onto the ball of the rear foot with the heel raised vertically and the rear knee
      hovering just above the floor (~y = 287), while the upright torso descends straight down between the hips
      with the near dumbbell hanging vertically beside the hip.
  - Highlighted Target Muscle Groups (all 8 muscles labeled in the reference, pulsing from warm orange to crimson):
    * Front Leg: Rectus femoris, Vastus lateralis, Hamstrings, Soleus
    * Rear Leg:  Gluteus maximus, Vastus medialis, Adductor magnus, Gastrocnemius, Soleus

Run:
    python3 gen_lunge.py            # writes scene.rml
    python3 gen_lunge.py --publish  # compiles assets/animations/lunge.riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/lunge.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/lunge.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 180  # 3.0s seamless 60fps loop
STEP = 2

# Segment Lengths for Exact 2-Bone IK (Hip -> Knee -> Ankle)
THIGH_LEN = 76.0
SHIN_LEN = 76.0
UPPER_ARM = 48.0
FOREARM = 44.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("B3475569", "C22B3649", "D1172033")
SHORTS_FAR = ("BF334155", "CC1E293B", "D90F172A")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "4D0F172A"

# Target Muscle Heat Colors: warm orange (#FFF97316) -> intense crimson (#FFF43F5E)
MUSCLE_LOW = (0xD9, 0xF9, 0x73, 0x16)
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


EASE_LUNGE = cubic_bezier(0.38, 0.0, 0.24, 1.0)
EASE_RETURN = cubic_bezier(0.42, 0.0, 0.36, 1.0)


def lunge_progress(frame):
    """Returns dumbbell lunge progress d in [0.0, 1.0] across 180 frames:
    - 0..16:    Standing tall hold (d = 0.0: feet together, dumbbells at sides)
    - 16..72:   Step forward-left & descend into deep 90/90 lunge (d: 0.0 -> 1.0)
    - 72..94:   Bottom isometric lunge hold (d = 1.0: front thigh horizontal, rear knee near floor)
    - 94..156:  Concentric drive back up to standing start position (d: 1.0 -> 0.0)
    - 156..180: Standing tall hold (d = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 16:
        return 0.0
    if fr <= 72:
        return EASE_LUNGE((fr - 16) / 56.0)
    if fr <= 94:
        return 1.0
    if fr <= 156:
        return 1.0 - EASE_RETURN((fr - 94) / 62.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def solve_ik_left(hip, ankle, l1, l2):
    """2-bone IK from hip -> knee -> ankle for a leftward-facing (-X) athlete.
    Using +acos(cos_a) bends the knee toward (+pi/2 .. +pi), i.e. forward-left (-X, +Y)."""
    dx = ankle[0] - hip[0]
    dy = ankle[1] - hip[1]
    d = max(1.0, min(l1 + l2 - 0.2, math.hypot(dx, dy)))
    base_ang = math.atan2(dy, dx)
    cos_a = max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2.0 * l1 * d)))
    thigh_ang = base_ang + math.acos(cos_a)
    knee = (hip[0] + l1 * math.cos(thigh_ang), hip[1] + l1 * math.sin(thigh_ang))
    shin_ang = math.atan2(ankle[1] - knee[1], ankle[0] - knee[0])
    return thigh_ang, knee, shin_ang


def pose(d):
    """Compute Dumbbell Lunge joint transforms at progress d in [0.0, 1.0]."""
    # Hips stand tall at d=0.0 (330, 141) and drop vertically into the lunge at d=1.0 (334, 214)
    hip_near = (lerp(330.0, 334.0, d), lerp(141.0, 214.0, d))
    hip_far = (lerp(320.0, 322.0, d), lerp(140.0, 212.0, d))

    # Front (Far / Right) Leg: steps forward-left from (318, 290) to (246, 290) with a natural step lift
    step_lift = -14.0 * math.sin(math.pi * d)
    ankle_front = (lerp(318.0, 246.0, d), 290.0 + step_lift)
    thigh_front_ang, knee_front, shin_front_ang = solve_ik_left(
        hip_far, ankle_front, THIGH_LEN, SHIN_LEN
    )

    # Rear (Near / Left) Leg: pivots back-right from standing (328, 290) to raised-heel lunge (426, 273)
    ankle_rear = (lerp(328.0, 426.0, d), lerp(290.0, 273.0, d))
    thigh_rear_ang, knee_rear, shin_rear_ang = solve_ik_left(
        hip_near, ankle_rear, THIGH_LEN, SHIN_LEN
    )
    # Rear foot rotates counter-clockwise (-62 deg at d=1) so the toes (-X) plant down on FLOOR=300 and the heel (+X) rises up!
    rear_foot_rot = math.radians(lerp(0.0, -62.0, d))

    # Upright Torso & Head: stays tall and braced (slight 3 deg athletic lean at bottom)
    torso_lean = math.radians(lerp(0.0, -3.0, d))

    # Near & Far Arms: hang vertically with dumbbells at sides
    shoulder_near = (hip_near[0] + 4.0, hip_near[1] - 78.0)
    shoulder_far = (hip_far[0] - 8.0, hip_far[1] - 78.0)

    return {
        "d": d,
        "hip_near": hip_near,
        "hip_far": hip_far,
        "shoulder_near": shoulder_near,
        "shoulder_far": shoulder_far,
        "torso_lean": torso_lean,
        "ankle_front": ankle_front,
        "knee_front": knee_front,
        "thigh_front_ang": thigh_front_ang,
        "shin_front_ang": shin_front_ang,
        "ankle_rear": ankle_rear,
        "knee_rear": knee_rear,
        "thigh_rear_ang": thigh_rear_ang,
        "shin_rear_ang": shin_rear_ang,
        "rear_foot_rot": rear_foot_rot,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(lunge_progress(fr)) for fr in FRAMES}


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


def muscle_paint_fn(name, fn_t, line=0.95):
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


# ---------------------------------------------------------------- 1. Dumbbell Arm Helper (Near & Far Arms)
def build_dumbbell_arm(indent, prefix, is_far):
    """Vertical hanging arm holding a 3D multi-plate cast-iron dumbbell in neutral hammer grip,
    matching the 3/4 side-left Dumbbell Lunge reference illustration."""
    i2 = indent + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if is_far else SKIN
    arm_id = nid()
    sh_key = "shoulder_far" if is_far else "shoulder_near"
    key_double(arm_id, 13, lambda p: p[sh_key][0])
    key_double(arm_id, 14, lambda p: p[sh_key][1])
    p0 = POSES[0]

    # Arm hangs straight down (+Y) from shoulder anchor (0,0):
    # -X is ANTERIOR (left/front of body: anterior deltoid, biceps, thumb/front dumbbell stack)
    # +X is POSTERIOR (right/back of body: posterior deltoid, triceps, rear dumbbell stack)
    delt_pts = [
        (-11.5, -2.0), (-2.0, -11.5), (10.5, -9.0),
        (12.5, 4.0), (8.0, 18.5), (-3.0, 19.5), (-12.0, 9.0),
    ]
    ua_pts = [
        (-9.5, 8.0), (9.5, 8.0), (10.2, 28.0),
        (7.5, 48.0), (0.0, 52.0), (-7.8, 48.0), (-10.8, 28.0),
    ]
    fa_pts = [
        (-7.8, 46.0), (7.5, 46.0), (6.5, 68.0),
        (4.8, 88.0), (-5.2, 88.0), (-8.5, 66.0),
    ]
    gy = 92.0
    hand_pts = [
        (-6.0, gy - 5.5), (5.5, gy - 5.5), (6.2, gy + 5.5),
        (0.0, gy + 7.2), (-6.2, gy + 5.5),
    ]

    plate_face = (
        f'<Fill name="{prefix}PlateFaceFill">{grad(prefix + "PlateGrad", -8, -16, 8, 16, "FF334155", "FF0F172A")}</Fill>'
        f'<Stroke thickness="1.15" name="{prefix}PlateRim"><SolidColor colorValue="FF64748B" name="{prefix}PlateRimCol"/></Stroke>'
    )
    plate_side = solid(prefix + "PlateSide", "FF090D16")
    collar_paint = (
        f'<Fill name="{prefix}CollarFill">{grad(prefix + "CollarGrad", -4, -3, 4, 3, "FFF8FAFC", "FF64748B")}</Fill>'
        f'<Stroke thickness="0.9" name="{prefix}CollarStroke"><SolidColor colorValue="FF334155" name="{prefix}CollarStrokeCol"/></Stroke>'
    )

    out = [
        f'{indent}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" name="{prefix}DumbbellArmNode" id="{arm_id}">'
    ]

    # Note: In Rive RML, earlier children render ON TOP of later children.
    # 1. Front Dumbbell Plate Stack (anterior -X side of the grip, in front of the hand)
    out.append(ellipse_shape(i2, f"{prefix}DbFrontSpinlock", -21.0, gy + 1.2, 5.5, 8.0, collar_paint))
    out.append(ellipse_shape(i2, f"{prefix}DbFrontPlate3Face", -18.0, gy + 1.0, 11.0, 22.0, plate_face))
    out.append(ellipse_shape(i2, f"{prefix}DbFrontPlate2Face", -14.8, gy + 0.8, 13.0, 27.0, plate_face))
    out.append(ellipse_shape(i2, f"{prefix}DbFrontPlate2Side", -13.2, gy + 0.8, 13.0, 27.0, plate_side))
    out.append(ellipse_shape(i2, f"{prefix}DbFrontPlate1Face", -10.8, gy + 0.4, 14.5, 31.0, plate_face))
    out.append(ellipse_shape(i2, f"{prefix}DbFrontPlate1Side", -9.2, gy + 0.4, 14.5, 31.0, plate_side))

    # 2. Hand & Knuckles gripping the chrome handle + Forearm + Upper Arm + Deltoid
    out.append(stroke_shape(i2, f"{prefix}Knuckle1", [(-3.0, gy + 4.5), (-3.0, gy - 2.0)], 1.0, SOFT_SHADOW, 0.0))
    out.append(stroke_shape(i2, f"{prefix}Knuckle2", [(0.5, gy + 4.8), (0.5, gy - 2.0)], 1.0, SOFT_SHADOW, 0.0))
    out.append(stroke_shape(i2, f"{prefix}Knuckle3", [(3.5, gy + 4.5), (3.5, gy - 2.0)], 1.0, SOFT_SHADOW, 0.0))
    out.append(smooth_shape(i2, f"{prefix}Hand", hand_pts, skin_fill(prefix + "Hand", gy - 6, gy + 7, skin)))
    out.append(stroke_shape(i2, f"{prefix}DbHandleBar", [(-10.0, gy + 0.4), (10.5, gy - 0.4)], 4.8, "FF94A3B8", 0.0))

    if not is_far:
        out.append(stroke_shape(i2, f"{prefix}DeltAnteriorGroove", [(-6.5, 4.0), (-4.0, 14.0)], 1.15, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i2, f"{prefix}DeltPosteriorGroove", [(5.5, 4.0), (4.0, 14.0)], 1.15, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i2, f"{prefix}DeltHi", [(-4.0, -5.0), (-6.0, 5.0), (-3.5, 14.0)], 2.8, HIGHLIGHT, 3.2))
    out.append(smooth_shape(i2, f"{prefix}Deltoid", delt_pts, skin_fill(prefix + "Delt", -12, 20, skin)))

    if not is_far:
        out.append(stroke_shape(i2, f"{prefix}ForearmBrachioLine", [(-1.5, 50.0), (-1.0, 70.0), (-0.5, 84.0)], 1.15, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i2, f"{prefix}ForearmHi", [(-5.0, 52.0), (-4.2, 70.0), (-3.0, 84.0)], 2.4, HIGHLIGHT, 2.8))
    out.append(stroke_shape(i2, f"{prefix}ForearmSh", [(4.5, 52.0), (4.0, 70.0), (2.8, 84.0)], 3.2, CORE_SHADOW, 3.2))
    out.append(smooth_shape(i2, f"{prefix}Forearm", fa_pts, skin_fill(prefix + "FA", 46, 88, skin)))

    if not is_far:
        out.append(stroke_shape(i2, f"{prefix}BicepsGroove", [(-1.5, 18.0), (-1.5, 34.0), (-1.0, 44.0)], 1.2, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i2, f"{prefix}UpperArmHi", [(-6.0, 16.0), (-5.8, 30.0), (-4.5, 44.0)], 2.6, HIGHLIGHT, 3.0))
    out.append(stroke_shape(i2, f"{prefix}UpperArmSh", [(6.2, 16.0), (6.0, 32.0), (4.8, 44.0)], 3.8, CORE_SHADOW, 3.8))
    out.append(smooth_shape(i2, f"{prefix}UpperArm", ua_pts, skin_fill(prefix + "UA", 8, 52, skin)))

    # 3. Rear Dumbbell Plate Stack (posterior +X side of the grip, behind the hand & forearm)
    out.append(ellipse_shape(i2, f"{prefix}DbRearPlate1Face", 10.5, gy - 0.4, 14.5, 31.0, plate_face))
    out.append(ellipse_shape(i2, f"{prefix}DbRearPlate1Side", 12.0, gy - 0.4, 14.5, 31.0, plate_side))
    out.append(ellipse_shape(i2, f"{prefix}DbRearPlate2Face", 14.2, gy - 0.8, 13.0, 27.0, plate_face))
    out.append(ellipse_shape(i2, f"{prefix}DbRearPlate2Side", 15.8, gy - 0.8, 13.0, 27.0, plate_side))
    out.append(ellipse_shape(i2, f"{prefix}DbRearPlate3Face", 17.5, gy - 1.0, 11.0, 22.0, plate_face))
    out.append(ellipse_shape(i2, f"{prefix}DbRearSpinlock", 20.5, gy - 1.2, 5.5, 8.0, collar_paint))

    out.append(f"{indent}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 2. Rear (Near / Left) Leg Rig
def build_rear_near_leg():
    """Rear (Near / Left) Leg in Dumbbell Lunge:
    - Anchored at hip_near(d), rotating by thigh_rear_ang(d)
    - Highlights Gluteus maximus, Vastus medialis, Adductor magnus, Gastrocnemius, and Soleus
    - Rear foot pivots onto the ball/toes on FLOOR = 300.0 with heel raised vertically at d = 1.0."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    thigh_id, shin_id, foot_id = nid(), nid(), nid()
    key_double(thigh_id, 13, lambda p: p["hip_near"][0])
    key_double(thigh_id, 14, lambda p: p["hip_near"][1])
    key_double(thigh_id, 15, lambda p: p["thigh_rear_ang"])

    key_double(shin_id, 13, lambda p: p["knee_rear"][0])
    key_double(shin_id, 14, lambda p: p["knee_rear"][1])
    key_double(shin_id, 15, lambda p: p["shin_rear_ang"])

    key_double(foot_id, 13, lambda p: p["ankle_rear"][0])
    key_double(foot_id, 14, lambda p: p["ankle_rear"][1])
    key_double(foot_id, 15, lambda p: p["rear_foot_rot"])

    p0 = POSES[0]

    def primary_t(p):
        return 0.42 + 0.58 * (p["d"] ** 0.78)

    def secondary_t(p):
        return 0.34 + 0.56 * (p["d"] ** 0.82)

    # In RearThigh local space (+x from Hip(0) -> Knee(76)):
    # Since thigh_rear_ang is in [+73.5 deg, +92 deg] (pointing downward),
    # local +y points LEFT (-X: anterior surface of thigh: Quadriceps / Vastus medialis!)
    # local -y points RIGHT (+X: posterior surface of thigh: Gluteus maximus, Adductor magnus, Hamstrings!)
    thigh_pts = [
        (-16.0, 12.0), (8.0, 18.0), (36.0, 17.5), (62.0, 13.5),
        (78.0, 6.0), (78.0, -5.5), (62.0, -12.0), (34.0, -16.5),
        (8.0, -18.5), (-16.0, -14.5),
    ]
    shorts_cuff_pts = [
        (-18.0, 13.5), (22.0, 18.8), (24.0, -18.2), (-18.0, -16.0),
    ]
    # Gluteus maximus on the upper-posterior hip (-y side, visible at the rear of the hip)
    glute_pts = [
        (-18.0, -2.0), (14.0, -4.0), (16.0, -17.5), (-6.0, -18.5), (-18.0, -12.0),
    ]
    # Vastus medialis teardrop on the anterior-lower aspect (+y side above the knee)
    vastus_med_pts = [
        (24.0, 15.5), (48.0, 15.2), (66.0, 11.5), (68.0, 4.5),
        (50.0, 4.0), (26.0, 6.5),
    ]
    # Adductor magnus along the posterior/medial aspect (-y side behind the femur)
    adductor_pts = [
        (18.0, -3.5), (44.0, -3.2), (64.0, -5.5),
        (58.0, -11.5), (34.0, -15.5), (16.0, -15.0),
    ]

    # In RearShin local space (+x from Knee(0) -> Ankle(76)):
    # At d=0 (+72 deg) and d=1 (-11 deg), local -y is the POSTERIOR/UPPER calf (Gastrocnemius & Soleus)
    # and local +y is the ANTERIOR/LOWER shin (Tibia)!
    shin_pts = [
        (-8.0, 6.8), (18.0, 7.2), (48.0, 6.2), (74.0, 4.5),
        (78.0, 0.0), (72.0, -5.2), (54.0, -7.8), (34.0, -14.8),
        (16.0, -15.2), (-6.0, -7.8),
    ]
    gastroc_pts = [
        (8.0, -5.5), (24.0, -6.2), (44.0, -6.0),
        (38.0, -13.8), (18.0, -14.8), (7.0, -10.5),
    ]
    soleus_pts = [
        (36.0, -4.5), (54.0, -4.8), (66.0, -4.5),
        (58.0, -7.8), (38.0, -12.2),
    ]

    # Bare Foot facing left (-X): at rot=0, sole rests at y=+10 (FLOOR=300 when ankle_y=290);
    # at rot=+62 deg (d=1, ankle=(428, 274)), the heel rises up-right and the ball/toes plant on FLOOR=300!
    foot_pts = [
        (9.0, -2.5), (-4.0, -3.5), (-18.0, 2.5), (-28.0, 6.8),
        (-29.0, 10.0), (-14.0, 10.2), (8.0, 9.8), (11.5, 5.0),
    ]

    out = [f'{ind}<Node name="RearNearLegGroup">']

    # 1. Rear Bare Foot
    out.append(
        f'{i2}<Node x="{f(p0["ankle_rear"][0])}" y="{f(p0["ankle_rear"][1])}" '
        f'rotation="{f(p0["rear_foot_rot"])}" name="RearFootNode" id="{foot_id}">'
    )
    out.append(stroke_shape(i3, "RearFootHi", [(2.0, 0.5), (-12.0, 3.2), (-24.0, 6.8)], 2.0, HIGHLIGHT, 2.2))
    out.append(stroke_shape(i3, "RearFootSole", [(8.0, 9.2), (-10.0, 9.5), (-26.0, 9.2)], 2.0, CORE_SHADOW, 1.5))
    out.append(smooth_shape(i3, "RearFootShape", foot_pts, skin_fill("RearFoot", -4, 10, SKIN)))
    out.append(f"{i2}</Node>")

    # 2. Rear Lower Leg (Gastrocnemius & Soleus highlighted as in reference)
    out.append(
        f'{i2}<Node x="{f(p0["knee_rear"][0])}" y="{f(p0["knee_rear"][1])}" '
        f'rotation="{f(p0["shin_rear_ang"])}" name="RearShinNode" id="{shin_id}">'
    )
    out.append(ellipse_shape(i3, "RearKneeCap", 0.0, 1.0, 18.0, 16.0, skin_fill("RearKnee", -8, 8, SKIN)))
    out.append(smooth_shape(i3, "RearSoleus", soleus_pts, muscle_paint_fn("RearSoleus", secondary_t, 0.9)))
    out.append(smooth_shape(i3, "RearGastrocnemius", gastroc_pts, muscle_paint_fn("RearGastroc", primary_t, 0.95)))
    out.append(stroke_shape(i3, "RearTibiaHi", [(12.0, 4.5), (40.0, 4.2), (66.0, 3.0)], 2.6, HIGHLIGHT, 2.8))
    out.append(stroke_shape(i3, "RearCalfSh", [(12.0, -11.5), (30.0, -13.0), (52.0, -6.5)], 3.2, CORE_SHADOW, 3.2))
    out.append(smooth_shape(i3, "RearShinShape", shin_pts, skin_fill("RearShin", -15, 8, SKIN)))
    out.append(f"{i2}</Node>")

    # 3. Rear Thigh (Gluteus maximus, Vastus medialis & Adductor magnus highlighted as in reference)
    out.append(
        f'{i2}<Node x="{f(p0["hip_near"][0])}" y="{f(p0["hip_near"][1])}" '
        f'rotation="{f(p0["thigh_rear_ang"])}" name="RearThighNode" id="{thigh_id}">'
    )
    out.append(stroke_shape(i3, "RearShortsHem", [(22.0, 18.0), (23.0, 0.0), (22.0, -17.5)], 1.4, "800F172A", 0.6))
    out.append(smooth_shape(i3, "RearGluteMax", glute_pts, muscle_paint_fn("RearGlute", primary_t, 1.0)))
    out.append(smooth_shape(i3, "RearShortsCuff", shorts_cuff_pts, skin_fill("RearShorts", -18, 19, SHORTS)))
    out.append(stroke_shape(i3, "RearFasciaLine", [(20.0, 1.5), (42.0, 1.2), (62.0, 0.8)], 2.0, HIGHLIGHT, 2.0))
    out.append(smooth_shape(i3, "RearVastusMedialis", vastus_med_pts, muscle_paint_fn("RearVM", primary_t, 0.95)))
    out.append(smooth_shape(i3, "RearAdductorMagnus", adductor_pts, muscle_paint_fn("RearAdd", secondary_t, 0.95)))
    out.append(stroke_shape(i3, "RearThighSh", [(14.0, -13.5), (38.0, -12.5), (58.0, -9.0)], 3.8, CORE_SHADOW, 3.8))
    out.append(smooth_shape(i3, "RearThighShape", thigh_pts, skin_fill("RearThigh", -18, 18, SKIN)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. Front (Far / Right) Leg Rig
def build_front_far_leg():
    """Front (Far / Right) Leg stepping forward-left into the 90-degree horizontal-thigh lunge:
    - Highlights Rectus femoris, Vastus lateralis, Hamstrings, and Soleus (matching reference labels)."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    thigh_id, shin_id, foot_id = nid(), nid(), nid()
    key_double(thigh_id, 13, lambda p: p["hip_far"][0])
    key_double(thigh_id, 14, lambda p: p["hip_far"][1])
    key_double(thigh_id, 15, lambda p: p["thigh_front_ang"])

    key_double(shin_id, 13, lambda p: p["knee_front"][0])
    key_double(shin_id, 14, lambda p: p["knee_front"][1])
    key_double(shin_id, 15, lambda p: p["shin_front_ang"])

    key_double(foot_id, 13, lambda p: p["ankle_front"][0])
    key_double(foot_id, 14, lambda p: p["ankle_front"][1])

    p0 = POSES[0]

    def primary_t(p):
        return 0.44 + 0.56 * (p["d"] ** 0.75)

    def secondary_t(p):
        return 0.34 + 0.54 * (p["d"] ** 0.82)

    # In FrontThigh local space (+x from Hip(0) -> Knee(76)):
    # At d=1 (thigh_front_ang = +178.5 deg, pointing horizontally LEFT -X):
    # local +y points UP (-Y screen: top/anterior crest of the thigh -> Rectus femoris & Vastus lateralis!)
    # local -y points DOWN (+Y screen: bottom/posterior contour of the thigh -> Hamstrings!)
    thigh_pts = [
        (-16.0, 12.0), (10.0, 18.2), (38.0, 18.5), (62.0, 14.5),
        (78.0, 6.0), (78.0, -5.5), (62.0, -11.5), (36.0, -15.5),
        (10.0, -17.5), (-16.0, -13.5),
    ]
    shorts_cuff_pts = [
        (-18.0, 13.5), (20.0, 18.5), (22.0, -17.5), (-18.0, -15.0),
    ]
    # Rectus femoris (top anterior crest of the front thigh, +y local)
    rectus_pts = [
        (12.0, 17.2), (36.0, 17.8), (56.0, 14.8), (66.0, 10.5),
        (64.0, 6.0), (44.0, 7.5), (22.0, 8.2), (10.0, 9.0),
    ]
    # Vastus lateralis (mid-lateral sweep below Rectus femoris, +y local)
    vastus_lat_pts = [
        (14.0, 8.0), (36.0, 7.2), (56.0, 6.2), (65.0, 4.2),
        (60.0, -0.8), (38.0, -1.2), (16.0, -0.5),
    ]
    # Hamstrings (lower posterior belly along -y local, separated by silver IT band)
    hamstring_pts = [
        (18.0, -4.8), (42.0, -5.0), (58.0, -4.8),
        (62.0, -8.5), (46.0, -13.0), (24.0, -15.5), (14.0, -14.5),
    ]

    # In FrontShin local space (+x from Knee(0) -> Ankle(76), pointing vertically DOWN +90 deg):
    # local +y points LEFT (-X screen: straight anterior Tibia)
    # local -y points RIGHT (+X screen: posterior Calf & Soleus!)
    shin_pts = [
        (-8.0, 6.8), (18.0, 6.8), (48.0, 5.8), (74.0, 4.2),
        (78.0, 0.0), (72.0, -4.8), (54.0, -7.2), (34.0, -13.8),
        (16.0, -14.8), (-6.0, -7.5),
    ]
    soleus_pts = [
        (14.0, -4.5), (36.0, -4.8), (58.0, -4.5),
        (52.0, -8.5), (32.0, -12.8), (14.0, -11.5),
    ]

    foot_pts = [
        (9.0, -2.5), (-4.0, -3.5), (-18.0, 2.5), (-28.0, 6.8),
        (-29.0, 10.0), (-14.0, 10.2), (8.0, 9.8), (11.5, 5.0),
    ]

    out = [f'{ind}<Node name="FrontFarLegGroup">']

    # 1. Front Bare Foot planted flat on FLOOR = 300.0
    out.append(
        f'{i2}<Node x="{f(p0["ankle_front"][0])}" y="{f(p0["ankle_front"][1])}" name="FrontFootNode" id="{foot_id}">'
    )
    out.append(stroke_shape(i3, "FrontFootHi", [(2.0, 0.5), (-12.0, 3.2), (-24.0, 6.8)], 2.0, HIGHLIGHT, 2.2))
    out.append(stroke_shape(i3, "FrontFootSole", [(8.0, 9.2), (-10.0, 9.5), (-26.0, 9.2)], 2.0, CORE_SHADOW, 1.5))
    out.append(smooth_shape(i3, "FrontFootShape", foot_pts, skin_fill("FrontFoot", -4, 10, SKIN)))
    out.append(f"{i2}</Node>")

    # 2. Front Shin (with Soleus highlighted as in reference)
    out.append(
        f'{i2}<Node x="{f(p0["knee_front"][0])}" y="{f(p0["knee_front"][1])}" '
        f'rotation="{f(p0["shin_front_ang"])}" name="FrontShinNode" id="{shin_id}">'
    )
    out.append(ellipse_shape(i3, "FrontKneeCap", 0.0, 1.0, 18.0, 16.0, skin_fill("FrontKnee", -8, 8, SKIN)))
    out.append(smooth_shape(i3, "FrontSoleus", soleus_pts, muscle_paint_fn("FrontSoleus", secondary_t, 0.9)))
    out.append(stroke_shape(i3, "FrontTibiaHi", [(12.0, 4.5), (40.0, 4.2), (66.0, 3.0)], 2.6, HIGHLIGHT, 2.8))
    out.append(stroke_shape(i3, "FrontCalfSh", [(12.0, -11.5), (30.0, -13.0), (52.0, -6.5)], 3.2, CORE_SHADOW, 3.2))
    out.append(smooth_shape(i3, "FrontShinShape", shin_pts, skin_fill("FrontShin", -15, 8, SKIN)))
    out.append(f"{i2}</Node>")

    # 3. Front Thigh (with Rectus femoris, Vastus lateralis & Hamstrings highlighted as in reference)
    out.append(
        f'{i2}<Node x="{f(p0["hip_far"][0])}" y="{f(p0["hip_far"][1])}" '
        f'rotation="{f(p0["thigh_front_ang"])}" name="FrontThighNode" id="{thigh_id}">'
    )
    out.append(smooth_shape(i3, "FrontShortsCuff", shorts_cuff_pts, skin_fill("FrontShorts", -18, 18, SHORTS_FAR)))
    out.append(stroke_shape(i3, "FrontQuadGroove", [(18.0, 7.8), (40.0, 7.0), (60.0, 5.5)], 1.15, "807F1D1D", 0.4))
    out.append(stroke_shape(i3, "FrontITBandHi", [(18.0, -2.5), (40.0, -2.8), (58.0, -2.5)], 2.0, HIGHLIGHT, 2.0))
    out.append(stroke_shape(i3, "FrontQuadHi", [(20.0, 13.5), (42.0, 13.0), (58.0, 9.5)], 2.4, HIGHLIGHT, 2.6))
    out.append(smooth_shape(i3, "FrontVastusLateralis", vastus_lat_pts, muscle_paint_fn("FrontVL", primary_t, 1.0)))
    out.append(smooth_shape(i3, "FrontRectusFemoris", rectus_pts, muscle_paint_fn("FrontRF", primary_t, 1.05)))
    out.append(smooth_shape(i3, "FrontHamstrings", hamstring_pts, muscle_paint_fn("FrontHam", secondary_t, 0.95)))
    out.append(stroke_shape(i3, "FrontThighSh", [(16.0, -13.0), (38.0, -11.5), (58.0, -8.0)], 3.8, CORE_SHADOW, 3.8))
    out.append(smooth_shape(i3, "FrontThighShape", thigh_pts, skin_fill("FrontThigh", -18, 19, SKIN)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 4. Upright 3/4 Side-Left Torso & Volumetric Head
def build_upright_torso_and_head():
    """Canonical 3/4 side-left CommunityFitness torso, pelvis shorts, sculpted pectorals, 6-pack abs,
    serratus anterior, muscular neck, and volumetric 3/4 head facing left (-X)."""
    ind = "        "
    i2 = ind + "    "

    torso_id = nid()
    key_double(torso_id, 13, lambda p: p["hip_near"][0])
    key_double(torso_id, 14, lambda p: p["hip_near"][1])
    key_double(torso_id, 15, lambda p: p["torso_lean"])
    p0 = POSES[0]

    def glute_t(p):
        return 0.42 + 0.58 * (p["d"] ** 0.78)

    # Local coordinates relative to hip_near (0,0), with -Y = UP and -X = LEFT (anterior chest/face):
    pelvis_shorts = [
        (-22.0, -18.0), (16.0, -18.0), (18.0, 14.0),
        (0.0, 17.5), (-20.0, 14.0),
    ]
    glute_pelvis_pts = [
        (0.0, -15.0), (15.5, -16.0), (17.5, 4.0),
        (8.0, 12.0), (-2.0, 4.0),
    ]
    torso_pts = [
        (-18.0, -8.0), (-20.0, -28.0), (-22.0, -52.0),
        (-26.0, -68.0), (-24.0, -82.0), (-12.0, -90.0),
        (10.0, -90.0), (20.0, -78.0), (18.0, -56.0),
        (15.0, -32.0), (16.0, -8.0),
    ]
    pec_near_pts = [
        (-2.0, -84.0), (-16.0, -86.0), (-24.0, -78.0),
        (-23.0, -62.0), (-12.0, -58.0), (-2.0, -62.0),
    ]
    pec_paint = (
        '<Fill name="PecFill"><SolidColor colorValue="140F172A" name="PecCol"/></Fill>'
        '<Stroke thickness="0.95" join="round" name="PecStroke"><SolidColor colorValue="380F172A" name="PecStrokeCol"/></Stroke>'
    )
    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1A0F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.85" join="round" name="AbsEdge"><SolidColor colorValue="3D0F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        [(-19.0, -56.0), (-10.0, -56.0), (-10.0, -46.0), (-19.0, -46.0)],
        [(-18.5, -44.0), (-9.5, -44.0), (-9.5, -34.0), (-18.5, -34.0)],
        [(-18.0, -32.0), (-9.0, -32.0), (-9.0, -22.0), (-18.0, -22.0)],
    ]

    # Volumetric 3/4 Head & Neck facing LEFT (-X) at top of spine (y ~ -90..-134)
    neck_pts = [
        (-10.0, -90.0), (-7.0, -106.0), (9.0, -108.0),
        (12.0, -96.0), (12.0, -86.0),
    ]
    head_pts = [
        (-13.0, -128.0), (-15.5, -121.5), (-17.2, -115.5), (-15.8, -110.5),
        (-15.2, -104.5), (-9.5, -101.5), (0.0, -103.0), (7.5, -107.0),
        (12.5, -115.0), (12.0, -126.0), (5.0, -133.0), (-6.0, -133.0),
    ]
    hair_pts = [
        (-13.5, -126.0), (-7.5, -133.5), (4.5, -133.8), (12.5, -127.5),
        (13.0, -116.5), (8.5, -112.5), (7.0, -120.5), (2.0, -125.5),
        (-6.0, -127.0),
    ]

    out = [
        f'{ind}<Node x="{f(p0["hip_near"][0])}" y="{f(p0["hip_near"][1])}" '
        f'rotation="{f(p0["torso_lean"])}" name="UprightTorsoAndHeadNode" id="{torso_id}">'
    ]

    # 1. Pelvis Compression Shorts & Gluteus Maximus Highlight
    out.append(smooth_shape(i2, "GlutePelvisHighlight", glute_pelvis_pts, muscle_paint_fn("GlutePelvis", glute_t, 0.95)))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill("PelvisShorts", -18, 18, SHORTS)))

    # 2. Head & Neck
    out.append(smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", -13, -134, 13, -112, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i2, "Ear", 5.0, -113.5, 5.5, 8.5, solid("Ear", "FFA3B1C4"), rot_deg=12.0))
    out.append(stroke_shape(i2, "BrowShade", [(-15.5, -121.2), (-11.0, -120.8)], 1.4, "590F172A", 0.8))
    out.append(stroke_shape(i2, "EyeLine", [(-13.8, -119.2), (-10.8, -119.0)], 1.1, "730F172A", 0.4))
    out.append(stroke_shape(i2, "MouthLine", [(-15.5, -109.5), (-12.0, -109.2)], 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i2, "HeadHi", [(-12.5, -124.0), (-8.0, -129.0), (1.0, -130.0)], 3.0, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i2, "JawShadow", [(-12.5, -102.5), (-3.5, -102.0), (4.5, -105.5)], 2.6, CORE_SHADOW, 2.5))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill("Head", -133, -101, SKIN, x0=-16, x1=12)))
    out.append(stroke_shape(i2, "SCMLine", [(3.0, -105.0), (-1.0, -96.0), (-4.0, -88.0)], 1.4, SOFT_SHADOW, 1.2))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", -108, -86, SKIN)))

    # 3. Sculpted Torso, Pectorals, 6-Pack Abs & Serratus Anterior
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "Serratus1", [(-2.0, -54.0), (-7.0, -48.0), (-9.0, -42.0)], 1.3, "380F172A", 1.0))
    out.append(stroke_shape(i2, "Serratus2", [(-1.0, -44.0), (-6.0, -38.0), (-8.5, -32.0)], 1.3, "380F172A", 1.0))
    out.append(stroke_shape(i2, "PecHi", [(-6.0, -80.0), (-16.0, -76.0), (-20.0, -66.0)], 2.6, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i2, "PectoralNear", pec_near_pts, pec_paint))
    out.append(stroke_shape(i2, "TorsoHi", [(-15.0, -74.0), (-15.0, -48.0), (-14.0, -22.0)], 3.8, HIGHLIGHT, 4.2))
    out.append(stroke_shape(i2, "TorsoBackSh", [(14.0, -74.0), (12.0, -46.0), (11.0, -18.0)], 4.8, CORE_SHADOW, 4.8))
    out.append(smooth_shape(i2, "Torso", torso_pts, skin_fill("Torso", -90, -8, SKIN, x0=-26, x1=20)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    near_arm_xml = build_dumbbell_arm("        ", "Near", False)
    rear_leg_xml = build_rear_near_leg()
    torso_xml = build_upright_torso_and_head()
    front_leg_xml = build_front_far_leg()
    far_arm_xml = build_dumbbell_arm("        ", "Far", True)

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
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="DumbbellLunge" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Left) Dumbbell Arm Hanging Vertically at Side -->
{near_arm_xml}

        <!-- 2. Rear (Near / Left) Leg (Gluteus maximus, Vastus medialis, Adductor magnus, Gastrocnemius, Soleus) -->
{rear_leg_xml}

        <!-- 3. Upright 3/4 Torso, Pectorals, 6-Pack Abs & Volumetric Head -->
{torso_xml}

        <!-- 4. Front (Far / Right) Stepping Leg (Rectus femoris, Vastus lateralis, Hamstrings, Soleus) -->
{front_leg_xml}

        <!-- 5. Background: Far (Right) Dumbbell Arm -->
{far_arm_xml}

        <!-- 6. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="328" y="{f(FLOOR - 2)}" scaleX="1.45" scaleY="0.10" name="AthleteShadow">
            <Ellipse width="210" height="210" name="AthleteShadowEllipse"/>
            <Fill name="AthleteShadowFill"><RadialGradient startX="0" startY="0" endX="105" endY="0" name="AthleteShadowGrad">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="DumbbellLunge" id="0:60">
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
    (BUILD / "lunge.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (44, "frame_mid"), (80, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(620, 40, 350))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
