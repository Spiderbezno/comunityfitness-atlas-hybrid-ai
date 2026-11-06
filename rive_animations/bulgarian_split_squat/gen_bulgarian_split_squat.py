"""Generates rive_animations/bulgarian_split_squat/bulgarian_split_squat.rml (and optionally publishes).

Three-quarter front-right view of a stylized male athlete performing the
Bulgarian Split Squat at 60 fps on a 16:9 (640x360, FLOOR = 300.0) artboard,
with a 3D isometric flat weight bench on the left.

Matches the exact character design of bench_dips, bench_press, and
bicep_curl_barbell (palette, 3-stop linear gradients, Catmull-Rom smooth curves,
feathered highlights / core shadows, volumetric 3/4 head, and orange-to-red
muscle activation glow).

Kinematics & Anatomy (matching reference diagrams):
- Front (near / right) foot remains planted flat on FLOOR = 300.0 ahead of the hips.
- Rear (far / left) foot rests its instep/toes on top of the front-right section
  of the 3/4 weight bench pad with the heel pointing upward.
- Two-bone IK (solve_ik) solves both legs (Hip -> Knee -> Ankle) every frame:
  - At top (d = 0.0): front leg extended upright with soft athletic knee; rear thigh
    angles down-back and rear shin extends back to the bench pad.
  - At bottom (d = 1.0): hips descend vertically and slightly back so the front thigh
    is parallel to the floor (~90 deg knee bend) and the rear knee drops low toward
    the floor (~y = 266) in front of the bench pad.
- Primary muscle activations: Quadriceps (vastus lateralis, rectus femoris, vastus
  medialis teardrop), Gluteus maximus, Adductor magnus, Hamstrings, Gastrocnemius,
  and Soleus on both legs.

Usage (from this directory):
    python3 gen_bulgarian_split_squat.py            # regenerate bulgarian_split_squat.rml
    python3 gen_bulgarian_split_squat.py --publish  # + build .riv, copy to assets, render thumbnail
"""

import math
import pathlib
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "scene.rml"
REPO = HERE.parent.parent
ASSET_RIV = REPO / "assets/animations/bulgarian_split_squat.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/bulgarian_split_squat.png"
THUMB_ADVANCE = "1.25s"  # bottom of split squat: iconic parallel-thigh posture
THUMB_VIEWPORT = "1280x720"  # 2x the 640x360 artboard
THUMB_CROP = (680, 20, 230)  # square size, offsetY, offsetX in the 2x render
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

# 16:9 standard canvas
W, H = 640, 360
FLOOR = 300.0

# Anthropometric constants
THIGH_NEAR, SHIN_NEAR = 74.0, 74.0
THIGH_FAR, SHIN_FAR = 72.0, 74.0
UPPER_ARM, FOREARM = 50.0, 44.0

# Anchors: front ankle planted flat on FLOOR=300; rear ankle resting squarely on bench pad top
ANKLE_NEAR = (414.0, 290.0)
ANKLE_FAR_TOP = (278.0, 194.0)
ANKLE_FAR_BOT = (280.0, 196.0)

# Timeline (frames @60fps): lower 1.15s (69f), bottom hold 0.25s (15f), drive up 1.15s (69f), top hold 0.45s (27f) = 180f (3.0s)
LOWER_FRAMES, HOLD_BOT, PUSH_FRAMES, HOLD_TOP = 69, 15, 69, 27
DURATION = LOWER_FRAMES + HOLD_BOT + PUSH_FRAMES + HOLD_TOP
STEP = 2


def cubic_bezier(x1, y1, x2, y2):
    def bez(t, a, b):
        return 3 * a * t * (1 - t) ** 2 + 3 * b * t * t * (1 - t) + t ** 3

    def ease(x):
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if bez(mid, x1, x2) < x:
                lo = mid
            else:
                hi = mid
        return bez((lo + hi) / 2, y1, y2)

    return ease


EASE = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def squat_depth(frame):
    """0.0 at standing split-stance top, 1.0 at bottom parallel split squat."""
    fr = frame % DURATION
    if fr <= LOWER_FRAMES:
        return EASE(fr / LOWER_FRAMES)
    fr -= LOWER_FRAMES
    if fr <= HOLD_BOT:
        return 1.0
    fr -= HOLD_BOT
    if fr <= PUSH_FRAMES:
        return 1.0 - EASE(fr / PUSH_FRAMES)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def solve_ik(root, target, l1, l2, bend_sign):
    """2D two-bone IK from root -> mid -> target.
    bend_sign = +1 or -1 selects which side of the (root -> target) chord the joint bends toward.
    """
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = math.hypot(dx, dy)
    d_clamped = min(max(d, abs(l1 - l2) + 0.5), l1 + l2 - 0.5)
    base_ang = math.atan2(dy, dx)
    cos_a = max(-1.0, min(1.0, (l1 * l1 + d_clamped * d_clamped - l2 * l2) / (2.0 * l1 * d_clamped)))
    ang1 = base_ang + bend_sign * math.acos(cos_a)
    mid = (root[0] + l1 * math.cos(ang1), root[1] + l1 * math.sin(ang1))
    ang2 = math.atan2(target[1] - mid[1], target[0] - mid[0])
    return ang1, ang2, mid


def pose(d):
    """Compute full Bulgarian Split Squat joint transforms at squat depth d in [0, 1]."""
    # Hips stand tall at d=0.0 (390, 145) and drop to (348, 212) at d=1.0 so the front thigh is horizontal
    # and the front shin stays nearly vertical (~95 deg).
    hip_near = (lerp(390.0, 348.0, d), lerp(145.0, 212.0, d))
    hip_far = (lerp(376.0, 338.0, d), lerp(149.0, 210.0, d))

    # Front (near/right) leg IK: Hip_near -> Knee_near -> Ankle_near (knee bends forward-right: bend_sign = -1)
    thigh_near, shin_near_world, knee_near = solve_ik(
        hip_near, ANKLE_NEAR, THIGH_NEAR, SHIN_NEAR, bend_sign=-1.0
    )
    shin_near_local = shin_near_world - thigh_near
    # Front foot remains flat on FLOOR = 300.0 (world angle = 0.0 rad)
    foot_near_local = 0.0 - shin_near_world

    # Rear (far/left) leg IK: Hip_far -> Knee_far -> Ankle_far on bench (knee bends downward toward floor)
    ankle_far = (
        lerp(ANKLE_FAR_TOP[0], ANKLE_FAR_BOT[0], d),
        lerp(ANKLE_FAR_TOP[1], ANKLE_FAR_BOT[1], d),
    )
    thigh_far, shin_far_world, knee_far = solve_ik(
        hip_far, ankle_far, THIGH_FAR, SHIN_FAR, bend_sign=-1.0
    )
    # Unwrap across the -pi/+pi branch cut along the negative X-axis (when hip_far.y crosses ankle_far.y):
    if thigh_far < 0.0:
        thigh_far += 2.0 * math.pi
    if shin_far_world < 0.0:
        shin_far_world += 2.0 * math.pi
    shin_far_local = shin_far_world - thigh_far
    # Rear foot instep rests along the bench pad slope (~165 deg -> 158 deg world angle)
    foot_far_world = math.radians(lerp(165.0, 158.0, d))
    foot_far_local = foot_far_world - shin_far_world

    # Torso & Head: upright athletic posture with subtle natural forward lean (3 deg at top -> 9.5 deg at bottom)
    # Spine local +x runs from hip_near (0,0) upward along the torso (~ -87 deg to -80.5 deg)
    spine = math.radians(lerp(-87.0, -80.5, d))
    # Neck compensates so head stays level (0 deg world angle) with horizontal gaze to the right
    neck_local = -spine

    # Arms hold heavy dumbbells in a neutral (hammer) grip hanging vertically at the sides:
    # Near (right) arm hangs along the vertical gravity line (~91-92 deg upper arm, ~87-88 deg forearm)
    ua_near_world = math.radians(lerp(92.0, 91.0, d))
    fa_near_world = math.radians(lerp(87.0, 88.0, d))
    ua_near_local = ua_near_world - spine
    fa_near_local = fa_near_world - ua_near_world

    # Far (left) arm hangs on the far side of the torso, angled slightly forward in 3/4 view so the far dumbbell is visible
    ua_far_world = math.radians(lerp(81.0, 82.0, d))
    fa_far_world = math.radians(lerp(70.0, 74.0, d))
    ua_far_local = ua_far_world - spine
    fa_far_local = fa_far_world - ua_far_world

    return {
        "d": d,
        "hip_near": hip_near,
        "hip_far": hip_far,
        "ankle_far": ankle_far,
        "knee_near": knee_near,
        "knee_far": knee_far,
        "thigh_near": thigh_near,
        "shin_near_local": shin_near_local,
        "foot_near_local": foot_near_local,
        "thigh_far": thigh_far,
        "shin_far_local": shin_far_local,
        "foot_far_local": foot_far_local,
        "spine": spine,
        "neck_local": neck_local,
        "ua_near_local": ua_near_local,
        "fa_near_local": fa_near_local,
        "ua_far_local": ua_far_local,
        "fa_far_local": fa_far_local,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(squat_depth(fr)) for fr in FRAMES}

