#!/usr/bin/env python3
"""Generates rive_animations/chest_fly/scene.rml (and optionally publishes).

16:9 (640x360, FLOOR = 300.0) 60 fps procedural Rive animation for the
Incline Dumbbell Chest Fly (`id: chest_fly`), matching the 2-panel 3/4 front-left
anatomical reference chart:
  - Camera: 3/4 front-left isometric view showing the athlete reclined at ~38 deg
    on an upholstered incline weight bench with a white/silver powder-coated steel
    frame resting on FLOOR = 300.0.
  - Anatomy:
    - Volumetric 3/4 head resting near the top of the backrest looking up-left
      toward the dumbbells (short dark hair cap, ear, brow, nose bridge/tip, jaw/chin),
      with sternocleidomastoid neck tendons.
    - Sculpted 6-pack rectus abdominis, linea alba, serratus anterior interdigitations,
      and external obliques above dark athletic compression shorts.
    - Both legs straddling the bench in 3/4 perspective with sculpted quadriceps
      (rectus femoris, vastus lateralis, vastus medialis), patella, tibialis anterior,
      and gastrocnemius contours.
  - Biomechanics (`r` in [0.0, 1.0], 168 frames / 2.8s @ 60 fps):
    - Bottom Stretch (`r = 0.0`, left panel): Arms open wide to the sides with a
      soft elbow bend (~22 deg) holding 3D cast-iron double-plate dumbbells in a
      neutral grip (palms facing inward/upward).
    - Wide Barrel-Hugging Arc (`0.0 < r < 1.0`): Wrists sweep along a polar circular
      arc around each shoulder so the elbows bow wide outward at mid-rep (`r = 0.5`)
      like hugging a barrel, never collapsing inward like a press.
    - Peak Contraction (`r = 1.0`, right panel): Both arms reach overhead above the
      upper chest with the two 3D dumbbells held parallel side-by-side (`y ~ 36..46`)
      while the pectorals dynamically contract and bulge inward toward the sternum.

Activated muscles (`muscle_t`):
  - Primary: Upper Pectoralis Major (Clavicular Head) + Sternocostal Pectoral Fibers
  - Secondary: Anterior Deltoid (front shoulder cap) & Biceps Brachii (Short Head)

Usage (from this directory):
    python3 gen_chest_fly.py            # regenerate scene.rml
    python3 gen_chest_fly.py --publish  # + build .riv, copy to assets, render thumbnail
"""
import math
import pathlib
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "scene.rml"
ASSET_RIV = REPO / "assets/animations/chest_fly.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/chest_fly.png"
THUMB_ADVANCE = "0.85s"  # dynamic mid-upper barrel-hugging fly frame with glowing red upper pecs, front delts & biceps short head
THUMB_VIEWPORT = "1280x720"  # 2x the 640x360 artboard
THUMB_CROP = (680, 16, 250)  # square size, offsetY, offsetX in the 2x render
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

# 16:9 standard canvas
W, H = 640, 360
FLOOR = 300.0

# Shoulder anchors in world space (athlete reclined ~38 deg on the incline backrest)
SHOULDER_FAR = (304.0, 114.0)   # Right (far / upper-left) shoulder
SHOULDER_NEAR = (350.0, 134.0)  # Left (near / lower-right) shoulder

# Rigid 2D limb lengths for the 3/4 front-left view
UPPER_ARM_FAR, FOREARM_FAR = 42.0, 41.0
UPPER_ARM_NEAR, FOREARM_NEAR = 45.0, 43.0

# Timeline (frames @60fps):
# 0..12: bottom wide-stretch hold (r=0.0)
# 12..68: concentric wide hugging fly upward (r: 0.0 -> 1.0)
# 68..84: peak isometric squeeze at top (r=1.0)
# 84..154: controlled eccentric lowering along wide arc (r: 1.0 -> 0.0)
# 154..168: bottom wide-stretch hold (r=0.0)
HOLD_BOT_1 = 12
RAISE_FRAMES = 56
HOLD_TOP = 16
LOWER_FRAMES = 70
HOLD_BOT_2 = 14
DURATION = HOLD_BOT_1 + RAISE_FRAMES + HOLD_TOP + LOWER_FRAMES + HOLD_BOT_2  # 168 frames (2.8s)
STEP = 2


def cubic_bezier(x1, y1, x2, y2):
    def bez(t, a, b):
        return 3 * a * t * (1 - t) ** 2 + 3 * b * t * t * (1 - t) + t ** 3

    def ease(x):
        if x <= 0.0:
            return 0.0
        if x >= 1.0:
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(50):
            mid = (lo + hi) / 2
            if bez(mid, x1, x2) < x:
                lo = mid
            else:
                hi = mid
        return bez((lo + hi) / 2, y1, y2)

    return ease


EASE_UP = cubic_bezier(0.42, 0.0, 0.58, 1.0)
EASE_DOWN = cubic_bezier(0.42, 0.0, 0.58, 1.0)


def fly_progress(frame):
    """0.0 at bottom wide chest stretch (Panel 1), 1.0 at peak overhead squeeze (Panel 2)."""
    fr = frame % DURATION
    if fr <= HOLD_BOT_1:
        return 0.0
    fr -= HOLD_BOT_1
    if fr <= RAISE_FRAMES:
        return EASE_UP(fr / RAISE_FRAMES)
    fr -= RAISE_FRAMES
    if fr <= HOLD_TOP:
        return 1.0
    fr -= HOLD_TOP
    if fr <= LOWER_FRAMES:
        return 1.0 - EASE_DOWN(fr / LOWER_FRAMES)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def solve_ik(root, target, l1, l2, bend_sign):
    """2D two-bone IK from root -> mid -> target."""
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = math.hypot(dx, dy)
    d_clamped = min(max(d, abs(l1 - l2) + 0.5), l1 + l2 - 0.5)
    base_ang = math.atan2(dy, dx)
    cos_a = max(-1.0, min(1.0, (l1 * l1 + d_clamped * d_clamped - l2 * l2) / (2.0 * l1 * d_clamped)))
    ang1 = base_ang + bend_sign * math.acos(cos_a)
    mid = (root[0] + l1 * math.cos(ang1), root[1] + l1 * math.sin(ang1))
    ang2 = math.atan2(target[1] - mid[1], target[0] - mid[0])
    return ang1, ang2, mid


# Polar wrist endpoints relative to each shoulder so the wrists sweep a wide circular
# barrel-hugging arc rather than cutting inward in a straight line:
# Far (Right) arm around SHOULDER_FAR = (304, 114):
#   Bottom (r=0.0): wrist at (234, 80) -> dx = -70, dy = -34 (ang = -154.1 deg, rad = 77.8)
#   Top    (r=1.0): wrist at (318, 36) -> dx = +14, dy = -78 (ang = -79.8 deg,  rad = 79.2)
_FAR_ANG_0 = math.atan2(80.0 - SHOULDER_FAR[1], 234.0 - SHOULDER_FAR[0])
_FAR_ANG_1 = math.atan2(36.0 - SHOULDER_FAR[1], 318.0 - SHOULDER_FAR[0])
_FAR_RAD_0 = math.hypot(234.0 - SHOULDER_FAR[0], 80.0 - SHOULDER_FAR[1])
_FAR_RAD_1 = math.hypot(318.0 - SHOULDER_FAR[0], 36.0 - SHOULDER_FAR[1])

