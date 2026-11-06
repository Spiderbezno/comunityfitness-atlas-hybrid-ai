"""Generates rive_animations/arnold_press/scene.rml (and optionally publishes).

Front-view stylized athlete performing a seated Arnold press at 60 fps.

Same character as ab_wheel_rollout (palette, 3-stop gradients, feathered
highlights / core shadows, muscle activation paint, limb outlines), drawn from
the front so the frontal-plane part of the lift reads clearly: the elbows open
from in front of the chest to the sides while the palms turn 180 degrees, then
the dumbbells press overhead.

Arms are solved in 3D (x lateral/outward, y up, z toward the camera) and
projected with a slight downward camera tilt. Each arm segment is a root-level
node: rotation follows the projected bone, scaleX encodes foreshortening and
scaleY mirrors the outline when the anterior side turns around. The dumbbell
shows the wrist rotation: horizontal bar with edge-on plates (palms in), plate
faces toward the camera at mid-rotation, horizontal again at lockout.

Activations (orange -> red as the dumbbells go overhead): anterior + lateral
deltoid heads, upper trapezius and triceps.

Usage (from this directory):
    python3 gen_arnold_press.py            # regenerate scene.rml
    python3 gen_arnold_press.py --publish  # + build .riv, copy to assets, render thumbnail
"""

import math
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "scene.rml"
REPO = HERE.parent.parent
ASSET_RIV = REPO / "assets/animations/arnold_press.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/arnold_press.png"
THUMB_ADVANCE = "0.9s"
THUMB_VIEWPORT = "1280x720"  # 2x the artboard
THUMB_CROP = (720, 0, 280)  # square size, offsetY, offsetX in the 2x render
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

W, H = 640, 360
CX = 0.0
SCALE = 0.70
TARGET_FLOOR = 300.0

UPPER_ARM, FOREARM = 60.0, 56.0
GRIP = FOREARM + 4.5
SHOULDER_X, SHOULDER_Y = 36.0, 192.0
TILT = math.radians(15.0)  # camera slightly above the athlete

# Lower body (body-centred coordinates, x to screen right).
HIP_J = (18.0, 300.0)
KNEE_J = (50.0, 342.0)
ANKLE_J = (55.0, 412.0)
FLOOR = ANKLE_J[1] + 10.0
THIGH_LEN, SHIN_LEN = 72.0, 70.0

# Timeline (frames @60fps): press 1.5s, lockout 0.25s, lower 1.45s, reset 0.4s.
PRESS, HOLD_TOP, LOWER, HOLD_BOTTOM = 90, 15, 87, 24
DURATION = PRESS + HOLD_TOP + LOWER + HOLD_BOTTOM
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


def press(frame):
    fr = frame % DURATION
    if fr <= PRESS:
        return EASE(fr / PRESS)
    fr -= PRESS
    if fr <= HOLD_TOP:
        return 1.0
    fr -= HOLD_TOP
    if fr <= LOWER:
        return 1.0 - EASE(fr / LOWER)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def mirror(pts):
    """Mirror a right-half outline (listed top -> bottom) into a closed symmetric outline."""
    return list(pts) + [(-x, y) for x, y in reversed(pts)]


def flip_x(pts):
    return [(-x, y) for x, y in pts]


# ---------------------------------------------------------------- 3D arm
def v_norm(v):
    m = math.sqrt(sum(c * c for c in v))
    return tuple(c / m for c in v)


def v_dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def v_sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def v_scale(a, s):
    return tuple(x * s for x in a)


def proj(v):
    """3D direction -> screen vector (y down), camera tilted down by TILT."""
    return (v[0], -v[1] * math.cos(TILT) + v[2] * math.sin(TILT))


VIEW = (0.0, math.sin(TILT), math.cos(TILT))  # toward the camera

# Keyposes for the screen-right arm (x = outward): start / goalpost / lockout.
U_KEYS = ((0.10, -0.35, 0.93), (0.97, 0.05, 0.22), (0.30, 0.95, 0.06))
F_KEYS = ((-0.10, 0.99, 0.05), (0.0, 1.0, 0.05), (-0.17, 0.98, 0.0))


def bez_dir(keys, t, side):
    a, b, c = [(k[0] * side, k[1], k[2]) for k in keys]
    ctrl = tuple(2 * bm - (am + cm) / 2 for am, bm, cm in zip(a, b, c))  # passes through b at t=0.5
    v = tuple((1 - t) ** 2 * am + 2 * t * (1 - t) * cm + t * t * zm for am, cm, zm in zip(a, ctrl, c))
    return v_norm(v)