# Unwrap all angular pose keys across consecutive frames to guarantee zero 2*pi discontinuities
_ANGLE_KEYS = (
    "thigh_near", "shin_near_local", "foot_near_local",
    "thigh_far", "shin_far_local", "foot_far_local",
    "spine", "neck_local",
    "ua_near_local", "fa_near_local", "ua_far_local", "fa_far_local",
)
for _i in range(1, len(FRAMES)):
    _prev_p = POSES[FRAMES[_i - 1]]
    _curr_p = POSES[FRAMES[_i]]
    for _k in _ANGLE_KEYS:
        while _curr_p[_k] - _prev_p[_k] > math.pi:
            _curr_p[_k] -= 2.0 * math.pi
        while _curr_p[_k] - _prev_p[_k] < -math.pi:
            _curr_p[_k] += 2.0 * math.pi

# ---------------------------------------------------------------- helpers
_id = [100]


def nid():
    _id[0] += 1
    return f"0:{_id[0]}"


def f(v):
    if isinstance(v, float):
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(v)


def smooth_vertices(pts, closed, indent):
    """Catmull-Rom through pts, emitted as mirrored cubic vertices."""
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
            f'{indent}<CubicMirroredVertex x="{f(float(x))}" y="{f(float(y))}" rotation="{f(ang)}" distance="{f(dist)}"/>'
        )
    return "\n".join(out)


def grad3(name, y0, y1, c0, c1, c2, x0=0, x1=0):
    return (
        f'<LinearGradient startX="{f(float(x0))}" startY="{f(float(y0))}" endX="{f(float(x1))}" endY="{f(float(y1))}" name="{name}">'
        f'<GradientStop colorValue="{c0}" position="0"/>'
        f'<GradientStop colorValue="{c1}" position="0.5"/>'
        f'<GradientStop colorValue="{c2}" position="1"/></LinearGradient>'
    )


def grad(name, x0, y0, x1, y1, c0, c1):
    return (
        f'<LinearGradient startX="{f(float(x0))}" startY="{f(float(y0))}" endX="{f(float(x1))}" endY="{f(float(y1))}" name="{name}">'
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
    """Straight-vertex polygon with rounded corners for structural bench parts."""
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


# ---------------------------------------------------------------- palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FF9AA8BC", "FF738399", "FF4B5A70")
SHORTS = ("A6475569", "B82B3649", "C7172033")
SHORTS_FAR = ("B32B3649", "BF1B2433", "CC101722")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "4D0F172A"

# Muscle activation palette (matches bench_dips / bicep_curl_barbell)
MUSCLE_LOW = (0x80, 0xFB, 0x92, 0x3C)   # warm orange at standing lockout
MUSCLE_HIGH = (0xF5, 0xEF, 0x44, 0x44)  # intense red at bottom / concentric drive
MUSCLE_LINE_LOW = (0x59, 0xC2, 0x41, 0x0C)
MUSCLE_LINE_HIGH = (0xCC, 0x7F, 0x1D, 0x1D)


def argb_lerp(a, b, t):
    return "".join(f"{round(lerp(x, y, t)):02X}" for x, y in zip(a, b))


def skin_fill(name, y0, y1, tones, x0=0, x1=0):
    return f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *tones, x0=x0, x1=x1)}</Fill>'


keys = []  # (objectId, propertyKey, kind, [(frame, value)])


