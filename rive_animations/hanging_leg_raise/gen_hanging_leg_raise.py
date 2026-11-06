#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive 7.3 scene for Hanging Leg Raise (id: 'hanging_leg_raise').

Uses our canonical 3/4 athletic male mannequin from `front_raise/gen_front_raise.py` and
`hammer_curl/gen_hammer_curl.py` (volumetric 3/4 head with cropped hair, ear, brow, eye, and mouth;
muscular neck; sculpted pectorals; 6-pack rectus abdominis; athletic compression shorts; sculpted
quadriceps, knees, gastrocnemius calves, and feet).

Matches the 2-panel 3/4 front-right Hanging Straight-Leg Raise reference illustration:
  - Left Panel (f = 0 & f = 160, r = 0.0):
    * Athlete hangs vertically from the overhead pull-up bar with an overhand pronated grip, arms extended
      overhead, latissimus dorsi flared, 6-pack abs taut, and straight legs hanging vertically (`~86.5 deg`)
      with feet suspended above the floor.
  - Right Panel (f = 74, r = 1.0):
    * While the overhead arms, head, chest, and upper ribcage remain rock-solid on the pull-up bar, the pelvis
      flexes slightly forward-upward and both straight legs (locked knees, plantarflexed feet together)
      sweep smoothly in a circular sagittal arc up to horizontal (`~2 deg`, `L-sit` position pointing front-right).
  - All 6 Labeled Target Muscle Groups from the reference illustration, glowing from warm orange (#FFF97316)
    at the bottom hang to intense crimson (#FFF43F5E) at the horizontal L-sit:
    1. Iliopsoas (deep inner hip flexor in the iliopectineal groove)
    2. Pectineus (flat quadrangular medial hip flexor immediately medial/inferior to Iliopsoas)
    3. Rectus Femoris (central bipennate anterior thigh muscle)
    4. Sartorius (long oblique strap muscle sweeping from ASIS across the thigh to the medial knee)
    5. Adductor longus (medial thigh fan beneath Pectineus and medial to Sartorius)
    6. Tensor fasciae latae (lateral superior hip flexor pocket at the outer iliac crest)

Run:
    python3 gen_hanging_leg_raise.py            # writes scene.rml
    python3 gen_hanging_leg_raise.py --publish  # compiles assets/animations/hanging_leg_raise.riv + 256x256 thumbnail
"""
import math
import pathlib
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "scene.rml"
BUILD = HERE / "build"

W, H = 640, 360
FLOOR = 324.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps loop
STEP = 2

# 3/4 Front-Right Hanging Anchors
HAND_NEAR = (279.0, 29.0)      # Right (near / screen-left) hand on pull-up bar
HAND_FAR = (323.0, 33.5)       # Left (far / screen-right) hand on pull-up bar
SHOULDER_NEAR = (278.0, 102.0)  # Right (near) shoulder
SHOULDER_FAR = (318.0, 105.0)   # Left (far) shoulder

# Canonical Palette from front_raise / hammer_curl / bicep_curl_barbell
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
RACK_POST = ("FFF8FAFC", "FFCBD5E1", "FF64748B")
BAR_DARK = ("FF475569", "FF1E293B", "FF090D16")
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


EASE_RAISE = cubic_bezier(0.40, 0.0, 0.24, 1.0)
EASE_LOWER = cubic_bezier(0.42, 0.0, 0.36, 1.0)


def leg_raise_progress(frame):
    """Returns straight-leg raise progress r in [0.0, 1.0] across 160 frames:
    - 0..14:   Bottom hang hold (r = 0.0: legs vertical)
    - 14..68:  Concentric straight-leg raise up to 90 deg L-sit (r: 0.0 -> 1.0)
    - 68..88:  Top peak isometric L-sit hold (r = 1.0: legs horizontal)
    - 88..148: Controlled eccentric lowering back to vertical hang (r: 1.0 -> 0.0)
    - 148..160: Bottom hang hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 14:
        return 0.0
    if fr <= 68:
        return EASE_RAISE((fr - 14) / 54.0)
    if fr <= 88:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_LOWER((fr - 88) / 60.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def pose(r):
    """Compute Hanging Straight-Leg Raise joint transforms at progress r in [0.0, 1.0]."""
    # Subtle posterior pelvic curl at the top of the L-sit (+3.5 px forward, -3.5 px upward)
    hip_near = (lerp(293.0, 296.5, r), lerp(183.0, 179.5, r))
    hip_far = (lerp(311.0, 314.5, r), lerp(180.0, 176.5, r))

    # Straight-leg hip flexion angle:
    #   r = 0.0 (Bottom Hang): +86.5 deg (hanging straight down with natural 3.5 deg forward alignment)
    #   r = 1.0 (Top L-sit):   +2.0 deg (horizontal straight out to the front-right)
    leg_near_ang = math.radians(lerp(86.5, 2.0, r))
    leg_far_ang = math.radians(lerp(85.5, 0.5, r))

    # Foreshortening scale along the leg bone: 1.00 when vertical -> 1.04 when extended toward the 3/4 camera
    leg_near_sc = lerp(1.00, 1.04, r)
    leg_far_sc = lerp(0.98, 1.02, r)

    # Rectus femoris & Tensor fasciae latae dynamic belly thickness (`scaleY` bulge at top contraction)
    rf_bulge = lerp(1.00, 1.15, r ** 0.9)

    return {
        "r": r,
        "hip_near": hip_near,
        "hip_far": hip_far,
        "leg_near_ang": leg_near_ang,
        "leg_far_ang": leg_far_ang,
        "leg_near_sc": leg_near_sc,
        "leg_far_sc": leg_far_sc,
        "rf_bulge": rf_bulge,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(leg_raise_progress(fr)) for fr in FRAMES}

if __name__ == "__main__":
    for _fr in (0, 40, 74, 118, DURATION):
        _p = POSES[_fr if _fr in POSES else min(POSES.keys(), key=lambda k: abs(k - _fr))]
        print(
            f"f{_fr:3d} r={_p['r']:.3f} leg_near_deg={math.degrees(_p['leg_near_ang']):5.1f} "
            f"hip_near=({_p['hip_near'][0]:.1f},{_p['hip_near'][1]:.1f})"
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


def poly_shape(indent, name, pts, paint_xml, radius=1.5):
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


def polyline_stroke_shape(indent, name, pts, width, color, radius=0.5, cap="round"):
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


# ---------------------------------------------------------------- 1. 3D Pull-Up Frame & Overhead Bar
def pullup_rack_back():
    """Twin vertical white/steel rack posts and horizontal support brackets behind the athlete."""
    ind = "        "
    i2 = ind + "    "
    post_near_paint = (
        f'<Fill name="PostNearFill">{grad("PostNearGrad", 206, 0, 222, 0, "FFF8FAFC", "FF94A3B8")}</Fill>'
        '<Stroke thickness="1.0" name="PostNearStroke"><SolidColor colorValue="FF475569" name="PostNearCol"/></Stroke>'
    )
    post_far_paint = (
        f'<Fill name="PostFarFill">{grad("PostFarGrad", 268, 0, 282, 0, "FFE2E8F0", "FF64748B")}</Fill>'
        '<Stroke thickness="0.9" name="PostFarStroke"><SolidColor colorValue="FF334155" name="PostFarCol"/></Stroke>'
    )
    bracket_paint = (
        '<Fill name="BracketFill"><SolidColor colorValue="FFCBD5E1" name="BracketCol"/></Fill>'
        '<Stroke thickness="0.9" name="BracketStroke"><SolidColor colorValue="FF475569" name="BracketEdgeCol"/></Stroke>'
    )

    return "\n".join([
        f'{ind}<Node name="PullupRackBack">',
        # Horizontal support arms extending from the posts to the pull-up bar
        poly_shape(i2, "NearBracketArm", [(218.0, 38.0), (266.0, 25.0), (266.0, 30.0), (218.0, 44.0)], bracket_paint, radius=1.0),
        poly_shape(i2, "FarBracketArm", [(280.0, 42.0), (336.0, 31.0), (336.0, 36.0), (280.0, 48.0)], bracket_paint, radius=1.0),
        # Near (left-most) vertical upright column (x = 206..220, y = 12..324)
        poly_shape(i2, "NearVerticalPost", [(206.0, 12.0), (219.0, 12.0), (219.0, 324.0), (206.0, 324.0)], post_near_paint, radius=1.0),
        stroke_shape(i2, "NearPostHi", [(209.0, 16.0), (209.0, 320.0)], 1.8, "B3FFFFFF", 0.0, cap="butt"),
        # Far (center-left) vertical upright column (x = 269..281, y = 16..316)
        poly_shape(i2, "FarVerticalPost", [(269.0, 16.0), (280.0, 16.0), (280.0, 316.0), (269.0, 316.0)], post_far_paint, radius=1.0),
        stroke_shape(i2, "FarPostHi", [(271.5, 20.0), (271.5, 312.0)], 1.4, "80FFFFFF", 0.0, cap="butt"),
        f"{ind}</Node>",
    ])


def pullup_bar_and_hands_front():
    """Black angled-tip overhead pull-up bar + pronated (overhand) gripping fingers wrapped over the bar."""
    ind = "        "
    i2 = ind + "    "

    bar_pts = [
        (242.0, 29.0),
        (260.0, 25.0),
        (342.0, 34.5),
        (360.0, 44.0),
    ]
    bar_hi_pts = [
        (243.0, 27.8),
        (260.0, 23.8),
        (341.5, 33.3),
        (359.0, 42.6),
    ]

    def grip_fingers(name, gx, gy, tones):
        """Pronated (overhand) 4 fingers + thumb wrapping over the pull-up bar."""
        knuckles = []
        for idx, dx in enumerate((-4.5, -1.5, 1.5, 4.5)):
            knuckles.append(
                ellipse_shape(
                    i2,
                    f"{name}Finger{idx + 1}",
                    gx + dx,
                    gy - 0.5 + 0.3 * idx,
                    3.6,
                    7.8,
                    skin_fill(f"{name}F{idx + 1}", -4, 4, tones),
                    rot_deg=6.0,
                )
            )
        thumb_pts = [
            (gx + 3.5, gy + 1.5),
            (gx + 7.5, gy + 2.5),
            (gx + 7.2, gy + 6.2),
            (gx + 2.5, gy + 5.8),
        ]
        return "\n".join([
            stroke_shape(i2, f"{name}KnuckleHi", [(gx - 4.2, gy - 2.8), (gx + 4.2, gy - 2.0)], 1.4, HIGHLIGHT, 1.0),
            *knuckles,
            smooth_shape(i2, f"{name}Thumb", thumb_pts, skin_fill(f"{name}Thumb", gy, gy + 7, tones)),
        ])

    return "\n".join([
        f'{ind}<Node name="PullupBarAndHandsFront">',
        grip_fingers("NearGrip", HAND_NEAR[0], HAND_NEAR[1], SKIN),
        grip_fingers("FarGrip", HAND_FAR[0], HAND_FAR[1], SKIN_FAR),
        poly_shape(i2, "MountTabLeft", [(263.0, 25.5), (268.0, 26.0), (268.0, 35.0), (263.0, 34.5)], solid("MountL", "FF1E293B"), radius=0.8),
        poly_shape(i2, "MountTabRight", [(333.0, 33.5), (338.0, 34.0), (338.0, 43.0), (333.0, 42.5)], solid("MountR", "FF1E293B"), radius=0.8),
        polyline_stroke_shape(i2, "PullupBarHi", bar_hi_pts, 1.5, "B3FFFFFF", radius=1.5),
        polyline_stroke_shape(i2, "PullupBarCore", bar_pts, 5.2, "FF1E293B", radius=2.0),
        polyline_stroke_shape(i2, "PullupBarOutline", bar_pts, 6.8, "FF090D16", radius=2.0),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 2. Canonical Straight-Leg Rig (Near & Far)
def canonical_straight_leg_rig(prefix, far):
    """Canonical straight-leg rig rotating about the hip joint with compression shorts cuff, smooth volumetric
    thigh/knee/calf/foot, and glowing target muscles:
    - Rectus Femoris (central anterior thigh muscle — glowing target #3)
    - Sartorius (oblique strap muscle from ASIS to medial knee — glowing target #4)
    - Adductor longus (medial thigh fan — glowing target #5)
    - Tensor fasciae latae (outer superior hip flexor — glowing target #6)
    """
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    shorts = SHORTS_FAR if far else SHORTS
    hip_k = "hip_far" if far else "hip_near"
    ang_k = "leg_far_ang" if far else "leg_near_ang"
    sc_k = "leg_far_sc" if far else "leg_near_sc"

    leg_id, rf_id = nid(), nid()
    key_double(leg_id, 13, lambda p: p[hip_k][0])
    key_double(leg_id, 14, lambda p: p[hip_k][1])
    key_double(leg_id, 15, lambda p: p[ang_k])
    key_double(leg_id, 16, lambda p: p[sc_k])
    key_double(rf_id, 17, lambda p: p["rf_bulge"])

    p0 = POSES[0]

    def rf_t(p):
        return 0.48 + 0.52 * (p["r"] ** 0.78)

    def sartorius_t(p):
        return 0.46 + 0.54 * (p["r"] ** 0.80)

    def adductor_t(p):
        return 0.44 + 0.54 * (p["r"] ** 0.82)

    def tfl_t(p):
        return 0.48 + 0.52 * (p["r"] ** 0.78)

    # 1. Proximal Compression Shorts Cuff on Upper Thigh (matching canonical mannequin from front_raise / hammer_curl)
    shorts_cuff_pts = [
        (-12.0, -8.5), (14.0, -11.5), (14.5, 13.5), (-6.0, 15.0), (-14.0, 6.0),
    ]
    shorts_hem_pts = [(13.8, -11.0), (14.2, 1.0), (14.0, 12.8)]

    # 2. Full Thigh Silhouette (x = -12..61)
    thigh_pts = [
        (-12.0, -7.5),
        (10.0, -11.5),
        (32.0, -11.0),
        (52.0, -7.8),
        (61.0, -6.5),
        (61.0, 6.5),
        (42.0, 10.2),
        (18.0, 13.5),
        (-4.0, 15.5),
        (-14.0, 6.0),
    ]

    # 3. Target Muscle #5: Adductor longus (medial thigh fan)
    adductor_pts = [
        (-3.0, -8.2), (9.0, -11.0), (25.0, -10.2), (31.0, -6.5), (15.0, -4.6), (-1.0, -5.0),
    ]

    # 4. Target Muscle #3: Rectus Femoris (central anterior quadriceps muscle, x = 2..51)
    rectus_femoris_pts = [
        (1.0, -5.0), (13.0, -10.6), (29.0, -11.0), (44.0, -8.4),
        (51.0, -5.5), (42.0, -2.5), (24.0, -2.0), (9.0, -2.5),
    ]

    # 5. Target Muscle #4: Sartorius (long oblique strap muscle sweeping from ASIS across the thigh to medial knee)
    sartorius_pts = [
        (-8.0, -6.2), (6.0, -8.5), (24.0, -6.2), (42.0, -2.2),
        (54.0, 1.5), (51.0, 4.0), (38.0, 0.5), (20.0, -3.4), (2.0, -5.2), (-9.0, -3.6),
    ]

    # 6. Target Muscle #6: Tensor fasciae latae (TFL — lateral superior hip flexor pocket)
    tfl_pts = [
        (-10.0, -2.2), (3.0, -3.2), (16.0, -0.8), (15.0, 4.5), (1.0, 6.0), (-9.5, 3.5),
    ]

    # 7. Lower Leg (Shin & Gastrocnemius Calf, x = 56..114) & Foot (x = 110..131)
    shin_pts = [
        (56.0, -6.2), (76.0, -6.0), (96.0, -4.5), (114.0, -3.5),
        (115.0, 3.8), (96.0, 4.8), (76.0, 9.8), (62.0, 7.2), (56.0, 4.5),
    ]
    foot_pts = [
        (111.0, -3.5), (121.0, -10.5), (128.5, -15.5), (131.5, -13.0),
        (129.0, -6.5), (122.0, 1.5), (116.5, 5.8), (110.5, 3.8),
    ]

    out = [
        f'{ind}<Node x="{f(p0[hip_k][0])}" y="{f(p0[hip_k][1])}" '
        f'rotation="{f(p0[ang_k])}" scaleX="{f(p0[sc_k])}" name="{prefix}LegRig" id="{leg_id}">'
    ]

    # --- Layer 1 (Topmost on Leg): Target Muscles (TFL, Sartorius, Rectus Femoris, Adductor Longus) ---
    if not far:
        out.append(smooth_shape(i2, f"{prefix}TensorFasciaeLatae", tfl_pts, muscle_paint_fn(prefix + "TFL", tfl_t, 0.95)))
    out.append(smooth_shape(i2, f"{prefix}Sartorius", sartorius_pts, muscle_paint_fn(prefix + "Sartorius", sartorius_t, 0.9)))

    out.append(f'{i2}<Node scaleY="{f(p0["rf_bulge"])}" name="{prefix}RectusFemorisNode" id="{rf_id}">')
    if not far:
        out.append(stroke_shape(i3, f"{prefix}RFSeptum", [(10.0, -6.5), (26.0, -6.8), (42.0, -5.8)], 1.0, "737F1D1D", 0.5))
        out.append(stroke_shape(i3, f"{prefix}RFHi", [(14.0, -8.5), (28.0, -8.8), (40.0, -7.2)], 1.8, "59FFFFFF", 2.0))
    out.append(smooth_shape(i3, f"{prefix}RectusFemoris", rectus_femoris_pts, muscle_paint_fn(prefix + "RectusFemoris", rf_t, 1.0)))
    out.append(f"{i2}</Node>")

    out.append(smooth_shape(i2, f"{prefix}AdductorLongus", adductor_pts, muscle_paint_fn(prefix + "AdductorLongus", adductor_t, 0.9)))

    # --- Layer 2: Compression Shorts Cuff on Proximal Thigh + Canonical Volumetric Thigh & Knee ---
    out.append(stroke_shape(i2, f"{prefix}ShortsHem", shorts_hem_pts, 1.6, "660F172A", 0.6))
    out.append(smooth_shape(i2, f"{prefix}ThighShorts", shorts_cuff_pts, skin_fill(prefix + "ThighShorts", -12, 15, shorts)))

    if not far:
        out.append(stroke_shape(i2, f"{prefix}QuadLatLine", [(16.0, 2.5), (34.0, 2.2), (50.0, 1.2)], 1.3, SOFT_SHADOW, 1.2))
        out.append(stroke_shape(i2, f"{prefix}ThighHi", [(16.0, -6.8), (34.0, -6.5), (48.0, -5.2)], 3.8, HIGHLIGHT, 3.8))
    out.append(stroke_shape(i2, f"{prefix}ThighCoreSh", [(10.0, 10.8), (32.0, 9.2), (52.0, 5.5)], 4.8, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i2, f"{prefix}ThighBase", thigh_pts, skin_fill(prefix + "ThighBase", -12, 15, skin)))
    out.append(ellipse_shape(i2, f"{prefix}Knee", 58.0, -0.5, 14.5, 13.5, skin_fill(prefix + "Knee", -7, 7, skin)))

    # --- Layer 3: Canonical Volumetric Shin, Calf & Foot ---
    if not far:
        out.append(stroke_shape(i2, f"{prefix}FootHi", [(114.0, -4.2), (122.5, -9.8), (128.0, -13.2)], 2.2, HIGHLIGHT, 2.5))
    out.append(stroke_shape(i2, f"{prefix}FootArchSh", [(114.0, 2.5), (122.0, -1.5), (128.5, -7.5)], 2.4, CORE_SHADOW, 2.0))
    out.append(smooth_shape(i2, f"{prefix}Foot", foot_pts, skin_fill(prefix + "Foot", -16, 6, skin)))

    if not far:
        out.append(stroke_shape(i2, f"{prefix}CalfCut", [(66.0, 3.2), (78.0, 6.5), (90.0, 3.5)], 1.3, SOFT_SHADOW, 1.2))
        out.append(stroke_shape(i2, f"{prefix}ShinHi", [(64.0, -4.5), (86.0, -3.8), (108.0, -2.8)], 3.0, HIGHLIGHT, 3.2))
    out.append(stroke_shape(i2, f"{prefix}ShinSh", [(64.0, 5.5), (82.0, 7.2), (106.0, 3.2)], 4.2, CORE_SHADOW, 4.0))
    out.append(smooth_shape(i2, f"{prefix}ShinBase", shin_pts, skin_fill(prefix + "Shin", -6, 10, skin)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. Canonical Hanging Upper Body, Head with Hair/Face & Shorts
def hanging_upper_body_and_pelvis():
    """Canonical 3/4 front-right athlete upper body with cropped hair, facial features, overhead hanging arms,
    sculpted pectorals, 6-pack abs, athletic compression shorts, and glowing Iliopsoas & Pectineus hip flexors."""
    ind = "        "
    i2 = ind + "    "

    def iliopsoas_t(p):
        return 0.50 + 0.50 * (p["r"] ** 0.75)

    def pectineus_t(p):
        return 0.48 + 0.52 * (p["r"] ** 0.78)

    # 1. Overhead Hanging Arms (Far Left Arm & Near Right Arm from Bar Hands to Shoulders)
    far_arm_pts = [
        (319.5, 33.5), (326.5, 34.5), (329.5, 52.0), (331.0, 68.0),
        (332.5, 86.0), (327.0, 106.0), (313.0, 105.0), (315.5, 84.0),
        (317.5, 66.0), (318.5, 50.0),
    ]
    near_arm_pts = [
        (274.5, 29.0), (282.5, 30.0), (284.5, 48.0), (286.5, 65.0),
        (287.5, 84.0), (283.0, 104.0), (268.5, 102.0), (269.5, 82.0),
        (272.0, 64.0), (273.5, 47.0),
    ]

    # 2. Canonical Volumetric 3/4 Front-Right Head with Cropped Hair, Ear, Brow, Eye & Mouth (mirrored from front_raise / hammer_curl)
    head_pts = [
        (308.0, 69.0),   # upper forehead facing front-right
        (310.5, 75.0),   # brow ridge
        (312.2, 81.0),   # nose bridge & tip (facing front-right)
        (310.8, 86.0),   # upper lip / mouth
        (310.2, 91.5),   # strong chin tip
        (304.0, 94.5),   # under-chin / anterior jawline
        (295.0, 92.5),   # mandible angle (gonion)
        (288.0, 87.5),   # beneath ear / mastoid
        (284.5, 79.0),   # occiput / back of skull
        (285.5, 68.5),   # posterior crown
        (292.5, 62.5),   # top cranial dome
        (302.0, 63.0),   # anterior crown
    ]
    hair_pts = [
        (308.5, 70.5), (303.0, 62.2), (292.0, 61.8), (284.5, 67.5),
        (284.0, 78.5), (288.5, 82.5), (290.0, 75.0), (295.0, 70.0),
        (302.5, 69.0),
    ]
    head_hi = [(307.5, 72.0), (303.5, 67.0), (295.5, 66.0)]
    cheek_hi = [(308.5, 80.0), (302.5, 81.5), (297.0, 80.5)]
    jaw_sh = [(308.0, 93.5), (299.0, 94.2), (291.5, 90.5)]

    neck_pts = [
        (289.0, 88.0), (305.0, 91.5), (309.0, 105.0),
        (282.0, 105.0), (286.0, 96.0),
    ]

    # 3. Hanging Torso Silhouette (V-taper lats + 6-pack waist + pelvis)
    torso_pts = [
        (271.0, 98.0),
        (296.0, 101.0),
        (322.0, 103.0),
        (320.0, 124.0),
        (315.0, 146.0),
        (314.0, 166.0),
        (315.0, 182.0),
        (301.0, 191.0),
        (282.0, 184.0),
        (280.0, 164.0),
        (282.0, 144.0),
        (272.0, 122.0),
    ]

    # Canonical Sculpted Pectoralis Major Plates (matching front_raise / hammer_curl shading)
    pec_near_pts = [
        (276.0, 100.0), (298.5, 106.0), (299.0, 128.5),
        (287.0, 130.5), (277.5, 122.5), (274.5, 109.0),
    ]
    pec_far_pts = [
        (300.5, 106.0), (318.5, 103.0), (319.5, 122.0),
        (312.5, 129.0), (300.5, 128.0),
    ]
    pec_paint = (
        '<Fill name="PecFill"><SolidColor colorValue="120F172A" name="PecCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="PecStroke"><SolidColor colorValue="380F172A" name="PecStrokeCol"/></Stroke>'
    )

    # Canonical Athletic Compression Shorts over the Pelvis (matching front_raise / hammer_curl)
    pelvis_shorts = [
        (280.0, 163.0), (299.5, 165.0), (315.0, 164.0),
        (317.0, 183.0), (302.0, 192.0), (293.0, 190.0), (279.0, 183.0),
    ]

    # Target Muscle #1: Iliopsoas (deep inner hip flexor emerging in the iliopectineal groove)
    iliopsoas_near_pts = [
        (289.0, 166.0), (297.5, 168.0), (298.0, 179.0), (289.5, 177.0),
    ]
    iliopsoas_far_pts = [
        (301.5, 167.5), (309.5, 165.5), (309.0, 176.5), (301.0, 178.0),
    ]

    # Target Muscle #2: Pectineus (flat quadrangular medial hip flexor immediately medial/inferior to Iliopsoas)
    pectineus_near_pts = [
        (291.0, 175.5), (299.5, 177.5), (299.5, 187.5), (291.5, 185.0),
    ]
    pectineus_far_pts = [
        (300.5, 177.0), (308.5, 174.5), (308.0, 184.0), (300.5, 186.5),
    ]

    # Canonical 6-Pack Rectus Abdominis Blocks (matching front_raise / hammer_curl)
    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1A0F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="AbsEdge"><SolidColor colorValue="400F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        [(287.5, 130.5), (298.5, 131.0), (298.5, 140.5), (287.0, 140.0)],
        [(287.0, 142.5), (298.5, 143.0), (298.5, 152.5), (287.2, 152.0)],
        [(287.5, 154.5), (298.5, 155.0), (298.5, 163.5), (288.5, 162.5)],
        [(301.0, 131.0), (310.5, 130.5), (310.2, 140.0), (301.0, 140.5)],
        [(301.0, 143.0), (310.0, 142.5), (309.8, 152.0), (301.0, 152.5)],
        [(301.0, 155.0), (309.5, 154.5), (309.0, 162.5), (301.0, 163.5)],
    ]

    out = [f'{ind}<Node name="HangingUpperBodyAndPelvis">']

    # 1. Near (Right) Overhead Hanging Arm (drawn in front of the shoulder/lat junction)
    out.append(stroke_shape(i2, "NearArmBrachioradialisLine", [(277.0, 44.0), (279.0, 62.0), (278.0, 78.0)], 1.15, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i2, "NearArmBicepsLine", [(280.5, 68.0), (282.0, 84.0), (279.5, 98.0)], 1.2, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i2, "NearArmHi", [(275.5, 36.0), (275.0, 66.0), (274.0, 94.0)], 2.8, HIGHLIGHT, 3.0))
    out.append(stroke_shape(i2, "NearArmSh", [(283.0, 40.0), (284.5, 70.0), (283.5, 98.0)], 3.8, CORE_SHADOW, 3.5))
    out.append(smooth_shape(i2, "NearHangingArm", near_arm_pts, skin_fill("NearHangingArm", 29, 104, SKIN)))

    # 2. Canonical Volumetric 3/4 Head with Cropped Hair, Ear, Brow, Eye & Mouth
    out.append(smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 284, 62, 308, 82, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i2, "Ear", 290.5, 81.5, 5.2, 8.2, solid("Ear", "FFA3B1C4"), rot_deg=-12.0))
    out.append(stroke_shape(i2, "BrowShade", [(306.0, 75.2), (310.5, 74.8)], 1.4, "590F172A", 0.8))
    out.append(stroke_shape(i2, "EyeLine", [(305.8, 77.0), (308.8, 76.8)], 1.1, "730F172A", 0.4))
    out.append(stroke_shape(i2, "MouthLine", [(307.0, 86.8), (310.5, 86.5)], 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i2, "HeadHi", head_hi, 3.0, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i2, "CheekHi", cheek_hi, 2.2, "80FFFFFF", 2.5))
    out.append(stroke_shape(i2, "JawShadow", jaw_sh, 2.6, CORE_SHADOW, 2.5))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill("Head", 62, 95, SKIN, x0=285, x1=312)))
    out.append(stroke_shape(i2, "UnderChinShadow", [(294.5, 92.5), (301.5, 94.5), (307.5, 93.0)], 3.0, CORE_SHADOW, 2.5))
    out.append(stroke_shape(i2, "SCMLine", [(293.5, 91.0), (296.5, 98.0), (298.5, 104.0)], 1.4, SOFT_SHADOW, 1.2))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", 88, 105, SKIN)))

    # 3. Target Muscles #1 & #2 (Iliopsoas & Pectineus) + Canonical Pelvis Compression Shorts
    out.append(smooth_shape(i2, "PectineusNear", pectineus_near_pts, muscle_paint_fn("PectineusNear", pectineus_t, 0.9)))
    out.append(smooth_shape(i2, "PectineusFar", pectineus_far_pts, muscle_paint_fn("PectineusFar", pectineus_t, 0.85)))
    out.append(smooth_shape(i2, "IliopsoasNear", iliopsoas_near_pts, muscle_paint_fn("IliopsoasNear", iliopsoas_t, 0.95)))
    out.append(smooth_shape(i2, "IliopsoasFar", iliopsoas_far_pts, muscle_paint_fn("IliopsoasFar", iliopsoas_t, 0.85)))
    out.append(stroke_shape(i2, "WaistbandLine", [(280.5, 165.0), (299.5, 167.0), (314.5, 166.0)], 1.8, "660F172A", 0.8))
    out.append(stroke_shape(i2, "ShortsFlyLine", [(299.5, 167.0), (299.5, 184.0)], 1.3, "660F172A", 0.8))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill("PelvisShorts", 163, 192, SHORTS)))

    # 4. Canonical 6-Pack Rectus Abdominis & Obliques
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "LineaAlba", [(299.5, 126.0), (299.8, 146.0), (299.8, 163.0)], 1.3, "470F172A", 0.8))
    out.append(stroke_shape(i2, "ObliqueLine1", [(280.5, 138.0), (284.5, 145.0), (287.0, 151.0)], 1.3, "380F172A", 1.0))
    out.append(stroke_shape(i2, "ObliqueLine2", [(280.5, 148.0), (284.5, 155.0), (287.5, 161.0)], 1.3, "380F172A", 1.0))

    # 5. Canonical Sculpted Pectoralis Major Plates
    out.append(stroke_shape(i2, "PecNearLowerSh", [(277.5, 123.0), (287.5, 130.8), (298.5, 128.5)], 2.4, CORE_SHADOW, 2.0))
    out.append(stroke_shape(i2, "PecFarLowerSh", [(300.5, 128.2), (312.0, 129.2), (319.0, 122.5)], 2.2, CORE_SHADOW, 2.0))
    out.append(stroke_shape(i2, "PecNearHi", [(279.0, 106.0), (289.0, 108.0), (296.5, 112.0)], 2.8, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i2, "PecNear", pec_near_pts, pec_paint))
    out.append(smooth_shape(i2, "PecFar", pec_far_pts, pec_paint))

    # 6. Torso & Flared Latissimus Dorsi Base
    out.append(stroke_shape(i2, "LatFlareSh", [(273.5, 108.0), (275.5, 126.0), (281.5, 144.0)], 5.0, CORE_SHADOW, 4.8))
    out.append(stroke_shape(i2, "TorsoCenterHi", [(304.0, 108.0), (305.0, 134.0), (304.0, 158.0)], 4.2, HIGHLIGHT, 4.2))
    out.append(smooth_shape(i2, "TorsoSilhouette", torso_pts, skin_fill("Torso", 98, 191, SKIN, x0=272, x1=322)))

    # 7. Far (Left) Overhead Hanging Arm (drawn behind the torso)
    out.append(stroke_shape(i2, "FarArmSh", [(326.0, 42.0), (328.0, 72.0), (325.0, 98.0)], 3.6, CORE_SHADOW, 3.5))
    out.append(smooth_shape(i2, "FarHangingArm", far_arm_pts, skin_fill("FarHangingArm", 33, 106, SKIN_FAR)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 4. Scene Assembly (RML First Child = Topmost Layer)
def build_rml():
    global _id
    _id = 0
    KEYED.clear()

    bar_front_xml = pullup_bar_and_hands_front()
    near_leg_xml = canonical_straight_leg_rig("Near", False)
    upper_body_xml = hanging_upper_body_and_pelvis()
    far_leg_xml = canonical_straight_leg_rig("Far", True)
    rack_back_xml = pullup_rack_back()

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
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="HangingLegRaise" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Overhead Pull-Up Bar & Pronated Gripping Hands -->
{bar_front_xml}

        <!-- 2. Foreground: Near (Right) Straight Leg (Rectus Femoris, Sartorius, Adductor Longus, TFL) -->
{near_leg_xml}

        <!-- 3. Canonical Hanging Upper Body, Volumetric Head & Shorts (Iliopsoas, Pectineus, 6-Pack Abs) -->
{upper_body_xml}

        <!-- 4. Background: Far (Left) Straight Leg -->
{far_leg_xml}

        <!-- 5. Pull-Up Rack Vertical Uprights & Support Brackets -->
{rack_back_xml}

        <!-- 6. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="296" y="{f(FLOOR - 2)}" scaleX="0.90" scaleY="0.08" name="BodyShadow">
            <Ellipse width="210" height="210" name="BodyShadowEllipse"/>
            <Fill name="BodyShadowFill"><RadialGradient startX="0" startY="0" endX="105" endY="0" name="BodyShadowGrad">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="HangingLegRaise" id="0:60">
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
    riv_out = HERE / "hanging_leg_raise.riv"
    riv_out.write_bytes(riv_bytes)

    repo = HERE.parent.parent
    riv_dest = repo / "assets/animations/hanging_leg_raise.riv"
    thumb_dest = repo / "assets/animations/thumbnails/hanging_leg_raise.png"
    riv_dest.write_bytes(riv_bytes)

    legacy_mk = repo / "assets/animations/hanging_leg_raise.movekit"
    if legacy_mk.exists():
        legacy_mk.unlink()

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png

    for fr, tag in ((0, "frame_start"), (40, "frame_mid"), (74, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(680, 12, 340))
            write_png(thumb_dest, 256, 256, thumb_rgb)

    print(f"Published {riv_dest} ({len(riv_bytes)} bytes) + {thumb_dest}")


if __name__ == "__main__":
    import sys

    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
