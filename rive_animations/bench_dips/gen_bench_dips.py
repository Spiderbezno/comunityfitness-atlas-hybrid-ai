"""Generates rive_animations/bench_dips/scene.rml (and optionally publishes).

Three-quarter front-side view of a stylized athlete performing bench dips at
60 fps on a 16:9 (640x360) artboard.

Matches the exact character design of ab_wheel_rollout, arnold_press, and
barbell_row (palette, 3-stop linear gradients, Catmull-Rom smooth curves,
feathered highlights / core shadows, and orange-to-red muscle activation glow).

Kinematics:
- Hands remain planted on the front edge of the bench pad behind the torso.
- Heels rest on the floor in front; legs pivot naturally as the hips descend
  and ascend.
- Two-bone IK solves both arms (Shoulder -> Elbow -> Hand) and both legs
  (Hip -> Knee -> Ankle) every frame so bone lengths stay rigid.
- Primary muscle activations: triceps brachii (long + lateral heads), pectoralis
  major (near + far), anterior deltoid, and serratus anterior.

Usage (from this directory):
    python3 gen_bench_dips.py            # regenerate scene.rml
    python3 gen_bench_dips.py --publish  # + build .riv, copy to assets, render thumbnail
"""

import math
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "scene.rml"
REPO = HERE.parent.parent
ASSET_RIV = REPO / "assets/animations/bench_dips.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/bench_dips.png"
THUMB_ADVANCE = "0.0s"  # top lockout: maximum concentric triceps/chest activation
THUMB_VIEWPORT = "1280x720"  # 2x the 640x360 artboard
THUMB_CROP = (680, 20, 250)  # square size, offsetY, offsetX in the 2x render
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

# 16:9 standard canvas matching ab_wheel_rollout, arnold_press, and barbell_row
W, H = 640, 360
FLOOR = 300.0

# Anthropometric constants (same character proportions)
THIGH, SHIN, FOOT = 72.0, 70.0, 24.0
UPPER_ARM, FOREARM = 62.0, 58.0
SHOULDER_IN_SPINE = (96.0, -9.0)
FAR_SHOULDER_IN_SPINE = (95.0, 14.0)
NECK_IN_SPINE = (110.0, -3.5)

# Fixed hand anchors on the front edge of the 3/4 bench pad
HAND_NEAR = (236.0, 207.5)
HAND_FAR = (284.0, 193.0)
FAR_LEG_OFFSET = (14.0, -5.0)

# Heel/ankle floor anchor (slides slightly as the legs pivot)
ANKLE_X_TOP = 414.0
ANKLE_X_BOT = 424.0
ANKLE_Y = FLOOR - 9.0

# Timeline (frames @60fps): lower 1.15s, bottom pause 0.25s, push up 1.15s, top hold 0.45s = 3.0s (180 frames)
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