def arm_geometry(p, side):
    u = bez_dir(U_KEYS, p, side)
    fd = bez_dir(F_KEYS, p, side)
    th = math.pi * smoothstep(0.0, 0.7, p)
    handle = (side * math.cos(th), 0.0, -math.sin(th))
    palm = (-side * math.sin(th), 0.0, -math.cos(th))
    anchor = (CX + side * SHOULDER_X, SHOULDER_Y)
    pu, pf = proj(u), proj(fd)
    elbow = (anchor[0] + pu[0] * UPPER_ARM, anchor[1] + pu[1] * UPPER_ARM)
    grip = (elbow[0] + pf[0] * GRIP, elbow[1] + pf[1] * GRIP)
    perp = v_sub(fd, v_scale(u, v_dot(fd, u)))
    pm = math.sqrt(v_dot(perp, perp))
    w = min(1.0, pm / 0.3)
    ant_u = tuple(w * (c / pm if pm > 1e-6 else 0.0) + (1 - w) * q for c, q in zip(perp, palm))
    ph = proj(handle)
    return {
        "anchor": anchor,
        "elbow": elbow,
        "grip": grip,
        "ua": math.atan2(pu[1], pu[0]),
        "ua_len": math.hypot(*pu),
        "fa": math.atan2(pf[1], pf[0]),
        "fa_len": math.hypot(*pf),
        "ant_u": proj(ant_u),
        "ant_f": proj(palm),
        "handle_proj": ph,
        "handle_d": v_dot(handle, VIEW),
        "theta": th,
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


def plate_sign_track(geoms, dead=0.1):
    cur = 1.0 if geoms[0]["handle_d"] >= 0 else -1.0
    for _ in range(2):
        out = []
        for g in geoms:
            if abs(g["handle_d"]) >= dead:
                cur = 1.0 if g["handle_d"] > 0 else -1.0
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
    poses = {fr: {"p": press(fr)} for fr in FRAMES}
    for side, tag in ((1, "right"), (-1, "left")):
        geoms = [arm_geometry(poses[fr]["p"], side) for fr in FRAMES]
        su = flip_track(geoms, "ua", "ant_u")
        sf = flip_track(geoms, "fa", "ant_f")
        ps = plate_sign_track(geoms)
        ua = unwrap([g["ua"] for g in geoms])
        fa = unwrap([g["fa"] for g in geoms])
        ha = unwrap([math.atan2(g["handle_proj"][1], g["handle_proj"][0]) for g in geoms])
        for i, fr in enumerate(FRAMES):
            g = dict(geoms[i])
            g.update(ua=ua[i], fa=fa[i], su=su[i], sf=sf[i], ps=ps[i], ha=ha[i])
            poses[fr][tag] = g
    return poses


POSES = build_poses()

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


def stroke_shape(indent, name, pts, width, color, feather):
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


def rect_shape(indent, name, cx, cy, w, h, radius, paint_xml):
    return (
        f'{indent}<Shape x="{f(float(cx))}" y="{f(float(cy))}" name="{name}">'
        f'<Rectangle width="{f(float(w))}" height="{f(float(h))}" cornerRadiusTL="{f(float(radius))}" name="{name}Rect"/>'
        f"{paint_xml}</Shape>"
    )


# ---------------------------------------------------------------- palette (ab_wheel_rollout)
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "4D0F172A"
MUSCLE_LOW = (0x4D, 0xFB, 0x92, 0x3C)
MUSCLE_HIGH = (0xF2, 0xEF, 0x44, 0x44)
MUSCLE_LINE_LOW = (0x33, 0xC2, 0x41, 0x0C)
MUSCLE_LINE_HIGH = (0xCC, 0x8B, 0x1A, 0x1A)
PLATE = ("FF475569", "FF1E293B", "FF0B1220")


def argb_lerp(a, b, t):
    return "".join(f"{round(lerp(x, y, t)):02X}" for x, y in zip(a, b))


def skin_fill(name, y0, y1, tones):
    return f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *tones)}</Fill>'


def hskin_fill(name, x0, x1, tones=SKIN):
    """Front-lit volume: light from the upper left, shade on the right."""
    c0, c1, c2 = tones
    return f'<Fill name="{name}Fill">{grad3(name + "Grad", 0, 0, c1, c0, c2, x0, x1)}</Fill>'


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


