#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360, FLOOR = 300.0) procedural Rive 7.3 scene for Barbell Squat (id: 'squat').

3/4 front-left view of our canonical CommunityFitness athlete performing a High-Bar Back Squat:
  - Top Standing Lockout (f = 0 & f = 176, r = 0.0):
    * Athlete stands tall in a balanced 3/4 stance on FLOOR = 300.0 with a loaded Olympic barbell
      (chrome bar + 3D multi-plate black cast-iron weight stacks on both ends) resting across the
      upper trapezius behind the neck, hands gripping the bar outside the shoulders with elbows tucked down-back.
  - Bottom Parallel / Below-Parallel Squat (f = 78, r = 1.0):
    * Hips and knees flex deeply into a full athletic squat while keeping the chest proud (sculpted
      pectorals, 6-pack abs, serratus anterior) and spine neutral, with the barbell tracking vertically
      over mid-foot.
  - Highlighted Target & Synergist Muscle Groups (pulsing from warm orange #FFF97316 to intense crimson #FFF43F5E):
    1. Quadriceps femoris (Rectus femoris, Vastus lateralis, Vastus medialis teardrop on both thighs)
    2. Gluteus maximus (Primary hip extensor on the posterior pelvis & upper hip)
    3. Adductor magnus & Hamstrings (Posterior/medial thigh stabilizers & hip extensors)

Run:
    python3 rive_animations/squat/gen_squat.py            # writes scene.rml
    python3 rive_animations/squat/gen_squat.py --publish  # compiles squat.riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/squat.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/squat.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 176  # 2.93s seamless 60fps loop
STEP = 2

# Stationary ankle anchors on FLOOR = 300.0 (3/4 front-left stance facing forward-left -X)
ANKLE_NEAR = (324.0, 287.0)
ANKLE_FAR = (290.0, 276.0)

# Exact 2-Bone IK Limb Lengths
THIGH_NEAR_LEN = 75.0
SHIN_NEAR_LEN = 75.0
THIGH_FAR_LEN = 73.0
SHIN_FAR_LEN = 73.0
UPPER_ARM_LEN = 42.0
FOREARM_LEN = 38.0

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


EASE_DESCEND = cubic_bezier(0.40, 0.0, 0.28, 1.0)
EASE_ASCEND = cubic_bezier(0.34, 0.0, 0.22, 1.0)


def squat_progress(frame):
    """Returns High-Bar Back Squat depth progress r in [0.0, 1.0] across 176 frames:
    - 0..14:    Top standing lockout hold (r = 0.0)
    - 14..70:   Controlled eccentric squat descent to parallel/below-parallel (r: 0.0 -> 1.0)
    - 70..88:   Bottom deep squat hold (r = 1.0)
    - 88..154:  Explosive concentric drive back up to standing lockout (r: 1.0 -> 0.0)
    - 154..176: Top standing lockout hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 14:
        return 0.0
    if fr <= 70:
        return EASE_DESCEND((fr - 14) / 56.0)
    if fr <= 88:
        return 1.0
    if fr <= 154:
        return 1.0 - EASE_ASCEND((fr - 88) / 66.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def solve_ik_left(hip, ankle, l1, l2):
    """Exact 2-bone IK from hip -> knee -> ankle for a leftward-facing (-X) 3/4 athlete.
    +acos(cos_a) bends the knee forward-left (-X, +Y)."""
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
    """Compute 3/4 High-Bar Back Squat joint transforms at depth progress r in [0.0, 1.0]."""
    # 1. Hips: Stand tall at r=0.0 -> Sit back-right and down into deep parallel squat at r=1.0
    hip_near = (lerp(328.0, 358.0, r), lerp(142.2, 214.0, r))
    hip_far = (lerp(306.0, 334.0, r), lerp(136.5, 204.0, r))

    # 2. Exact 2-bone IK for Near (Left) and Far (Right) Legs
    thigh_near_ang, knee_near, shin_near_ang = solve_ik_left(
        hip_near, ANKLE_NEAR, THIGH_NEAR_LEN, SHIN_NEAR_LEN
    )
    thigh_far_ang, knee_far, shin_far_ang = solve_ik_left(
        hip_far, ANKLE_FAR, THIGH_FAR_LEN, SHIN_FAR_LEN
    )

    # 3. Proud Braced Torso & Neutral Spine:
    #    Torso leans forward-left slightly (-19 deg at bottom) so the high-bar barbell stays directly over mid-foot!
    torso_lean = math.radians(lerp(-2.0, -19.0, r))
    head_counter_rot = -torso_lean * 0.82  # Head maintains level forward-left gaze

    # Compute world shoulder & upper-trapezius barbell shelf coordinates from torso transform
    cs, sn = math.cos(torso_lean), math.sin(torso_lean)

    def torso_world(lx, ly):
        return (hip_near[0] + lx * cs - ly * sn, hip_near[1] + lx * sn + ly * cs)

    sh_near = torso_world(8.0, -76.0)
    sh_far = torso_world(-34.0, -78.0)
    bar_center = torso_world(-10.0, -82.0)

    # 4. Hands gripping the Olympic barbell outside the shoulders + tucked elbows under the bar
    hand_near = (bar_center[0] + 42.0, bar_center[1] + 5.8)
    hand_far = (bar_center[0] - 40.0, bar_center[1] - 5.5)

    elbow_near = (sh_near[0] + lerp(18.0, 16.0, r), sh_near[1] + lerp(30.0, 28.0, r))
    elbow_far = (sh_far[0] - lerp(16.0, 14.0, r), sh_far[1] + lerp(26.0, 24.0, r))

    ua_near_ang, ua_near_sc = seg_xform(sh_near, elbow_near, UPPER_ARM_LEN)
    fa_near_ang, fa_near_sc = seg_xform(elbow_near, hand_near, FOREARM_LEN)
    ua_far_ang, ua_far_sc = seg_xform(sh_far, elbow_far, UPPER_ARM_LEN)
    fa_far_ang, fa_far_sc = seg_xform(elbow_far, hand_far, FOREARM_LEN)

    shd_sx = lerp(1.06, 1.24, r)

    return {
        "r": r,
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
POSES = {fr: pose(squat_progress(fr)) for fr in FRAMES}

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


def poly_shape(indent, name, pts, paint_xml, radius=1.2):
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


def muscle_paint_fn(name, fn_t, line=0.95):
    fid, lid = nid(), nid()
    key_color(fid, 37, lambda p: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, fn_t(p)))
    key_color(lid, 37, lambda p: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, fn_t(p)))
    t0 = fn_t(POSES[0])
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- 1. High-Bar Olympic Barbell & Arms (Foreground Near Side + Background Far Side)
def build_barbell_and_arms():
    """Returns (near_bar_and_arm_xml, far_bar_and_arm_xml) so the Olympic barbell shaft passes cleanly
    BEHIND the athlete's head/neck across the upper trapezius while the near arm & near multi-plate
    stack render in the foreground."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    p0 = POSES[0]

    near_bar_id, far_bar_id = nid(), nid()
    for bid in (near_bar_id, far_bar_id):
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

    prot = 8.0
    near_plate_face = (
        f'<Fill name="NearPlateFaceFill">{grad3("NearPlateFaceGrad", -38, 38, *PLATE_DARK, x0=-22, x1=22)}</Fill>'
        '<Stroke thickness="1.35" join="round" name="NearPlateRimStroke"><SolidColor colorValue="FF475569" name="NearPlateRimCol"/></Stroke>'
    )
    near_plate_rim = f'<Fill name="NearPlateBackFill">{grad("NearPlateBackGrad", -22, -38, 22, 38, "FF0F172A", "FF020617")}</Fill>'
    near_ring_paint = (
        '<Fill name="NearRingFill"><SolidColor colorValue="FF111827" name="NearRingCol"/></Fill>'
        '<Stroke thickness="1.15" join="round" name="NearRingStroke"><SolidColor colorValue="FF334155" name="NearRingStrokeCol"/></Stroke>'
    )
    hub_paint = (
        f'<Fill name="HubFill">{grad3("HubGrad", -8, 8, "FFE2E8F0", "FF64748B", "FF1E293B")}</Fill>'
        '<Stroke thickness="1.0" join="round" name="HubStroke"><SolidColor colorValue="FFCBD5E1" name="HubStrokeCol"/></Stroke>'
    )
    shaft_fill = f'<Fill name="ShaftFill">{grad3("ShaftGrad", -12, 12, "FFF1F5F9", "FF64748B", "FF1E293B")}</Fill>'

    ua_pts = [
        (-8.0, 0.0), (-5.0, -9.2), (10.0, -10.5), (26.0, -9.5), (38.0, -6.5),
        (44.0, 0.0), (38.0, 6.5), (26.0, 9.5), (10.0, 10.5), (-5.0, 9.2),
    ]
    delt_pts = [
        (-12.0, -2.0), (-5.0, -11.5), (8.0, -10.5), (16.0, -2.0),
        (14.0, 9.5), (3.0, 12.5), (-9.0, 9.0),
    ]
    fa_pts = [
        (-5.5, 0.0), (-3.5, -7.2), (12.0, -8.2), (28.0, -6.2), (36.0, -4.5),
        (40.0, 0.0), (36.0, 4.5), (28.0, 6.2), (12.0, 8.2), (-3.5, 7.2),
    ]
    fist_pts = [
        (33.0, -5.5), (42.0, -5.2), (44.0, 0.0), (42.0, 5.2), (33.0, 5.5),
    ]

    # --- Foreground: Near-Right Stepped Multi-Plate Stack + Near Arm Gripping Bar ---
    near_sleeve_pts = [(74.0, 7.8), (104.0, 12.0), (103.2, 17.6), (73.2, 13.4)]
    near_shaft_pts = [(16.0, -0.2), (56.0, 5.4), (55.2, 10.6), (15.2, 5.0)]

    near_xml = "\n".join([
        f'{ind}<Node name="ForegroundNearBarbellAndArm">',
        # 1. Near Multi-Plate Stack (45-lb + 25-lb + 10-lb) & Protruding Outer Sleeve
        f'{i2}<Node x="{f(p0["bar_center"][0])}" y="{f(p0["bar_center"][1])}" name="NearBarbellStack" id="{near_bar_id}">',
        ellipse_shape(i3, "NearSleeveEndCap", 103.6, 14.8, 4.5, 6.8, solid("NearCap", "FF0F172A"), rot_deg=prot),
        ellipse_shape(i3, "NearSleeveEndRim", 103.6, 14.8, 5.8, 8.2, solid("NearCapRim", "FF94A3B8"), rot_deg=prot),
        stroke_shape(i3, "NearSleeveHi", [(75.0, 9.4), (90.0, 11.5), (102.0, 13.2)], 1.5, "CCE2E8F0", 0.4),
        poly_shape(i3, "NearOuterSleeve", near_sleeve_pts, shaft_fill, radius=1.0),
        ellipse_shape(i3, "NearOuterCollar", 75.5, 10.6, 9.5, 15.0, hub_paint, rot_deg=prot),
        # Outer 10-lb Plate (71.0, 10.0)
        ellipse_shape(i3, "NearPlate3Face", 71.0, 10.0, 30.0, 48.0, near_plate_face, rot_deg=prot),
        ellipse_shape(i3, "NearPlate3Rim", 68.0, 9.5, 30.0, 48.0, near_plate_rim, rot_deg=prot),
        # Middle 25-lb Plate (64.5, 9.1)
        ellipse_shape(i3, "NearPlate2Inner", 64.5, 9.1, 28.0, 45.0, near_ring_paint, rot_deg=prot),
        ellipse_shape(i3, "NearPlate2Face", 64.5, 9.1, 38.0, 62.0, near_plate_face, rot_deg=prot),
        ellipse_shape(i3, "NearPlate2Rim", 61.0, 8.6, 38.0, 62.0, near_plate_rim, rot_deg=prot),
        # Inner 45-lb Plate (57.5, 8.1)
        ellipse_shape(i3, "NearPlate1Inner", 57.5, 8.1, 34.0, 56.0, near_ring_paint, rot_deg=prot),
        ellipse_shape(i3, "NearPlate1Face", 57.5, 8.1, 46.0, 76.0, near_plate_face, rot_deg=prot),
        ellipse_shape(i3, "NearPlate1Rim", 53.5, 7.5, 46.0, 76.0, near_plate_rim, rot_deg=prot),
        ellipse_shape(i3, "NearInnerCollar", 51.0, 7.2, 7.8, 12.2, hub_paint, rot_deg=prot),
        f"{i2}</Node>",

        # 2. Near Forearm & Gripping Hand on Bar (drawn in front of the near bar shaft)
        f'{i2}<Node x="{f(p0["elbow_near"][0])}" y="{f(p0["elbow_near"][1])}" '
        f'rotation="{f(p0["fa_near_ang"])}" scaleX="{f(p0["fa_near_sc"])}" name="NearForearm" id="{fa_near_id}">',
        stroke_shape(i3, "NearKnuckle1", [(35.0, -2.2), (41.0, -2.0)], 0.95, SOFT_SHADOW, 0.0),
        stroke_shape(i3, "NearKnuckle2", [(35.0, 1.2), (41.0, 1.4)], 0.95, SOFT_SHADOW, 0.0),
        smooth_shape(i3, "NearGrippingFist", fist_pts, skin_fill("NearFist", -6, 6, SKIN)),
        stroke_shape(i3, "NearForearmHi", [(6.0, -3.5), (26.0, -3.0)], 2.4, HIGHLIGHT, 2.5),
        stroke_shape(i3, "NearForearmSh", [(6.0, 3.8), (26.0, 3.2)], 3.2, CORE_SHADOW, 3.0),
        smooth_shape(i3, "NearForearmShape", fa_pts, skin_fill("NearFA", -8, 8, SKIN)),
        f"{i2}</Node>",

        # 3. Near Upper Arm & Sculpted Deltoid Cap
        f'{i2}<Node x="{f(p0["sh_near"][0])}" y="{f(p0["sh_near"][1])}" '
        f'rotation="{f(p0["ua_near_ang"])}" scaleX="{f(p0["ua_near_sc"])}" name="NearUpperArm" id="{ua_near_id}">',
        stroke_shape(i3, "NearDeltHi", [(-2.0, -6.0), (8.0, -4.5)], 2.4, HIGHLIGHT, 2.4),
        smooth_shape(i3, "NearDeltoidCap", delt_pts, skin_fill("NearDelt", -12, 12, SKIN)),
        stroke_shape(i3, "NearUpperArmHi", [(10.0, -5.0), (30.0, -4.5)], 2.6, HIGHLIGHT, 2.6),
        stroke_shape(i3, "NearUpperArmSh", [(10.0, 5.5), (30.0, 5.0)], 3.4, CORE_SHADOW, 3.2),
        smooth_shape(i3, "NearUpperArmShape", ua_pts, skin_fill("NearUA", -10, 10, SKIN)),
        f"{i2}</Node>",

        # 4. Near Bar Shaft Segment from Neck/Trap (+16, +2.2) out to Near Collar (+55, +7.8)
        f'{i2}<Node x="{f(p0["bar_center"][0])}" y="{f(p0["bar_center"][1])}" name="NearBarShaftNode" id="{nid()}">',
        stroke_shape(i3, "NearShaftHi", [(16.0, 1.2), (36.0, 4.0), (54.0, 6.5)], 1.4, "CCE2E8F0", 0.4),
        poly_shape(i3, "NearBarShaft", near_shaft_pts, shaft_fill, radius=1.0),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])
    # Key the NearBarShaftNode position too
    near_shaft_oid = f"o{_id}"
    key_double(near_shaft_oid, 13, lambda p: p["bar_center"][0])
    key_double(near_shaft_oid, 14, lambda p: p["bar_center"][1])

    # --- Background (Behind Neck/Torso): Center/Far Barbell Shaft, Far Arm & Far Multi-Plate Stack ---
    far_shaft_pts = [(-86.0, -14.5), (20.0, 0.4), (19.2, 5.6), (-86.8, -9.3)]
    far_plate_face = (
        f'<Fill name="FarPlateFaceFill">{grad3("FarPlateFaceGrad", -34, 34, "FF263244", "FF111827", "FF060911", x0=-20, x1=20)}</Fill>'
        '<Stroke thickness="1.25" join="round" name="FarPlateRimStroke"><SolidColor colorValue="FF334155" name="FarPlateRimCol"/></Stroke>'
    )
    far_plate_rim = f'<Fill name="FarPlateBackFill">{grad("FarPlateBackGrad", -20, -34, 20, 34, "FF090D16", "FF020617")}</Fill>'

    far_xml = "\n".join([
        f'{ind}<Node name="BackgroundFarBarbellAndArm">',
        # 1. Far Forearm & Hand Gripping Bar outside Far Shoulder
        f'{i2}<Node x="{f(p0["elbow_far"][0])}" y="{f(p0["elbow_far"][1])}" '
        f'rotation="{f(p0["fa_far_ang"])}" scaleX="{f(p0["fa_far_sc"])}" name="FarForearm" id="{fa_far_id}">',
        smooth_shape(i3, "FarGrippingFist", fist_pts, skin_fill("FarFist", -6, 6, SKIN_FAR)),
        smooth_shape(i3, "FarForearmShape", fa_pts, skin_fill("FarFA", -8, 8, SKIN_FAR)),
        f"{i2}</Node>",

        # 2. Far Upper Arm & Deltoid
        f'{i2}<Node x="{f(p0["sh_far"][0])}" y="{f(p0["sh_far"][1])}" '
        f'rotation="{f(p0["ua_far_ang"])}" scaleX="{f(p0["ua_far_sc"])}" name="FarUpperArm" id="{ua_far_id}">',
        smooth_shape(i3, "FarDeltoidCap", delt_pts, skin_fill("FarDelt", -12, 12, SKIN_FAR)),
        smooth_shape(i3, "FarUpperArmShape", ua_pts, skin_fill("FarUA", -10, 10, SKIN_FAR)),
        f"{i2}</Node>",

        # 3. Center & Far Barbell Shaft + Far Stepped Multi-Plate Stack (-56, -7.8)
        f'{i2}<Node x="{f(p0["bar_center"][0])}" y="{f(p0["bar_center"][1])}" name="FarBarbellStackAndShaft" id="{far_bar_id}">',
        stroke_shape(i3, "FarShaftHi", [(-84.0, -12.8), (-32.0, -5.5), (18.0, 1.5)], 1.4, "B3CBD5E1", 0.4),
        poly_shape(i3, "FarAndCenterBarShaft", far_shaft_pts, shaft_fill, radius=1.0),
        ellipse_shape(i3, "FarInnerCollar", -50.0, -7.0, 7.2, 11.5, hub_paint, rot_deg=prot),
        ellipse_shape(i3, "FarPlate1Inner", -56.0, -7.8, 30.0, 50.0, near_ring_paint, rot_deg=prot),
        ellipse_shape(i3, "FarPlate1Face", -56.0, -7.8, 42.0, 70.0, far_plate_face, rot_deg=prot),
        ellipse_shape(i3, "FarPlate1Rim", -59.5, -8.3, 42.0, 70.0, far_plate_rim, rot_deg=prot),
        ellipse_shape(i3, "FarPlate2Face", -62.5, -8.8, 34.0, 56.0, far_plate_face, rot_deg=prot),
        ellipse_shape(i3, "FarPlate2Rim", -65.5, -9.2, 34.0, 56.0, far_plate_rim, rot_deg=prot),
        ellipse_shape(i3, "FarPlate3Face", -68.5, -9.6, 26.0, 42.0, far_plate_face, rot_deg=prot),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])

    return near_xml, far_xml


# ---------------------------------------------------------------- 2. Squat Leg Builder (Quadriceps, Gluteus Maximus, Adductor Magnus / Hamstrings)
def build_squat_leg(prefix, is_far=False):
    """Builds the Near (Left) or Far (Right) Leg in 3/4 view with glowing:
      1. Quadriceps femoris (Rectus femoris, Vastus lateralis, Vastus medialis teardrop)
      2. Gluteus maximus
      3. Adductor magnus / Hamstrings"""
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

    def quad_t(p):
        return (0.44 + 0.56 * (p["r"] ** 0.74)) * m_scale

    def glute_t(p):
        return (0.42 + 0.58 * (p["r"] ** 0.76)) * m_scale

    def adductor_t(p):
        return (0.38 + 0.56 * (p["r"] ** 0.80)) * m_scale

    # In Thigh local space (+X from Hip(0) -> Knee(75); thigh_ang in [+94 deg .. +174 deg]):
    # +Y points UP-LEFT (anterior/superior Quadriceps surface: Rectus femoris, Vastus lateralis, Vastus medialis!)
    # -Y points DOWN-RIGHT (posterior/inferior Gluteus maximus, Adductor magnus & Hamstrings!)
    thigh_pts = [
        (-16.0, 12.0), (10.0, 18.5), (38.0, 18.8), (62.0, 14.5),
        (77.0, 6.0), (77.0, -5.5), (62.0, -11.8), (36.0, -16.2),
        (10.0, -18.2), (-16.0, -14.0),
    ]
    shorts_cuff_pts = [
        (-13.0, 10.5), (18.0, 17.5), (19.0, -17.0), (-14.0, -13.5),
    ]
    glute_pts = [
        (-15.0, -1.5), (14.0, -3.5), (16.0, -17.2), (-5.0, -18.0), (-15.0, -11.5),
    ]
    rectus_femoris_pts = [
        (10.0, 17.5), (35.0, 18.0), (56.0, 15.0), (66.0, 10.5),
        (63.0, 6.2), (42.0, 7.8), (20.0, 8.5), (8.0, 9.2),
    ]
    vastus_lat_pts = [
        (12.0, 8.2), (35.0, 7.5), (55.0, 6.5), (64.0, 4.2),
        (59.0, -0.8), (36.0, -1.2), (14.0, -0.5),
    ]
    vastus_med_pts = [
        (44.0, 14.8), (60.0, 13.2), (69.0, 7.5), (62.0, 2.2), (46.0, 5.2),
    ]
    adductor_ham_pts = [
        (16.0, -4.5), (40.0, -4.8), (58.0, -4.8),
        (62.0, -8.8), (46.0, -13.5), (24.0, -16.2), (14.0, -15.2),
    ]

    shin_pts = [
        (-8.0, 6.8), (18.0, 6.8), (48.0, 5.8), (72.0, 4.2),
        (76.0, 0.0), (70.0, -4.8), (52.0, -7.2), (34.0, -14.2),
        (16.0, -15.0), (-6.0, -7.5),
    ]
    foot_pts = [
        (ax + 10.0, ay - 2.0), (ax - 4.0, ay - 3.5), (ax - 18.0, ay + 2.5),
        (ax - 29.0, ay + 6.8), (ax - 30.0, ay + 11.2), (ax - 14.0, ay + 11.8),
        (ax + 8.0, ay + 11.5), (ax + 12.0, ay + 5.5),
    ]

    out = [f'{ind}<Node name="{prefix}SquatLegGroup">']

    # 1. Stationary Planted Bare Foot on FLOOR = 300.0
    out.append(stroke_shape(i2, f"{prefix}FootHi", [(ax + 2.0, ay + 0.5), (ax - 12.0, ay + 3.5), (ax - 24.0, ay + 7.2)], 2.0, HIGHLIGHT, 2.2))
    out.append(stroke_shape(i2, f"{prefix}FootSole", [(ax + 8.0, ay + 10.8), (ax - 10.0, ay + 11.2), (ax - 26.0, ay + 10.8)], 2.0, CORE_SHADOW, 1.5))
    out.append(smooth_shape(i2, f"{prefix}PlantedFoot", foot_pts, skin_fill(prefix + "Foot", ay - 4, ay + 12, skin)))

    # 2. Shin & Sculpted Silver-Slate Gastrocnemius/Soleus Calf
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

    # 3. Thigh with Opaque Compression Shorts, Glowing Gluteus Maximus, 3 Quadriceps Heads & Adductor Magnus / Hamstrings
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
    out.append(smooth_shape(i3, f"{prefix}AdductorHamstrings", adductor_ham_pts, muscle_paint_fn(prefix + "AddHam", adductor_t, 0.95)))
    out.append(stroke_shape(i3, f"{prefix}ThighSh", [(16.0, -13.0), (38.0, -11.5), (58.0, -8.0)], 3.8, CORE_SHADOW, 3.8))
    out.append(smooth_shape(i3, f"{prefix}ThighShape", thigh_pts, skin_fill(prefix + "Thigh", -18, 19, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. Braced 3/4 Torso, Pectorals, 6-Pack Abs & Volumetric Head
def build_squat_torso_and_head():
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
        return 0.42 + 0.58 * (p["r"] ** 0.76)

    pelvis_shorts = [
        (-28.0, -18.0), (16.0, -18.0), (18.0, 14.0),
        (-2.0, 17.5), (-26.0, 14.0),
    ]
    glute_pelvis_pts = [
        (0.0, -15.0), (16.0, -16.0), (18.0, 5.0),
        (8.0, 13.0), (-2.0, 4.0),
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

    # Volumetric 3/4 Head & Neck anchored at (-4.0, -88.0) so it counter-rotates to stay level
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
        f'rotation="{f(p0["torso_lean"])}" name="SquatTorsoAndHeadNode" id="{torso_id}">'
    ]

    # 1. Pelvis Compression Shorts & Gluteus Maximus Highlight
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill("PelvisShorts", -18, 18, SHORTS)))
    out.append(smooth_shape(i2, "GlutePelvisHighlight", glute_pelvis_pts, muscle_paint_fn("GlutePelvis", glute_t, 0.95)))

    # 2. Counter-Rotating Volumetric 3/4 Head & Muscular Neck (in front of the high-bar barbell shaft!)
    out.append(f'{i2}<Node x="-4.0" y="-88.0" rotation="{f(p0["head_counter_rot"])}" name="HeadAndNeckNode" id="{head_id}">')
    out.append(smooth_shape(i3, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", -12, -44, 15, -22, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i3, "Ear", 7.0, -23.5, 5.5, 8.5, solid("Ear", "FFA3B1C4"), rot_deg=12.0))
    out.append(stroke_shape(i3, "BrowShade", [(-13.5, -31.2), (-9.0, -30.8)], 1.4, "590F172A", 0.8))
    out.append(stroke_shape(i3, "EyeLine", [(-11.8, -29.2), (-8.8, -29.0)], 1.1, "730F172A", 0.4))
    out.append(stroke_shape(i3, "MouthLine", [(-13.5, -19.5), (-10.0, -19.2)], 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i3, "HeadHi", [(-10.5, -34.0), (-6.0, -39.0), (3.0, -40.0)], 3.0, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i3, "JawShadow", [(-10.5, -12.5), (-1.5, -12.0), (6.5, -15.5)], 2.6, CORE_SHADOW, 2.5))
    out.append(smooth_shape(i3, "Head", head_pts, skin_fill("Head", -43, -11, SKIN, x0=-15, x1=14)))
    out.append(stroke_shape(i3, "SCMLine", [(5.0, -15.0), (1.0, -6.0), (-2.0, 2.0)], 1.4, SOFT_SHADOW, 1.2))
    out.append(smooth_shape(i3, "Neck", neck_pts, skin_fill("Neck", -18, 4, SKIN)))
    out.append(f"{i2}</Node>")

    # 3. Sculpted Torso, Pectorals, 6-Pack Abs & Serratus Anterior
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "Serratus1", [(-4.0, -52.0), (-10.0, -46.0), (-12.5, -40.0)], 1.3, "380F172A", 1.0))
    out.append(stroke_shape(i2, "Serratus2", [(-3.0, -42.0), (-9.0, -36.0), (-11.5, -30.0)], 1.3, "380F172A", 1.0))
    out.append(stroke_shape(i2, "PecHi", [(-10.0, -78.0), (-22.0, -74.0), (-26.0, -64.0)], 2.6, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i2, "PectoralNear", pec_near_pts, pec_paint))
    out.append(stroke_shape(i2, "TorsoHi", [(-20.0, -72.0), (-19.0, -46.0), (-18.0, -20.0)], 3.8, HIGHLIGHT, 4.2))
    out.append(stroke_shape(i2, "TorsoBackSh", [(12.0, -72.0), (10.0, -44.0), (9.0, -18.0)], 4.8, CORE_SHADOW, 4.8))
    out.append(smooth_shape(i2, "Torso", torso_pts, skin_fill("Torso", -88, -8, SKIN, x0=-34, x1=18)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    shd_id = nid()
    key_double(shd_id, 16, lambda p: p["shd_sx"])
    p0 = POSES[0]

    near_bar_arm_xml, far_bar_arm_xml = build_barbell_and_arms()
    near_leg_xml = build_squat_leg("Near", is_far=False)
    torso_xml = build_squat_torso_and_head()
    far_leg_xml = build_squat_leg("Far", is_far=True)

    by_obj = {}
    for oid, kp_xml in KEYED:
        by_obj.setdefault(oid, []).append(kp_xml)
    keyed_objects_xml = "\n".join(
        f'        <KeyedObject objectId="{oid}">\n' + "\n".join(kps) + "\n        </KeyedObject>"
        for oid, kps in by_obj.items()
    )

    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"

    return f"""<Rive version="7.3">
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="BarbellSquat" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near-Right Multi-Plate Barbell Stack & Near Arm Gripping Bar -->
{near_bar_arm_xml}

        <!-- 2. Near (Left) Squatting Leg (Quadriceps, Gluteus maximus, Adductor magnus / Hamstrings) -->
{near_leg_xml}

        <!-- 3. Braced 3/4 Torso, Pectorals, 6-Pack Abs & Volumetric Head (in front of Center Bar Shaft) -->
{torso_xml}

        <!-- 4. Far (Right) Squatting Leg -->
{far_leg_xml}

        <!-- 5. Background: Center/Far Barbell Shaft (across Upper Traps), Far Arm & Far Multi-Plate Stack -->
{far_bar_arm_xml}

        <!-- 6. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="312" y="{f(FLOOR - 2)}" scaleX="{f(p0['shd_sx'])}" scaleY="0.09" name="AthleteShadow" id="{shd_id}">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="BarbellSquat" id="0:60">
{keyed_objects_xml}
        </LinearAnimation>
    </Artboard>
</Rive>
"""


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
    (BUILD / "squat.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/7d19b873-f31d-4a3e-a561-525605ec3add/scratch")
    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (42, "frame_mid"), (78, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(620, 30, 290))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
