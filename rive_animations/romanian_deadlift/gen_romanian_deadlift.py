#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360, FLOOR = 300.0) procedural Rive 7.3 scene for Romanian Deadlift (id: 'romanian_deadlift').

3/4 dorso-lateral view of our canonical CommunityFitness athlete performing a Barbell Romanian Deadlift (RDL):
  - Top Standing Lockout (f = 0 & f = 168, r = 0.0):
    * Athlete stands tall in a 3/4 stance on FLOOR = 300.0 holding a loaded Olympic barbell
      (chrome bar + 3D multi-plate black cast-iron weight stacks on both ends) across the upper thighs
      with straight hanging arms.
  - Bottom Hip-Hinge Stretch (f = 78, r = 1.0):
    * Athlete performs a deep hip hinge by driving the pelvis and glutes backward while maintaining
      a soft ~18 deg knee bend (nearly vertical shins) and a flat neutral spine (~22 deg above horizontal),
      sliding the barbell close along the shins to mid-shin height (plates suspended above the floor).
  - Highlighted Target & Synergist Muscle Groups (pulsing from warm orange #FFF97316 to intense crimson #FFF43F5E):
    1. Hamstrings (Biceps femoris & Semitendinosus — primary posterior thigh hip extensors)
    2. Gluteus maximus & Gluteus medius (Primary — posterior pelvis hip extensors visible through athletic shorts)
    3. Erector spinae & Upper-back stabilizers (Synergists — lumbar/thoracic paraspinal columns & middle/lower trapezius)

Run:
    python3 rive_animations/romanian_deadlift/gen_romanian_deadlift.py            # writes scene.rml
    python3 rive_animations/romanian_deadlift/gen_romanian_deadlift.py --publish  # compiles .riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/romanian_deadlift.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/romanian_deadlift.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 168  # 2.8s seamless 60fps loop
STEP = 2

# Stationary ankle anchors on FLOOR = 300.0 (3/4 stance facing forward-left)
ANKLE_NEAR = (296.0, 286.0)
ANKLE_FAR = (330.0, 274.0)

# Canonical Limb Rest Lengths
SHIN_NEAR_LEN = 66.0
THIGH_NEAR_LEN = 74.0
SHIN_FAR_LEN = 66.0
THIGH_FAR_LEN = 72.0
TORSO_LEN = 88.0
UPPER_ARM_LEN = 50.0
FOREARM_LEN = 46.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
TENDON = ("FFFFFFFF", "FFE2E8F0", "FFCBD5E1")
SHORTS_TRANSLUCENT = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR_TRANSLUCENT = ("FF334155", "FF1E293B", "FF0F172A")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
ANATOMY_LINE = "520F172A"

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


EASE_HINGE = cubic_bezier(0.40, 0.0, 0.32, 1.0)
EASE_PULL = cubic_bezier(0.34, 0.0, 0.22, 1.0)


def rdl_progress(frame):
    """Returns Romanian Deadlift hip-hinge progress r in [0.0, 1.0] across 168 frames:
    - 0..14:    Top standing lockout hold (r = 0.0)
    - 14..70:   Controlled eccentric hip-hinge descent to mid-shin (r: 0.0 -> 1.0)
    - 70..88:   Bottom hamstring stretch hold at mid-shin (r = 1.0)
    - 88..152:  Powerful concentric hip-extension drive to standing lockout (r: 1.0 -> 0.0)
    - 152..168: Top standing lockout hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 14:
        return 0.0
    if fr <= 70:
        return EASE_HINGE((fr - 14) / 56.0)
    if fr <= 88:
        return 1.0
    if fr <= 152:
        return 1.0 - EASE_PULL((fr - 88) / 64.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def quad_interp_pt(p0, p_mid, p1, r):
    """Smooth quadratic Lagrange interpolation through p0 (r=0), p_mid (r=0.5), and p1 (r=1.0)."""
    l0 = (1.0 - r) * (1.0 - 2.0 * r)
    l1 = 4.0 * r * (1.0 - r)
    l2 = r * (2.0 * r - 1.0)
    return (
        l0 * p0[0] + l1 * p_mid[0] + l2 * p1[0],
        l0 * p0[1] + l1 * p_mid[1] + l2 * p1[1],
    )


def seg_xform(p0, p1, base_len):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ang = math.atan2(dy, dx)
    if ang < 0:
        ang += 2.0 * math.pi
    sc = max(0.50, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute 3/4 Barbell Romanian Deadlift (RDL) joint transforms at progress r in [0.0, 1.0].
    - r = 0.0: Top standing lockout with loaded barbell across upper thighs.
    - r = 1.0: Deep hip-hinge stretch with pelvis pushed back, soft ~18 deg knee bend,
               flat neutral spine (~22 deg above horizontal), and barbell at mid-shin.
    """
    # 1. Knees: Soft ~15 deg knee bend while shins stay nearly vertical (pure hip hinge, not a squat)
    knee_near = quad_interp_pt((292.0, 222.0), (291.0, 222.5), (290.0, 223.0), r)
    knee_far = quad_interp_pt((322.0, 210.0), (321.0, 210.5), (320.0, 211.0), r)

    # 2. Hips / Pelvis: Tall over ankles at r=0.0 -> Driven far backward-right (+X) at r=1.0
    hip_near = quad_interp_pt((300.0, 156.0), (330.0, 161.0), (354.0, 168.0), r)
    hip_far = quad_interp_pt((318.0, 147.0), (348.0, 152.0), (372.0, 158.0), r)

    # 3. Shoulders & Dorsal Torso: Tall upright (~85 deg) at r=0.0 -> Hinged flat spine (~18 deg) at r=1.0
    sh_near = quad_interp_pt((291.0, 70.0), (277.0, 102.0), (269.0, 140.0), r)
    sh_far = quad_interp_pt((324.0, 62.0), (310.0, 93.0), (303.0, 128.0), r)

    # 4. 3D Olympic Barbell Center & Hands Locked to Bar Shaft
    #    Slides closely down the thighs and shins from upper thigh (y=156) to mid-shin (y=222),
    #    keeping the multi-plate stacks suspended above FLOOR=300 at r=1.0!
    bar_center = quad_interp_pt((281.0, 156.0), (276.0, 190.0), (272.0, 222.0), r)
    hand_near = (bar_center[0] - 25.0, bar_center[1] + 8.5)
    hand_far = (bar_center[0] + 25.0, bar_center[1] - 8.5)

    # 5. Straight Hanging Arms under heavy barbell load
    elb_near = (
        lerp(sh_near[0], hand_near[0], 0.52) - lerp(3.2, 2.5, r),
        lerp(sh_near[1], hand_near[1], 0.52),
    )

    # 6. Segment transforms
    shin_near_ang, shin_near_sc = seg_xform(knee_near, ANKLE_NEAR, SHIN_NEAR_LEN)
    thigh_near_ang, thigh_near_sc = seg_xform(hip_near, knee_near, THIGH_NEAR_LEN)
    shin_far_ang, shin_far_sc = seg_xform(knee_far, ANKLE_FAR, SHIN_FAR_LEN)
    thigh_far_ang, thigh_far_sc = seg_xform(hip_far, knee_far, THIGH_FAR_LEN)
    torso_ang, torso_sc = seg_xform(hip_near, sh_near, TORSO_LEN)
    ua_near_ang, ua_near_sc = seg_xform(sh_near, elb_near, UPPER_ARM_LEN)
    fa_near_ang, fa_near_sc = seg_xform(elb_near, hand_near, FOREARM_LEN)

    # 7. Neutral cervical spine alignment throughout the hip hinge
    neck_local = math.radians(lerp(6.0, 14.0, r))
    bar_shadow_sx = lerp(0.92, 1.16, r)

    return {
        "r": r,
        "knee_near": knee_near,
        "knee_far": knee_far,
        "hip_near": hip_near,
        "hip_far": hip_far,
        "sh_near": sh_near,
        "sh_far": sh_far,
        "bar_center": bar_center,
        "hand_near": hand_near,
        "hand_far": hand_far,
        "elb_near": elb_near,
        "shin_near_ang": shin_near_ang,
        "shin_near_sc": shin_near_sc,
        "thigh_near_ang": thigh_near_ang,
        "thigh_near_sc": thigh_near_sc,
        "shin_far_ang": shin_far_ang,
        "shin_far_sc": shin_far_sc,
        "thigh_far_ang": thigh_far_ang,
        "thigh_far_sc": thigh_far_sc,
        "torso_ang": torso_ang,
        "torso_sc": torso_sc,
        "ua_near_ang": ua_near_ang,
        "fa_near_ang": fa_near_ang,
        "ua_near_sc": ua_near_sc,
        "fa_near_sc": fa_near_sc,
        "neck_local": neck_local,
        "bar_shadow_sx": bar_shadow_sx,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(rdl_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = (
    "shin_near_ang",
    "thigh_near_ang",
    "shin_far_ang",
    "thigh_far_ang",
    "torso_ang",
    "ua_near_ang",
    "fa_near_ang",
    "neck_local",
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


def skin_fill_outlined(name, y0, y1, tones=SKIN, x0=0, x1=0, line=1.0, stroke_col="400F172A"):
    return (
        f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *tones, x0=x0, x1=x1)}</Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{stroke_col}" name="{name}EdgeCol"/></Stroke>'
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


def muscle_paint_fn(name, fn_t, line=1.05):
    fid, lid = nid(), nid()
    key_color(fid, 37, lambda p: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, fn_t(p)))
    key_color(lid, 37, lambda p: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, fn_t(p)))
    t0 = fn_t(POSES[0])
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- 1. 3D Multi-Plate Olympic Barbell Builders
def barbell_layers():
    """Returns (near_plate_xml, mid_shaft_xml, far_plate_xml) for a 3D multi-plate Olympic barbell
    (stepped 45-lb, 25-lb, and 10-lb black cast-iron weight plates + chrome collars & sleeves)."""
    ind = "        "
    i2 = ind + "    "
    p0 = POSES[0]

    def bar_node(name):
        bid = nid()
        key_double(bid, 13, lambda p: p["bar_center"][0])
        key_double(bid, 14, lambda p: p["bar_center"][1])
        return bid, f'{ind}<Node x="{f(p0["bar_center"][0])}" y="{f(p0["bar_center"][1])}" name="{name}" id="{bid}">'

    prot = -12.0
    near_plate_face = (
        f'<Fill name="NearPlateFaceFill">{grad3("NearPlateFaceGrad", -44, 44, "FF334155", "FF182232", "FF090D16", x0=-24, x1=24)}</Fill>'
        '<Stroke thickness="1.4" join="round" name="NearPlateRimStroke"><SolidColor colorValue="FF475569" name="NearPlateRimCol"/></Stroke>'
    )
    near_plate_rim = f'<Fill name="NearPlateBackFill">{grad("NearPlateBackGrad", -26, -44, 26, 44, "FF0F172A", "FF020617")}</Fill>'
    near_ring_paint = (
        '<Fill name="NearRingFill"><SolidColor colorValue="FF111827" name="NearRingCol"/></Fill>'
        '<Stroke thickness="1.2" join="round" name="NearRingStroke"><SolidColor colorValue="FF334155" name="NearRingStrokeCol"/></Stroke>'
    )
    hub_paint = (
        f'<Fill name="NearHubFill">{grad3("NearHubGrad", -9, 9, "FFE2E8F0", "FF64748B", "FF1E293B")}</Fill>'
        '<Stroke thickness="1.1" join="round" name="NearHubStroke"><SolidColor colorValue="FFCBD5E1" name="NearHubStrokeCol"/></Stroke>'
    )

    # --- Layer A (Frontmost): Near-Left Stepped Multi-Plate Stack (45-lb + 25-lb + 10-lb), Collar & Sleeve ---
    _, near_open = bar_node("NearBarbellPlateAndSleeve")
    sleeve_pts = [(-74.0, 22.0), (-114.0, 35.6), (-116.0, 41.8), (-76.0, 28.2)]
    sleeve_fill = f'<Fill name="NearSleeveFill">{grad3("NearSleeveGrad", 22, 42, "FFCBD5E1", "FF64748B", "FF0F172A")}</Fill>'
    left_shaft_pts = [(-25.0, 5.8), (-56.0, 16.4), (-57.6, 21.6), (-26.6, 11.0)]
    shaft_fill = f'<Fill name="LeftShaftFill">{grad3("LeftShaftGrad", 5, 22, "FFE2E8F0", "FF64748B", "FF1E293B")}</Fill>'

    near_xml = "\n".join([
        near_open,
        # 1. Protruding outer chrome bar sleeve & spinlock collar
        ellipse_shape(i2, "NearSleeveEndCap", -115.0, 38.7, 4.8, 7.2, solid("NearCap", "FF0F172A"), rot_deg=prot),
        ellipse_shape(i2, "NearSleeveEndRim", -115.0, 38.7, 6.2, 8.6, solid("NearCapRim", "FF94A3B8"), rot_deg=prot),
        stroke_shape(i2, "NearSleeveHi", [(-76.0, 24.0), (-96.0, 30.8), (-113.0, 36.6)], 1.6, "CCE2E8F0", 0.5),
        poly_shape(i2, "NearOuterSleeve", sleeve_pts, sleeve_fill, radius=1.2),
        ellipse_shape(i2, "NearOuterCollar", -77.5, 26.3, 10.5, 16.5, hub_paint, rot_deg=prot),
        # 2. Outer 10-lb Plate (-73.0, 24.8)
        ellipse_shape(i2, "NearPlate3Face", -73.0, 24.8, 34.0, 56.0, near_plate_face, rot_deg=prot),
        ellipse_shape(i2, "NearPlate3Rim", -69.5, 23.6, 34.0, 56.0, near_plate_rim, rot_deg=prot),
        # 3. Middle 25-lb Plate (-67.0, 22.8)
        ellipse_shape(i2, "NearPlate2Inner", -67.0, 22.8, 32.0, 52.0, near_ring_paint, rot_deg=prot),
        ellipse_shape(i2, "NearPlate2Face", -67.0, 22.8, 44.0, 72.0, near_plate_face, rot_deg=prot),
        ellipse_shape(i2, "NearPlate2Rim", -63.0, 21.4, 44.0, 72.0, near_plate_rim, rot_deg=prot),
        # 4. Inner 45-lb Plate (-60.0, 20.4)
        ellipse_shape(i2, "NearPlate1Inner", -60.0, 20.4, 40.0, 65.0, near_ring_paint, rot_deg=prot),
        ellipse_shape(i2, "NearPlate1Face", -60.0, 20.4, 54.0, 88.0, near_plate_face, rot_deg=prot),
        ellipse_shape(i2, "NearPlate1Rim", -55.5, 18.9, 54.0, 88.0, near_plate_rim, rot_deg=prot),
        # 5. Inner collar & left bar shaft into HAND_NEAR
        ellipse_shape(i2, "NearInnerCollar", -53.0, 18.0, 8.2, 13.0, hub_paint, rot_deg=prot),
        stroke_shape(i2, "LeftShaftHi", [(-26.0, 7.2), (-40.0, 12.0), (-53.0, 16.5)], 1.4, "CCE2E8F0", 0.4),
        poly_shape(i2, "LeftBarShaft", left_shaft_pts, shaft_fill, radius=1.0),
        f"{ind}</Node>",
    ])

    # --- Layer B (Midground): Inner Chrome Barbell Shaft from HAND_NEAR (-25, +8.5) to Far Stack (+56, -19.0) ---
    _, mid_open = bar_node("MidBarbellShaft")
    mid_shaft_pts = [(-25.0, 5.8), (56.0, -21.6), (57.6, -16.4), (-23.4, 11.0)]
    mid_shaft_fill = f'<Fill name="MidShaftFill">{grad3("MidShaftGrad", -22, 11, "FFE2E8F0", "FF64748B", "FF1E293B")}</Fill>'
    mid_xml = "\n".join([
        mid_open,
        stroke_shape(i2, "MidShaftHi", [(-24.0, 7.0), (16.0, -6.5), (54.0, -19.4)], 1.5, "CCE2E8F0", 0.4),
        poly_shape(i2, "MidBarShaft", mid_shaft_pts, mid_shaft_fill, radius=1.0),
        f"{ind}</Node>",
    ])

    # --- Layer C (Background): Far-Right Multi-Plate Stack behind Far Leg ---
    _, far_open = bar_node("FarBarbellPlate")
    far_plate_face = (
        f'<Fill name="FarPlateFaceFill">{grad3("FarPlateFaceGrad", -40, 40, "FF263244", "FF111827", "FF060911", x0=-22, x1=22)}</Fill>'
        '<Stroke thickness="1.3" join="round" name="FarPlateRimStroke"><SolidColor colorValue="FF334155" name="FarPlateRimCol"/></Stroke>'
    )
    far_plate_rim = f'<Fill name="FarPlateBackFill">{grad("FarPlateBackGrad", -24, -40, 24, 40, "FF090D16", "FF020617")}</Fill>'
    far_xml = "\n".join([
        far_open,
        ellipse_shape(i2, "FarInnerCollar", 50.5, -17.1, 8.0, 12.5, hub_paint, rot_deg=prot),
        ellipse_shape(i2, "FarPlate1Inner", 57.0, -19.4, 36.0, 58.0, near_ring_paint, rot_deg=prot),
        ellipse_shape(i2, "FarPlate1Face", 57.0, -19.4, 50.0, 82.0, far_plate_face, rot_deg=prot),
        ellipse_shape(i2, "FarPlate1Rim", 61.0, -20.8, 50.0, 82.0, far_plate_rim, rot_deg=prot),
        ellipse_shape(i2, "FarPlate2Face", 64.0, -21.8, 40.0, 66.0, far_plate_face, rot_deg=prot),
        ellipse_shape(i2, "FarPlate2Rim", 67.5, -23.0, 40.0, 66.0, far_plate_rim, rot_deg=prot),
        ellipse_shape(i2, "FarPlate3Face", 70.0, -23.8, 30.0, 50.0, far_plate_face, rot_deg=prot),
        f"{ind}</Node>",
    ])

    return near_xml, mid_xml, far_xml


# ---------------------------------------------------------------- 2. Near & Far Leg Builders (Hamstrings Highlighted, Quads/Calves Silver-Slate)
def leg_rig(prefix, far):
    """3/4 rear-left leg rig with glowing posterior Hamstrings (Biceps femoris & Semitendinosus),
    white lateral IT Band, and sculpted silver-slate Quadriceps & Gastrocnemius/Soleus calves."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    shorts_tones = SHORTS_FAR_TRANSLUCENT if far else SHORTS_TRANSLUCENT
    hip_key = "hip_far" if far else "hip_near"
    knee_key = "knee_far" if far else "knee_near"
    th_ang_key = "thigh_far_ang" if far else "thigh_near_ang"
    th_sc_key = "thigh_far_sc" if far else "thigh_near_sc"
    sh_ang_key = "shin_far_ang" if far else "shin_near_ang"
    sh_sc_key = "shin_far_sc" if far else "shin_near_sc"
    ankle_pt = ANKLE_FAR if far else ANKLE_NEAR
    m_scale = 0.88 if far else 1.00

    th_id, sh_id = nid(), nid()
    key_double(th_id, 13, lambda p: p[hip_key][0])
    key_double(th_id, 14, lambda p: p[hip_key][1])
    key_double(th_id, 15, lambda p: p[th_ang_key])
    key_double(th_id, 16, lambda p: p[th_sc_key])

    key_double(sh_id, 13, lambda p: p[knee_key][0])
    key_double(sh_id, 14, lambda p: p[knee_key][1])
    key_double(sh_id, 15, lambda p: p[sh_ang_key])
    key_double(sh_id, 16, lambda p: p[sh_sc_key])
    p0 = POSES[0]

    def hamstring_t(p):
        return (0.48 + 0.52 * (p["r"] ** 0.72)) * m_scale

    ax, ay = ankle_pt
    foot_pts = [
        (ax - 7, ay - 3),
        (ax - 22, ay + 3),
        (ax - 38, ay + 6),
        (ax - 44, ay + 8),
        (ax - 42, ay + 12),
        (ax - 24, ay + 12),
        (ax - 10, ay + 11),
        (ax + 6, ay + 12),
        (ax + 10, ay + 7),
        (ax + 7, ay - 2),
    ]

    shin_pts = [
        (-8, 0), (-6, 8.5), (12, 9.2), (34, 8.0), (54, 6.2), (65, 5.2),
        (69, 0), (64, -5.8), (48, -7.2), (30, -14.2), (14, -15.5), (2, -11.5), (-6, -7.5),
    ]
    achilles_pts = [
        (28, -9.5), (44, -6.8), (64, -5.5), (66, 1.5), (48, 1.0), (34, -2.5),
    ]

    x_prox = 0 if far else -16
    x_prox_in = 2 if far else -12
    thigh_pts = [
        (x_prox, 0), (x_prox_in, 14.5), (10, 18.8), (34, 18.2), (56, 13.8), (70, 9.2),
        (78, 0), (69, -9.2), (50, -13.5), (28, -17.2), (8, -18.5), (x_prox_in, -14.5),
    ]
    # Primary Target Muscle: Hamstrings (Biceps Femoris long/short head & Semitendinosus along -Y posterior thigh)
    biceps_femoris_pts = [
        (4, -2.8), (26, -2.4), (50, -2.0), (67, -4.2),
        (58, -10.2), (34, -11.5), (10, -11.0), (2, -7.5),
    ]
    semitendinosus_pts = [
        (6, -10.5), (32, -11.0), (56, -9.8), (62, -11.5),
        (48, -14.2), (28, -17.5), (9, -18.2), (2, -13.5),
    ]
    it_band_pts = [
        (2, -3.2), (24, -2.6), (48, -2.0), (70, -1.8),
        (72, 4.0), (48, 3.8), (24, 3.4), (2, 3.0),
    ]
    shorts_thigh_pts = [
        (-16 if not far else -8, 0), (-12 if not far else -6, 15.0), (10, 18.8), (26, 18.2),
        (26, -17.2), (10, -18.8), (-12 if not far else -6, -15.5),
    ]
    glute_thigh_pts = [
        (-16 if not far else -10, -1.5), (2, -2.5), (18, -6.0),
        (16, -16.8), (-2, -18.8), (-16 if not far else -10, -10.5),
    ]

    def glute_thigh_t(p):
        return (0.46 + 0.54 * (p["r"] ** 0.74)) * m_scale

    thigh_out = [
        f'{ind}<Node x="{f(p0[hip_key][0])}" y="{f(p0[hip_key][1])}" '
        f'rotation="{f(p0[th_ang_key])}" scaleX="{f(p0[th_sc_key])}" name="{prefix}Thigh" id="{th_id}">'
    ]
    if not far:
        thigh_out.append(stroke_shape(i3, f"{prefix}GluteFiber1", [(-8, -7.5), (4, -9.5), (14, -11.5)], 1.1, "667F1D1D", 0.4))
    thigh_out.append(smooth_shape(i3, f"{prefix}GluteusMaximus", glute_thigh_pts, muscle_paint_fn(prefix + "GluteMax", glute_thigh_t, 1.05)))
    thigh_out.append(stroke_shape(i3, f"{prefix}ShortsHem", [(26, -16.8), (26, 0.0), (26, 17.8)], 1.6, "CC020617", 0.0))
    thigh_out.append(smooth_shape(i3, f"{prefix}ThighShorts", shorts_thigh_pts, skin_fill(prefix + "ThighShorts", -19, 19, shorts_tones)))
    if not far:
        thigh_out.append(stroke_shape(i3, f"{prefix}ITGroove", [(8, 0.4), (36, 0.8), (66, 1.0)], 1.2, "66475569", 0.4))
    thigh_out.append(smooth_shape(i3, f"{prefix}ITBand", it_band_pts, skin_fill_outlined(prefix + "ITBand", -4, 4, TENDON, line=0.9)))

    # Glowing Hamstrings (Biceps Femoris + Semitendinosus) with fiber striations
    if not far:
        thigh_out.append(stroke_shape(i3, f"{prefix}HamSplitLine", [(10, -10.5), (34, -10.8), (56, -9.5)], 1.25, "997F1D1D", 0.3))
        thigh_out.append(stroke_shape(i3, f"{prefix}HamFiberHi", [(14, -6.5), (36, -6.2), (56, -5.8)], 2.0, "59FFFFFF", 2.0))
        thigh_out.append(stroke_shape(i3, f"{prefix}QuadVastusGroove", [(12, 11.5), (36, 11.8), (58, 9.5)], 1.3, CORE_SHADOW, 0.8))
        thigh_out.append(stroke_shape(i3, f"{prefix}QuadHi", [(14, 7.8), (38, 8.2), (58, 6.8)], 2.8, HIGHLIGHT, 2.8))
    thigh_out.append(smooth_shape(i3, f"{prefix}Semitendinosus", semitendinosus_pts, muscle_paint_fn(prefix + "Semi", hamstring_t, 1.05)))
    thigh_out.append(smooth_shape(i3, f"{prefix}BicepsFemoris", biceps_femoris_pts, muscle_paint_fn(prefix + "BicepsFem", hamstring_t, 1.1)))
    thigh_out.append(smooth_shape(i3, f"{prefix}ThighSkin", thigh_pts, skin_fill_outlined(prefix + "Thigh", -18, 18, skin, line=1.1)))
    thigh_out.append(f"{ind}</Node>")

    shin_out = [f'{ind}<Node name="{prefix}ShinAndFootGroup">']
    shin_out.append(
        f'{i2}<Node x="{f(p0[knee_key][0])}" y="{f(p0[knee_key][1])}" '
        f'rotation="{f(p0[sh_ang_key])}" scaleX="{f(p0[sh_sc_key])}" name="{prefix}Shin" id="{sh_id}">'
    )
    if not far:
        shin_out.append(stroke_shape(i3, f"{prefix}GastrocGroove", [(8, -3.5), (24, -4.0), (40, -2.5)], 1.3, CORE_SHADOW, 0.8))
        shin_out.append(stroke_shape(i3, f"{prefix}CalfHi", [(10, -10.5), (28, -9.8)], 2.4, HIGHLIGHT, 2.4))
        shin_out.append(stroke_shape(i3, f"{prefix}ShinHi", [(10, 4.5), (36, 4.2), (56, 3.0)], 2.4, HIGHLIGHT, 2.4))
    shin_out.append(smooth_shape(i3, f"{prefix}AchillesTendon", achilles_pts, skin_fill_outlined(prefix + "Achilles", -9, 2, TENDON, line=0.85)))
    shin_out.append(smooth_shape(i3, f"{prefix}ShinSkin", shin_pts, skin_fill_outlined(prefix + "Shin", -15, 9, skin, line=1.1)))
    shin_out.append(f"{i2}</Node>")

    if not far:
        shin_out.append(stroke_shape(i2, f"{prefix}AnkleMalleolus", [(ax - 1, ay - 4), (ax + 1, ay + 2), (ax - 3, ay + 5)], 1.3, ANATOMY_LINE, 0.0))
        shin_out.append(stroke_shape(i2, f"{prefix}ToeCrease1", [(ax - 41, ay + 9), (ax - 36, ay + 9)], 1.0, ANATOMY_LINE, 0.0))
        shin_out.append(stroke_shape(i2, f"{prefix}ToeCrease2", [(ax - 39, ay + 11), (ax - 34, ay + 11)], 1.0, ANATOMY_LINE, 0.0))
    shin_out.append(smooth_shape(i2, f"{prefix}Foot", foot_pts, skin_fill_outlined(prefix + "Foot", ay - 3, ay + 12, skin, line=1.15)))
    shin_out.append(f"{ind}</Node>")

    return "\n".join(thigh_out), "\n".join(shin_out)


# ---------------------------------------------------------------- 3. Dorsal Torso, Glutes, Erector Spinae & 3/4 Head
def dorsal_torso_glutes_and_head():
    """3/4 rear-left Dorsal Torso with glowing Gluteus Maximus/Medius, Erector Spinae, and Upper-Back Stabilizers."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    torso_id, neck_id = nid(), nid()
    key_double(torso_id, 13, lambda p: p["hip_near"][0])
    key_double(torso_id, 14, lambda p: p["hip_near"][1])
    key_double(torso_id, 15, lambda p: p["torso_ang"])
    key_double(torso_id, 16, lambda p: p["torso_sc"])
    key_double(neck_id, 15, lambda p: p["neck_local"])
    p0 = POSES[0]

    def glute_t(p):
        return 0.46 + 0.54 * (p["r"] ** 0.74)

    def erector_t(p):
        return 0.42 + 0.52 * (p["r"] ** 0.78)

    torso_pts = [
        (-8, 18), (14, 21), (38, 28), (64, 34), (86, 29),
        (94, 8), (82, -17), (64, -20), (36, -15), (14, -15), (-8, -14),
    ]
    pelvis_shorts_pts = [
        (-13, 2), (-10, 17), (4, 20), (14, 19),
        (14, -14), (-8, -14), (-13, -6),
    ]
    glute_med_pts = [
        (-9, 3), (2, 4), (12, 8), (13, 18), (-2, 18), (-10, 12),
    ]

    # Target Muscle #3: Erector Spinae & Upper-Back Stabilizers (Middle/Lower Trapezius)
    erector_pts = [
        (14, 13), (38, 17), (64, 22), (62, 30), (36, 25), (14, 22),
    ]
    upper_back_trap_pts = [
        (56, 22), (76, 18), (86, 27), (70, 34), (54, 29),
    ]
    lat_pts = [
        (16, 5), (42, 3), (68, 2), (76, 15), (56, 23), (34, 18), (15, 14),
    ]
    scapula_near_pts = [
        (56, 12), (75, 9), (82, 19), (68, 24), (56, 20),
    ]

    neck_pts = [(-10, -9), (10, -8), (14, 11), (-10, 12)]
    head_pts = [
        (4, -9), (11, -17), (17, -17), (24, -19), (30, -16),
        (38, -12), (44, -1), (41, 11), (30, 16), (16, 14), (6, 9),
    ]
    hair_pts = [
        (35, -12), (43, -4), (45, 7), (38, 15),
        (24, 16), (16, 12), (20, 4), (27, -2), (32, -8),
    ]
    hair_paint = (
        f'<Fill name="HairFill">{grad("HairGrad", 45, -5, 16, 16, "FF334155", "FF0F172A")}</Fill>'
        '<Stroke thickness="1.0" join="round" name="HairStroke"><SolidColor colorValue="FF090D16" name="HairStrokeCol"/></Stroke>'
    )

    out = [
        f'{ind}<Node x="{f(p0["hip_near"][0])}" y="{f(p0["hip_near"][1])}" '
        f'rotation="{f(p0["torso_ang"])}" scaleX="{f(p0["torso_sc"])}" name="DorsalTorsoAndHead" id="{torso_id}">'
    ]

    # A. Pelvic Compression Shorts Cap & Gluteus Medius at Hip Crest
    out.append(stroke_shape(i2, "ShortsWaistband", [(13, -14), (13, 4), (13, 19)], 2.4, "E6090D16", 0.0, cap="butt"))
    out.append(smooth_shape(i2, "GluteusMedius", glute_med_pts, muscle_paint_fn("GluteMed", lambda p: glute_t(p) * 0.90, 1.0)))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts_pts, skin_fill("PelvisShorts", -14, 20, SHORTS_TRANSLUCENT)))

    # C. Dorsal Back Anatomy, Glowing Erector Spinae & Upper-Back Stabilizers
    out.append(stroke_shape(i2, "SpinalGroove", [(14, 21), (42, 25), (78, 28)], 1.6, "660F172A", 0.5))
    out.append(stroke_shape(i2, "LatBorderCrease", [(18, 8), (42, 7), (66, 6)], 1.4, ANATOMY_LINE, 0.3))
    out.append(stroke_shape(i2, "RibSerratus1", [(46, -4), (54, 1)], 1.2, ANATOMY_LINE, 0.0))
    out.append(stroke_shape(i2, "RibSerratus2", [(36, -5), (44, 0)], 1.2, ANATOMY_LINE, 0.0))
    out.append(smooth_shape(i2, "UpperBackTraps", upper_back_trap_pts, muscle_paint_fn("UpperBackTraps", lambda p: erector_t(p) * 0.88, 0.95)))
    out.append(smooth_shape(i2, "ErectorSpinae", erector_pts, muscle_paint_fn("ErectorSpinae", erector_t, 1.0)))
    out.append(smooth_shape(i2, "ScapulaNear", scapula_near_pts, skin_fill("ScapulaNear", 9, 24, SKIN)))
    out.append(smooth_shape(i2, "LatissimusDorsi", lat_pts, skin_fill("LatDorsi", 2, 23, SKIN)))
    out.append(stroke_shape(i2, "DorsalHi", [(20, 20), (50, 25), (78, 26)], 3.8, HIGHLIGHT, 4.0))
    out.append(stroke_shape(i2, "VentralSh", [(20, -10), (50, -12), (76, -9)], 4.5, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i2, "TorsoSilhouette", torso_pts, skin_fill_outlined("Torso", -20, 35, SKIN, line=1.2)))

    # D. 3/4 Head & Neck
    out.append(f'{i2}<Node x="92" y="2" rotation="{f(p0["neck_local"])}" name="HeadAndNeck" id="{neck_id}">')
    out.append(ellipse_shape(i3, "LeftEar", 21, -2, 5.5, 8.5, skin_fill_outlined("Ear", -4, 4, SKIN, line=0.9), rot_deg=-15.0))
    out.append(smooth_shape(i3, "HairCap", hair_pts, hair_paint))
    out.append(stroke_shape(i3, "BrowLine", [(28, -14), (32, -12)], 1.3, CORE_SHADOW, 0.3))
    out.append(stroke_shape(i3, "EyeDark", [(26, -13), (29, -11.5)], 1.4, "FF334155", 0.2))
    out.append(stroke_shape(i3, "JawLine", [(11, -14), (13, -6), (18, -1)], 1.4, CORE_SHADOW, 1.0))
    out.append(stroke_shape(i3, "HeadHi", [(27, -14), (37, -9), (41, 2)], 2.4, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i3, "HeadShape", head_pts, skin_fill_outlined("Head", -19, 16, SKIN, line=1.15)))
    out.append(smooth_shape(i3, "NeckShape", neck_pts, skin_fill_outlined("Neck", -9, 12, SKIN, line=1.0)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 4. Near-Left Straight Hanging Arm
def near_arm_rig():
    """Articulated Near-Left Arm (Shoulder -> Elbow -> Pronated Hand locked to Barbell at HAND_NEAR)."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    ua_id, fa_id = nid(), nid()
    key_double(ua_id, 13, lambda p: p["sh_near"][0])
    key_double(ua_id, 14, lambda p: p["sh_near"][1])
    key_double(ua_id, 15, lambda p: p["ua_near_ang"])
    key_double(ua_id, 16, lambda p: p["ua_near_sc"])

    key_double(fa_id, 13, lambda p: p["elb_near"][0])
    key_double(fa_id, 14, lambda p: p["elb_near"][1])
    key_double(fa_id, 15, lambda p: p["fa_near_ang"])
    key_double(fa_id, 16, lambda p: p["fa_near_sc"])
    p0 = POSES[0]

    ua_pts = [
        (-12, 0), (-9, -11.5), (8, -13.2), (26, -11.8), (42, -9.0), (50, -6.8),
        (54, 0), (49, 6.8), (36, 9.8), (18, 11.2), (4, 10.8), (-9, 8.8),
    ]
    delt_pts = [
        (-15, 0), (-11, -13.2), (3, -14.8), (18, -10.5), (24, 0),
        (17, 10.2), (3, 12.8), (-10, 9.8),
    ]
    fa_pts = [
        (-6, 0), (-5, -8.2), (10, -9.8), (26, -7.8), (39, -5.5),
        (45, 0), (39, 5.5), (25, 7.5), (9, 8.8), (-5, 7.2),
    ]
    hand_pts = [
        (-5, -6.8), (4, -8.2), (10, -5.5), (11, 2.5), (6, 7.2), (-3, 6.8), (-7, 1.5),
    ]

    return "\n".join([
        f'{ind}<Node name="NearLeftArmGroup">',
        f'{i2}<Node x="{f(p0["elb_near"][0])}" y="{f(p0["elb_near"][1])}" '
        f'rotation="{f(p0["fa_near_ang"])}" scaleX="{f(p0["fa_near_sc"])}" name="NearForearm" id="{fa_id}">',
        stroke_shape(i3, "NearHandKnuckles", [(48, -4.5), (50, 0.0), (48, 4.5)], 1.2, ANATOMY_LINE, 0.0),
        smooth_shape(i3, "NearHand", hand_pts, skin_fill_outlined("NearHand", -8, 7, SKIN, line=1.2), x=FOREARM_LEN - 2.0),
        stroke_shape(i3, "ForearmExtensorLine", [(6, -3.2), (22, -2.5), (36, -1.5)], 1.3, ANATOMY_LINE, 0.0),
        stroke_shape(i3, "NearForearmHi", [(6, 4.8), (22, 4.2), (36, 3.0)], 2.6, HIGHLIGHT, 2.5),
        stroke_shape(i3, "NearForearmSh", [(6, -5.2), (22, -4.5), (36, -3.0)], 3.4, CORE_SHADOW, 3.5),
        smooth_shape(i3, "NearForearmShape", fa_pts, skin_fill_outlined("NearForearm", -10, 9, SKIN, line=1.2)),
        f"{i2}</Node>",
        f'{i2}<Node x="{f(p0["sh_near"][0])}" y="{f(p0["sh_near"][1])}" '
        f'rotation="{f(p0["ua_near_ang"])}" scaleX="{f(p0["ua_near_sc"])}" name="NearUpperArm" id="{ua_id}">',
        stroke_shape(i3, "DeltBorderCrease", [(4, -10.5), (16, -6.0), (22, 2.5)], 1.4, ANATOMY_LINE, 0.0),
        stroke_shape(i3, "TricepsCrease", [(18, -7.2), (32, -5.8), (44, -2.8)], 1.4, ANATOMY_LINE, 0.0),
        stroke_shape(i3, "NearDeltHi", [(-4, 6.5), (8, 7.8), (18, 4.5)], 2.8, HIGHLIGHT, 3.0),
        smooth_shape(i3, "NearDeltoid", delt_pts, skin_fill_outlined("NearDeltoid", -15, 13, SKIN, line=1.15)),
        stroke_shape(i3, "NearUpperArmHi", [(10, 6.8), (28, 6.2), (44, 4.2)], 2.8, HIGHLIGHT, 3.0),
        stroke_shape(i3, "NearUpperArmSh", [(10, -8.2), (28, -7.5), (44, -4.8)], 3.8, CORE_SHADOW, 3.8),
        smooth_shape(i3, "NearUpperArmShape", ua_pts, skin_fill_outlined("NearUpperArm", -13, 11, SKIN, line=1.2)),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 5. Scene Assembly & Verbatim Rive 7.3 Compiler
def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    sh_id = nid()
    key_double(sh_id, 16, lambda p: p["bar_shadow_sx"])
    p0 = POSES[0]

    near_plate_xml, mid_shaft_xml, far_plate_xml = barbell_layers()
    near_arm_xml = near_arm_rig()
    torso_head_xml = dorsal_torso_glutes_and_head()
    near_thigh_xml, near_shin_xml = leg_rig("Near", False)
    far_thigh_xml, far_shin_xml = leg_rig("Far", True)

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
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="RomanianDeadlift" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground Near-Left Stepped Multi-Plate Barbell Stack, Collar & Outer Sleeve -->
{near_plate_xml}

        <!-- 2. Foreground Near-Left Hanging Arm & Pronated Hand Gripping Barbell -->
{near_arm_xml}

        <!-- 3. Dorsal Torso (Erector Spinae, Upper-Back Stabilizers), Glutes, Shorts & 3/4 Head -->
{torso_head_xml}

        <!-- 4. Foreground Near-Left Thigh (Hamstrings: Biceps Femoris & Semitendinosus) & Shin/Foot -->
{near_thigh_xml}
{near_shin_xml}

        <!-- 5. Far-Right Thigh -->
{far_thigh_xml}

        <!-- 6. Midground Chrome Barbell Shaft -->
{mid_shaft_xml}

        <!-- 7. Background Far-Right Shin & Foot -->
{far_shin_xml}

        <!-- 8. Background Far-Right Multi-Plate Barbell Stack -->
{far_plate_xml}

        <!-- 9. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="292" y="297" scaleX="{f(p0['bar_shadow_sx'])}" scaleY="0.068" name="FloorContactShadow" id="{sh_id}">
            <Ellipse width="280" height="220" name="FloorShadowEllipse"/>
            <Fill name="FloorShadowFill"><RadialGradient startX="0" startY="0" endX="140" endY="0" name="FloorShadowGrad">
                <GradientStop colorValue="D9000000" position="0"/>
                <GradientStop colorValue="66000000" position="0.62"/>
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="RomanianDeadlift" id="0:60">
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
    (BUILD / "romanian_deadlift.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/7d19b873-f31d-4a3e-a561-525605ec3add/scratch")
    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (42, "frame_mid"), (78, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(600, 30, 240))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
