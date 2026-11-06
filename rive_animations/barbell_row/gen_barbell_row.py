"""Generates rive_animations/barbell_row/scene.rml (and optionally publishes).

Rear three-quarter view of a stylized athlete performing a bent-over barbell
row at 60 fps.

Same character as ab_wheel_rollout / arnold_press (palette, 3-stop gradients,
feathered highlights / core shadows, muscle activation paint, limb outlines).
The camera sits behind the athlete's left shoulder, slightly above, so the
upper back (lats, traps, rhomboids, rear delts) faces the viewer while the
elbows travel past the torso line.

The static body (legs, hips, torso, head) is posed in 3D and projected straight
into artboard coordinates (Catmull-Rom outlines are affine invariant, so the
projected control points give the projected curve). Only the arms (3D two-bone
IK toward the bar) and the barbell are animated with keyed nodes.

3D frame: X = athlete's right, Y = up, Z = athlete's forward.

Usage (from this directory):
    python3 gen_barbell_row.py            # regenerate scene.rml
    python3 gen_barbell_row.py --publish  # + build .riv, copy to assets, render thumbnail
"""

import math
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "scene.rml"
REPO = HERE.parent.parent
ASSET_RIV = REPO / "assets/animations/barbell_row.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/barbell_row.png"
THUMB_ADVANCE = "1.15s"
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

# ---------------------------------------------------------------- camera
YAW = math.radians(58.0)  # camera behind the athlete's left shoulder
TILT = math.radians(14.0)  # camera above, looking down
R_AX = (math.cos(YAW), 0.0, -math.sin(YAW))  # screen right
UP_AX = (math.sin(YAW) * math.sin(TILT), math.cos(TILT), math.cos(YAW) * math.sin(TILT))  # screen up
VIEW = (-math.sin(YAW) * math.cos(TILT), math.sin(TILT), -math.cos(YAW) * math.cos(TILT))  # toward camera


def v_add(*vs):
    return tuple(sum(c) for c in zip(*vs))


def v_sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def v_scale(a, s):
    return tuple(x * s for x in a)


def v_dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def v_len(a):
    return math.sqrt(v_dot(a, a))


def v_norm(a):
    m = v_len(a)
    return tuple(c / m for c in a)


def pvec(d):
    """3D vector -> screen vector (y down)."""
    return (v_dot(d, R_AX), -v_dot(d, UP_AX))


OFFSET = [0.0, 0.0]  # artboard offset, solved after the bounds pass


def proj(p):
    sx, sy = pvec(p)
    return (sx + OFFSET[0], sy + OFFSET[1])


def depth(p):
    return v_dot(p, VIEW)


# ---------------------------------------------------------------- pose (static body)
X3, Y3, Z3 = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)
UPPER_ARM, FOREARM = 60.0, 56.0
GRIP = 60.0  # elbow -> bar (bar sits in the palm)
THIGH_LEN, SHIN_LEN, FOOT_LEN = 72.0, 70.0, 24.0

ANKLE = {s: (16.0 * s, 7.0, 0.0) for s in (1, -1)}
KNEE = {s: (15.0 * s, 74.6, 18.1) for s in (1, -1)}
HIP_C = (0.0, 125.5, -32.8)
HIP = {s: (12.0 * s, 125.5, -32.8) for s in (1, -1)}
TOE = {s: (19.0 * s, 3.0, 23.0) for s in (1, -1)}

TORSO_ANGLE = math.radians(36.0)  # spine above horizontal (flat back)
T_AX = (0.0, math.sin(TORSO_ANGLE), math.cos(TORSO_ANGLE))  # hips -> neck
N_AX = (0.0, -math.cos(TORSO_ANGLE), math.sin(TORSO_ANGLE))  # back -> chest
BACK_OFF = -18.0  # back surface along N
SIDE_OFF = -19.0  # near side profile plane along X


def back_pt(u, w):
    return v_add(HIP_C, v_scale(T_AX, u), v_scale(X3, w), v_scale(N_AX, BACK_OFF))


def side_pt(x, y):
    return v_add(HIP_C, v_scale(T_AX, x), v_scale(N_AX, y), v_scale(X3, SIDE_OFF))


SHOULDER = {s: v_add(HIP_C, v_scale(T_AX, 98), v_scale(N_AX, -4), v_scale(X3, 23 * s)) for s in (1, -1)}
NECK_BASE = v_add(HIP_C, v_scale(T_AX, 108), v_scale(N_AX, -8))
HEAD_DIR = v_norm(v_add(T_AX, (0.0, 0.08, 0.0)))
HEAD_C = v_add(NECK_BASE, v_scale(HEAD_DIR, 20))

# Bar path (bar centre): hanging below the shoulders -> lower chest.
BAR_START = (0.0, SHOULDER[1][1] - 116.0, SHOULDER[1][2] + 3.0)
BAR_TOP = v_add(HIP_C, v_scale(T_AX, 64), v_scale(N_AX, 24))
HAND_X = 25.0

