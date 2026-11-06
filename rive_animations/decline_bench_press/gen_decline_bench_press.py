#!/usr/bin/env python3
"""Generate scene.rml — 60 FPS, 16:9 (640x360, FLOOR = 300.0) HD procedural Rive animation for Decline Bench Press.

Matches the repository visual standard and the 2-panel (Left: bottom chest touch, Right: top lockout)
3/4 front-left Decline Barbell Bench Press reference illustration:
- 3D Decline Weight Bench with Leg-Hold Rollers & Barbell Rack Uprights:
  * Declined dark-slate upholstered pad elevated at the left hip/knee end (~(224, 162)) and sloping
    downward-right toward the lower shoulder/head end (~(376, 198)), plus a white/silver headrest pad
    extending under the head/upper back (~(366, 182) -> (412, 208)).
  * Angled front-left steel roller post ((218, 172) -> (164, 248)) with:
    - Dual Upper Knee Rollers (~(188, 182) and ~(224, 204)) tucked UNDER the knees.
    - Dual Lower Shin/Ankle Rollers (~(156, 224) and ~(190, 246), 3D white/silver foam cylinders)
      drawn IN FRONT OF the lower shins/ankles to lock the athlete onto the decline slope.
  * White/silver powder-coated steel frame with front support post descending to FLOOR = 300.0,
    diagonal floor base rail running back-right, angled seat strut, and two vertical Barbell Rack
    Uprights with J-hook slots flanking the shoulder/head end:
    - Far (Right) Upright in the background (~(278, 54..192)) behind the far arm/barbell.
    - Near (Left) Upright (~(412, 114..248)) behind the near arm/barbell.
- Decline Supine Athlete Anatomy & 4 Target Muscle Activations (MUSCLE_LOW -> MUSCLE_HIGH):
  1. Pectoralis major (lower) (scale = 1.00): Large sternocostal-abdominal lower chest plates on both
     right (far) and left (near) sides with fan striations.
  2. Pectoralis major (upper) (scale = 0.82): Clavicular upper-chest bands above the lower pectoral plates.
  3. Anterior deltoid (scale = 0.88): Front shoulder caps on both near and far shoulders.
  4. Triceps brachii (scale = 0.88): Lateral and long heads along the outer/posterior aspect of both upper arms.
- Decline Barbell Bench Press Kinematics (DURATION = 160 frames / 2.67s @ 60 FPS):
  * 0..12: Bottom chest-touch hold (r = 0.0, Left panel of reference)
  * 12..66: Smooth, powerful concentric press upward (r: 0.0 -> 1.0)
  * 66..84: Top lockout hold (r = 1.0, Right panel of reference)
  * 84..148: Controlled eccentric lowering back to lower chest (r: 1.0 -> 0.0)
  * 148..160: Bottom hold (r = 0.0)

Run:
    python3 rive_animations/decline_bench_press/gen_decline_bench_press.py            # writes scene.rml
    python3 rive_animations/decline_bench_press/gen_decline_bench_press.py --publish  # builds .riv + copies asset & 256x256 thumbnail
"""
import math
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "scene.rml"
ASSET_RIV = REPO / "assets/animations/decline_bench_press.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/decline_bench_press.png"
THUMB_ADVANCE = "1.20s"      # Frame 72: Top lockout hold (Right panel of reference)
THUMB_VIEWPORT = "1280x720"  # 2x the 640x360 artboard
THUMB_CROP = (660, 20, 220)  # square size, offsetY, offsetX in the 2x render
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

# 16:9 standard canvas
W, H = 640, 360
FLOOR = 300.0

# Timeline: 160 frames @ 60 FPS (2.67s loop)
DURATION = 160
STEP = 2

# Shoulder anchors on the declined bench pad (head/shoulders lower on the right than hips on the left)
FAR_SH = (302.0, 146.0)   # Right (far / upper-left) shoulder
NEAR_SH = (348.0, 174.0)  # Left (near / lower-right) shoulder

# Base rest lengths for 3D-foreshortened sibling-node arm segments
UA_FAR_LEN, FA_FAR_LEN = 46.0, 46.0
UA_NEAR_LEN, FA_NEAR_LEN = 42.0, 42.0

# Isometric barbell axis (+26.57 deg, matching the 3/4 shoulder line FAR_SH -> NEAR_SH)
# Delta from BAR_CENTER to FAR_HAND is (-52.0, -26.0); delta to NEAR_HAND is (+52.0, +26.0)
BAR_ANGLE = math.atan2(26.0, 52.0)  # ~ +26.57 deg
BAR_COS = math.cos(BAR_ANGLE)
BAR_SIN = math.sin(BAR_ANGLE)
GRIP_SPAN = math.hypot(52.0, 26.0)  # ~ 58.14 px


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


