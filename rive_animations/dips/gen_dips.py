#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive scene for Chest Dips (id: 'dips').

Matches the 2-panel 3/4 front-left Chest Dips reference illustrations:
  - Image 1 (Chest Dips vs Tricep Dips):
    * "More Forward Lean" (~38 deg forward torso lean at bottom dip)
    * "Feet Behind the Body" (thighs vertical below shifted-back hips, knees flexed ~90 deg with lower legs horizontal behind the body)
  - Image 2 (Top Support -> Bottom Forward-Lean Chest Dip on Dip Station / Captain's Chair):
    * Left panel (Top Support, d = 0.0): Arms extended nearly straight down to the stationary parallel dip bars
      (FAR_HAND = (284, 162), NEAR_HAND = (348, 166)), torso upright (~10 deg tilt), knees flexed below the hips.
    * Right panel (Bottom Deep Chest Dip, d = 1.0): Shoulders & head dive forward-left while hips shift back-right
      into a ~38 deg forward torso lean, elbows flex ~90 deg above/behind the shoulders, and lower legs extend
      horizontally behind the body.
  - 4 Highlighted Muscle Groups (pulsing from warm amber #F97316 at d = 0.0 to vivid crimson #DC2626 at d = 1.0):
    1. Pectoralis major (lower sternocostal-abdominal & upper clavicular heads) — scale = 1.00 (primary mover!)
    2. Anterior deltoid — scale = 0.92 (front shoulder cap)
    3. Pectoralis minor / Serratus anterior / Lateral chest wall — scale = 0.85 (sub-axillary lateral torso band)
    4. Triceps brachii (lateral & long heads) — scale = 0.85 (upper-extensor border of the upper arms)

Run:
    python3 gen_dips.py            # writes scene.rml
    python3 gen_dips.py --publish  # compiles assets/animations/dips.riv + 256x256 thumbnail
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

# Stationary Grip Points on the Parallel Dip Handles (100% locked throughout the entire cycle!)
FAR_HAND = (284.0, 162.0)
NEAR_HAND = (348.0, 166.0)

# Base rest lengths for 3D-foreshortened sibling-node limb segments
UA_FAR_LEN, FA_FAR_LEN = 42.0, 48.0
UA_NEAR_LEN, FA_NEAR_LEN = 44.0, 50.0
THIGH_FAR_LEN, SHIN_FAR_LEN = 58.0, 54.0
THIGH_NEAR_LEN, SHIN_NEAR_LEN = 60.0, 54.0

# Palette — matches existing 16:9 procedural catalog (decline_bench_press, chest_fly, concentration_curl, deadlift)
SKIN = ("FFF8FAFC", "FFCBD5E1", "FF64748B")
SKIN_FAR = ("FFE2E8F0", "FF94A3B8", "FF475569")
SHORTS = ("FF334155", "FF1E293B", "FF0F172A")
FRAME_WHITE = ("FFFFFFFF", "FFE2E8F0", "FF94A3B8")
FRAME_FAR = ("FFF1F5F9", "FFCBD5E1", "FF64748B")
PAD_DARK = ("FF334155", "FF1E293B", "FF090D16")
ANATOMY_LINE = "66475569"
OUTLINE = "990F172A"
HIGHLIGHT = "59FFFFFF"
CORE_SHADOW = "400F172A"

# Muscle activation stops (d = 0.0 Top Support -> d = 1.0 Deep Forward-Lean Chest Dip)
M_REST = ((249, 115, 22), (234, 88, 12), (180, 52, 9))     # #F97316 -> #EA580C -> #B43409
M_PEAK = ((248, 113, 113), (220, 38, 38), (153, 27, 27))   # #F87171 -> #DC2626 -> #991B1B


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


EASE_DESCEND = cubic_bezier(0.38, 0.0, 0.28, 1.0)
EASE_PRESS = cubic_bezier(0.36, 0.0, 0.24, 1.0)


def dip_progress(frame):
    """Returns chest-dip depth d in [0.0, 1.0] across 160 frames:
    - 0..12:   Top Support hold (d = 0.0, Left panel of Image 2)
    - 12..62:  Controlled eccentric descent with increasing forward torso lean (d: 0.0 -> 1.0)
    - 62..82:  Bottom Deep Chest Dip hold (d = 1.0, Right panel of Image 2 & Left panel of Image 1)
    - 82..146: Powerful concentric press back up to Top Support (d: 1.0 -> 0.0)
    - 146..160: Top Support hold (d = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 62:
        return EASE_DESCEND((fr - 12) / 50.0)
    if fr <= 82:
        return 1.0
    if fr <= 146:
        return 1.0 - EASE_PRESS((fr - 82) / 64.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_pt(p0, p1, t):
    return (lerp(p0[0], p1[0], t), lerp(p0[1], p1[1], t))


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
    sc = max(0.45, math.hypot(dx, dy) / base_len)
    return ang, sc


def rot_local(origin, rot_rad, lx, ly):
    cs, sn = math.cos(rot_rad), math.sin(rot_rad)
    return (origin[0] + lx * cs - ly * sn, origin[1] + lx * sn + ly * cs)


def pose(d):
    """Compute Chest Dip torso lean, head, stationary-hand arms, and feet-behind-body legs at depth d in [0.0, 1.0]."""
    # 1. Mid-Shoulder Origin & Forward Torso Lean:
    #    - At d = 0.0 (Top Support, Left panel of Image 2):
    #      mid_sh = (310.0, 91.0), torso_rot = 0.0 deg (torso upright with ~10 deg natural forward tilt)
    #      Local pelvis center (8, 73) -> World HIP_CENTER = (318.0, 164.0)
    #    - At d = 1.0 (Bottom Deep Chest Dip, Right panel of Image 2 & Left panel of Image 1):
    #      mid_sh = (302.0, 131.0), torso_rot = -36.0 deg (pronounced ~38 deg forward chest lean!)
    #      Local pelvis center (8, 73) rotated by -36 deg -> World HIP_CENTER = (351.4, 185.4)
    mid_sh = quad_interp_pt((310.0, 91.0), (305.0, 112.0), (302.0, 131.0), d)
    torso_rot = math.radians(lerp(0.0, -36.0, d))

    # Head tilts forward slightly less than the ribcage so the gaze stays forward-down
    head_counter_rot = math.radians(lerp(0.0, 16.0, d))

    # 2. Shoulder Sockets (FAR_SH, NEAR_SH):
    #    - At d = 0.0: FAR_SH = (284.0, 88.0),  NEAR_SH = (336.0, 94.0)
    #    - At d = 1.0: FAR_SH = (276.0, 128.0), NEAR_SH = (324.0, 134.0)
    far_sh = quad_interp_pt((284.0, 88.0), (279.0, 109.0), (276.0, 128.0), d)
    near_sh = quad_interp_pt((336.0, 94.0), (329.0, 115.0), (324.0, 134.0), d)

    # 3. Elbows (FAR_EL, NEAR_EL) with Stationary Hands Locked at FAR_HAND=(284, 162), NEAR_HAND=(348, 166):
    #    - At d = 0.0 (Top Support): Arms extended nearly straight down to the dip handles:
    #      FAR_EL = (286.0, 126.0), NEAR_EL = (346.0, 130.0)
    #    - At d = 0.5 (Mid Dip):
    #      FAR_EL = (289.0, 127.0), NEAR_EL = (358.0, 122.0)
    #    - At d = 1.0 (Bottom Deep Chest Dip): Near elbow flexes ~90 deg above/behind the dropped shoulder,
    #      while far elbow stays tucked behind the forward-leaning torso:
    #      FAR_EL = (292.0, 128.0), NEAR_EL = (368.0, 116.0)
    far_el = quad_interp_pt((286.0, 126.0), (289.0, 127.0), (292.0, 128.0), d)
    near_el = quad_interp_pt((346.0, 130.0), (358.0, 122.0), (368.0, 116.0), d)

    ua_far_ang, ua_far_sc = seg_xform(far_sh, far_el, UA_FAR_LEN)
    fa_far_ang, fa_far_sc = seg_xform(far_el, FAR_HAND, FA_FAR_LEN)
    ua_near_ang, ua_near_sc = seg_xform(near_sh, near_el, UA_NEAR_LEN)
    fa_near_ang, fa_near_sc = seg_xform(near_el, NEAR_HAND, FA_NEAR_LEN)

    # Anterior Deltoid shoulder cap orientation (tracks torso lean + humeral extension smoothly)
    delt_far_ang = math.radians(lerp(75.0, -18.0, d))
    delt_near_ang = math.radians(lerp(72.0, -18.0, d))

    # 4. Hips, Knees & Feet ("Feet Behind the Body" — ~90 deg knee bend at bottom dip):
    #    Compute exact world positions of FAR_HIP and NEAR_HIP on the rotating pelvis
    far_hip = rot_local(mid_sh, torso_rot, -4.0, 72.0)
    near_hip = rot_local(mid_sh, torso_rot, 16.0, 74.0)

    # Knees descend nearly vertically under the shifted-back hips at d = 1.0:
    far_knee = quad_interp_pt((298.0, 220.0), (324.0, 232.0), (344.0, 242.0), d)
    near_knee = quad_interp_pt((316.0, 226.0), (342.0, 238.0), (364.0, 248.0), d)

    # Lower legs angle back-right at d = 0.0 and bend horizontally behind the body at d = 1.0:
    far_ankle = quad_interp_pt((346.0, 250.0), (374.0, 248.0), (398.0, 244.0), d)
    near_ankle = quad_interp_pt((364.0, 258.0), (392.0, 255.0), (416.0, 252.0), d)

    th_far_ang, th_far_sc = seg_xform(far_hip, far_knee, THIGH_FAR_LEN)
    sh_far_ang, sh_far_sc = seg_xform(far_knee, far_ankle, SHIN_FAR_LEN)
    th_near_ang, th_near_sc = seg_xform(near_hip, near_knee, THIGH_NEAR_LEN)
    sh_near_ang, sh_near_sc = seg_xform(near_knee, near_ankle, SHIN_NEAR_LEN)

    # Feet stay pointing downward (slight plantarflexion behind the body)
    foot_far_ang = math.radians(lerp(78.0, 82.0, d))
    foot_near_ang = math.radians(lerp(78.0, 82.0, d))

    return {
        "d": d,
        "mid_sh": mid_sh,
        "torso_rot": torso_rot,
        "head_counter_rot": head_counter_rot,
        "far_sh": far_sh,
        "near_sh": near_sh,
        "far_el": far_el,
        "near_el": near_el,
        "ua_far_ang": ua_far_ang,
        "ua_far_sc": ua_far_sc,
        "fa_far_ang": fa_far_ang,
        "fa_far_sc": fa_far_sc,
        "ua_near_ang": ua_near_ang,
        "ua_near_sc": ua_near_sc,
        "fa_near_ang": fa_near_ang,
        "fa_near_sc": fa_near_sc,
        "delt_far_ang": delt_far_ang,
        "delt_near_ang": delt_near_ang,
        "far_hip": far_hip,
        "near_hip": near_hip,
        "far_knee": far_knee,
        "near_knee": near_knee,
        "far_ankle": far_ankle,
        "near_ankle": near_ankle,
        "th_far_ang": th_far_ang,
        "th_far_sc": th_far_sc,
        "sh_far_ang": sh_far_ang,
        "sh_far_sc": sh_far_sc,
        "th_near_ang": th_near_ang,
        "th_near_sc": th_near_sc,
        "sh_near_ang": sh_near_ang,
        "sh_near_sc": sh_near_sc,
        "foot_far_ang": foot_far_ang,
        "foot_near_ang": foot_near_ang,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(dip_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = (
    "torso_rot",
    "head_counter_rot",
    "ua_far_ang",
    "fa_far_ang",
    "ua_near_ang",
    "fa_near_ang",
    "delt_far_ang",
    "delt_near_ang",
    "th_far_ang",
    "sh_far_ang",
    "th_near_ang",
    "sh_near_ang",
    "foot_far_ang",
    "foot_near_ang",
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
    for _fr in (0, 36, 70, 114, DURATION):
        _p = POSES[_fr if _fr in POSES else min(POSES.keys(), key=lambda k: abs(k - _fr))]
        print(
            f"f{_fr:3d} d={_p['d']:.3f} mid_sh=({_p['mid_sh'][0]:.1f},{_p['mid_sh'][1]:.1f}) "
            f"near_el=({_p['near_el'][0]:.1f},{_p['near_el'][1]:.1f}) "
            f"near_knee=({_p['near_knee'][0]:.1f},{_p['near_knee'][1]:.1f})"
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


# Muscle activation colors: warm orange (#FFF97316) at Top Support (d=0.0) -> intense crimson (#FFF43F5E) at Bottom Dip (d=1.0)
MUSCLE_LOW = (0xE6, 0xF9, 0x73, 0x16)
MUSCLE_HIGH = (0xFF, 0xF4, 0x3F, 0x5E)
MUSCLE_LINE_LOW = (0x80, 0x9A, 0x34, 0x12)
MUSCLE_LINE_HIGH = (0xE6, 0x88, 0x13, 0x37)


def argb_lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return "".join(f"{round(lerp(x, y, t)):02X}" for x, y in zip(a, b))


def muscle_t(p):
    """Chest-dip muscle activation intensity in [0.42, 1.0] peaking at Bottom Forward-Lean Dip (d = 1.0)."""
    return 0.42 + 0.58 * (p["d"] ** 0.85)


def muscle_paint(name, scale=1.0, line=1.1, y0=-24, y1=24, x0=-14, x1=14):
    """Animated SolidColor muscle fill & edge pulsing from warm orange (d=0.0) to vivid crimson (d=1.0)."""
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


# ---------------------------------------------------------------- 1. 3D Commercial Dip Station / Captain's Chair (Split Z-Order)
def dip_station_layers():
    """Returns (dip_station_back_xml, dip_station_front_left_xml) matching Reference Image 2."""
    ind = "        "
    i2 = ind + "    "

    def frame_paint(name, x0, y0, x1, y1, far=False):
        pal = FRAME_FAR if far else FRAME_WHITE
        return skin_fill_outlined(name, y0, y1, pal, line=1.1, x0=x0, x1=x1, stroke_col="99334155")

    def pad_paint(name, x0, y0, x1, y1):
        return skin_fill_outlined(name, y0, y1, PAD_DARK, line=1.15, x0=x0, x1=x1, stroke_col="FF020617")

    # ---- A. DipStationBack (Background: Far base runner, far upright, far rear arch, backrest pad, far forearm pad, far handle)
    far_runner = [(136, 282), (274, 270), (276, 279), (138, 291)]
    cross_bar = [(158, 282), (206, 294), (200, 300), (152, 288)]
    far_upright = [(222, 276), (194, 146), (207, 144), (235, 275)]
    far_arch_pts = [
        (146, 284), (149, 214), (160, 174), (182, 152), (198, 148),
        (200, 158), (186, 162), (170, 180), (160, 216), (157, 283),
    ]
    far_step_peg = [(218, 232), (254, 230), (254, 236), (218, 238)]
    far_top_beam = [(186, 152), (268, 136), (270, 146), (188, 162)]
    far_arm_pad = [(210, 146), (268, 134), (270, 143), (212, 155)]
    backrest_pad = [(186, 118), (208, 115), (218, 174), (196, 177)]
    backrest_side = [(182, 120), (186, 118), (196, 177), (191, 179)]

    far_back_xml = "\n".join([
        f'{ind}<Node name="DipStationBack">',
        # 1. Far Dip Handle (gripped at FAR_HAND = (284, 162))
        ellipse_shape(i2, "FarHandleEndCap", 298, 162, 5.5, 6.5, solid("FarHandleCap", "FF020617")),
        polyline_stroke_shape(i2, "FarHandleGripHi", [(274, 160), (296, 160)], 1.6, "FF64748B", radius=1.0),
        polyline_stroke_shape(i2, "FarHandleBar", [(256, 144), (272, 162), (298, 162)], 7.2, "FF1E293B", radius=4.0),
        # 2. Far Forearm Pad & Top Support Beam
        poly_shape(i2, "FarForearmPad", far_arm_pad, pad_paint("FarArmPad", 210, 134, 270, 155), radius=3.5),
        poly_shape(i2, "FarTopSupportBeam", far_top_beam, frame_paint("FarTopBeam", 186, 136, 270, 162, far=True), radius=1.8),
        # 3. Vertical Upholstered Backrest Pad (Captain's Chair Back Pad)
        poly_shape(i2, "BackrestPadFace", backrest_pad, pad_paint("BackPad", 186, 115, 218, 177), radius=4.0),
        poly_shape(i2, "BackrestPadSide", backrest_side, solid("BackPadSide", "FF090D16"), radius=3.0),
        polyline_stroke_shape(i2, "BackrestBracket", [(176, 148), (222, 142)], 5.5, "FF1E293B", radius=1.0),
        # 4. Far Foot-Step Peg, Main Upright, Curved Rear Arch & Base Runner
        poly_shape(i2, "FarFootStepPeg", far_step_peg, pad_paint("FarPeg", 218, 230, 254, 238), radius=2.0),
        poly_shape(i2, "FarMainUpright", far_upright, frame_paint("FarUpright", 194, 144, 235, 276, far=True), radius=1.5),
        smooth_shape(i2, "FarRearArch", far_arch_pts, frame_paint("FarArch", 146, 148, 200, 284, far=True)),
        poly_shape(i2, "CrossStabilizerBar", cross_bar, frame_paint("CrossBar", 152, 282, 206, 300, far=True), radius=1.5),
        poly_shape(i2, "FarFrontRubberFoot", [(266, 269), (279, 269), (281, 280), (268, 280)], pad_paint("FarFootCapF", 266, 269, 281, 280), radius=2.0),
        poly_shape(i2, "FarRearRubberFoot", [(130, 282), (142, 281), (143, 292), (131, 293)], pad_paint("FarFootCapR", 130, 281, 143, 293), radius=2.0),
        poly_shape(i2, "FarBaseRunner", far_runner, frame_paint("FarRunner", 136, 270, 276, 291, far=True), radius=1.5),
        f"{ind}</Node>",
    ])

    # ---- B. DipStationFrontLeft (Foreground Left: Near handle stem, near forearm pad, near upright, near rear arch, near base runner)
    #         Drawn IN FRONT of the athlete's right thigh/hip on the left, and BEHIND NearLeftArm!
    near_runner = [(178, 292), (336, 286), (338, 296), (180, 301)]
    near_upright = [(270, 290), (238, 162), (252, 160), (284, 289)]
    near_arch_pts = [
        (188, 294), (191, 224), (202, 184), (224, 164), (242, 160),
        (244, 170), (228, 174), (212, 192), (202, 226), (199, 293),
    ]
    near_step_peg = [(266, 246), (304, 244), (304, 250), (266, 252)]
    near_top_beam = [(230, 164), (314, 148), (316, 158), (232, 174)]
    near_arm_pad = [(242, 156), (308, 142), (310, 151), (244, 165)]

    near_front_xml = "\n".join([
        f'{ind}<Node name="DipStationFrontLeft">',
        # 1. Near Dip Handle Stem & Grip Bar (curves from under NearForearmPad at (302, 154) to NEAR_HAND=(348, 166) and tip (364, 166))
        ellipse_shape(i2, "NearHandleEndCap", 364, 166, 5.8, 7.0, solid("NearHandleCap", "FF020617")),
        polyline_stroke_shape(i2, "NearHandleGripHi", [(324, 164), (362, 164)], 1.8, "FF64748B", radius=1.0),
        polyline_stroke_shape(i2, "NearHandleBar", [(302, 152), (322, 166), (364, 166)], 8.0, "FF1E293B", radius=4.5),
        # 2. Near Forearm Pad & White Horizontal Support Beam
        stroke_shape(i2, "NearPadTopHi", [(246, 156), (306, 143)], 1.4, "FF64748B", 0.2),
        poly_shape(i2, "NearForearmPad", near_arm_pad, pad_paint("NearArmPad", 242, 142, 310, 165), radius=3.8),
        poly_shape(i2, "NearTopSupportBeam", near_top_beam, frame_paint("NearTopBeam", 230, 148, 316, 174, far=False), radius=1.8),
        # 3. Near Foot-Step Peg, Main Upright, Curved Rear Arch & Base Runner
        poly_shape(i2, "NearFootStepPeg", near_step_peg, pad_paint("NearPeg", 266, 244, 304, 252), radius=2.2),
        stroke_shape(i2, "NearUprightHi", [(242, 166), (273, 286)], 2.2, "FFFFFFFF", 0.5),
        poly_shape(i2, "NearMainUpright", near_upright, frame_paint("NearUpright", 238, 160, 284, 290, far=False), radius=1.5),
        smooth_shape(i2, "NearRearArch", near_arch_pts, frame_paint("NearArch", 188, 160, 244, 294, far=False)),
        poly_shape(i2, "NearFrontRubberFoot", [(328, 284), (342, 284), (345, 297), (330, 297)], pad_paint("NearFootCapF", 328, 284, 345, 297), radius=2.2),
        poly_shape(i2, "NearRearRubberFoot", [(172, 291), (185, 291), (186, 301), (173, 301)], pad_paint("NearFootCapR", 172, 291, 186, 301), radius=2.0),
        poly_shape(i2, "NearBaseRunner", near_runner, frame_paint("NearRunner", 178, 286, 338, 301, far=False), radius=1.5),
        f"{ind}</Node>",
    ])

    return far_back_xml, near_front_xml


# ---------------------------------------------------------------- 2. Foreshortened Bent-Knee Legs ("Feet Behind the Body")
def leg_rig(prefix, far):
    """3-segment sibling-node leg (Thigh HIP->KNEE, Shin KNEE->ANKLE, Foot at ANKLE) with sculpted quads, calves, and bare feet."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    hip_key = "far_hip" if far else "near_hip"
    knee_key = "far_knee" if far else "near_knee"
    ankle_key = "far_ankle" if far else "near_ankle"
    th_len = THIGH_FAR_LEN if far else THIGH_NEAR_LEN
    sh_len = SHIN_FAR_LEN if far else SHIN_NEAR_LEN
    th_ang_key = "th_far_ang" if far else "th_near_ang"
    th_sc_key = "th_far_sc" if far else "th_near_sc"
    sh_ang_key = "sh_far_ang" if far else "sh_near_ang"
    sh_sc_key = "sh_far_sc" if far else "sh_near_sc"
    foot_ang_key = "foot_far_ang" if far else "foot_near_ang"

    th_id, sh_id, ft_id = nid(), nid(), nid()
    key_double(th_id, 13, lambda p: p[hip_key][0])
    key_double(th_id, 14, lambda p: p[hip_key][1])
    key_double(th_id, 15, lambda p: p[th_ang_key])
    key_double(th_id, 16, lambda p: p[th_sc_key])

    key_double(sh_id, 13, lambda p: p[knee_key][0])
    key_double(sh_id, 14, lambda p: p[knee_key][1])
    key_double(sh_id, 15, lambda p: p[sh_ang_key])
    key_double(sh_id, 16, lambda p: p[sh_sc_key])

    key_double(ft_id, 13, lambda p: p[ankle_key][0])
    key_double(ft_id, 14, lambda p: p[ankle_key][1])
    key_double(ft_id, 15, lambda p: p[foot_ang_key])
    p0 = POSES[0]

    # Thigh along +X (0 -> th_len): local +Y points anterior/left (Rectus Femoris / Vastus Medialis), -Y points posterior/right (Hamstrings)
    thigh_pts = [
        (-10, 0), (-6, -13.5), (14, -14.0), (th_len * 0.58, -12.0), (th_len - 5, -8.5),
        (th_len + 6, 0), (th_len - 5, 8.8), (th_len * 0.58, 12.8), (14, 14.5), (-6, 13.5),
    ]
    shorts_leg_pts = [
        (-11, -13.8), (22, -14.2), (20, 14.8), (-11, 13.8),
    ]
    # Shin along +X (0 -> sh_len): local -Y is dorsal/upper calf (Gastrocnemius bulge), +Y is anterior/lower shin (Tibialis Anterior)
    shin_pts = [
        (-6, 0), (-3, -8.8), (sh_len * 0.35, -11.5), (sh_len * 0.68, -8.2), (sh_len - 4, -5.2),
        (sh_len + 4, 0), (sh_len - 4, 5.2), (sh_len * 0.5, 7.6), (-3, 7.5),
    ]
    # Bare foot along +X (0 -> 26): heel at (-5, -5) extending down to toes at (26, 4)
    foot_pts = [
        (-6, -5.5), (4, -5.2), (18, -3.5), (27, 0.5), (26, 6.2), (14, 6.8), (2, 5.5), (-6, 3.8),
    ]

    return "\n".join([
        f'{ind}<Node name="{prefix}LegGroup">',
        # 1. Thigh (Quadriceps, Vastus Medialis, Compression Shorts)
        f'{i2}<Node x="{f(p0[hip_key][0])}" y="{f(p0[hip_key][1])}" '
        f'rotation="{f(p0[th_ang_key])}" scaleX="{f(p0[th_sc_key])}" name="{prefix}Thigh" id="{th_id}">',
        smooth_shape(i3, f"{prefix}ThighShorts", shorts_leg_pts, skin_fill_outlined(prefix + "ShortsLeg", -14, 14, SHORTS, line=1.15, stroke_col="CC020617")),
        ellipse_shape(i3, f"{prefix}KneeCap", th_len - 2, 2.0, 13.5, 11.5, skin_fill_outlined(prefix + "Patella", -6, 6, skin, line=0.95)),
        stroke_shape(i3, f"{prefix}RectusFemorisLine", [(22, 3.5), (th_len - 10, 2.8)], 1.3, ANATOMY_LINE, 0.2),
        stroke_shape(i3, f"{prefix}VastusLateralisLine", [(22, -3.2), (th_len - 10, -2.5)], 1.3, ANATOMY_LINE, 0.2),
        stroke_shape(i3, f"{prefix}ThighHi", [(20, 5.8), (th_len - 10, 4.5)], 3.2, HIGHLIGHT, 3.0),
        stroke_shape(i3, f"{prefix}ThighSh", [(20, -6.5), (th_len - 10, -5.2)], 4.0, CORE_SHADOW, 3.8),
        smooth_shape(i3, f"{prefix}ThighShape", thigh_pts, skin_fill_outlined(prefix + "Thigh", -14, 14, skin, line=1.15)),
        f"{i2}</Node>",

        # 2. Bare Foot & Toes (behind the body)
        f'{i2}<Node x="{f(p0[ankle_key][0])}" y="{f(p0[ankle_key][1])}" '
        f'rotation="{f(p0[foot_ang_key])}" name="{prefix}Foot" id="{ft_id}">',
        stroke_shape(i3, f"{prefix}ToeCrease1", [(19, 1.5), (25, 2.2)], 0.95, ANATOMY_LINE, 0.0),
        stroke_shape(i3, f"{prefix}ToeCrease2", [(18, 3.8), (24, 4.5)], 0.95, ANATOMY_LINE, 0.0),
        smooth_shape(i3, f"{prefix}FootShape", foot_pts, skin_fill_outlined(prefix + "Foot", -6, 7, skin, line=1.1)),
        f"{i2}</Node>",

        # 3. Shin & Sculpted Gastrocnemius / Soleus Calf
        f'{i2}<Node x="{f(p0[knee_key][0])}" y="{f(p0[knee_key][1])}" '
        f'rotation="{f(p0[sh_ang_key])}" scaleX="{f(p0[sh_sc_key])}" name="{prefix}Shin" id="{sh_id}">',
        stroke_shape(i3, f"{prefix}GastrocnemiusLine", [(8, -3.8), (sh_len * 0.52, -4.5), (sh_len - 8, -1.8)], 1.25, ANATOMY_LINE, 0.2),
        stroke_shape(i3, f"{prefix}ShinHi", [(6, 2.8), (sh_len - 8, 2.2)], 2.6, HIGHLIGHT, 2.5),
        stroke_shape(i3, f"{prefix}ShinSh", [(8, -6.2), (sh_len - 8, -3.5)], 3.4, CORE_SHADOW, 3.2),
        smooth_shape(i3, f"{prefix}ShinShape", shin_pts, skin_fill_outlined(prefix + "Shin", -11, 8, skin, line=1.15)),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 3. Forward-Leaning Torso, Pectoralis Major/Minor, 6-Pack Abs & 3/4 Head
def torso_and_head_rig():
    """Animated TorsoGroup anchored at MID_SH (tilting from 0 deg at Top Support to -36 deg at Bottom Chest Dip),
    with activated Pectoralis Major (lower & upper), Pectoralis Minor / Serratus Anterior lateral chest wall,
    sculpted 6-pack Rectus Abdominis, compression shorts pelvis, and volumetric 3/4 head."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "
    torso_id = nid()
    head_id = nid()
    key_double(torso_id, 13, lambda p: p["mid_sh"][0])
    key_double(torso_id, 14, lambda p: p["mid_sh"][1])
    key_double(torso_id, 15, lambda p: p["torso_rot"])
    key_double(head_id, 15, lambda p: p["head_counter_rot"])
    p0 = POSES[0]

    # All coordinates inside TorsoGroup are relative to MID_SH = (310, 91) at d = 0.0 (upright posture):
    # - Sternum top (jugular notch): (-8, 2)
    # - Far (right) chest outer border: (-26, 6) .. (-24, 30)
    # - Near (left) chest outer border: (18, 8) .. (16, 34)
    # - Lateral chest wall (Pectoralis minor / Serratus anterior / Latissimus dorsi): (10, 18) .. (24, 52)
    # - Waist / 6-pack abs: (-18, 32) .. (16, 66)
    # - Pelvis / Compression Shorts: (-14, 58) .. (28, 84)

    # 1. Pelvic Compression Shorts (glutes & hip flexors)
    pelvis_shorts = [
        (-16, 60), (2, 56), (22, 52), (30, 66), (26, 84), (4, 86), (-14, 78),
    ]

    # 2. Sculpted 3/4 Male Torso Silhouette
    torso_pts = [
        (-22, -2), (0, -4), (22, 2), (26, 22), (22, 46),
        (22, 64), (4, 70), (-14, 66), (-20, 46), (-24, 22),
    ]

    # 3. Sculpted 6-Pack Rectus Abdominis & External Obliques (in local TorsoGroup coordinates)
    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="240F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.95" join="round" name="AbsEdge"><SolidColor colorValue="520F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        # Right (far / anterior-left) column of 3 abdominal blocks
        [(-16, 31), (-8, 31), (-7, 40), (-15, 40)],
        [(-15, 42), (-7, 42), (-6, 51), (-14, 51)],
        [(-14, 53), (-6, 53), (-5, 61), (-13, 61)],
        # Left (near / anterior-right) column of 3 abdominal blocks
        [(-5, 32), (5, 32), (6, 41), (-4, 41)],
        [(-4, 43), (6, 43), (7, 52), (-3, 52)],
        [(-3, 54), (7, 54), (8, 62), (-2, 62)],
    ]

    # 4. Target Muscle #3: Pectoralis Minor / Serratus Anterior / Lateral Chest Wall (scale = 0.85)
    #    Highlighted crimson lateral torso band beneath the near pectoral and axilla in Image 1 & Image 2!
    lat_wall_pts = [
        (8, 20), (20, 16), (25, 30), (23, 48), (15, 52), (9, 38),
    ]

    # 5. Target Muscle #1: Pectoralis Major (Lower Sternocostal-Abdominal & Upper Clavicular Heads, scale = 1.00 — Primary Mover!)
    pec_right_pts = [
        (-24, 0), (-13, -3), (-7, 2), (-7, 28), (-17, 30), (-25, 20),
    ]
    pec_left_lower_pts = [
        (-7, 8), (6, 9), (17, 15), (15, 29), (3, 33), (-7, 29),
    ]
    pec_left_upper_pts = [
        (-7, 2), (4, -3), (20, 3), (18, 16), (4, 12), (-7, 9),
    ]
    # Highlighted upper trapezius / sternocleidomastoid accent seen in Reference Image 2
    neck_trap_pts = [
        (0, -14), (8, -22), (14, -6), (4, 0),
    ]

    # 6. Volumetric 3/4 Male Head & Neck (anchored at neck base (-4, -8) inside TorsoGroup, looking forward-left)
    neck_pts = [(-12, -2), (-14, -22), (6, -22), (10, 0)]
    head_pts = [
        (-16, -18),  # chin bottom
        (-24, -22),  # sculpted chin tip facing left
        (-26, -30),  # lips / maxilla
        (-28, -37),  # nose bridge / tip facing left
        (-25, -46),  # brow ridge / forehead
        (-16, -54),  # anterior crown
        (-2, -55),   # cranial dome
        (9, -48),    # posterior cranium
        (11, -35),   # occiput
        (6, -23),    # mastoid / behind ear
        (-4, -18),   # jaw angle (mandible)
    ]
    hair_pts = [
        (-23, -47), (-15, -55), (-1, -56), (10, -49),
        (11, -35), (6, -25), (3, -34), (-2, -43), (-14, -46),
    ]
    hair_paint = (
        f'<Fill name="HairFill">{grad("HairGrad", -23, -56, 11, -25, "FF334155", "FF0F172A")}</Fill>'
        '<Stroke thickness="0.95" join="round" name="HairStroke"><SolidColor colorValue="FF090D16" name="HairStrokeCol"/></Stroke>'
    )

    out = [
        f'{ind}<Node x="{f(p0["mid_sh"][0])}" y="{f(p0["mid_sh"][1])}" '
        f'rotation="{f(p0["torso_rot"])}" name="TorsoAndHeadGroup" id="{torso_id}">',
    ]

    # A. Activated Chest Musculature (Pectoralis Major Lower/Upper + Lateral Chest Wall) — drawn in front of ribcage
    # Fan striations across the left and right pectorals
    out.append(stroke_shape(i2, "PecLeftStriation1", [(-4, 16), (6, 17), (14, 15)], 1.1, "667F1D1D", 0.3))
    out.append(stroke_shape(i2, "PecLeftStriation2", [(-4, 22), (5, 24), (13, 22)], 1.1, "667F1D1D", 0.3))
    out.append(stroke_shape(i2, "PecRightStriation1", [(-10, 15), (-18, 16), (-23, 14)], 1.0, "667F1D1D", 0.3))
    out.append(stroke_shape(i2, "SternalCleavage", [(-7, 2), (-7, 29)], 1.5, "99450A0A", 0.2))
    out.append(smooth_shape(i2, "PecLeftUpper", pec_left_upper_pts, muscle_paint("PecLeftUpper", scale=0.92, line=1.05, y0=-3, y1=18)))
    out.append(smooth_shape(i2, "PecLeftLower", pec_left_lower_pts, muscle_paint("PecLeftLower", scale=1.00, line=1.15, y0=8, y1=34)))
    out.append(smooth_shape(i2, "PecRight", pec_right_pts, muscle_paint("PecRight", scale=0.94, line=1.05, y0=-3, y1=30)))
    # Lateral Chest Wall (Pectoralis Minor / Serratus Anterior / Anterior Lat)
    out.append(stroke_shape(i2, "LatWallDigit1", [(11, 29), (20, 32)], 1.1, "667F1D1D", 0.3))
    out.append(stroke_shape(i2, "LatWallDigit2", [(11, 36), (21, 39)], 1.1, "667F1D1D", 0.3))
    out.append(smooth_shape(i2, "LateralChestWall", lat_wall_pts, muscle_paint("LatWall", scale=0.85, line=1.05, y0=16, y1=52)))

    # B. Sculpted 6-Pack Rectus Abdominis, Linea Alba & External Obliques
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "LineaAlba", [(-6, 30), (-5, 46), (-4, 62)], 1.3, ANATOMY_LINE, 0.3))
    out.append(stroke_shape(i2, "ObliqueLine1", [(9, 44), (17, 50)], 1.2, ANATOMY_LINE, 0.2))
    out.append(stroke_shape(i2, "ObliqueLine2", [(9, 51), (17, 57)], 1.2, ANATOMY_LINE, 0.2))

    # C. Pelvic Compression Shorts & Torso Base Silhouette
    out.append(stroke_shape(i2, "ShortsWaistband", [(-15, 60), (3, 56), (22, 53)], 2.2, "CC020617", 0.0))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill_outlined("PelvisShorts", 52, 86, SHORTS, line=1.15, stroke_col="CC020617")))
    out.append(stroke_shape(i2, "TorsoHi", [(-12, 34), (-10, 56)], 3.8, HIGHLIGHT, 3.8))
    out.append(stroke_shape(i2, "TorsoSh", [(16, 36), (16, 58)], 4.8, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i2, "TorsoSilhouette", torso_pts, skin_fill_outlined("Torso", -4, 70, SKIN, line=1.15)))

    # D. Volumetric 3/4 Head & Neck (with subtle counter-rotation so gaze remains forward-left)
    out.append(f'{i2}<Node x="0" y="0" rotation="{f(p0["head_counter_rot"])}" name="HeadGroup" id="{head_id}">')
    out.append(smooth_shape(i3, "HairCap", hair_pts, hair_paint))
    out.append(ellipse_shape(i3, "LeftEar", -1, -29, 5.2, 7.6, skin_fill_outlined("Ear", -4, 4, SKIN, line=0.85), rot_deg=10.0))
    # Subtle facial features (brow, eye, nose bridge, jaw crease) facing front-left
    out.append(stroke_shape(i3, "BrowLine", [(-24, -40), (-18, -40)], 1.3, "FF1E293B", 0.0))
    out.append(ellipse_shape(i3, "EyeDot", -20.5, -37.5, 2.2, 1.6, solid("Eye", "FF0F172A")))
    out.append(stroke_shape(i3, "MouthLine", [(-25, -27), (-20, -27)], 1.1, ANATOMY_LINE, 0.0))
    out.append(stroke_shape(i3, "JawCrease", [(-20, -20), (-7, -20), (-2, -25)], 1.4, CORE_SHADOW, 1.2))
    out.append(stroke_shape(i3, "HeadHi", [(-22, -45), (-12, -52), (-2, -51)], 2.8, HIGHLIGHT, 2.8))
    out.append(smooth_shape(i3, "HeadShape", head_pts, skin_fill_outlined("Head", -55, -18, SKIN, line=1.1)))
    out.append(smooth_shape(i3, "NeckTrapAccent", neck_trap_pts, muscle_paint("NeckTrap", scale=0.65, line=0.85, y0=-22, y1=0)))
    out.append(stroke_shape(i3, "SCMCrease", [(-4, -22), (-6, -2)], 1.3, ANATOMY_LINE, 0.2))
    out.append(smooth_shape(i3, "NeckShape", neck_pts, skin_fill_outlined("Neck", -22, 0, SKIN_FAR, line=1.0)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 4. Foreshortened Sibling-Node Arms (Anterior Deltoid & Triceps Brachii)
def arm_rig(prefix, far):
    """Sibling-node foreshortened arm (UpperArm SH->EL, Forearm EL->HAND, ShoulderCap at SH) with
    activated Anterior Deltoid (scale=0.92) & Triceps Brachii (scale=0.85) and stationary hand locked to the dip bar."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    sh_key = "far_sh" if far else "near_sh"
    el_key = "far_el" if far else "near_el"
    hand_pt = FAR_HAND if far else NEAR_HAND
    ua_len = UA_FAR_LEN if far else UA_NEAR_LEN
    fa_len = FA_FAR_LEN if far else FA_NEAR_LEN
    ua_ang_key = "ua_far_ang" if far else "ua_near_ang"
    ua_sc_key = "ua_far_sc" if far else "ua_near_sc"
    fa_ang_key = "fa_far_ang" if far else "fa_near_ang"
    fa_sc_key = "fa_far_sc" if far else "fa_near_sc"
    delt_ang_key = "delt_far_ang" if far else "delt_near_ang"
    m_scale = 0.88 if far else 1.00

    ua_id, fa_id, delt_id = nid(), nid(), nid()
    key_double(ua_id, 13, lambda p: p[sh_key][0])
    key_double(ua_id, 14, lambda p: p[sh_key][1])
    key_double(ua_id, 15, lambda p: p[ua_ang_key])
    key_double(ua_id, 16, lambda p: p[ua_sc_key])

    key_double(fa_id, 13, lambda p: p[el_key][0])
    key_double(fa_id, 14, lambda p: p[el_key][1])
    key_double(fa_id, 15, lambda p: p[fa_ang_key])
    key_double(fa_id, 16, lambda p: p[fa_sc_key])

    key_double(delt_id, 13, lambda p: p[sh_key][0])
    key_double(delt_id, 14, lambda p: p[sh_key][1])
    key_double(delt_id, 15, lambda p: p[delt_ang_key])
    p0 = POSES[0]

    # UpperArm along +X (0 -> ua_len):
    # Because SH -> EL rotates from +74 deg (vertical down at d=0.0) to -21 deg (angled up-right at d=1.0):
    # - Local -Y (y < 0) ALWAYS points to the posterior/upper extensor border (Triceps brachii!)
    # - Local +Y (y > 0) ALWAYS points to the anterior/lower flexor border (Biceps brachii!)
    ua_pts = [
        (-9, 0), (-6, -10.2), (8, -11.5), (ua_len * 0.55, -10.5), (ua_len - 4, -5.8),
        (ua_len + 1.5, 0), (ua_len - 4, 5.8), (ua_len * 0.55, 10.2), (8, 10.8), (-6, 9.8),
    ]
    # Target Muscle #4: Triceps brachii (lateral & long heads along local -Y extensor border, scale = 0.85)
    tri_pts = [
        (6, -1.2), (ua_len * 0.45, -1.5), (ua_len - 5, -2.0),
        (ua_len - 7, -9.2), (ua_len * 0.45, -11.0), (7, -9.8),
    ]
    biceps_pts = [
        (7, 1.2), (ua_len * 0.45, 1.5), (ua_len - 6, 1.8),
        (ua_len - 8, 7.8), (ua_len * 0.45, 9.5), (8, 8.8),
    ]

    # Target Muscle #3: Anterior deltoid (front shoulder cap on ShoulderCap, scale = 0.92)
    delt_pts = [
        (-10, 0), (-6, -11.5), (5, -12.2), (16, -8.5), (18, 0),
        (16, 9.2), (5, 12.5), (-6, 11.2),
    ]
    front_delt_pts = [
        (-6, 0.5), (5, 0.0), (16, 2.5), (15, 9.2), (5, 12.2), (-5, 10.2),
    ]

    fa_pts = [
        (-8, 0), (-4, -8.5), (fa_len * 0.35, -9.5), (fa_len - 5, -5.8),
        (fa_len + 4, 0), (fa_len - 5, 5.8), (fa_len * 0.35, 8.5), (-4, 7.8),
    ]

    # Stationary hand & finger knuckles locked directly at hand_pt = FAR_HAND or NEAR_HAND!
    hx, hy = hand_pt
    hand_pts = [
        (hx - 7.5, hy - 6.5), (hx + 6.5, hy - 6.5), (hx + 8.5, hy + 1.5),
        (hx + 5.5, hy + 6.5), (hx - 6.5, hy + 6.0), (hx - 8.5, hy + 0.5),
    ]

    return "\n".join([
        f'{ind}<Node name="{prefix}ArmGroup">',
        # 1. Stationary Hand & Pronated Knuckles Locked onto the Parallel Dip Bar (zero drift!)
        stroke_shape(i2, f"{prefix}KnuckleLine1", [(hx - 3, hy - 3), (hx - 3, hy + 4)], 1.0, ANATOMY_LINE, 0.0),
        stroke_shape(i2, f"{prefix}KnuckleLine2", [(hx + 1, hy - 3), (hx + 1, hy + 4)], 1.0, ANATOMY_LINE, 0.0),
        smooth_shape(i2, f"{prefix}LockedHand", hand_pts, skin_fill_outlined(prefix + "Hand", hy - 7, hy + 7, skin, line=1.15)),

        # 2. Forearm (EL -> HAND, drawn in front of the elbow joint)
        f'{i2}<Node x="{f(p0[el_key][0])}" y="{f(p0[el_key][1])}" '
        f'rotation="{f(p0[fa_ang_key])}" scaleX="{f(p0[fa_sc_key])}" name="{prefix}Forearm" id="{fa_id}">',
        stroke_shape(i3, f"{prefix}BrachioradialisLine", [(5, -2.2), (fa_len * 0.62, -1.8)], 1.25, ANATOMY_LINE, 0.2),
        stroke_shape(i3, f"{prefix}ExtensorLine", [(8, -5.2), (fa_len * 0.58, -4.0)], 1.1, ANATOMY_LINE, 0.2),
        stroke_shape(i3, f"{prefix}ForearmHi", [(5, -4.5), (fa_len - 8, -3.2)], 2.6, HIGHLIGHT, 2.5),
        stroke_shape(i3, f"{prefix}ForearmSh", [(5, 4.8), (fa_len - 8, 3.5)], 3.2, CORE_SHADOW, 3.0),
        smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill_outlined(prefix + "Forearm", -9, 9, skin, line=1.15)),
        f"{i2}</Node>",

        # 3. Dedicated Shoulder Cap Node (Anterior Deltoid + Sculpted Deltoid Base)
        f'{i2}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" '
        f'rotation="{f(p0[delt_ang_key])}" name="{prefix}ShoulderCap" id="{delt_id}">',
        stroke_shape(i3, f"{prefix}AntDeltFiber", [(0, 6.0), (12, 6.5)], 1.1, "667F1D1D", 0.3),
        smooth_shape(i3, f"{prefix}AnteriorDeltoid", front_delt_pts, muscle_paint(prefix + "FrontDelt", scale=0.92 * m_scale, line=1.05, y0=0, y1=13)),
        stroke_shape(i3, f"{prefix}LatDeltCrease", [(-2, -5.5), (11, -4.5)], 1.15, ANATOMY_LINE, 0.2),
         stroke_shape(i3, f"{prefix}LatDeltHi", [(-2, -8.5), (10, -7.5)], 2.4, HIGHLIGHT, 2.4),
        smooth_shape(i3, f"{prefix}DeltoidBase", delt_pts, skin_fill_outlined(prefix + "Deltoid", -12, 12, skin, line=1.1)),
        f"{i2}</Node>",

        # 4. Upper Arm (SH -> EL) with Triceps Brachii (upper-extensor -Y) & Biceps Brachii (lower-flexor +Y)
        f'{i2}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" '
        f'rotation="{f(p0[ua_ang_key])}" scaleX="{f(p0[ua_sc_key])}" name="{prefix}UpperArm" id="{ua_id}">',
        stroke_shape(i3, f"{prefix}UpperArmHi", [(6, 4.5), (ua_len - 8, 3.8)], 2.4, HIGHLIGHT, 2.5),
        smooth_shape(i3, f"{prefix}BicepsBelly", biceps_pts, skin_fill_outlined(prefix + "Biceps", 1, 10, skin, line=0.95)),
        stroke_shape(i3, f"{prefix}TricepsHorseshoe", [(8, -6.0), (ua_len - 9, -5.5)], 1.2, "667F1D1D", 0.3),
        smooth_shape(i3, f"{prefix}TricepsBrachii", tri_pts, muscle_paint(prefix + "Triceps", scale=0.85 * m_scale, line=1.05, y0=-12, y1=-1)),
        smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill_outlined(prefix + "UpperArm", -12, 12, skin, line=1.15)),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 5. Scene Assembly (RML First Child = Topmost Layer)
def build_rml():
    global _id
    _id = 0
    KEYED.clear()

    dip_back_xml, dip_front_left_xml = dip_station_layers()
    far_leg_xml = leg_rig("FarRight", far=True)
    near_leg_xml = leg_rig("NearLeft", far=False)
    torso_head_xml = torso_and_head_rig()
    far_arm_xml = arm_rig("FarRight", far=True)
    near_arm_xml = arm_rig("NearLeft", far=False)

    grouped = {}
    for oid, kxml in KEYED:
        grouped.setdefault(oid, []).append(kxml)
    keyed_objects_xml = "\n".join(
        f'        <KeyedObject objectId="{oid}">\n' + "\n".join(props) + "\n        </KeyedObject>"
        for oid, props in grouped.items()
    )

    # Note: In Rive RML, FIRST child of Artboard is drawn IN FRONT (topmost); LAST child is drawn BEHIND (bottommost)!
    # Layer order from front to back:
    #   1. NearLeftArm (grips NEAR_HAND=(348, 166) in front of the near handle & torso)
    #   2. DipStationFrontLeft (near forearm pad & upright pass in front of the right thigh/hip on the left, behind NearLeftArm!)
    #   3. NearLeftLeg (bent knee with foot held behind the body)
    #   4. TorsoAndHeadGroup (forward-leaning torso, glowing Pectoralis Major/Minor, 6-pack abs, volumetric 3/4 head)
    #   5. FarRightLeg (behind near leg)
    #   6. FarRightArm (behind torso, grips FAR_HAND=(284, 162))
    #   7. DipStationBack (far upright, backrest pad, far forearm pad, far handle, base runner)
    #   8. Studio Floor & Ambient Backdrop
    return f"""<Rive version="7.3">
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="Dips" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Left) Arm Locked to Near Dip Handle (348, 166) -->
{near_arm_xml}

        <!-- 2. Mid-Foreground Left: Dip Station Near Upright, Near Forearm Pad & Near Handle -->
{dip_front_left_xml}

        <!-- 3. Midground: Near (Left) Bent Leg ("Feet Behind the Body") -->
{near_leg_xml}

        <!-- 4. Midground: Forward-Leaning Torso, Pectoralis Major/Minor, 6-Pack Abs & 3/4 Head -->
{torso_head_xml}

        <!-- 5. Mid-Background: Far (Right) Bent Leg -->
{far_leg_xml}

        <!-- 6. Mid-Background: Far (Right) Arm Locked to Far Dip Handle (284, 162) -->
{far_arm_xml}

        <!-- 7. Background: Dip Station Far Upright, Backrest Pad, Far Forearm Pad & Far Base Runner -->
{dip_back_xml}

        <!-- 8. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="268" y="{f(FLOOR - 4.0)}" name="FloorShadow">
            <Ellipse width="290" height="22" name="ShadowEllipse"/>
            <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="145" endY="0" name="ShadowGrad">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="Dips" id="0:60">
{keyed_objects_xml}
        </LinearAnimation>
    </Artboard>
</Rive>
"""


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
    riv_out = HERE / "dips.riv"
    riv_out.write_bytes(riv_bytes)

    repo = HERE.parent.parent
    riv_dest = repo / "assets/animations/dips.riv"
    thumb_dest = repo / "assets/animations/thumbnails/dips.png"
    riv_dest.write_bytes(riv_bytes)

    # Remove legacy movekit file if present
    legacy_mk = repo / "assets/animations/dips.movekit"
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
