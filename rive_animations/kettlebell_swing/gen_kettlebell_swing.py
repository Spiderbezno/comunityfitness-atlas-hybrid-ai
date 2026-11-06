#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive 7.3 scene for Kettlebell Swing (id: 'kettlebell_swing').

Uses our canonical 3/4 athletic male mannequin (`front_raise`, `hammer_curl`, `incline_dumbbell_press`,
`hanging_leg_raise`): volumetric 3/4 head with cropped dark hair, ear, brow, eye, and mouth; sculpted
pectorals, serratus anterior, 6-pack abs, and dark athletic compression shorts.

Matches the 2-panel 3/4 front-right Russian Kettlebell Swing reference illustration:
  - Left Panel (f = 0 & f = 160, r = 0.0 — Bottom Hip-Hinge Hike):
    * Athlete hinges deeply at the hips (`hip_near = (264, 178)`) with a flat neutral spine angled at
      `~37 deg` above horizontal (`sh_near = (328, 128)`) and slight knee flexion (`knee_near = (324, 224)`).
    * Both arms reach straight down-back between the thighs (`hand_near = (304, 206)`) hiking the heavy
      3D matte-black cast-iron kettlebell behind the knees (`kb_center = (290, 224)`), partially occluded
      by the near right knee/thigh just like the reference illustration.
  - Right Panel (f = 74, r = 1.0 — Standing Hip-Snap Lockout):
    * Powerful hip extension snaps the pelvis forward (`hip_near = (306, 158)`) and locks out the knees
      (`knee_near = (312, 222)`) into a tall vertical standing plank (`sh_near = (308, 74)`).
    * Both straight arms swing in a ballistic pendulum arc up to horizontal shoulder height
      (`hand_near = (392, 92)`), floating the 3D kettlebell horizontally in extension of the forearms.
  - All 10 Labeled Target Muscle Groups from the reference illustration, glowing from warm orange (#FFF97316)
    to intense crimson (#FFF43F5E):
    1. Anterior deltoid (`Deltoides anterior`)
    2. Lateral deltoid (`Deltoides lateral`)
    3. Upper pectoralis major (`Parte superior del pectoral`)
    4. Serratus anterior (`Serrato anterior`)
    5. Gluteus maximus (`Glúteo mayor`)
    6. Hamstrings (`Isquiotibiales`)
    7. Vastus lateralis (`Vasto lateral`)
    8. Rectus femoris (`Recto femoral`)
    9. Vastus medialis (`Vasto medial`)
    10. Soleus (`Sóleo`)

Run:
    python3 gen_kettlebell_swing.py            # writes scene.rml
    python3 gen_kettlebell_swing.py --publish  # compiles assets/animations/kettlebell_swing.riv + thumbnail
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
ASSET_RIV = REPO / "assets/animations/kettlebell_swing.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/kettlebell_swing.png"

# 16:9 standard canvas
W, H = 640, 360
FLOOR = 300.0
FPS = 60

# Timeline (160 frames / 2.67s @ 60fps):
#   0..12:   Bottom hip-hinge backswing peak hold (r = 0.0: Left Panel)
#   12..66:  Explosive hip-snap & ballistic upward swing (r: 0.0 -> 1.0)
#   66..84:  Top float at shoulder height (r = 1.0: Right Panel)
#   84..148: Controlled pendulum drop & hip-hinge absorption (r: 1.0 -> 0.0)
#   148..160: Bottom hip-hinge backswing peak hold (r = 0.0)
DURATION = 160
STEP = 2

# Stationary ankle anchors on FLOOR = 300.0 (3/4 front-right stance facing +X)
ANKLE_NEAR = (306.0, 286.0)
ANKLE_FAR = (324.0, 270.0)

# Reference rest lengths for articulated limb segments
SHIN_NEAR_LEN = 66.0
THIGH_NEAR_LEN = 74.0
SHIN_FAR_LEN = 64.0
THIGH_FAR_LEN = 72.0
TORSO_LEN = 84.0
UPPER_ARM_LEN = 44.0
FOREARM_LEN = 42.0


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


EASE_SWING_UP = cubic_bezier(0.32, 0.0, 0.22, 1.0)
EASE_SWING_DOWN = cubic_bezier(0.42, 0.0, 0.36, 1.0)


def swing_progress(frame):
    """Returns kettlebell swing progress r in [0.0, 1.0] across 160 frames."""
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 66:
        return EASE_SWING_UP((fr - 12) / 54.0)
    if fr <= 84:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_SWING_DOWN((fr - 84) / 64.0)
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
    sc = max(0.60, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute 3/4 Front-Right Russian Kettlebell Swing joint transforms at progress r in [0.0, 1.0]."""
    # 1. Knees: Flexed forward-right in bottom hinge (r=0.0) -> Locked out upright at top (r=1.0)
    knee_near = quad_interp_pt((325.0, 224.0), (317.0, 223.0), (311.0, 222.0), r)
    knee_far = quad_interp_pt((340.0, 210.0), (333.0, 209.0), (327.0, 208.0), r)

    # 2. Hips / Pelvis: Pushed far back-left in bottom hinge (r=0.0) -> Snapped forward over ankles at top (r=1.0)
    hip_near = quad_interp_pt((264.0, 178.0), (290.0, 165.0), (305.0, 158.0), r)
    hip_far = quad_interp_pt((278.0, 166.0), (304.0, 154.0), (319.0, 148.0), r)

    # 3. Shoulders & Hinged Torso:
    #    - At r=0.0 (Bottom Hinge): sh_near = (328.0, 128.0) (~ -38 deg forward-right torso hinge)
    #    - At r=0.5 (Mid Hip Drive): sh_near = (316.0, 96.0)
    #    - At r=1.0 (Standing Plank): sh_near = (307.0, 74.0) (~ -88.5 deg tall vertical lockout)
    sh_near = quad_interp_pt((328.0, 128.0), (316.0, 96.0), (307.0, 74.0), r)
    sh_far = quad_interp_pt((340.0, 120.0), (328.0, 89.0), (320.0, 68.0), r)

    # 4. Ballistic Pendulum Arm Swing (True Polar Arc from Shoulder -> Elbow -> Hand -> Kettlebell):
    #    - At r=0.0 (Bottom Hike): ua_near_ang = +106 deg, fa_near_ang = +115 deg, kb_ang = +124 deg
    #      (arms reach down-back between the thighs; kettlebell bell tucks behind the knees at ~(290, 224)!)
    #    - At r=1.0 (Top Float):   ua_near_ang = +14 deg,  fa_near_ang = +7 deg,   kb_ang = +4 deg
    #      (arms extended forward-right at chest/shoulder level; kettlebell floats horizontally!)
    ua_near_ang = math.radians(lerp(106.0, 14.0, r))
    fa_near_ang = math.radians(lerp(115.0, 7.0, r))
    kb_ang = math.radians(lerp(124.0, 4.0, r))

    elb_near = (
        sh_near[0] + UPPER_ARM_LEN * math.cos(ua_near_ang),
        sh_near[1] + UPPER_ARM_LEN * math.sin(ua_near_ang),
    )
    hand_near = (
        elb_near[0] + FOREARM_LEN * math.cos(fa_near_ang),
        elb_near[1] + FOREARM_LEN * math.sin(fa_near_ang),
    )

    ua_far_ang = math.radians(lerp(104.0, 12.0, r))
    fa_far_ang = math.radians(lerp(113.0, 5.0, r))
    elb_far = (
        sh_far[0] + UPPER_ARM_LEN * 0.94 * math.cos(ua_far_ang),
        sh_far[1] + UPPER_ARM_LEN * 0.94 * math.sin(ua_far_ang),
    )
    hand_far = (
        elb_far[0] + FOREARM_LEN * 0.94 * math.cos(fa_far_ang),
        elb_far[1] + FOREARM_LEN * 0.94 * math.sin(fa_far_ang),
    )

    # 5. Leg & Torso Segment Transforms
    shin_near_ang, shin_near_sc = seg_xform(knee_near, ANKLE_NEAR, SHIN_NEAR_LEN)
    thigh_near_ang, thigh_near_sc = seg_xform(hip_near, knee_near, THIGH_NEAR_LEN)
    shin_far_ang, shin_far_sc = seg_xform(knee_far, ANKLE_FAR, SHIN_FAR_LEN)
    thigh_far_ang, thigh_far_sc = seg_xform(hip_far, knee_far, THIGH_FAR_LEN)
    torso_ang, torso_sc = seg_xform(hip_near, sh_near, TORSO_LEN)

    # 6. Head & Neck local rotation inside TorsoRig:
    #    - At r=0.0 (torso_ang = -38.0 deg), neck_local = -6.0 deg (head gazes forward-right)
    #    - At r=1.0 (torso_ang = -88.6 deg), neck_local = -1.4 deg (upright horizontal gaze to the right!)
    neck_local = math.radians(lerp(-6.0, -1.4, r))

    return {
        "r": r,
        "knee_near": knee_near,
        "knee_far": knee_far,
        "hip_near": hip_near,
        "hip_far": hip_far,
        "sh_near": sh_near,
        "sh_far": sh_far,
        "elb_near": elb_near,
        "hand_near": hand_near,
        "elb_far": elb_far,
        "hand_far": hand_far,
        "ua_near_ang": ua_near_ang,
        "fa_near_ang": fa_near_ang,
        "ua_far_ang": ua_far_ang,
        "fa_far_ang": fa_far_ang,
        "kb_ang": kb_ang,
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
        "neck_local": neck_local,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(swing_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = (
    "ua_near_ang",
    "fa_near_ang",
    "ua_far_ang",
    "fa_far_ang",
    "kb_ang",
    "shin_near_ang",
    "thigh_near_ang",
    "shin_far_ang",
    "thigh_far_ang",
    "torso_ang",
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

if __name__ == "__main__":
    for _fr in (0, 38, 74, 118, DURATION):
        _p = POSES[_fr if _fr in POSES else min(POSES.keys(), key=lambda k: abs(k - _fr))]
        print(
            f"f{_fr:3d} r={_p['r']:.3f} hip=({_p['hip_near'][0]:.1f},{_p['hip_near'][1]:.1f}) "
            f"sh=({_p['sh_near'][0]:.1f},{_p['sh_near'][1]:.1f}) "
            f"hand=({_p['hand_near'][0]:.1f},{_p['hand_near'][1]:.1f}) "
            f"torso_deg={math.degrees(_p['torso_ang']):+.1f}"
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


# ---------------------------------------------------------------- Canonical Palette & Muscle Activation
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
KB_DARK = ("FF475569", "FF1E293B", "FF090D16")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "4D0F172A"

# Target Muscle Heat Colors: warm orange (#FFF97316) -> intense crimson (#FFF43F5E)
MUSCLE_LOW = (0xE6, 0xF9, 0x73, 0x16)
MUSCLE_HIGH = (0xFF, 0xF4, 0x3F, 0x5E)
MUSCLE_LINE_LOW = (0x80, 0x9A, 0x34, 0x12)
MUSCLE_LINE_HIGH = (0xE6, 0x88, 0x13, 0x37)


def argb_lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return "".join(f"{round(lerp(x, y, t)):02X}" for x, y in zip(a, b))


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


# ---------------------------------------------------------------- 1. Heavy 3D Cast-Iron Kettlebell (Between Legs at r=0 -> Shoulder Float at r=1)
def kettlebell_3d_rig():
    """3D Cast-Iron Kettlebell anchored at `hand_near` and rotating by `kb_ang`:
    - Local `(0, 0)` is the gripping handle bar inside the athlete's hands.
    - Local `+X` extends distally from the handle horn (`x = 0..14`) into the heavy spherical cast-iron
      kettlebell body (`x = 12..40`, radius `~15 px`).
    """
    ind = "        "
    i2 = ind + "    "
    kb_id = nid()
    key_double(kb_id, 13, lambda p: p["hand_near"][0])
    key_double(kb_id, 14, lambda p: p["hand_near"][1])
    key_double(kb_id, 15, lambda p: p["kb_ang"])
    p0 = POSES[0]

    # Curved steel kettlebell handle horn loop (from grip at x=0 to bell shoulders at x=16, y=+-9.5)
    horn_outer_pts = [
        (-4.5, -8.5), (6.0, -11.5), (16.5, -9.0),
        (16.5, 9.0), (6.0, 11.5), (-4.5, 8.5),
    ]
    horn_window_pts = [
        (0.5, -5.8), (7.5, -7.2), (13.5, -5.5),
        (13.5, 5.5), (7.5, 7.2), (0.5, 5.8),
    ]
    horn_paint = (
        f'<Fill name="KBHornFill">{grad3("KBHornGrad", -12, 12, "FF94A3B8", "FF334155", "FF0F172A")}</Fill>'
        '<Stroke thickness="1.0" join="round" name="KBHornEdge"><SolidColor colorValue="FF090D16" name="KBHornEdgeCol"/></Stroke>'
    )
    bell_paint = (
        f'<Fill name="KBBellFill">{grad3("KBBellGrad", -16, 16, *KB_DARK, x0=14, x1=42)}</Fill>'
        '<Stroke thickness="1.2" join="round" name="KBBellEdge"><SolidColor colorValue="FF020617" name="KBBellEdgeCol"/></Stroke>'
    )
    flat_base_pts = [
        (38.5, -9.5), (41.5, -6.8), (41.5, 6.8), (38.5, 9.5),
    ]

    return "\n".join([
        f'{ind}<Node x="{f(p0["hand_near"][0])}" y="{f(p0["hand_near"][1])}" '
        f'rotation="{f(p0["kb_ang"])}" name="Kettlebell3D" id="{kb_id}">',
        # 1. Specular highlight & weight ring on the spherical cast-iron kettlebell body
        ellipse_shape(i2, "KBBellSpecHi", 23.5, -5.5, 11.0, 6.5, solid("KBHi", "4DFFFFFF"), rot_deg=-15.0),
        ellipse_shape(i2, "KBWeightBoss", 27.5, 0.0, 14.0, 14.0, '<Stroke thickness="1.0" name="KBBossRing"><SolidColor colorValue="FF334155" name="KBBossCol"/></Stroke>'),
        smooth_shape(i2, "KBFlatBottom", flat_base_pts, solid("KBBase", "FF090D16")),
        ellipse_shape(i2, "KBBellSphere", 27.0, 0.0, 29.0, 29.5, bell_paint),
        # 2. Curved kettlebell handle horn + dark cutout window
        smooth_shape(i2, "KBHornWindow", horn_window_pts, solid("KBWin", "FF0F172A")),
        stroke_shape(i2, "KBHornHi", [(-2.0, -8.5), (6.5, -10.2), (14.5, -8.2)], 1.5, "B3FFFFFF", 0.5),
        smooth_shape(i2, "KBHornLoop", horn_outer_pts, horn_paint),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 2. Swing Arm Rig (Anterior Deltoid + Lateral Deltoid + Forearm & Grip)
def swing_arm_rig(prefix, is_near):
    """Articulated UpperArm + Forearm + Gripping Hand with glowing Anterior Deltoid & Lateral Deltoid."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN if is_near else SKIN_FAR
    sh_k = "sh_near" if is_near else "sh_far"
    el_k = "elb_near" if is_near else "elb_far"
    ua_k = "ua_near_ang" if is_near else "ua_far_ang"
    fa_k = "fa_near_ang" if is_near else "fa_far_ang"
    sc = 1.0 if is_near else 0.94
    ua_len = UPPER_ARM_LEN * sc
    fa_len = FOREARM_LEN * sc

    ua_id, fa_id = nid(), nid()
    key_double(ua_id, 13, lambda p: p[sh_k][0])
    key_double(ua_id, 14, lambda p: p[sh_k][1])
    key_double(ua_id, 15, lambda p: p[ua_k])

    key_double(fa_id, 13, lambda p: p[el_k][0])
    key_double(fa_id, 14, lambda p: p[el_k][1])
    key_double(fa_id, 15, lambda p: p[fa_k])

    p0 = POSES[0]

    # Deltoid activation peaks as the kettlebell swings up to shoulder height (r = 1.0)
    def ant_delt_t(p):
        return 0.46 + 0.54 * (p["r"] ** 0.78)

    def lat_delt_t(p):
        return 0.44 + 0.54 * (p["r"] ** 0.80)

    # In UpperArm local frame (`+X` from shoulder to elbow, `ua_ang` from +106 deg down to +14 deg right):
    # - Local `-Y` (`ua_ang - 90 deg`, i.e. +16 deg to -76 deg = front-right / superior) is ANTERIOR (Anterior Deltoid & Biceps).
    # - Local `0` (central humerus axis) is LATERAL (Lateral Deltoid).
    # - Local `+Y` (`ua_ang + 90 deg`, i.e. +196 deg to +104 deg = rear-left / inferior) is POSTERIOR (Triceps).
    ua_pts = [
        (-8.0, 0.0), (-5.0, -9.2), (8.0, -10.5), (ua_len * 0.55, -9.8), (ua_len - 4.0, -6.8),
        (ua_len + 4.0, 0.0), (ua_len - 4.0, 6.8), (ua_len * 0.55, 9.8), (8.0, 10.5), (-5.0, 9.2),
    ]
    delt_base_pts = [
        (-11.0, 0.0), (-7.0, -10.2), (4.0, -11.5), (15.0, -8.0),
        (18.0, 0.0), (15.0, 8.0), (4.0, 11.5), (-7.0, 10.2),
    ]
    # Target Muscle #1: Deltoides anterior (front/superior `-Y` cap of the shoulder)
    ant_delt_pts = [
        (-7.0, -1.5), (-2.0, -10.5), (8.5, -10.2), (16.5, -5.5), (14.0, -0.5), (2.0, -1.0),
    ]
    # Target Muscle #2: Deltoides lateral (central/multipennate lateral cap of the shoulder)
    lat_delt_pts = [
        (-9.5, -1.0), (2.0, -2.5), (15.5, -1.0), (16.0, 4.5), (3.5, 7.8), (-7.5, 5.2),
    ]

    fa_pts = [
        (-5.0, 0.0), (-3.0, -7.2), (fa_len * 0.35, -8.5), (fa_len - 4.5, -4.8),
        (fa_len + 3.5, 0.0), (fa_len - 4.5, 4.8), (fa_len * 0.35, 8.5), (-3.0, 7.2),
    ]
    fist_pts = [
        (fa_len - 4.5, -5.2), (fa_len + 5.5, -4.8), (fa_len + 6.8, 0.0),
        (fa_len + 5.2, 5.2), (fa_len - 4.5, 4.8),
    ]

    out = [f'{ind}<Node name="{prefix}SwingArmGroup">']

    # --- Layer 1: Forearm & Gripping Fist (elbow -> hand) ---
    out.append(
        f'{i2}<Node x="{f(p0[el_k][0])}" y="{f(p0[el_k][1])}" '
        f'rotation="{f(p0[fa_k])}" name="{prefix}Forearm" id="{fa_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}Knuckle1", [(fa_len - 1.5, -2.2), (fa_len + 4.5, -2.0)], 0.9, SOFT_SHADOW, 0.0))
    out.append(stroke_shape(i3, f"{prefix}Knuckle2", [(fa_len - 1.5, 1.0), (fa_len + 4.5, 1.2)], 0.9, SOFT_SHADOW, 0.0))
    out.append(smooth_shape(i3, f"{prefix}GrippingFist", fist_pts, skin_fill(prefix + "Fist", -5, 5, skin)))
    if is_near:
        out.append(stroke_shape(i3, f"{prefix}BrachioradialisLine", [(6.0, -1.5), (22.0, -1.2), (34.0, -0.8)], 1.15, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(6.0, -4.2), (fa_len - 8.0, -3.0)], 2.6, HIGHLIGHT, 2.8))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(6.0, 4.5), (fa_len - 8.0, 3.2)], 3.2, CORE_SHADOW, 3.0))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -9, 9, skin)))
    out.append(f"{i2}</Node>")

    # --- Layer 2: Upper Arm + Glowing Anterior & Lateral Deltoids ---
    out.append(
        f'{i2}<Node x="{f(p0[sh_k][0])}" y="{f(p0[sh_k][1])}" '
        f'rotation="{f(p0[ua_k])}" name="{prefix}UpperArm" id="{ua_id}">'
    )
    if is_near:
        out.append(stroke_shape(i3, f"{prefix}AntDeltHi", [(-1.0, -6.5), (10.0, -5.8)], 1.8, "66FFFFFF", 1.6))
        out.append(stroke_shape(i3, f"{prefix}DeltSeptum", [(-4.0, -1.2), (7.0, -1.5), (15.5, -0.8)], 1.1, "807F1D1D", 0.4))
    out.append(smooth_shape(i3, f"{prefix}AnteriorDeltoid", ant_delt_pts, muscle_paint_fn(prefix + "AntDelt", ant_delt_t, 0.95)))
    out.append(smooth_shape(i3, f"{prefix}LateralDeltoid", lat_delt_pts, muscle_paint_fn(prefix + "LatDelt", lat_delt_t, 0.95)))
    out.append(smooth_shape(i3, f"{prefix}DeltoidCap", delt_base_pts, skin_fill(prefix + "Deltoid", -12, 12, skin)))

    if is_near:
        out.append(stroke_shape(i3, f"{prefix}BicepsGroove", [(12.0, -1.5), (ua_len - 6.0, -1.2)], 1.2, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i3, f"{prefix}UpperArmHi", [(12.0, -5.5), (ua_len - 8.0, -4.8)], 2.8, HIGHLIGHT, 2.8))
    out.append(stroke_shape(i3, f"{prefix}UpperArmSh", [(10.0, 6.2), (ua_len - 8.0, 5.2)], 3.6, CORE_SHADOW, 3.2))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UpperArm", -11, 11, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. Articulated Hip-Hinge Leg Rig (Glutes, Hamstrings, Quads, Soleus)