# Timeline (frames @60fps): pull 1.1s, squeeze 0.2s, lower 1.4s, reset 0.3s.
PULL, HOLD_TOP, LOWER, HOLD_BOTTOM = 66, 12, 84, 18
DURATION = PULL + HOLD_TOP + LOWER + HOLD_BOTTOM
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


EASE = cubic_bezier(0.45, 0.0, 0.4, 1.0)


def pull(frame):
    fr = frame % DURATION
    if fr <= PULL:
        return EASE(fr / PULL)
    fr -= PULL
    if fr <= HOLD_TOP:
        return 1.0
    fr -= HOLD_TOP
    if fr <= LOWER:
        return 1.0 - EASE(fr / LOWER)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def bar_center(p):
    return (0.0, lerp(BAR_START[1], BAR_TOP[1], p),
            lerp(BAR_START[2], BAR_TOP[2], p) + 4.0 * math.sin(math.pi * p))


# ---------------------------------------------------------------- arm IK
def arm_geometry(p, side):
    s3 = SHOULDER[side]
    hand = v_add(bar_center(p), (HAND_X * side, 0.0, 0.0))
    to_h = v_sub(hand, s3)
    d = min(v_len(to_h), UPPER_ARM + GRIP - 1.0)
    e = v_norm(to_h)
    pole = v_norm((0.2 * side, 0.25, -1.0))
    pole = v_norm(v_sub(pole, v_scale(e, v_dot(pole, e))))
    cos_a = max(-1.0, min(1.0, (UPPER_ARM ** 2 + d * d - GRIP ** 2) / (2 * UPPER_ARM * d)))
    sin_a = math.sqrt(1 - cos_a * cos_a)
    elbow = v_add(s3, v_scale(e, UPPER_ARM * cos_a), v_scale(pole, UPPER_ARM * sin_a))
    hand = v_add(s3, v_scale(e, d))
    u = v_norm(v_sub(elbow, s3))
    fd = v_norm(v_sub(hand, elbow))
    perp = v_sub(fd, v_scale(u, v_dot(fd, u)))
    pm = v_len(perp)
    w = min(1.0, pm / 0.3)
    ant = v_norm(tuple(w * (c / pm if pm > 1e-6 else 0.0) + (1 - w) * z for c, z in zip(perp, Z3)))
    pu, pf = pvec(u), pvec(fd)
    return {
        "s3": s3, "e3": elbow, "h3": hand,
        "ua": math.atan2(pu[1], pu[0]),
        "ua_len": math.hypot(*pu),
        "fa": math.atan2(pf[1], pf[0]),
        "fa_len": math.hypot(*pf),
        "ant": pvec(ant),
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)


def flip_track(geoms, angle_key, ant_key, dead=0.12):
    """scaleY sign per frame: +1 when the anterior vector projects onto local -y."""
    def comp(g):
        a = g[angle_key]
        return g[ant_key][0] * math.sin(a) - g[ant_key][1] * math.cos(a)

    cur = 1.0 if comp(geoms[0]) >= 0 else -1.0
    for _ in range(2):  # second pass seeds frame 0 with the end state: seamless loop
        out = []
        for g in geoms:
            c = comp(g)
            if abs(c) >= dead:
                cur = 1.0 if c > 0 else -1.0
            out.append(cur)
    return out


def unwrap(vals):
    out = [vals[0]]
    for v in vals[1:]:
        while v - out[-1] > math.pi:
            v -= 2 * math.pi
        while v - out[-1] < -math.pi:
            v += 2 * math.pi
        out.append(v)
    return out


def build_poses():
    poses = {fr: {"p": pull(fr)} for fr in FRAMES}
    for side, tag in ((-1, "near"), (1, "far")):
        geoms = [arm_geometry(poses[fr]["p"], side) for fr in FRAMES]
        su = flip_track(geoms, "ua", "ant")
        sf = flip_track(geoms, "fa", "ant")
        ua = unwrap([g["ua"] for g in geoms])
        fa = unwrap([g["fa"] for g in geoms])
        for i, fr in enumerate(FRAMES):
            g = dict(geoms[i])
            g.update(ua=ua[i], fa=fa[i], su=su[i], sf=sf[i])
            poses[fr][tag] = g
    return poses


POSES = build_poses()

# ---------------------------------------------------------------- outlines (ab_wheel_rollout)
UPPER_ARM_PTS = [(-15, 0), (-12, -11), (2, -14.5), (18, -12.5), (31, -12), (45, -10), (57, -7.5), (64, -6.5),
                 (69, 0), (64, 6.5), (52, 8.5), (36, 12.5), (20, 13), (4, 13.5), (-10, 10)]
UPPER_ARM_HI = [(6, -9), (20, -8.5), (33, -8), (50, -5.5)]
UPPER_ARM_SH = [(6, 9.5), (22, 9.5), (38, 8.5), (54, 5)]
BICEPS_PTS = [(6, -5.5), (20, -7), (36, -7), (50, -4.5), (56, -6.5), (44, -10), (28, -12), (12, -12), (2, -9.5)]
DELT_PTS = [(-16, 0), (-12, -13), (2, -16.5), (17, -14), (28, -6), (29, 4), (18, 13), (2, 15.5), (-12, 12)]
REAR_DELT_PTS = [(-8, 10), (3, 13.5), (16, 11), (25, 4.5), (16, 1.5), (4, 2.5)]

