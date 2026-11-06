#!/usr/bin/env python3
"""Generate deadlift.rml — 60 FPS, 16:9 (640x360, FLOOR = 300.0) HD procedural Rive animation for Deadlift.

Matches the repository visual standard and the 2-panel (A: bottom setup, B: standing lockout)
3/4 rear-left Conventional Barbell Deadlift reference illustration:
- 3/4 rear-left isometric view on `FLOOR = 300.0`, athlete facing forward-left:
  * Sculpted dorsal back (`Trapezius`, `Scapulae`, `Latissimus Dorsi`, `Erector Spinae`), left deltoid,
    triceps, forearm, and pronated hand in the near-left foreground.
  * 3/4 rear-left head & neck (short dark hair cap, left ear, brow/nose/jaw profile looking forward-left).
  * Glutes (`Gluteus Maximus` & `Gluteus Medius`) on the rear-right pelvis covered by sleek
    semi-translucent dark compression shorts (`#800F172A` / `#8C1E293B`) so the glowing red gluteal
    muscle fibers and upper hamstrings/quads remain clearly visible through the shorts.
  * Both legs (`FarRightLeg` in background-right, `NearLeftLeg` in foreground-left) planted on
    `FLOOR = 300.0` (`ANKLE_FAR = (344, 272)`, `ANKLE_NEAR = (300, 286)`) with bare sculpted feet,
    white Achilles tendons, lateral & medial `Gastrocnemius`/`Soleus` calf heads, posterior
    `Hamstrings` (`Biceps Femoris`, `Semitendinosus`), anterior-lateral `Quadriceps` (`Vastus Lateralis`,
    `Rectus Femoris`), and the signature white lateral Iliotibial (`IT`) band.
- 3D Olympic Barbell with 45-lb Radial-Spoke Bumper Plates (3-Layer Depth Split):
  1. `FarBarbellPlate` (behind `FarRightLeg`): Far-right 45-lb bumper plate (`56x88`, rotated `-12 deg`)
     with 3D rim bevel, inner ring, 4 radial spoke ridges, and collar.
  2. `MidBarbellShaft` (between `FarRightLeg` and `NearLeftLeg`): Gunmetal/chrome steel bar shaft
     passing in front of the far shin and behind the near shin/thigh.
  3. `NearBarbellPlateAndLeftShaft` (in front of `NearLeftArm` / `NearLeftLeg`): Large near-left 45-lb
     Olympic bumper plate (`66x104`, rotated `-12 deg`, resting directly on `FLOOR = 300.0` at `r = 0.0`),
     with 3D rim thickness, 4 radial spoke ridges, chrome collar, and protruding outer bar sleeve.
- Conventional Deadlift Kinematics (`DURATION = 168` frames / `2.8s` @ `60 FPS`):
  * `0..14`: Bottom floor setup hold (`r = 0.0`, Panel A of reference)
  * `14..70`: Smooth, powerful concentric pull from floor to standing lockout (`r: 0.0 -> 1.0`)
  * `70..88`: Standing lockout hold at top (`r = 1.0`, Panel B of reference)
  * `88..154`: Controlled eccentric hip-hinge + knee-flexion lowering back to the floor (`r: 1.0 -> 0.0`)
  * `154..168`: Bottom floor setup hold (`r = 0.0`)

Run:
    python3 rive_animations/deadlift/gen_deadlift.py            # writes scene.rml
    python3 rive_animations/deadlift/gen_deadlift.py --publish  # builds .riv + copies asset & 256x256 thumbnail
"""
import math
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "scene.rml"
ASSET_RIV = REPO / "assets/animations/deadlift.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/deadlift.png"
THUMB_ADVANCE = "1.30s"      # Frame 78: Standing lockout hold (Panel B of reference)
THUMB_VIEWPORT = "1280x720"  # 2x the 640x360 artboard
THUMB_CROP = (560, 40, 260)  # square size, offsetY, offsetX in the 2x render
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

# 16:9 standard canvas
W, H = 640, 360
FLOOR = 300.0

# Timeline: 168 frames @ 60 FPS (2.80s cycle)
DURATION = 168
STEP = 2

# Stationary ankle anchors on FLOOR = 300.0
ANKLE_NEAR = (300.0, 286.0)
ANKLE_FAR = (334.0, 274.0)

# Reference rest lengths for articulated limb segments
SHIN_NEAR_LEN = 66.0
THIGH_NEAR_LEN = 74.0
SHIN_FAR_LEN = 66.0
THIGH_FAR_LEN = 72.0
TORSO_LEN = 88.0
UPPER_ARM_LEN = 50.0
FOREARM_LEN = 46.0


def cubic_bezier(x1, y1, x2, y2):
    def bez(t, a, b):
        return 3 * a * t * (1 - t) ** 2 + 3 * b * t * t * (1 - t) + t ** 3

    def ease(x):
        if x <= 0.0:
            return 0.0
        if x >= 1.0:
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if bez(mid, x1, x2) < x:
                lo = mid
            else:
                hi = mid
        return bez((lo + hi) / 2, y1, y2)

    return ease


EASE_PULL = cubic_bezier(0.36, 0.0, 0.24, 1.0)
EASE_LOWER = cubic_bezier(0.38, 0.0, 0.34, 1.0)