# ---------------------------------------------------------------- limb outlines (ab_wheel_rollout)
UPPER_ARM_PTS = [(-15, 0), (-12, -11), (2, -14.5), (18, -12.5), (31, -12), (45, -10), (57, -7.5), (64, -6.5),
                 (69, 0), (64, 6.5), (52, 8.5), (36, 12.5), (20, 13), (4, 13.5), (-10, 10)]
UPPER_ARM_HI = [(6, -9), (20, -8.5), (33, -8), (50, -5.5)]
UPPER_ARM_SH = [(6, 9.5), (22, 9.5), (38, 8.5), (54, 5)]
TRICEPS_PTS = [(6, 5.5), (20, 6.5), (36, 6), (50, 4), (56, 6.5), (44, 9), (28, 11), (12, 11.5), (2, 9.5)]

FOREARM_PTS = [(-9, 0), (-8, -7.5), (6, -10.5), (21, -9), (37, -6.5), (51, -5), (58, -4.5),
               (62, 0), (58, 4.5), (44, 5.5), (27, 7.5), (10, 8.5), (-4, 8)]
FOREARM_HI = [(6, -6.5), (22, -6), (42, -3.8)]
FOREARM_SH = [(8, 5.5), (28, 4.8), (46, 3.2)]
HAND_PTS = [(-4, -7.5), (8, -8.5), (15, -4.5), (15.5, 3.5), (8, 8), (-4, 7.5), (-7, 0)]

THIGH_PTS = [(-19, 0), (-14, -12), (6, -17), (30, -17.5), (52, -14.5), (66, -11), (77, -9.5),
             (83, 0), (77, 9), (60, 10), (40, 13), (18, 17), (-2, 19), (-16, 12)]
THIGH_HI = [(8, -12.5), (32, -13.5), (56, -10)]
THIGH_SH = [(10, 13.5), (36, 9.5), (60, 6.5)]
SHORTS_THIGH_FRONT = [(-21, 0), (-15, -14), (6, -19), (25, -18.5), (27, 15.5), (14, 19), (-4, 21), (-18, 13)]
SHORTS_THIGH_PTS = [(-21, 0), (-15, -14), (6, -19), (36, -18.5), (38, 14.5), (14, 19), (-4, 21), (-18, 13)]

SHIN_PTS = [(-11, 0), (-10, -8), (14, -8.5), (40, -7), (62, -5), (72, -4.5),
            (76, 0), (72, 5), (56, 6.5), (36, 10.5), (18, 14), (4, 12.5), (-8, 8.5)]
SHIN_HI = [(10, -5), (40, -4.5), (62, -3)]
SHIN_SH = [(18, 9), (36, 7), (56, 4.5)]

# ---------------------------------------------------------------- front-view outlines (same character)
# Deltoid cap seen from the front: symmetric across the bone so it works on either arm.
DELT_PTS = [(-16, 0), (-12, -13), (2, -16.5), (17, -14), (28, -6), (29, 4), (18, 13), (2, 15.5), (-12, 12)]
FRONT_DELT_PTS = [(-8, -10), (3, -13.5), (16, -11), (25, -4.5), (16, -1.5), (4, -2.5)]
LATERAL_DELT_PTS = [(-8, 10), (3, 12.5), (16, 10.5), (25, 4), (16, 1.5), (4, 2.5)]

HEAD_PTS = mirror([(0, 127), (9, 128.5), (14.5, 135), (16, 146), (15, 157), (11.5, 165), (6, 170.5)])
HAIR_PTS = [(-15.5, 146), (-15, 136), (-10, 128.5), (0, 125.5), (10, 128.5), (15, 136), (15.5, 146),
            (12, 139), (5, 135.5), (-5, 135.5), (-12, 139)]
HEAD_HI = [(-10, 137), (-12.5, 146), (-12, 154)]
NECK_PTS = mirror([(0, 164), (9, 165), (10, 177), (13, 186)])
TORSO_RIGHT = [(0, 178), (12, 180), (26, 184), (40, 189), (46, 199), (43, 214), (39, 233), (32, 254), (30, 270), (29, 284)]
TORSO_PTS = TORSO_RIGHT + [(0, 290)] + [(-x, y) for x, y in reversed(TORSO_RIGHT[1:])]
TORSO_HI = [(-34, 198), (-36, 214), (-32, 236), (-26, 256)]
TORSO_SH = [(37, 212), (34, 232), (28, 252), (26, 270)]
PEC_R = [(3, 199), (16, 196), (31, 199), (38, 209), (32, 221), (17, 225), (4, 221)]
PEC_SH = [(5, 224), (18, 227.5), (33, 221)]
TRAP_R = [(8, 177), (18, 179.5), (31, 185), (36, 190), (26, 191), (14, 187), (8, 184)]
SHORTS_PTS = mirror([(0, 266), (31, 266), (34, 281), (39, 296), (30, 306), (12, 306), (0, 299)])