def dip_depth(frame):
    """0.0 at top lockout, 1.0 at bottom of the dip."""
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
    """Compute full body joint angles at dip depth d in [0, 1]."""
    # Hips descend in front of the bench pad; torso stays upright with a slight forward lean at the bottom.
    hip = (lerp(292.0, 297.0, d), lerp(198.0, 246.0, d))
    spine = math.radians(lerp(-83.0, -87.0, d))
    # Head points +40 deg in Neck space; neck_local ~37-41 deg aligns gaze horizontally forward
    neck_local = math.radians(lerp(37.0, 41.0, d))
    shoulder = add(hip, rot(SHOULDER_IN_SPINE, spine))

    # Near Arm IK: shoulder -> elbow -> HAND_NEAR (elbow bends backward to the left, bend_sign = +1)
    ua, fa_world, elbow = solve_ik(shoulder, HAND_NEAR, UPPER_ARM, FOREARM, bend_sign=1.0)
    ua_local = ua - spine
    forearm_local = fa_world - ua

    # Far Arm IK: far shoulder -> far elbow -> HAND_FAR
    far_shoulder = add(hip, rot(FAR_SHOULDER_IN_SPINE, spine))
    far_ua, far_fa_world, far_elbow = solve_ik(far_shoulder, HAND_FAR, UPPER_ARM, FOREARM, bend_sign=1.0)
    far_ua_local = far_ua - spine
    far_forearm_local = far_fa_world - far_ua

    # Leg IK: hip -> knee -> ankle (knee stays slightly above the chord, bend_sign = -1)
    ankle = (lerp(ANKLE_X_TOP, ANKLE_X_BOT, d), ANKLE_Y)
    thigh, shin_world, knee = solve_ik(hip, ankle, THIGH, SHIN, bend_sign=-1.0)
    shin_local = shin_world - thigh
    # Keep foot angled up with heel planted on the floor
    foot_world = math.radians(lerp(-42.0, -34.0, d))
    foot_local = foot_world - shin_world

    return {
        "d": d,
        "hip": hip,
        "spine": spine,
        "neck_local": neck_local,
        "shoulder": shoulder,
        "elbow": elbow,
        "ua": ua,
        "ua_local": ua_local,
        "forearm_local": forearm_local,
        "far_ua_local": far_ua_local,
        "far_forearm_local": far_forearm_local,
        "thigh": thigh,
        "shin_local": shin_local,
        "foot_local": foot_local,
        "ankle": ankle,
        "knee": knee,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(dip_depth(fr)) for fr in FRAMES}

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


def ellipse_shape(indent, name, x, y, w, h, paint_xml):
    return (
        f'{indent}<Shape x="{f(float(x))}" y="{f(float(y))}" name="{name}">\n'
        f'{indent}    <Ellipse width="{f(float(w))}" height="{f(float(h))}" name="{name}Ellipse"/>\n'
        f"{indent}    {paint_xml}\n"
        f"{indent}</Shape>"
    )


# ---------------------------------------------------------------- palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FF9AA8BC", "FF738399", "FF4B5A70")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF2B3649", "FF1B2433", "FF101722")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "4D0F172A"
MUSCLE_LOW = (0x59, 0xFB, 0x92, 0x3C)  # warm orange at lockout
MUSCLE_HIGH = (0xF2, 0xEF, 0x44, 0x44)  # intense red at bottom of dip
MUSCLE_LINE_LOW = (0x40, 0xC2, 0x41, 0x0C)
MUSCLE_LINE_HIGH = (0xCC, 0x8B, 0x1A, 0x1A)


def argb_lerp(a, b, t):
    return "".join(f"{round(lerp(x, y, t)):02X}" for x, y in zip(a, b))


def skin_fill(name, y0, y1, tones):
    return f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *tones)}</Fill>'


keys = []  # (objectId, propertyKey, kind, [(frame, value)])


