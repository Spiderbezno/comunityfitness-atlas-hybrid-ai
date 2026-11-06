#!/usr/bin/env python3
"""Procedural generator for `rive_animations/thruster/scene.rml`.

Builds a 640x360, 60fps, 180-frame (3.0s) loopable Rive 7.3 animation of a
Barbell Thruster (Front Squat into Overhead Press) in a 3/4 front-left oblique view:
  - Phase 1 (r: 0.0 -> 0.52): Explosive Front Squat drive out of the bottom hole
    with the loaded Olympic barbell racked across the anterior deltoids/clavicles
    and elbows angled forward-up.
  - Phase 2 (r: 0.52 -> 1.0): Seamless transfer of momentum into a full standing
    Overhead Press lockout directly over mid-foot.
  - Primary muscles (pulsing orange #FFF97316 -> crimson #FFF43F5E):
      1. Quadriceps femoris (Rectus femoris, Vastus lateralis, Vastus medialis)
      2. Gluteus maximus
      3. Anterior & Lateral Deltoids (Deltoideus anterior & lateralis)
      4. Triceps brachii (Caput laterale & longum)

Run:
    python3 rive_animations/thruster/gen_thruster.py --publish
"""

import math
import pathlib
import struct
import sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "scene.rml"
REPO_ROOT = HERE.parent.parent

W, H = 640, 360
FPS = 60
DURATION = 180
STEP = 2
FLOOR = 300.0

# Stationary ankle anchors on FLOOR = 300.0 (3/4 front-left athletic stance)
ANKLE_NEAR = (324.0, 290.0)
ANKLE_FAR = (298.0, 281.0)

# Canonical Limb Rest Lengths (proportioned so overhead barbell lockout stays cleanly inside y >= 14)
THIGH_NEAR_LEN = 62.0
SHIN_NEAR_LEN = 62.0
THIGH_FAR_LEN = 60.0
SHIN_FAR_LEN = 60.0
UPPER_ARM_LEN = 36.0
FOREARM_LEN = 34.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
PLATE_DARK = ("FF334155", "FF182232", "FF090D16")
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


EASE_DRIVE = cubic_bezier(0.32, 0.0, 0.20, 1.0)
EASE_LOWER = cubic_bezier(0.40, 0.0, 0.28, 1.0)


def thruster_progress(frame):
    """Returns Barbell Thruster progress r in [0.0, 1.0] across 180 frames:
    - 0..16:    Bottom Front Squat hold (r = 0.0)
    - 16..76:   Explosive Front Squat drive + Overhead Press lockout (r: 0.0 -> 1.0)
    - 76..96:   Top Overhead Lockout hold (r = 1.0)
    - 96..162:  Controlled eccentric return to Front Rack & Squat bottom (r: 1.0 -> 0.0)
    - 162..180: Bottom Front Squat hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 16:
        return 0.0
    if fr <= 76:
        return EASE_DRIVE((fr - 16) / 60.0)
    if fr <= 96:
        return 1.0
    if fr <= 162:
        return 1.0 - EASE_LOWER((fr - 96) / 66.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def clamp01(v):
    return max(0.0, min(1.0, v))


def solve_ik_left(hip, ankle, l1, l2):
    """Exact 2-bone IK from hip -> knee -> ankle for a leftward-facing (-X) 3/4 athlete."""
    dx = ankle[0] - hip[0]
    dy = ankle[1] - hip[1]
    d = max(1.0, min(l1 + l2 - 0.2, math.hypot(dx, dy)))
    base_ang = math.atan2(dy, dx)
    cos_a = max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2.0 * l1 * d)))
    thigh_ang = base_ang + math.acos(cos_a)
    knee = (hip[0] + l1 * math.cos(thigh_ang), hip[1] + l1 * math.sin(thigh_ang))
    shin_ang = math.atan2(ankle[1] - knee[1], ankle[0] - knee[0])
    return thigh_ang, knee, shin_ang


def seg_xform(p0, p1, base_len):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ang = math.atan2(dy, dx)
    sc = max(0.55, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute 3/4 Barbell Thruster joint transforms at progress r in [0.0, 1.0]:
    - squat_depth (1.0 at r=0.0 -> 0.0 at r>=0.56): Front squat leg extension
    - press_frac  (0.0 at r<=0.38 -> 1.0 at r=1.0): Overhead press lockout
    """
    squat_depth = 1.0 - clamp01(r / 0.56) ** 0.90
    press_frac = clamp01((r - 0.36) / 0.64) ** 0.92

    # 1. Hips: Deep below-parallel Front Squat at r=0.0 -> Tall locked standing at r>=0.56
    hip_near = (lerp(328.0, 352.0, squat_depth), lerp(167.2, 224.0, squat_depth))
    hip_far = (lerp(306.0, 328.0, squat_depth), lerp(162.5, 214.0, squat_depth))

    # 2. Exact 2-bone IK for Near (Left) and Far (Right) Legs
    thigh_near_ang, knee_near, shin_near_ang = solve_ik_left(
        hip_near, ANKLE_NEAR, THIGH_NEAR_LEN, SHIN_NEAR_LEN
    )
    thigh_far_ang, knee_far, shin_far_ang = solve_ik_left(
        hip_far, ANKLE_FAR, THIGH_FAR_LEN, SHIN_FAR_LEN
    )

    # 3. Upright Front-Squat Torso:
    #    Front squats keep a prouder, more upright torso (-13 deg at bottom -> -1.5 deg at lockout)
    torso_lean = math.radians(lerp(-1.5, -13.5, squat_depth))
    head_counter_rot = -torso_lean * 0.85

    cs, sn = math.cos(torso_lean), math.sin(torso_lean)

    def torso_world(lx, ly):
        return (hip_near[0] + lx * cs - ly * sn, hip_near[1] + lx * sn + ly * cs)

    sh_near = torso_world(7.0, -66.0)
    sh_far = torso_world(-29.0, -68.0)

    # 4. Olympic Barbell Trajectory:
    #    At press_frac=0.0 (Front Rack): Racked on anterior clavicles in front-left of neck (-18, -68)
    #    At press_frac=1.0 (Overhead Lockout): Directly above crown/mid-foot at y=39 (plates stay inside y>=14)
    rack_bar = torso_world(-18.0, -68.0)
    lockout_bar = (sh_near[0] - 19.0, sh_near[1] - 62.0)  # ~(316, 39) well above head crown (y~54)
    bar_center = (
        lerp(rack_bar[0], lockout_bar[0], press_frac),
        lerp(rack_bar[1], lockout_bar[1], press_frac),
    )

    # 5. Hands locked to barbell shaft & Elbows transitioning from Front-Rack to Overhead Lockout
    hand_near = (bar_center[0] + 36.0, bar_center[1] + 5.0)
    hand_far = (bar_center[0] - 34.0, bar_center[1] - 4.8)

    # Front rack: elbows driven forward-left and slightly down from shoulders;
    # Overhead lockout: elbows driven straight up between shoulders and overhead hands!
    elb_near_rack = (sh_near[0] - 8.0, sh_near[1] + 19.0)
    elb_near_lock = (lerp(sh_near[0], hand_near[0], 0.52) + 5.0, lerp(sh_near[1], hand_near[1], 0.52))
    elbow_near = (
        lerp(elb_near_rack[0], elb_near_lock[0], press_frac),
        lerp(elb_near_rack[1], elb_near_lock[1], press_frac),
    )

    elb_far_rack = (sh_far[0] - 13.0, sh_far[1] + 16.0)
    elb_far_lock = (lerp(sh_far[0], hand_far[0], 0.52) - 5.0, lerp(sh_far[1], hand_far[1], 0.52))
    elbow_far = (
        lerp(elb_far_rack[0], elb_far_lock[0], press_frac),
        lerp(elb_far_rack[1], elb_far_lock[1], press_frac),
    )

    ua_near_ang, ua_near_sc = seg_xform(sh_near, elbow_near, UPPER_ARM_LEN)
    fa_near_ang, fa_near_sc = seg_xform(elbow_near, hand_near, FOREARM_LEN)
    ua_far_ang, ua_far_sc = seg_xform(sh_far, elbow_far, UPPER_ARM_LEN)
    fa_far_ang, fa_far_sc = seg_xform(elbow_far, hand_far, FOREARM_LEN)

    shd_sx = lerp(1.04, 1.22, squat_depth)

    return {
        "r": r,
        "squat_depth": squat_depth,
        "press_frac": press_frac,
        "hip_near": hip_near,
        "hip_far": hip_far,
        "knee_near": knee_near,
        "knee_far": knee_far,
        "thigh_near_ang": thigh_near_ang,
        "shin_near_ang": shin_near_ang,
        "thigh_far_ang": thigh_far_ang,
        "shin_far_ang": shin_far_ang,
        "torso_lean": torso_lean,
        "head_counter_rot": head_counter_rot,
        "sh_near": sh_near,
        "sh_far": sh_far,
        "bar_center": bar_center,
        "hand_near": hand_near,
        "hand_far": hand_far,
        "elbow_near": elbow_near,
        "elbow_far": elbow_far,
        "ua_near_ang": ua_near_ang,
        "ua_near_sc": ua_near_sc,
        "fa_near_ang": fa_near_ang,
        "fa_near_sc": fa_near_sc,
        "ua_far_ang": ua_far_ang,
        "ua_far_sc": ua_far_sc,
        "fa_far_ang": fa_far_ang,
        "fa_far_sc": fa_far_sc,
        "shd_sx": shd_sx,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(thruster_progress(fr)) for fr in FRAMES}