FOOT_R = [(-6, -4), (6, -4), (10, 2), (12, 9), (8, 11.5), (-6, 11.5), (-9, 5)]


def abs_blocks(indent):
    """Rectus abdominis: neutral definition (not a working muscle in this lift)."""
    out = []
    for k, (y0, h) in enumerate(((232, 10), (245, 10), (258, 10.5))):
        for s in (1, -1):
            x_in, x_out = 2.0 * s, 12.5 * s
            pts = [(x_in, y0), (x_out, y0 + 0.8), (x_out + 0.8 * s, y0 + h / 2), (x_out, y0 + h),
                   (x_in, y0 + h + 0.5), (x_in - 0.4 * s, y0 + h / 2)]
            nm = f"Abs{k + 1}{'R' if s > 0 else 'L'}"
            paint = (f'<Fill name="{nm}Fill"><SolidColor colorValue="140F172A" name="{nm}Color"/></Fill>'
                     f'<Stroke thickness="0.8" join="round" name="{nm}Edge"><SolidColor colorValue="2E0F172A" name="{nm}EdgeColor"/></Stroke>')
            out.append(smooth_shape(indent, nm, pts, paint))
    return "\n".join(out)


def shading(indent, nm, hi, sh, hw=3.2, sw=6.0):
    return [stroke_shape(indent, nm + "Highlight", hi, hw * 1.5, HIGHLIGHT, 4),
            stroke_shape(indent, nm + "CoreShadow", sh, sw * 1.3, CORE_SHADOW, 7)]


# ---------------------------------------------------------------- arms + dumbbells
def plate_node(indent, name):
    """Weight plate seen face-on at scaleX=1; scaleX shrinks it toward edge-on."""
    pid = nid()
    xml = (
        f'{indent}<Node name="{name}" id="{pid}">\n'
        f'{indent}    <Shape name="{name}Hub"><Ellipse width="7" height="7" name="{name}HubEllipse"/>{solid(name + "Hub", "FF94A3B8")}</Shape>\n'
        f'{indent}    <Shape name="{name}Ring"><Ellipse width="17" height="17" name="{name}RingEllipse"/>'
        f'<Stroke thickness="1.2" name="{name}RingStroke"><SolidColor colorValue="59FFFFFF" name="{name}RingColor"/></Stroke></Shape>\n'
        f'{indent}    <Shape name="{name}Disc"><Ellipse width="27" height="27" name="{name}DiscEllipse"/>'
        f'<Fill name="{name}DiscFill">{grad3(name + "DiscGrad", -13.5, 13.5, *PLATE)}</Fill>'
        f'<Stroke thickness="2" name="{name}Rim"><SolidColor colorValue="FF64748B" name="{name}RimColor"/></Stroke></Shape>\n'
        f"{indent}</Node>"
    )
    return pid, xml


PLATE_OFFSET = 16.0
PLATE_MIN_SX = 0.3


def plate_pos(a, front):
    s = a["ps"] if front else -a["ps"]
    return (PLATE_OFFSET * a["handle_proj"][0] * s, PLATE_OFFSET * a["handle_proj"][1] * s)


def plate_sx(a):
    return max(PLATE_MIN_SX, abs(a["handle_d"]))