def deadlift_progress(frame):
    """Returns deadlift progress r in [0.0, 1.0] across 168 frames:
    - 0..14: Bottom floor setup hold (r = 0.0, Panel A)
    - 14..70: Concentric pull from floor to standing lockout (r: 0.0 -> 1.0)
    - 70..88: Standing lockout hold at top (r = 1.0, Panel B)
    - 88..154: Controlled eccentric lowering back to floor (r: 1.0 -> 0.0)
    - 154..168: Bottom floor setup hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 14:
        return 0.0
    if fr <= 70:
        return EASE_PULL((fr - 14) / 56.0)
    if fr <= 88:
        return 1.0
    if fr <= 154:
        return 1.0 - EASE_LOWER((fr - 88) / 66.0)
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
    sc = max(0.40, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute 3/4 rear-left Conventional Barbell Deadlift joint transforms at progress r in [0.0, 1.0]."""
    # 1. Knees: Flexed forward-left over the bar at r=0.0 (Panel A) -> Straightened back into lockout at r=1.0 (Panel B)
    knee_near = quad_interp_pt((266.0, 224.0), (284.0, 223.0), (294.0, 222.0), r)
    knee_far = quad_interp_pt((302.0, 212.0), (316.0, 211.0), (322.0, 210.0), r)

    # 2. Hips / Pelvis: Hinged back-right at r=0.0 (Panel A) -> Driven forward-up into full hip lockout at r=1.0 (Panel B)
    hip_near = quad_interp_pt((352.0, 192.0), (324.0, 174.0), (302.0, 158.0), r)
    hip_far = quad_interp_pt((370.0, 182.0), (342.0, 164.0), (320.0, 149.0), r)

    # 3. Shoulders & Dorsal Torso: Hinged at ~32 deg above horizontal at r=0.0 -> Tall upright lockout (~85 deg) at r=1.0
    sh_near = quad_interp_pt((260.0, 134.0), (275.0, 98.0), (293.0, 72.0), r)
    sh_far = quad_interp_pt((294.0, 122.0), (310.0, 88.0), (326.0, 64.0), r)

    # 4. 3D Olympic Barbell Center & Hands Locked to the Bar Shaft
    #    The bar axis runs at ~ -18.8 deg (delta from BAR_CENTER to HAND_NEAR is (-25.0, +8.5),
    #    delta to HAND_FAR is (+25.0, -8.5)).
    #    - At r=0.0: BAR_CENTER = (287.0, 229.5), HAND_NEAR = (262.0, 238.0), Near Bumper Plate bottom at y = 299.8 (FLOOR=300!)
    #    - At r=0.5: BAR_CENTER = (285.0, 192.0), HAND_NEAR = (260.0, 200.5)
    #    - At r=1.0: BAR_CENTER = (283.0, 158.0), HAND_NEAR = (258.0, 166.5) (in front-left of the thigh/hip as in Panel B!)
    bar_center = quad_interp_pt((287.0, 229.5), (285.0, 192.0), (283.0, 158.0), r)
    hand_near = (bar_center[0] - 25.0, bar_center[1] + 8.5)
    hand_far = (bar_center[0] + 25.0, bar_center[1] - 8.5)

    # 5. Straight Hanging Arms under heavy load (Elbow slightly outside/left of the Shoulder -> Hand line)
    elb_near = (
        lerp(sh_near[0], hand_near[0], 0.52) - lerp(2.5, 3.5, r),
        lerp(sh_near[1], hand_near[1], 0.52),
    )

    # 6. Segment transforms (x, y, rotation, scaleX)
    shin_near_ang, shin_near_sc = seg_xform(knee_near, ANKLE_NEAR, SHIN_NEAR_LEN)
    thigh_near_ang, thigh_near_sc = seg_xform(hip_near, knee_near, THIGH_NEAR_LEN)
    shin_far_ang, shin_far_sc = seg_xform(knee_far, ANKLE_FAR, SHIN_FAR_LEN)
    thigh_far_ang, thigh_far_sc = seg_xform(hip_far, knee_far, THIGH_FAR_LEN)
    torso_ang, torso_sc = seg_xform(hip_near, sh_near, TORSO_LEN)
    ua_near_ang, ua_near_sc = seg_xform(sh_near, elb_near, UPPER_ARM_LEN)
    fa_near_ang, fa_near_sc = seg_xform(elb_near, hand_near, FOREARM_LEN)

    # 7. Head & Neck local rotation inside DorsalTorso:
    #    - At r=0.0 (torso_ang = +212.2 deg), neck_local = +14.0 deg -> world_head_ang = +226.2 deg (neutral cervical alignment).
    #    - At r=1.0 (torso_ang = +264.0 deg), neck_local = +6.0 deg  -> world_head_ang = +270.0 deg (upright head, horizontal forward-left gaze!).
    neck_local = math.radians(lerp(14.0, 6.0, r))

    # 8. Dynamic floor contact shadow of barbell (intense when plates rest on floor at r=0.0, softer as bar rises)
    bar_shadow_sx = lerp(1.15, 0.88, r)

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
        "ua_near_sc": ua_near_sc,
        "fa_near_ang": fa_near_ang,
        "fa_near_sc": fa_near_sc,
        "neck_local": neck_local,
        "bar_shadow_sx": bar_shadow_sx,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(deadlift_progress(fr)) for fr in FRAMES}

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

if __name__ == "__main__":
    for _fr in (0, 42, 78, 120, DURATION):
        _p = POSES[_fr if _fr in POSES else min(POSES.keys(), key=lambda k: abs(k - _fr))]
        print(
            f"f{_fr:3d} r={_p['r']:.3f} hip=({_p['hip_near'][0]:.1f},{_p['hip_near'][1]:.1f}) "
            f"sh=({_p['sh_near'][0]:.1f},{_p['sh_near'][1]:.1f}) "
            f"bar=({_p['bar_center'][0]:.1f},{_p['bar_center'][1]:.1f}) "
            f"torso_ang={math.degrees(_p['torso_ang']):+.1f}"
        )


# ---------------------------------------------------------------- RML Helpers
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
    """Catmull-Rom spline through pts, emitted as CubicMirroredVertex elements."""
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


# ---------------------------------------------------------------- Palette & Muscle Activation
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
TENDON = ("FFFFFFFF", "FFE2E8F0", "FFCBD5E1")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
ANATOMY_LINE = "520F172A"

# Semi-translucent dark compression shorts so the glowing Gluteus Maximus, Hamstrings, and Quads
# remain clearly visible underneath just like in Panels A and B of the reference image!
SHORTS_TRANSLUCENT = ("99334155", "881E293B", "990F172A")
SHORTS_FAR_TRANSLUCENT = ("991E293B", "880F172A", "99090D16")

# Muscle activation colors: warm orange (#FFF97316) at setup -> intense crimson-red (#FFF43F5E) through pull & lockout
MUSCLE_LOW = (0xE6, 0xF9, 0x73, 0x16)
MUSCLE_HIGH = (0xFF, 0xEF, 0x3B, 0x4D)
MUSCLE_LINE_LOW = (0x80, 0x9A, 0x34, 0x12)
MUSCLE_LINE_HIGH = (0xE6, 0x7F, 0x1D, 0x1D)


def argb_lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return "".join(f"{round(lerp(x, y, t)):02X}" for x, y in zip(a, b))


def skin_fill(name, y0, y1, tones, x0=0, x1=0):
    return f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *tones, x0=x0, x1=x1)}</Fill>'


def skin_fill_outlined(name, y0, y1, tones, x0=0, x1=0, line=1.0, stroke_col="400F172A"):
    return (
        f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *tones, x0=x0, x1=x1)}</Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{stroke_col}" name="{name}EdgeCol"/></Stroke>'
    )


keys = []  # (objectId, propertyKey, kind, [(frame, value)])