FOREARM_PTS = [(-9, 0), (-8, -7.5), (6, -10.5), (21, -9), (37, -6.5), (51, -5), (58, -4.5),
               (62, 0), (58, 4.5), (44, 5.5), (27, 7.5), (10, 8.5), (-4, 8)]
FOREARM_HI = [(6, -6.5), (22, -6), (42, -3.8)]
FOREARM_SH = [(8, 5.5), (28, 4.8), (46, 3.2)]
HAND_PTS = [(-4, -7.5), (8, -8.5), (15, -4.5), (15.5, 3.5), (8, 8), (-4, 7.5), (-7, 0)]

TORSO_PTS = [(-24, 7), (-28, -7), (-17, -20), (0, -19.5), (22, -16), (48, -18), (72, -24.5), (92, -27.5),
             (108, -22), (118, -13), (117, -2), (112, 10), (104, 22), (90, 27.5), (77, 22.5), (63, 17),
             (46, 14), (27, 16), (9, 21), (-8, 20.5), (-19, 14)]
SHORTS_TORSO_PTS = [(-29, -6), (-18, -21.5), (0, -21), (25, -17), (27, 17.5), (9, 22), (-9, 21.5), (-23, 14)]
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
SHIN_HI = [(18, 9), (36, 7), (56, 4.5)]  # calf faces the camera: light it
SHIN_SH = [(10, -5), (40, -4.5), (62, -3)]
FOOT_PTS = [(-9, 0), (-7, -6), (8, -6.5), (22, -4.5), (28, 0), (24, 4.5), (10, 7), (-6, 7)]

# ---------------------------------------------------------------- back plane outlines (u along spine, w = X)
BACK_RIGHT = [(110, 0), (108, 9), (103, 17), (99, 25), (92, 30), (82, 29), (70, 26), (56, 21), (42, 16.5),
              (28, 15), (14, 16), (2, 17)]
BACK_PTS = BACK_RIGHT + [(-3, 0)] + [(u, -w) for u, w in reversed(BACK_RIGHT[1:])]
LAT_R = [(90, 27), (82, 28.5), (68, 25.5), (52, 20), (38, 15.5), (28, 13), (30, 8), (40, 6.5), (54, 9),
         (68, 13), (80, 17), (88, 20)]
TRAP_RIGHT = [(112, 0), (110, 7), (104, 15), (99, 23), (95, 24), (88, 15), (78, 7), (64, 2.5)]
TRAP_PTS = TRAP_RIGHT + [(58, 0)] + [(u, -w) for u, w in reversed(TRAP_RIGHT[1:])]
INFRA_R = [(97, 8), (96, 20), (88, 24), (78, 20), (76, 12), (84, 8)]
TERES_R = [(80, 22), (86, 27), (92, 29), (90, 25), (84, 21)]
BACK_SHORTS = [(15, 17.5), (2, 19), (-10, 20), (-18, 16), (-22, 6), (-22, -6), (-18, -16), (-10, -20), (2, -19), (15, -17.5)]

# ---------------------------------------------------------------- palette (ab_wheel_rollout)
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_SIDE = ("FFCBD5E1", "FFAFBCCB", "FF7C8BA0")
SKIN_FAR = ("FF9AA8BC", "FF738399", "FF4B5A70")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "4D0F172A"
MUSCLE_LOW = (0x4D, 0xFB, 0x92, 0x3C)
MUSCLE_HIGH = (0xF2, 0xEF, 0x44, 0x44)
MUSCLE_LINE_LOW = (0x33, 0xC2, 0x41, 0x0C)
MUSCLE_LINE_HIGH = (0xCC, 0x8B, 0x1A, 0x1A)
PLATE = ("FF475569", "FF1E293B", "FF0B1220")


# ---------------------------------------------------------------- rml helpers
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


def grad3(name, p0, p1, c0, c1, c2):
    return (
        f'<LinearGradient startX="{f(float(p0[0]))}" startY="{f(float(p0[1]))}" endX="{f(float(p1[0]))}" endY="{f(float(p1[1]))}" name="{name}">'
        f'<GradientStop colorValue="{c0}" position="0"/>'
        f'<GradientStop colorValue="{c1}" position="0.5"/>'
        f'<GradientStop colorValue="{c2}" position="1"/></LinearGradient>'
    )


def grad(name, p0, p1, c0, c1):
    return (
        f'<LinearGradient startX="{f(float(p0[0]))}" startY="{f(float(p0[1]))}" endX="{f(float(p1[0]))}" endY="{f(float(p1[1]))}" name="{name}">'
        f'<GradientStop colorValue="{c0}" position="0"/>'
        f'<GradientStop colorValue="{c1}" position="1"/></LinearGradient>'
    )