def arm(prefix, tag):
    ind = "        "
    i2 = ind + "    "
    out = []
    p0 = POSES[0][tag]

    def g(fn):
        return lambda P: fn(P[tag])

    def plate_group(group_name, front, with_handle):
        gid = nid()
        key_double(gid, 13, g(lambda a: a["grip"][0]))
        key_double(gid, 14, g(lambda a: a["grip"][1]))
        out.append(f'{ind}<Node x="{f(p0["grip"][0])}" y="{f(p0["grip"][1])}" name="{prefix}{group_name}" id="{gid}">')
        if with_handle:
            hid = nid()
            key_double(hid, 15, g(lambda a: a["ha"]))
            key_double(hid, 16, g(lambda a: max(0.08, math.hypot(*a["handle_proj"]))))
            out.append(f'{i2}<Shape rotation="{f(p0["ha"])}" scaleX="{f(max(0.08, math.hypot(*p0["handle_proj"])))}" name="{prefix}Handle" id="{hid}">'
                       f'<Rectangle width="34" height="5" cornerRadiusTL="2.5" name="{prefix}HandleRect"/>'
                       f'<Fill name="{prefix}HandleFill">{grad(prefix + "HandleGrad", 0, -2.5, 0, 2.5, "FFCBD5E1", "FF475569")}</Fill></Shape>')
        nm = f"{prefix}{'Front' if front else 'Back'}Plate"
        pid, pxml = plate_node(i2, nm)
        key_double(pid, 13, g(lambda a: plate_pos(a, front)[0]), hold=True)
        key_double(pid, 14, g(lambda a: plate_pos(a, front)[1]), hold=True)
        key_double(pid, 16, g(plate_sx))
        px, py = plate_pos(p0, front)
        out.append(pxml.replace(f'id="{pid}"', f'x="{f(px)}" y="{f(py)}" scaleX="{f(plate_sx(p0))}" id="{pid}"'))
        out.append(f"{ind}</Node>")

    # Front plate (closest to the camera) above the fist.
    plate_group("DumbbellFront", True, False)

    # Forearm + hand.
    fa_id = nid()
    key_double(fa_id, 13, g(lambda a: a["elbow"][0]))
    key_double(fa_id, 14, g(lambda a: a["elbow"][1]))
    key_double(fa_id, 15, g(lambda a: a["fa"]))
    key_double(fa_id, 16, g(lambda a: a["fa_len"]))
    key_double(fa_id, 17, g(lambda a: a["sf"]), hold=True)
    out.append(f'{ind}<Node x="{f(p0["elbow"][0])}" y="{f(p0["elbow"][1])}" rotation="{f(p0["fa"])}" '
               f'scaleX="{f(p0["fa_len"])}" scaleY="{f(p0["sf"])}" name="{prefix}Forearm" id="{fa_id}">')
    out.append(smooth_shape(i2, f"{prefix}Hand", HAND_PTS, skin_fill(prefix + "Hand", -8, 8, SKIN), x=FOREARM))
    out += shading(i2, prefix + "Forearm", FOREARM_HI, FOREARM_SH, 2.6, 4.5)
    out.append(smooth_shape(i2, f"{prefix}ForearmShape", FOREARM_PTS, skin_fill(prefix + "Forearm", -10, 9, SKIN)))
    out.append(f"{ind}</Node>")

    # Handle + back plate behind the fist.
    plate_group("DumbbellBack", False, True)

    # Shoulder cap. Mirrored per side so the lateral head always sits on the outside.
    side = 1.0 if tag == "right" else -1.0
    sh_id = nid()
    shoulder_sx = lambda a: 0.6 + 0.4 * a["ua_len"]
    key_double(sh_id, 15, g(lambda a: a["ua"]))
    key_double(sh_id, 16, g(shoulder_sx))
    ax, ay = p0["anchor"]

    def delt_flip(a):
        # Local +y (lateral head) must point away from the midline / upward.
        ang = a["ua"]
        lat = (-math.sin(ang), math.cos(ang))  # world direction of local +y
        return 1.0 if lat[0] * side - 0.35 * lat[1] >= 0 else -1.0

    key_double(sh_id, 17, g(delt_flip), hold=True)
    out.append(f'{ind}<Node x="{f(ax)}" y="{f(ay)}" rotation="{f(p0["ua"])}" scaleX="{f(shoulder_sx(p0))}" '
               f'scaleY="{f(delt_flip(p0))}" name="{prefix}Shoulder" id="{sh_id}">')
    out.append(smooth_shape(i2, f"{prefix}FrontDeltActivation", FRONT_DELT_PTS, muscle_paint(prefix + "FrontDelt")))
    out.append(smooth_shape(i2, f"{prefix}LateralDeltActivation", LATERAL_DELT_PTS, muscle_paint(prefix + "LateralDelt")))
    out.append(stroke_shape(i2, f"{prefix}DeltHighlight", [(-4, -9), (8, -12), (20, -8)], 3, HIGHLIGHT, 3.5))
    out.append(smooth_shape(i2, f"{prefix}Deltoid", DELT_PTS, skin_fill(prefix + "Deltoid", -16, 15, SKIN)))
    out.append(f"{ind}</Node>")

    # Upper arm.
    ua_id = nid()
    key_double(ua_id, 15, g(lambda a: a["ua"]))
    key_double(ua_id, 16, g(lambda a: a["ua_len"]))
    key_double(ua_id, 17, g(lambda a: a["su"]), hold=True)
    out.append(f'{ind}<Node x="{f(ax)}" y="{f(ay)}" rotation="{f(p0["ua"])}" scaleX="{f(p0["ua_len"])}" '
               f'scaleY="{f(p0["su"])}" name="{prefix}UpperArm" id="{ua_id}">')
    out.append(smooth_shape(i2, f"{prefix}TricepsActivation", TRICEPS_PTS, muscle_paint(prefix + "Triceps")))
    out += shading(i2, prefix + "UpperArm", UPPER_ARM_HI, UPPER_ARM_SH)
    out.append(smooth_shape(i2, f"{prefix}UpperArmShape", UPPER_ARM_PTS, skin_fill(prefix + "UpperArm", -14, 13, SKIN)))
    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- body