def key_double(obj, prop, fn):
    keys.append((obj, prop, "double", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def key_color(obj, prop, fn):
    keys.append((obj, prop, "color", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def muscle_t(p):
    return 0.18 + 0.82 * ((1.0 - p["d"]) ** 1.1)


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


# ---------------------------------------------------------------- anatomy (ab_wheel_rollout character)
# Limb local frames: +x runs along the bone, -y is the anterior side
# (biceps / front delt / quads / tibia), +y is the posterior side (triceps / hamstrings / calf).

UPPER_ARM_PTS = [(-15, 0), (-12, -11), (2, -14.5), (18, -12.5), (31, -12), (45, -10), (57, -7.5), (64, -6.5),
                 (69, 0), (64, 6.5), (52, 8.5), (36, 12.5), (20, 13), (4, 13.5), (-10, 10)]
UPPER_ARM_HI = [(6, -9), (20, -8.5), (33, -8), (50, -5.5)]
UPPER_ARM_SH = [(6, 9.5), (22, 9.5), (38, 8.5), (54, 5)]
# Prominent triceps brachii (lateral + long heads) on the +y posterior aspect of the upper arm
TRICEPS_LAT_PTS = [(8, 2.5), (22, 3.5), (38, 4.0), (52, 3.5), (56, 6.5), (42, 11.0), (24, 12.0), (8, 11.5), (2, 7.0)]
TRICEPS_LONG_PTS = [(12, 8.0), (28, 9.5), (44, 8.5), (36, 12.2), (18, 12.8), (6, 11.0)]

DELT_PTS = [(-17, -1), (-12, -13), (1, -17.5), (16, -15), (28, -8.5), (27, 2), (15, 9.5), (0, 12.5), (-12, 9)]
FRONT_DELT_PTS = [(-6, -11), (4, -15.5), (17, -13), (26, -7), (18, -1.5), (5, -3)]

FOREARM_PTS = [(-9, 0), (-8, -7.5), (6, -10.5), (21, -9), (37, -6.5), (51, -5), (58, -4.5),
               (62, 0), (58, 4.5), (44, 5.5), (27, 7.5), (10, 8.5), (-4, 8)]
FOREARM_HI = [(6, -6.5), (22, -6), (42, -3.8)]
FOREARM_SH = [(8, 5.5), (28, 4.8), (46, 3.2)]
# Hand gripping the front edge of the bench pad (palm on top, fingers wrapping down the front lip)
HAND_PTS = [(-5, -7.5), (7, -8.5), (15, -3.5), (16, 4.5), (9, 9.0), (-3, 7.5), (-7, 0)]

# 3/4 front-side torso: slightly broader chest/abdomen (+y) so both pecs and 3/4 abs read clearly
TORSO_PTS = [(-24, 7), (-28, -7), (-17, -20), (0, -19.5), (22, -16), (48, -17.5), (72, -23.5), (92, -26.0),
             (108, -21), (118, -12), (117, -1), (112, 12), (104, 24), (90, 29.5), (75, 26.0), (60, 21.5),
             (44, 18.5), (26, 19.5), (9, 22), (-8, 21), (-19, 14)]
TORSO_HI = [(-4, -10), (24, -8), (52, -10), (80, -15.5), (98, -14)]
TORSO_SH = [(22, 12), (46, 11), (64, 15), (86, 22)]
GLUTE_HI = [(-22, -2), (-16, -13), (-4, -15)]
SHORTS_TORSO_PTS = [(-29, -6), (-18, -21.5), (0, -21), (22, -17), (24, 19.5), (9, 23), (-9, 22), (-23, 14)]

# Pectoralis major (near right pec + foreshortened far left pec across the sternum)
PEC_NEAR_PTS = [(74, 2.0), (86, -2.0), (99, 0.0), (104, 11.0), (99, 21.5), (86, 23.0), (74, 18.5), (70, 9.5)]
PEC_FAR_PTS = [(103, 13.0), (103, 22.5), (92, 28.5), (78, 25.5), (75, 19.5), (88, 22.5)]
# Serratus anterior / anterolateral ribs under the pec
SERRATUS_PTS = [(48, -3.5), (66, -6.5), (76, -1.0), (71, 8.5), (56, 7.5), (46, 2.5)]
# Upper trapezius / neck activation (in Neck local space, between skull base and deltoid)
TRAP_PTS = [(-2, -6.5), (10, -7.2), (16, -2.5), (7, 2.5), (-4, -0.5)]

NECK_PTS = [(-3, -6.8), (9, -7.5), (19, -5.5), (20, 7.5), (9, 9.5), (-3, 8.0)]
HEAD_PTS = [(12, -6), (19, -15), (33, -18.5), (46, -12), (51, -1), (49, 9), (45, 14), (46.5, 18.5), (40, 20.5),
            (36, 23), (29, 25), (21, 21), (15, 13), (11, 4)]
HAIR_PTS = [(13, -9), (22, -17), (36, -19.5), (47, -13), (50, -4), (41, -8), (27, -9.5), (17, -4)]
HEAD_HI = [(20, -10), (34, -13), (44, -8)]

THIGH_PTS = [(-19, 0), (-14, -12), (6, -17), (30, -17.5), (52, -14.5), (66, -11), (77, -9.5),
             (83, 0), (77, 9), (60, 10), (40, 13), (18, 17), (-2, 19), (-16, 12)]
THIGH_HI = [(8, -12.5), (32, -13.5), (56, -10)]
THIGH_SH = [(10, 13.5), (36, 9.5), (60, 6.5)]
SHORTS_THIGH_PTS = [(-21, 0), (-15, -14), (6, -19), (32, -18.5), (34, 15.0), (14, 19), (-4, 21), (-18, 13)]

SHIN_PTS = [(-11, 0), (-10, -8), (14, -8.5), (40, -7), (62, -5), (72, -4.5),
            (76, 0), (72, 5), (56, 6.5), (36, 10.5), (18, 14), (4, 12.5), (-8, 8.5)]
SHIN_HI = [(10, -5), (40, -4.5), (62, -3)]  # anterior shin faces up-right: light it
SHIN_SH = [(18, 9), (36, 7.5), (56, 4.5)]
FOOT_PTS = [(-9, 0), (-7, -6), (8, -6.5), (22, -4.5), (28, 0), (24, 4.5), (10, 7), (-6, 7)]


def sculpted_abs(indent):
    """Neutral sculpted 3/4 rectus abdominis and oblique lines (matches reference image)."""
    out = []
    paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="180F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.85" join="round" name="AbsEdge"><SolidColor colorValue="380F172A" name="AbsEdgeColor"/></Stroke>'
    )
    # Near column of abs
    for k, (x0, x1, y_in, y_out) in enumerate((
        (59, 70, 9.5, 17.5),
        (46, 57, 8.5, 16.5),
        (33, 44, 9.0, 17.0),
        (21, 31, 10.0, 17.5),
    )):
        cx = (x0 + x1) / 2
        pts = [(x0, y_in), (cx, y_in - 0.5), (x1, y_in), (x1, y_out), (cx, y_out + 0.6), (x0, y_out)]
        out.append(smooth_shape(indent, f"AbsNear{k + 1}", pts, paint))
    # Foreshortened far column of abs along the anterior contour
    for k, (x0, x1, y_in, y_out) in enumerate((
        (59, 70, 18.8, 23.0),
        (46, 57, 17.8, 21.5),
        (33, 44, 18.2, 21.5),
    )):
        cx = (x0 + x1) / 2
        pts = [(x0, y_in), (x1, y_in), (x1, y_out), (cx, y_out + 0.4), (x0, y_out)]
        out.append(smooth_shape(indent, f"AbsFar{k + 1}", pts, paint))
    # Linea alba + oblique definition
    out.append(stroke_shape(indent, "LineaAlba", [(73, 18.5), (52, 17.2), (26, 18.0)], 1.1, "330F172A", 1.0))
    out.append(stroke_shape(indent, "ObliqueLine1", [(48, 2.0), (39, 6.5), (29, 9.0)], 1.3, "2E0F172A", 1.2))
    out.append(stroke_shape(indent, "ObliqueLine2", [(38, 1.0), (29, 5.5), (21, 8.5)], 1.3, "2E0F172A", 1.2))
    return "\n".join(out)


def shading(indent, nm, hi, sh, hw=3.2, sw=6.0):
    return [
        stroke_shape(indent, nm + "Highlight", hi, hw * 1.5, HIGHLIGHT, 4),
        stroke_shape(indent, nm + "CoreShadow", sh, sw * 1.3, CORE_SHADOW, 7),
    ]


def arm_branch(indent, prefix, far):
    """UpperArm -> Forearm -> Hand branch attached to Spine (or Far rig)."""
    skin = SKIN_FAR if far else SKIN
    ua_id, fa_id = nid(), nid()
    ua_key = "far_ua_local" if far else "ua_local"
    fa_key = "far_forearm_local" if far else "forearm_local"
    key_double(ua_id, 15, lambda p: p[ua_key])
    key_double(fa_id, 15, lambda p: p[fa_key])
    p0 = POSES[0]
    sx, sy = FAR_SHOULDER_IN_SPINE if far else SHOULDER_IN_SPINE
    i2 = indent + "    "
    i3 = i2 + "    "
    out = [f'{indent}<Node x="{f(sx)}" y="{f(sy)}" rotation="{f(p0[ua_key])}" name="{prefix}UpperArm" id="{ua_id}">']

    # Forearm + Hand (drawn in front of the elbow joint)
    out.append(f'{i2}<Node x="{f(UPPER_ARM)}" rotation="{f(p0[fa_key])}" name="{prefix}Forearm" id="{fa_id}">')
    out.append(smooth_shape(i3, f"{prefix}Hand", HAND_PTS, skin_fill(prefix + "Hand", -8, 9, skin), x=FOREARM))
    if not far:
        out += shading(i3, prefix + "Forearm", FOREARM_HI, FOREARM_SH, 2.6, 4.5)
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", FOREARM_PTS, skin_fill(prefix + "Forearm", -10, 9, skin)))
    out.append(f"{i2}</Node>")

    # Deltoid cap + Front Delt activation
    if not far:
        out.append(smooth_shape(i2, "FrontDeltActivation", FRONT_DELT_PTS, muscle_paint("FrontDelt")))
        out.append(stroke_shape(i2, "DeltHighlight", [(-6, -9), (6, -12), (18, -9)], 3, HIGHLIGHT, 3.5))
    else:
        out.append(smooth_shape(i2, "FarFrontDeltActivation", FRONT_DELT_PTS, muscle_paint("FarFrontDelt")))
    out.append(smooth_shape(i2, f"{prefix}Deltoid", DELT_PTS, skin_fill(prefix + "Deltoid", -17, 12, skin)))

    # Upper arm + Triceps brachii activation
    if not far:
        out.append(smooth_shape(i2, "TricepsLongActivation", TRICEPS_LONG_PTS, muscle_paint("TricepsLong")))
        out.append(smooth_shape(i2, "TricepsLatActivation", TRICEPS_LAT_PTS, muscle_paint("TricepsLat")))
        out += shading(i2, prefix + "UpperArm", UPPER_ARM_HI, UPPER_ARM_SH)
    else:
        out.append(smooth_shape(i2, "FarTricepsActivation", TRICEPS_LAT_PTS, muscle_paint("FarTriceps")))
    out.append(smooth_shape(i2, f"{prefix}UpperArmShape", UPPER_ARM_PTS, skin_fill(prefix + "UpperArm", -14, 13, skin)))
    out.append(f"{indent}</Node>")
    return "\n".join(out)


def leg_branch(indent, prefix, far):
    """Thigh -> Shin -> Foot branch attached to Hip."""
    skin = SKIN_FAR if far else SKIN
    shorts = SHORTS_FAR if far else SHORTS
    thigh_id, shin_id, foot_id = nid(), nid(), nid()
    key_double(thigh_id, 15, lambda p: p["thigh"])
    key_double(shin_id, 15, lambda p: p["shin_local"])
    key_double(foot_id, 15, lambda p: p["foot_local"])
    p0 = POSES[0]
    i2 = indent + "    "
    i3 = i2 + "    "
    out = [f'{indent}<Node rotation="{f(p0["thigh"])}" name="{prefix}Thigh" id="{thigh_id}">']
    out.append(f'{i2}<Node x="{f(THIGH)}" rotation="{f(p0["shin_local"])}" name="{prefix}Shin" id="{shin_id}">')
    out.append(f'{i3}<Node x="{f(SHIN)}" rotation="{f(p0["foot_local"])}" name="{prefix}Foot" id="{foot_id}">')
    out.append(smooth_shape(i3 + "    ", f"{prefix}FootShape", FOOT_PTS, skin_fill(prefix + "Foot", -7, 7, skin)))
    out.append(f"{i3}</Node>")
    out.append(ellipse_shape(i3, f"{prefix}KneeCap", 1, -1, 21, 19, skin_fill(prefix + "Knee", -10, 10, skin)))
    if not far:
        out += shading(i3, prefix + "Shin", SHIN_HI, SHIN_SH, 3, 4.5)
    out.append(smooth_shape(i3, f"{prefix}ShinShape", SHIN_PTS, skin_fill(prefix + "Shin", -9, 14, skin)))
    out.append(f"{i2}</Node>")
    out.append(smooth_shape(i2, f"{prefix}ThighShorts", SHORTS_THIGH_PTS, skin_fill(prefix + "ThighShorts", -19, 21, shorts)))
    if not far:
        out += shading(i2, prefix + "Thigh", THIGH_HI, THIGH_SH, 3.5, 7)
    out.append(smooth_shape(i2, f"{prefix}ThighShape", THIGH_PTS, skin_fill(prefix + "Thigh", -18, 19, skin)))
    out.append(f"{indent}</Node>")
    return "\n".join(out)


def near_rig():
    """Foreground right arm + torso/head + right leg."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    hip_id, spine_id, neck_id = nid(), nid(), nid()
    key_double(hip_id, 13, lambda p: p["hip"][0])
    key_double(hip_id, 14, lambda p: p["hip"][1])
    key_double(spine_id, 15, lambda p: p["spine"])
    key_double(neck_id, 15, lambda p: p["neck_local"])
    p0 = POSES[0]

    out = [f'{ind}<Node x="{f(p0["hip"][0])}" y="{f(p0["hip"][1])}" name="Hip" id="{hip_id}">']
    out.append(f'{i2}<Node rotation="{f(p0["spine"])}" name="Spine" id="{spine_id}">')

    # 1. Near (right) arm in foreground of the torso
    out.append(arm_branch(i3, "", False))

    # 2. Head & Neck
    nx, ny = NECK_IN_SPINE
    out.append(f'{i3}<Node x="{f(nx)}" y="{f(ny)}" rotation="{f(p0["neck_local"])}" name="Neck" id="{neck_id}">')
    i4 = i3 + "    "
    out.append(smooth_shape(i4, "Hair", HAIR_PTS, f'<Fill name="HairFill">{grad("HairGrad", 0, -19, 0, -4, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i4, "Ear", 27, 2, 7, 10, solid("Ear", "FFA3B1C4")))
    out.append(stroke_shape(i4, "HeadHighlight", HEAD_HI, 3, HIGHLIGHT, 4))
    out.append(smooth_shape(i4, "Head", HEAD_PTS, skin_fill("Head", -18, 25, SKIN)))
    out.append(smooth_shape(i4, "TrapActivation", TRAP_PTS, muscle_paint("Trap", 0.85)))
    out.append(smooth_shape(i4, "NeckShape", NECK_PTS, skin_fill("Neck", -9, 11, SKIN)))
    out.append(f"{i3}</Node>")

    # 3. Torso muscle activations (Pecs, Serratus) + sculpted 6-pack abs
    out.append(smooth_shape(i3, "PecNearActivation", PEC_NEAR_PTS, muscle_paint("PecNear", 1.0)))
    out.append(smooth_shape(i3, "PecFarActivation", PEC_FAR_PTS, muscle_paint("PecFar", 0.9)))
    out.append(smooth_shape(i3, "SerratusActivation", SERRATUS_PTS, muscle_paint("Serratus", 0.85)))
    out.append(sculpted_abs(i3))
    out.append(smooth_shape(i3, "Shorts", SHORTS_TORSO_PTS, skin_fill("Shorts", -21, 22, SHORTS)))
    out.append(stroke_shape(i3, "GluteHighlight", GLUTE_HI, 3, "59FFFFFF", 4))
    out += shading(i3, "Torso", TORSO_HI, TORSO_SH, 4, 8)
    out.append(smooth_shape(i3, "Torso", TORSO_PTS, skin_fill("Torso", -26, 29, SKIN)))
    out.append(f"{i2}</Node>")

    # 4. Near (right) leg
    out.append(leg_branch(i2, "", False))
    out.append(f"{ind}</Node>")
    return "\n".join(out)


def far_leg_rig():
    """Far (left) leg slightly offset in 3/4 perspective behind the near leg."""
    ind = "        "
    i2 = ind + "    "
    hip_id = nid()
    ox, oy = FAR_LEG_OFFSET
    key_double(hip_id, 13, lambda p: p["hip"][0] + ox)
    key_double(hip_id, 14, lambda p: p["hip"][1] + oy)
    p0 = POSES[0]
    return "\n".join([
        f'{ind}<Node x="{f(p0["hip"][0] + ox)}" y="{f(p0["hip"][1] + oy)}" name="FarLegHip" id="{hip_id}">',
        leg_branch(i2, "Far", True),
        f"{ind}</Node>",
    ])


def far_arm_rig():
    """Far (left) arm anchored on the far side of the chest and reaching to HAND_FAR on the bench."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    hip_id, spine_id = nid(), nid()
    key_double(hip_id, 13, lambda p: p["hip"][0])
    key_double(hip_id, 14, lambda p: p["hip"][1])
    key_double(spine_id, 15, lambda p: p["spine"])
    p0 = POSES[0]
    return "\n".join([
        f'{ind}<Node x="{f(p0["hip"][0])}" y="{f(p0["hip"][1])}" name="FarArmHip" id="{hip_id}">',
        f'{i2}<Node rotation="{f(p0["spine"])}" name="FarSpine" id="{spine_id}">',
        arm_branch(i3, "Far", True),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


def bench():
    """3/4 perspective flat gym bench matching the reference image."""
    ind = "        "
    i2 = ind + "    "
    metal_front = f'<Fill name="MetalFrontFill">{grad("MetalFrontGrad", 160, 220, 195, 298, "FFF1F5F9", "FF94A3B8")}</Fill>'
    metal_back = f'<Fill name="MetalBackFill">{grad("MetalBackGrad", 285, 195, 315, 270, "FFE2E8F0", "FF64748B")}</Fill>'
    metal_rail = f'<Fill name="MetalRailFill">{grad("MetalRailGrad", 180, 270, 305, 240, "FFCBD5E1", "FF64748B")}</Fill>'
    pad_top = f'<Fill name="PadTopFill">{grad("PadTopGrad", 210, 175, 245, 226, "FF334155", "FF1E293B")}</Fill>'
    pad_side = f'<Fill name="PadSideFill">{grad("PadSideGrad", 220, 195, 220, 238, "FF1E293B", "FF0B1120")}</Fill>'
    rubber = solid("Rubber", "FF0F172A")

    # Bench pad geometry in 3/4 view (crisp straight upholstered edges with rounded corners):
    # Front-right edge passes directly under HAND_NEAR (242, 206) and HAND_FAR (284, 193)
    top_pts = [(162, 227), (324, 177), (298, 166), (138, 215)]
    front_skirt_pts = [(162, 226), (324, 176), (324, 190), (162, 240)]
    left_skirt_pts = [(138, 215), (162, 226), (162, 240), (138, 228)]

    return "\n".join([
        f'{ind}<Node name="Bench">',
        # Pad top & 3D side skirts (drawn above the metal frame)
        stroke_shape(i2, "PadEdgeHighlight", [(164, 226.5), (242, 202.5), (320, 178)], 1.5, "40FFFFFF", 1.0),
        poly_shape(i2, "BenchPadTop", top_pts, pad_top, radius=4.5),
        poly_shape(i2, "BenchPadFrontSkirt", front_skirt_pts, pad_side, radius=3.5),
        poly_shape(i2, "BenchPadLeftSkirt", left_skirt_pts, pad_side, radius=3.5),

        # Front-left leg post (angled slightly outward) + rubber foot
        poly_shape(i2, "FrontFootCap", [(158, 296), (182, 296), (182, 300), (158, 300)], rubber),
        poly_shape(i2, "FrontLegPost", [(175, 235), (189, 231), (177, 297), (163, 297)], metal_front),

        # Longitudinal under-bar connecting front and rear legs
        poly_shape(i2, "UnderRail", [(177, 275), (298, 241), (298, 249), (176, 284)], metal_rail),
        stroke_shape(i2, "UnderRailShadow", [(179, 275), (296, 241)], 2.0, "FF0F172A", 0.0, cap="butt"),

        # Back-right leg post + horizontal stabilizer T-bar
        poly_shape(i2, "RearStabilizerFootR", [(322, 268), (336, 270), (336, 274), (322, 272)], rubber),
        poly_shape(i2, "RearStabilizerFootL", [(262, 261), (274, 263), (274, 267), (262, 265)], rubber),
        poly_shape(i2, "RearStabilizerBar", [(266, 259), (334, 267), (334, 272), (266, 264)], metal_back),
        poly_shape(i2, "RearLegPost", [(292, 186), (304, 182), (304, 265), (292, 264)], metal_back),
        f"{ind}</Node>",
    ])


def shadow():
    ind = "        "
    sid = nid()
    key_double(sid, 13, lambda p: lerp(345.0, 352.0, p["d"]))
    key_double(sid, 16, lambda p: lerp(1.05, 1.22, p["d"]))
    return "\n".join([
        # Dynamic athlete shadow (under hips -> heels)
        f'{ind}<Shape x="345" y="{f(FLOOR + 1)}" scaleX="1.05" scaleY="0.08" name="BodyShadow" id="{sid}">\n'
        f'{ind}    <Ellipse width="200" height="200" name="ShadowEllipse"/>\n'
        f'{ind}    <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="100" endY="0" name="ShadowGrad">'
        f'<GradientStop colorValue="B3000000" position="0"/><GradientStop colorValue="59000000" position="0.6"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{ind}</Shape>",
        # Static bench shadow
        f'{ind}<Shape x="235" y="{f(FLOOR - 4)}" scaleX="0.85" scaleY="0.07" name="BenchShadow">\n'
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


near_xml = near_rig()
far_leg_xml = far_leg_rig()
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
    <!-- Bench Dips: 3/4 view, 60 fps, 16:9 (640x360), generated by gen_bench_dips.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="BenchDips" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- Near-side athlete (right arm, torso, head, right leg) -->
{near_xml}

        <!-- Far-side left leg -->
{far_leg_xml}

        <!-- 3/4 Gym Bench -->
{bench_xml}

        <!-- Floor shadows -->
{shd_xml}

{scenery()}

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

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="Dip" id="0:60">
{keyed_xml()}
        </LinearAnimation>
    </Artboard>
</Rive>
"""

OUT.write_text(rml)

for fr in (0, 34, 68, 84, 120, DURATION):
    P = POSES[fr]
    print(
        f"f{fr:3d} d={P['d']:.3f} hip=({P['hip'][0]:.1f},{P['hip'][1]:.1f}) "
        f"sh=({P['shoulder'][0]:.1f},{P['shoulder'][1]:.1f}) elb=({P['elbow'][0]:.1f},{P['elbow'][1]:.1f}) "
        f"ua={math.degrees(P['ua']):.0f} fa_loc={math.degrees(P['forearm_local']):.0f} "
        f"knee=({P['knee'][0]:.1f},{P['knee'][1]:.1f})"
    )
print("keyed props:", len(keys), "bytes:", len(rml))


def publish():
    """Build the .riv, copy it into the Flutter assets and render the catalog thumbnail."""
    subprocess.run([str(RIVE_BIN), ".", "--once"], cwd=HERE, check=True)
    built = HERE / "build/bench_dips.riv"
    shutil.copyfile(built, ASSET_RIV)
    ASSET_THUMB.parent.mkdir(parents=True, exist_ok=True)
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
    print("published", ASSET_RIV, ASSET_THUMB)


if "--publish" in sys.argv:
    publish()
