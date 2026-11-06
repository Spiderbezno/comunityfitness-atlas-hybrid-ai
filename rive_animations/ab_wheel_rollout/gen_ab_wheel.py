"""Generates rive_animations/ab_wheel_rollout/scene.rml (and optionally publishes).

Side-view stylized athlete performing an ab wheel rollout at 60 fps.

Rig: Node hierarchy (hip root -> spine -> neck/head, shoulder -> upper arm ->
forearm -> hand; hip -> thigh -> shin -> foot). Poses are joint rotations plus
hip translation. Every keyed value is sampled from one eased extension
parameter e(t), so the knee stays planted, the hands stay on the wheel hub and
the wheel rotation matches its travel (rotation = dx / radius).

Anatomy: muscle-shaped silhouettes built from smooth Catmull-Rom outlines
(emitted as CubicMirroredVertex), 3-stop base gradients, feathered highlight and
core-shadow strokes, and red activation shapes (rectus abdominis segments, lats,
front delt) whose colour intensifies with extension.

Usage (from this directory):
    python3 gen_ab_wheel.py            # regenerate scene.rml
    python3 gen_ab_wheel.py --publish  # + build .riv, copy to assets, render thumbnail
"""

import math
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "scene.rml"
REPO = HERE.parent.parent
ASSET_RIV = REPO / "assets/animations/ab_wheel_rollout.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/ab_wheel_rollout.png"
THUMB_ADVANCE = "0.6s"  # mid-rollout: the most readable silhouette for a small square tile
THUMB_VIEWPORT = "1280x720"  # 2x the artboard
THUMB_CROP = (640, 80, 180)  # square size, offsetY, offsetX in the 2x render (frames the athlete)
THUMB_SIZE = 256  # final px; the catalog tile is 48 dp
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

W, H = 640, 360
FLOOR = 300.0
KNEE = (190.0, 291.0)  # knee centre, cap resting on the floor
WHEEL_R = 23.0
WHEEL_Y = FLOOR - WHEEL_R

THIGH, SHIN, FOOT = 72.0, 70.0, 24.0
SHOULDER_IN_SPINE = (100.0, -3.0)
NECK_IN_SPINE = (106.0, -10.0)
UPPER_ARM, FOREARM = 60.0, 56.0

SHIN_ABS = math.radians(191.0)
FOOT_LOCAL = math.radians(-68.0)

FAR_OFFSET = (6.0, -5.0)

# Timeline (frames @60fps): rollout 1.6s, hold 0.3s, return 1.4s, hold 0.3s.
ROLL_OUT, HOLD_EXT, ROLL_BACK, HOLD_START = 96, 18, 84, 18
DURATION = ROLL_OUT + HOLD_EXT + ROLL_BACK + HOLD_START
STEP = 3


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


EASE = cubic_bezier(0.45, 0.0, 0.4, 1.0)


def extension(frame):
    fr = frame % DURATION
    if fr <= ROLL_OUT:
        return EASE(fr / ROLL_OUT)
    fr -= ROLL_OUT
    if fr <= HOLD_EXT:
        return 1.0
    fr -= HOLD_EXT
    if fr <= ROLL_BACK:
        return 1.0 - EASE(fr / ROLL_BACK)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def pose(e):
    # Thigh: hip -> knee direction. 84 deg = near-vertical thigh, hip slightly
    # behind the knee (reference start pose); 167 deg = almost flat.
    thigh = math.radians(lerp(84.0, 167.0, e))
    spine = math.radians(lerp(-33.0, -6.0, e))
    # Negative bend = slight elbow flexion (forearm toward the anterior side).
    bend = math.radians(-lerp(7.0, 3.0, e))
    neck_local = math.radians(lerp(16.0, 4.0, e))
    hip = (KNEE[0] - THIGH * math.cos(thigh), KNEE[1] - THIGH * math.sin(thigh))
    shoulder = add(hip, rot(SHOULDER_IN_SPINE, spine))

    def hand_for(ua):
        elbow = add(shoulder, (UPPER_ARM * math.cos(ua), UPPER_ARM * math.sin(ua)))
        return add(elbow, (FOREARM * math.cos(ua + bend), FOREARM * math.sin(ua + bend)))

    lo, hi = math.radians(-20.0), math.radians(100.0)
    for _ in range(80):
        mid = (lo + hi) / 2
        if hand_for(mid)[1] < WHEEL_Y:
            lo = mid
        else:
            hi = mid
    ua = (lo + hi) / 2
    hand = hand_for(ua)
    return {
        "hip": hip,
        "thigh": thigh,
        "spine": spine,
        "shoulder": shoulder,
        "shin_local": SHIN_ABS - thigh,
        "neck_local": neck_local,
        "ua": ua,
        "ua_local": ua - spine,
        "forearm_local": bend,
        "hand": hand,
        "e": e,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(extension(fr)) for fr in FRAMES}