def head_and_neck(indent):
    return "\n".join([
        smooth_shape(indent, "Hair", HAIR_PTS, f'<Fill name="HairFill">{grad("HairGrad", 0, 125, 0, 146, "FF475569", "FF1E293B")}</Fill>'),
        stroke_shape(indent, "HeadHighlight", HEAD_HI, 3, HIGHLIGHT, 4),
        stroke_shape(indent, "JawShade", [(-9, 163), (0, 168.5), (9, 163)], 2.5, SOFT_SHADOW, 3),
        smooth_shape(indent, "Head", HEAD_PTS, hskin_fill("Head", -18, 18)),
        ellipse_shape(indent, "EarL", -15.5, 150, 6, 10, solid("EarL", "FFC2CCD9")),
        ellipse_shape(indent, "EarR", 15.5, 150, 6, 10, solid("EarR", "FFA3B1C4")),
        stroke_shape(indent, "ChinShadow", [(-8, 168), (0, 172), (8, 168)], 4, CORE_SHADOW, 4),
        smooth_shape(indent, "Neck", NECK_PTS, hskin_fill("Neck", -14, 14)),
    ])


def torso(indent):
    parts = [
        smooth_shape(indent, "TrapActivationR", TRAP_R, muscle_paint("TrapR")),
        smooth_shape(indent, "TrapActivationL", flip_x(TRAP_R), muscle_paint("TrapL")),
        stroke_shape(indent, "PecHighlight", [(-30, 201), (-18, 198), (-6, 200)], 3, HIGHLIGHT, 4),
        stroke_shape(indent, "PecShadowR", PEC_SH, 3.5, SOFT_SHADOW, 3),
        stroke_shape(indent, "PecShadowL", flip_x(PEC_SH), 3.5, SOFT_SHADOW, 3),
        stroke_shape(indent, "Sternum", [(0, 198), (0, 222)], 1.4, SOFT_SHADOW, 1.5),
        stroke_shape(indent, "LineaAlba", [(0, 230), (0, 270)], 1.2, "330F172A", 1.2),
        abs_blocks(indent),
        stroke_shape(indent, "ObliqueR", [(26, 236), (25, 252), (23, 266)], 2, SOFT_SHADOW, 2.5),
        stroke_shape(indent, "ObliqueL", [(-26, 236), (-25, 252), (-23, 266)], 2, "260F172A", 2.5),
    ]
    parts += shading(indent, "Torso", TORSO_HI, TORSO_SH, 4, 8)
    parts.append(smooth_shape(indent, "Torso", TORSO_PTS, hskin_fill("Torso", -52, 48)))
    return "\n".join(parts)