# Unwrap all angle channels to guarantee smooth continuous rotation with zero 2*pi flips
_ANGLE_KEYS = (
    "thigh_near_ang",
    "shin_near_ang",
    "thigh_far_ang",
    "shin_far_ang",
    "torso_lean",
    "head_counter_rot",
    "ua_near_ang",
    "fa_near_ang",
    "ua_far_ang",
    "fa_far_ang",
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


def skin_fill(name, y0, y1, tones=SKIN, x0=0, x1=0):
    return (
        f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *tones, x0=x0, x1=x1)}</Fill>'
        f'<Stroke thickness="0.95" join="round" name="{name}Outline">'
        f'<SolidColor colorValue="380F172A" name="{name}OutlineCol"/></Stroke>'
    )


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
    fid, lid = nid(), nid()
    key_color(fid, 37, lambda p: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, fn_t(p)))
    key_color(lid, 37, lambda p: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, fn_t(p)))
    t0 = fn_t(POSES[0])
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- 1. 3D Olympic Barbell & Pressing Arms (Deltoids + Triceps)
def build_barbell_and_arms():
    """Returns (near_bar_and_arm_xml, far_bar_and_arm_xml) with glowing Anterior/Lateral Deltoids
    and Triceps Brachii driving the barbell from the Front Rack into Overhead Lockout."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    p0 = POSES[0]

    near_bar_id, far_bar_id, near_shaft_id = nid(), nid(), nid()
    for bid in (near_bar_id, far_bar_id, near_shaft_id):
        key_double(bid, 13, lambda p: p["bar_center"][0])
        key_double(bid, 14, lambda p: p["bar_center"][1])

    ua_near_id, fa_near_id = nid(), nid()
    key_double(ua_near_id, 13, lambda p: p["sh_near"][0])
    key_double(ua_near_id, 14, lambda p: p["sh_near"][1])
    key_double(ua_near_id, 15, lambda p: p["ua_near_ang"])
    key_double(ua_near_id, 16, lambda p: p["ua_near_sc"])

    key_double(fa_near_id, 13, lambda p: p["elbow_near"][0])
    key_double(fa_near_id, 14, lambda p: p["elbow_near"][1])
    key_double(fa_near_id, 15, lambda p: p["fa_near_ang"])
    key_double(fa_near_id, 16, lambda p: p["fa_near_sc"])

    ua_far_id, fa_far_id = nid(), nid()
    key_double(ua_far_id, 13, lambda p: p["sh_far"][0])
    key_double(ua_far_id, 14, lambda p: p["sh_far"][1])
    key_double(ua_far_id, 15, lambda p: p["ua_far_ang"])
    key_double(ua_far_id, 16, lambda p: p["ua_far_sc"])

    key_double(fa_far_id, 13, lambda p: p["elbow_far"][0])
    key_double(fa_far_id, 14, lambda p: p["elbow_far"][1])
    key_double(fa_far_id, 15, lambda p: p["fa_far_ang"])
    key_double(fa_far_id, 16, lambda p: p["fa_far_sc"])

    # Deltoids & Triceps stay warm supporting the front rack (0.48) and blaze at overhead lockout (1.0)
    def delt_t(p):
        return 0.48 + 0.52 * (p["r"] ** 0.72)

    def triceps_t(p):
        return 0.42 + 0.58 * (p["press_frac"] ** 0.75)

    prot = 10.0
    near_plate_face = (
        f'<Fill name="NearPlateFaceFill">{grad3("NearPlateFaceGrad", -34, 34, *PLATE_DARK, x0=-20, x1=20)}</Fill>'
        '<Stroke thickness="1.35" join="round" name="NearPlateRimStroke"><SolidColor colorValue="FF475569" name="NearPlateRimCol"/></Stroke>'
    )
    near_plate_rim = f'<Fill name="NearPlateBackFill">{grad("NearPlateBackGrad", -22, -34, 22, 34, "FF0F172A", "FF020617")}</Fill>'
    near_ring_paint = (
        '<Fill name="NearRingFill"><SolidColor colorValue="FF111827" name="NearRingCol"/></Fill>'
        '<Stroke thickness="1.15" join="round" name="NearRingStroke"><SolidColor colorValue="FF334155" name="NearRingStrokeCol"/></Stroke>'
    )
    hub_paint = (
        f'<Fill name="NearHubFill">{grad3("NearHubGrad", -8, 8, "FFE2E8F0", "FF64748B", "FF1E293B")}</Fill>'
        '<Stroke thickness="1.0" join="round" name="NearHubStroke"><SolidColor colorValue="FFCBD5E1" name="NearHubStrokeCol"/></Stroke>'
    )
    sleeve_fill = f'<Fill name="NearSleeveFill">{grad3("NearSleeveGrad", 5, 16, "FFCBD5E1", "FF64748B", "FF0F172A")}</Fill>'
    shaft_fill = f'<Fill name="ShaftFill">{grad3("ShaftGrad", -8, 10, "FFE2E8F0", "FF64748B", "FF1E293B")}</Fill>'

    near_sleeve_pts = [(66.0, 6.8), (94.0, 10.8), (93.2, 16.0), (65.2, 12.0)]
    full_front_shaft_pts = [(-48.0, -9.2), (52.0, 4.8), (51.2, 9.8), (-48.8, -4.2)]

    ua_pts = [
        (-8.0, -9.2), (10.0, -10.5), (28.0, -8.8), (42.0, -5.8),
        (44.0, 0.0), (41.0, 6.2), (26.0, 9.2), (8.0, 9.8), (-8.0, 8.2),
    ]
    delt_pts = [
        (-13.0, 0.0), (-9.0, -11.5), (4.0, -12.8), (15.0, -8.2),
        (18.0, 0.0), (14.0, 8.5), (3.0, 11.5), (-9.0, 9.5),
    ]
    ant_delt_pts = [
        (-9.0, -1.5), (-4.0, -11.0), (8.0, -10.5), (16.0, -5.0), (12.0, 0.5), (0.0, 0.5),
    ]
    lat_delt_pts = [
        (-11.0, 0.0), (2.0, -1.0), (14.5, 0.5), (14.0, 7.2), (2.0, 10.2), (-9.0, 7.5),
    ]
    triceps_pts = [
        (10.0, 1.5), (26.0, 1.2), (38.0, 2.5), (36.0, 7.8), (22.0, 8.8), (10.0, 7.2),
    ]
    fa_pts = [
        (-5.0, -7.2), (12.0, -8.2), (28.0, -5.8), (39.0, -4.5),
        (41.0, 0.0), (38.0, 4.8), (26.0, 6.8), (10.0, 7.5), (-5.0, 6.5),
    ]
    fist_pts = [
        (33.0, -5.5), (42.0, -5.2), (44.0, 0.0), (41.5, 5.5), (33.0, 5.2),
    ]

    # --- Foreground: Near Plate Stack, Near Arm (Deltoids + Triceps) & Front-Rack Bar Shaft ---
    near_xml = "\n".join([
        f'{ind}<Node name="ForegroundNearBarbellAndArm">',
        # 1. Near-Right Stepped Plate Stack
        f'{i2}<Node x="{f(p0["bar_center"][0])}" y="{f(p0["bar_center"][1])}" name="NearBarbellStack" id="{near_bar_id}">',
        ellipse_shape(i3, "NearSleeveEndCap", 93.6, 13.4, 4.2, 6.5, solid("NearCap", "FF0F172A"), rot_deg=prot),
        ellipse_shape(i3, "NearSleeveEndRim", 93.6, 13.4, 5.5, 7.8, solid("NearCapRim", "FF94A3B8"), rot_deg=prot),
        stroke_shape(i3, "NearSleeveHi", [(67.0, 8.2), (80.0, 10.0), (92.0, 11.8)], 1.4, "CCE2E8F0", 0.4),
        poly_shape(i3, "NearOuterSleeve", near_sleeve_pts, sleeve_fill, radius=1.0),
        ellipse_shape(i3, "NearOuterCollar", 67.5, 9.6, 9.0, 14.5, hub_paint, rot_deg=prot),
        ellipse_shape(i3, "NearPlate3Face", 63.5, 9.0, 26.0, 42.0, near_plate_face, rot_deg=prot),
        ellipse_shape(i3, "NearPlate3Rim", 60.5, 8.6, 26.0, 42.0, near_plate_rim, rot_deg=prot),
        ellipse_shape(i3, "NearPlate2Inner", 58.0, 8.2, 24.0, 39.0, near_ring_paint, rot_deg=prot),
        ellipse_shape(i3, "NearPlate2Face", 58.0, 8.2, 34.0, 54.0, near_plate_face, rot_deg=prot),
        ellipse_shape(i3, "NearPlate2Rim", 54.5, 7.7, 34.0, 54.0, near_plate_rim, rot_deg=prot),
        ellipse_shape(i3, "NearPlate1Inner", 52.0, 7.4, 30.0, 48.0, near_ring_paint, rot_deg=prot),
        ellipse_shape(i3, "NearPlate1Face", 52.0, 7.4, 42.0, 66.0, near_plate_face, rot_deg=prot),
        ellipse_shape(i3, "NearPlate1Rim", 48.0, 6.8, 42.0, 66.0, near_plate_rim, rot_deg=prot),
        ellipse_shape(i3, "NearInnerCollar", 45.5, 6.4, 7.5, 11.8, hub_paint, rot_deg=prot),
        f"{i2}</Node>",

        # 2. Near Forearm & Gripping Fist on Bar
        f'{i2}<Node x="{f(p0["elbow_near"][0])}" y="{f(p0["elbow_near"][1])}" '
        f'rotation="{f(p0["fa_near_ang"])}" scaleX="{f(p0["fa_near_sc"])}" name="NearForearm" id="{fa_near_id}">',
        stroke_shape(i3, "NearKnuckle1", [(35.0, -2.2), (41.0, -2.0)], 0.95, SOFT_SHADOW, 0.0),
        stroke_shape(i3, "NearKnuckle2", [(35.0, 1.2), (41.0, 1.4)], 0.95, SOFT_SHADOW, 0.0),
        smooth_shape(i3, "NearGrippingFist", fist_pts, skin_fill("NearFist", -6, 6, SKIN)),
        stroke_shape(i3, "NearForearmHi", [(6.0, -3.5), (26.0, -3.0)], 2.4, HIGHLIGHT, 2.5),
        stroke_shape(i3, "NearForearmSh", [(6.0, 3.8), (26.0, 3.2)], 3.2, CORE_SHADOW, 3.0),
        smooth_shape(i3, "NearForearmShape", fa_pts, skin_fill("NearFA", -8, 8, SKIN)),
        f"{i2}</Node>",

        # 3. Near Upper Arm with Glowing Anterior/Lateral Deltoids & Triceps Brachii
        f'{i2}<Node x="{f(p0["sh_near"][0])}" y="{f(p0["sh_near"][1])}" '
        f'rotation="{f(p0["ua_near_ang"])}" scaleX="{f(p0["ua_near_sc"])}" name="NearUpperArm" id="{ua_near_id}">',
        stroke_shape(i3, "NearDeltHi", [(-2.0, -6.0), (8.0, -4.5)], 2.0, "66FFFFFF", 2.0),
        stroke_shape(i3, "NearDeltSeptum", [(-5.0, -0.5), (6.0, -0.5), (14.0, 0.0)], 1.05, "807F1D1D", 0.4),
        smooth_shape(i3, "NearAnteriorDeltoid", ant_delt_pts, muscle_paint_fn("NearAntDelt", delt_t, 0.95)),
        smooth_shape(i3, "NearLateralDeltoid", lat_delt_pts, muscle_paint_fn("NearLatDelt", delt_t, 0.95)),
        smooth_shape(i3, "NearDeltoidCap", delt_pts, skin_fill("NearDelt", -12, 12, SKIN)),
        smooth_shape(i3, "NearTricepsBrachii", triceps_pts, muscle_paint_fn("NearTriceps", triceps_t, 0.95)),
        stroke_shape(i3, "NearUpperArmHi", [(10.0, -5.0), (30.0, -4.5)], 2.4, HIGHLIGHT, 2.4),
        stroke_shape(i3, "NearUpperArmSh", [(10.0, 5.5), (30.0, 5.0)], 3.2, CORE_SHADOW, 3.0),
        smooth_shape(i3, "NearUpperArmShape", ua_pts, skin_fill("NearUA", -10, 10, SKIN)),
        f"{i2}</Node>",

        # 4. Olympic Barbell Shaft across the Front Rack / Overhead Lockout
        f'{i2}<Node x="{f(p0["bar_center"][0])}" y="{f(p0["bar_center"][1])}" name="FrontBarShaftNode" id="{near_shaft_id}">',
        stroke_shape(i3, "FrontShaftHi", [(-46.0, -7.8), (2.0, -1.0), (50.0, 5.8)], 1.4, "CCE2E8F0", 0.4),
        poly_shape(i3, "FrontBarShaft", full_front_shaft_pts, shaft_fill, radius=1.0),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])

    # --- Background: Far Arm (Deltoids + Triceps) & Far Multi-Plate Stack ---
    far_plate_face = (
        f'<Fill name="FarPlateFaceFill">{grad3("FarPlateFaceGrad", -28, 28, "FF263244", "FF111827", "FF060911", x0=-18, x1=18)}</Fill>'
        '<Stroke thickness="1.2" join="round" name="FarPlateRimStroke"><SolidColor colorValue="FF334155" name="FarPlateRimCol"/></Stroke>'
    )
    far_plate_rim = f'<Fill name="FarPlateBackFill">{grad("FarPlateBackGrad", -18, -28, 18, 28, "FF090D16", "FF020617")}</Fill>'

    far_xml = "\n".join([
        f'{ind}<Node name="BackgroundFarBarbellAndArm">',
        # 1. Far Forearm & Hand Gripping Bar
        f'{i2}<Node x="{f(p0["elbow_far"][0])}" y="{f(p0["elbow_far"][1])}" '
        f'rotation="{f(p0["fa_far_ang"])}" scaleX="{f(p0["fa_far_sc"])}" name="FarForearm" id="{fa_far_id}">',
        smooth_shape(i3, "FarGrippingFist", fist_pts, skin_fill("FarFist", -6, 6, SKIN_FAR)),
        smooth_shape(i3, "FarForearmShape", fa_pts, skin_fill("FarFA", -8, 8, SKIN_FAR)),
        f"{i2}</Node>",

        # 2. Far Upper Arm with Glowing Deltoid & Triceps
        f'{i2}<Node x="{f(p0["sh_far"][0])}" y="{f(p0["sh_far"][1])}" '
        f'rotation="{f(p0["ua_far_ang"])}" scaleX="{f(p0["ua_far_sc"])}" name="FarUpperArm" id="{ua_far_id}">',
        smooth_shape(i3, "FarDeltoidGlow", ant_delt_pts, muscle_paint_fn("FarDeltGlow", lambda p: delt_t(p) * 0.88, 0.9)),
        smooth_shape(i3, "FarDeltoidCap", delt_pts, skin_fill("FarDelt", -12, 12, SKIN_FAR)),
        smooth_shape(i3, "FarTricepsGlow", triceps_pts, muscle_paint_fn("FarTriGlow", lambda p: triceps_t(p) * 0.88, 0.9)),
        smooth_shape(i3, "FarUpperArmShape", ua_pts, skin_fill("FarUA", -10, 10, SKIN_FAR)),
        f"{i2}</Node>",

        # 3. Far Stepped Multi-Plate Stack (-48, -6.8)
        f'{i2}<Node x="{f(p0["bar_center"][0])}" y="{f(p0["bar_center"][1])}" name="FarBarbellStack" id="{far_bar_id}">',
        ellipse_shape(i3, "FarInnerCollar", -44.0, -6.2, 6.8, 10.8, hub_paint, rot_deg=prot),
        ellipse_shape(i3, "FarPlate1Inner", -49.0, -6.9, 26.0, 42.0, near_ring_paint, rot_deg=prot),
        ellipse_shape(i3, "FarPlate1Face", -49.0, -6.9, 36.0, 56.0, far_plate_face, rot_deg=prot),
        ellipse_shape(i3, "FarPlate1Rim", -52.5, -7.4, 36.0, 56.0, far_plate_rim, rot_deg=prot),
        ellipse_shape(i3, "FarPlate2Face", -55.0, -7.8, 28.0, 44.0, far_plate_face, rot_deg=prot),
        ellipse_shape(i3, "FarPlate2Rim", -58.0, -8.2, 28.0, 44.0, far_plate_rim, rot_deg=prot),
        ellipse_shape(i3, "FarPlate3Face", -60.5, -8.5, 22.0, 34.0, far_plate_face, rot_deg=prot),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])

    return near_xml, far_xml


# ---------------------------------------------------------------- 2. Thruster Leg Builder (Quadriceps & Gluteus Maximus)
def build_thruster_leg(prefix, is_far=False):
    """Builds the Near (Left) or Far (Right) Leg in 3/4 view with glowing:
      1. Quadriceps femoris (Rectus femoris, Vastus lateralis, Vastus medialis teardrop)
      2. Gluteus maximus"""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if is_far else SKIN
    shorts = SHORTS_FAR if is_far else SHORTS
    hip_key = "hip_far" if is_far else "hip_near"
    knee_key = "knee_far" if is_far else "knee_near"
    th_ang_key = "thigh_far_ang" if is_far else "thigh_near_ang"
    sh_ang_key = "shin_far_ang" if is_far else "shin_near_ang"
    ax, ay = ANKLE_FAR if is_far else ANKLE_NEAR
    m_scale = 0.88 if is_far else 1.0

    thigh_id, shin_id = nid(), nid()
    key_double(thigh_id, 13, lambda p: p[hip_key][0])
    key_double(thigh_id, 14, lambda p: p[hip_key][1])
    key_double(thigh_id, 15, lambda p: p[th_ang_key])

    key_double(shin_id, 13, lambda p: p[knee_key][0])
    key_double(shin_id, 14, lambda p: p[knee_key][1])
    key_double(shin_id, 15, lambda p: p[sh_ang_key])
    p0 = POSES[0]

    # Quads & Glutes stay strongly active throughout the Front Squat & Overhead Lockout
    def quad_t(p):
        return (0.52 + 0.48 * max(p["squat_depth"], p["press_frac"] * 0.85)) * m_scale

    def glute_t(p):
        return (0.50 + 0.50 * max(p["squat_depth"], p["press_frac"] * 0.90)) * m_scale

    thigh_pts = [
        (-13.0, 10.5), (9.0, 16.5), (32.0, 16.8), (52.0, 12.8),
        (64.0, 5.2), (64.0, -5.0), (52.0, -10.5), (30.0, -14.2),
        (9.0, -16.0), (-13.0, -12.0),
    ]
    shorts_cuff_pts = [
        (-12.0, 9.5), (15.5, 15.8), (16.5, -15.5), (-12.5, -12.0),
    ]
    glute_pts = [
        (-13.5, -1.2), (12.0, -3.0), (14.0, -15.5), (-4.0, -16.2), (-13.5, -10.5),
    ]
    rectus_femoris_pts = [
        (8.5, 15.8), (29.0, 16.2), (46.0, 13.5), (55.0, 9.5),
        (52.0, 5.5), (35.0, 7.0), (17.0, 7.6), (7.0, 8.2),
    ]
    vastus_lat_pts = [
        (10.0, 7.4), (29.0, 6.8), (46.0, 5.8), (53.0, 3.8),
        (49.0, -0.8), (30.0, -1.2), (12.0, -0.5),
    ]
    vastus_med_pts = [
        (36.0, 13.2), (50.0, 11.8), (57.5, 6.8), (51.5, 2.0), (38.0, 4.6),
    ]

    shin_pts = [
        (-7.0, 6.2), (15.0, 6.2), (40.0, 5.2), (60.0, 3.8),
        (64.0, 0.0), (58.0, -4.2), (43.0, -6.5), (28.0, -12.8),
        (13.0, -13.5), (-5.0, -6.8),
    ]
    foot_pts = [
        (ax + 10.0, ay - 2.0), (ax - 4.0, ay - 3.5), (ax - 18.0, ay + 2.5),
        (ax - 29.0, ay + 6.8), (ax - 30.0, ay + 11.2), (ax - 14.0, ay + 11.8),
        (ax + 8.0, ay + 11.5), (ax + 12.0, ay + 5.5),
    ]

    out = [f'{ind}<Node name="{prefix}ThrusterLegGroup">']

    # 1. Stationary Planted Bare Foot on FLOOR = 300.0
    out.append(stroke_shape(i2, f"{prefix}FootHi", [(ax + 2.0, ay + 0.5), (ax - 12.0, ay + 3.5), (ax - 24.0, ay + 7.2)], 2.0, HIGHLIGHT, 2.2))
    out.append(stroke_shape(i2, f"{prefix}FootSole", [(ax + 8.0, ay + 10.8), (ax - 10.0, ay + 11.2), (ax - 26.0, ay + 10.8)], 2.0, CORE_SHADOW, 1.5))
    out.append(smooth_shape(i2, f"{prefix}PlantedFoot", foot_pts, skin_fill(prefix + "Foot", ay - 4, ay + 12, skin)))

    # 2. Shin & Sculpted Calf
    out.append(
        f'{i2}<Node x="{f(p0[knee_key][0])}" y="{f(p0[knee_key][1])}" '
        f'rotation="{f(p0[sh_ang_key])}" name="{prefix}ShinNode" id="{shin_id}">'
    )
    out.append(ellipse_shape(i3, f"{prefix}KneeCap", 0.0, 1.0, 18.0, 16.0, skin_fill(prefix + "Knee", -8, 8, skin)))
    if not is_far:
        out.append(stroke_shape(i3, f"{prefix}GastrocLine", [(10.0, -5.5), (28.0, -6.2), (44.0, -4.5)], 1.3, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}TibiaHi", [(12.0, 4.5), (40.0, 4.2), (64.0, 3.0)], 2.6, HIGHLIGHT, 2.8))
    out.append(stroke_shape(i3, f"{prefix}CalfSh", [(12.0, -11.5), (30.0, -13.0), (52.0, -6.5)], 3.2, CORE_SHADOW, 3.2))
    out.append(smooth_shape(i3, f"{prefix}ShinShape", shin_pts, skin_fill(prefix + "Shin", -15, 8, skin)))
    out.append(f"{i2}</Node>")

    # 3. Thigh with Opaque Compression Shorts, Glowing Gluteus Maximus & 3 Quadriceps Heads
    out.append(
        f'{i2}<Node x="{f(p0[hip_key][0])}" y="{f(p0[hip_key][1])}" '
        f'rotation="{f(p0[th_ang_key])}" name="{prefix}ThighNode" id="{thigh_id}">'
    )
    out.append(smooth_shape(i3, f"{prefix}GluteusMaximus", glute_pts, muscle_paint_fn(prefix + "Glute", glute_t, 1.0)))
    out.append(stroke_shape(i3, f"{prefix}ShortsHem", [(18.0, 16.8), (18.8, 0.0), (18.5, -16.5)], 1.5, "800F172A", 0.5))
    out.append(smooth_shape(i3, f"{prefix}ShortsCuff", shorts_cuff_pts, skin_fill(prefix + "Shorts", -17, 18, shorts)))

    if not is_far:
        out.append(stroke_shape(i3, f"{prefix}QuadGroove1", [(16.0, 8.0), (40.0, 7.2), (60.0, 5.5)], 1.15, "807F1D1D", 0.4))
        out.append(stroke_shape(i3, f"{prefix}ITBandHi", [(18.0, -2.5), (40.0, -2.8), (58.0, -2.5)], 2.0, HIGHLIGHT, 2.0))
        out.append(stroke_shape(i3, f"{prefix}QuadHi", [(20.0, 13.8), (42.0, 13.2), (58.0, 9.8)], 2.4, HIGHLIGHT, 2.6))

    out.append(smooth_shape(i3, f"{prefix}VastusMedialis", vastus_med_pts, muscle_paint_fn(prefix + "VM", quad_t, 0.95)))
    out.append(smooth_shape(i3, f"{prefix}VastusLateralis", vastus_lat_pts, muscle_paint_fn(prefix + "VL", quad_t, 1.0)))
    out.append(smooth_shape(i3, f"{prefix}RectusFemoris", rectus_femoris_pts, muscle_paint_fn(prefix + "RF", quad_t, 1.05)))
    out.append(stroke_shape(i3, f"{prefix}ThighSh", [(16.0, -13.0), (38.0, -11.5), (58.0, -8.0)], 3.8, CORE_SHADOW, 3.8))
    out.append(smooth_shape(i3, f"{prefix}ThighShape", thigh_pts, skin_fill(prefix + "Thigh", -18, 19, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. Braced 3/4 Torso, Pectorals, 6-Pack Abs & Volumetric Head
def build_thruster_torso_and_head():
    """Canonical 3/4 front-left torso, pelvis shorts with Gluteus maximus glow, sculpted pectorals,
    6-pack abs, serratus anterior, and counter-rotating volumetric 3/4 head."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    torso_id, head_id = nid(), nid()
    key_double(torso_id, 13, lambda p: p["hip_near"][0])
    key_double(torso_id, 14, lambda p: p["hip_near"][1])
    key_double(torso_id, 15, lambda p: p["torso_lean"])
    key_double(head_id, 15, lambda p: p["head_counter_rot"])
    p0 = POSES[0]

    def glute_t(p):
        return 0.50 + 0.50 * max(p["squat_depth"], p["press_frac"] * 0.90)

    pelvis_shorts = [
        (-26.0, -16.0), (15.0, -16.0), (16.5, 13.0),
        (-2.0, 16.0), (-24.0, 12.5),
    ]
    glute_pelvis_pts = [
        (0.0, -14.0), (15.0, -15.0), (16.5, 5.0),
        (7.5, 12.0), (-2.0, 3.5),
    ]
    torso_pts = [
        (-24.0, -8.0), (-26.0, -28.0), (-28.0, -52.0),
        (-34.0, -68.0), (-32.0, -82.0), (-14.0, -88.0),
        (10.0, -88.0), (18.0, -76.0), (16.0, -54.0),
        (14.0, -30.0), (15.0, -8.0),
    ]
    pec_near_pts = [
        (-10.0, -82.0), (-28.0, -82.0), (-32.0, -70.0),
        (-28.0, -58.0), (-14.0, -56.0), (-4.0, -62.0),
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
        [(-25.0, -55.0), (-14.0, -55.0), (-14.0, -45.0), (-25.0, -45.0)],
        [(-24.0, -43.0), (-13.5, -43.0), (-13.5, -33.0), (-24.0, -33.0)],
        [(-23.0, -31.0), (-13.0, -31.0), (-13.0, -21.0), (-23.0, -21.0)],
    ]

    neck_pts = [
        (-8.0, 2.0), (-5.0, -16.0), (11.0, -18.0),
        (14.0, -6.0), (14.0, 4.0),
    ]
    head_pts = [
        (-11.0, -38.0), (-13.5, -31.5), (-15.2, -25.5), (-13.8, -20.5),
        (-13.2, -14.5), (-7.5, -11.5), (2.0, -13.0), (9.5, -17.0),
        (14.5, -25.0), (14.0, -36.0), (7.0, -43.0), (-4.0, -43.0),
    ]
    hair_pts = [
        (-11.5, -36.0), (-5.5, -43.5), (6.5, -43.8), (14.5, -37.5),
        (15.0, -26.5), (10.5, -22.5), (9.0, -30.5), (4.0, -35.5),
        (-4.0, -37.0),
    ]

    out = [
        f'{ind}<Node x="{f(p0["hip_near"][0])}" y="{f(p0["hip_near"][1])}" '
        f'rotation="{f(p0["torso_lean"])}" scaleX="0.88" scaleY="0.88" name="ThrusterTorsoAndHeadNode" id="{torso_id}">'
    ]

    # 1. Volumetric 3/4 Head & Neck
    out.append(f'{i2}<Node x="-4.0" y="-88.0" rotation="{f(p0["head_counter_rot"])}" name="HeadCounterNode" id="{head_id}">')
    out.append(smooth_shape(i3, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", -12, -44, 15, -22, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i3, "Ear", 6.5, -25.0, 5.2, 8.0, solid("Ear", "FFA3B1C4"), rot_deg=10.0))
    out.append(stroke_shape(i3, "Brow", [(-13.2, -28.0), (-8.5, -28.5)], 1.25, "FF475569", 0.3))
    out.append(ellipse_shape(i3, "Eye", -10.5, -26.2, 2.5, 1.3, solid("Eye", "FF334155")))
    out.append(stroke_shape(i3, "NoseLine", [(-14.8, -23.0), (-11.8, -21.8)], 0.9, "660F172A", 0.3))
    out.append(stroke_shape(i3, "JawLine", [(-7.5, -12.0), (2.0, -14.0), (6.5, -20.5)], 1.2, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, "HeadHi", [(-9.5, -39.0), (-11.5, -29.0), (-9.0, -16.0)], 2.4, HIGHLIGHT, 2.6))
    out.append(smooth_shape(i3, "HeadSkull", head_pts, skin_fill("Head", -44, -11, SKIN, x0=-15, x1=15)))
    out.append(stroke_shape(i3, "SCMNeckLine", [(2.0, -14.0), (-3.0, 0.0)], 1.2, SOFT_SHADOW, 0.8))
    out.append(smooth_shape(i3, "NeckCol", neck_pts, skin_fill("Neck", -18, 4, SKIN, x0=-8, x1=14)))
    out.append(f"{i2}</Node>")

    # 2. Pelvis Compression Shorts & Posterior Hip Glute Glow
    out.append(stroke_shape(i2, "ShortsWaistband", [(-25.0, -16.0), (-4.0, -16.0), (14.5, -16.0)], 2.2, "CC090D16", 0.0))
    out.append(smooth_shape(i2, "GlutePelvisGlow", glute_pelvis_pts, muscle_paint_fn("GlutePelvis", glute_t, 0.95)))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill("PelvisShorts", -16, 16, SHORTS, x0=-26, x1=17)))

    # 3. Sculpted Pectoral Plate, 6-Pack Abs, Serratus Anterior & Torso Silhouette
    out.append(smooth_shape(i2, "NearPectoral", pec_near_pts, pec_paint))
    for idx, blk in enumerate(abs_blocks):
        out.append(poly_shape(i2, f"AbsBlock{idx + 1}", blk, abs_paint, radius=1.8))
    out.append(stroke_shape(i2, "LineaAlba", [(-26.0, -58.0), (-24.5, -38.0), (-23.0, -18.0)], 1.15, SOFT_SHADOW, 0.4))
    out.append(stroke_shape(i2, "Serratus1", [(-8.0, -54.0), (-2.0, -50.0)], 1.1, SOFT_SHADOW, 0.3))
    out.append(stroke_shape(i2, "Serratus2", [(-9.0, -47.0), (-3.0, -43.0)], 1.1, SOFT_SHADOW, 0.3))
    out.append(stroke_shape(i2, "ObliqueLine", [(-6.0, -38.0), (-9.0, -24.0), (-12.0, -16.0)], 1.2, SOFT_SHADOW, 0.5))
    out.append(stroke_shape(i2, "TorsoHi", [(-24.0, -76.0), (-22.0, -46.0), (-20.0, -18.0)], 3.8, HIGHLIGHT, 4.0))
    out.append(stroke_shape(i2, "TorsoBackSh", [(12.0, -74.0), (11.0, -44.0), (10.0, -16.0)], 4.5, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i2, "TorsoShape", torso_pts, skin_fill("Torso", -88, -8, SKIN, x0=-34, x1=18)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 4. Backdrop, Ground Shadow & RML Scene Assembly
def backdrop_and_ground():
    shd_id = nid()
    key_double(shd_id, 16, lambda p: p["shd_sx"])
    p0 = POSES[0]
    return f"""        <Node x="320" y="{f(FLOOR + 3.0)}" scaleX="{f(p0['shd_sx'])}" name="GroundShadowNode" id="{shd_id}">
            <Shape y="2" name="ShadowSoft">
                <Ellipse width="248" height="24" name="ShadowSoftEllipse"/>
                <Fill name="ShadowSoftFill">
                    <RadialGradient startX="0" startY="0" endX="124" endY="0" name="ShadowSoftGrad">
                        <GradientStop colorValue="8002050B" position="0"/>
                        <GradientStop colorValue="3802050B" position="0.58"/>
                        <GradientStop colorValue="0002050B" position="1"/>
                    </RadialGradient>
                </Fill>
            </Shape>
            <Shape name="ShadowCore">
                <Ellipse width="160" height="12" name="ShadowCoreEllipse"/>
                <Fill name="ShadowCoreFill">
                    <RadialGradient startX="0" startY="0" endX="80" endY="0" name="ShadowCoreGrad">
                        <GradientStop colorValue="BF02050B" position="0"/>
                        <GradientStop colorValue="0002050B" position="1"/>
                    </RadialGradient>
                </Fill>
            </Shape>
        </Node>
        <Shape name="FloorLine">
            <PointsPath isClosed="false" name="FloorPath">
                <StraightVertex x="30" y="{f(FLOOR + 3.0)}"/>
                <StraightVertex x="610" y="{f(FLOOR + 3.0)}"/>
            </PointsPath>
            <Stroke thickness="1.2" cap="round" name="FloorStroke">
                <LinearGradient startX="30" startY="{f(FLOOR + 3.0)}" endX="610" endY="{f(FLOOR + 3.0)}" name="FloorGrad">
                    <GradientStop colorValue="00475569" position="0"/>
                    <GradientStop colorValue="66475569" position="0.5"/>
                    <GradientStop colorValue="00475569" position="1"/>
                </LinearGradient>
            </Stroke>
        </Shape>
        <Shape name="FloorBase">
            <PointsPath isClosed="true" name="FloorBasePath">
                <StraightVertex x="0" y="{f(FLOOR + 3.0)}"/>
                <StraightVertex x="{W}" y="{f(FLOOR + 3.0)}"/>
                <StraightVertex x="{W}" y="{H}"/>
                <StraightVertex x="0" y="{H}"/>
            </PointsPath>
            <Fill name="FloorBaseFill">
                <LinearGradient startX="0" startY="{f(FLOOR + 3.0)}" endX="0" endY="{H}" name="FloorBaseGrad">
                    <GradientStop colorValue="FF0E1525" position="0"/>
                    <GradientStop colorValue="FF080C15" position="1"/>
                </LinearGradient>
            </Fill>
        </Shape>
        <Shape name="StudioBackdrop">
            <PointsPath isClosed="true" name="BackdropPath">
                <StraightVertex x="0" y="0"/>
                <StraightVertex x="{W}" y="0"/>
                <StraightVertex x="{W}" y="{H}"/>
                <StraightVertex x="0" y="{H}"/>
            </PointsPath>
            <Fill name="BackdropFill">
                <RadialGradient startX="320" startY="155" endX="620" endY="155" name="BackdropGrad">
                    <GradientStop colorValue="FF1E293B" position="0"/>
                    <GradientStop colorValue="FF131C2D" position="0.55"/>
                    <GradientStop colorValue="FF0B111E" position="1"/>
                </RadialGradient>
            </Fill>
        </Shape>"""


def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    near_bar_arm_xml, far_bar_arm_xml = build_barbell_and_arms()
    near_leg_xml = build_thruster_leg("Near", is_far=False)
    far_leg_xml = build_thruster_leg("Far", is_far=True)
    torso_head_xml = build_thruster_torso_and_head()
    bg_xml = backdrop_and_ground()

    kobjs = "\n".join(
        f'        <KeyedObject objectId="{oid}">\n{props}\n        </KeyedObject>'
        for oid, props in KEYED
    )

    # Rive 7.3 Draw Order (earlier children render ON TOP of later children):
    # 1. ForegroundNearBarbellAndArm (Near plate stack + Near arm with glowing Deltoids/Triceps + Front-Rack Barbell Shaft)
    # 2. NearThrusterLegGroup        (Near left leg with glowing Quadriceps + Gluteus maximus)
    # 3. ThrusterTorsoAndHeadNode    (3/4 Torso + Pectorals + 6-Pack Abs + Volumetric 3/4 Head)
    # 4. FarThrusterLegGroup         (Far right leg with glowing Quadriceps + Gluteus maximus)
    # 5. BackgroundFarBarbellAndArm  (Far arm + Far stepped plate stack)
    # 6. GroundShadow & StudioBackdrop
    return f"""<RiveData version="7.3">
    <Artboard width="{W}" height="{H}" name="thruster">
{near_bar_arm_xml}
{near_leg_xml}
{torso_head_xml}
{far_leg_xml}
{far_bar_arm_xml}
{bg_xml}
        <LinearAnimation fps="{FPS}" duration="{DURATION}" loop="1" name="main">
{kobjs}
        </LinearAnimation>
        <StateMachine name="State Machine 1">
            <StateMachineLayer name="Layer 1">
                <AnimationState animationId="main" name="main"/>
                <EntryState name="Entry">
                    <Transition to="main"/>
                </EntryState>
                <AnyState name="Any"/>
                <ExitState name="Exit"/>
            </StateMachineLayer>
        </StateMachine>
    </Artboard>
</RiveData>
"""


# ---------------------------------------------------------------- Direct Rive 7.3 Binary Compiler (.riv) & Software Renderer
def _compile_rml_bytes(rml_path: pathlib.Path) -> bytes:
    """Compile RML XML directly to a self-contained Rive 7.3 binary (.riv) with the 52-byte TOC."""
    import xml.etree.ElementTree as ET

    def varuint(val: int) -> bytes:
        out = bytearray()
        v = int(val)
        while True:
            b = v & 0x7F
            v >>= 7
            if v:
                out.append(b | 0x80)
            else:
                out.append(b)
                break
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


def compile_and_render():
    """Compile scene.rml -> thruster.riv and render start/peak PNGs + 256x256 thumbnail."""
    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/7d19b873-f31d-4a3e-a561-525605ec3add/scratch")
    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    riv_bytes = _compile_rml_bytes(OUT)
    build_dir = HERE / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "thruster.riv").write_bytes(riv_bytes)

    assets_riv = REPO_ROOT / "assets" / "animations" / "thruster.riv"
    assets_riv.parent.mkdir(parents=True, exist_ok=True)
    assets_riv.write_bytes(riv_bytes)

    thumb_path = REPO_ROOT / "assets" / "animations" / "thumbnails" / "thruster.png"
    thumb_path.parent.mkdir(parents=True, exist_ok=True)

    # Render start (frame 0, r=0.0 deep front squat), mid (frame 46, r~0.50), and peak (frame 84, r=1.0 overhead lockout)
    for fr, tag in ((0, "frame_start"), (46, "frame_mid"), (84, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(build_dir / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(610, 14, 304))
            write_png(thumb_path, 256, 256, thumb_rgb)

    print(f"Published {assets_riv} ({len(riv_bytes):,} bytes) + {thumb_path}")


if __name__ == "__main__":
    xml = build_rml()
    OUT.write_text(xml, encoding="utf-8")
    print(f"Wrote {OUT} ({len(xml):,} bytes, {len(KEYED)} keyed objects)")
    if "--publish" in sys.argv:
        compile_and_render()