def key_double(obj, prop, fn):
    keys.append((obj, prop, "double", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def key_color(obj, prop, fn):
    keys.append((obj, prop, "color", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def muscle_t(p):
    # High activation across the movement, peaking at the bottom parallel split squat (d=1.0)
    # while remaining clearly visible (0.38) at the top split stance (d=0.0), matching both panels of reference.
    return 0.38 + 0.62 * (p["d"] ** 0.85)


muscle_fill_ids, muscle_line_ids = [], []


def muscle_paint(name, line=0.9):
    fid, lid = nid(), nid()
    muscle_fill_ids.append(fid)
    muscle_line_ids.append(lid)
    t0 = muscle_t(POSES[0])
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{line}" join="round" name="{name}Edge"><SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- Anatomy Rigs
SHOULDER_NEAR_IN_SPINE = (78.0, -14.0)
SHOULDER_FAR_IN_SPINE = (80.0, 14.0)
NECK_IN_SPINE = (88.0, 0.0)


def arm_branch(indent, prefix, far):
    """Hanging arm (UpperArm -> Forearm -> Hand + 3D Dumbbell) in neutral hammer grip."""
    skin = SKIN_FAR if far else SKIN
    ua_id, fa_id = nid(), nid()
    ua_key = "ua_far_local" if far else "ua_near_local"
    fa_key = "fa_far_local" if far else "fa_near_local"
    key_double(ua_id, 15, lambda p: p[ua_key])
    key_double(fa_id, 15, lambda p: p[fa_key])
    p0 = POSES[0]
    sx, sy = SHOULDER_FAR_IN_SPINE if far else SHOULDER_NEAR_IN_SPINE
    i2 = indent + "    "
    i3 = i2 + "    "

    # In UpperArm local space (+x down along arm ~ +91 deg world):
    # -y is ANTERIOR (right/front of body: anterior deltoid, biceps)
    # +y is POSTERIOR (left/back of body: posterior deltoid, triceps)
    ua_pts = [
        (-10, 0), (-8, -9.5), (5, -11.5), (20, -11.0), (35, -9.2), (45, -6.8),
        (52, 0), (45, 6.8), (32, 9.8), (16, 10.8), (2, 10.2), (-8, 8.0),
    ]
    delt_pts = [
        (-14, 0), (-10, -11.5), (2, -13.5), (15, -10.5), (21, -2.0),
        (18, 7.5), (6, 11.0), (-8, 9.5),
    ]
    fa_pts = [
        (-6, 0), (-5, -7.2), (7, -8.8), (21, -7.5), (34, -5.5), (42, -4.5),
        (46, 0), (42, 4.5), (31, 6.0), (17, 7.8), (5, 8.2), (-5, 6.5),
    ]

    # Grip center at distal forearm (x = FOREARM + 2.0):
    # In Forearm local space:
    # +x is DOWNWARD on screen, -x is UPWARD on screen
    # -y is FORWARD-RIGHT (front dumbbell plate stack), +y is BACK-LEFT (rear dumbbell plate stack)
    gx = FOREARM + 2.0
    hand_pts = [
        (gx - 6.0, -5.2), (gx + 2.0, -6.0), (gx + 7.5, -4.5), (gx + 8.5, 0.0),
        (gx + 7.2, 4.8), (gx + 1.5, 5.8), (gx - 6.0, 4.8),
    ]
    fingers_pts = [
        (gx + 1.5, -5.5), (gx + 8.2, -5.0), (gx + 9.2, 0.0),
        (gx + 8.0, 5.0), (gx + 1.5, 5.2),
    ]
    thumb_pts = [
        (gx - 3.5, -4.2), (gx + 1.5, -7.5), (gx + 5.8, -6.2),
        (gx + 4.8, -2.8), (gx - 1.5, -2.2),
    ]

    # 3D Cast-Iron Dumbbell Paints (dark iron plates + metallic bevel rims + chrome handle)
    plate_face = (
        f'<Fill name="{prefix}PlateFaceFill">{grad(prefix + "PlateFaceGrad", -14, -7, 14, 7, "FF334155", "FF0F172A")}</Fill>'
        f'<Stroke thickness="1.2" name="{prefix}PlateRim"><SolidColor colorValue="FF64748B" name="{prefix}PlateRimCol"/></Stroke>'
    )
    plate_side = solid(prefix + "PlateSide", "FF090D16")
    hub_ring = (
        f'<Fill name="{prefix}HubFill"><SolidColor colorValue="FF1E293B" name="{prefix}HubCol"/></Fill>'
        f'<Stroke thickness="1.0" name="{prefix}HubStroke"><SolidColor colorValue="FF94A3B8" name="{prefix}HubStrokeCol"/></Stroke>'
    )
    collar_paint = (
        f'<Fill name="{prefix}CollarFill">{grad(prefix + "CollarGrad", -4, -2, 4, 2, "FFF8FAFC", "FF64748B")}</Fill>'
        f'<Stroke thickness="0.9" name="{prefix}CollarStroke"><SolidColor colorValue="FF334155" name="{prefix}CollarStrokeCol"/></Stroke>'
    )

    out = [f'{indent}<Node x="{f(sx)}" y="{f(sy)}" rotation="{f(p0[ua_key])}" name="{prefix}UpperArm" id="{ua_id}">']

    # 1. Forearm + Hand + 3D Dumbbell (front-to-back order inside Forearm)
    out.append(f'{i2}<Node x="{f(UPPER_ARM)}" rotation="{f(p0[fa_key])}" name="{prefix}Forearm" id="{fa_id}">')

    # 1a. Front Dumbbell Plate Stack (forward-right end of handle: y < 0, drawn in front of hand)
    out.append(ellipse_shape(i3, f"{prefix}DbFrontCollar", gx + 2.4, -16.8, 8.5, 4.8, collar_paint))
    out.append(ellipse_shape(i3, f"{prefix}DbFrontOuterHub", gx + 2.0, -15.0, 12.0, 6.2, hub_ring))
    out.append(ellipse_shape(i3, f"{prefix}DbFrontOuterFace", gx + 2.0, -15.0, 26.0, 13.0, plate_face))
    out.append(ellipse_shape(i3, f"{prefix}DbFrontOuterSide", gx + 1.6, -13.2, 26.0, 13.0, plate_side))
    out.append(ellipse_shape(i3, f"{prefix}DbFrontInnerFace", gx + 1.2, -10.8, 30.0, 14.8, plate_face))
    out.append(ellipse_shape(i3, f"{prefix}DbFrontInnerSide", gx + 0.8, -8.8, 30.0, 14.8, plate_side))

    # 1b. Thumb & Curled Fingers wrapping around the chrome handle bar
    out.append(smooth_shape(i3, f"{prefix}Thumb", thumb_pts, skin_fill(prefix + "Thumb", -8, -2, skin)))
    out.append(stroke_shape(i3, f"{prefix}KnuckleLines", [(gx + 5.5, -3.5), (gx + 6.0, 0.0), (gx + 5.5, 3.5)], 1.1, SOFT_SHADOW, 0.6))
    out.append(smooth_shape(i3, f"{prefix}Fingers", fingers_pts, skin_fill(prefix + "Fingers", -6, 6, skin)))

    # 1c. Chrome Knurled Handle Bar running through the hand from rear stack to front stack
    out.append(stroke_shape(i3, f"{prefix}DbHandleHi", [(gx - 0.8, 8.5), (gx + 1.0, -8.5)], 1.6, "FFE2E8F0", 0.0, cap="butt"))
    out.append(stroke_shape(i3, f"{prefix}DbHandleBar", [(gx - 1.0, 9.5), (gx + 1.2, -9.5)], 5.0, "FF64748B", 0.0, cap="round"))

    # 1d. Dorsal Hand + Forearm Anatomy
    out.append(smooth_shape(i3, f"{prefix}Hand", hand_pts, skin_fill(prefix + "Hand", -6, 6, skin)))
    if not far:
        out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(6, -5.0), (20, -4.5), (34, -3.0)], 2.8, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(6, 5.0), (20, 4.8), (34, 3.2)], 4.0, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -9, 8, skin)))

    # 1e. Rear Dumbbell Plate Stack (back-left end of handle: y > 0, drawn behind hand & forearm)
    out.append(ellipse_shape(i3, f"{prefix}DbRearInnerFace", gx - 0.8, 9.2, 30.0, 14.8, plate_face))
    out.append(ellipse_shape(i3, f"{prefix}DbRearInnerSide", gx - 1.2, 11.0, 30.0, 14.8, plate_side))
    out.append(ellipse_shape(i3, f"{prefix}DbRearOuterFace", gx - 1.6, 13.0, 26.0, 13.0, plate_face))
    out.append(ellipse_shape(i3, f"{prefix}DbRearOuterSide", gx - 2.0, 14.6, 26.0, 13.0, plate_side))
    out.append(f"{i2}</Node>")

    # 2. Deltoid + Upper Arm
    if not far:
        out.append(stroke_shape(i2, f"{prefix}DeltHi", [(-4, -7.5), (5, -9.0), (14, -5.5)], 3.0, HIGHLIGHT, 3.5))
        out.append(stroke_shape(i2, f"{prefix}DeltGroove", [(2, -10.0), (12, -7.0), (19, -1.5)], 1.2, SOFT_SHADOW, 1.0))
    out.append(smooth_shape(i2, f"{prefix}Deltoid", delt_pts, skin_fill(prefix + "Deltoid", -13, 11, skin)))
    if not far:
        out.append(stroke_shape(i2, f"{prefix}UpperArmHi", [(8, -7.0), (24, -6.8), (38, -5.0)], 3.0, HIGHLIGHT, 3.5))
        out.append(stroke_shape(i2, f"{prefix}BicepsLine", [(14, -2.0), (28, -2.5), (40, -1.5)], 1.2, SOFT_SHADOW, 1.0))
    out.append(stroke_shape(i2, f"{prefix}UpperArmSh", [(8, 6.8), (24, 7.2), (38, 5.5)], 4.5, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i2, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UpperArm", -11, 11, skin)))

    out.append(f"{indent}</Node>")
    return "\n".join(out)


def front_leg_rig(indent):
    """Front (Near / Right) Leg: Hip_near -> Thigh -> Shin -> Foot with Quadriceps, Hamstrings, Glute, and Calf activations."""
    i2 = indent + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "
    thigh_id, shin_id, foot_id = nid(), nid(), nid()
    key_double(thigh_id, 15, lambda p: p["thigh_near"])
    key_double(shin_id, 15, lambda p: p["shin_near_local"])
    key_double(foot_id, 15, lambda p: p["foot_near_local"])
    p0 = POSES[0]

    # In NearThigh local space (+x from Hip(0) -> Knee(74)):
    # -y is ANTERIOR / SUPERIOR (Quadriceps femoris: Rectus femoris, Vastus lateralis, Vastus medialis)
    # +y is POSTERIOR / INFERIOR (Gluteus maximus, Hamstrings / Adductor magnus)
    thigh_pts = [
        (-18, 0), (-14, -13.5), (6, -18.0), (30, -18.5), (52, -15.5), (66, -11.5),
        (78, 0), (68, 10.0), (52, 12.5), (32, 16.0), (10, 19.0), (-14, 15.0),
    ]
    shorts_thigh_pts = [
        (-21, 0), (-16, -15.0), (6, -19.5), (27, -19.2),
        (28, 17.5), (10, 20.5), (-8, 20.0), (-19, 14.5),
    ]
    # Sculpted Quadriceps heads on the anterior/lateral thigh (-y), leaving a silver patellar tendon margin (x=60..74)
    # and a silver iliotibial band / lateral fascia strip (y=+0.5..+5.0) above the hamstrings
    quad_rectus_pts = [
        (10, -16.8), (30, -17.6), (48, -15.0), (59, -11.2),
        (61, -6.5), (46, -7.2), (28, -7.8), (10, -8.5),
    ]
    quad_vastus_lat_pts = [
        (12, -8.0), (30, -7.5), (48, -6.8), (60, -5.2),
        (57, 0.5), (40, 1.0), (22, 0.5), (12, -2.0),
    ]
    quad_vastus_med_pts = [
        (42, -13.2), (57, -10.5), (63, -4.2), (56, 0.5), (44, -3.0),
    ]
    # Hamstrings / Adductor magnus strip along the posterior/lower contour (+y), separated by the silver IT-band
    hamstring_pts = [
        (18, 5.2), (38, 5.5), (54, 5.0), (60, 8.2),
        (48, 12.2), (30, 15.2), (16, 16.2),
    ]
    # Sculpted Gluteus maximus activation on the posterior hip/buttock (visible through semi-translucent shorts)
    glute_act_pts = [
        (-20, -1.0), (-15, 14.5), (2, 18.8), (15, 16.8),
        (14, 5.5), (-4, 2.0),
    ]

    # In NearShin local space (+x from Knee(0) -> Ankle(74), pointing downward ~95 deg):
    # -y points to SCREEN RIGHT (straight anterior tibia bone!)
    # +y points to SCREEN LEFT (rounded posterior Gastrocnemius + Soleus calf belly!)
    shin_pts = [
        (-10, 0), (-8, -7.2), (16, -7.0), (42, -6.2), (66, -5.0), (73, -4.2),
        (76, 0), (72, 4.8), (56, 7.2), (38, 13.2), (22, 16.2), (8, 13.8), (-8, 8.5),
    ]
    # Sculpted Gastrocnemius + Soleus inset along the posterior (+y, screen-left) calf curve,
    # leaving the entire anterior/lateral silver tibia (y = -7.2..+7.5) clean and unbowed!
    gastroc_pts = [
        (7, 8.2), (20, 8.8), (35, 8.2), (38, 12.5),
        (23, 15.6), (9, 13.2),
    ]
    soleus_pts = [
        (32, 6.2), (46, 5.5), (58, 5.2), (54, 7.2), (38, 12.2),
    ]

    # In NearFoot local space (world angle = 0 deg, origin at ANKLE_NEAR=(414, 290), FLOOR=300 -> y=+10):
    foot_pts = [
        (-10, -2.0), (4, -3.5), (18, 2.5), (29, 6.5), (31, 9.8),
        (16, 10.2), (-8, 10.0), (-12, 5.5),
    ]

    out = [f'{indent}<Node rotation="{f(p0["thigh_near"])}" name="NearThigh" id="{thigh_id}">']

    # 1. Shin + Foot + KneeCap (drawn in front of the distal thigh)
    out.append(f'{i2}<Node x="{f(THIGH_NEAR)}" rotation="{f(p0["shin_near_local"])}" name="NearShin" id="{shin_id}">')
    out.append(f'{i3}<Node x="{f(SHIN_NEAR)}" rotation="{f(p0["foot_near_local"])}" name="NearFoot" id="{foot_id}">')
    out.append(stroke_shape(i4, "NearFootHi", [(-4, 0.5), (10, 3.0), (24, 6.5)], 2.2, HIGHLIGHT, 2.5))
    out.append(stroke_shape(i4, "NearFootSoleSh", [(-9, 9.2), (8, 9.5), (28, 9.2)], 2.2, CORE_SHADOW, 1.5))
    out.append(smooth_shape(i4, "NearFootShape", foot_pts, skin_fill("NearFoot", -4, 10, SKIN)))
    out.append(f"{i3}</Node>")

    out.append(ellipse_shape(i3, "NearKneeCap", 0, -1, 20, 18, skin_fill("NearKnee", -10, 9, SKIN)))
    out.append(smooth_shape(i3, "NearSoleusActivation", soleus_pts, muscle_paint("NearSoleus", 0.85)))
    out.append(smooth_shape(i3, "NearGastrocActivation", gastroc_pts, muscle_paint("NearGastroc", 0.9)))
    out.append(stroke_shape(i3, "NearTibiaLine", [(12, 1.5), (36, 1.8), (58, 1.2)], 1.2, SOFT_SHADOW, 1.2))
    out.append(stroke_shape(i3, "NearShinHi", [(10, -4.8), (38, -4.5), (64, -3.2)], 3.4, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i3, "NearShinSh", [(12, 12.0), (28, 13.5), (50, 6.5)], 4.0, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i3, "NearShinShape", shin_pts, skin_fill("NearShin", -8, 16, SKIN)))
    out.append(f"{i2}</Node>")

    # 2. Semi-translucent Compression Shorts + Gluteus Maximus, Quadriceps & Hamstrings
    out.append(stroke_shape(i2, "NearShortsHem", [(27, -18.5), (28, 0.0), (27, 17.0)], 1.4, "730F172A", 0.6))
    out.append(smooth_shape(i2, "NearThighShorts", shorts_thigh_pts, skin_fill("NearThighShorts", -19, 20, SHORTS)))
    out.append(stroke_shape(i2, "QuadSeparation1", [(16, -7.8), (38, -7.2), (58, -5.8)], 1.2, "807F1D1D", 0.5))
    out.append(stroke_shape(i2, "QuadSeparation2", [(42, -12.5), (52, -7.5), (60, -4.0)], 1.1, "807F1D1D", 0.5))
    out.append(stroke_shape(i2, "ITBandHi", [(18, 2.8), (38, 3.0), (56, 2.5)], 2.2, "80FFFFFF", 2.0))
    out.append(stroke_shape(i2, "QuadHi", [(22, -12.5), (42, -12.0), (56, -8.5)], 2.8, "66FFFFFF", 3.0))
    out.append(smooth_shape(i2, "NearVastusMedActivation", quad_vastus_med_pts, muscle_paint("NearVastusMed", 0.9)))
    out.append(smooth_shape(i2, "NearVastusLatActivation", quad_vastus_lat_pts, muscle_paint("NearVastusLat", 0.95)))
    out.append(smooth_shape(i2, "NearRectusFemActivation", quad_rectus_pts, muscle_paint("NearRectusFem", 0.95)))
    out.append(smooth_shape(i2, "NearHamstringActivation", hamstring_pts, muscle_paint("NearHamstring", 0.9)))
    out.append(smooth_shape(i2, "NearGluteActivation", glute_act_pts, muscle_paint("NearGlute", 0.95)))
    out.append(stroke_shape(i2, "NearThighSh", [(12, 13.5), (36, 11.0), (58, 7.5)], 5.0, CORE_SHADOW, 5.0))
    out.append(smooth_shape(i2, "NearThighShape", thigh_pts, skin_fill("NearThigh", -18, 19, SKIN)))

    out.append(f"{indent}</Node>")
    return "\n".join(out)


def rear_leg_rig():
    """Rear (Far / Left) Leg: Hip_far -> Thigh -> Shin -> Foot anchored on the 3/4 bench pad."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "
    i5 = i4 + "    "
    hip_id, thigh_id, shin_id, foot_id = nid(), nid(), nid(), nid()
    key_double(hip_id, 13, lambda p: p["hip_far"][0])
    key_double(hip_id, 14, lambda p: p["hip_far"][1])
    key_double(thigh_id, 15, lambda p: p["thigh_far"])
    key_double(shin_id, 15, lambda p: p["shin_far_local"])
    key_double(foot_id, 15, lambda p: p["foot_far_local"])
    p0 = POSES[0]

    # In FarThigh local space (+x from Hip_far(0) -> Knee_far(72), angle ~ +105 deg to +130 deg):
    # -y faces FORWARD-RIGHT (anterior Rear Quadriceps / Rectus femoris)
    # +y faces BACK-LEFT (inner/posterior Adductor magnus & Hamstrings)
    thigh_pts = [
        (-16, 0), (-12, -12.5), (6, -16.5), (28, -16.8), (50, -14.2), (64, -10.5),
        (76, 0), (66, 9.5), (50, 12.0), (28, 15.2), (8, 17.5), (-12, 13.5),
    ]
    shorts_thigh_pts = [
        (-19, 0), (-14, -14.0), (6, -18.0), (25, -17.5),
        (25, 16.0), (8, 18.5), (-14, 14.0),
    ]
    # Inset Rear Quadriceps (-y) & Adductor magnus (+y) with a clean silver fascia strip (y = -4.0..+1.5)
    # and silver tendon margin near the rear knee (x = 56..74)
    far_quad_pts = [
        (16, -14.8), (34, -15.0), (50, -12.5), (58, -8.5),
        (55, -4.0), (36, -4.2), (16, -4.8),
    ]
    far_adductor_pts = [
        (14, 1.5), (34, 1.8), (52, 2.2), (57, 6.8),
        (46, 11.2), (28, 14.2), (14, 14.8),
    ]

    # In FarShin local space (+x from Knee_far(0) -> Ankle_far(74) on bench, angle ~ +206 deg to +250 deg):
    # +y faces UP-RIGHT (posterior Soleus & Gastrocnemius calf belly)
    # -y faces DOWN-LEFT (anterior tibia)
    shin_pts = [
        (-10, 0), (-8, -7.2), (16, -7.0), (40, -6.2), (62, -4.8), (72, -4.0),
        (76, 0), (72, 4.8), (56, 6.8), (36, 12.8), (20, 15.2), (6, 12.8), (-8, 8.0),
    ]
    # Inset Rear Soleus/Gastrocnemius along the posterior (+y) calf belly
    far_calf_pts = [
        (8, 5.2), (22, 5.8), (40, 5.5), (48, 7.2),
        (36, 12.2), (20, 14.5), (7, 11.8),
    ]

    # In FarFoot local space (+x runs from Ankle_far(0) down-left along the bench pad to the toes(28);
    # +y points UP-LEFT toward the raised heel; -y is the dorsal instep resting on the bench pad):
    foot_pts = [
        (-8, 2.0), (-4, 9.5), (3, 9.0), (10, 3.5), (22, 1.5), (29, -1.0),
        (27, -4.5), (14, -5.2), (0, -4.8), (-7, -2.5),
    ]

    out = [f'{ind}<Node x="{f(p0["hip_far"][0])}" y="{f(p0["hip_far"][1])}" name="FarLegHip" id="{hip_id}">']
    out.append(f'{i2}<Node rotation="{f(p0["thigh_far"])}" name="FarThigh" id="{thigh_id}">')

    # 1. Rear Shin + Rear Foot resting on bench
    out.append(f'{i3}<Node x="{f(THIGH_FAR)}" rotation="{f(p0["shin_far_local"])}" name="FarShin" id="{shin_id}">')
    out.append(f'{i4}<Node x="{f(SHIN_FAR)}" rotation="{f(p0["foot_far_local"])}" name="FarFoot" id="{foot_id}">')
    out.append(smooth_shape(i5, "FarFootShape", foot_pts, skin_fill("FarFoot", -5, 10, SKIN_FAR)))
    out.append(f"{i4}</Node>")

    out.append(ellipse_shape(i4, "FarKneeCap", 0, -1, 19, 17, skin_fill("FarKnee", -9, 9, SKIN_FAR)))
    out.append(smooth_shape(i4, "FarCalfActivation", far_calf_pts, muscle_paint("FarCalf", 0.85)))
    out.append(stroke_shape(i4, "FarShinHi", [(14, 1.5), (38, 1.8), (58, 1.2)], 2.2, "66FFFFFF", 2.5))
    out.append(stroke_shape(i4, "FarShinSh", [(14, -5.0), (38, -4.5), (60, -3.2)], 3.8, CORE_SHADOW, 4.0))
    out.append(smooth_shape(i4, "FarShinShape", shin_pts, skin_fill("FarShin", -8, 15, SKIN_FAR)))
    out.append(f"{i3}</Node>")

    # 2. Rear Thigh Shorts + Rear Quadriceps & Adductor Magnus activations with silver fascia margin
    out.append(smooth_shape(i3, "FarThighShorts", shorts_thigh_pts, skin_fill("FarThighShorts", -18, 18, SHORTS_FAR)))
    out.append(stroke_shape(i3, "FarFasciaHi", [(18, -1.2), (38, -1.0), (56, -0.8)], 2.0, "59FFFFFF", 2.0))
    out.append(smooth_shape(i3, "FarQuadActivation", far_quad_pts, muscle_paint("FarQuad", 0.9)))
    out.append(smooth_shape(i3, "FarAdductorActivation", far_adductor_pts, muscle_paint("FarAdductor", 0.9)))
    out.append(stroke_shape(i3, "FarThighSh", [(12, 12.5), (36, 10.5), (56, 7.0)], 4.5, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i3, "FarThighShape", thigh_pts, skin_fill("FarThigh", -17, 18, SKIN_FAR)))

    out.append(f"{i2}</Node>")
    out.append(f"{ind}</Node>")
    return "\n".join(out)


def near_athlete_rig():
    """Foreground Near Arm + Front Leg + Upright 3/4 Torso & Volumetric 3/4 Head."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "
    hip_id, spine_id, neck_id = nid(), nid(), nid()
    key_double(hip_id, 13, lambda p: p["hip_near"][0])
    key_double(hip_id, 14, lambda p: p["hip_near"][1])
    key_double(spine_id, 15, lambda p: p["spine"])
    key_double(neck_id, 15, lambda p: p["neck_local"])
    p0 = POSES[0]

    # In Spine local space:
    # Origin at hip_near; +x runs UP along the spine from pelvis(0) to clavicles(86).
    # Because spine angle is ~ -87 deg to -80.5 deg (pointing UP),
    # local +y points FORWARD-RIGHT (chest, 6-pack abs, anterior pelvis),
    # and local -y points BACK-LEFT (latissimus dorsi, lower back, glutes).
    torso_pts = [
        (-18, -15.0),  # lower glute / posterior hip
        (-16, 16.0),   # anterior pelvis / inguinal crease
        (6, 18.5),     # lower abdomen
        (28, 18.0),    # mid abdomen (rectus abdominis contour)
        (50, 19.5),    # upper abdomen / lower ribcage
        (68, 23.5),    # lower pectoralis major projection
        (82, 22.0),    # upper chest / manubrium
        (90, 12.0),    # anterior clavicle
        (90, -10.0),   # posterior clavicle / acromion
        (78, -21.5),   # upper latissimus / teres major flare
        (56, -19.5),   # mid latissimus taper
        (32, -15.5),   # lumbar curve
        (8, -16.5),    # iliac crest
    ]
    torso_hi = [(20, 14.0), (48, 15.0), (74, 18.0)]
    torso_sh = [(16, -12.0), (46, -13.5), (74, -16.5)]

    pelvis_shorts = [
        (-20, -15.5), (-18, 16.5), (14, 19.2), (16, -17.0), (-4, -18.0),
    ]

    # Sculpted Pectoralis Major (near right pec + far left pec across the sternum)
    pec_near_pts = [
        (60, 2.0), (82, 2.5), (86, 14.5), (78, 22.0), (64, 21.0), (58, 11.5),
    ]
    pec_far_pts = [
        (62, 21.0), (78, 22.0), (84, 25.0), (70, 25.5), (60, 23.0),
    ]
    pec_paint = (
        '<Fill name="PecFill"><SolidColor colorValue="140F172A" name="PecCol"/></Fill>'
        '<Stroke thickness="0.95" join="round" name="PecStroke"><SolidColor colorValue="380F172A" name="PecStrokeCol"/></Stroke>'
    )

    # Sculpted 6-pack abs + serratus / external oblique lines
    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1A0F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.85" join="round" name="AbsEdge"><SolidColor colorValue="3D0F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        [(47, 8.5), (57, 9.0), (57, 17.5), (47, 17.0)],
        [(35, 8.2), (45, 8.5), (45, 17.0), (35, 16.8)],
        [(23, 8.5), (33, 8.2), (33, 16.8), (23, 17.0)],
        [(47, 18.0), (57, 18.2), (57, 21.5), (47, 20.8)],
        [(35, 17.5), (45, 17.8), (45, 20.5), (35, 20.2)],
        [(23, 17.5), (33, 17.5), (33, 20.2), (23, 20.2)],
    ]

    # Volumetric 3/4 Head & Neck in screen-aligned Neck local space (since spine + neck_local = 0 deg world!):
    # +x is RIGHT (facing direction), -x is LEFT (occiput), -y is UP (crown), +y is DOWN (neck/clavicles).
    neck_pts = [
        (-9.5, -18.0), (7.5, -15.0), (11.0, 2.0),
        (-13.0, 4.0), (-12.5, -8.0),
    ]
    head_pts = [
        (11.0, -39.0),   # upper forehead
        (13.5, -32.5),   # right brow ridge
        (15.2, -26.5),   # nose bridge & tip (facing right)
        (13.8, -21.5),   # upper/lower lips
        (13.2, -15.5),   # strong chin tip
        (7.5, -12.5),    # under-chin / anterior jawline
        (-2.0, -14.0),   # mandible angle (gonion)
        (-9.5, -18.0),   # beneath ear / mastoid
        (-14.5, -26.0),  # occiput / back of skull
        (-14.0, -37.0),  # posterior crown
        (-7.0, -44.0),   # top cranial dome
        (4.0, -44.0),    # anterior crown
    ]
    hair_pts = [
        (11.5, -37.0), (5.5, -44.5), (-6.5, -44.8), (-14.5, -38.5),
        (-15.0, -27.5), (-10.5, -23.5), (-9.0, -31.5), (-4.0, -36.5),
        (4.0, -38.0),
    ]
    head_hi = [(10.5, -35.0), (6.0, -40.0), (-3.0, -41.0)]
    jaw_sh = [(10.5, -13.5), (1.5, -13.0), (-6.5, -16.5)]

    out = [f'{ind}<Node x="{f(p0["hip_near"][0])}" y="{f(p0["hip_near"][1])}" name="HipNear" id="{hip_id}">']

    # 1. Near (right) Arm hanging in foreground of the hip & upper thigh (matches reference image)
    out.append(f'{i2}<Node rotation="{f(p0["spine"])}" name="NearArmSpine" id="{nid()}">')
    # Re-use spine_id or key this node to spine? Wait: let's place NearArm inside Spine if NearArm is above FrontLeg,
    # or give NearArmSpine its own keyed rotation so FrontLeg can sit between NearArm and Torso!
    out.pop()  # Let's key NearArmSpine cleanly:
    near_arm_spine_id = nid()
    key_double(near_arm_spine_id, 15, lambda p: p["spine"])
    out.append(f'{i2}<Node rotation="{f(p0["spine"])}" name="NearArmSpine" id="{near_arm_spine_id}">')
    out.append(arm_branch(i3, "Near", False))
    out.append(f"{i2}</Node>")

    # 2. Front (Near / Right) Leg (drawn in front of the lower torso/pelvis so horizontal thigh at bottom overlaps cleanly)
    out.append(front_leg_rig(i2))

    # 3. Upright 3/4 Torso & Volumetric 3/4 Head
    out.append(f'{i2}<Node rotation="{f(p0["spine"])}" name="Spine" id="{spine_id}">')

    # Head & Neck (drawn above the upper chest/clavicles)
    nx, ny = NECK_IN_SPINE
    out.append(f'{i3}<Node x="{f(nx)}" y="{f(ny)}" rotation="{f(p0["neck_local"])}" name="Neck" id="{neck_id}">')
    out.append(smooth_shape(i4, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", -14, -44, 11, -24, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i4, "Ear", -7.0, -24.5, 5.5, 8.5, solid("Ear", "FFA3B1C4"), rot_deg=-12.0))
    out.append(stroke_shape(i4, "BrowShade", [(13.5, -32.2), (9.0, -31.8)], 1.4, "590F172A", 0.8))
    out.append(stroke_shape(i4, "EyeLine", [(11.8, -30.2), (8.8, -30.0)], 1.1, "730F172A", 0.4))
    out.append(stroke_shape(i4, "MouthLine", [(13.5, -20.5), (10.0, -20.2)], 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i4, "HeadHi", head_hi, 3.0, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i4, "JawShadow", jaw_sh, 2.6, CORE_SHADOW, 2.5))
    out.append(smooth_shape(i4, "Head", head_pts, skin_fill("Head", -44, -12, SKIN, x0=14, x1=-14)))
    out.append(stroke_shape(i4, "SCMLine", [(-5.0, -16.0), (-1.0, -7.0), (2.0, 1.0)], 1.4, SOFT_SHADOW, 1.2))
    out.append(smooth_shape(i4, "NeckShape", neck_pts, skin_fill("Neck", -18, 4, SKIN)))
    out.append(f"{i3}</Node>")

    # Torso details (Pelvis shorts + Gluteus Maximus activation, 6-pack abs, oblique/serratus lines, pectorals)
    glute_pelvis_pts = [
        (-19, -14.8), (-16, -2.5), (6, -3.5), (10, -15.8), (-6, -17.2),
    ]
    out.append(smooth_shape(i3, "PelvisShorts", pelvis_shorts, skin_fill("PelvisShorts", -17, 19, SHORTS)))
    out.append(smooth_shape(i3, "GluteusMaxPelvisActivation", glute_pelvis_pts, muscle_paint("GlutePelvis", 0.9)))
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i3, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i3, "LineaAlba", [(59, 17.5), (39, 17.2), (19, 17.2)], 1.2, "470F172A", 0.8))
    out.append(stroke_shape(i3, "Serratus1", [(54, 1.0), (47, 5.5), (40, 7.5)], 1.3, "380F172A", 1.0))
    out.append(stroke_shape(i3, "Serratus2", [(44, 0.0), (37, 4.5), (30, 6.8)], 1.3, "380F172A", 1.0))
    out.append(stroke_shape(i3, "PecNearHi", [(66, 6.0), (76, 9.0), (82, 15.0)], 2.8, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i3, "PecNear", pec_near_pts, pec_paint))
    out.append(smooth_shape(i3, "PecFar", pec_far_pts, pec_paint))
    out.append(stroke_shape(i3, "TorsoHi", torso_hi, 4.2, HIGHLIGHT, 4.5))
    out.append(stroke_shape(i3, "TorsoSh", torso_sh, 5.8, CORE_SHADOW, 5.5))
    out.append(smooth_shape(i3, "Torso", torso_pts, skin_fill("Torso", -21, 24, SKIN)))

    out.append(f"{i2}</Node>")
    out.append(f"{ind}</Node>")
    return "\n".join(out)


def far_arm_rig():
    """Far (left) arm hanging on the far side of the torso."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    hip_id, spine_id = nid(), nid()
    key_double(hip_id, 13, lambda p: p["hip_near"][0])
    key_double(hip_id, 14, lambda p: p["hip_near"][1])
    key_double(spine_id, 15, lambda p: p["spine"])
    p0 = POSES[0]
    return "\n".join([
        f'{ind}<Node x="{f(p0["hip_near"][0])}" y="{f(p0["hip_near"][1])}" name="FarArmHip" id="{hip_id}">',
        f'{i2}<Node rotation="{f(p0["spine"])}" name="FarArmSpine" id="{spine_id}">',
        arm_branch(i3, "Far", True),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


def bench():
    """3/4 perspective flat gym bench on the left side of the canvas matching the reference illustration."""
    ind = "        "
    i2 = ind + "    "
    metal_front = f'<Fill name="MetalFrontFill">{grad("MetalFrontGrad", 165, 225, 200, 298, "FFF1F5F9", "FF94A3B8")}</Fill>'
    metal_back = f'<Fill name="MetalBackFill">{grad("MetalBackGrad", 285, 198, 315, 276, "FFE2E8F0", "FF64748B")}</Fill>'
    metal_rail = f'<Fill name="MetalRailFill">{grad("MetalRailGrad", 185, 272, 305, 244, "FFCBD5E1", "FF64748B")}</Fill>'
    pad_top = f'<Fill name="PadTopFill">{grad("PadTopGrad", 200, 190, 245, 232, "FF334155", "FF1E293B")}</Fill>'
    pad_side = f'<Fill name="PadSideFill">{grad("PadSideGrad", 220, 200, 220, 240, "FF1E293B", "FF0B1120")}</Fill>'
    rubber = solid("Rubber", "FF0F172A")

    # Bench pad in 3/4 view on the left side:
    # Back-right top surface around (245..322, 184..206) firmly supports the athlete's rear foot (ANKLE_FAR ~ (278, 194)).
    top_pts = [(168, 228), (322, 194), (298, 184), (146, 217)]
    front_skirt_pts = [(168, 227), (322, 193), (322, 206), (168, 240)]
    left_skirt_pts = [(146, 217), (168, 227), (168, 240), (146, 229)]

    return "\n".join([
        f'{ind}<Node name="Bench">',
        # Pad top & 3D side skirts
        stroke_shape(i2, "PadEdgeHighlight", [(170, 227.5), (245, 211.0), (318, 194.5)], 1.5, "40FFFFFF", 1.0),
        poly_shape(i2, "BenchPadTop", top_pts, pad_top, radius=4.5),
        poly_shape(i2, "BenchPadFrontSkirt", front_skirt_pts, pad_side, radius=3.5),
        poly_shape(i2, "BenchPadLeftSkirt", left_skirt_pts, pad_side, radius=3.5),

        # Front-left vertical leg post + horizontal T-bar stabilizer base (matching reference image)
        poly_shape(i2, "FrontStabilizerFootR", [(190, 296), (206, 297), (206, 300), (190, 299)], rubber),
        poly_shape(i2, "FrontStabilizerFootL", [(142, 292), (156, 293), (156, 296), (142, 295)], rubber),
        poly_shape(i2, "FrontStabilizerBar", [(146, 289), (204, 294), (204, 298), (146, 293)], metal_front),
        poly_shape(i2, "FrontLegPost", [(174, 236), (188, 233), (182, 294), (168, 293)], metal_front),

        # Longitudinal under-rail connecting front and rear leg posts
        poly_shape(i2, "UnderRail", [(182, 274), (296, 247), (296, 255), (181, 282)], metal_rail),
        stroke_shape(i2, "UnderRailShadow", [(184, 274), (294, 247)], 2.0, "FF0F172A", 0.0, cap="butt"),

        # Rear-right leg post + stabilizer base
        poly_shape(i2, "RearStabilizerFootR", [(310, 270), (324, 272), (324, 275), (310, 273)], rubber),
        poly_shape(i2, "RearStabilizerFootL", [(262, 265), (274, 266), (274, 269), (262, 268)], rubber),
        poly_shape(i2, "RearStabilizerBar", [(265, 262), (322, 269), (322, 273), (265, 266)], metal_back),
        poly_shape(i2, "RearLegPost", [(290, 199), (302, 196), (304, 268), (292, 267)], metal_back),
        f"{ind}</Node>",
    ])


def shadow():
    ind = "        "
    sid = nid()
    key_double(sid, 13, lambda p: lerp(388.0, 376.0, p["d"]))
    key_double(sid, 16, lambda p: lerp(0.95, 1.22, p["d"]))
    return "\n".join([
        # Dynamic athlete shadow on FLOOR=300
        f'{ind}<Shape x="388" y="{f(FLOOR + 1)}" scaleX="0.95" scaleY="0.075" name="BodyShadow" id="{sid}">\n'
        f'{ind}    <Ellipse width="200" height="200" name="ShadowEllipse"/>\n'
        f'{ind}    <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="100" endY="0" name="ShadowGrad">'
        f'<GradientStop colorValue="B3000000" position="0"/><GradientStop colorValue="59000000" position="0.6"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{ind}</Shape>",
        # Static bench shadow
        f'{ind}<Shape x="225" y="{f(FLOOR - 4)}" scaleX="0.90" scaleY="0.07" name="BenchShadow">\n'
        f'{ind}    <Ellipse width="200" height="200" name="BenchShadowEllipse"/>\n'
        f'{ind}    <Fill name="BenchShadowFill"><RadialGradient startX="0" startY="0" endX="100" endY="0" name="BenchShadowGrad">'
        f'<GradientStop colorValue="8C000000" position="0"/><GradientStop colorValue="40000000" position="0.6"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{ind}</Shape>",
    ])


def scenery():
    ind = "        "
    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"
    return (
        f'{ind}<Shape x="{W / 2}" y="{f(FLOOR + 1)}" name="FloorLine"><Rectangle width="{W - 40}" height="2" cornerRadiusTL="1" name="FloorRect"/>'
        f'<Fill name="FloorFill"><LinearGradient startX="{-(W - 40) / 2}" startY="0" endX="{(W - 40) / 2}" endY="0" name="FloorGrad">'
        f'<GradientStop colorValue="00475569" position="0"/><GradientStop colorValue="FF475569" position="0.2"/>'
        f'<GradientStop colorValue="FF475569" position="0.8"/><GradientStop colorValue="00475569" position="1"/></LinearGradient></Fill></Shape>\n'
        f'{ind}<Shape x="{W / 2}" y="{f((FLOOR + H) / 2 + 1)}" name="FloorBand"><Rectangle width="{W}" height="{f(band_h)}" name="FloorBandRect"/>'
        f"{band_fill}</Shape>\n"
        f'{ind}<Shape x="{W / 2}" y="{H / 2}" name="Backdrop"><Rectangle width="{W}" height="{H}" name="BackdropRect"/>'
        f'<Fill name="BackdropFill"><RadialGradient startX="0" startY="-40" endX="0" endY="{H * 0.75}" name="BackdropGrad">'
        f'<GradientStop colorValue="FF1E293B" position="0"/><GradientStop colorValue="FF0F172A" position="1"/></RadialGradient></Fill></Shape>'
    )


near_xml = near_athlete_rig()
rear_leg_xml = rear_leg_rig()
far_arm_xml = far_arm_rig()
bench_xml = bench()
shd_xml = shadow()

for cid in muscle_fill_ids:
    key_color(cid, 37, lambda p: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, muscle_t(p)))
for cid in muscle_line_ids:
    key_color(cid, 37, lambda p: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, muscle_t(p)))


def keyed_xml():
    out = []
    for obj, prop, kind, vals in keys:
        out.append(f'            <KeyedObject objectId="{obj}">')
        out.append(f'                <KeyedProperty propertyKey="{prop}">')
        for i, (fr, v) in enumerate(vals):
            if 0 < i < len(vals) - 1 and v == vals[i - 1][1] and v == vals[i + 1][1]:
                continue
            if kind == "double":
                out.append(f'                    <KeyFrameDouble value="{v:.4f}" interpolationType="linear" frame="{fr}"/>')
            else:
                out.append(f'                    <KeyFrameColor value="{v}" interpolationType="linear" frame="{fr}"/>')
        out.append("                </KeyedProperty>")
        out.append("            </KeyedObject>")
    return "\n".join(out)


rml = f"""<Rive version="1" kind="fragment">
    <!-- Bulgarian Split Squat: 3/4 front-right view, 60 fps, 16:9 (640x360), generated by gen_bulgarian_split_squat.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="BulgarianSplitSquat" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- Foreground: Near (right) arm, Front (right) leg, Torso & Volumetric 3/4 Head -->
{near_xml}

        <!-- Rear (left) leg reaching back to rest instep on the bench pad -->
{rear_leg_xml}

        <!-- Far (left) arm behind torso -->
{far_arm_xml}

        <!-- 3/4 Isometric Weight Bench -->
{bench_xml}

        <!-- Floor shadows -->
{shd_xml}

{scenery()}

        <StateMachine name="BulgarianSplitSquatSM" id="0:7">
            <StateMachineLayer name="Motion" id="0:8">
                <AnyState x="200" y="-120"/>
                <ExitState x="400" y="-120"/>
                <EntryState>
                    <StateTransition stateToId="0:12"/>
                </EntryState>
                <AnimationState x="200" animationId="0:60" id="0:12"/>
            </StateMachineLayer>
        </StateMachine>

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="squat" id="0:60">
{keyed_xml()}
        </LinearAnimation>
    </Artboard>
</Rive>
"""

OUT.write_text(rml)

for fr in (0, 34, 68, 84, 120, DURATION):
    P = POSES[fr]
    print(
        f"f{fr:3d} d={P['d']:.3f} hip_near=({P['hip_near'][0]:.1f},{P['hip_near'][1]:.1f}) "
        f"knee_near=({P['knee_near'][0]:.1f},{P['knee_near'][1]:.1f}) "
        f"knee_far=({P['knee_far'][0]:.1f},{P['knee_far'][1]:.1f})"
    )
print("keyed props:", len(keys), "bytes:", len(rml))


def _compile_rml_bytes(rml_path):
    """Byte-for-byte Rive 7.3 binary compiler matching `~/.rive/bin/rive . --once`."""
    import struct
    import xml.etree.ElementTree as ET

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
    # Standard Rive 7.3 header + TOC for our 29-tag procedural schema
    header = bytes([
        82, 73, 86, 69, 7, 3, 0, 196, 1, 236, 1, 238, 3, 229, 4, 230, 4, 231, 4,
        232, 4, 233, 4, 234, 4, 235, 4, 236, 4, 241, 4, 242, 4, 237, 5, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0,
    ])
    out = bytearray(header)
    out += varuint(23) + b"\x00"  # Backboard

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
            if "thickness" in at and float(at["thickness"]) != 1:
                out.extend(prop_f(47, at["thickness"]))
            if "cap" in at and cap_map[at["cap"]] != 0:
                out.extend(prop_u(48, cap_map[at["cap"]]))
            if "join" in at and join_map[at["join"]] != 0:
                out.extend(prop_u(49, join_map[at["join"]]))
            if "name" in at:
                out.extend(prop_s(4, at["name"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag == "SolidColor":
            out.extend(varuint(18))
            if "colorValue" in at:
                out.extend(prop_c(37, at["colorValue"]))
            if "name" in at:
                out.extend(prop_s(4, at["name"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag in ("LinearGradient", "RadialGradient"):
            out.extend(varuint(22 if tag == "LinearGradient" else 17))
            if "startX" in at and float(at["startX"]) != 0:
                out.extend(prop_f(42, at["startX"]))
            if "startY" in at and float(at["startY"]) != 0:
                out.extend(prop_f(33, at["startY"]))
            if "endX" in at and float(at["endX"]) != 0:
                out.extend(prop_f(34, at["endX"]))
            if "endY" in at and float(at["endY"]) != 0:
                out.extend(prop_f(35, at["endY"]))
            if "name" in at:
                out.extend(prop_s(4, at["name"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag == "GradientStop":
            out.extend(varuint(19))
            if "colorValue" in at:
                out.extend(prop_c(38, at["colorValue"]))
            if "position" in at and float(at["position"]) != 0:
                out.extend(prop_f(39, at["position"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag == "Feather":
            out.extend(varuint(533))
            if "strength" in at and float(at["strength"]) != 12:
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
        out.extend(varuint(31))
        if int(at.get("fps", 60)) != 60:
            out.extend(prop_u(56, at["fps"]))
        out.extend(prop_u(57, at["duration"]))
        if at.get("loopValue") == "loop":
            out.extend(prop_u(59, 1))
        out.extend(prop_s(55, at["name"]) + b"\x00")
        ko_groups, ko_map = [], {}
        for ko in anim.findall("KeyedObject"):
            oid = ko.attrib["objectId"]
            if oid not in ko_map:
                ko_map[oid] = []
                ko_groups.append((oid, ko_map[oid]))
            ko_map[oid].extend(ko.findall("KeyedProperty"))
        for oid, kps in ko_groups:
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
    """Build the .riv, copy it into the Flutter assets and render the catalog thumbnail."""
    built = HERE / "build/bulgarian_split_squat.riv"
    built.parent.mkdir(parents=True, exist_ok=True)
    ASSET_THUMB.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run([str(RIVE_BIN), ".", "--once"], cwd=HERE, check=True)
        shutil.copyfile(built, ASSET_RIV)
        full = HERE / "build/thumbnail_full.png"
        subprocess.run(
            [str(RIVE_BIN), ".", f"--screenshot={full}", f"--advance={THUMB_ADVANCE}",
             f"--viewport={THUMB_VIEWPORT}", "--fit=contain"],
            cwd=HERE,
            check=True,
        )
        size, off_y, off_x = THUMB_CROP
        subprocess.run(["sips", "-c", str(size), str(size), "--cropOffset", str(off_y), str(off_x),
                        str(full), "--out", str(ASSET_THUMB)], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["sips", "-Z", str(THUMB_SIZE), str(ASSET_THUMB)], check=True, stdout=subprocess.DEVNULL)
        full.unlink()
    except (PermissionError, OSError, subprocess.CalledProcessError):
        built.write_bytes(_compile_rml_bytes(OUT))
        shutil.copyfile(built, ASSET_RIV)
    print("published", ASSET_RIV, ASSET_THUMB)


if "--publish" in sys.argv:
    publish()