def solid(name, color):
    return f'<Fill name="{name}Fill"><SolidColor colorValue="{color}" name="{name}Color"/></Fill>'


def fill3(name, p0, p1, tones):
    return f'<Fill name="{name}Fill">{grad3(name + "Grad", p0, p1, *tones)}</Fill>'


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


def stroke_shape(indent, name, pts, width, color, feather, cap="round"):
    return (
        f'{indent}<Shape name="{name}">\n'
        f'{indent}    <PointsPath isClosed="false" name="{name}Path">\n'
        f"{smooth_vertices(pts, False, indent + '        ')}\n"
        f"{indent}    </PointsPath>\n"
        f'{indent}    <Stroke thickness="{f(float(width))}" cap="{cap}" join="round" name="{name}Stroke">'
        f'<SolidColor colorValue="{color}" name="{name}Color"/>'
        + (f'<Feather strength="{f(float(feather))}" name="{name}Feather"/>' if feather else "")
        + f"</Stroke>\n"
        f"{indent}</Shape>"
    )


def ellipse_shape(indent, name, x, y, w, h, paint_xml, rotation=0.0):
    rot = f' rotation="{f(float(rotation))}"' if rotation else ""
    return (
        f'{indent}<Shape x="{f(float(x))}" y="{f(float(y))}"{rot} name="{name}">\n'
        f'{indent}    <Ellipse width="{f(float(w))}" height="{f(float(h))}" name="{name}Ellipse"/>\n'
        f"{indent}    {paint_xml}\n"
        f"{indent}</Shape>"
    )


def argb_lerp(a, b, t):
    return "".join(f"{round(lerp(x, y, t)):02X}" for x, y in zip(a, b))


keys = []  # (objectId, propertyKey, kind, [(frame, value)])