def key_double(obj, prop, fn):
    keys.append((obj, prop, "double", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def key_color(obj, prop, fn):
    keys.append((obj, prop, "color", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def muscle_t(p):
    """Posterior-chain & leg activation intensity in [0.42, 1.0]: loaded orange-red at setup -> intense crimson at lockout."""
    return 0.42 + 0.58 * (p["r"] ** 0.78)


muscle_fill_ids = []  # (cid, scale)
muscle_line_ids = []  # (cid, scale)


def muscle_paint(name, scale=1.0, line=1.1):
    fid, lid = nid(), nid()
    muscle_fill_ids.append((fid, scale))
    muscle_line_ids.append((lid, scale))
    t0 = muscle_t(POSES[0]) * scale
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- 1. 3D Olympic Barbell Builders
def barbell_layers():
    """Returns (near_plate_xml, mid_shaft_xml, far_plate_xml) for the 3D Olympic Barbell with 45-lb bumper plates."""
    ind = "        "
    i2 = ind + "    "
    p0 = POSES[0]

    # Shared helper to animate any barbell layer at BAR_CENTER(r)
    def bar_node(name):
        bid = nid()
        key_double(bid, 13, lambda p: p["bar_center"][0])
        key_double(bid, 14, lambda p: p["bar_center"][1])
        return bid, f'{ind}<Node x="{f(p0["bar_center"][0])}" y="{f(p0["bar_center"][1])}" name="{name}" id="{bid}">'

    # --- Layer A (Frontmost): Near-Left 45-lb Bumper Plate, Collar, Left Shaft & Protruding Outer Sleeve ---
    # Plate center is at (-64.0, +21.8) relative to BAR_CENTER (so at r=0.0, y = 229.5 + 21.8 = 251.3, height=97 -> bottom rim at y=299.8 on FLOOR=300!)
    # Because pw = 58 (radius 29), the plate right edge is at dx = -35, leaving HAND_NEAR (dx = -25) 100% visible!
    _, near_open = bar_node("NearBarbellPlateAndSleeve")
    px, py = -64.0, 21.8
    pw, ph, prot = 58.0, 97.0, -12.0

    # Protruding outer bar sleeve from plate center (-64, +21.8) out to (-110, +37.5)
    sleeve_pts = [
        (-62.0, 18.0), (-109.0, 34.0), (-111.0, 40.5), (-64.0, 24.5),
    ]
    sleeve_fill = f'<Fill name="NearSleeveFill">{grad3("NearSleeveGrad", 18, 41, "FF94A3B8", "FF475569", "FF0F172A")}</Fill>'
    # Left shaft segment strictly from HAND_NEAR (-25, +8.5) into the inner plate collar (-58, +19.7)
    # so nothing in Layer A protrudes to the right of HAND_NEAR!
    left_shaft_pts = [
        (-25.0, 5.8), (-58.0, 17.1), (-59.6, 22.3), (-26.6, 11.0),
    ]
    shaft_fill = f'<Fill name="LeftShaftFill">{grad3("LeftShaftGrad", 5, 22, "FFCBD5E1", "FF64748B", "FF1E293B")}</Fill>'

    near_plate_face = (
        f'<Fill name="NearPlateFaceFill">{grad3("NearPlateFaceGrad", -49, 49, "FF334155", "FF182232", "FF090D16", x0=-26, x1=26)}</Fill>'
        '<Stroke thickness="1.6" join="round" name="NearPlateRimStroke"><SolidColor colorValue="FF475569" name="NearPlateRimCol"/></Stroke>'
    )
    near_plate_rim = f'<Fill name="NearPlateBackFill">{grad("NearPlateBackGrad", -29, -49, 29, 49, "FF0F172A", "FF020617")}</Fill>'
    near_ring_paint = (
        '<Fill name="NearRingFill"><SolidColor colorValue="FF111827" name="NearRingCol"/></Fill>'
        '<Stroke thickness="1.4" join="round" name="NearRingStroke"><SolidColor colorValue="FF334155" name="NearRingStrokeCol"/></Stroke>'
    )
    hub_paint = (
        f'<Fill name="NearHubFill">{grad3("NearHubGrad", -10, 10, "FF94A3B8", "FF475569", "FF1E293B")}</Fill>'
        '<Stroke thickness="1.2" join="round" name="NearHubStroke"><SolidColor colorValue="FFCBD5E1" name="NearHubStrokeCol"/></Stroke>'
    )

    near_xml = "\n".join([
        near_open,
        # 1. Protruding outer bar sleeve & end cap (drawn in front of the near plate face!)
        ellipse_shape(i2, "NearSleeveEndCap", -110.0, 37.2, 4.8, 7.2, solid("NearCap", "FF0F172A"), rot_deg=-12.0),
        ellipse_shape(i2, "NearSleeveEndRim", -110.0, 37.2, 6.2, 8.6, solid("NearCapRim", "FF64748B"), rot_deg=-12.0),
        stroke_shape(i2, "NearSleeveHi", [(-64.0, 19.8), (-87.0, 27.6), (-108.0, 34.8)], 1.6, "B3E2E8F0", 0.5),
        poly_shape(i2, "NearOuterSleeve", sleeve_pts, sleeve_fill, radius=1.2),
        # 2. Center chrome hub & 4 radial bumper-plate spoke ridges
        ellipse_shape(i2, "NearPlateHub", px, py, 11.5, 18.0, hub_paint, rot_deg=prot),
        stroke_shape(i2, "NearSpoke1", [(px - 5, py + 2), (px - 23, py + 8)], 2.2, "FF334155", 0.0),
        stroke_shape(i2, "NearSpoke2", [(px + 5, py - 2), (px + 22, py - 8)], 2.2, "FF334155", 0.0),
        stroke_shape(i2, "NearSpoke3", [(px - 2, py - 8), (px - 8, py - 39)], 2.2, "FF334155", 0.0),
        stroke_shape(i2, "NearSpoke4", [(px + 2, py + 8), (px + 8, py + 39)], 2.2, "FF334155", 0.0),
        # 3. Crisp right-side-up '45' bumper plate mark at bottom of plate face ("4" on left, "5" on right)
        polyline_stroke_shape(i2, "Near45Digit4A", [(px - 2.2, py + 28.5), (px - 6.2, py + 33.2), (px - 0.8, py + 33.2)], 1.35, "FF64748B", radius=0.15),
        polyline_stroke_shape(i2, "Near45Digit4B", [(px - 2.2, py + 28.5), (px - 2.2, py + 36.0)], 1.35, "FF64748B", radius=0.15),
        polyline_stroke_shape(
            i2,
            "Near45Digit5",
            [
                (px + 5.2, py + 28.5),
                (px + 1.4, py + 28.5),
                (px + 1.4, py + 31.8),
                (px + 4.8, py + 31.8),
                (px + 5.5, py + 33.5),
                (px + 4.6, py + 35.8),
                (px + 1.2, py + 35.8),
            ],
            1.35,
            "FF64748B",
            radius=0.25,
        ),
        # 4. Inner recessed ring, front plate face, and 3D rear rim thickness (+4.8 px right, -1.6 px up)
        ellipse_shape(i2, "NearPlateInnerRing", px, py, pw * 0.74, ph * 0.74, near_ring_paint, rot_deg=prot),
        ellipse_shape(i2, "NearPlateFace", px, py, pw, ph, near_plate_face, rot_deg=prot),
        ellipse_shape(i2, "NearPlateRim3D", px + 4.8, py - 1.6, pw, ph, near_plate_rim, rot_deg=prot),
        # 5. Inner collar & left bar shaft leading into HAND_NEAR
        ellipse_shape(i2, "NearInnerCollar", -55.0, 18.7, 8.2, 13.0, hub_paint, rot_deg=prot),
        stroke_shape(i2, "LeftShaftHi", [(-26.0, 7.2), (-41.0, 12.3), (-56.0, 17.5)], 1.4, "CCE2E8F0", 0.4),
        poly_shape(i2, "LeftBarShaft", left_shaft_pts, shaft_fill, radius=1.0),
        f"{ind}</Node>",
    ])

    # --- Layer B (Midground): Inner Barbell Shaft from HAND_NEAR (-25, +8.5) to Far Plate (+58, -19.6) ---
    # Drawn BEHIND NearLeftArmGroup, DorsalTorsoAndHead, NearThigh, NearShin, and FarThigh!
    _, mid_open = bar_node("MidBarbellShaft")
    mid_shaft_pts = [
        (-25.0, 5.8), (58.0, -22.3), (59.6, -17.1), (-23.4, 11.0),
    ]
    mid_shaft_fill = f'<Fill name="MidShaftFill">{grad3("MidShaftGrad", -22, 11, "FFCBD5E1", "FF64748B", "FF1E293B")}</Fill>'
    mid_xml = "\n".join([
        mid_open,
        stroke_shape(i2, "MidShaftHi", [(-24.0, 7.0), (16.0, -6.5), (56.0, -20.0)], 1.5, "CCE2E8F0", 0.4),
        poly_shape(i2, "MidBarShaft", mid_shaft_pts, mid_shaft_fill, radius=1.0),
        f"{ind}</Node>",
    ])

    # --- Layer C (Background): Far-Right 45-lb Bumper Plate & Far Sleeve behind FarRightLeg ---
    _, far_open = bar_node("FarBarbellPlate")
    fpx, fpy = 59.0, -20.0
    fpw, fph = 56.0, 88.0
    far_plate_face = (
        f'<Fill name="FarPlateFaceFill">{grad3("FarPlateFaceGrad", -44, 44, "FF263244", "FF111827", "FF060911", x0=-24, x1=24)}</Fill>'
        '<Stroke thickness="1.4" join="round" name="FarPlateRimStroke"><SolidColor colorValue="FF334155" name="FarPlateRimCol"/></Stroke>'
    )
    far_plate_rim = f'<Fill name="FarPlateBackFill">{grad("FarPlateBackGrad", -28, -44, 28, 44, "FF090D16", "FF020617")}</Fill>'
    far_xml = "\n".join([
        far_open,
        ellipse_shape(i2, "FarInnerCollar", 50.5, -17.1, 8.0, 12.5, hub_paint, rot_deg=prot),
        stroke_shape(i2, "FarSpoke1", [(fpx - 4, fpy + 2), (fpx - 21, fpy + 8)], 2.0, "FF1E293B", 0.0),
        stroke_shape(i2, "FarSpoke2", [(fpx + 4, fpy - 2), (fpx + 21, fpy - 8)], 2.0, "FF1E293B", 0.0),
        stroke_shape(i2, "FarSpoke3", [(fpx - 2, fpy - 8), (fpx - 8, fpy - 35)], 2.0, "FF1E293B", 0.0),
        stroke_shape(i2, "FarSpoke4", [(fpx + 2, fpy + 8), (fpx + 8, fpy + 35)], 2.0, "FF1E293B", 0.0),
        ellipse_shape(i2, "FarPlateInnerRing", fpx, fpy, fpw * 0.72, fph * 0.72, near_ring_paint, rot_deg=prot),
        ellipse_shape(i2, "FarPlateFace", fpx, fpy, fpw, fph, far_plate_face, rot_deg=prot),
        ellipse_shape(i2, "FarPlateRim3D", fpx + 4.2, fpy - 1.4, fpw, fph, far_plate_rim, rot_deg=prot),
        f"{ind}</Node>",
    ])

    return near_xml, mid_xml, far_xml


# ---------------------------------------------------------------- 2. Near & Far Leg Builders (Quads, IT Band, Hamstrings, Calves, Achilles)
def leg_rig(prefix, far):
    """3/4 rear-left leg rig with sculpted Quadriceps, white IT Band, Hamstrings, Gastrocnemius/Soleus, and white Achilles Tendon."""
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

    # Note on local coordinate axes for Thigh (Hip -> Knee) and Shin (Knee -> Ankle):
    # - For Thigh: Hip is upper-right, Knee is lower-left (angle ~ +100 deg at top lockout to +160 deg at bottom setup).
    #   Therefore:
    #     +X runs distally from Hip (0,0) -> Knee (THIGH_LEN=74, 0).
    #     +Y points DOWN-LEFT (the ANTERIOR-LATERAL Quadriceps side!).
    #     -Y points UP-RIGHT (the POSTERIOR Hamstrings / Glute fold side!).
    # - For Shin: Knee is upper-left, Ankle is lower-right (angle ~ +62 deg at bottom setup to +83 deg at top lockout).
    #   Therefore:
    #     +X runs distally from Knee (0,0) -> Ankle (SHIN_LEN=66, 0).
    #     +Y points DOWN-LEFT (the ANTERIOR Shin / Lateral Calf side!).
    #     -Y points UP-RIGHT (the POSTERIOR Gastrocnemius / Achilles Tendon side!).

    # 1. Stationary Bare Foot planted flat on FLOOR = 300.0 pointing forward-left
    ax, ay = ankle_pt
    foot_pts = [
        (ax - 7, ay - 3),    # anterior ankle instep
        (ax - 22, ay + 3),   # dorsal midfoot slope
        (ax - 38, ay + 6),   # forefoot / metatarsal bridge
        (ax - 44, ay + 8),   # distal toe tips pointing forward-left!
        (ax - 42, ay + 12),  # plantar toe pad on floor
        (ax - 24, ay + 12),  # plantar forefoot sole
        (ax - 10, ay + 11),  # medial plantar arch
        (ax + 6, ay + 12),   # plantar calcaneus heel pad on floor
        (ax + 10, ay + 7),   # rounded posterior heel
        (ax + 7, ay - 2),    # posterior Achilles entry
    ]

    # 2. Shin & Calf contour (Knee (0,0) -> Ankle (66,0))
    shin_pts = [
        (-8, 0), (-6, 8.5), (12, 9.2), (34, 8.0), (54, 6.2), (65, 5.2),
        (69, 0), (64, -5.8), (48, -7.2), (30, -14.2), (14, -15.5), (2, -11.5), (-6, -7.5),
    ]
    # White Achilles Tendon & Gastrocnemius aponeurosis on the lower posterior shin (x = 30..66)
    achilles_pts = [
        (28, -9.5), (44, -6.8), (64, -5.5), (66, 1.5), (48, 1.0), (34, -2.5),
    ]
    # Medial Gastrocnemius head (bulging on the posterior -Y border, x = 6..40)
    calf_medial_pts = [
        (5, -7.8), (15, -15.0), (30, -13.8), (41, -7.8),
        (32, -2.5), (18, -2.2), (6, -3.5),
    ]
    # Lateral Gastrocnemius & Soleus head (along the anterior-lateral +Y aspect of the lower leg, x = 6..48)
    calf_lateral_pts = [
        (6, -1.5), (20, -1.5), (36, -1.0), (49, 2.2),
        (38, 7.2), (20, 8.2), (6, 6.2),
    ]

    # 3. Thigh contour (Hip (0,0) -> Knee (74,0))
    # For FarThigh, start proximal cap at x = 0 so it stays cleanly inside DorsalTorso's GluteusMaximusFar & PelvisShorts!
    x_prox = 0 if far else -16
    x_prox_in = 2 if far else -12
    thigh_pts = [
        (x_prox, 0), (x_prox_in, 14.5), (10, 18.8), (34, 18.2), (56, 13.8), (70, 9.2),
        (78, 0), (69, -9.2), (50, -13.5), (28, -17.2), (8, -18.5), (x_prox_in, -14.5),
    ]
    # Anterior-Lateral Quadriceps (Vastus Lateralis & Rectus Femoris along +Y border, x = 4..64)
    quad_pts = [
        (4, 3.2), (22, 4.0), (44, 4.2), (64, 5.5),
        (54, 13.5), (34, 17.8), (12, 18.2), (2, 12.5),
    ]
    # Posterior Hamstrings (Biceps Femoris & Semitendinosus along -Y border, x = 6..66)
    hamstring_pts = [
        (6, -3.2), (26, -2.8), (48, -2.2), (66, -4.5),
        (52, -13.0), (30, -16.8), (10, -17.8), (2, -12.0),
    ]
    # Signature White/Silver Lateral Iliotibial (IT) Band running between Quads (+Y) and Hamstrings (-Y) into the lateral knee!
    it_band_pts = [
        (2, -3.5), (24, -2.8), (48, -2.2), (70, -2.0),
        (72, 4.2), (48, 4.0), (24, 3.5), (2, 3.2),
    ]
    # Semi-translucent proximal thigh compression shorts so red muscle fibers glow through!
    shorts_thigh_pts = [
        (0 if far else -18, 0), (2 if far else -13, 15.5), (10, 19.5), (28, 18.8),
        (28, -17.5), (10, -19.2), (2 if far else -13, -15.5),
    ]

    thigh_out = [
        f'{ind}<Node x="{f(p0[hip_key][0])}" y="{f(p0[hip_key][1])}" '
        f'rotation="{f(p0[th_ang_key])}" scaleX="{f(p0[th_sc_key])}" name="{prefix}Thigh" id="{th_id}">'
    ]
    # Semi-translucent compression shorts over upper thigh + dark charcoal hem stroke
    thigh_out.append(stroke_shape(i3, f"{prefix}ShortsHem", [(28, -17.0), (28, 0.0), (28, 18.2)], 1.6, "CC020617", 0.0))
    thigh_out.append(smooth_shape(i3, f"{prefix}ThighShorts", shorts_thigh_pts, skin_fill(prefix + "ThighShorts", -19, 19, shorts_tones)))
    # White Lateral Iliotibial (IT) Band + central fascial groove line
    if not far:
        thigh_out.append(stroke_shape(i3, f"{prefix}ITGroove", [(8, 0.4), (36, 0.8), (66, 1.0)], 1.2, "66475569", 0.4))
    thigh_out.append(smooth_shape(i3, f"{prefix}ITBand", it_band_pts, skin_fill_outlined(prefix + "ITBand", -4, 4, TENDON, line=0.9)))
    # Activated Quadriceps (Vastus Lateralis) & Hamstrings (Biceps Femoris + Semitendinosus)
    if not far:
        thigh_out.append(stroke_shape(i3, f"{prefix}QuadFiber", [(12, 11.5), (32, 11.8), (52, 9.5)], 1.2, "667F1D1D", 0.4))
        thigh_out.append(stroke_shape(i3, f"{prefix}HamFiber", [(14, -10.5), (34, -9.8), (54, -7.5)], 1.2, "667F1D1D", 0.4))
    thigh_out.append(smooth_shape(i3, f"{prefix}Quadriceps", quad_pts, muscle_paint(prefix + "Quad", scale=0.92 * m_scale, line=1.1)))
    thigh_out.append(smooth_shape(i3, f"{prefix}Hamstrings", hamstring_pts, muscle_paint(prefix + "Ham", scale=1.00 * m_scale, line=1.1)))
    thigh_out.append(smooth_shape(i3, f"{prefix}ThighSkin", thigh_pts, skin_fill_outlined(prefix + "Thigh", -18, 18, skin, line=1.1)))
    thigh_out.append(f"{ind}</Node>")

    shin_out = [f'{ind}<Node name="{prefix}ShinAndFootGroup">']
    # Shin & Calf (Knee -> Ankle)
    shin_out.append(
        f'{i2}<Node x="{f(p0[knee_key][0])}" y="{f(p0[knee_key][1])}" '
        f'rotation="{f(p0[sh_ang_key])}" scaleX="{f(p0[sh_sc_key])}" name="{prefix}Shin" id="{sh_id}">'
    )
    if not far:
        shin_out.append(stroke_shape(i3, f"{prefix}CalfSplit", [(6, -2.0), (22, -2.0), (38, -1.5)], 1.3, "807F1D1D", 0.3))
    shin_out.append(smooth_shape(i3, f"{prefix}CalfMedial", calf_medial_pts, muscle_paint(prefix + "CalfMed", scale=0.88 * m_scale, line=1.05)))
    shin_out.append(smooth_shape(i3, f"{prefix}CalfLateral", calf_lateral_pts, muscle_paint(prefix + "CalfLat", scale=0.86 * m_scale, line=1.05)))
    shin_out.append(smooth_shape(i3, f"{prefix}AchillesTendon", achilles_pts, skin_fill_outlined(prefix + "Achilles", -9, 2, TENDON, line=0.85)))
    shin_out.append(smooth_shape(i3, f"{prefix}ShinSkin", shin_pts, skin_fill_outlined(prefix + "Shin", -15, 9, skin, line=1.1)))
    shin_out.append(f"{i2}</Node>")

    # Planted Bare Foot on FLOOR = 300.0
    if not far:
        shin_out.append(stroke_shape(i2, f"{prefix}AnkleMalleolus", [(ax - 1, ay - 4), (ax + 1, ay + 2), (ax - 3, ay + 5)], 1.3, ANATOMY_LINE, 0.0))
        shin_out.append(stroke_shape(i2, f"{prefix}ToeCrease1", [(ax - 41, ay + 9), (ax - 36, ay + 9)], 1.0, ANATOMY_LINE, 0.0))
        shin_out.append(stroke_shape(i2, f"{prefix}ToeCrease2", [(ax - 39, ay + 11), (ax - 34, ay + 11)], 1.0, ANATOMY_LINE, 0.0))
    shin_out.append(smooth_shape(i2, f"{prefix}Foot", foot_pts, skin_fill_outlined(prefix + "Foot", ay - 3, ay + 12, skin, line=1.15)))
    shin_out.append(f"{ind}</Node>")

    return "\n".join(thigh_out), "\n".join(shin_out)


# ---------------------------------------------------------------- 3. Dorsal Torso, Glutes, Semi-Translucent Shorts & Head
def dorsal_torso_glutes_and_head():
    """3/4 rear-left Dorsal Torso (Traps, Scapulae, Lats, Erector Spinae), Gluteus Maximus/Medius, Shorts, and Head."""
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

    # Note on DorsalTorso local frame:
    # Origin (0,0) = HIP_NEAR, +X runs from HIP_NEAR (0,0) -> SHOULDER_NEAR (TORSO_LEN=88, 0).
    # Since torso_ang is in [+212 deg (Panel A) .. +264 deg (Panel B)]:
    #   +X points toward the shoulders/neck (up-left in Panel A, straight up in Panel B).
    #   -X points toward the glutes/tailbone (down-right in Panel A, straight down in Panel B).
    #   +Y points UP-RIGHT in Panel A and RIGHT in Panel B -> This is the DORSAL BACK & GLUTEAL surface!
    #   -Y points DOWN-LEFT in Panel A and LEFT in Panel B -> This is the ANTERIOR chest/waist profile!

    # Upper/Mid Dorsal Torso skin silhouette (tucks smoothly inside the top of the waistband at x = 2..14)
    torso_pts = [
        (2, 23),     # sacral waist tucked inside upper glutes/waistband
        (14, 24),    # posterior lumbar waist at top of shorts waistband
        (38, 29),    # mid-thoracic dorsal spine
        (64, 35),    # broad upper-thoracic / scapular back & far rear deltoid
        (86, 29),    # upper Trapezius / base of neck
        (94, 8),     # anterior neck base
        (82, -17),   # anterior clavicular / Pectoralis Major chest bulge
        (64, -20),   # lower Pectoralis Major / anterior ribcage
        (36, -15),   # anterior waist / external oblique side
        (14, -15),   # anterior iliac crest at top of shorts waistband
        (2, -14),    # lower iliac waist tucked inside GluteusMedius
    ]

    # 1. Pelvic Base, Activated Gluteus Maximus (Near Left + Far Right) & Gluteus Medius
    pelvis_shorts_pts = [
        (-26, 2), (-20, 29), (-2, 32), (14, 24),
        (14, -15), (-14, -15), (-23, -7),
    ]
    glute_far_pts = [
        (-24, 15), (-16, 31), (1, 32), (12, 24), (2, 16), (-14, 11),
    ]
    glute_max_pts = [
        (-25, 1), (-19, 28), (-1, 30), (13, 23),
        (10, 6), (-6, -6), (-21, -5),
    ]
    glute_med_pts = [
        (-21, -5), (-6, -6), (10, 6), (13, 18), (13, -14), (-13, -14),
    ]

    # 2. Activated Erector Spinae columns along the lumbar/thoracic dorsal spine (scale = 0.78)
    erector_pts = [
        (14, 14), (36, 18), (60, 23), (58, 30), (34, 25), (14, 22),
    ]

    # 3. Broad Sculpted Dorsal Back Anatomy (Latissimus Dorsi, Scapulae / Infraspinatus, Far Rear Deltoid, Trapezius)
    lat_pts = [
        (16, 5), (42, 3), (68, 2), (76, 15), (56, 23), (34, 18), (15, 14),
    ]
    scapula_near_pts = [
        (56, 14), (77, 10), (85, 23), (70, 30), (56, 24),
    ]
    scapula_far_pts = [
        (58, 26), (78, 24), (85, 32), (66, 35),
    ]

    # 4. 3/4 Rear-Left Head & Neck (child at x = 92, y = 2, rotated by neck_local)
    #    In Head local space, +X points up along the crown of the skull, -Y points forward-left (nose/brow/jaw)!
    neck_pts = [
        (-10, -9), (10, -8), (14, 11), (-10, 12),
    ]
    head_pts = [
        (4, -9),     # anterior throat / under-chin
        (11, -17),   # strong chin tip (pointing forward-left!)
        (17, -17),   # lips / maxilla
        (24, -19),   # sculpted nose tip (projecting forward-left!)
        (30, -16),   # brow ridge
        (38, -12),   # forehead
        (44, -1),    # crown of skull
        (41, 11),    # posterior parietal cranium
        (30, 16),    # occiput (back of head)
        (16, 14),    # lower nape / nuchal line
        (6, 9),      # posterior neck transition
    ]
    # Short athletic dark-brown/auburn-slate cropped hair cap matching reference
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

    # A. Semi-Translucent Pelvic Compression Shorts (drawn OVER Gluteus Maximus & Gluteus Medius so red fibers shine through!)
    out.append(stroke_shape(i2, "ShortsWaistband", [(13, -14), (13, 6), (13, 23)], 2.8, "E6090D16", 0.0, cap="butt"))
    out.append(stroke_shape(i2, "GluteCleftLine", [(-21, 25), (-7, 23), (9, 20)], 1.8, "B3020617", 0.2))
    out.append(
        smooth_shape(
            i2,
            "PelvisShorts",
            pelvis_shorts_pts,
            skin_fill("PelvisShorts", -15, 32, SHORTS_TRANSLUCENT),
        )
    )

    # B. Activated Gluteus Maximus (Near + Far) & Gluteus Medius over a dark charcoal pelvic base (zero white bleed!)
    out.append(stroke_shape(i2, "GluteFiber1", [(-16, 8), (-4, 14), (6, 18)], 1.2, "667F1D1D", 0.4))
    out.append(stroke_shape(i2, "GluteFiber2", [(-18, 16), (-6, 21), (6, 23)], 1.2, "667F1D1D", 0.4))
    out.append(smooth_shape(i2, "GluteusMedius", glute_med_pts, muscle_paint("GluteMed", scale=0.88, line=1.0)))
    out.append(smooth_shape(i2, "GluteusMaximusNear", glute_max_pts, muscle_paint("GluteMaxNear", scale=1.00, line=1.15)))
    out.append(smooth_shape(i2, "GluteusMaximusFar", glute_far_pts, muscle_paint("GluteMaxFar", scale=0.90, line=1.05)))
    out.append(smooth_shape(i2, "PelvisBase", pelvis_shorts_pts, solid("PelvisBase", "FF0F172A")))

    # C. Broad Sculpted Dorsal Back Anatomy & Erector Spinae
    out.append(stroke_shape(i2, "SpinalGroove", [(14, 21), (42, 25), (78, 28)], 1.6, "660F172A", 0.5))
    out.append(stroke_shape(i2, "ScapulaCreaseNear", [(56, 15), (68, 23), (82, 22)], 1.5, ANATOMY_LINE, 0.3))
    out.append(stroke_shape(i2, "ScapulaCreaseFar", [(60, 27), (72, 31), (83, 30)], 1.3, ANATOMY_LINE, 0.3))
    out.append(stroke_shape(i2, "LatBorderCrease", [(18, 8), (42, 7), (66, 6)], 1.4, ANATOMY_LINE, 0.3))
    out.append(stroke_shape(i2, "RibSerratus1", [(46, -4), (54, 1)], 1.2, ANATOMY_LINE, 0.0))
    out.append(stroke_shape(i2, "RibSerratus2", [(36, -5), (44, 0)], 1.2, ANATOMY_LINE, 0.0))
    out.append(smooth_shape(i2, "ErectorSpinae", erector_pts, muscle_paint("ErectorSpinae", scale=0.78, line=0.95)))
    out.append(smooth_shape(i2, "ScapulaNear", scapula_near_pts, skin_fill("ScapulaNear", 10, 30, SKIN)))
    out.append(smooth_shape(i2, "ScapulaFar", scapula_far_pts, skin_fill("ScapulaFar", 24, 35, SKIN_FAR)))
    out.append(smooth_shape(i2, "LatissimusDorsi", lat_pts, skin_fill("LatDorsi", 2, 23, SKIN)))
    out.append(stroke_shape(i2, "DorsalHi", [(20, 20), (50, 25), (78, 26)], 3.8, HIGHLIGHT, 4.0))
    out.append(stroke_shape(i2, "VentralSh", [(20, -10), (50, -12), (76, -9)], 4.5, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i2, "TorsoSilhouette", torso_pts, skin_fill_outlined("Torso", -20, 35, SKIN, line=1.2)))

    # D. 3/4 Rear-Left Head & Neck (positioned at x=92, y=2 so head rises high above the shoulders in Panel B!)
    out.append(f'{i2}<Node x="92" y="2" rotation="{f(p0["neck_local"])}" name="HeadAndNeck" id="{neck_id}">')
    out.append(ellipse_shape(i3, "LeftEar", 21, -2, 5.5, 8.5, skin_fill_outlined("Ear", -4, 4, SKIN, line=0.9), rot_deg=-15.0))
    out.append(smooth_shape(i3, "HairCap", hair_pts, hair_paint))
    out.append(stroke_shape(i3, "JawLine", [(11, -14), (13, -6), (18, -1)], 1.4, CORE_SHADOW, 1.0))
    out.append(stroke_shape(i3, "HeadHi", [(27, -14), (37, -9), (41, 2)], 2.4, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i3, "HeadShape", head_pts, skin_fill_outlined("Head", -19, 16, SKIN, line=1.15)))
    out.append(smooth_shape(i3, "NeckShape", neck_pts, skin_fill_outlined("Neck", -9, 12, SKIN, line=1.0)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 4. Near-Left Straight Hanging Arm (Deltoid, Triceps, Forearm, Pronated Hand)
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

    # Since the arm hangs vertically down (angle ~ +90 deg), in local space:
    # +X runs from Shoulder (0,0) -> Elbow (50,0) -> Hand (46,0).
    # +Y points LEFT (anterior/lateral biceps & radial forearm side!).
    # -Y points RIGHT (posterior triceps horseshoe & ulnar extensor side!).
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
    # Pronated left hand wrapping around the barbell shaft at HAND_NEAR (x = FOREARM_LEN = 46)
    hand_pts = [
        (-5, -6.8), (4, -8.2), (10, -5.5), (11, 2.5), (6, 7.2), (-3, 6.8), (-7, 1.5),
    ]

    return "\n".join([
        f'{ind}<Node name="NearLeftArmGroup">',
        # 1. Forearm & Pronated Hand on Bar
        f'{i2}<Node x="{f(p0["elb_near"][0])}" y="{f(p0["elb_near"][1])}" '
        f'rotation="{f(p0["fa_near_ang"])}" scaleX="{f(p0["fa_near_sc"])}" name="NearForearm" id="{fa_id}">',
        stroke_shape(i3, "NearHandKnuckles", [(48, -4.5), (50, 0.0), (48, 4.5)], 1.2, ANATOMY_LINE, 0.0),
        smooth_shape(i3, "NearHand", hand_pts, skin_fill_outlined("NearHand", -8, 7, SKIN, line=1.2), x=FOREARM_LEN - 2.0),
        stroke_shape(i3, "ForearmExtensorLine", [(6, -3.2), (22, -2.5), (36, -1.5)], 1.3, ANATOMY_LINE, 0.0),
        stroke_shape(i3, "NearForearmHi", [(6, 4.8), (22, 4.2), (36, 3.0)], 2.6, HIGHLIGHT, 2.5),
        stroke_shape(i3, "NearForearmSh", [(6, -5.2), (22, -4.5), (36, -3.0)], 3.4, CORE_SHADOW, 3.5),
        smooth_shape(i3, "NearForearmShape", fa_pts, skin_fill_outlined("NearForearm", -10, 9, SKIN, line=1.2)),
        f"{i2}</Node>",
        # 2. Upper Arm, Triceps Horseshoe & Deltoid Cap (drawn above Forearm at elbow)
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


# ---------------------------------------------------------------- 5. Floor Shadow & Scenery
def floor_shadow_and_scenery():
    ind = "        "
    sh_id = nid()
    key_double(sh_id, 16, lambda p: p["bar_shadow_sx"])
    p0 = POSES[0]
    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"
    return "\n".join([
        # Contact shadow under feet & barbell bumper plates on FLOOR = 300.0
        f'{ind}<Shape x="292" y="297" scaleX="{f(p0["bar_shadow_sx"])}" scaleY="0.068" name="FloorContactShadow" id="{sh_id}">\n'
        f'{ind}    <Ellipse width="280" height="220" name="FloorShadowEllipse"/>\n'
        f'{ind}    <Fill name="FloorShadowFill"><RadialGradient startX="0" startY="0" endX="140" endY="0" name="FloorShadowGrad">'
        f'<GradientStop colorValue="D9000000" position="0"/><GradientStop colorValue="66000000" position="0.62"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{ind}</Shape>",
        f'{ind}<Shape x="{W / 2}" y="{f(FLOOR + 1)}" name="FloorLine"><Rectangle width="{W - 40}" height="2" cornerRadiusTL="1" name="FloorRect"/>'
        f'<Fill name="FloorFill"><LinearGradient startX="{-(W - 40) / 2}" startY="0" endX="{(W - 40) / 2}" endY="0" name="FloorGrad">'
        f'<GradientStop colorValue="00475569" position="0"/><GradientStop colorValue="FF475569" position="0.2"/>'
        f'<GradientStop colorValue="FF475569" position="0.8"/><GradientStop colorValue="00475569" position="1"/></LinearGradient></Fill></Shape>',
        f'{ind}<Shape x="{W / 2}" y="{f((FLOOR + H) / 2 + 1)}" name="FloorBand"><Rectangle width="{W}" height="{f(band_h)}" name="FloorBandRect"/>'
        f"{band_fill}</Shape>",
        f'{ind}<Shape x="{W / 2}" y="{H / 2}" name="Backdrop"><Rectangle width="{W}" height="{H}" name="BackdropRect"/>'
        f'<Fill name="BackdropFill"><RadialGradient startX="0" startY="-40" endX="0" endY="{H * 0.75}" name="BackdropGrad">'
        f'<GradientStop colorValue="FF1E293B" position="0"/><GradientStop colorValue="FF0F172A" position="1"/></RadialGradient></Fill></Shape>',
    ])


near_plate_xml, mid_shaft_xml, far_plate_xml = barbell_layers()
near_arm_xml = near_arm_rig()
torso_head_xml = dorsal_torso_glutes_and_head()
near_thigh_xml, near_shin_xml = leg_rig("Near", False)
far_thigh_xml, far_shin_xml = leg_rig("Far", True)
scenery_xml = floor_shadow_and_scenery()

for cid, sc in muscle_fill_ids:
    key_color(cid, 37, (lambda s: lambda p: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, muscle_t(p) * s))(sc))
for cid, sc in muscle_line_ids:
    key_color(cid, 37, (lambda s: lambda p: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, muscle_t(p) * s))(sc))


def keyed_xml():
    out = []
    for obj, prop, kind, vals in keys:
        out.append(f'            <KeyedObject objectId="{obj}">')
        out.append(f'                <KeyedProperty propertyKey="{prop}">')
        for i, (fr, v) in enumerate(vals):
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
    <!-- Deadlift: 3/4 rear-left view, 60 fps, 16:9 (640x360), generated by gen_deadlift.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="Deadlift" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- 1. Foreground Near-Left 45-lb Olympic Bumper Plate, Collar & Protruding Outer Bar Sleeve -->
{near_plate_xml}

        <!-- 2. Foreground Near-Left Hanging Arm & Pronated Hand Gripping Barbell -->
{near_arm_xml}

        <!-- 3. Dorsal Torso (Traps, Scapulae, Lats, Erector Spinae), Glutes, Semi-Translucent Shorts & 3/4 Head -->
{torso_head_xml}

        <!-- 4. Foreground Near-Left Thigh & Shin/Foot -->
{near_thigh_xml}
{near_shin_xml}

        <!-- 5. Far-Right Thigh (in front of MidBarbellShaft so glute/thigh occlude bar at standing lockout!) -->
{far_thigh_xml}

        <!-- 6. Midground Barbell Shaft & Far Hand (in front of FarShin at bottom setup!) -->
{mid_shaft_xml}

        <!-- 7. Background Far-Right Shin & Foot -->
{far_shin_xml}

        <!-- 8. Background Far-Right 45-lb Olympic Bumper Plate behind Far Leg -->
{far_plate_xml}

{scenery_xml}

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

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="Deadlift" id="0:60">
{keyed_xml()}
        </LinearAnimation>
    </Artboard>
</Rive>
"""

OUT.write_text(rml)
print("keyed props:", len(keys), "bytes:", len(rml))


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
            if "thickness" in at and float(at["thickness"]) != 1:
                out.extend(prop_f(47, at["thickness"]))
            if "cap" in at and cap_map[at["cap"]] != 0:
                out.extend(prop_u(48, cap_map[at["cap"]]))
            if "join" in at and join_map[at["join"]] != 0:
                out.extend(prop_u(49, join_map[at["join"]]))
            if "name" in at:
                out.extend(prop_s(4, at["name"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag == "SolidColor":
            out.extend(varuint(18))
            if "colorValue" in at:
                out.extend(prop_c(37, at["colorValue"]))
            if "name" in at:
                out.extend(prop_s(4, at["name"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag in ("LinearGradient", "RadialGradient"):
            out.extend(varuint(22 if tag == "LinearGradient" else 17))
            if "startX" in at and float(at["startX"]) != 0:
                out.extend(prop_f(42, at["startX"]))
            if "startY" in at and float(at["startY"]) != 0:
                out.extend(prop_f(33, at["startY"]))
            if "endX" in at and float(at["endX"]) != 0:
                out.extend(prop_f(34, at["endX"]))
            if "endY" in at and float(at["endY"]) != 0:
                out.extend(prop_f(35, at["endY"]))
            if "name" in at:
                out.extend(prop_s(4, at["name"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag == "GradientStop":
            out.extend(varuint(19))
            if "colorValue" in at:
                out.extend(prop_c(38, at["colorValue"]))
            if "position" in at and float(at["position"]) != 0:
                out.extend(prop_f(39, at["position"]))
            out.extend(prop_u(5, parent_id) + b"\x00")
        elif tag == "Feather":
            out.extend(varuint(533))
            if "strength" in at and float(at["strength"]) != 12:
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
        out.extend(varuint(31))
        if int(at.get("fps", 60)) != 60:
            out.extend(prop_u(56, at["fps"]))
        out.extend(prop_u(57, at["duration"]))
        if at.get("loopValue") == "loop":
            out.extend(prop_u(59, 1))
        out.extend(prop_s(55, at["name"]) + b"\x00")
        ko_groups, ko_map = [], {}
        for ko in anim.findall("KeyedObject"):
            oid = ko.attrib["objectId"]
            if oid not in ko_map:
                ko_map[oid] = []
                ko_groups.append((oid, ko_map[oid]))
            ko_map[oid].extend(ko.findall("KeyedProperty"))
        for oid, kps in ko_groups:
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
    """Build the .riv, copy it into the Flutter assets, and render the catalog thumbnail."""
    built = HERE / "build/deadlift.riv"
    built.parent.mkdir(parents=True, exist_ok=True)
    ASSET_THUMB.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run([str(RIVE_BIN), ".", "--once"], cwd=HERE, check=True)
        shutil.copyfile(built, ASSET_RIV)
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
    except (PermissionError, OSError, subprocess.CalledProcessError):
        built.write_bytes(_compile_rml_bytes(OUT))
        shutil.copyfile(built, ASSET_RIV)
    print("published", ASSET_RIV, ASSET_THUMB)


if "--publish" in sys.argv:
    publish()
