#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive scene for Dumbbell Hammer Curl (id: 'hammer_curl').

Reuses our canonical standing 3/4 front-left athletic male mannequin from `front_raise/gen_front_raise.py`
and `bicep_curl_barbell/gen_bicep_curl_barbell.py` (volumetric 3/4 head, muscular neck, sculpted pectorals,
6-pack rectus abdominis, slender waist, compression shorts, quadriceps, gastrocnemius calves, and planted feet).

Matches the 2-panel 3/4 front-left Alternating Standing Dumbbell Hammer Curl reference illustration:
  - Left Panel (f = 0 & f = 160, r = 0.0):
    * Near (Left) Arm is curled up to the top peak contraction in front of the left shoulder/chest
      holding a heavy 3D double-plate black dumbbell vertically in a NEUTRAL (hammer / thumbs-up) grip.
    * Far (Right) Arm hangs extended at the side of the right hip/thigh holding the second black
      double-plate dumbbell in a neutral grip.
  - Right Panel (f = 74, r = 1.0):
    * Far (Right) Arm curls smoothly up to peak contraction in front of the right shoulder/chest
      holding its black dumbbell vertically in a neutral (hammer) grip.
    * Near (Left) Arm lowers smoothly down to the side of the left thigh/hip in a neutral grip,
      exposing the full 3/4 chest, 6-pack abs, and all 3 glowing arm muscles on the near left arm.
  - Stationary Body Rule:
    * Feet, calves, thighs, hips/shorts, 6-pack abs, chest, neck, and head remain 100% stationary
      throughout the entire repetition while the elbows stay anchored at the sides of the torso.
  - All 3 Labeled Target Muscle Groups (pulsing from warm orange #FFF97316 to intense crimson #FFF43F5E):
    1. Biceps brachii (short & long heads on the anterior upper arm, with dynamic biceps peak bulge)
    2. Brachialis (fusiform lateral/deep elbow flexor between biceps and triceps — primary mover in hammer curl)
    3. Brachioradialis (prominent thumb-side proximal/radial forearm muscle — heavily recruited by neutral grip)

Run:
    python3 gen_hammer_curl.py            # writes scene.rml
    python3 gen_hammer_curl.py --publish  # compiles assets/animations/hammer_curl.riv + 256x256 thumbnail
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

# Canonical Shoulder Anchors & Limb Lengths from front_raise / bicep_curl_barbell
SHOULDER_FAR = (296.0, 99.0)   # Right (far / screen-left) shoulder
SHOULDER_NEAR = (346.0, 102.0)  # Left (near / screen-right) shoulder
UPPER_ARM_LEN = 48.0
FOREARM_LEN = 43.0

# Canonical Palette from front_raise / bicep_curl_barbell
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
PLATE_DARK = ("FF334155", "FF182232", "FF090D16")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "4D0F172A"

# Muscle activation colors: warm orange (#FFF97316) -> intense crimson (#FFF43F5E)
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


EASE_CURL = cubic_bezier(0.38, 0.0, 0.26, 1.0)
EASE_LOWER = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def hammer_progress(frame):
    """Returns alternating hammer-curl progress r in [0.0, 1.0] across 160 frames:
    - 0..12:   Left Panel hold (r = 0.0: Near left arm curled at top peak, Far right arm extended at hip)
    - 12..64:  Alternating transition (r: 0.0 -> 1.0: Near left arm lowers, Far right arm curls to top peak)
    - 64..84:  Right Panel hold (r = 1.0: Far right arm curled at top peak, Near left arm extended at hip)
    - 84..148: Alternating return (r: 1.0 -> 0.0: Far right arm lowers, Near left arm curls to top peak)
    - 148..160: Left Panel hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 64:
        return EASE_CURL((fr - 12) / 52.0)
    if fr <= 84:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_LOWER((fr - 84) / 64.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


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
    sc = max(0.60, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute Alternating Standing Dumbbell Hammer Curl transforms at progress r in [0.0, 1.0]."""
    # Left Panel (r = 0.0): near_curl = 1.0 (Near Left Arm at top), far_curl = 0.0 (Far Right Arm at bottom)
    # Right Panel (r = 1.0): near_curl = 0.0 (Near Left Arm at bottom), far_curl = 1.0 (Far Right Arm at top)
    near_curl = 1.0 - r
    far_curl = r

    # 1. Near (Left) Arm Hammer Curl Kinematics (SHOULDER_NEAR = (346, 102)):
    #    - near_curl = 0.0 (Right Panel — extended at side of left thigh):
    #        elbow = (349.0, 148.0), hand = (345.0, 189.0)
    #    - near_curl = 0.5 (Mid-curl — forearm horizontal forward-left):
    #        elbow = (344.0, 149.0), hand = (303.0, 146.0)
    #    - near_curl = 1.0 (Left Panel — curled up in front of left chest/clavicle):
    #        elbow = (340.0, 147.0), hand = (310.0, 111.0)
    elbow_near = quad_interp_pt((349.0, 148.0), (344.0, 149.0), (340.0, 147.0), near_curl)
    hand_near = quad_interp_pt((345.0, 189.0), (303.0, 146.0), (310.0, 111.0), near_curl)
    ua_near_ang, ua_near_sc = seg_xform(SHOULDER_NEAR, elbow_near, UPPER_ARM_LEN)
    fa_near_ang, fa_near_sc = seg_xform(elbow_near, hand_near, FOREARM_LEN)
    biceps_near_peak = lerp(1.0, 1.22, near_curl ** 1.1)

    # 2. Far (Right) Arm Hammer Curl Kinematics (SHOULDER_FAR = (296, 99)):
    #    - far_curl = 0.0 (Left Panel — extended at side of right hip/thigh):
    #        elbow = (294.0, 144.0), hand = (284.0, 184.0)
    #    - far_curl = 0.5 (Mid-curl — forearm horizontal forward-left):
    #        elbow = (291.0, 145.0), hand = (252.0, 142.0)
    #    - far_curl = 1.0 (Right Panel — curled up in front of right shoulder/clavicle):
    #        elbow = (288.0, 143.0), hand = (264.0, 108.0)
    elbow_far = quad_interp_pt((294.0, 144.0), (291.0, 145.0), (288.0, 143.0), far_curl)
    hand_far = quad_interp_pt((284.0, 184.0), (252.0, 142.0), (264.0, 108.0), far_curl)
    ua_far_ang, ua_far_sc = seg_xform(SHOULDER_FAR, elbow_far, UPPER_ARM_LEN)
    fa_far_ang, fa_far_sc = seg_xform(elbow_far, hand_far, FOREARM_LEN)
    biceps_far_peak = lerp(1.0, 1.20, far_curl ** 1.1)

    return {
        "r": r,
        "near_curl": near_curl,
        "far_curl": far_curl,
        "elbow_near": elbow_near,
        "hand_near": hand_near,
        "ua_near_ang": ua_near_ang,
        "ua_near_sc": ua_near_sc,
        "fa_near_ang": fa_near_ang,
        "fa_near_sc": fa_near_sc,
        "biceps_near_peak": biceps_near_peak,
        "elbow_far": elbow_far,
        "hand_far": hand_far,
        "ua_far_ang": ua_far_ang,
        "ua_far_sc": ua_far_sc,
        "fa_far_ang": fa_far_ang,
        "fa_far_sc": fa_far_sc,
        "biceps_far_peak": biceps_far_peak,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(hammer_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = (
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

if __name__ == "__main__":
    for _fr in (0, 38, 74, 116, DURATION):
        _p = POSES[_fr if _fr in POSES else min(POSES.keys(), key=lambda k: abs(k - _fr))]
        print(
            f"f{_fr:3d} r={_p['r']:.3f} hand_near=({_p['hand_near'][0]:.1f},{_p['hand_near'][1]:.1f}) "
            f"hand_far=({_p['hand_far'][0]:.1f},{_p['hand_far'][1]:.1f})"
        )


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


# ---------------------------------------------------------------- 1. Neutral-Grip (Hammer) Dumbbell & Arm Rig (Biceps, Brachialis, Brachioradialis)
def hammer_curl_arm_rig(prefix, far):
    """Arm + Biceps brachii + Brachialis + Brachioradialis + 3D Double-Plate Black Dumbbell held in a NEUTRAL (hammer) grip."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "
    skin = SKIN_FAR if far else SKIN
    sx, sy = SHOULDER_FAR if far else SHOULDER_NEAR
    ua_ang_k = "ua_far_ang" if far else "ua_near_ang"
    ua_sc_k = "ua_far_sc" if far else "ua_near_sc"
    el_k = "elbow_far" if far else "elbow_near"
    hand_k = "hand_far" if far else "hand_near"
    fa_ang_k = "fa_far_ang" if far else "fa_near_ang"
    fa_sc_k = "fa_far_sc" if far else "fa_near_sc"
    bic_peak_k = "biceps_far_peak" if far else "biceps_near_peak"
    curl_k = "far_curl" if far else "near_curl"

    ua_id, bic_id, fa_id, db_top_id, db_bot_id = nid(), nid(), nid(), nid(), nid()
    key_double(ua_id, 15, lambda p: p[ua_ang_k])
    key_double(ua_id, 16, lambda p: p[ua_sc_k])
    key_double(bic_id, 17, lambda p: p[bic_peak_k])

    key_double(fa_id, 13, lambda p: p[el_k][0])
    key_double(fa_id, 14, lambda p: p[el_k][1])
    key_double(fa_id, 15, lambda p: p[fa_ang_k])
    key_double(fa_id, 16, lambda p: p[fa_sc_k])

    # In a Hammer (Neutral) Grip, the dumbbell handle axis is perpendicular to the forearm bone (+x)
    # in the sagittal plane (pointing towards the thumb side +y_local of the forearm).
    # We drive the dumbbell nodes with `fa_ang_k` so the dumbbell rotates 1:1 with the forearm's curl arc!
    for db_id in (db_top_id, db_bot_id):
        key_double(db_id, 13, lambda p: p[hand_k][0])
        key_double(db_id, 14, lambda p: p[hand_k][1])
        key_double(db_id, 15, lambda p: p[fa_ang_k])

    p0 = POSES[0]

    # Muscle activation intensity: remains visibly warm orange (0.48) at bottom extension so all 3 target
    # muscles are clearly visible in the Right Panel, and surges to intense crimson (1.0) at peak contraction!
    def biceps_t(p):
        return 0.46 + 0.54 * (p[curl_k] ** 0.80)

    def brachialis_t(p):
        return 0.50 + 0.50 * (p[curl_k] ** 0.75)

    def brachioradialis_t(p):
        return 0.52 + 0.48 * (p[curl_k] ** 0.75)

    # 1. Upper Arm, Biceps brachii (short + long head), Brachialis & Deltoid Cap
    # Local frame of UpperArm: +x runs from shoulder (0,0) to elbow (48,0).
    # Since ua_ang ~ +90 deg (pointing down), local +y is ANTERIOR (left/chest side) and local -y is POSTERIOR/LATERAL (right/outer side).
    ua_pts = [
        (-10, 0), (-8, 9.0), (6, 11.2), (22, 11.8), (37, 9.8), (45, 6.8),
        (50, 0), (45, -6.8), (32, -10.2), (17, -11.0), (3, -10.5), (-8, -8.0),
    ]
    # Target Muscle #1: Biceps brachii (short head = inner/anterior +y; long head = outer/central belly)
    biceps_short_pts = [
        (9, 4.0), (19, 9.2), (31, 10.0), (40, 8.0), (43, 4.4),
        (34, 3.4), (21, 3.0), (11, 2.6),
    ]
    biceps_long_pts = [
        (7, -0.8), (17, 4.2), (29, 5.2), (39, 3.8), (43, 0.8),
        (35, -1.8), (22, -2.2), (11, -1.8),
    ]
    # Target Muscle #2: Brachialis (fusiform muscle on the distal lateral upper arm between biceps long head and triceps)
    brachialis_pts = [
        (18, -1.6), (29, -0.3), (40, -0.6), (43, -3.6),
        (34, -6.8), (22, -6.0), (16, -3.6),
    ]
    # Sculpted Deltoid Cap overlapping the proximal humerus
    delt_pts = [
        (-13, 0.5), (-9, 10.5), (2, 12.2), (13, 8.8), (19, 1.5),
        (17, -6.5), (8, -11.2), (-3, -11.8), (-11, -8.0),
    ]
    delt_hi = [(-5, -5.5), (4, -7.2), (12, -4.0)]
    delt_feather = [(3, 9.5), (12, 6.0), (16, 0.0), (12, -6.0)]

    # 2. Forearm, Brachioradialis & Neutral-Grip (Hammer) Fist
    # Local frame of Forearm: +x runs from elbow (0,0) to hand (43,0).
    # Throughout the hammer curl arc (fa_ang from ~95 deg down to ~230 deg up-left),
    # the thumb/radial aspect (Brachioradialis) always sits on the +y_local side of the forearm!
    fa_pts = [
        (-6, 0), (-4, 7.6), (10, 9.4), (24, 7.4), (36, 5.2), (42, 4.2),
        (45, 0), (42, -4.2), (34, -5.0), (19, -7.0), (6, -7.8), (-4, -6.5),
    ]
    # Target Muscle #3: Brachioradialis (prominent thumb-side proximal/radial forearm belly along +y_local)
    brachioradialis_pts = [
        (-3, 0.5), (5, 7.2), (17, 7.8), (29, 5.4), (35, 2.8),
        (24, 1.0), (11, 0.2), (-1, -0.5),
    ]
    # Neutral-grip (thumbs-up) fist wrapping around the dumbbell handle at x = FOREARM_LEN (43.0)
    fist_pts = [
        (FOREARM_LEN - 5.5, -5.2), (FOREARM_LEN + 5.5, -4.8), (FOREARM_LEN + 6.8, 0.5),
        (FOREARM_LEN + 5.2, 5.8), (FOREARM_LEN - 5.5, 5.4),
    ]
    thumb_pts = [
        (FOREARM_LEN - 4.5, 3.8), (FOREARM_LEN + 3.5, 4.5),
        (FOREARM_LEN + 4.2, 7.8), (FOREARM_LEN - 3.5, 7.2),
    ]

    # 3. Heavy 3D Double-Plate Black Dumbbell oriented in NEUTRAL (Hammer) Grip
    # In the hand's local frame (rotated by `fa_ang_k`), +y_local is the thumb/top end of the dumbbell
    # and -y_local is the pinky/bottom end of the dumbbell, with 3/4 perspective offset along x_local.
    plate_face = (
        f'<Fill name="{prefix}PlateFaceFill">{grad3(prefix + "PlateFaceGrad", -18, 18, *PLATE_DARK, x0=-18, x1=18)}</Fill>'
        f'<Stroke thickness="1.15" name="{prefix}PlateFaceStroke"><SolidColor colorValue="FF475569" name="{prefix}PlateFaceStrokeCol"/></Stroke>'
    )
    plate_rim = (
        f'<Fill name="{prefix}PlateRimFill"><SolidColor colorValue="FF020617" name="{prefix}PlateRimCol"/></Fill>'
        f'<Stroke thickness="0.95" name="{prefix}PlateRimStroke"><SolidColor colorValue="FF1E293B" name="{prefix}PlateRimStrokeCol"/></Stroke>'
    )
    plate_groove = (
        f'<Stroke thickness="1.0" name="{prefix}PlateGrooveStroke"><SolidColor colorValue="FF334155" name="{prefix}PlateGrooveCol"/></Stroke>'
    )
    hub_paint = (
        f'<Fill name="{prefix}HubFill">{grad(prefix + "HubGrad", -5, -5, 5, 5, "FFE2E8F0", "FF475569")}</Fill>'
        f'<Stroke thickness="0.85" name="{prefix}HubStroke"><SolidColor colorValue="FF0F172A" name="{prefix}HubStrokeCol"/></Stroke>'
    )

    out = [f'{ind}<Node name="{prefix}ArmAndDumbbellGroup">']

    # Layer A (Foreground of Arm): Thumb-Side (+y_local) Double Plates of Dumbbell (drawn in front of the gripping fist)
    out.append(
        f'{i2}<Node x="{f(p0[hand_k][0])}" y="{f(p0[hand_k][1])}" '
        f'rotation="{f(p0[fa_ang_k])}" name="{prefix}DumbbellTopPlates" id="{db_top_id}">'
    )
    out.append(ellipse_shape(i3, f"{prefix}TopCollarHub", -5.2, 16.5, 10.0, 6.8, hub_paint, rot_deg=-16.0))
    out.append(ellipse_shape(i3, f"{prefix}TopOuterGroove", -4.2, 14.0, 26.5, 16.5, plate_groove, rot_deg=-16.0))
    out.append(ellipse_shape(i3, f"{prefix}TopOuterPlateFace", -4.2, 14.0, 37.5, 23.5, plate_face, rot_deg=-16.0))
    out.append(ellipse_shape(i3, f"{prefix}TopOuterPlateRim", -3.6, 12.2, 37.5, 23.5, plate_rim, rot_deg=-16.0))
    out.append(ellipse_shape(i3, f"{prefix}TopInnerPlateFace", -2.8, 9.4, 35.5, 22.0, plate_face, rot_deg=-16.0))
    out.append(ellipse_shape(i3, f"{prefix}TopInnerPlateRim", -2.2, 7.8, 35.5, 22.0, plate_rim, rot_deg=-16.0))
    out.append(f"{i2}</Node>")

    # Layer B: Forearm, Prominent Brachioradialis & Neutral-Grip (Hammer) Fist
    out.append(
        f'{i2}<Node x="{f(p0[el_k][0])}" y="{f(p0[el_k][1])}" '
        f'rotation="{f(p0[fa_ang_k])}" scaleX="{f(p0[fa_sc_k])}" name="{prefix}Forearm" id="{fa_id}">'
    )
    # Neutral-grip thumb & curled fingers gripping the handle
    out.append(smooth_shape(i3, f"{prefix}Thumb", thumb_pts, skin_fill(prefix + "Thumb", 3, 8, skin)))
    out.append(stroke_shape(i3, f"{prefix}Knuckle1", [(FOREARM_LEN - 2.5, -2.2), (FOREARM_LEN + 4.2, -2.0)], 0.95, SOFT_SHADOW, 0.0))
    out.append(stroke_shape(i3, f"{prefix}Knuckle2", [(FOREARM_LEN - 2.5, 0.8), (FOREARM_LEN + 4.5, 1.0)], 0.95, SOFT_SHADOW, 0.0))
    out.append(stroke_shape(i3, f"{prefix}Knuckle3", [(FOREARM_LEN - 2.5, 3.2), (FOREARM_LEN + 4.0, 3.4)], 0.95, SOFT_SHADOW, 0.0))
    out.append(smooth_shape(i3, f"{prefix}GrippingFist", fist_pts, skin_fill(prefix + "Fist", -6, 6, skin)))

    # Target Muscle #3: Brachioradialis on the thumb/radial aspect (+y_local) of the forearm
    if not far:
        out.append(stroke_shape(i3, f"{prefix}BrachioradialisFiber", [(4, 4.2), (16, 4.8), (28, 3.2)], 1.05, "737F1D1D", 0.4))
    out.append(
        smooth_shape(
            i3,
            f"{prefix}Brachioradialis",
            brachioradialis_pts,
            muscle_paint_fn(prefix + "Brachioradialis", brachioradialis_t, 0.95),
        )
    )
    if not far:
        out.append(stroke_shape(i3, f"{prefix}ForearmTendon", [(12, -1.2), (25, -1.5), (36, -1.0)], 1.15, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(8, -3.2), (22, -2.8), (34, -1.8)], 2.6, HIGHLIGHT, 3.0))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(6, -6.0), (22, -5.2), (34, -3.6)], 3.8, CORE_SHADOW, 4.0))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -8, 10, skin)))
    out.append(f"{i2}</Node>")

    # Layer C: Upper Arm, Deltoid Cap, Biceps brachii (Short + Long Head) & Brachialis
    out.append(
        f'{i2}<Node x="{f(sx)}" y="{f(sy)}" rotation="{f(p0[ua_ang_k])}" scaleX="{f(p0[ua_sc_k])}" name="{prefix}UpperArm" id="{ua_id}">'
    )
    # Deltoid cap on top of the proximal upper arm so biceps and brachialis emerge cleanly from underneath
    if not far:
        out.append(stroke_shape(i3, f"{prefix}DeltAnteriorGroove", delt_feather, 1.3, SOFT_SHADOW, 1.2))
        out.append(stroke_shape(i3, f"{prefix}DeltHi", delt_hi, 3.2, HIGHLIGHT, 3.5))
    else:
        out.append(stroke_shape(i3, f"{prefix}DeltHi", [(-4, 6.0), (5, 7.8), (12, 5.0)], 2.6, "80FFFFFF", 3.0))
    out.append(smooth_shape(i3, f"{prefix}Deltoid", delt_pts, skin_fill(prefix + "Deltoid", -12, 13, skin)))

    # Target Muscle #1: Dynamic Biceps brachii group (scales along +y at peak contraction for realistic biceps peak)
    out.append(f'{i3}<Node scaleY="{f(p0[bic_peak_k])}" name="{prefix}BicepsPeak" id="{bic_id}">')
    if not far:
        out.append(stroke_shape(i4, f"{prefix}BicepsSeptum", [(12, 3.5), (26, 4.2), (38, 3.2)], 1.1, "737F1D1D", 0.5))
        out.append(stroke_shape(i4, f"{prefix}BicepsPeakHi", [(16, 5.2), (28, 6.2), (36, 4.8)], 2.0, "59FFFFFF", 2.2))
    out.append(smooth_shape(i4, f"{prefix}BicepsShortHead", biceps_short_pts, muscle_paint_fn(prefix + "BicepsShort", biceps_t, 0.9)))
    out.append(smooth_shape(i4, f"{prefix}BicepsLongHead", biceps_long_pts, muscle_paint_fn(prefix + "BicepsLong", biceps_t, 0.95)))
    out.append(f"{i3}</Node>")

    # Target Muscle #2: Brachialis (distal lateral upper arm between biceps long head and triceps)
    if not far:
        out.append(stroke_shape(i3, f"{prefix}BrachialisFiber", [(22, -3.2), (32, -3.4), (40, -2.5)], 1.0, "737F1D1D", 0.4))
    out.append(smooth_shape(i3, f"{prefix}Brachialis", brachialis_pts, muscle_paint_fn(prefix + "Brachialis", brachialis_t, 0.95)))
    if not far:
        out.append(stroke_shape(i3, f"{prefix}TricepsHi", [(14, -7.4), (30, -7.8), (41, -5.8)], 2.6, HIGHLIGHT, 3.2))
    out.append(stroke_shape(i3, f"{prefix}UpperArmSh", [(12, -9.2), (28, -9.5), (41, -7.2)], 4.5, CORE_SHADOW, 4.8))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UpperArm", -11, 12, skin)))
    out.append(f"{i2}</Node>")

    # Layer D (Background of Arm): Pinky-Side (-y_local) Double Plates & Chrome Handle Shaft (drawn behind the gripping fist)
    out.append(
        f'{i2}<Node x="{f(p0[hand_k][0])}" y="{f(p0[hand_k][1])}" '
        f'rotation="{f(p0[fa_ang_k])}" name="{prefix}DumbbellBottomPlates" id="{db_bot_id}">'
    )
    out.append(polyline_stroke_shape(i3, f"{prefix}HandleHi", [(2.5, -11.0), (-2.5, 11.0)], 1.4, "FFFFFFFF", radius=0.4))
    out.append(polyline_stroke_shape(i3, f"{prefix}HandleShaft", [(3.0, -12.0), (-3.0, 12.0)], 4.8, "FF94A3B8", radius=0.8))
    out.append(ellipse_shape(i3, f"{prefix}BottomInnerPlateFace", 2.8, -9.4, 35.0, 21.5, plate_face, rot_deg=-16.0))
    out.append(ellipse_shape(i3, f"{prefix}BottomInnerPlateRim", 3.4, -11.0, 35.0, 21.5, plate_rim, rot_deg=-16.0))
    out.append(ellipse_shape(i3, f"{prefix}BottomOuterGroove", 4.2, -14.0, 26.0, 16.0, plate_groove, rot_deg=-16.0))
    out.append(ellipse_shape(i3, f"{prefix}BottomOuterPlateFace", 4.2, -14.0, 37.0, 23.0, plate_face, rot_deg=-16.0))
    out.append(ellipse_shape(i3, f"{prefix}BottomOuterPlateRim", 4.8, -15.8, 37.0, 23.0, plate_rim, rot_deg=-16.0))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 2. Canonical Standing 3/4 Athlete Body (Exact Proportions from front_raise / bicep_curl_barbell)
def torso_and_head():
    """Standing 3/4 front-left torso, pectorals, sculpted 6-pack abs, compression shorts, and volumetric 3/4 head."""
    ind = "        "
    i2 = ind + "    "

    # Volumetric 3/4 head facing front-left (exact coordinates from front_raise / bicep_curl_barbell)
    head_pts = [
        (304.0, 50.0),  # upper forehead
        (301.5, 56.5),  # left brow ridge
        (300.0, 62.5),  # nose bridge & tip (facing left-front)
        (301.2, 67.5),  # upper lip / mouth
        (301.8, 73.5),  # strong chin tip
        (307.5, 76.5),  # under-chin / anterior jawline
        (316.5, 75.0),  # mandible angle (gonion)
        (323.5, 71.0),  # beneath ear / mastoid
        (328.5, 63.0),  # occiput / back of skull
        (328.0, 52.0),  # posterior crown
        (321.0, 45.0),  # top cranial dome
        (311.0, 45.0),  # anterior crown
    ]
    hair_pts = [
        (303.5, 52.0), (309.0, 44.5), (320.5, 44.2), (328.5, 50.5),
        (329.0, 61.5), (324.5, 65.5), (323.0, 57.5), (318.0, 52.5),
        (310.5, 51.0),
    ]
    head_hi = [(304.5, 54.0), (308.5, 49.0), (317.0, 48.0)]
    cheek_hi = [(303.5, 61.5), (309.5, 63.0), (315.0, 62.0)]
    jaw_sh = [(304.0, 75.5), (313.0, 76.2), (320.5, 72.5)]

    # Muscular neck & upper trapezius flare connecting into the clavicles
    neck_pts = [
        (306.5, 73.0), (322.5, 70.0), (334.0, 86.0),
        (338.0, 94.0), (296.0, 92.0), (304.0, 83.0),
    ]
    scm_line = [(320.0, 72.5), (315.5, 82.0), (312.5, 90.5)]

    # 3/4 Torso silhouette from clavicles (y=89) through slender waist (y=154) and pelvis (y=182)
    torso_pts = [
        (294.0, 91.0),   # far right clavicle
        (313.0, 89.0),   # suprasternal notch
        (344.0, 94.0),   # near left clavicle
        (346.0, 114.0),  # near lateral pec / lat border
        (340.0, 134.0),  # near serratus / external oblique taper
        (335.0, 154.0),  # near waist / iliac crest
        (338.0, 174.0),  # near outer hip
        (316.0, 182.0),  # pelvis base
        (294.0, 174.0),  # far outer hip
        (297.0, 152.0),  # far waist
        (296.0, 132.0),  # far oblique contour
        (292.0, 112.0),  # far lateral chest contour
    ]
    torso_hi = [(302.0, 98.0), (303.0, 122.0), (304.0, 146.0)]
    torso_sh = [(339.0, 116.0), (334.0, 138.0), (330.0, 154.0)]

    # Sculpted Near (left) and Far (right) Pectoralis Major plates
    pec_near_pts = [
        (312.5, 93.0), (336.0, 95.5), (342.0, 108.0),
        (337.5, 119.5), (324.0, 121.5), (312.0, 117.5),
    ]
    pec_far_pts = [
        (295.0, 93.5), (311.5, 93.0), (311.0, 117.0),
        (300.5, 119.0), (292.5, 112.5), (292.5, 101.0),
    ]
    pec_paint = (
        '<Fill name="PecFill"><SolidColor colorValue="120F172A" name="PecCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="PecStroke"><SolidColor colorValue="380F172A" name="PecStrokeCol"/></Stroke>'
    )

    # Sculpted 6-pack abs (verbatim from front_raise / bicep_curl_barbell)
    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1A0F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="AbsEdge"><SolidColor colorValue="400F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        [(313.0, 121.0), (325.0, 121.5), (325.5, 130.0), (312.8, 129.5)],
        [(312.6, 131.5), (324.8, 132.0), (324.2, 140.5), (312.4, 140.0)],
        [(312.2, 142.0), (323.5, 142.5), (322.0, 151.5), (312.0, 151.0)],
        [(301.5, 121.0), (310.5, 121.0), (310.3, 129.5), (301.2, 129.0)],
        [(301.2, 131.0), (310.2, 131.5), (310.0, 140.0), (301.2, 139.5)],
        [(301.5, 141.5), (309.8, 142.0), (309.5, 151.0), (302.0, 150.5)],
    ]

    # Athletic compression shorts over the pelvis (verbatim from front_raise / bicep_curl_barbell)
    pelvis_shorts = [
        (296.0, 153.0), (313.0, 155.0), (336.0, 154.0),
        (341.0, 176.0), (322.0, 186.0), (311.0, 184.0), (292.0, 176.0),
    ]

    out = [f'{ind}<Node name="TorsoAndHead">']

    # 1. Volumetric 3/4 Head (drawn on top of the neck)
    out.append(smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 304, 44, 329, 65, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i2, "Ear", 321.5, 64.5, 5.5, 8.5, solid("Ear", "FFA3B1C4"), rot_deg=12.0))
    out.append(stroke_shape(i2, "BrowShade", [(301.5, 56.8), (306.0, 57.2)], 1.4, "590F172A", 0.8))
    out.append(stroke_shape(i2, "EyeLine", [(303.2, 58.6), (306.2, 58.8)], 1.1, "730F172A", 0.4))
    out.append(stroke_shape(i2, "MouthLine", [(301.5, 68.5), (305.0, 68.8)], 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i2, "HeadHi", head_hi, 3.0, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i2, "CheekHi", cheek_hi, 2.2, "80FFFFFF", 2.5))
    out.append(stroke_shape(i2, "JawShadow", jaw_sh, 2.6, CORE_SHADOW, 2.5))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill("Head", 45, 77, SKIN, x0=300, x1=328)))

    # 2. Muscular Neck & Clavicles
    out.append(stroke_shape(i2, "UnderChinShadow", [(306.5, 76.5), (313.5, 77.5), (320.0, 74.5)], 3.2, CORE_SHADOW, 2.5))
    out.append(stroke_shape(i2, "SCMLine", scm_line, 1.5, SOFT_SHADOW, 1.5))
    out.append(stroke_shape(i2, "ClavicleLine", [(296.0, 92.5), (312.5, 92.0), (336.0, 94.5)], 1.5, SOFT_SHADOW, 1.2))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", 70, 94, SKIN)))

    # 3. Pelvis Shorts & Waistband
    out.append(stroke_shape(i2, "WaistbandLine", [(296.5, 155.5), (314.0, 157.5), (335.5, 156.5)], 1.8, "660F172A", 0.8))
    out.append(stroke_shape(i2, "ShortsFlyLine", [(312.0, 157.5), (311.5, 176.0)], 1.3, "660F172A", 0.8))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill("PelvisShorts", 153, 186, SHORTS)))

    # 4. Pectorals, 6-Pack Abs & Obliques
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "LineaAlba", [(312.0, 118.0), (311.5, 136.0), (311.0, 153.0)], 1.3, "470F172A", 0.8))
    out.append(stroke_shape(i2, "ObliqueLine1", [(336.0, 126.0), (330.0, 134.0), (326.0, 141.0)], 1.3, "380F172A", 1.0))
    out.append(stroke_shape(i2, "ObliqueLine2", [(334.0, 136.0), (328.0, 144.0), (324.0, 150.0)], 1.3, "380F172A", 1.0))
    out.append(stroke_shape(i2, "PecNearLowerSh", [(312.5, 118.0), (324.5, 122.0), (338.0, 119.5)], 2.4, CORE_SHADOW, 2.0))
    out.append(stroke_shape(i2, "PecFarLowerSh", [(293.0, 113.0), (301.0, 119.5), (311.0, 117.5)], 2.2, CORE_SHADOW, 2.0))
    out.append(stroke_shape(i2, "PecNearHi", [(316.0, 99.0), (328.0, 100.5), (337.0, 105.0)], 2.8, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i2, "PecNear", pec_near_pts, pec_paint))
    out.append(smooth_shape(i2, "PecFar", pec_far_pts, pec_paint))

    # 5. Torso Base
    out.append(stroke_shape(i2, "TorsoHi", torso_hi, 4.5, HIGHLIGHT, 4.5))
    out.append(stroke_shape(i2, "TorsoSh", torso_sh, 6.0, CORE_SHADOW, 5.5))
    out.append(smooth_shape(i2, "Torso", torso_pts, skin_fill("Torso", 89, 182, SKIN, x0=294, x1=346)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def near_leg():
    """Near (left) leg planted on FLOOR=300 in 3/4 view (verbatim from front_raise / bicep_curl_barbell)."""
    ind = "        "
    i2 = ind + "    "

    shorts_pts = [
        (313.0, 168.0), (339.5, 166.0), (344.5, 192.0),
        (315.5, 194.0), (312.0, 178.0),
    ]
    thigh_pts = [
        (315.0, 174.0), (340.0, 172.0), (346.5, 196.0),
        (343.0, 218.0), (338.0, 232.0), (322.0, 232.0),
        (317.5, 214.0), (314.5, 194.0),
    ]
    thigh_hi = [(324.0, 192.0), (325.0, 210.0), (326.0, 224.0)]
    thigh_sh = [(341.0, 192.0), (340.0, 212.0), (336.0, 228.0)]
    quad_med_line = [(324.0, 200.0), (321.0, 214.0), (324.0, 225.0)]
    quad_lat_line = [(335.0, 194.0), (336.5, 212.0), (333.5, 226.0)]

    shin_pts = [
        (322.5, 230.0), (338.0, 230.0), (346.5, 248.0),
        (345.0, 266.0), (339.5, 288.0), (328.5, 289.0),
        (325.0, 268.0), (322.0, 248.0),
    ]
    shin_hi = [(327.0, 240.0), (328.5, 262.0), (330.0, 282.0)]
    shin_sh = [(342.0, 246.0), (341.5, 264.0), (337.5, 284.0)]
    calf_cut = [(334.0, 246.0), (338.5, 258.0), (335.5, 270.0)]

    foot_pts = [
        (328.5, 286.0), (340.0, 286.0), (343.5, 297.5),
        (334.0, 300.5), (314.0, 301.5), (309.5, 297.5),
        (316.0, 292.5),
    ]

    return "\n".join([
        f'{ind}<Node name="NearLeg">',
        stroke_shape(i2, "NearShortsHem", [(315.5, 192.5), (329.5, 193.0), (344.0, 190.5)], 1.6, "660F172A", 0.6),
        smooth_shape(i2, "NearThighShorts", shorts_pts, skin_fill("NearThighShorts", 166, 194, SHORTS)),
        stroke_shape(i2, "NearQuadMedLine", quad_med_line, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearQuadLatLine", quad_lat_line, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearThighHi", thigh_hi, 4.0, HIGHLIGHT, 4.0),
        stroke_shape(i2, "NearThighSh", thigh_sh, 5.2, CORE_SHADOW, 5.0),
        smooth_shape(i2, "NearThigh", thigh_pts, skin_fill("NearThigh", 172, 232, SKIN)),
        ellipse_shape(i2, "NearKnee", 329.5, 231.0, 16.5, 15.0, skin_fill("NearKnee", -8, 8, SKIN)),
        stroke_shape(i2, "NearFootHi", [(329.0, 290.0), (319.0, 295.0), (312.5, 298.0)], 2.2, HIGHLIGHT, 2.5),
        smooth_shape(i2, "NearFoot", foot_pts, skin_fill("NearFoot", 286, 302, SKIN)),
        stroke_shape(i2, "NearCalfCut", calf_cut, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearShinHi", shin_hi, 3.2, HIGHLIGHT, 3.5),
        stroke_shape(i2, "NearShinSh", shin_sh, 4.5, CORE_SHADOW, 4.5),
        smooth_shape(i2, "NearShin", shin_pts, skin_fill("NearShin", 230, 289, SKIN)),
        f"{ind}</Node>",
    ])


def far_leg():
    """Far (right) leg planted slightly further back-left in 3/4 perspective (verbatim from front_raise / bicep_curl_barbell)."""
    ind = "        "
    i2 = ind + "    "

    shorts_pts = [
        (292.0, 166.0), (315.0, 168.0), (314.0, 190.0),
        (289.5, 188.0),
    ]
    thigh_pts = [
        (291.0, 172.0), (314.0, 174.0), (313.0, 198.0),
        (309.5, 224.0), (294.5, 224.0), (289.5, 204.0),
        (288.0, 186.0),
    ]
    thigh_hi = [(294.5, 188.0), (295.5, 206.0), (297.0, 220.0)]
    thigh_sh = [(309.0, 190.0), (308.0, 208.0), (306.0, 222.0)]
    quad_line = [(302.5, 192.0), (303.5, 208.0), (301.5, 220.0)]

    shin_pts = [
        (295.0, 222.0), (309.5, 222.0), (316.0, 242.0),
        (314.5, 260.0), (309.5, 281.0), (299.0, 282.0),
        (296.5, 260.0), (294.5, 242.0),
    ]
    shin_hi = [(298.5, 232.0), (299.5, 254.0), (301.0, 274.0)]
    shin_sh = [(312.0, 240.0), (311.0, 258.0), (307.5, 276.0)]

    foot_pts = [
        (299.0, 279.0), (310.0, 279.0), (313.0, 289.5),
        (303.0, 292.5), (284.0, 293.5), (279.5, 289.5),
        (286.5, 285.0),
    ]

    return "\n".join([
        f'{ind}<Node name="FarLeg">',
        smooth_shape(i2, "FarThighShorts", shorts_pts, skin_fill("FarThighShorts", 166, 190, SHORTS_FAR)),
        stroke_shape(i2, "FarQuadLine", quad_line, 1.2, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "FarThighHi", thigh_hi, 3.4, HIGHLIGHT, 3.5),
        stroke_shape(i2, "FarThighSh", thigh_sh, 4.6, CORE_SHADOW, 4.5),
        smooth_shape(i2, "FarThigh", thigh_pts, skin_fill("FarThigh", 172, 224, SKIN_FAR)),
        ellipse_shape(i2, "FarKnee", 301.5, 223.5, 15.5, 14.0, skin_fill("FarKnee", -7, 7, SKIN_FAR)),
        smooth_shape(i2, "FarFoot", foot_pts, skin_fill("FarFoot", 279, 294, SKIN_FAR)),
        stroke_shape(i2, "FarShinHi", shin_hi, 2.8, HIGHLIGHT, 3.0),
        stroke_shape(i2, "FarShinSh", shin_sh, 4.0, CORE_SHADOW, 4.0),
        smooth_shape(i2, "FarShin", shin_pts, skin_fill("FarShin", 222, 282, SKIN_FAR)),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 3. Scene Assembly (RML First Child = Topmost Layer)
def build_rml():
    global _id
    _id = 0
    KEYED.clear()

    near_arm_xml = hammer_curl_arm_rig("Near", False)
    torso_head_xml = torso_and_head()
    near_leg_xml = near_leg()
    far_leg_xml = far_leg()
    far_arm_xml = hammer_curl_arm_rig("Far", True)

    grouped = {}
    for oid, kxml in KEYED:
        grouped.setdefault(oid, []).append(kxml)
    keyed_objects_xml = "\n".join(
        f'        <KeyedObject objectId="{oid}">\n' + "\n".join(props) + "\n        </KeyedObject>"
        for oid, props in grouped.items()
    )

    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"

    return f"""<Rive version="7.3">
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="HammerCurl" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Left) Arm (Biceps brachii, Brachialis, Brachioradialis) & Neutral-Grip Black Dumbbell -->
{near_arm_xml}

        <!-- 2. Canonical Standing 3/4 Athlete Torso, Pectorals, 6-Pack Abs & Volumetric Head -->
{torso_head_xml}

        <!-- 3. Near (Left) Standing Leg on Floor -->
{near_leg_xml}

        <!-- 4. Far (Right) Standing Leg in 3/4 Depth -->
{far_leg_xml}

        <!-- 5. Background: Far (Right) Arm (Biceps brachii, Brachialis, Brachioradialis) & Neutral-Grip Black Dumbbell -->
{far_arm_xml}

        <!-- 6. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="314" y="{f(FLOOR - 2)}" scaleX="0.82" scaleY="0.09" name="BodyShadow">
            <Ellipse width="190" height="190" name="BodyShadowEllipse"/>
            <Fill name="BodyShadowFill"><RadialGradient startX="0" startY="0" endX="95" endY="0" name="BodyShadowGrad">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="HammerCurl" id="0:60">
{keyed_objects_xml}
        </LinearAnimation>
    </Artboard>
</Rive>
"""


# ---------------------------------------------------------------- Verbatim Rive 7.3 Binary Compiler (52-byte TOC)
def _compile_rml_bytes(rml_path):
    """Byte-for-byte Rive 7.3 binary compiler matching `~/.rive/bin/rive . --once`."""
    import struct

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
    import sys

    BUILD.mkdir(parents=True, exist_ok=True)
    riv_bytes = _compile_rml_bytes(OUT)
    riv_out = HERE / "hammer_curl.riv"
    riv_out.write_bytes(riv_bytes)

    repo = HERE.parent.parent
    riv_dest = repo / "assets/animations/hammer_curl.riv"
    thumb_dest = repo / "assets/animations/thumbnails/hammer_curl.png"
    riv_dest.write_bytes(riv_bytes)

    legacy_mk = repo / "assets/animations/hammer_curl.movekit"
    if legacy_mk.exists():
        legacy_mk.unlink()

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png

    for fr, tag in ((0, "frame_start"), (38, "frame_mid"), (74, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_start":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(680, 20, 250))
            write_png(thumb_dest, 256, 256, thumb_rgb)

    print("published", riv_dest, thumb_dest)


if __name__ == "__main__":
    import sys
    xml = build_rml()
    OUT.write_text(xml)
    print("keyed props:", len(KEYED), "bytes:", len(xml))
    if "--publish" in sys.argv:
        publish()