WHEEL_X0 = POSES[0]["hand"][0]

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
            dist *= 2.0  # one-sided tangent spans a single segment
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


def stroke_shape(indent, name, pts, width, color, feather):
    """Open feathered stroke used for soft highlights and core shadows."""
    return (
        f'{indent}<Shape name="{name}">\n'
        f'{indent}    <PointsPath isClosed="false" name="{name}Path">\n'
        f"{smooth_vertices(pts, False, indent + '        ')}\n"
        f"{indent}    </PointsPath>\n"
        f'{indent}    <Stroke thickness="{f(float(width))}" cap="round" join="round" name="{name}Stroke">'
        f'<SolidColor colorValue="{color}" name="{name}Color"/><Feather strength="{f(float(feather))}" name="{name}Feather"/></Stroke>\n'
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
MUSCLE_LOW = (0x4D, 0xFB, 0x92, 0x3C)  # soft orange, low alpha
MUSCLE_HIGH = (0xF2, 0xEF, 0x44, 0x44)  # saturated red
MUSCLE_LINE_LOW = (0x33, 0xC2, 0x41, 0x0C)
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
    return p["e"] ** 1.15


muscle_fill_ids, muscle_line_ids = [], []


def muscle_paint(name, line=0.9):
    fid, lid = nid(), nid()
    muscle_fill_ids.append(fid)
    muscle_line_ids.append(lid)
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, 0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{line}" join="round" name="{name}Edge"><SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, 0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- anatomy
# Limb local frames: +x runs along the bone, -y is the anterior side
# (biceps / quads / tibia), +y the posterior side (triceps / hamstrings / calf).
# Torso and neck: -y is the back, +y the chest/abdomen.

UPPER_ARM_PTS = [(-15, 0), (-12, -11), (2, -14.5), (18, -12.5), (31, -12), (45, -10), (57, -7.5), (64, -6.5),
                 (69, 0), (64, 6.5), (52, 8.5), (36, 12.5), (20, 13), (4, 13.5), (-10, 10)]
UPPER_ARM_HI = [(6, -9), (20, -8.5), (33, -8), (50, -5.5)]
UPPER_ARM_SH = [(6, 9.5), (22, 9.5), (38, 8.5), (54, 5)]
DELT_PTS = [(-17, -1), (-12, -13), (1, -17.5), (16, -15), (28, -8.5), (27, 2), (15, 9.5), (0, 12.5), (-12, 9)]
FRONT_DELT_PTS = [(-6, -11), (4, -15), (16, -12.5), (25, -7), (18, -3), (6, -4.5)]

FOREARM_PTS = [(-9, 0), (-8, -7.5), (6, -10.5), (21, -9), (37, -6.5), (51, -5), (58, -4.5),
               (62, 0), (58, 4.5), (44, 5.5), (27, 7.5), (10, 8.5), (-4, 8)]
FOREARM_HI = [(6, -6.5), (22, -6), (42, -3.8)]
FOREARM_SH = [(8, 5.5), (28, 4.8), (46, 3.2)]
HAND_PTS = [(-4, -7.5), (8, -8.5), (15, -4.5), (15.5, 3.5), (8, 8), (-4, 7.5), (-7, 0)]

TORSO_PTS = [(-24, 7), (-28, -7), (-17, -20), (0, -19.5), (22, -16), (48, -18), (72, -24.5), (92, -27.5),
             (108, -22), (118, -13), (117, -2), (112, 10), (104, 22), (90, 27.5), (77, 22.5), (63, 17),
             (46, 14), (27, 16), (9, 21), (-8, 20.5), (-19, 14)]
TORSO_HI = [(-4, -10), (24, -8), (52, -10), (80, -15.5), (98, -14)]
TORSO_SH = [(22, 11), (46, 9), (64, 12), (86, 20)]
GLUTE_HI = [(-22, -2), (-16, -13), (-4, -15)]
SHORTS_TORSO_PTS = [(-29, -6), (-18, -21.5), (0, -21), (25, -17), (27, 17.5), (9, 22), (-9, 21.5), (-23, 14)]
LAT_PTS = [(46, -6), (70, -14), (90, -17), (99, -7), (90, 3), (72, 3), (56, 0)]

NECK_PTS = [(-8, -9), (8, -8.5), (20, -6.5), (21, 7), (8, 9.5), (-8, 11)]
HEAD_PTS = [(12, -6), (19, -15), (33, -18.5), (46, -12), (51, -1), (49, 9), (45, 14), (46.5, 18.5), (40, 20.5),
            (36, 23), (29, 25), (21, 21), (15, 13), (11, 4)]
HAIR_PTS = [(13, -9), (22, -17), (36, -19.5), (47, -13), (50, -4), (41, -8), (27, -9.5), (17, -4)]
HEAD_HI = [(20, -10), (34, -13), (44, -8)]

THIGH_PTS = [(-19, 0), (-14, -12), (6, -17), (30, -17.5), (52, -14.5), (66, -11), (77, -9.5),
             (83, 0), (77, 9), (60, 10), (40, 13), (18, 17), (-2, 19), (-16, 12)]
THIGH_HI = [(8, -12.5), (32, -13.5), (56, -10)]
THIGH_SH = [(10, 13.5), (36, 9.5), (60, 6.5)]
SHORTS_THIGH_PTS = [(-21, 0), (-15, -14), (6, -19), (36, -18.5), (38, 14.5), (14, 19), (-4, 21), (-18, 13)]

SHIN_PTS = [(-11, 0), (-10, -8), (14, -8.5), (40, -7), (62, -5), (72, -4.5),
            (76, 0), (72, 5), (56, 6.5), (36, 10.5), (18, 14), (4, 12.5), (-8, 8.5)]
SHIN_HI = [(18, 6.5), (34, 5)]  # calf faces up: light it
SHIN_SH = [(10, -5), (40, -4.5), (62, -3)]
FOOT_PTS = [(-9, 0), (-7, -6), (8, -6.5), (22, -4.5), (28, 0), (24, 4.5), (10, 7), (-6, 7)]


def abs_segments(indent):
    """Rectus abdominis: four stacked blocks hugging the anterior contour."""
    front = [(9, 21), (27, 16), (46, 14), (63, 17), (77, 22.5)]

    def front_y(x):
        for (x0, y0), (x1, y1) in zip(front, front[1:]):
            if x0 <= x <= x1:
                return lerp(y0, y1, (x - x0) / (x1 - x0))
        return front[-1][1]

    out = []
    for k, cx in enumerate((22, 35, 48, 61)):
        x0, x1 = cx - 5.5, cx + 5.5
        y_out0, y_out1 = front_y(x0) - 1.8, front_y(x1) - 1.8
        pts = [(x0, y_out0 - 7), (cx, (y_out0 + y_out1) / 2 - 7.8), (x1, y_out1 - 7),
               (x1 + 0.6, y_out1 - 3.5), (x1, y_out1), (cx, (y_out0 + y_out1) / 2 + 0.6), (x0, y_out0), (x0 - 0.6, y_out0 - 3.5)]
        out.append(smooth_shape(indent, f"AbsSegment{k + 1}", pts, muscle_paint(f"AbsSegment{k + 1}", 0.8)))
    return "\n".join(out)


def rig(prefix, far):
    skin = SKIN_FAR if far else SKIN
    shorts = SHORTS_FAR if far else SHORTS
    ind = "        "
    hip_id, thigh_id, shin_id, spine_id = nid(), nid(), nid(), nid()
    ua_id, fa_id = nid(), nid()
    ox, oy = FAR_OFFSET if far else (0.0, 0.0)
    key_double(hip_id, 13, lambda p: p["hip"][0] + ox)
    key_double(hip_id, 14, lambda p: p["hip"][1] + oy)
    key_double(thigh_id, 15, lambda p: p["thigh"])
    key_double(shin_id, 15, lambda p: p["shin_local"])
    key_double(spine_id, 15, lambda p: p["spine"])
    key_double(ua_id, 15, lambda p: p["ua_local"])
    key_double(fa_id, 15, lambda p: p["forearm_local"])

    def shading(indent, nm, hi, sh, hw=3.2, sw=6.0):
        if far:
            return []
        return [stroke_shape(indent, nm + "Highlight", hi, hw * 1.5, HIGHLIGHT, 4),
                stroke_shape(indent, nm + "CoreShadow", sh, sw * 1.3, CORE_SHADOW, 7)]

    p0 = POSES[0]
    out = [f'{ind}<Node x="{f(p0["hip"][0] + ox)}" y="{f(p0["hip"][1] + oy)}" name="{prefix}Hip" id="{hip_id}">']

    # ---- spine branch (drawn above the legs)
    i2 = ind + "    "
    out.append(f'{i2}<Node rotation="{f(p0["spine"])}" name="{prefix}Spine" id="{spine_id}">')
    i3 = i2 + "    "
    sx, sy = SHOULDER_IN_SPINE
    out.append(f'{i3}<Node x="{f(sx)}" y="{f(sy)}" rotation="{f(p0["ua_local"])}" name="{prefix}UpperArm" id="{ua_id}">')
    i4 = i3 + "    "
    out.append(f'{i4}<Node x="{f(UPPER_ARM)}" rotation="{f(p0["forearm_local"])}" name="{prefix}Forearm" id="{fa_id}">')
    i5 = i4 + "    "
    out.append(smooth_shape(i5, f"{prefix}Hand", HAND_PTS, skin_fill(prefix + "Hand", -8, 8, skin), x=FOREARM))
    out += shading(i5, prefix + "Forearm", FOREARM_HI, FOREARM_SH, 2.6, 4.5)
    out.append(smooth_shape(i5, f"{prefix}ForearmShape", FOREARM_PTS, skin_fill(prefix + "Forearm", -10, 9, skin)))
    out.append(f"{i4}</Node>")
    if not far:
        out.append(smooth_shape(i4, "FrontDeltActivation", FRONT_DELT_PTS, muscle_paint("FrontDelt")))
        out.append(stroke_shape(i4, "DeltHighlight", [(-6, -9), (6, -12), (18, -9)], 3, HIGHLIGHT, 3.5))
    out.append(smooth_shape(i4, f"{prefix}Deltoid", DELT_PTS, skin_fill(prefix + "Deltoid", -17, 12, skin)))
    out += shading(i4, prefix + "UpperArm", UPPER_ARM_HI, UPPER_ARM_SH)
    out.append(smooth_shape(i4, f"{prefix}UpperArmShape", UPPER_ARM_PTS, skin_fill(prefix + "UpperArm", -14, 13, skin)))
    out.append(f"{i3}</Node>")

    if not far:
        nx, ny = NECK_IN_SPINE
        neck_id = nid()
        key_double(neck_id, 15, lambda p: p["neck_local"])
        out.append(f'{i3}<Node x="{f(nx)}" y="{f(ny)}" rotation="{f(p0["neck_local"])}" name="Neck" id="{neck_id}">')
        i4 = i3 + "    "
        out.append(smooth_shape(i4, "Hair", HAIR_PTS, f'<Fill name="HairFill">{grad("HairGrad", 0, -19, 0, -4, "FF475569", "FF1E293B")}</Fill>'))
        out.append(ellipse_shape(i4, "Ear", 27, 2, 7, 10, solid("Ear", "FFA3B1C4")))
        out.append(stroke_shape(i4, "HeadHighlight", HEAD_HI, 3, HIGHLIGHT, 4))
        out.append(smooth_shape(i4, "Head", HEAD_PTS, skin_fill("Head", -18, 25, skin)))
        out.append(smooth_shape(i4, "NeckShape", NECK_PTS, skin_fill("Neck", -9, 11, skin)))
        out.append(f"{i3}</Node>")

        out.append(abs_segments(i3))
        out.append(smooth_shape(i3, "LatActivation", LAT_PTS, muscle_paint("Lat")))
        out.append(smooth_shape(i3, "Shorts", SHORTS_TORSO_PTS, skin_fill("Shorts", -21, 22, shorts)))
        out.append(stroke_shape(i3, "GluteHighlight", GLUTE_HI, 3, "59FFFFFF", 4))
        out += shading(i3, "Torso", TORSO_HI, TORSO_SH, 4, 8)
        out.append(smooth_shape(i3, "Torso", TORSO_PTS, skin_fill("Torso", -27, 27, skin)))
    out.append(f"{i2}</Node>")

    # ---- leg branch
    out.append(f'{i2}<Node rotation="{f(p0["thigh"])}" name="{prefix}Thigh" id="{thigh_id}">')
    i3 = i2 + "    "
    out.append(f'{i3}<Node x="{f(THIGH)}" rotation="{f(p0["shin_local"])}" name="{prefix}Shin" id="{shin_id}">')
    i4 = i3 + "    "
    out.append(f'{i4}<Node x="{f(SHIN)}" rotation="{f(FOOT_LOCAL)}" name="{prefix}Foot">')
    out.append(smooth_shape(i4 + "    ", f"{prefix}FootShape", FOOT_PTS, skin_fill(prefix + "Foot", -7, 7, skin)))
    out.append(f"{i4}</Node>")
    out.append(ellipse_shape(i4, f"{prefix}KneeCap", 1, -1, 22, 20, skin_fill(prefix + "Knee", -10, 10, skin)))
    out += shading(i4, prefix + "Shin", SHIN_HI, SHIN_SH, 3, 4.5)
    out.append(smooth_shape(i4, f"{prefix}ShinShape", SHIN_PTS, skin_fill(prefix + "Shin", -9, 14, skin)))
    out.append(f"{i3}</Node>")
    out.append(smooth_shape(i3, f"{prefix}ThighShorts", SHORTS_THIGH_PTS, skin_fill(prefix + "ThighShorts", -19, 21, shorts)))
    out += shading(i3, prefix + "Thigh", THIGH_HI, THIGH_SH, 3.5, 7)
    out.append(smooth_shape(i3, f"{prefix}ThighShape", THIGH_PTS, skin_fill(prefix + "Thigh", -18, 19, skin)))
    out.append(f"{i2}</Node>")
    out.append(f"{ind}</Node>")
    return "\n".join(out)


def wheel():
    ind = "        "
    wid = nid()
    key_double(wid, 13, lambda p: p["hand"][0])
    key_double(wid, 15, lambda p: (p["hand"][0] - WHEEL_X0) / WHEEL_R)
    r = WHEEL_R
    spokes = "".join(
        f'{ind}    <Shape rotation="{f(k * math.pi / 3)}" name="Spoke{k}"><Rectangle width="{f(r * 1.25)}" height="2.4" cornerRadiusTL="1.2" name="Spoke{k}Rect"/>'
        f'{solid("Spoke" + str(k), "FF64748B")}</Shape>\n'
        for k in range(3)
    )
    return (
        f'{ind}<Node x="{f(WHEEL_X0)}" y="{f(WHEEL_Y)}" name="Wheel" id="{wid}">\n'
        f'{ind}    <Shape name="HandleCap"><Ellipse width="9" height="9" name="HandleCapEllipse"/>{solid("HandleCap", "FF1E293B")}</Shape>\n'
        f'{ind}    <Shape name="Hub"><Ellipse width="{f(r * 0.62)}" height="{f(r * 0.62)}" name="HubEllipse"/>'
        f'<Fill name="HubFill">{grad("HubGrad", -6, -6, 6, 6, "FFFDBA74", "FFEA580C")}</Fill></Shape>\n'
        f"{spokes}"
        f'{ind}    <Shape name="Tread"><Ellipse width="{f(r * 2 - 5)}" height="{f(r * 2 - 5)}" name="TreadEllipse"/>'
        f'<Stroke thickness="2" name="TreadStroke"><SolidColor colorValue="FF64748B" name="TreadColor"/>'
        f'<DashPath name="TreadDashes"><Dash length="0.06" lengthIsPercentage="true" name="On"/><Dash length="0.065" lengthIsPercentage="true" name="Off"/></DashPath></Stroke></Shape>\n'
        f'{ind}    <Shape name="Tire"><Ellipse width="{f(r * 2)}" height="{f(r * 2)}" name="TireEllipse"/>'
        f'<Fill name="TireFill">{grad("TireGrad", 0, -r, 0, r, "FF334155", "FF0B1220")}</Fill>'
        f'<Stroke thickness="2.5" name="TireRim"><SolidColor colorValue="FF94A3B8" name="TireRimColor"/></Stroke></Shape>\n'
        f"{ind}</Node>"
    )


def shadow():
    ind = "        "
    sid = nid()
    feet_x = KNEE[0] - SHIN - 10

    def cx(p):
        return (feet_x + p["hand"][0] + WHEEL_R) / 2

    def sx(p):
        return (p["hand"][0] + WHEEL_R - feet_x + 30) / 200.0

    key_double(sid, 13, cx)
    key_double(sid, 16, sx)
    p0 = POSES[0]
    return (
        f'{ind}<Shape x="{f(cx(p0))}" y="{f(FLOOR + 1)}" scaleX="{f(sx(p0))}" scaleY="0.075" name="BodyShadow" id="{sid}">\n'
        f'{ind}    <Ellipse width="200" height="200" name="ShadowEllipse"/>\n'
        f'{ind}    <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="100" endY="0" name="ShadowGrad">'
        f'<GradientStop colorValue="B3000000" position="0"/><GradientStop colorValue="59000000" position="0.6"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{ind}</Shape>"
    )


def scenery():
    ind = "        "
    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"
    return (
        f'{ind}<Shape x="{W / 2}" y="{FLOOR + 1}" name="FloorLine"><Rectangle width="{W - 40}" height="2" cornerRadiusTL="1" name="FloorRect"/>'
        f'<Fill name="FloorFill"><LinearGradient startX="{-(W - 40) / 2}" startY="0" endX="{(W - 40) / 2}" endY="0" name="FloorGrad">'
        f'<GradientStop colorValue="00475569" position="0"/><GradientStop colorValue="FF475569" position="0.2"/>'
        f'<GradientStop colorValue="FF475569" position="0.8"/><GradientStop colorValue="00475569" position="1"/></LinearGradient></Fill></Shape>\n'
        f'{ind}<Shape x="{W / 2}" y="{(FLOOR + H) / 2 + 1}" name="FloorBand"><Rectangle width="{W}" height="{band_h}" name="FloorBandRect"/>'
        f"{band_fill}</Shape>\n"
        f'{ind}<Shape x="{W / 2}" y="{H / 2}" name="Backdrop"><Rectangle width="{W}" height="{H}" name="BackdropRect"/>'
        f'<Fill name="BackdropFill"><RadialGradient startX="0" startY="-40" endX="0" endY="{H * 0.75}" name="BackdropGrad">'
        f'<GradientStop colorValue="FF1E293B" position="0"/><GradientStop colorValue="FF0F172A" position="1"/></RadialGradient></Fill></Shape>'
    )


near = rig("", False)
whl = wheel()
far = rig("Far", True)
shd = shadow()

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
            # Drop interior keys whose value equals both neighbours (holds).
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
    <!-- Ab Wheel Rollout: side view, 60 fps, generated by gen_ab_wheel.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="AbWheelRollout" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- Near-side athlete (front) -->
{near}

        <!-- Ab wheel: rotation = dx / radius -->
{whl}

        <!-- Far-side limbs (behind, darker) -->
{far}

        <!-- Floor shadow stretches with the body -->
{shd}

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

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="Rollout" id="0:60">
{keyed_xml()}
        </LinearAnimation>
    </Artboard>
</Rive>
"""

OUT.write_text(rml)

# Diagnostics: planted knee, hand on the wheel hub, arm angle.
for fr in (0, 36, 72, 96, 168, 216):
    p = POSES[fr]
    knee = add(p["hip"], (THIGH * math.cos(p["thigh"]), THIGH * math.sin(p["thigh"])))
    print(
        f"f{fr:3d} e={p['e']:.3f} hip=({p['hip'][0]:.1f},{p['hip'][1]:.1f}) knee=({knee[0]:.2f},{knee[1]:.2f}) "
        f"shoulder=({p['shoulder'][0]:.1f},{p['shoulder'][1]:.1f}) hand=({p['hand'][0]:.1f},{p['hand'][1]:.2f}) "
        f"arm={math.degrees(p['ua']):.1f}deg"
    )
print("keyed props:", len(keys), "bytes:", len(rml))


def publish():
    """Build the .riv, copy it into the Flutter assets and render the catalog thumbnail."""
    subprocess.run([str(RIVE_BIN), ".", "--once"], cwd=HERE, check=True)
    shutil.copyfile(HERE / "build/ab_wheel_rollout.riv", ASSET_RIV)
    ASSET_THUMB.parent.mkdir(parents=True, exist_ok=True)
    full = HERE / "build/thumbnail_full.png"
    subprocess.run(
        [str(RIVE_BIN), ".", f"--screenshot={full}", f"--advance={THUMB_ADVANCE}",
         f"--viewport={THUMB_VIEWPORT}", "--fit=contain"],
        cwd=HERE,
        check=True,
    )
    size, off_y, off_x = THUMB_CROP
    # macOS `sips`: crop the athlete into a square, then downscale.
    subprocess.run(["sips", "-c", str(size), str(size), "--cropOffset", str(off_y), str(off_x),
                    str(full), "--out", str(ASSET_THUMB)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["sips", "-Z", str(THUMB_SIZE), str(ASSET_THUMB)], check=True, stdout=subprocess.DEVNULL)
    full.unlink()
    print("published", ASSET_RIV, ASSET_THUMB)


if "--publish" in sys.argv:
    publish()