def leg(indent, side):
    """Seated leg seen from the front: thigh foreshortened toward the camera, shin hanging."""
    nm = "R" if side > 0 else "L"
    hx, hy = HIP_J[0] * side, HIP_J[1]
    kx, ky = KNEE_J[0] * side, KNEE_J[1]
    axx, ay = ANKLE_J[0] * side, ANKLE_J[1]
    th_ang = math.atan2(ky - hy, kx - hx)
    th_sx = math.hypot(kx - hx, ky - hy) / THIGH_LEN
    sh_ang = math.atan2(ay - ky, axx - kx)
    sh_sx = math.hypot(axx - kx, ay - ky) / SHIN_LEN
    th_sy = 1.0 if side > 0 else -1.0  # quads toward the top / camera
    sh_sy = -1.0 if side > 0 else 1.0  # calf bulges outward
    i2 = indent + "    "
    foot = FOOT_R if side > 0 else flip_x(FOOT_R)
    out = [
        ellipse_shape(indent, f"KneeCap{nm}", kx, ky, 20, 19, skin_fill(f"Knee{nm}", ky - 10, ky + 10, SKIN)),
        f'{indent}<Node x="{f(hx)}" y="{f(hy)}" rotation="{f(th_ang)}" scaleX="{f(th_sx)}" scaleY="{f(th_sy)}" name="Thigh{nm}">',
        smooth_shape(i2, f"ThighShorts{nm}", SHORTS_THIGH_FRONT, skin_fill(f"ThighShorts{nm}", -19, 21, SHORTS)),
    ]
    out += shading(i2, f"Thigh{nm}", THIGH_HI, THIGH_SH, 3.5, 7)
    out.append(smooth_shape(i2, f"ThighShape{nm}", THIGH_PTS, skin_fill(f"Thigh{nm}", -18, 19, SKIN)))
    out.append(f"{indent}</Node>")
    out.append(smooth_shape(indent, f"Foot{nm}", foot, skin_fill(f"Foot{nm}", -4, 12, SKIN), x=axx, y=ay))
    out.append(f'{indent}<Node x="{f(kx)}" y="{f(ky)}" rotation="{f(sh_ang)}" scaleX="{f(sh_sx)}" scaleY="{f(sh_sy)}" name="Shin{nm}">')
    out += shading(i2, f"Shin{nm}", SHIN_HI, SHIN_SH, 3, 4.5)
    out.append(smooth_shape(i2, f"ShinShape{nm}", SHIN_PTS, skin_fill(f"Shin{nm}", -9, 14, SKIN)))
    out.append(f"{indent}</Node>")
    return "\n".join(out)


def body():
    ind = "        "
    i2 = ind + "    "
    return "\n".join([
        f'{ind}<Node x="{f(CX)}" name="Body">',
        head_and_neck(i2),
        leg(i2, 1),
        leg(i2, -1),
        smooth_shape(i2, "Shorts", SHORTS_PTS, f'<Fill name="ShortsFill">{grad3("ShortsGrad", 0, 0, SHORTS[1], SHORTS[0], SHORTS[2], -45, 45)}</Fill>'),
        torso(i2),
        bench(i2),
        f"{ind}</Node>",
    ])


def bench(indent):
    metal = lambda n, x0, y0, x1, y1: f'<Fill name="{n}Fill">{grad(n + "Grad", x0, y0, x1, y1, "FFE2E8F0", "FF94A3B8")}</Fill>'
    pad = lambda n, x0, y0, x1, y1: f'<Fill name="{n}Fill">{grad(n + "Grad", x0, y0, x1, y1, "FF334155", "FF0F172A")}</Fill>'
    foam = f'<Fill name="FoamFill">{grad("FoamGrad", 0, -5, 0, 5, "FF475569", "FF1E293B")}</Fill>'
    seat_y = 306.0
    post_top, post_bot = seat_y + 9, FLOOR - 7
    return "\n".join([
        rect_shape(indent, "SeatPad", 0, seat_y, 104, 18, 6, pad("SeatPad", 0, -9, 0, 9)),
        rect_shape(indent, "SeatTop", 0, seat_y - 7, 98, 5, 2.5, solid("SeatTop", "FF475569")),
        rect_shape(indent, "BackPad", 0, 236, 84, 124, 9, pad("BackPad", -42, 0, 42, 0)),
        stroke_shape(indent, "BackPadSheen", [(-34, 186), (-34, 280)], 1.6, "33FFFFFF", 1.5),
        rect_shape(indent, "Post", 0, (post_top + post_bot) / 2, 9, post_bot - post_top, 2, metal("Post", -4.5, 0, 4.5, 0)),
        rect_shape(indent, "FrontRail", 0, FLOOR - 5, 150, 5, 2.5, metal("FrontRail", 0, -2.5, 0, 2.5)),
        rect_shape(indent, "FoamR", 80, FLOOR - 5, 22, 10, 5, foam),
        rect_shape(indent, "FoamL", -80, FLOOR - 5, 22, 10, 5, foam),
        rect_shape(indent, "RearRail", 0, FLOOR - 22, 96, 4, 2, solid("RearRail", "FF64748B")),
        rect_shape(indent, "RearPostR", 40, (seat_y + FLOOR - 22) / 2, 5, FLOOR - 22 - seat_y, 2, solid("RearPostR", "FF64748B")),
        rect_shape(indent, "RearPostL", -40, (seat_y + FLOOR - 22) / 2, 5, FLOOR - 22 - seat_y, 2, solid("RearPostL", "FF64748B")),
    ])