def swing_leg_rig(prefix, is_near):
    """Articulated Thigh (`hip -> knee`) + Shin (`knee -> ankle`) + Planted Foot on `FLOOR = 300.0` with:
    - Gluteus maximus (`Glúteo mayor` — glowing target #5)
    - Hamstrings (`Isquiotibiales` — glowing target #6)
    - Vastus lateralis (`Vasto lateral` — glowing target #7)
    - Rectus femoris (`Recto femoral` — glowing target #8)
    - Vastus medialis (`Vasto medial` — glowing target #9)
    - Soleus (`Sóleo` — glowing target #10)
    """
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN if is_near else SKIN_FAR
    shorts = SHORTS if is_near else SHORTS_FAR
    hip_k = "hip_near" if is_near else "hip_far"
    knee_k = "knee_near" if is_near else "knee_far"
    th_ang_k = "thigh_near_ang" if is_near else "thigh_far_ang"
    th_sc_k = "thigh_near_sc" if is_near else "thigh_far_sc"
    sh_ang_k = "shin_near_ang" if is_near else "shin_far_ang"
    sh_sc_k = "shin_near_sc" if is_near else "shin_far_sc"
    ax, ay = ANKLE_NEAR if is_near else ANKLE_FAR
    th_len = THIGH_NEAR_LEN if is_near else THIGH_FAR_LEN
    sh_len = SHIN_NEAR_LEN if is_near else SHIN_FAR_LEN

    thigh_id, shin_id = nid(), nid()
    key_double(thigh_id, 13, lambda p: p[hip_k][0])
    key_double(thigh_id, 14, lambda p: p[hip_k][1])
    key_double(thigh_id, 15, lambda p: p[th_ang_k])
    key_double(thigh_id, 16, lambda p: p[th_sc_k])

    key_double(shin_id, 13, lambda p: p[knee_k][0])
    key_double(shin_id, 14, lambda p: p[knee_k][1])
    key_double(shin_id, 15, lambda p: p[sh_ang_k])
    key_double(shin_id, 16, lambda p: p[sh_sc_k])

    p0 = POSES[0]

    # Posterior chain & quadriceps stay strongly active in both the loaded bottom hinge (0.55) and top lockout (1.0)
    def glute_t(p):
        return 0.56 + 0.44 * (p["r"] ** 0.72)

    def hamstring_t(p):
        return 0.58 + 0.42 * ((1.0 - 0.35 * p["r"]) ** 0.8)

    def quad_t(p):
        return 0.52 + 0.48 * (p["r"] ** 0.78)

    def soleus_t(p):
        return 0.48 + 0.50 * (p["r"] ** 0.80)

    # Local Thigh Frame (`(0,0)` at Hip -> `(th_len, 0)` at Knee; `th_ang` ~ +36 deg at r=0 -> +84 deg at r=1):
    # - Local `-Y` (`th_ang - 90 deg` = front-right) is ANTERIOR (Rectus Femoris & Vastus Medialis).
    # - Local `0` (central femur) is LATERAL (Vastus Lateralis).
    # - Local `+Y` (`th_ang + 90 deg` = rear-left) is POSTERIOR (Gluteus Maximus & Hamstrings / Biceps Femoris).
    thigh_pts = [
        (-14.0, -7.5), (12.0, -12.0), (38.0, -11.5), (60.0, -8.0),
        (th_len + 3.0, -5.5), (th_len + 3.0, 6.5), (52.0, 10.8),
        (24.0, 14.8), (-4.0, 17.5), (-16.0, 7.5),
    ]
    shorts_cuff_pts = [
        (-14.0, -8.5), (18.0, -12.2), (18.5, 15.2), (-6.0, 18.0), (-16.5, 7.5),
    ]
    # Target Muscle #5: Glúteo mayor (posterior hip/buttock curve at `x = -15..16, y = +2..+17`)
    glute_pts = [
        (-15.0, 1.5), (2.0, 2.5), (16.5, 6.5), (14.0, 14.8), (-4.0, 17.2), (-15.5, 9.5),
    ]
    # Target Muscle #6: Isquiotibiales (posterior thigh belly at `x = 14..60, y = +2.5..+13.5`)
    hamstring_pts = [
        (14.0, 3.2), (36.0, 2.8), (58.0, 3.5), (60.0, 8.2), (38.0, 12.8), (16.0, 13.8),
    ]
    # Target Muscle #7: Vasto lateral (central-anterior lateral sweep at `x = 12..56, y = -4.5..+3.2`)
    vastus_lat_pts = [
        (12.0, -4.2), (34.0, -4.5), (55.0, -3.2), (56.0, 2.2), (34.0, 3.0), (13.0, 2.2),
    ]
    # Target Muscle #8: Recto femoral (anterior thigh belly at `x = 8..58, y = -11.5..-4.0`)
    rectus_femoris_pts = [
        (8.0, -5.0), (24.0, -11.2), (44.0, -10.8), (58.0, -7.2), (48.0, -3.8), (24.0, -4.0),
    ]
    # Target Muscle #9: Vasto medial (VMO teardrop just above the anterior-medial knee at `x = 44..66, y = -10.5..-3.5`)
    vmo_pts = [
        (44.0, -9.5), (58.0, -10.2), (66.0, -6.8), (58.0, -3.2), (44.0, -4.5),
    ]

    # Local Shin Frame (`(0,0)` at Knee -> `(sh_len, 0)` at Ankle; `sh_ang` ~ +105 deg at r=0 -> +94 deg at r=1):
    # - Local `-Y` is ANTERIOR (Shin / Tibialis Anterior).
    # - Local `+Y` is POSTERIOR (Gastrocnemius & Soleus).
    shin_pts = [
        (-4.0, -6.5), (20.0, -6.2), (44.0, -4.8), (sh_len, -3.8),
        (sh_len + 2.0, 4.2), (44.0, 5.2), (22.0, 10.8), (6.0, 8.2), (-4.0, 5.0),
    ]
    # Target Muscle #10: Sóleo (lower/outer posterior calf belly running down toward the Achilles tendon, `x = 18..56, y = +1..+8.5`)
    soleus_pts = [
        (18.0, 1.5), (38.0, 1.2), (56.0, 1.8), (55.0, 5.2), (36.0, 8.5), (20.0, 8.2),
    ]

    # Planted Bare/Studio Foot on FLOOR = 300.0 pointing right (+X)
    foot_pts = [
        (ax - 7.5, ay - 3.0), (ax + 6.0, ay - 2.5), (ax + 21.0, ay + 4.5),
        (ax + 26.5, ay + 9.5), (ax + 22.0, ay + 13.5), (ax + 4.0, ay + 12.8),
        (ax - 8.5, ay + 10.5), (ax - 9.5, ay + 3.5),
    ]

    out = [f'{ind}<Node name="{prefix}SwingLegGroup">']

    # --- Layer 1: Thigh (`hip -> knee`) with Compression Shorts, Gluteus Maximus, Hamstrings & 3 Quadriceps Heads ---
    out.append(
        f'{i2}<Node x="{f(p0[hip_k][0])}" y="{f(p0[hip_k][1])}" '
        f'rotation="{f(p0[th_ang_k])}" scaleX="{f(p0[th_sc_k])}" name="{prefix}Thigh" id="{thigh_id}">'
    )
    # Glowing Quadriceps (Vastus Medialis VMO, Rectus Femoris, Vastus Lateralis) & Hamstrings
    out.append(smooth_shape(i3, f"{prefix}VastusMedialis", vmo_pts, muscle_paint_fn(prefix + "VMO", quad_t, 0.9)))
    out.append(smooth_shape(i3, f"{prefix}RectusFemoris", rectus_femoris_pts, muscle_paint_fn(prefix + "RF", quad_t, 0.95)))
    if is_near:
        out.append(stroke_shape(i3, f"{prefix}QuadSeparation", [(16.0, -4.2), (36.0, -4.2), (54.0, -3.2)], 1.1, "807F1D1D", 0.4))
        out.append(stroke_shape(i3, f"{prefix}HamstringSeparation", [(16.0, 3.0), (36.0, 2.8), (56.0, 3.2)], 1.1, "807F1D1D", 0.4))
    out.append(smooth_shape(i3, f"{prefix}VastusLateralis", vastus_lat_pts, muscle_paint_fn(prefix + "VL", quad_t, 0.95)))
    out.append(smooth_shape(i3, f"{prefix}Hamstrings", hamstring_pts, muscle_paint_fn(prefix + "Ham", hamstring_t, 0.95)))

    # Glowing Gluteus Maximus on top of the posterior hip + Compression Shorts Cuff
    out.append(smooth_shape(i3, f"{prefix}GluteusMaximus", glute_pts, muscle_paint_fn(prefix + "Glute", glute_t, 0.95)))
    out.append(stroke_shape(i3, f"{prefix}ShortsHem", [(17.8, -11.8), (18.2, 1.5), (18.0, 14.5)], 1.6, "660F172A", 0.6))
    out.append(smooth_shape(i3, f"{prefix}ThighShorts", shorts_cuff_pts, skin_fill(prefix + "Shorts", -12, 18, shorts)))

    if is_near:
        out.append(stroke_shape(i3, f"{prefix}ThighHi", [(18.0, -7.8), (38.0, -7.5), (54.0, -5.8)], 3.4, "73FFFFFF", 3.2))
    out.append(stroke_shape(i3, f"{prefix}ThighCoreSh", [(12.0, 11.5), (36.0, 10.2), (56.0, 6.2)], 4.2, CORE_SHADOW, 4.0))
    out.append(smooth_shape(i3, f"{prefix}ThighBase", thigh_pts, skin_fill(prefix + "Thigh", -12, 17, skin)))
    out.append(ellipse_shape(i3, f"{prefix}Knee", th_len, 0.0, 15.0, 14.0, skin_fill(prefix + "Knee", -7, 7, skin)))
    out.append(f"{i2}</Node>")

    # --- Layer 2: Stationary Planted Foot on FLOOR = 300.0 ---
    if is_near:
        out.append(stroke_shape(i2, f"{prefix}FootHi", [(ax + 4.0, ay - 0.5), (ax + 16.0, ay + 4.2), (ax + 23.0, ay + 8.5)], 2.2, HIGHLIGHT, 2.2))
    out.append(stroke_shape(i2, f"{prefix}FootSoleSh", [(ax - 7.5, ay + 10.5), (ax + 8.0, ay + 12.2), (ax + 22.0, ay + 12.5)], 2.4, CORE_SHADOW, 1.8))
    out.append(smooth_shape(i2, f"{prefix}PlantedFoot", foot_pts, skin_fill(prefix + "Foot", ay - 3, ay + 14, skin)))

    # --- Layer 3: Shin (`knee -> ankle`) with Glowing Soleus & Gastrocnemius ---
    out.append(
        f'{i2}<Node x="{f(p0[knee_k][0])}" y="{f(p0[knee_k][1])}" '
        f'rotation="{f(p0[sh_ang_k])}" scaleX="{f(p0[sh_sc_k])}" name="{prefix}Shin" id="{shin_id}">'
    )
    out.append(smooth_shape(i3, f"{prefix}Soleus", soleus_pts, muscle_paint_fn(prefix + "Soleus", soleus_t, 0.9)))
    if is_near:
        out.append(stroke_shape(i3, f"{prefix}GastrocCut", [(6.0, 3.5), (20.0, 7.5), (32.0, 3.8)], 1.3, SOFT_SHADOW, 1.0))
        out.append(stroke_shape(i3, f"{prefix}ShinHi", [(8.0, -4.5), (30.0, -3.8), (52.0, -2.8)], 2.8, HIGHLIGHT, 3.0))
    out.append(stroke_shape(i3, f"{prefix}ShinSh", [(8.0, 5.8), (28.0, 7.8), (52.0, 3.5)], 3.8, CORE_SHADOW, 3.5))
    out.append(smooth_shape(i3, f"{prefix}ShinBase", shin_pts, skin_fill(prefix + "Shin", -7, 11, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 4. Articulated Hip-Hinge Torso, Upper Pectoral, Serratus & Canonical 3/4 Head
def hinging_torso_and_head_rig():
    """Articulated Torso (`hip_near -> sh_near`) with:
    - Canonical Volumetric 3/4 Head (cropped dark hair, ear, brow, eye, nose, mouth) with counter-rotating neck
    - Parte superior del pectoral (`Upper pectoralis major` — glowing target #3)
    - Serrato anterior (`Serratus anterior` — glowing target #4)
    - Sculpted sternocostal chest, 6-pack rectus abdominis, external obliques, and pelvis compression shorts
    """
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    torso_id, head_id = nid(), nid()
    key_double(torso_id, 13, lambda p: p["hip_near"][0])
    key_double(torso_id, 14, lambda p: p["hip_near"][1])
    key_double(torso_id, 15, lambda p: p["torso_ang"])
    key_double(torso_id, 16, lambda p: p["torso_sc"])
    key_double(head_id, 15, lambda p: p["neck_local"])

    p0 = POSES[0]

    def upper_pec_t(p):
        return 0.46 + 0.54 * (p["r"] ** 0.78)

    def serratus_t(p):
        return 0.48 + 0.52 * (p["r"] ** 0.76)

    # Local Torso Frame (`(0,0)` at `hip_near` -> `(TORSO_LEN=84, 0)` at `sh_near`; `torso_ang` from -38 deg to -88.5 deg):
    # - Local `+X` runs from the hip up the spine to the shoulder (`x = 0..84`).
    # - Local `+Y` (`torso_ang + 90 deg` = +52 deg to +1.5 deg = front-right) is ANTERIOR (Chest, 6-Pack Abs, Chin/Face).
    # - Local `-Y` (`torso_ang - 90 deg` = -128 deg to -178.5 deg = rear-left) is POSTERIOR (Upper/Lower Back, Occiput).

    # 1. Pelvis Compression Shorts (`x = -16..18`)
    pelvis_shorts_pts = [
        (-16.0, -14.5), (16.0, -13.5), (18.0, 14.5), (-8.0, 15.0), (-18.0, 2.0),
    ]

    # 2. Full Torso Silhouette (`x = -12..88, y = -16..+20`)
    torso_pts = [
        (-12.0, -14.0), (18.0, -13.5), (48.0, -15.5), (78.0, -15.0),
        (88.0, -4.0), (86.0, 14.5), (66.0, 20.5), (44.0, 17.5),
        (18.0, 15.0), (-12.0, 13.5),
    ]

    # 3. Canonical Sternocostal Chest Plate + Target Muscle #3: Parte superior del pectoral (Clavicular Head)
    sternal_pec_pts = [
        (56.0, 1.5), (74.0, 1.0), (76.0, 17.5), (62.0, 20.0), (54.0, 12.5),
    ]
    sternal_pec_paint = (
        '<Fill name="SternalPecFill"><SolidColor colorValue="140F172A" name="SternalPecCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="SternalPecStroke"><SolidColor colorValue="3D0F172A" name="SternalPecEdge"/></Stroke>'
    )
    upper_pec_pts = [
        (68.0, 0.5), (84.0, 1.5), (85.5, 14.8), (74.0, 17.2), (66.5, 8.5),
    ]

    # 4. Target Muscle #4: Serrato anterior (3 glowing finger-like slips on the lateral ribcage at `x = 38..58, y = -1..+11`)
    serratus_1_pts = [(50.0, -0.5), (58.0, 2.5), (56.0, 6.8), (47.5, 3.8)]
    serratus_2_pts = [(43.5, 1.0), (51.5, 4.0), (49.5, 8.2), (41.0, 5.2)]
    serratus_3_pts = [(37.0, 2.5), (45.0, 5.5), (43.0, 9.5), (35.0, 6.5)]

    # 5. Sculpted Anterior 6-Pack Rectus Abdominis Blocks (`x = 20..54, y = 7..17`)
    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1A0F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="AbsEdge"><SolidColor colorValue="400F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        [(43.0, 8.0), (53.0, 8.5), (52.5, 16.5), (42.5, 16.0)],
        [(31.5, 7.5), (41.0, 8.0), (40.5, 15.8), (31.0, 15.2)],
        [(20.0, 7.0), (29.5, 7.5), (29.0, 15.0), (19.5, 14.5)],
    ]

    # 6. Canonical Volumetric 3/4 Head & Neck (pivoting at `(86.0, -1.0)` inside TorsoRig):
    #    In HeadNode local coordinates (`+X` = up the cervical axis/crown, `+Y` = facing front-right):
    neck_pts = [
        (-4.0, -7.5), (18.0, -6.5), (18.0, 8.5), (-2.0, 9.5),
    ]
    head_pts = [
        (15.0, -9.5),   # occiput / back of skull
        (26.0, -10.5),  # posterior crown
        (36.0, -5.5),   # top cranial dome
        (37.5, 4.5),    # anterior crown
        (32.0, 11.5),   # upper forehead facing front-right (+Y)
        (26.0, 13.5),   # brow ridge
        (20.5, 15.5),   # nose bridge & tip
        (16.0, 14.0),   # upper/lower lip
        (11.0, 13.0),   # strong chin tip
        (8.5, 6.5),     # under-chin / jawline
        (10.5, -2.5),   # mandible angle (gonion)
    ]
    hair_pts = [
        (30.5, 11.8), (37.5, 5.5), (37.5, -5.0), (27.0, -11.0),
        (16.0, -10.0), (13.5, -4.5), (21.0, -3.0), (27.0, 1.5), (29.0, 8.5),
    ]

    out = [
        f'{ind}<Node x="{f(p0["hip_near"][0])}" y="{f(p0["hip_near"][1])}" '
        f'rotation="{f(p0["torso_ang"])}" scaleX="{f(p0["torso_sc"])}" name="HingingTorsoRig" id="{torso_id}">'
    ]

    # --- 1. Canonical 3/4 Head & Neck (pivoting at shoulder/cervical base `(86.0, -1.0)`) ---
    out.append(f'{i2}<Node x="86.0" y="-1.0" rotation="{f(p0["neck_local"])}" name="HeadAndNeck" id="{head_id}">')
    out.append(smooth_shape(i3, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 15, -11, 37, 12, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i3, "Ear", 19.5, -1.5, 8.0, 5.2, solid("Ear", "FFA3B1C4"), rot_deg=10.0))
    out.append(stroke_shape(i3, "BrowShade", [(26.5, 9.0), (26.0, 13.5)], 1.4, "590F172A", 0.8))
    out.append(stroke_shape(i3, "EyeLine", [(24.5, 9.2), (24.2, 12.0)], 1.1, "730F172A", 0.4))
    out.append(stroke_shape(i3, "MouthLine", [(15.5, 10.5), (15.8, 13.8)], 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i3, "HeadHi", [(29.0, 10.0), (34.5, 4.0), (34.0, -4.0)], 2.8, HIGHLIGHT, 3.0))
    out.append(stroke_shape(i3, "JawShadow", [(11.0, -1.5), (9.0, 6.0), (11.5, 12.0)], 2.4, CORE_SHADOW, 2.2))
    out.append(smooth_shape(i3, "Head", head_pts, skin_fill("Head", -11, 16, SKIN, x0=9, x1=37)))
    out.append(stroke_shape(i3, "SCMLine", [(2.0, 3.5), (10.0, 1.5), (17.0, -1.0)], 1.4, SOFT_SHADOW, 1.0))
    out.append(smooth_shape(i3, "Neck", neck_pts, skin_fill("Neck", -8, 10, SKIN)))
    out.append(f"{i2}</Node>")

    # --- 2. Target Muscles #3 & #4: Upper Pectoralis Major & Serratus Anterior ---
    out.append(stroke_shape(i2, "UpperPecHi", [(72.0, 4.5), (82.0, 6.5), (84.0, 13.0)], 1.8, "66FFFFFF", 1.6))
    out.append(smooth_shape(i2, "UpperPectoralisMajor", upper_pec_pts, muscle_paint_fn("UpperPec", upper_pec_t, 0.95)))
    out.append(stroke_shape(i2, "PecUnderFold", [(54.5, 13.0), (62.0, 20.0), (75.5, 17.5)], 2.0, CORE_SHADOW, 1.4))
    out.append(smooth_shape(i2, "SternalPectoral", sternal_pec_pts, sternal_pec_paint))

    out.append(smooth_shape(i2, "Serratus1", serratus_1_pts, muscle_paint_fn("Serratus1", serratus_t, 0.85)))
    out.append(smooth_shape(i2, "Serratus2", serratus_2_pts, muscle_paint_fn("Serratus2", serratus_t, 0.85)))
    out.append(smooth_shape(i2, "Serratus3", serratus_3_pts, muscle_paint_fn("Serratus3", serratus_t, 0.85)))

    # --- 3. 6-Pack Abs, Pelvis Compression Shorts & Torso Base ---
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "ObliqueLine1", [(24.0, 1.5), (32.0, 5.5)], 1.2, "380F172A", 0.8))
    out.append(stroke_shape(i2, "ObliqueLine2", [(16.0, 2.0), (24.0, 6.0)], 1.2, "380F172A", 0.8))
    out.append(stroke_shape(i2, "WaistbandLine", [(16.5, -13.0), (17.5, 0.0), (17.5, 14.0)], 1.8, "660F172A", 0.8))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts_pts, skin_fill("PelvisShorts", -15, 15, SHORTS)))

    out.append(stroke_shape(i2, "BackErectorSh", [(18.0, -10.5), (48.0, -12.0), (76.0, -11.5)], 4.5, CORE_SHADOW, 4.2))
    out.append(stroke_shape(i2, "TorsoFrontHi", [(22.0, 10.5), (48.0, 12.5), (68.0, 14.5)], 3.8, HIGHLIGHT, 3.8))
    out.append(smooth_shape(i2, "TorsoBase", torso_pts, skin_fill("Torso", -16, 20, SKIN, x0=-12, x1=88)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 5. Scene Assembly (RML First Child = Topmost Layer)
def build_rml():
    global _id
    _id = 0
    KEYED.clear()

    near_arm_xml = swing_arm_rig("Near", True)
    near_leg_xml = swing_leg_rig("Near", True)
    torso_head_xml = hinging_torso_and_head_rig()
    kb_xml = kettlebell_3d_rig()
    far_arm_xml = swing_arm_rig("Far", False)
    far_leg_xml = swing_leg_rig("Far", False)

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
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="KettlebellSwing" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Right) Swing Arm (Anterior & Lateral Deltoids, Forearm & Gripping Fist) -->
{near_arm_xml}

        <!-- 2. Mid-Foreground: Near (Right) Leg (Gluteus Maximus, Hamstrings, Vastus Lateralis, Rectus Femoris, VMO, Soleus) -->
{near_leg_xml}

        <!-- 3. Midground: Articulated Hip-Hinge Torso, Upper Pectoral, Serratus Anterior & Canonical 3/4 Head -->
{torso_head_xml}

        <!-- 4. Heavy 3D Cast-Iron Kettlebell (Passes Between Near & Far Legs at Bottom Hinge -> Shoulder Float at Top) -->
{kb_xml}

        <!-- 5. Background: Far (Left) Swing Arm & Far (Left) Leg -->
{far_arm_xml}
{far_leg_xml}

        <!-- 6. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="316" y="{f(FLOOR - 2)}" scaleX="1.05" scaleY="0.08" name="BodyShadow">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="KettlebellSwing" id="0:60">
{keyed_objects_xml}
        </LinearAnimation>
    </Artboard>
</Rive>
"""


# ---------------------------------------------------------------- Verbatim Rive 7.3 Binary Compiler (52-byte TOC)
def _compile_rml_bytes(rml_path):
    """Byte-for-byte Rive 7.3 binary compiler matching `~/.rive/bin/rive . --once`."""
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
    riv_out = HERE / "kettlebell_swing.riv"
    riv_out.write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    legacy_mk = REPO / "assets/animations/kettlebell_swing.movekit"
    if legacy_mk.exists():
        legacy_mk.unlink()

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png

    for fr, tag in ((0, "frame_start"), (38, "frame_mid"), (74, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(680, 16, 290))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes)} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