def key_double(obj, prop, fn, hold=False):
    keys.append((obj, prop, "hold" if hold else "double", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def key_color(obj, prop, fn):
    keys.append((obj, prop, "color", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def muscle_t(p):
    return 0.15 + 0.85 * p["p"] ** 1.2


muscle_fill_ids, muscle_line_ids = [], []


def muscle_paint(name, line=0.9):
    fid, lid = nid(), nid()
    muscle_fill_ids.append(fid)
    muscle_line_ids.append(lid)
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, 0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{line}" join="round" name="{name}Edge"><SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, 0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


def shading(indent, nm, hi, sh, hw=3.2, sw=6.0):
    return [stroke_shape(indent, nm + "Highlight", hi, hw * 1.5, HIGHLIGHT, 4),
            stroke_shape(indent, nm + "CoreShadow", sh, sw * 1.3, CORE_SHADOW, 7)]


# ---------------------------------------------------------------- static projection helpers
def limb_mapper(a3, b3, length, ant3):
    """Map a limb outline (x along the bone, -y anterior) onto the projected bone a3 -> b3."""
    a, b = proj(a3), proj(b3)
    dx, dy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    m = math.hypot(b[0] - a[0], b[1] - a[1])
    perp = (-(b[1] - a[1]) / m, (b[0] - a[0]) / m)
    ant = pvec(ant3)
    sign = -1.0 if perp[0] * ant[0] + perp[1] * ant[1] > 0 else 1.0

    def mp(pts):
        return [(a[0] + x * dx + y * sign * perp[0], a[1] + x * dy + y * sign * perp[1]) for x, y in pts]

    return mp


def back_map(pts):
    return [proj(back_pt(u, w)) for u, w in pts]


def side_map(pts):
    return [proj(side_pt(x, y)) for x, y in pts]


def mirror_w(pts):
    return [(u, -w) for u, w in pts]


# ---------------------------------------------------------------- legs
def leg(indent, side):
    nm = "Near" if side < 0 else "Far"
    tones = SKIN if side < 0 else SKIN_FAR
    shorts = SHORTS if side < 0 else SHORTS_FAR
    thigh_dir = v_norm(v_sub(KNEE[side], HIP[side]))
    thigh_ant = v_norm(v_sub(Z3, v_scale(thigh_dir, v_dot(Z3, thigh_dir))))
    shin_dir = v_norm(v_sub(ANKLE[side], KNEE[side]))
    shin_ant = v_norm(v_sub(Z3, v_scale(shin_dir, v_dot(Z3, shin_dir))))
    th = limb_mapper(HIP[side], KNEE[side], THIGH_LEN, thigh_ant)
    sh = limb_mapper(KNEE[side], ANKLE[side], SHIN_LEN, shin_ant)
    ft = limb_mapper(ANKLE[side], TOE[side], FOOT_LEN, Y3)
    out = [
        smooth_shape(indent, f"{nm}ThighShorts", th(SHORTS_THIGH_PTS), fill3(f"{nm}ThighShorts", *th([(20, -19), (20, 21)]), shorts)),
        stroke_shape(indent, f"{nm}ThighHighlight", th(THIGH_HI), 4.5, HIGHLIGHT, 4),
        stroke_shape(indent, f"{nm}ThighCoreShadow", th(THIGH_SH), 8, CORE_SHADOW, 7),
        smooth_shape(indent, f"{nm}Thigh", th(THIGH_PTS), fill3(f"{nm}Thigh", *th([(40, -18), (40, 19)]), tones)),
        stroke_shape(indent, f"{nm}ShinHighlight", sh(SHIN_HI), 4.5, HIGHLIGHT, 4),
        stroke_shape(indent, f"{nm}ShinCoreShadow", sh(SHIN_SH), 5.5, CORE_SHADOW, 6),
        smooth_shape(indent, f"{nm}Shin", sh(SHIN_PTS), fill3(f"{nm}Shin", *sh([(36, -9), (36, 14)]), tones)),
        smooth_shape(indent, f"{nm}Foot", ft(FOOT_PTS), fill3(f"{nm}Foot", *ft([(10, -7), (10, 7)]), tones)),
    ]
    return "\n".join(out)


# ---------------------------------------------------------------- torso (static)
def glutes(indent):
    """Shorts over the hips on the back plane, with the gluteal crease."""
    return "\n".join([
        stroke_shape(indent, "GluteCrease", back_map([(4, 0), (-8, 0), (-19, 0)]), 2.2, SOFT_SHADOW, 2),
        stroke_shape(indent, "NearGluteHighlight", back_map([(6, -7), (-4, -13), (-14, -12)]), 3, "40FFFFFF", 3),
        stroke_shape(indent, "WaistbandShade", back_map([(12, -16), (13, 0), (12, 16)]), 2.4, SOFT_SHADOW, 2),
        smooth_shape(indent, "BackShorts", back_map(BACK_SHORTS),
                     fill3("BackShorts", proj(back_pt(14, -20)), proj(back_pt(-22, 20)), SHORTS)),
    ])


def back(indent):
    parts = []
    for s, nm in ((-1, "L"), (1, "R")):
        m = (lambda pts: pts) if s > 0 else mirror_w
        parts.append(smooth_shape(indent, f"TeresActivation{nm}", back_map(m(TERES_R)), muscle_paint(f"Teres{nm}")))
        parts.append(smooth_shape(indent, f"InfraspinatusActivation{nm}", back_map(m(INFRA_R)), muscle_paint(f"Infraspinatus{nm}")))
        parts.append(smooth_shape(indent, f"LatActivation{nm}", back_map(m(LAT_R)), muscle_paint(f"Lat{nm}")))
    parts.append(smooth_shape(indent, "TrapActivation", back_map(TRAP_PTS), muscle_paint("Trap")))
    # Muscle definition: spine groove, erector highlights, scapula borders.
    parts.append(stroke_shape(indent, "SpineGroove", back_map([(104, 0), (70, 0), (36, 0), (4, 0)]), 2, SOFT_SHADOW, 2))
    for s, nm in ((-1, "L"), (1, "R")):
        parts.append(stroke_shape(indent, f"Erector{nm}", back_map([(6, 5 * s), (24, 5.5 * s), (44, 5 * s)]),
                                  3.5, "73FFFFFF" if s < 0 else "40FFFFFF", 3.5))
        parts.append(stroke_shape(indent, f"ScapulaEdge{nm}", back_map([(100, 9 * s), (88, 10 * s), (76, 13 * s)]),
                                  2.4, SOFT_SHADOW, 2.5))
    parts.append(stroke_shape(indent, "BackHighlight", back_map([(102, -10), (92, -18), (74, -18), (56, -13)]),
                              4, HIGHLIGHT, 5))
    parts.append(stroke_shape(indent, "BackFarShadow", back_map([(96, 18), (84, 21), (66, 18), (44, 12), (20, 10)]),
                              7, CORE_SHADOW, 7))
    parts.append(smooth_shape(indent, "Back", back_map(BACK_PTS),
                              fill3("Back", proj(back_pt(100, -24)), proj(back_pt(0, 22)), SKIN)))
    return "\n".join(parts)


def torso_side(indent):
    return "\n".join([
        smooth_shape(indent, "SideShorts", side_map(SHORTS_TORSO_PTS),
                     fill3("SideShorts", proj(side_pt(0, -21)), proj(side_pt(0, 22)), SHORTS)),
        stroke_shape(indent, "SideCoreShadow", side_map([(22, 11), (46, 9), (64, 12), (86, 20)]), 8, CORE_SHADOW, 7),
        smooth_shape(indent, "TorsoSide", side_map(TORSO_PTS),
                     fill3("TorsoSide", proj(side_pt(60, -26)), proj(side_pt(60, 26)), SKIN_SIDE)),
    ])


def head_and_neck(indent):
    """ab_wheel_rollout profile head, mapped onto the projected neck axis (face toward the floor)."""
    origin = v_add(HIP_C, v_scale(T_AX, 106), v_scale(N_AX, -10))
    hd = limb_mapper(origin, v_add(origin, v_scale(HEAD_DIR, 40)), 40.0, v_scale(N_AX, -1))
    ear = hd([(27, 2)])[0]
    ang = math.atan2(*reversed(v_sub(*hd([(1, 0), (0, 0)]))))
    return "\n".join([
        smooth_shape(indent, "Hair", hd(HAIR_PTS), f'<Fill name="HairFill">{grad("HairGrad", *hd([(30, -19), (30, -4)]), "FF475569", "FF1E293B")}</Fill>'),
        ellipse_shape(indent, "Ear", ear[0], ear[1], 7, 10, solid("Ear", "FFA3B1C4"), rotation=ang),
        stroke_shape(indent, "HeadHighlight", hd(HEAD_HI), 3, HIGHLIGHT, 4),
        smooth_shape(indent, "Head", hd(HEAD_PTS), fill3("Head", *hd([(30, -18), (30, 25)]), SKIN)),
        smooth_shape(indent, "Neck", hd(NECK_PTS), fill3("Neck", *hd([(8, -9), (8, 11)]), SKIN)),
    ])


# ---------------------------------------------------------------- arms
def arm(tag):
    ind = "        "
    i2 = ind + "    "
    near = tag == "near"
    prefix = "Near" if near else "Far"
    tones = SKIN if near else SKIN_FAR
    out = []
    p0 = POSES[0][tag]

    def g(fn):
        return lambda P: fn(P[tag])

    def elbow_s(a):
        return proj(a["e3"])

    ax, ay = proj(p0["s3"])

    # Forearm + hand.
    fa_id = nid()
    key_double(fa_id, 13, g(lambda a: elbow_s(a)[0]))
    key_double(fa_id, 14, g(lambda a: elbow_s(a)[1]))
    key_double(fa_id, 15, g(lambda a: a["fa"]))
    key_double(fa_id, 16, g(lambda a: a["fa_len"]))
    key_double(fa_id, 17, g(lambda a: a["sf"]), hold=True)
    ex, ey = elbow_s(p0)
    out.append(f'{ind}<Node x="{f(ex)}" y="{f(ey)}" rotation="{f(p0["fa"])}" '
               f'scaleX="{f(p0["fa_len"])}" scaleY="{f(p0["sf"])}" name="{prefix}Forearm" id="{fa_id}">')
    out.append(smooth_shape(i2, f"{prefix}Hand", HAND_PTS, fill3(prefix + "Hand", (0, -8), (0, 8), tones), x=FOREARM))
    out += shading(i2, prefix + "Forearm", FOREARM_HI, FOREARM_SH, 2.6, 4.5)
    out.append(smooth_shape(i2, f"{prefix}ForearmShape", FOREARM_PTS, fill3(prefix + "Forearm", (0, -10), (0, 9), tones)))
    out.append(f"{ind}</Node>")

    # Shoulder cap (rear delt on the posterior side).
    sh_id = nid()
    shoulder_sx = lambda a: 0.5 + 0.35 * a["ua_len"]
    key_double(sh_id, 15, g(lambda a: a["ua"]))
    key_double(sh_id, 16, g(shoulder_sx))
    key_double(sh_id, 17, g(lambda a: 0.8 * a["su"]), hold=True)
    out.append(f'{ind}<Node x="{f(ax)}" y="{f(ay)}" rotation="{f(p0["ua"])}" scaleX="{f(shoulder_sx(p0))}" '
               f'scaleY="{f(0.8 * p0["su"])}" name="{prefix}Shoulder" id="{sh_id}">')
    if near:
        out.append(smooth_shape(i2, f"{prefix}RearDeltActivation", REAR_DELT_PTS, muscle_paint(prefix + "RearDelt")))
        out.append(stroke_shape(i2, f"{prefix}DeltHighlight", [(-4, 9), (8, 12), (20, 8)], 3, HIGHLIGHT, 3.5))
    out.append(smooth_shape(i2, f"{prefix}Deltoid", DELT_PTS, fill3(prefix + "Deltoid", (0, 15), (0, -16), tones)))
    out.append(f"{ind}</Node>")

    # Upper arm.
    ua_id = nid()
    key_double(ua_id, 15, g(lambda a: a["ua"]))
    key_double(ua_id, 16, g(lambda a: a["ua_len"]))
    key_double(ua_id, 17, g(lambda a: a["su"]), hold=True)
    out.append(f'{ind}<Node x="{f(ax)}" y="{f(ay)}" rotation="{f(p0["ua"])}" scaleX="{f(p0["ua_len"])}" '
               f'scaleY="{f(p0["su"])}" name="{prefix}UpperArm" id="{ua_id}">')
    if near:
        out.append(smooth_shape(i2, f"{prefix}BicepsActivation", BICEPS_PTS, muscle_paint(prefix + "Biceps")))
    out += shading(i2, prefix + "UpperArm", UPPER_ARM_HI, UPPER_ARM_SH)
    out.append(smooth_shape(i2, f"{prefix}UpperArmShape", UPPER_ARM_PTS, fill3(prefix + "UpperArm", (0, -14), (0, 13), tones)))
    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- barbell
def disc_pts(x, r, n=16):
    """Circle of radius r in the (Z, Y) plane at lateral offset x, projected relative to the bar centre."""
    return [pvec((x, r * math.sin(2 * math.pi * k / n), r * math.cos(2 * math.pi * k / n))) for k in range(n)]


def plate_items(indent, nm, side):
    """Weight plates, collar and sleeve for one side, sorted near (smaller X) -> far."""
    items = []  # (x, xml)

    def slab(tag, x0, x1, r, face_tones):
        xs = sorted((x0 * side, x1 * side))
        near_x, far_x = xs[0], xs[1]
        n_slices = 5
        for k in range(n_slices):
            x = lerp(far_x, near_x, k / (n_slices - 1))
            if k < n_slices - 1:
                items.append((x, smooth_shape(indent, f"{nm}{tag}Edge{k}", disc_pts(x, r),
                                              solid(f"{nm}{tag}Edge{k}", "FF0B1220"))))
        face = disc_pts(near_x, r)
        top = pvec((near_x, r, 0.0))
        bot = pvec((near_x, -r, 0.0))
        face_xml = "\n".join([
            smooth_shape(indent, f"{nm}{tag}Hub", disc_pts(near_x, 4.5), solid(f"{nm}{tag}Hub", "FF94A3B8")),
            f'{indent}<Shape name="{nm}{tag}Ring"><PointsPath isClosed="true" name="{nm}{tag}RingPath">\n'
            f"{smooth_vertices(disc_pts(near_x, r * 0.55), True, indent + '    ')}\n"
            f'{indent}</PointsPath><Stroke thickness="1.2" name="{nm}{tag}RingStroke"><SolidColor colorValue="59FFFFFF" name="{nm}{tag}RingColor"/></Stroke></Shape>',
            f'{indent}<Shape name="{nm}{tag}Face"><PointsPath isClosed="true" name="{nm}{tag}FacePath">\n'
            f"{smooth_vertices(face, True, indent + '    ')}\n"
            f'{indent}</PointsPath>{fill3(nm + tag + "Face", top, bot, face_tones)}'
            f'<Stroke thickness="2" name="{nm}{tag}Rim"><SolidColor colorValue="FF64748B" name="{nm}{tag}RimColor"/></Stroke></Shape>',
        ])
        items.append((near_x - 0.01, face_xml))

    slab("BigPlate", 62, 70, 34, PLATE)
    slab("SmallPlate", 70, 75, 24, PLATE)
    for tag, x0, x1, w, col in (("Collar", 75, 79, 12, "FF94A3B8"), ("Sleeve", 79, 95, 8, "FFCBD5E1")):
        a, b = pvec((x0 * side, 0, 0)), pvec((x1 * side, 0, 0))
        items.append((min(x0 * side, x1 * side) + (0.0 if side < 0 else 2.0),
                      stroke_shape(indent, f"{nm}{tag}", [a, b], w, col, 0, cap="butt")))
    items.sort(key=lambda it: it[0])
    return [xml for _, xml in items]


def bar_node(name, children_fn):
    ind = "        "
    nid_ = nid()
    c0 = proj(bar_center(0.0))
    key_double(nid_, 13, lambda P: proj(bar_center(P["p"]))[0])
    key_double(nid_, 14, lambda P: proj(bar_center(P["p"]))[1])
    return "\n".join([f'{ind}<Node x="{f(c0[0])}" y="{f(c0[1])}" name="{name}" id="{nid_}">',
                      children_fn(ind + "    "),
                      f"{ind}</Node>"])


def shaft(indent):
    a, b = pvec((-62.0, 0, 0)), pvec((62.0, 0, 0))
    return "\n".join([
        stroke_shape(indent, "ShaftSheen", [a, b], 1.2, "8CFFFFFF", 0, cap="butt").replace("<Shape ", '<Shape y="-1.2" ', 1),
        stroke_shape(indent, "Shaft", [a, b], 4.5, "FF94A3B8", 0, cap="butt"),
    ])


# ---------------------------------------------------------------- bounds -> artboard
def bounds_points():
    pts = [TOE[s] for s in (1, -1)] + [v_add(ANKLE[s], (0, -7, -9)) for s in (1, -1)]
    pts += [v_add(HEAD_C, v_scale(d, 22)) for d in (X3, Y3, Z3, v_scale(X3, -1), v_scale(Z3, -1))]
    pts += [back_pt(-22, w) for w in (-23, 23)]
    for p in (0.0, 1.0):
        c = bar_center(p)
        for x in (-95.0, 95.0):
            for k in range(8):
                a = 2 * math.pi * k / 8
                pts.append(v_add(c, (x, 34 * math.sin(a), 34 * math.cos(a))))
    for fr in FRAMES:
        for tag in ("near", "far"):
            pts.append(POSES[fr][tag]["e3"])
    return pts


_raw = [pvec(p) for p in bounds_points()]
MIN_X, MAX_X = min(p[0] for p in _raw), max(p[0] for p in _raw)
MIN_Y, MAX_Y = min(p[1] for p in _raw), max(p[1] for p in _raw)
W, H = 640, 360  # 16:9 standard matching ab_wheel_rollout
FLOOR = 300.0
feet_raw_y = max(pvec(v_add(ANKLE[s], (0, -7, -9)))[1] for s in (1, -1))
OFFSET[0] = W / 2.0 - (MIN_X + MAX_X) / 2.0
OFFSET[1] = FLOOR - feet_raw_y
FOOT_MID = proj((0.0, 0.0, 10.0))


def shadow():
    ind = "        "
    return (
        f'{ind}<Shape x="{f(FOOT_MID[0])}" y="{f(FLOOR - 2)}" scaleX="0.75" scaleY="0.14" name="BodyShadow">\n'
        f'{ind}    <Ellipse width="200" height="200" name="ShadowEllipse"/>\n'
        f'{ind}    <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="100" endY="0" name="ShadowGrad">'
        f'<GradientStop colorValue="B3000000" position="0"/><GradientStop colorValue="59000000" position="0.6"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{ind}</Shape>"
    )


def scenery():
    ind = "        "
    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", (0, -band_h / 2), (0, band_h / 2), "FF172033", "FF0B1120") + "</Fill>"
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


# ---------------------------------------------------------------- assemble
I2 = "            "


def static_group(name, xml):
    return f'        <Node name="{name}">\n{xml}\n        </Node>'


near_plate = bar_node("NearPlates", lambda ind: "\n".join(plate_items(ind, "Near", -1)))
glute_xml = static_group("Glutes", glutes(I2))
near_leg = static_group("NearLeg", leg(I2, -1))
near_arm = arm("near")
head_xml = static_group("HeadNeck", head_and_neck(I2))
back_xml = static_group("Back", back(I2))
side_xml = static_group("TorsoSide", torso_side(I2))
far_leg = static_group("FarLeg", leg(I2, 1))
far_arm = arm("far")
shaft_xml = bar_node("BarShaft", shaft)
far_plate = bar_node("FarPlates", lambda ind: "\n".join(plate_items(ind, "Far", 1)))
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
            if 0 < i < len(vals) - 1 and v == vals[i - 1][1] and v == vals[i + 1][1]:
                continue
            if kind == "color":
                out.append(f'                    <KeyFrameColor value="{v}" interpolationType="linear" frame="{fr}"/>')
            else:
                interp = "hold" if kind == "hold" else "linear"
                out.append(f'                    <KeyFrameDouble value="{v:.4f}" interpolationType="{interp}" frame="{fr}"/>')
        out.append("                </KeyedProperty>")
        out.append("            </KeyedObject>")
    return "\n".join(out)


rml = f"""<Rive version="1" kind="fragment">
    <!-- Barbell Row: rear three-quarter view, 60 fps, generated by gen_barbell_row.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="BarbellRow" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

{near_plate}
{glute_xml}
{near_leg}
{near_arm}
{head_xml}
{back_xml}
{side_xml}
{far_leg}
{far_arm}
{shaft_xml}
{far_plate}

        <!-- Floor shadow -->
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

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="Row" id="0:60">
{keyed_xml()}
        </LinearAnimation>
    </Artboard>
</Rive>
"""

OUT.write_text(rml)

print(f"artboard {W}x{H} floor={FLOOR:.1f}")
for fr in (0, 20, 40, 66, 78, 120, DURATION):
    P = POSES[fr]
    a = P["near"]
    e, h = a["e3"], a["h3"]
    print(f"f{fr:3d} p={P['p']:.3f} elbow=({e[0]:.1f},{e[1]:.1f},{e[2]:.1f}) hand=({h[0]:.1f},{h[1]:.1f},{h[2]:.1f}) "
          f"ua={math.degrees(a['ua']):.0f} su={a['su']:+.0f} sf={a['sf']:+.0f}")
print("keyed props:", len(keys), "bytes:", len(rml))


def publish():
    """Build the .riv, copy it into the Flutter assets and render the catalog thumbnail."""
    subprocess.run([str(RIVE_BIN), ".", "--once"], cwd=HERE, check=True)
    built = HERE / "build/barbell_row.riv"
    shutil.copyfile(built, ASSET_RIV)
    ASSET_THUMB.parent.mkdir(parents=True, exist_ok=True)
    full = HERE / "build/thumbnail_full.png"
    subprocess.run(
        [str(RIVE_BIN), ".", f"--screenshot={full}", f"--advance={THUMB_ADVANCE}",
         "--viewport=1280x720", "--fit=contain"],
        cwd=HERE,
        check=True,
    )
    # Crop 720x720 centered around the athlete from the 1280x720 render
    subprocess.run(["sips", "-c", "720", "720", "--cropOffset", "0", "280",
                    str(full), "--out", str(ASSET_THUMB)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["sips", "-Z", str(THUMB_SIZE), str(ASSET_THUMB)], check=True, stdout=subprocess.DEVNULL)
    full.unlink()
    print("published", ASSET_RIV, ASSET_THUMB)


if "--publish" in sys.argv:
    publish()