def shadow():
    ind = "        "
    return (
        f'{ind}<Shape x="{f(CX)}" y="{f(FLOOR + 1)}" scaleX="0.95" scaleY="0.08" name="BodyShadow">\n'
        f'{ind}    <Ellipse width="200" height="200" name="ShadowEllipse"/>\n'
        f'{ind}    <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="100" endY="0" name="ShadowGrad">'
        f'<GradientStop colorValue="B3000000" position="0"/><GradientStop colorValue="59000000" position="0.6"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{ind}</Shape>"
    )


def scenery():
    ind = "        "
    band_h = H - TARGET_FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"
    return (
        f'{ind}<Shape x="{W / 2}" y="{f(TARGET_FLOOR + 1)}" name="FloorLine"><Rectangle width="{W - 40}" height="2" cornerRadiusTL="1" name="FloorRect"/>'
        f'<Fill name="FloorFill"><LinearGradient startX="{-(W - 40) / 2}" startY="0" endX="{(W - 40) / 2}" endY="0" name="FloorGrad">'
        f'<GradientStop colorValue="00475569" position="0"/><GradientStop colorValue="FF475569" position="0.2"/>'
        f'<GradientStop colorValue="FF475569" position="0.8"/><GradientStop colorValue="00475569" position="1"/></LinearGradient></Fill></Shape>\n'
        f'{ind}<Shape x="{W / 2}" y="{f((TARGET_FLOOR + H) / 2 + 1)}" name="FloorBand"><Rectangle width="{W}" height="{f(band_h)}" name="FloorBandRect"/>'
        f"{band_fill}</Shape>\n"
        f'{ind}<Shape x="{W / 2}" y="{H / 2}" name="Backdrop"><Rectangle width="{W}" height="{H}" name="BackdropRect"/>'
        f'<Fill name="BackdropFill"><RadialGradient startX="0" startY="-40" endX="0" endY="{H * 0.75}" name="BackdropGrad">'
        f'<GradientStop colorValue="FF1E293B" position="0"/><GradientStop colorValue="FF0F172A" position="1"/></RadialGradient></Fill></Shape>'
    )


right_arm = arm("R", "right")
left_arm = arm("L", "left")
body_xml = body()
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
    <!-- Arnold Press: seated front view, 60 fps, generated by gen_arnold_press.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="ArnoldPress" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- Athlete Rig centered and scaled to 16:9 canvas -->
        <Node x="{W / 2}" y="{f(TARGET_FLOOR - FLOOR * SCALE)}" scaleX="{f(SCALE)}" scaleY="{f(SCALE)}" name="AthleteRig">
{right_arm}
{left_arm}
{body_xml}
{shd}
        </Node>

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

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="Press" id="0:60">
{keyed_xml()}
        </LinearAnimation>
    </Artboard>
</Rive>
"""

OUT.write_text(rml)

for fr in (0, 20, 40, 60, 90, 150, 216):
    P = POSES[fr]
    a = P["right"]
    print(
        f"f{fr:3d} p={P['p']:.3f} elbow=({a['elbow'][0] - CX:.1f},{a['elbow'][1]:.1f}) grip=({a['grip'][0] - CX:.1f},{a['grip'][1]:.1f}) "
        f"ua={math.degrees(a['ua']):.0f} su={a['su']:+.0f} sf={a['sf']:+.0f} th={math.degrees(a['theta']):.0f} "
        f"h=({a['handle_proj'][0]:+.2f},{a['handle_proj'][1]:+.2f}) d={a['handle_d']:+.2f} ps={a['ps']:+.0f}"
    )
print("keyed props:", len(keys), "bytes:", len(rml))


def publish():
    """Build the .riv, copy it into the Flutter assets and render the catalog thumbnail."""
    subprocess.run([str(RIVE_BIN), ".", "--once"], cwd=HERE, check=True)
    built = HERE / "build/arnold_press.riv"
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