# Near (Left) arm around SHOULDER_NEAR = (350, 134):
#   Bottom (r=0.0): wrist at (424, 162) -> dx = +74, dy = +28 (ang = +20.7 deg, rad = 79.1)
#   Top    (r=1.0): wrist at (348, 48)  -> dx = -2,  dy = -86 (ang = -91.3 deg, rad = 86.0)
_NEAR_ANG_0 = math.atan2(162.0 - SHOULDER_NEAR[1], 424.0 - SHOULDER_NEAR[0])
_NEAR_ANG_1 = math.atan2(48.0 - SHOULDER_NEAR[1], 348.0 - SHOULDER_NEAR[0])
_NEAR_RAD_0 = math.hypot(424.0 - SHOULDER_NEAR[0], 162.0 - SHOULDER_NEAR[1])
_NEAR_RAD_1 = math.hypot(348.0 - SHOULDER_NEAR[0], 48.0 - SHOULDER_NEAR[1])


def pose(r):
    """Compute Wide Barrel-Hugging Chest Fly pose at progress r in [0.0, 1.0]."""
    arc_bow = math.sin(r * math.pi)

    # 1. Far (Right) wrist polar arc around SHOULDER_FAR = (304, 114)
    far_ang = lerp(_FAR_ANG_0, _FAR_ANG_1, r)
    far_rad = lerp(_FAR_RAD_0, _FAR_RAD_1, r) - 1.5 * arc_bow
    hand_far = (
        SHOULDER_FAR[0] + far_rad * math.cos(far_ang),
        SHOULDER_FAR[1] + far_rad * math.sin(far_ang),
    )

    # 2. Near (Left) wrist polar arc around SHOULDER_NEAR = (350, 134)
    near_ang = lerp(_NEAR_ANG_0, _NEAR_ANG_1, r)
    near_rad = lerp(_NEAR_RAD_0, _NEAR_RAD_1, r) - 2.0 * arc_bow
    hand_near = (
        SHOULDER_NEAR[0] + near_rad * math.cos(near_ang),
        SHOULDER_NEAR[1] + near_rad * math.sin(near_ang),
    )

    # 3. Two-bone IK with outward barrel-hugging elbow bend:
    #    Far (Right) elbow bows outward/down-left (bend_sign = -1.0)
    ua_far, fa_far_world, elbow_far = solve_ik(
        SHOULDER_FAR, hand_far, UPPER_ARM_FAR, FOREARM_FAR, bend_sign=-1.0
    )
    fa_far_local = fa_far_world - ua_far

    #    Near (Left) elbow bows outward/down-right (bend_sign = +1.0)
    ua_near, fa_near_world, elbow_near = solve_ik(
        SHOULDER_NEAR, hand_near, UPPER_ARM_NEAR, FOREARM_NEAR, bend_sign=1.0
    )
    fa_near_local = fa_near_world - ua_near

    # 4. Dynamic Pectoralis Major contraction:
    #    At r = 0.0 (wide stretch): pectorals are stretched wide toward the shoulders
    #    At r = 1.0 (peak squeeze): pectorals bulge upward-inward toward the sternum
    pec_near_dx = lerp(1.5, -2.5, r)
    pec_near_dy = lerp(1.0, -2.2, r)
    pec_far_dx = lerp(-1.2, 2.0, r)
    pec_far_dy = lerp(0.8, -2.0, r)
    chest_lift = lerp(0.8, -1.6, r)

    # 5. World-space neutral-grip dumbbell orientation (~ -28 deg / -24 deg parallel to torso incline)
    #    converted to Forearm local space so the handle always lies across the palm!
    db_far_rot = math.radians(lerp(-32.0, -24.0, r)) - fa_far_world
    db_near_rot = math.radians(lerp(-28.0, -22.0, r)) - fa_near_world

    return {
        "r": r,
        "hand_far": hand_far,
        "hand_near": hand_near,
        "elbow_far": elbow_far,
        "elbow_near": elbow_near,
        "ua_far": ua_far,
        "fa_far_local": fa_far_local,
        "ua_near": ua_near,
        "fa_near_local": fa_near_local,
        "pec_near_dx": pec_near_dx,
        "pec_near_dy": pec_near_dy,
        "pec_far_dx": pec_far_dx,
        "pec_far_dy": pec_far_dy,
        "chest_lift": chest_lift,
        "db_far_rot": db_far_rot,
        "db_near_rot": db_near_rot,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(fly_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = ("ua_far", "fa_far_local", "ua_near", "fa_near_local", "db_far_rot", "db_near_rot")
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
    for _fr in (0, 40, 52, 74, 120, DURATION):
        _p = POSES[_fr]
        print(
            f"f{_fr:3d} r={_p['r']:.3f} far_w=({_p['hand_far'][0]:.1f},{_p['hand_far'][1]:.1f}) "
            f"near_w=({_p['hand_near'][0]:.1f},{_p['hand_near'][1]:.1f}) "
            f"ua_near={math.degrees(_p['ua_near']):+.1f}"
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


def solid(name, c):
    return f'<Fill name="{name}Fill"><SolidColor colorValue="{c}" name="{name}Color"/></Fill>'


def skin_fill(name, y0, y1, trip, x0=0, x1=0):
    return f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *trip, x0=x0, x1=x1)}</Fill>'


def smooth_shape(indent, name, pts, paint, closed=True, x=None, y=None, sid=None):
    attrs = f'name="{name}"'
    if x is not None:
        attrs = f'x="{f(x)}" ' + attrs
    if y is not None:
        attrs = f'y="{f(y)}" ' + attrs
    if sid is not None:
        attrs = attrs + f' id="{sid}"'
    v = smooth_vertices(pts, closed, indent + "        ")
    cl = "true" if closed else "false"
    return (
        f"{indent}<Shape {attrs}>\n"
        f'{indent}    <PointsPath isClosed="{cl}" name="{name}Path">\n{v}\n{indent}    </PointsPath>\n'
        f"{indent}    {paint}\n"
        f"{indent}</Shape>"
    )


def poly_shape(indent, name, pts, paint, radius=1.5):
    v = "\n".join(
        f'{indent}        <StraightVertex x="{f(float(x))}" y="{f(float(y))}" radius="{f(radius)}"/>'
        for x, y in pts
    )
    return (
        f'{indent}<Shape name="{name}">\n'
        f'{indent}    <PointsPath isClosed="true" name="{name}Path">\n{v}\n{indent}    </PointsPath>\n'
        f"{indent}    {paint}\n"
        f"{indent}</Shape>"
    )


def stroke_shape(indent, name, pts, width, color, feather=0.0, closed=False, cap="round"):
    fe = f'<Feather strength="{f(feather)}" name="{name}Feather"/>' if feather > 0 else ""
    paint = (
        f'<Stroke thickness="{f(width)}" cap="{cap}" join="round" name="{name}Stroke">'
        f'<SolidColor colorValue="{color}" name="{name}Color"/>{fe}</Stroke>'
    )
    return smooth_shape(indent, name, pts, paint, closed=closed)


def ellipse_shape(indent, name, x, y, w, h, paint, rot_deg=0.0):
    rot = f' rotation="{f(math.radians(rot_deg))}"' if rot_deg else ""
    return (
        f'{indent}<Shape x="{f(x)}" y="{f(y)}"{rot} name="{name}">\n'
        f'{indent}    <Ellipse width="{f(w)}" height="{f(h)}" name="{name}El"/>\n'
        f"{indent}    {paint}\n"
        f"{indent}</Shape>"
    )


# ---------------------------------------------------------------- Palette & Muscle Activation
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF334155", "FF1E293B", "FF0F172A")
SHORTS_FAR = ("FF263142", "FF151E2E", "FF090D16")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "520F172A"

# Dynamic orange-to-crimson muscle activation palette (matching reference chart)
MUSCLE_LOW = (0xBF, 0xF9, 0x73, 0x16)       # warm glowing orange at wide bottom stretch
MUSCLE_HIGH = (0xF5, 0xF4, 0x3F, 0x5E)      # intense crimson-red at peak fly squeeze
MUSCLE_LINE_LOW = (0x80, 0x9A, 0x34, 0x12)
MUSCLE_LINE_HIGH = (0xE6, 0x88, 0x13, 0x37)


def argb_lerp(a, b, t):
    return "".join(f"{round(lerp(x, y, t)):02X}" for x, y in zip(a, b))


keys = []


def key_double(obj, prop, fn):
    keys.append((obj, prop, "double", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def key_color(obj, prop, fn):
    keys.append((obj, prop, "color", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def muscle_t(p, scale=1.0):
    """Activation curve: warm orange stretch at r=0.0 (0.30) -> fiery crimson squeeze at r=1.0 (1.00)."""
    base = 0.30 + 0.70 * (p["r"] ** 0.85)
    return min(1.0, max(0.0, base * scale))


muscle_fill_ids = []  # (cid, scale)
muscle_line_ids = []  # (cid, scale)


def muscle_paint(name, line=0.95, scale=1.0):
    fid, lid = nid(), nid()
    muscle_fill_ids.append((fid, scale))
    muscle_line_ids.append((lid, scale))
    t0 = muscle_t(POSES[0], scale)
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{line}" join="round" name="{name}Edge"><SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- 3D Incline Weight Bench
def front_bench_arch_rig():
    """Foreground white arched front stabilizer leg (drawn in front of FarRightLeg ankle and behind NearLeftLeg)."""
    ind = "        "
    i2 = ind + "    "
    steel_top = f'<Fill name="ArchTopFill">{grad("ArchTopGrad", 155, 240, 238, 300, "FFF8FAFC", "FFCBD5E1")}</Fill>'
    steel_side = f'<Fill name="ArchSideFill">{grad("ArchSideGrad", 155, 244, 238, 300, "FFCBD5E1", "FF64748B")}</Fill>'
    steel_edge = '<Stroke thickness="0.9" join="round" name="ArchRim"><SolidColor colorValue="FF94A3B8" name="ArchRimCol"/></Stroke>'
    rubber_foot = solid("ArchRubberFoot", "FF0F172A")

    return "\n".join([
        f'{ind}<Node name="FrontBenchArch">',
        poly_shape(
            i2, "FrontArchSide",
            [(158, 266), (186, 244), (210, 248), (234, 298), (222, 299), (202, 258), (184, 256), (164, 270)],
            steel_side + steel_edge, radius=3.5,
        ),
        poly_shape(
            i2, "FrontArchTop",
            [(156, 262), (184, 240), (212, 244), (236, 295), (226, 297), (204, 253), (186, 251), (162, 266)],
            steel_top + steel_edge, radius=3.5,
        ),
        poly_shape(i2, "FrontFootCapNear", [(220, 294), (237, 294), (238, 300), (219, 300)], rubber_foot, radius=1.5),
        poly_shape(i2, "FrontFootCapFar", [(152, 261), (166, 264), (165, 270), (151, 267)], rubber_foot, radius=1.5),
        f"{ind}</Node>",
    ])


def incline_bench_rig():
    """3D Isometric Incline Weight Bench with white/silver steel frame on FLOOR = 300.0 and dark upholstered pads."""
    ind = "        "
    i2 = ind + "    "

    steel_top = f'<Fill name="SteelTopFill">{grad("SteelTopGrad", 170, 200, 410, 300, "FFF8FAFC", "FFCBD5E1")}</Fill>'
    steel_side = f'<Fill name="SteelSideFill">{grad("SteelSideGrad", 170, 200, 410, 300, "FFCBD5E1", "FF64748B")}</Fill>'
    steel_edge = '<Stroke thickness="0.9" join="round" name="SteelRim"><SolidColor colorValue="FF94A3B8" name="SteelRimCol"/></Stroke>'

    pad_top = f'<Fill name="PadTopFill">{grad("PadTopGrad", 240, 95, 385, 225, "FF334155", "FF1E293B")}</Fill>'
    pad_side = f'<Fill name="PadSideFill">{grad("PadSideGrad", 240, 100, 390, 232, "FF1E293B", "FF090D16")}</Fill>'
    pad_rim = '<Stroke thickness="0.9" join="round" name="PadRim"><SolidColor colorValue="FF475569" name="PadRimCol"/></Stroke>'
    rubber_foot = solid("RubberFoot", "FF0F172A")

    return "\n".join([
        f'{ind}<Node name="InclineBench">',

        # 1. Upholstered Seat Pad (angled slightly upward-left under the athlete's pelvis/hips)
        stroke_shape(i2, "SeatPadEdgeHi", [(232, 212), (264, 224), (294, 206)], 1.2, "5994A3B8", 0.5),
        poly_shape(i2, "SeatPadFrontSkirt", [(228, 204), (264, 220), (264, 231), (228, 214)], pad_side, radius=2.5),
        poly_shape(i2, "SeatPadRightSkirt", [(264, 220), (296, 202), (296, 212), (264, 231)], pad_side, radius=2.5),
        poly_shape(i2, "SeatPadTop", [(228, 204), (260, 188), (296, 202), (264, 220)], pad_top + pad_rim, radius=3.0),

        # 2. Upholstered Inclined Backrest Pad (~38 deg incline from (282, 202) up-right to (376, 92))
        stroke_shape(i2, "BackrestHighlight", [(298, 204), (340, 152), (380, 102)], 1.4, "5994A3B8", 0.5),
        poly_shape(i2, "BackrestRightSide", [(296, 208), (382, 100), (390, 108), (304, 217)], pad_side + pad_rim, radius=3.0),
        poly_shape(i2, "BackrestBottomSkirt", [(274, 196), (296, 208), (304, 217), (282, 204)], pad_side, radius=2.5),
        poly_shape(i2, "BackrestTopFace", [(274, 196), (360, 88), (382, 100), (296, 208)], pad_top + pad_rim, radius=4.0),

        # 3. Under-Seat Main Spine Beam, Telescoping Backrest Support Strut & Rear Floor Stabilizer Leg on FLOOR = 300.0
        poly_shape(i2, "SeatSupportPost", [(256, 218), (268, 214), (268, 236), (256, 240)], steel_side + steel_edge, radius=1.5),
        poly_shape(i2, "BackrestLadderBracket", [(308, 210), (336, 226), (334, 232), (306, 216)], steel_side + steel_edge, radius=1.5),
        poly_shape(i2, "BackrestSupportStrut", [(318, 174), (327, 170), (340, 230), (331, 234)], steel_top + steel_edge, radius=1.5),
        poly_shape(i2, "MainSpineSide", [(196, 254), (296, 206), (296, 216), (196, 264)], steel_side + steel_edge, radius=2.0),
        poly_shape(i2, "MainSpineTop", [(194, 248), (294, 200), (298, 206), (198, 254)], steel_top + steel_edge, radius=2.0),
        poly_shape(i2, "RearStabilizerSide", [(292, 208), (396, 288), (393, 297), (290, 216)], steel_side + steel_edge, radius=2.5),
        poly_shape(i2, "RearStabilizerTop", [(294, 202), (398, 282), (396, 288), (292, 208)], steel_top + steel_edge, radius=2.5),
        poly_shape(i2, "RearFootCap", [(388, 288), (400, 290), (399, 300), (387, 300)], rubber_foot, radius=2.0),

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- Straddled Legs (3/4 Perspective)
def far_right_leg_rig():
    """Far (Right) Leg extending left from right hip (256, 186) to knee (188, 202) and foot peeking behind the front stabilizer arch."""
    ind = "        "
    i2 = ind + "    "

    shorts_pts = [
        (264, 174), (234, 172), (218, 178), (226, 204), (258, 198),
    ]
    thigh_pts = [
        (254, 176), (224, 175), (196, 185), (182, 198),
        (188, 214), (212, 211), (242, 202), (258, 194),
    ]
    shin_pts = [
        (182, 204), (186, 226), (194, 248), (200, 260),
        (210, 256), (212, 234), (208, 214), (196, 202),
    ]
    foot_pts = [
        (196, 254), (168, 256), (144, 263), (146, 270),
        (170, 268), (204, 262), (206, 256),
    ]

    return "\n".join([
        f'{ind}<Node name="FarRightLeg">',
        # 1. Thigh shorts hem & sculpted quadriceps (Rectus Femoris, Vastus Lateralis, Vastus Medialis, Sartorius)
        stroke_shape(i2, "FarShortsHem", [(220, 178), (222, 192), (227, 203)], 1.3, "80090D16", 0.4),
        smooth_shape(i2, "FarThighShorts", shorts_pts, skin_fill("FarShorts", 172, 204, SHORTS_FAR, x0=260, x1=218)),
        stroke_shape(i2, "FarQuadGroove1", [(232, 182), (208, 189), (190, 198)], 1.2, CORE_SHADOW, 0.7),
        stroke_shape(i2, "FarQuadGroove2", [(236, 192), (212, 199), (194, 205)], 1.2, CORE_SHADOW, 0.7),
        stroke_shape(i2, "FarVastusMedialisLine", [(208, 195), (198, 203), (204, 210)], 1.1, SOFT_SHADOW, 0.6),
        stroke_shape(i2, "FarThighHi", [(238, 180), (212, 184), (190, 194)], 3.2, HIGHLIGHT, 3.0),
        stroke_shape(i2, "FarThighSh", [(240, 199), (214, 207), (192, 211)], 3.8, CORE_SHADOW, 3.5),
        smooth_shape(i2, "FarThigh", thigh_pts, skin_fill("FarThigh", 175, 214, SKIN_FAR, x0=254, x1=182)),

        # 2. Knee Patella, Lower Leg (Tibialis Anterior & Gastrocnemius) & Foot
        ellipse_shape(i2, "FarKneeCap", 187, 204, 14, 15, skin_fill("FarKnee", -7, 7, SKIN_FAR)),
        stroke_shape(i2, "FarCalfGroove", [(198, 214), (204, 232), (204, 248)], 1.2, CORE_SHADOW, 0.7),
        stroke_shape(i2, "FarShinHi", [(188, 212), (194, 234), (200, 252)], 2.4, HIGHLIGHT, 2.5),
        smooth_shape(i2, "FarShin", shin_pts, skin_fill("FarShin", 202, 260, SKIN_FAR, x0=212, x1=182)),
        stroke_shape(i2, "FarFootSoleSh", [(148, 268), (174, 266), (200, 261)], 1.6, CORE_SHADOW, 1.0),
        smooth_shape(i2, "FarFoot", foot_pts, skin_fill("FarFoot", 254, 270, SKIN_FAR, x0=206, x1=144)),
        f"{ind}</Node>",
    ])


def near_left_leg_rig():
    """Near (Left) Leg in foreground from left hip (284, 198) to knee (252, 232) and planted foot on FLOOR = 300.0."""
    ind = "        "
    i2 = ind + "    "

    shorts_pts = [
        (264, 188), (298, 194), (300, 216), (282, 224), (258, 212),
    ]
    thigh_pts = [
        (268, 196), (294, 204), (288, 222), (272, 238),
        (252, 240), (244, 228), (252, 210),
    ]
    shin_pts = [
        (244, 232), (264, 234), (266, 254), (258, 274),
        (252, 290), (240, 290), (240, 268), (241, 248),
    ]
    foot_pts = [
        (240, 286), (253, 286), (254, 296), (244, 301),
        (230, 300), (228, 295), (235, 290),
    ]

    return "\n".join([
        f'{ind}<Node name="NearLeftLeg">',
        # 1. Thigh shorts + Sculpted Quadriceps (Rectus Femoris, Vastus Medialis teardrop, Vastus Lateralis)
        stroke_shape(i2, "NearShortsHem", [(259, 211), (272, 218), (284, 223)], 1.4, "80090D16", 0.4),
        smooth_shape(i2, "NearThighShorts", shorts_pts, skin_fill("NearShorts", 188, 224, SHORTS, x0=258, x1=300)),
        stroke_shape(i2, "NearRectusFemorisL", [(272, 204), (260, 218), (251, 230)], 1.3, CORE_SHADOW, 0.8),
        stroke_shape(i2, "NearRectusFemorisR", [(284, 210), (272, 224), (261, 234)], 1.3, CORE_SHADOW, 0.8),
        stroke_shape(i2, "NearVastusMedialis", [(256, 216), (248, 224), (252, 233)], 1.1, SOFT_SHADOW, 0.6),
        stroke_shape(i2, "NearThighHi", [(276, 205), (264, 219), (254, 231)], 3.8, HIGHLIGHT, 3.5),
        stroke_shape(i2, "NearThighSh", [(288, 214), (276, 229), (264, 237)], 4.2, CORE_SHADOW, 3.8),
        smooth_shape(i2, "NearThigh", thigh_pts, skin_fill("NearThigh", 196, 240, SKIN, x0=250, x1=294)),

        # 2. Knee Patella & Lower Leg (Tibialis Anterior & Gastrocnemius flare)
        ellipse_shape(i2, "NearKneeCap", 252, 235, 16, 15, skin_fill("NearKnee", -8, 8, SKIN)),
        stroke_shape(i2, "NearPatellaLine", [(246, 238), (252, 242), (258, 238)], 1.1, SOFT_SHADOW, 0.5),
        stroke_shape(i2, "NearTibialisLine", [(250, 244), (248, 266), (246, 285)], 1.3, CORE_SHADOW, 0.8),
        stroke_shape(i2, "NearCalfFlareLine", [(258, 246), (261, 262), (254, 278)], 1.2, SOFT_SHADOW, 0.7),
        stroke_shape(i2, "NearShinHi", [(246, 244), (245, 266), (244, 284)], 2.8, HIGHLIGHT, 2.8),
        stroke_shape(i2, "NearShinSh", [(260, 248), (259, 266), (252, 284)], 3.2, CORE_SHADOW, 3.0),
        smooth_shape(i2, "NearShin", shin_pts, skin_fill("NearShin", 232, 290, SKIN, x0=240, x1=266)),

        # 3. Planted Left Foot on FLOOR = 300.0 with Toe Creases
        stroke_shape(i2, "NearToeLine1", [(234, 295), (238, 299)], 0.9, SOFT_SHADOW, 0.3),
        stroke_shape(i2, "NearToeLine2", [(239, 295), (243, 300)], 0.9, SOFT_SHADOW, 0.3),
        stroke_shape(i2, "NearFootHi", [(244, 289), (238, 294)], 2.0, HIGHLIGHT, 1.8),
        smooth_shape(i2, "NearFoot", foot_pts, skin_fill("NearFoot", 286, 301, SKIN, x0=230, x1=254)),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- Reclined Torso, Pectorals, 6-Pack Abs & 3/4 Head
def reclined_torso_and_head_rig():
    """Reclined torso (~38 deg), sculpted 6-pack abs, serratus anterior, dynamic Upper + Sternal Pectorals, and 3/4 Head."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "

    chest_id = nid()
    pec_far_id = nid()
    pec_near_id = nid()
    key_double(chest_id, 14, lambda p: p["chest_lift"])
    key_double(pec_far_id, 13, lambda p: p["pec_far_dx"])
    key_double(pec_far_id, 14, lambda p: p["pec_far_dy"])
    key_double(pec_near_id, 13, lambda p: p["pec_near_dx"])
    key_double(pec_near_id, 14, lambda p: p["pec_near_dy"])
    p0 = POSES[0]

    # 1. Pelvis / Compression Shorts bridging both hips on the seat pad
    pelvis_shorts_pts = [
        (246, 174), (268, 174), (298, 190),
        (300, 212), (274, 216), (244, 196),
    ]

    # 2. Reclined Torso Silhouette (from waist (258, 178)..(296, 194) up-right to shoulders (304, 114) & (350, 134))
    torso_pts = [
        (256, 176), (272, 156), (288, 136), (302, 114),
        (326, 112), (350, 128), (352, 148), (334, 168),
        (314, 184), (296, 196), (274, 190),
    ]

    # 3. Sculpted 6-Pack Rectus Abdominis (2 rows of 3 anatomical blocks along the ~38 deg torso midline)
    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1F0F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.95" join="round" name="AbsEdge"><SolidColor colorValue="470F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        # Right (upper-left) 3 rectus abdominis blocks
        [(292, 144), (302, 135), (311, 141), (301, 151)],
        [(281, 156), (291, 146), (300, 153), (290, 163)],
        [(270, 168), (280, 158), (289, 165), (279, 175)],
        # Left (lower-right) 3 rectus abdominis blocks
        [(303, 152), (313, 142), (322, 149), (312, 159)],
        [(292, 164), (302, 154), (311, 161), (301, 171)],
        [(281, 176), (291, 166), (300, 173), (290, 183)],
    ]

    # 4. Pectoralis Major:
    #    - Sternocostal Head (lower/middle fan-shaped chest plate, warm orange-red activation)
    #    - Upper Pectoralis Major / Clavicular Head (upper-chest band along the clavicle, intense crimson-red activation!)
    pec_right_sternal_pts = [
        (296, 126), (304, 116), (322, 120),
        (320, 134), (308, 139), (295, 134),
    ]
    pec_right_clavicular_pts = [
        (299, 118), (307, 111), (325, 116),
        (322, 124), (306, 122),
    ]

    pec_left_sternal_pts = [
        (322, 134), (332, 124), (348, 134),
        (344, 150), (328, 154), (315, 144),
    ]
    pec_left_clavicular_pts = [
        (324, 123), (330, 117), (348, 127),
        (345, 137), (329, 130),
    ]

    # 5. Volumetric 3/4 Head & Neck resting near top of backrest looking up-left
    neck_pts = [
        (322, 116), (334, 98), (350, 108), (336, 124),
    ]
    head_pts = [
        (332, 99),   # under chin
        (326, 92),   # chin tip (facing up-left)
        (327, 85),   # lower/upper lip profile
        (329, 79),   # nose tip
        (334, 74),   # brow ridge & forehead
        (345, 70),   # high cranial dome
        (357, 73),   # upper-right crown
        (363, 83),   # back of skull
        (360, 95),   # occiput resting on pad
        (351, 102),  # behind left ear
        (340, 102),  # mandible jaw angle
    ]
    hair_pts = [
        (337, 73), (347, 69.5), (358, 72.5), (364, 82),
        (361, 95), (354, 99), (355, 89), (350, 80), (342, 76),
    ]

    out = [f'{ind}<Node name="ReclinedTorsoAndHead">']

    # --- 1. Animated Chest Group (Upper Clavicular Pectorals + Sternocostal Pectorals) ---
    out.append(f'{i2}<Node y="{f(p0["chest_lift"])}" name="ChestGroup" id="{chest_id}">')

    # Sternal cleavage line between left and right pectorals
    out.append(stroke_shape(i3, "SternalCleavage", [(326, 117), (321, 130), (315, 140)], 1.6, "997C2D12", 0.5))

    # Near (Left) Pectoralis Major (Clavicular Head on top + Sternocostal Head below)
    out.append(f'{i3}<Node x="{f(p0["pec_near_dx"])}" y="{f(p0["pec_near_dy"])}" name="PecLeftNode" id="{pec_near_id}">')
    out.append(stroke_shape(i4, "UpperPecLeftHi", [(328, 122), (338, 126), (345, 132)], 2.2, HIGHLIGHT, 2.0))
    out.append(stroke_shape(i4, "UpperPecLeftGroove", [(324, 128), (335, 133), (345, 137)], 1.2, "B3881337", 0.4))
    out.append(smooth_shape(i4, "UpperPecLeftActivation", pec_left_clavicular_pts, muscle_paint("UpperPecLeft", 1.0, scale=1.0)))
    out.append(stroke_shape(i4, "PecLeftFiber1", [(320, 138), (332, 139), (343, 141)], 0.95, "737C2D12", 0.3))
    out.append(stroke_shape(i4, "PecLeftFiber2", [(318, 143), (330, 146), (341, 147)], 0.95, "737C2D12", 0.3))
    out.append(stroke_shape(i4, "PecLeftUnderFold", [(315, 145), (328, 154), (343, 150)], 1.5, CORE_SHADOW, 0.8))
    out.append(smooth_shape(i4, "PecLeftSternalActivation", pec_left_sternal_pts, muscle_paint("PecLeftSternal", 0.9, scale=0.72)))
    out.append(f"{i3}</Node>")

    # Far (Right) Pectoralis Major (Clavicular Head on top + Sternocostal Head below)
    out.append(f'{i3}<Node x="{f(p0["pec_far_dx"])}" y="{f(p0["pec_far_dy"])}" name="PecRightNode" id="{pec_far_id}">')
    out.append(stroke_shape(i4, "UpperPecRightHi", [(303, 115), (313, 116), (322, 119)], 1.8, HIGHLIGHT, 1.8))
    out.append(stroke_shape(i4, "UpperPecRightGroove", [(300, 121), (312, 122), (322, 124)], 1.1, "B3881337", 0.4))
    out.append(smooth_shape(i4, "UpperPecRightActivation", pec_right_clavicular_pts, muscle_paint("UpperPecRight", 0.95, scale=1.0)))
    out.append(stroke_shape(i4, "PecRightFiber1", [(298, 128), (309, 129), (319, 130)], 0.9, "737C2D12", 0.3))
    out.append(stroke_shape(i4, "PecRightUnderFold", [(295, 134), (308, 139), (320, 134)], 1.4, CORE_SHADOW, 0.7))
    out.append(smooth_shape(i4, "PecRightSternalActivation", pec_right_sternal_pts, muscle_paint("PecRightSternal", 0.85, scale=0.72)))
    out.append(f"{i3}</Node>")

    out.append(f"{i2}</Node>")

    # --- 2. Sculpted 6-Pack Rectus Abdominis, Linea Alba, Serratus Anterior & External Obliques ---
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "LineaAlba", [(315, 139), (296, 160), (277, 180)], 1.4, CORE_SHADOW, 0.8))
    # Serratus Anterior ribs on the near-left lateral ribcage
    out.append(stroke_shape(i2, "SerratusRib1", [(324, 156), (334, 154)], 1.2, CORE_SHADOW, 0.6))
    out.append(stroke_shape(i2, "SerratusRib2", [(316, 164), (326, 162)], 1.2, CORE_SHADOW, 0.6))
    out.append(stroke_shape(i2, "SerratusRib3", [(308, 172), (318, 170)], 1.2, CORE_SHADOW, 0.6))
    # External oblique grooves framing the rectus abdominis
    out.append(stroke_shape(i2, "ObliqueLineLeft", [(322, 152), (308, 168), (294, 184)], 1.3, SOFT_SHADOW, 0.7))
    out.append(stroke_shape(i2, "ObliqueLineRight", [(290, 142), (278, 158), (266, 172)], 1.3, SOFT_SHADOW, 0.7))

    # --- 3. Pelvis Compression Shorts & Torso Base ---
    out.append(stroke_shape(i2, "ShortsWaistband", [(250, 174), (274, 180), (297, 191)], 1.5, "99020617", 0.4))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts_pts, skin_fill("PelvisShorts", 174, 216, SHORTS, x0=246, x1=300)))
    out.append(stroke_shape(i2, "TorsoHi", [(298, 134), (284, 152), (270, 168)], 4.0, HIGHLIGHT, 3.8))
    out.append(stroke_shape(i2, "TorsoSh", [(340, 156), (320, 176), (298, 192)], 5.0, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i2, "TorsoBase", torso_pts, skin_fill("Torso", 112, 196, SKIN, x0=270, x1=350)))

    # --- 4. Volumetric 3/4 Head & Neck (drawn behind the clavicles so the neck tucks into the sternal notch) ---
    out.append(f'{i2}<Node name="HeadAndNeck">')
    out.append(smooth_shape(i3, "HairCap", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 336, 70, 364, 98, "FF334155", "FF0F172A")}</Fill>'))
    out.append(ellipse_shape(i3, "LeftEar", 348.5, 96.5, 6.5, 5.0, solid("Ear", "FFCBD5E1"), rot_deg=-25.0))
    out.append(stroke_shape(i3, "EarHelix", [(347.5, 95.5), (349.5, 97.0)], 0.9, SOFT_SHADOW, 0.2))
    # Facial features in 3/4 up-left profile (brow ridge, eye socket shadow, nose bridge, mouth line, jawline)
    out.append(stroke_shape(i3, "BrowAndEye", [(334.5, 78.5), (338.0, 80.5)], 1.3, CORE_SHADOW, 0.5))
    out.append(stroke_shape(i3, "MouthLine", [(328.0, 87.5), (332.0, 89.0)], 1.0, SOFT_SHADOW, 0.3))
    out.append(stroke_shape(i3, "JawlineShadow", [(328.0, 95.0), (338.0, 100.5), (346.0, 99.0)], 1.8, CORE_SHADOW, 1.2))
    out.append(stroke_shape(i3, "HeadHighlight", [(331.0, 82.0), (337.0, 75.0), (348.0, 72.5)], 2.8, HIGHLIGHT, 2.8))
    out.append(smooth_shape(i3, "HeadShape", head_pts, skin_fill("Head", 70, 102, SKIN, x0=326, x1=363)))
    # Sternocleidomastoid (SCM) V-tendons on the neck
    out.append(stroke_shape(i3, "NeckSCMLeft", [(344.0, 102.0), (334.0, 114.0), (326.0, 120.0)], 1.4, CORE_SHADOW, 0.8))
    out.append(stroke_shape(i3, "NeckSCMRight", [(332.0, 99.0), (325.0, 110.0), (322.0, 118.0)], 1.2, SOFT_SHADOW, 0.7))
    out.append(smooth_shape(i3, "NeckShape", neck_pts, skin_fill("Neck", 98, 124, SKIN_FAR, x0=322, x1=350)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3D Cast-Iron Dumbbells & 2-Bone IK Arms
def dumbbell_3d(indent, prefix, is_near):
    """3D Cast-Iron Double-Plate Dumbbell in neutral fly grip (handle along local X, which is -28 deg in world space)."""
    i2 = indent + "    "
    plate_face = (
        f'<Fill name="{prefix}PlateFace">{grad(prefix + "PFG", -9, -15, 9, 15, "FF334155", "FF090D16")}</Fill>'
        f'<Stroke thickness="1.0" name="{prefix}PlateRim"><SolidColor colorValue="FF64748B" name="{prefix}PRCol"/></Stroke>'
    )
    plate_edge = (
        f'<Fill name="{prefix}PlateEdge"><SolidColor colorValue="FF0F172A" name="{prefix}PECol"/></Fill>'
        f'<Stroke thickness="0.9" name="{prefix}PlateEdgeRim"><SolidColor colorValue="FF475569" name="{prefix}PERCol"/></Stroke>'
    )
    chrome_bar = f'<Fill name="{prefix}BarFill">{grad(prefix + "BarG", -15, -3, 15, 3, "FFF8FAFC", "FF475569")}</Fill>'
    skin = SKIN if is_near else SKIN_FAR

    # Wrapped fingers & thumb around the chrome handle in neutral fly grip
    fingers_pts = [
        (-5.2, -4.5), (4.8, -4.5), (6.2, 0.0), (4.8, 4.5), (-5.2, 4.5),
    ]
    thumb_pts = [
        (-6.0, -2.2), (-1.5, -5.5), (3.5, -4.0), (2.0, -1.0), (-4.5, -0.5),
    ]

    out = [f'{indent}<Node name="{prefix}DumbbellNode">']
    # 1. Foreground: Front-Left Double Cast-Iron Plate Stack (closest to camera at -X in DumbbellNode local space)
    out.append(ellipse_shape(i2, f"{prefix}FrontCollar", -14.8, 0.0, 5.2, 8.5, chrome_bar))
    out.append(ellipse_shape(i2, f"{prefix}FrontOuterPlateEdge", -13.5, 0.0, 13.5, 24.0, plate_edge))
    out.append(ellipse_shape(i2, f"{prefix}FrontOuterPlateFace", -12.0, 0.0, 13.5, 24.0, plate_face))
    out.append(ellipse_shape(i2, f"{prefix}FrontInnerPlateEdge", -9.5, 0.0, 16.5, 29.0, plate_edge))
    out.append(ellipse_shape(i2, f"{prefix}FrontInnerPlateFace", -7.8, 0.0, 16.5, 29.0, plate_face))

    # 2. Midground: Wrapped Fingers, Thumb & Chrome Handle Bar
    out.append(smooth_shape(i2, f"{prefix}Thumb", thumb_pts, skin_fill(prefix + "Thumb", -6, 0, skin)))
    out.append(stroke_shape(i2, f"{prefix}Knuckle1", [(-2.0, -3.5), (-1.8, 3.5)], 0.9, SOFT_SHADOW, 0.3))
    out.append(stroke_shape(i2, f"{prefix}Knuckle2", [(1.2, -3.5), (1.4, 3.5)], 0.9, SOFT_SHADOW, 0.3))
    out.append(smooth_shape(i2, f"{prefix}Fingers", fingers_pts, skin_fill(prefix + "Fingers", -5, 5, skin)))
    handle_pts = [(-14.0, -1.8), (14.0, -1.8), (14.0, 1.8), (-14.0, 1.8)]
    out.append(poly_shape(i2, f"{prefix}HandleBar", handle_pts, chrome_bar, radius=1.2))

    # 3. Background: Rear-Right Double Cast-Iron Plate Stack (further from camera at +X in DumbbellNode local space)
    out.append(ellipse_shape(i2, f"{prefix}RearInnerPlateEdge", 8.2, 0.0, 16.5, 29.0, plate_edge))
    out.append(ellipse_shape(i2, f"{prefix}RearInnerPlateFace", 9.8, 0.0, 16.5, 29.0, plate_face))
    out.append(ellipse_shape(i2, f"{prefix}RearOuterPlateEdge", 12.0, 0.0, 13.5, 24.0, plate_edge))
    out.append(ellipse_shape(i2, f"{prefix}RearOuterPlateFace", 13.5, 0.0, 13.5, 24.0, plate_face))
    out.append(ellipse_shape(i2, f"{prefix}RearCollar", 15.0, 0.0, 5.0, 8.0, chrome_bar))
    out.append(f"{indent}</Node>")
    return "\n".join(out)


def arm_rig(prefix, is_near):
    """2-Bone IK Arm (UpperArm -> Forearm -> 3D Dumbbell) with Anterior Deltoid & Biceps Brachii (Short Head) activation."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "

    skin = SKIN if is_near else SKIN_FAR
    sx, sy = SHOULDER_NEAR if is_near else SHOULDER_FAR
    ua_len = UPPER_ARM_NEAR if is_near else UPPER_ARM_FAR
    fa_len = FOREARM_NEAR if is_near else FOREARM_FAR
    ua_key = "ua_near" if is_near else "ua_far"
    fa_key = "fa_near_local" if is_near else "fa_far_local"
    db_key = "db_near_rot" if is_near else "db_far_rot"

    ua_id, fa_id, db_id = nid(), nid(), nid()
    key_double(ua_id, 15, lambda p: p[ua_key])
    key_double(fa_id, 15, lambda p: p[fa_key])
    key_double(db_id, 15, lambda p: p[db_key])
    p0 = POSES[0]

    # Note on local Y orientation of UpperArm (+X points from shoulder to elbow):
    # - For Near (Left) Arm: at r=0.0 (+20 deg) and r=1.0 (-80 deg), local -Y faces INWARD/UPWARD
    #   (anterior deltoid & biceps brachii short head), while local +Y faces OUTWARD/DOWNWARD (triceps/brachialis).
    # - For Far (Right) Arm: at r=0.0 (-168 deg) and r=1.0 (-76 deg), local +Y faces INWARD/UPWARD
    #   toward the chest/chin (anterior deltoid & biceps brachii short head), while local -Y faces OUTWARD/BACK.
    in_sign = -1.0 if is_near else 1.0

    # 1. Sculpted Upper Arm Silhouette (0 .. ua_len)
    ua_pts = [
        (-8.0, 0.0), (-5.0, -9.5), (8.0, -11.0), (ua_len * 0.55, -10.2), (ua_len - 4.0, -7.2),
        (ua_len + 4.5, 0.0), (ua_len - 4.0, 7.2), (ua_len * 0.55, 10.2), (8.0, 11.0), (-5.0, 9.5),
    ]

    # 2. Activated Biceps Brachii (Short Head) along the inner/anterior aspect of the upper arm (matching reference chart!)
    biceps_short_pts = [
        (9.0, in_sign * 1.2),
        (ua_len * 0.45, in_sign * 0.8),
        (ua_len - 4.5, in_sign * 2.2),
        (ua_len - 6.5, in_sign * 8.2),
        (ua_len * 0.48, in_sign * 10.2),
        (10.0, in_sign * 8.8),
    ]

    # 3. Sculpted Deltoid Cap + Activated Anterior Deltoid
    delt_pts = [
        (-11.5, 0.0), (-7.5, -10.5), (4.0, -12.0), (15.5, -8.5),
        (18.0, 0.0), (15.5, 8.5), (4.0, 12.0), (-7.5, 10.5),
    ]
    front_delt_pts = [
        (-7.0, in_sign * 1.5),
        (3.5, in_sign * 10.8),
        (15.0, in_sign * 8.0),
        (16.5, in_sign * 1.0),
        (4.5, -in_sign * 2.0),
    ]

    # 4. Sculpted Forearm (Brachioradialis & Flexor Carpi) from elbow (0,0) to wrist (fa_len, 0)
    fa_pts = [
        (-5.5, 0.0), (-3.5, -7.5), (fa_len * 0.35, -8.8), (fa_len - 5.0, -5.2),
        (fa_len + 4.0, 0.0), (fa_len - 5.0, 5.2), (fa_len * 0.35, 8.8), (-3.5, 7.5),
    ]

    out = [f'{ind}<Node x="{f(sx)}" y="{f(sy)}" rotation="{f(p0[ua_key])}" name="{prefix}Arm" id="{ua_id}">']

    # --- 1. Forearm & 3D Cast-Iron Dumbbell (drawn in front of the elbow joint) ---
    out.append(f'{i2}<Node x="{f(ua_len)}" rotation="{f(p0[fa_key])}" name="{prefix}Forearm" id="{fa_id}">')
    out.append(f'{i3}<Node x="{f(fa_len)}" rotation="{f(p0[db_key])}" name="{prefix}DumbbellPivot" id="{db_id}">')
    out.append(dumbbell_3d(i4, prefix, is_near))
    out.append(f"{i3}</Node>")
    out.append(stroke_shape(i3, f"{prefix}ForearmGroove", [(4.0, in_sign * 1.0), (fa_len * 0.5, in_sign * 1.5), (fa_len - 6.0, in_sign * 0.8)], 1.2, CORE_SHADOW, 0.7))
    out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(5.0, in_sign * 4.2), (fa_len - 8.0, in_sign * 3.0)], 2.6, HIGHLIGHT, 2.8))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(5.0, -in_sign * 4.5), (fa_len - 8.0, -in_sign * 3.2)], 3.0, CORE_SHADOW, 2.8))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -9, 9, skin)))
    out.append(f"{i2}</Node>")

    # --- 2. Anterior Deltoid Activation & Shoulder Cap ---
    out.append(stroke_shape(i2, f"{prefix}FrontDeltHi", [(0.0, in_sign * 5.5), (11.0, in_sign * 5.0)], 2.2, HIGHLIGHT, 2.0))
    out.append(stroke_shape(i2, f"{prefix}DeltFiber", [(-2.0, in_sign * 4.0), (12.0, in_sign * 4.5)], 0.9, "737C2D12", 0.3))
    out.append(smooth_shape(i2, f"{prefix}FrontDeltActivation", front_delt_pts, muscle_paint(prefix + "FrontDelt", 0.95, scale=0.92)))
    out.append(stroke_shape(i2, f"{prefix}LateralDeltGroove", [(0.0, -in_sign * 2.5), (13.0, -in_sign * 2.0)], 1.2, CORE_SHADOW, 0.7))
    out.append(smooth_shape(i2, f"{prefix}DeltoidCap", delt_pts, skin_fill(prefix + "Deltoid", -12, 12, skin)))

    # --- 3. Biceps Brachii (Short Head) Activation & Upper Arm ---
    out.append(stroke_shape(i2, f"{prefix}BicepsShortHi", [(13.0, in_sign * 5.0), (ua_len - 9.0, in_sign * 5.0)], 2.2, HIGHLIGHT, 2.0))
    out.append(stroke_shape(i2, f"{prefix}BicepsSulcus", [(10.0, in_sign * 1.2), (ua_len - 6.0, in_sign * 1.8)], 1.2, "997C2D12", 0.5))
    out.append(smooth_shape(i2, f"{prefix}BicepsShortHeadActivation", biceps_short_pts, muscle_paint(prefix + "BicepsShort", 0.9, scale=0.82)))
    out.append(stroke_shape(i2, f"{prefix}UpperArmSh", [(8.0, -in_sign * 6.0), (ua_len - 8.0, -in_sign * 5.0)], 3.4, CORE_SHADOW, 3.0))
    out.append(smooth_shape(i2, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UpperArm", -11, 11, skin)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def shadow():
    ind = "        "
    return "\n".join([
        f'{ind}<Shape x="292" y="{f(FLOOR - 2)}" scaleX="1.38" scaleY="0.08" name="BenchAndAthleteShadow">\n'
        f'{ind}    <Ellipse width="220" height="220" name="ShadowEl"/>\n'
        f'{ind}    <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="110" endY="0" name="ShadowGrad">'
        f'<GradientStop colorValue="B3000000" position="0"/><GradientStop colorValue="59000000" position="0.6"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{ind}</Shape>",
    ])


def scenery():
    ind = "        "
    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"
    return (
        f'{ind}<Shape x="{W / 2}" y="{f(FLOOR + 1)}" name="FloorLine"><Rectangle width="{W - 40}" height="2" cornerRadiusTL="1" name="FloorRect"/>'
        f'<Fill name="FloorFill"><LinearGradient startX="{-(W - 40) / 2}" startY="0" endX="{(W - 40) / 2}" endY="0" name="FloorGrad">'
        f'<GradientStop colorValue="00475569" position="0"/><GradientStop colorValue="FF475569" position="0.2"/>'
        f'<GradientStop colorValue="FF475569" position="0.8"/><GradientStop colorValue="00475569" position="1"/></LinearGradient></Fill></Shape>\n'
        f'{ind}<Shape x="{W / 2}" y="{f((FLOOR + H) / 2 + 1)}" name="FloorBand"><Rectangle width="{W}" height="{f(band_h)}" name="FloorBandRect"/>'
        f"{band_fill}</Shape>\n"
        f'{ind}<Shape x="{W / 2}" y="{H / 2}" name="Backdrop"><Rectangle width="{W}" height="{H}" name="BackdropRect"/>'
        f'<Fill name="BackdropFill"><RadialGradient startX="0" startY="-40" endX="0" endY="{H * 0.75}" name="BackdropGrad">'
        f'<GradientStop colorValue="FF1E293B" position="0"/><GradientStop colorValue="FF0F172A" position="1"/></RadialGradient></Fill></Shape>'
    )


near_arm_xml = arm_rig("Near", True)
near_leg_xml = near_left_leg_rig()
front_arch_xml = front_bench_arch_rig()
torso_xml = reclined_torso_and_head_rig()
far_arm_xml = arm_rig("Far", False)
far_leg_xml = far_right_leg_rig()
bench_xml = incline_bench_rig()
shd_xml = shadow()

for cid, sc in muscle_fill_ids:
    key_color(cid, 37, lambda p, _s=sc: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, muscle_t(p, _s)))
for cid, sc in muscle_line_ids:
    key_color(cid, 37, lambda p, _s=sc: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, muscle_t(p, _s)))


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
    <!-- Incline Dumbbell Chest Fly: 60 fps, 16:9 (640x360), generated by gen_chest_fly.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="ChestFly" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- Foreground: Near (Left) Arm & 3D Cast-Iron Dumbbell -->
{near_arm_xml}

        <!-- Mid-Foreground: Near (Left) Leg Planted on FLOOR = 300.0 + Front Bench Stabilizer Arch -->
{near_leg_xml}
{front_arch_xml}

        <!-- Midground: Reclined Torso, Upper/Sternal Pectorals, 6-Pack Abs & 3/4 Head -->
{torso_xml}

        <!-- Mid-Background: Far (Right) Arm & 3D Cast-Iron Dumbbell + Far (Right) Leg -->
{far_arm_xml}
{far_leg_xml}

        <!-- Background Equipment: 3D Isometric Incline Weight Bench -->
{bench_xml}

        <!-- Floor Shadow & Scenery -->
{shd_xml}
{scenery()}

        <StateMachine name="ChestFlySM" id="0:7">
            <StateMachineLayer name="Motion" id="0:8">
                <AnyState x="200" y="-120"/>
                <ExitState x="400" y="-120"/>
                <EntryState>
                    <StateTransition stateToId="0:12"/>
                </EntryState>
                <AnimationState x="200" animationId="0:60" id="0:12"/>
            </StateMachineLayer>
        </StateMachine>

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="chest_fly" id="0:60">
{keyed_xml()}
        </LinearAnimation>
    </Artboard>
</Rive>
"""

OUT.write_text(rml)
print("keyed props:", len(keys), "bytes:", len(rml))


def _compile_rml_bytes(rml_path):
    """Direct Rive 7.3 binary compiler matching ~/.rive/bin/rive output."""
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
    out += varuint(23) + b"\x00"  # Backboard

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
    """Build the .riv, copy it into the Flutter assets and render the catalog thumbnail."""
    built = HERE / "build/chest_fly.riv"
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