EASE_PRESS = cubic_bezier(0.36, 0.0, 0.24, 1.0)
EASE_LOWER = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def press_progress(frame):
    """Returns press progress r in [0.0, 1.0] across 160 frames:
    - 0..12: Bottom chest-touch hold (r = 0.0, Left panel)
    - 12..66: Concentric press upward (r: 0.0 -> 1.0)
    - 66..84: Top lockout hold (r = 1.0, Right panel)
    - 84..148: Controlled eccentric lowering back to lower chest (r: 1.0 -> 0.0)
    - 148..160: Bottom hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 66:
        return EASE_PRESS((fr - 12) / 54.0)
    if fr <= 84:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_LOWER((fr - 84) / 64.0)
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
    sc = max(0.45, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute Decline Barbell Bench Press barbell and sibling-node arm transforms at progress r in [0.0, 1.0]."""
    # 1. Barbell Center & Hands Locked to the Bar Shaft:
    #    - At r = 0.0 (Bottom chest touch, Left panel):
    #      BAR_CENTER = (324.0, 142.0) -> FAR_HAND = (272.0, 116.0), NEAR_HAND = (376.0, 168.0)
    #    - At r = 0.5 (Mid press):
    #      BAR_CENTER = (324.0, 107.0) -> FAR_HAND = (272.0, 81.0),  NEAR_HAND = (376.0, 133.0)
    #    - At r = 1.0 (Top lockout, Right panel):
    #      BAR_CENTER = (324.0, 72.0)  -> FAR_HAND = (272.0, 46.0),  NEAR_HAND = (376.0, 98.0)
    bar_center = quad_interp_pt((324.0, 142.0), (324.0, 107.0), (324.0, 72.0), r)
    far_hand = (bar_center[0] - 52.0, bar_center[1] - 26.0)
    near_hand = (bar_center[0] + 52.0, bar_center[1] + 26.0)

    # 2. Elbows (FAR_EL, NEAR_EL):
    #    - At r = 0.0 (Left panel): Elbows drop wide below the decline pad:
    #      FAR_EL = (264.0, 152.0), NEAR_EL = (396.0, 204.0)
    #    - At r = 0.5 (Mid press):
    #      FAR_EL = (274.0, 124.0), NEAR_EL = (380.0, 170.0)
    #    - At r = 1.0 (Right panel, Top lockout):
    #      FAR_EL = (285.0, 96.0),  NEAR_EL = (364.0, 136.0)
    far_el = quad_interp_pt((264.0, 152.0), (274.0, 124.0), (285.0, 96.0), r)
    near_el = quad_interp_pt((396.0, 204.0), (380.0, 170.0), (364.0, 136.0), r)

    # 3. Foreshortened sibling-node arm transforms (SH -> EL and EL -> HAND)
    ua_far_ang, ua_far_sc = seg_xform(FAR_SH, far_el, UA_FAR_LEN)
    fa_far_ang, fa_far_sc = seg_xform(far_el, far_hand, FA_FAR_LEN)
    ua_near_ang, ua_near_sc = seg_xform(NEAR_SH, near_el, UA_NEAR_LEN)
    fa_near_ang, fa_near_sc = seg_xform(near_el, near_hand, FA_NEAR_LEN)

    # 4. Smooth scapulohumeral rotation for Anterior Deltoid shoulder caps aligned with the rising upper arms
    delt_far_ang = math.radians(lerp(185.0, 246.0, r))
    delt_near_ang = math.radians(lerp(28.0, -56.0, r))

    # 5. Subtle pectoral contraction lift at lockout
    chest_lift = lerp(0.0, -1.6, r)

    return {
        "r": r,
        "bar_center": bar_center,
        "far_hand": far_hand,
        "near_hand": near_hand,
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
        "chest_lift": chest_lift,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(press_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = (
    "ua_far_ang",
    "fa_far_ang",
    "ua_near_ang",
    "fa_near_ang",
    "delt_far_ang",
    "delt_near_ang",
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
    for _fr in (0, 38, 72, 116, DURATION):
        _p = POSES[_fr if _fr in POSES else min(POSES.keys(), key=lambda k: abs(k - _fr))]
        print(
            f"f{_fr:3d} r={_p['r']:.3f} bar=({_p['bar_center'][0]:.1f},{_p['bar_center'][1]:.1f}) "
            f"far_el=({_p['far_el'][0]:.1f},{_p['far_el'][1]:.1f}) "
            f"near_el=({_p['near_el'][0]:.1f},{_p['near_el'][1]:.1f})"
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
SHORTS = ("FF334155", "FF1E293B", "FF0B1120")
SHORTS_FAR = ("FF263244", "FF151E2E", "FF090D16")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
ANATOMY_LINE = "520F172A"

# Muscle activation colors: loaded warm orange (#FFF97316) at bottom stretch -> intense crimson (#FFF43F5E) at lockout
MUSCLE_LOW = (0xE6, 0xF9, 0x73, 0x16)
MUSCLE_HIGH = (0xFF, 0xF4, 0x3F, 0x5E)
MUSCLE_LINE_LOW = (0x80, 0x9A, 0x34, 0x12)
MUSCLE_LINE_HIGH = (0xE6, 0x88, 0x13, 0x37)


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
    """Pectoralis major (lower/upper), Anterior deltoid, and Triceps brachii activation intensity in [0.45, 1.0]."""
    return 0.45 + 0.55 * (p["r"] ** 0.80)


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


# ---------------------------------------------------------------- 1. 3D Decline Bench, Leg Rollers & Rack Uprights
def roller_cylinder_xml(indent, name, x0, y0, x1, y1, r=10.5, far=False):
    """Render a 3D white/silver cylindrical foam roller pad from (x0, y0) to (x1, y1) with circular end cap at (x1, y1)."""
    dx, dy = x1 - x0, y1 - y0
    L = max(1e-3, math.hypot(dx, dy))
    nx, ny = -dy / L, dx / L
    if ny < 0:
        nx, ny = -nx, -ny
    body_pts = [
        (x0 - nx * r, y0 - ny * r),
        (x1 - nx * r, y1 - ny * r),
        (x1 + nx * r, y1 + ny * r),
        (x0 + nx * r, y0 + ny * r),
    ]
    c_top = "FFE2E8F0" if far else "FFF8FAFC"
    c_mid = "FFCBD5E1" if far else "FFE2E8F0"
    c_bot = "FF64748B" if far else "FF94A3B8"
    body_paint = (
        f'<Fill name="{name}BodyFill">{grad3(name + "BodyGrad", min(y0, y1) - r, max(y0, y1) + r, c_top, c_mid, c_bot)}</Fill>'
        '<Stroke thickness="1.1" join="round" name="' + name + 'BodyStroke"><SolidColor colorValue="FF475569" name="' + name + 'BodyCol"/></Stroke>'
    )
    cap_paint = (
        f'<Fill name="{name}CapFill">{grad(name + "CapGrad", -6, -9, 6, 9, c_mid, c_bot)}</Fill>'
        '<Stroke thickness="1.1" join="round" name="' + name + 'CapStroke"><SolidColor colorValue="FF475569" name="' + name + 'CapCol"/></Stroke>'
    )
    inner_cap = solid(name + "AxisCap", "FF334155")
    rot_deg = math.degrees(math.atan2(dy, dx)) + 90.0
    return "\n".join([
        ellipse_shape(indent, name + "AxisHub", x1, y1, r * 0.42, r * 0.62, inner_cap, rot_deg=rot_deg),
        ellipse_shape(indent, name + "EndCap", x1, y1, r * 1.18, r * 1.85, cap_paint, rot_deg=rot_deg),
        stroke_shape(indent, name + "Hi", [(x0 - nx * r * 0.45, y0 - ny * r * 0.45), (x1 - nx * r * 0.45, y1 - ny * r * 0.45)], 2.0, "B3FFFFFF", 0.5),
        poly_shape(indent, name + "Barrel", body_pts, body_paint, radius=4.0),
    ])


def decline_bench_and_rack_layers():
    """Returns (front_ankle_rollers_xml, mid_bench_and_near_rack_xml, far_rack_upright_xml)."""
    ind = "        "
    i2 = ind + "    "

    metal_light = (
        f'<Fill name="MetalLightFill">{grad("MetalLightGrad", 160, 60, 440, 290, "FFF8FAFC", "FFD3DCE7")}</Fill>'
        '<Stroke thickness="1.0" join="round" name="MetalLightStroke"><SolidColor colorValue="FF64748B" name="MetalLightCol"/></Stroke>'
    )
    metal_side = (
        f'<Fill name="MetalSideFill">{grad("MetalSideGrad", 160, 60, 440, 290, "FFCBD5E1", "FF64748B")}</Fill>'
        '<Stroke thickness="1.0" join="round" name="MetalSideStroke"><SolidColor colorValue="FF475569" name="MetalSideCol"/></Stroke>'
    )
    metal_dark = (
        f'<Fill name="MetalDarkFill">{grad("MetalDarkGrad", 160, 80, 440, 290, "FF64748B", "FF334155")}</Fill>'
        '<Stroke thickness="1.0" join="round" name="MetalDarkStroke"><SolidColor colorValue="FF1E293B" name="MetalDarkCol"/></Stroke>'
    )
    pad_top = (
        f'<Fill name="PadTopFill">{grad("PadTopGrad", 210, 155, 390, 210, "FF334155", "FF1E293B")}</Fill>'
        '<Stroke thickness="1.2" join="round" name="PadTopStroke"><SolidColor colorValue="FF0F172A" name="PadTopCol"/></Stroke>'
    )
    pad_side = (
        f'<Fill name="PadSideFill">{grad("PadSideGrad", 210, 175, 390, 225, "FF1E293B", "FF090D16")}</Fill>'
        '<Stroke thickness="1.1" join="round" name="PadSideStroke"><SolidColor colorValue="FF020617" name="PadSideCol"/></Stroke>'
    )
    head_pad_paint = (
        f'<Fill name="HeadPadFill">{grad("HeadPadGrad", 360, 175, 420, 215, "FFF1F5F9", "FFCBD5E1")}</Fill>'
        '<Stroke thickness="1.0" join="round" name="HeadPadStroke"><SolidColor colorValue="FF64748B" name="HeadPadCol"/></Stroke>'
    )
    rubber_foot = solid("RubberFoot", "FF0F172A")

    # --- Layer 1 (Frontmost): Lower Shin/Ankle Foam Rollers & Front Roller Post Tip ---
    # Drawn IN FRONT OF the athlete's lower shins (NearShin & FarShin) so the ankles hook behind them!
    front_rollers_xml = "\n".join([
        f'{ind}<Node name="FrontAnkleRollers">',
        # Near-left (lower-right on screen) ankle roller across front of NearShin
        roller_cylinder_xml(i2, "NearAnkleRoller", 172.0, 238.0, 198.0, 256.0, r=10.5, far=False),
        # Central angled white/silver steel roller post between the two ankle rollers
        poly_shape(i2, "RollerPostLowerFront", [(194, 202), (204, 208), (174, 252), (164, 246)], metal_light, radius=1.8),
        poly_shape(i2, "RollerPostLowerSide", [(188, 198), (194, 202), (164, 246), (158, 242)], metal_side, radius=1.8),
        # Far-right (upper-left on screen) ankle roller across front of FarShin
        roller_cylinder_xml(i2, "FarAnkleRoller", 142.0, 216.0, 166.0, 234.0, r=9.8, far=True),
        f"{ind}</Node>",
    ])

    # --- Layer 2 (Midground): Near Knee Roller, Central Roller Post, Declined Bench Pad, Frame & Near Rack Upright ---
    # Drawn BEHIND NearLeftLeg, Torso, and NearLeftArm, and IN FRONT OF FarRightLeg!
    mid_bench_out = [f'{ind}<Node name="DeclineBenchAndNearRack">']

    # A. Near Upper Knee Roller & Central Roller Post (tucked under NearKnee and in front of FarRightLeg)
    mid_bench_out.append(roller_cylinder_xml(i2, "NearKneeRoller", 206.0, 194.0, 234.0, 212.0, r=10.2, far=False))
    mid_bench_out.append(poly_shape(i2, "RollerPostUpperFront", [(218, 168), (228, 174), (204, 208), (194, 202)], metal_light, radius=1.8))
    mid_bench_out.append(poly_shape(i2, "RollerPostUpperSide", [(212, 164), (218, 168), (194, 202), (188, 198)], metal_side, radius=1.8))

    # B. Declined Upholstered Bench Pad (elevated at left hip end (222, 164) -> sloping down-right to shoulder end (378, 202))
    mid_bench_out.append(stroke_shape(i2, "DeclinePadSeam", [(222, 176), (296, 194), (374, 210)], 1.4, "40FFFFFF", 0.5))
    mid_bench_out.append(
        poly_shape(
            i2,
            "DeclinePadTop",
            [(216, 162), (248, 146), (392, 182), (366, 204)],
            pad_top,
            radius=5.0,
        )
    )
    mid_bench_out.append(
        poly_shape(
            i2,
            "DeclinePadFrontSkirt",
            [(216, 162), (366, 204), (366, 216), (216, 176)],
            pad_side,
            radius=3.5,
        )
    )
    # Sleek silver-grey headrest extension board at lower-right end of decline bench
    mid_bench_out.append(
        poly_shape(
            i2,
            "HeadrestBoardTop",
            [(360, 182), (388, 166), (410, 180), (382, 198)],
            head_pad_paint,
            radius=2.5,
        )
    )

    # C. Near-Right Vertical Barbell Rack Upright (at x ~ 410..424, y ~ 116..248, behind NearLeftArm & NearPlate)
    for jy in (136, 152, 168, 184):
        mid_bench_out.append(poly_shape(i2, f"NearJHook_{jy}", [(402, jy), (410, jy - 4), (410, jy + 3), (402, jy + 7)], metal_dark, radius=1.2))
    mid_bench_out.append(poly_shape(i2, "NearRackTopCap", [(406, 114), (418, 108), (426, 113), (414, 119)], metal_light, radius=1.0))
    mid_bench_out.append(poly_shape(i2, "NearRackPostFront", [(414, 119), (426, 113), (426, 244), (414, 250)], metal_light, radius=1.2))
    mid_bench_out.append(poly_shape(i2, "NearRackPostSide", [(406, 114), (414, 119), (414, 250), (406, 245)], metal_side, radius=1.2))
    mid_bench_out.append(poly_shape(i2, "NearRackBaseFoot", [(398, 244), (434, 238), (438, 246), (402, 254)], metal_side, radius=1.5))

    # D. White/Silver Steel Under-Frame, Front Support Leg & Diagonal Floor Base Rail
    # Front vertical-angled bench leg descending from under elevated seat (206, 186) to floor foot (194, 294) on FLOOR = 300.0
    mid_bench_out.append(poly_shape(i2, "FrontBenchLegFront", [(206, 186), (220, 192), (202, 294), (188, 288)], metal_light, radius=1.8))
    mid_bench_out.append(poly_shape(i2, "FrontBenchLegSide", [(198, 182), (206, 186), (188, 288), (180, 284)], metal_side, radius=1.8))
    mid_bench_out.append(poly_shape(i2, "FrontBenchFloorPlate", [(174, 286), (210, 294), (206, 300), (170, 292)], rubber_foot, radius=2.0))

    # Diagonal main floor rail from FrontBenchLeg base (198, 284) up-right to NearRack base (416, 242) + cross-strut
    mid_bench_out.append(poly_shape(i2, "FloorDiagonalRailTop", [(200, 276), (344, 198), (354, 204), (204, 286)], metal_light, radius=1.8))
    mid_bench_out.append(poly_shape(i2, "FloorDiagonalRailSide", [(204, 286), (354, 204), (354, 214), (204, 295)], metal_side, radius=1.8))
    # Rear diagonal frame strut from bench underside (334, 194) down-right to NearRack base (414, 244)
    mid_bench_out.append(poly_shape(i2, "RearBenchFrameStrut", [(334, 192), (344, 186), (418, 238), (408, 246)], metal_light, radius=1.8))
    mid_bench_out.append(poly_shape(i2, "RearBenchFrameSide", [(330, 196), (334, 192), (408, 246), (402, 250)], metal_side, radius=1.8))

    mid_bench_out.append(f"{ind}</Node>")
    mid_bench_xml = "\n".join(mid_bench_out)

    # --- Layer 3 (Background): Far Knee Roller & Far-Left Vertical Barbell Rack Upright (behind FarRightLeg & FarRightArm) ---
    far_rack_out = [f'{ind}<Node name="FarRackUpright">']
    far_rack_out.append(roller_cylinder_xml(i2, "FarKneeRoller", 174.0, 172.0, 200.0, 190.0, r=9.5, far=True))
    for jy in (74, 90, 106, 122):
        far_rack_out.append(poly_shape(i2, f"FarJHook_{jy}", [(266, jy), (274, jy - 4), (274, jy + 3), (266, jy + 7)], metal_dark, radius=1.2))
    far_rack_out.append(poly_shape(i2, "FarRackTopCap", [(270, 52), (282, 46), (290, 51), (278, 57)], metal_light, radius=1.0))
    far_rack_out.append(poly_shape(i2, "FarRackPostFront", [(278, 57), (290, 51), (290, 186), (278, 192)], metal_light, radius=1.2))
    far_rack_out.append(poly_shape(i2, "FarRackPostSide", [(270, 52), (278, 57), (278, 192), (270, 187)], metal_side, radius=1.2))
    far_rack_out.append(f"{ind}</Node>")
    far_rack_xml = "\n".join(far_rack_out)

    return front_rollers_xml, mid_bench_xml, far_rack_xml


# ---------------------------------------------------------------- 2. Anchored Decline Legs (Quads, Patella, Shins, Bare Feet)
def far_leg():
    """Right (far / upper-left) leg: thigh over FarKneeRoller, shin descending behind FarAnkleRoller to bare foot."""
    ind = "        "
    i2 = ind + "    "
    # Far thigh from elevated right hip (244, 152) up-left over FarKneeRoller to right knee (180, 172)
    thigh_pts = [
        (246, 146), (218, 142), (192, 150), (174, 164),
        (180, 182), (204, 178), (232, 174), (250, 166),
    ]
    shorts_pts = [
        (254, 146), (222, 142), (208, 147), (216, 176), (248, 168),
    ]
    # Far shin descending from right knee (180, 172) behind FarAnkleRoller (156, 224) to right ankle (150, 242)
    shin_pts = [
        (174, 166), (160, 188), (150, 214), (146, 238),
        (158, 244), (168, 224), (178, 198), (184, 176),
    ]
    # Bare right foot pointing down-left at (128, 256)
    foot_pts = [
        (146, 236), (132, 244), (120, 252), (124, 260),
        (140, 258), (156, 250), (160, 242),
    ]
    return "\n".join([
        f'{ind}<Node name="FarRightLeg">',
        smooth_shape(i2, "FarFoot", foot_pts, skin_fill_outlined("FarFoot", 236, 260, SKIN_FAR, line=1.05)),
        stroke_shape(i2, "FarShinCrease", [(170, 182), (160, 206), (152, 230)], 1.2, ANATOMY_LINE, 0.0),
        smooth_shape(i2, "FarShin", shin_pts, skin_fill_outlined("FarShin", 166, 244, SKIN_FAR, line=1.05)),
        ellipse_shape(i2, "FarKneeCap", 178, 170, 16, 14, skin_fill_outlined("FarKnee", -7, 7, SKIN_FAR, line=0.95), rot_deg=-20.0),
        smooth_shape(i2, "FarThighShorts", shorts_pts, skin_fill_outlined("FarThighShorts", 142, 176, SHORTS_FAR, line=1.1, stroke_col="CC020617")),
        stroke_shape(i2, "FarQuadSplit", [(222, 150), (200, 154), (182, 162)], 1.3, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "FarThighHi", [(226, 148), (202, 150), (184, 158)], 3.2, HIGHLIGHT, 3.0),
        stroke_shape(i2, "FarThighSh", [(230, 168), (204, 172), (184, 176)], 4.2, CORE_SHADOW, 4.0),
        smooth_shape(i2, "FarThigh", thigh_pts, skin_fill_outlined("FarThigh", 142, 182, SKIN_FAR, line=1.1)),
        f"{ind}</Node>",
    ])


def near_leg():
    """Left (near / foreground) leg: sculpted Quads over NearKneeRoller, Shin behind NearAnkleRoller, Bare Foot."""
    ind = "        "
    i2 = ind + "    "
    # Near thigh from elevated left hip (268, 168) over NearKneeRoller to left knee (206, 192)
    thigh_pts = [
        (268, 162), (242, 160), (216, 170), (198, 184),
        (204, 204), (228, 198), (256, 192), (274, 182),
    ]
    shorts_pts = [
        (274, 160), (244, 158), (230, 164), (238, 196), (272, 186),
    ]
    # Near shin descending from left knee (206, 192) behind NearAnkleRoller (190, 246) to left ankle (176, 268)
    shin_pts = [
        (198, 188), (186, 212), (176, 240), (172, 264),
        (184, 270), (196, 248), (208, 220), (212, 196),
    ]
    # Bare left foot pointing down-left at (150, 286)
    foot_pts = [
        (172, 262), (158, 272), (146, 280), (150, 290),
        (166, 288), (182, 278), (186, 268),
    ]
    return "\n".join([
        f'{ind}<Node name="NearLeftLeg">',
        # 1. Bare Left Foot & Ankle details
        stroke_shape(i2, "NearToeLine1", [(150, 282), (158, 278)], 1.0, ANATOMY_LINE, 0.0),
        stroke_shape(i2, "NearToeLine2", [(154, 286), (162, 282)], 1.0, ANATOMY_LINE, 0.0),
        smooth_shape(i2, "NearFoot", foot_pts, skin_fill_outlined("NearFoot", 262, 290, SKIN, line=1.15)),
        # 2. Sculpted Near Shin (Tibialis Anterior & Gastrocnemius) passing BEHIND NearAnkleRoller
        stroke_shape(i2, "NearTibialisCrease", [(198, 202), (188, 228), (180, 254)], 1.3, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "NearShinHi", [(196, 200), (186, 226), (178, 252)], 3.0, HIGHLIGHT, 3.0),
        stroke_shape(i2, "NearShinSh", [(206, 206), (198, 232), (188, 258)], 4.0, CORE_SHADOW, 4.0),
        smooth_shape(i2, "NearShin", shin_pts, skin_fill_outlined("NearShin", 188, 270, SKIN, line=1.15)),
        # 3. Sculpted Patella & Quadriceps (Rectus Femoris, Vastus Medialis teardrop, Vastus Lateralis)
        ellipse_shape(i2, "NearKneeCap", 204, 192, 17, 15, skin_fill_outlined("NearKnee", -8, 8, SKIN, line=1.0), rot_deg=-22.0),
        smooth_shape(i2, "NearThighShorts", shorts_pts, skin_fill_outlined("NearThighShorts", 158, 196, SHORTS, line=1.15, stroke_col="CC020617")),
        stroke_shape(i2, "NearRectusFemorisLine", [(240, 168), (222, 174), (206, 184)], 1.4, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "NearVastusMedialisLine", [(236, 182), (218, 188), (208, 194)], 1.3, ANATOMY_LINE, 0.2),
        stroke_shape(i2, "NearThighHi", [(242, 166), (222, 172), (206, 182)], 3.8, HIGHLIGHT, 3.5),
        stroke_shape(i2, "NearThighSh", [(250, 188), (226, 194), (208, 198)], 4.8, CORE_SHADOW, 4.5),
        smooth_shape(i2, "NearThigh", thigh_pts, skin_fill_outlined("NearThigh", 160, 204, SKIN, line=1.15)),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 3. Declined Supine Torso, 6-Pack Abs, Lower/Upper Pectorals & Head
def decline_torso_and_head():
    """Declined supine torso (hips higher on left, shoulders/head lower on right), 6-pack abs,
    activated Pectoralis major (lower & upper), and volumetric 3/4 head."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    chest_id = nid()
    key_double(chest_id, 14, lambda p: p["chest_lift"])

    # 1. Pelvic Compression Shorts on the elevated left end of the decline bench pad
    pelvis_shorts = [
        (232, 152), (258, 148), (282, 164), (278, 192), (252, 194), (228, 172),
    ]

    # 2. Declined Supine Torso from elevated waist (256, 168) sloping down-right to shoulders (304, 148) & (352, 176)
    torso_pts = [
        (254, 156), (276, 148), (300, 142), (324, 142),
        (348, 152), (358, 170), (346, 188), (322, 196),
        (296, 196), (272, 192), (254, 182),
    ]
    torso_hi = [(268, 154), (294, 148), (320, 148)]
    torso_sh = [(340, 186), (312, 192), (280, 188)]

    # 3. Sculpted 6-Pack Rectus Abdominis & External Obliques angled along the declined torso
    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="220F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.95" join="round" name="AbsEdge"><SolidColor colorValue="4D0F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        # Upper-right (far side of linea alba) 3 abdominal blocks from ribcage toward pelvis
        [(294, 152), (306, 149), (311, 156), (299, 159)],
        [(280, 156), (292, 153), (297, 160), (285, 163)],
        [(266, 160), (278, 157), (283, 164), (271, 167)],
        # Lower-left (near side of linea alba) 3 abdominal blocks
        [(300, 162), (312, 159), (317, 167), (305, 170)],
        [(286, 166), (298, 163), (303, 171), (291, 174)],
        [(272, 170), (284, 167), (289, 175), (277, 178)],
    ]

    # 4. Target Muscle #1: Pectoralis major (lower) — scale = 1.00 (Primary Mover!)
    #    Large fan-shaped sternocostal-abdominal lower chest plates on both right (far) and left (near) sides
    pec_right_lower_pts = [
        (300, 148), (310, 140), (324, 141), (331, 149),
        (322, 158), (308, 158),
    ]
    pec_left_lower_pts = [
        (324, 160), (333, 151), (348, 160), (351, 175),
        (338, 184), (322, 179), (315, 169),
    ]

    # 5. Target Muscle #2: Pectoralis major (upper) — scale = 0.82
    #    Clavicular upper-chest bands tucked along the upper-medial border of the chest
    pec_right_upper_pts = [
        (312, 140), (324, 138), (338, 145), (332, 151), (320, 145),
    ]
    pec_left_upper_pts = [
        (333, 151), (340, 146), (354, 155), (352, 164), (342, 158),
    ]

    # 6. Volumetric 3/4 Supine Head & Neck at the lower-right end of the decline bench (looking up-left at the bar!)
    neck_pts = [(322, 152), (334, 144), (348, 155), (332, 165)]
    head_pts = [
        (330, 146),  # anterior throat / under-chin
        (331, 137),  # sculpted chin tip pointing up-left
        (337, 131),  # lips / maxilla
        (344, 127),  # nose tip projecting up-left
        (352, 127),  # brow ridge / forehead
        (361, 129),  # cranial dome
        (368, 136),  # posterior crown
        (368, 147),  # occiput resting on decline headrest
        (361, 155),  # lower cranium behind ear
        (350, 158),  # mandible / jaw angle
        (340, 154),  # jawline
    ]
    hair_pts = [
        (353, 127), (362, 128), (369, 135), (369, 147),
        (362, 153), (361, 144), (357, 135), (351, 131),
    ]
    hair_paint = (
        f'<Fill name="HairFill">{grad("HairGrad", 351, 127, 369, 153, "FF334155", "FF0F172A")}</Fill>'
        '<Stroke thickness="0.95" join="round" name="HairStroke"><SolidColor colorValue="FF090D16" name="HairStrokeCol"/></Stroke>'
    )

    out = [f'{ind}<Node name="DeclineSupineTorsoAndHead">']

    # A. Volumetric 3/4 Head & Neck (tucked behind the upper clavicular chest)
    out.append(smooth_shape(i2, "HairCap", hair_pts, hair_paint))
    out.append(ellipse_shape(i2, "LeftEar", 354, 151, 6.8, 5.0, skin_fill_outlined("Ear", -3, 3, SKIN, line=0.85), rot_deg=-20.0))
    out.append(stroke_shape(i2, "HeadHi", [(338, 134), (348, 129), (358, 130)], 2.6, HIGHLIGHT, 2.5))
    out.append(stroke_shape(i2, "JawLine", [(334, 146), (344, 151), (352, 150)], 1.4, CORE_SHADOW, 1.2))
    out.append(smooth_shape(i2, "HeadShape", head_pts, skin_fill_outlined("Head", 127, 158, SKIN, line=1.1)))
    out.append(smooth_shape(i2, "NeckShape", neck_pts, skin_fill_outlined("Neck", 144, 165, SKIN_FAR, line=1.0)))

    # B. Animated Pectoralis Major Group (1. Pectoralis major (lower) + 2. Pectoralis major (upper))
    out.append(f'{i2}<Node y="0" name="ChestGroup" id="{chest_id}">')
    # Fan striations across Lower & Upper Pectoralis Major
    out.append(stroke_shape(i3, "PecLowerStriationL1", [(324, 166), (336, 166), (346, 171)], 1.1, "667F1D1D", 0.3))
    out.append(stroke_shape(i3, "PecLowerStriationL2", [(321, 172), (333, 174), (344, 178)], 1.1, "667F1D1D", 0.3))
    out.append(stroke_shape(i3, "PecLowerStriationR1", [(306, 148), (316, 147), (326, 150)], 1.0, "667F1D1D", 0.3))
    out.append(stroke_shape(i3, "PecUpperCleftLine", [(332, 151), (324, 158)], 1.4, "807F1D1D", 0.2))
    # Upper Clavicular Pectorals (scale = 0.82)
    out.append(smooth_shape(i3, "PecLeftUpper", pec_left_upper_pts, muscle_paint("PecLeftUpper", scale=0.82, line=1.0)))
    out.append(smooth_shape(i3, "PecRightUpper", pec_right_upper_pts, muscle_paint("PecRightUpper", scale=0.78, line=0.95)))
    # Lower Sternocostal-Abdominal Pectorals (scale = 1.00 — Primary Mover!)
    out.append(smooth_shape(i3, "PecLeftLower", pec_left_lower_pts, muscle_paint("PecLeftLower", scale=1.00, line=1.15)))
    out.append(smooth_shape(i3, "PecRightLower", pec_right_lower_pts, muscle_paint("PecRightLower", scale=0.94, line=1.05)))
    out.append(f"{i2}</Node>")

    # C. Sculpted 6-Pack Rectus Abdominis, Linea Alba & Serratus Anterior / External Obliques
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "LineaAlba", [(322, 158), (296, 162), (270, 168)], 1.3, ANATOMY_LINE, 0.4))
    out.append(stroke_shape(i2, "Serratus1", [(314, 180), (304, 176)], 1.2, ANATOMY_LINE, 0.2))
    out.append(stroke_shape(i2, "Serratus2", [(300, 184), (290, 180)], 1.2, ANATOMY_LINE, 0.2))
    out.append(stroke_shape(i2, "ObliqueCrease", [(286, 186), (270, 180)], 1.3, ANATOMY_LINE, 0.2))

    # D. Pelvic Compression Shorts & Declined Torso Base
    out.append(stroke_shape(i2, "ShortsWaistband", [(256, 150), (268, 168), (274, 190)], 2.2, "CC020617", 0.0))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill_outlined("PelvisShorts", 148, 194, SHORTS, line=1.15, stroke_col="CC020617")))
    out.append(stroke_shape(i2, "TorsoHi", torso_hi, 4.0, HIGHLIGHT, 4.0))
    out.append(stroke_shape(i2, "TorsoSh", torso_sh, 5.2, CORE_SHADOW, 5.0))
    out.append(smooth_shape(i2, "TorsoSilhouette", torso_pts, skin_fill_outlined("Torso", 142, 196, SKIN, line=1.15)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 4. Foreshortened Sibling-Node Arms (Anterior Deltoid & Triceps Brachii)
def arm_rig(prefix, far):
    """Sibling-node foreshortened arm (UpperArm SH->EL, Forearm EL->HAND, DeltoidCap at SH) with Anterior Deltoid & Triceps Brachii."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    sh_pt = FAR_SH if far else NEAR_SH
    el_key = "far_el" if far else "near_el"
    ua_len = UA_FAR_LEN if far else UA_NEAR_LEN
    fa_len = FA_FAR_LEN if far else FA_NEAR_LEN
    ua_ang_key = "ua_far_ang" if far else "ua_near_ang"
    ua_sc_key = "ua_far_sc" if far else "ua_near_sc"
    fa_ang_key = "fa_far_ang" if far else "fa_near_ang"
    fa_sc_key = "fa_far_sc" if far else "fa_near_sc"
    delt_ang_key = "delt_far_ang" if far else "delt_near_ang"
    m_scale = 0.88 if far else 1.00

    ua_id, fa_id, delt_id = nid(), nid(), nid()
    key_double(ua_id, 15, lambda p: p[ua_ang_key])
    key_double(ua_id, 16, lambda p: p[ua_sc_key])

    key_double(fa_id, 13, lambda p: p[el_key][0])
    key_double(fa_id, 14, lambda p: p[el_key][1])
    key_double(fa_id, 15, lambda p: p[fa_ang_key])
    key_double(fa_id, 16, lambda p: p[fa_sc_key])

    key_double(delt_id, 15, lambda p: p[delt_ang_key])
    p0 = POSES[0]

    tri_sign = -1.0 if far else 1.0

    ua_pts = [
        (-10, 0), (-7, -10.5), (6, -12.0), (ua_len * 0.55, -11.0), (ua_len - 4, -7.8),
        (ua_len + 5, 0), (ua_len - 4, 7.8), (ua_len * 0.55, 11.0), (6, 12.0), (-7, 10.5),
    ]
    # Target Muscle #4: Triceps brachii (lateral & long heads along outer/extensor aspect, scale = 0.88)
    tri_pts = [
        (5, tri_sign * 1.5),
        (ua_len * 0.45, tri_sign * 2.0),
        (ua_len - 5, tri_sign * 2.5),
        (ua_len - 7, tri_sign * 10.2),
        (ua_len * 0.45, tri_sign * 11.5),
        (6, tri_sign * 10.2),
    ]
    # Sculpted Biceps brachii / Brachialis belly on the inner/anterior aspect of UpperArm
    biceps_pts = [
        (6, -tri_sign * 1.0),
        (ua_len * 0.45, -tri_sign * 1.2),
        (ua_len - 6, -tri_sign * 1.5),
        (ua_len - 8, -tri_sign * 8.5),
        (ua_len * 0.45, -tri_sign * 10.5),
        (7, -tri_sign * 9.5),
    ]

    # Target Muscle #3: Anterior deltoid (front shoulder cap anchored on dedicated shoulder node, scale = 0.88)
    delt_pts = [
        (-12, 0), (-8, -11.5), (5, -13.5), (17, -9.5), (20, 0),
        (17, 9.5), (5, 13.5), (-8, 11.5),
    ]
    front_delt_pts = [
        (-8, -1.0), (-3, -10.5), (8, -12.0), (18, -6.5),
        (18, 4.5), (7, 8.5), (-4, 5.5),
    ] if not far else [
        (-8, 1.0), (-3, 10.5), (8, 12.0), (18, 6.5),
        (18, -4.5), (7, -8.5), (-4, -5.5),
    ]

    fa_pts = [
        (-6, 0), (-4, -8.0), (fa_len * 0.35, -9.2), (fa_len - 5, -5.8),
        (fa_len + 4, 0), (fa_len - 5, 5.8), (fa_len * 0.35, 9.2), (-4, 8.0),
    ]
    hand_pts = [
        (-5, -6.8), (5, -7.5), (10, -2.5), (10, 4.8), (4, 7.2), (-5, 5.8),
    ]

    return "\n".join([
        f'{ind}<Node name="{prefix}ArmGroup">',
        # 1. Forearm & Wrist/Hand (drawn in front of the elbow joint, sibling of UpperArm)
        f'{i2}<Node x="{f(p0[el_key][0])}" y="{f(p0[el_key][1])}" '
        f'rotation="{f(p0[fa_ang_key])}" scaleX="{f(p0[fa_sc_key])}" name="{prefix}Forearm" id="{fa_id}">',
        smooth_shape(i3, f"{prefix}Hand", hand_pts, skin_fill_outlined(prefix + "Hand", -8, 8, skin, line=1.1), x=fa_len - 2.0),
        stroke_shape(i3, f"{prefix}BrachioradialisLine", [(5, -2.2), (fa_len * 0.55, -1.8)], 1.2, ANATOMY_LINE, 0.0),
        stroke_shape(i3, f"{prefix}ForearmHi", [(5, -4.5), (fa_len - 8, -3.2)], 2.6, HIGHLIGHT, 2.5),
        stroke_shape(i3, f"{prefix}ForearmSh", [(5, 4.8), (fa_len - 8, 3.5)], 3.2, CORE_SHADOW, 3.0),
        smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill_outlined(prefix + "Forearm", -9, 9, skin, line=1.15)),
        f"{i2}</Node>",

        # 2. Dedicated Shoulder Cap Node for Anterior Deltoid (stays naturally oriented on the shoulder!)
        f'{i2}<Node x="{f(sh_pt[0])}" y="{f(sh_pt[1])}" '
        f'rotation="{f(p0[delt_ang_key])}" name="{prefix}ShoulderCap" id="{delt_id}">',
        stroke_shape(i3, f"{prefix}DeltFiber1", [(0, -3.5 * tri_sign), (13, -2.0 * tri_sign)], 1.1, "667F1D1D", 0.3),
        stroke_shape(i3, f"{prefix}DeltFiber2", [(0, 1.5 * tri_sign), (13, 2.0 * tri_sign)], 1.1, "667F1D1D", 0.3),
        smooth_shape(i3, f"{prefix}AnteriorDeltoid", front_delt_pts, muscle_paint(prefix + "FrontDelt", scale=0.88 * m_scale, line=1.05)),
        smooth_shape(i3, f"{prefix}DeltoidBase", delt_pts, skin_fill_outlined(prefix + "Deltoid", -13, 13, skin, line=1.1)),
        f"{i2}</Node>",

        # 3. Upper Arm, Biceps Brachii & Triceps Brachii
        f'{i2}<Node x="{f(sh_pt[0])}" y="{f(sh_pt[1])}" '
        f'rotation="{f(p0[ua_ang_key])}" scaleX="{f(p0[ua_sc_key])}" name="{prefix}UpperArm" id="{ua_id}">',
        stroke_shape(i3, f"{prefix}UpperArmHi", [(6, -tri_sign * 5.5), (ua_len - 8, -tri_sign * 4.5)], 2.6, HIGHLIGHT, 2.8),
        smooth_shape(i3, f"{prefix}BicepsBelly", biceps_pts, skin_fill_outlined(prefix + "Biceps", -11, 11, skin, line=0.95)),
        stroke_shape(i3, f"{prefix}TricepsSplit", [(8, tri_sign * 6.5), (ua_len - 9, tri_sign * 6.0)], 1.2, "667F1D1D", 0.3),
        smooth_shape(i3, f"{prefix}TricepsBrachii", tri_pts, muscle_paint(prefix + "Triceps", scale=0.88 * m_scale, line=1.05)),
        smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill_outlined(prefix + "UpperArm", -12, 12, skin, line=1.15)),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 5. 3D Olympic Barbell with 45-lb Bumper Plates & Finger Wraps
def barbell_rig():
    """Animated 3D Olympic Barbell with far/near 45-lb dark charcoal plates, chrome sleeves, shaft, and finger wraps."""
    ind = "        "
    i2 = ind + "    "
    bar_id = nid()
    key_double(bar_id, 13, lambda p: p["bar_center"][0])
    key_double(bar_id, 14, lambda p: p["bar_center"][1])
    p0 = POSES[0]

    ux, uy = BAR_COS, BAR_SIN
    nx, ny = -BAR_SIN, BAR_COS

    def bar_pt(along, perp=0.0):
        return (along * ux + perp * nx, along * uy + perp * ny)

    plate_rot_deg = math.degrees(BAR_ANGLE)
    plate_face_near = (
        f'<Fill name="NearPlateFaceFill">{grad3("NearPlateFaceGrad", -38, 38, "FF334155", "FF182232", "FF090D16", x0=-20, x1=20)}</Fill>'
        '<Stroke thickness="1.5" join="round" name="NearPlateRimStroke"><SolidColor colorValue="FF475569" name="NearPlateRimCol"/></Stroke>'
    )
    plate_face_far = (
        f'<Fill name="FarPlateFaceFill">{grad3("FarPlateFaceGrad", -36, 36, "FF263244", "FF111827", "FF060911", x0=-18, x1=18)}</Fill>'
        '<Stroke thickness="1.4" join="round" name="FarPlateRimStroke"><SolidColor colorValue="FF334155" name="FarPlateRimCol"/></Stroke>'
    )
    plate_rim_paint = f'<Fill name="PlateBackFill">{grad("PlateBackGrad", -22, -38, 22, 38, "FF0F172A", "FF020617")}</Fill>'
    plate_ring_paint = (
        '<Fill name="PlateRingFill"><SolidColor colorValue="FF111827" name="PlateRingCol"/></Fill>'
        '<Stroke thickness="1.2" join="round" name="PlateRingStroke"><SolidColor colorValue="FF334155" name="PlateRingStrokeCol"/></Stroke>'
    )
    hub_paint = (
        f'<Fill name="BarHubFill">{grad3("BarHubGrad", -8, 8, "FF94A3B8", "FF475569", "FF1E293B")}</Fill>'
        '<Stroke thickness="1.1" join="round" name="BarHubStroke"><SolidColor colorValue="FFCBD5E1" name="BarHubStrokeCol"/></Stroke>'
    )

    # Near (bottom-right) 45-lb plate center at along = +114.0 (clear of the athlete's head at lockout!)
    npx, npy = bar_pt(114.0)
    nbx, nby = bar_pt(110.0)
    npw, nph = 38.0, 68.0

    # Far (top-left) 45-lb plate center at along = -114.0
    fpx, fpy = bar_pt(-114.0)
    fbx, fby = bar_pt(-118.0)
    fpw, fph = 36.0, 64.0

    # Hand grip centers at +/- GRIP_SPAN ((-52, -27) and (+52, +27))
    gf = bar_pt(-GRIP_SPAN)
    gn = bar_pt(GRIP_SPAN)

    return "\n".join([
        f'{ind}<Node x="{f(p0["bar_center"][0])}" y="{f(p0["bar_center"][1])}" name="BarbellGroup" id="{bar_id}">',

        # 1. Near (bottom-right) protruding outer chrome sleeve & 45-lb Olympic bumper plate (in front of shaft)
        ellipse_shape(i2, "NearSleeveEndCap", *bar_pt(154.0), 4.5, 6.8, solid("NearSleeveCap", "FF0F172A"), rot_deg=plate_rot_deg),
        stroke_shape(i2, "NearSleeveOuter", [bar_pt(114.0), bar_pt(154.0)], 7.2, "FF94A3B8", 0.0, cap="round"),
        stroke_shape(i2, "NearSleeveHi", [bar_pt(115.0, -1.2), bar_pt(152.0, -1.2)], 2.0, "FFE2E8F0", 0.2, cap="round"),
        ellipse_shape(i2, "NearPlateHub", npx, npy, 9.5, 15.0, hub_paint, rot_deg=plate_rot_deg),
        stroke_shape(i2, "NearSpoke1", [(npx - 3, npy - 5), (npx - 11, npy - 22)], 1.8, "FF334155", 0.0),
        stroke_shape(i2, "NearSpoke2", [(npx + 3, npy + 5), (npx + 11, npy + 22)], 1.8, "FF334155", 0.0),
        stroke_shape(i2, "NearSpoke3", [(npx - 4, npy + 2), (npx - 14, npy + 8)], 1.8, "FF334155", 0.0),
        stroke_shape(i2, "NearSpoke4", [(npx + 4, npy - 2), (npx + 14, npy - 8)], 1.8, "FF334155", 0.0),
        ellipse_shape(i2, "NearPlateInnerRing", npx, npy, npw * 0.72, nph * 0.72, plate_ring_paint, rot_deg=plate_rot_deg),
        ellipse_shape(i2, "NearPlateFace", npx, npy, npw, nph, plate_face_near, rot_deg=plate_rot_deg),
        ellipse_shape(i2, "NearPlateRim3D", nbx, nby, npw, nph, plate_rim_paint, rot_deg=plate_rot_deg),
        ellipse_shape(i2, "NearInnerCollar", *bar_pt(105.0), 7.5, 11.8, hub_paint, rot_deg=plate_rot_deg),

        # 2. Pronated finger knuckles wrapping over the barbell shaft at both hands
        ellipse_shape(i2, "NearFingerWrap", gn[0], gn[1], 14.5, 10.5, skin_fill_outlined("NearWrap", -5, 5, SKIN, line=1.0), rot_deg=plate_rot_deg),
        ellipse_shape(i2, "FarFingerWrap", gf[0], gf[1], 13.5, 9.8, skin_fill_outlined("FarWrap", -5, 5, SKIN_FAR, line=0.95), rot_deg=plate_rot_deg),

        # 3. Main chrome/gunmetal Olympic barbell shaft across the chest (-110 .. +110)
        stroke_shape(i2, "BarShaftHi", [bar_pt(-106.0, -1.1), bar_pt(0.0, -1.1), bar_pt(106.0, -1.1)], 1.5, "FFFFFFFF", 0.2, cap="butt"),
        stroke_shape(i2, "BarShaftCore", [bar_pt(-110.0), bar_pt(0.0), bar_pt(110.0)], 4.2, "FFCBD5E1", 0.0, cap="butt"),
        stroke_shape(i2, "BarShaftShadow", [bar_pt(-110.0), bar_pt(0.0), bar_pt(110.0)], 5.8, "FF334155", 0.0, cap="butt"),

        # 4. Far (top-left) 45-lb Olympic bumper plate & outer sleeve (behind main shaft)
        ellipse_shape(i2, "FarInnerCollar", *bar_pt(-105.0), 7.2, 11.2, hub_paint, rot_deg=plate_rot_deg),
        ellipse_shape(i2, "FarPlateHub", fpx, fpy, 9.0, 14.0, hub_paint, rot_deg=plate_rot_deg),
        stroke_shape(i2, "FarSpoke1", [(fpx - 3, fpy - 5), (fpx - 10, fpy - 20)], 1.6, "FF1E293B", 0.0),
        stroke_shape(i2, "FarSpoke2", [(fpx + 3, fpy + 5), (fpx + 10, fpy + 20)], 1.6, "FF1E293B", 0.0),
        ellipse_shape(i2, "FarPlateInnerRing", fpx, fpy, fpw * 0.72, fph * 0.72, plate_ring_paint, rot_deg=plate_rot_deg),
        ellipse_shape(i2, "FarPlateFace", fpx, fpy, fpw, fph, plate_face_far, rot_deg=plate_rot_deg),
        ellipse_shape(i2, "FarPlateRim3D", fbx, fby, fpw, fph, plate_rim_paint, rot_deg=plate_rot_deg),
        stroke_shape(i2, "FarSleeveHi", [bar_pt(-115.0, -1.0), bar_pt(-148.0, -1.0)], 1.8, "FFE2E8F0", 0.2, cap="round"),
        stroke_shape(i2, "FarSleeveOuter", [bar_pt(-114.0), bar_pt(-150.0)], 6.6, "FF94A3B8", 0.0, cap="round"),

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 6. Floor Shadows & Scenery
def floor_shadow_and_scenery():
    ind = "        "
    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"
    return "\n".join([
        f'{ind}<Shape x="296" y="295" scaleX="1.45" scaleY="0.085" name="BenchRackFloorShadow">\n'
        f'{ind}    <Ellipse width="280" height="220" name="BenchRackShadowEllipse"/>\n'
        f'{ind}    <Fill name="BenchRackShadowFill"><RadialGradient startX="0" startY="0" endX="140" endY="0" name="BenchRackShadowGrad">'
        f'<GradientStop colorValue="CC000000" position="0"/><GradientStop colorValue="59000000" position="0.62"/>'
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


front_rollers_xml, mid_bench_xml, far_rack_xml = decline_bench_and_rack_layers()
barbell_xml = barbell_rig()
near_arm_xml = arm_rig("Near", False)
near_leg_xml = near_leg()
torso_xml = decline_torso_and_head()
far_arm_xml = arm_rig("Far", True)
far_leg_xml = far_leg()
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
    <!-- Decline Bench Press: 3/4 front-left view, 60 fps, 16:9 (640x360), generated by gen_decline_bench_press.py -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="DeclineBenchPress" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- 1. Frontmost Lower Shin/Ankle Foam Rollers locking the athlete's ankles -->
{front_rollers_xml}

        <!-- 2. 3D Olympic Barbell, 45-lb Bumper Plates & Finger Wraps (in front of chest/arms) -->
{barbell_xml}

        <!-- 3. Near (Left) Articulated Arm with Anterior Deltoid & Triceps Brachii -->
{near_arm_xml}

        <!-- 4. Near (Left) Anchored Leg (Thigh over Knee Roller, Shin behind Ankle Roller) -->
{near_leg_xml}

        <!-- 5. Declined Supine Torso, 6-Pack Abs, Lower & Upper Pectoralis Major, and 3/4 Head -->
{torso_xml}

        <!-- 6. Far (Right) Articulated Arm with Anterior Deltoid & Triceps Brachii -->
{far_arm_xml}

        <!-- 7. Upper Knee Rollers, Declined Bench Pad, Steel Frame & Near Rack Upright -->
{mid_bench_xml}

        <!-- 8. Far (Right) Anchored Leg -->
{far_leg_xml}

        <!-- 9. Far (Upper-Left) Barbell Rack Upright behind Far Arm -->
{far_rack_xml}

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

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="DeclineBenchPress" id="0:60">
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
    """Build the .riv, copy it into the Flutter assets, and render the catalog thumbnail."""
    built = HERE / "build/decline_bench_press.riv"
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
