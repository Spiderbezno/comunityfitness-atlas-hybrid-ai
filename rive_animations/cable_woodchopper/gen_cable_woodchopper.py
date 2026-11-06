#!/usr/bin/env python3
"""Generates rive_animations/cable_woodchopper/scene.rml (and optionally publishes).

16:9 (640x360, FLOOR = 300.0) 60 fps procedural Rive animation for the
Cable Woodchopper (`id: cable_woodchopper`), matching the 4-panel reference chart:
  1. SET UP (c = 0.0): Wide athletic stance away from the hip-height cable pulley
     tower on the left; trunk and hips turned slightly left toward the tower;
     both arms extended long holding the D-handle at hip height.
  2. START THE TURN (c = 0.5): Hips and trunk rotate through the front-facing
     view toward the right; both arms sweep the handle horizontally across at
     hip level; back (left) heel begins to lift.
  3. CHOP ACROSS (c = 1.0): Full hip and trunk axial rotation to the right;
     arms pull the handle across past the right hip; back (left) foot pivots
     onto the ball of the foot with the heel lifted high and left knee driving
     inward-right.
  4. CONTROL BACK (c = 1.0 -> 0.0): Smooth controlled eccentric return along
     the same horizontal hip-height line as the weight stack lowers.

Activated muscles (`muscle_t`):
  - External & Internal Obliques (sculpted lateral abdominal wall on both flanks)
  - Rectus abdominis / Transversus abdominis core segments
  - Serratus anterior & Anterior/Lateral Deltoids

Usage (from this directory):
    python3 gen_cable_woodchopper.py            # regenerate scene.rml
    python3 gen_cable_woodchopper.py --publish  # + build .riv, copy to assets, render thumbnail
"""

import math
import pathlib
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "scene.rml"
REPO = HERE.parent.parent
ASSET_RIV = REPO / "assets/animations/cable_woodchopper.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/cable_woodchopper.png"
THUMB_ADVANCE = "0.60s"  # Mid-turn rotational power phase (Panel 2 / Panel 4)
THUMB_VIEWPORT = "1280x720"  # 2x the 640x360 artboard
THUMB_CROP = (660, 20, 310)  # square size, offsetY, offsetX in the 2x render
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

# 16:9 standard canvas
W, H = 640, 360
FLOOR = 300.0

# Cable pulley wheel exit coordinate at hip / waist height on the left tower
PULLEY_X, PULLEY_Y = 204.0, 168.0

# Anthropometric limb segment lengths
THIGH_L, SHIN_L = 60.0, 59.0
THIGH_R, SHIN_R = 60.0, 59.0
UPPER_ARM, FOREARM = 48.0, 44.0

# Timeline (frames @60fps): chop across 1.15s (69f), peak hold 0.25s (15f), control back 1.25s (75f), setup pause 0.35s (21f) = 180f (3.0s)
CHOP_FRAMES, HOLD_PEAK, RETURN_FRAMES, HOLD_START = 69, 15, 75, 21
DURATION = CHOP_FRAMES + HOLD_PEAK + RETURN_FRAMES + HOLD_START
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


EASE = cubic_bezier(0.42, 0.0, 0.35, 1.0)


def chop_progress(frame):
    """0.0 at Set Up (Panel 1), 0.5 at Start The Turn / Control Back (Panels 2 & 4), 1.0 at Chop Across (Panel 3)."""
    fr = frame % DURATION
    if fr <= CHOP_FRAMES:
        return EASE(fr / CHOP_FRAMES)
    fr -= CHOP_FRAMES
    if fr <= HOLD_PEAK:
        return 1.0
    fr -= HOLD_PEAK
    if fr <= RETURN_FRAMES:
        return 1.0 - EASE(fr / RETURN_FRAMES)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def quad_interp(v0, v_mid, v1, c):
    """Smooth quadratic interpolation passing exactly through v0 at c=0, v_mid at c=0.5, and v1 at c=1."""
    return v0 * (1.0 - c) * (1.0 - 2.0 * c) + 4.0 * v_mid * c * (1.0 - c) + v1 * c * (2.0 * c - 1.0)


def quad_pt(p0, pm, p1, c):
    return (quad_interp(p0[0], pm[0], p1[0], c), quad_interp(p0[1], pm[1], p1[1], c))


def solve_ik(root, target, l1, l2, bend_sign):
    """2D two-bone IK from root -> mid -> target."""
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = math.hypot(dx, dy)
    d_clamped = min(max(d, abs(l1 - l2) + 0.5), l1 + l2 - 0.15)
    base_ang = math.atan2(dy, dx)
    cos_a = max(-1.0, min(1.0, (l1 * l1 + d_clamped * d_clamped - l2 * l2) / (2.0 * l1 * d_clamped)))
    ang1 = base_ang + bend_sign * math.acos(cos_a)
    mid = (root[0] + l1 * math.cos(ang1), root[1] + l1 * math.sin(ang1))
    ang2 = math.atan2(target[1] - mid[1], target[0] - mid[0])
    return ang1, ang2, mid


def solve_long_arm(sh, target, alpha_deg):
    """3D-foreshortened long-arm solver keeping a natural ~12-16 deg anatomical elbow bend without chicken-winging."""
    dx, dy = target[0] - sh[0], target[1] - sh[1]
    d = math.hypot(dx, dy)
    base_ang = math.atan2(dy, dx)
    alpha = math.radians(alpha_deg)
    sin_beta = max(-0.95, min(0.95, (UPPER_ARM / FOREARM) * math.sin(alpha)))
    beta = math.asin(sin_beta)
    unscaled_reach = UPPER_ARM * math.cos(alpha) + FOREARM * math.cos(beta)
    arm_sx = d / unscaled_reach
    ua_world = base_ang + alpha
    fa_world = base_ang - beta
    fa_local = fa_world - ua_world
    elbow = (
        sh[0] + arm_sx * UPPER_ARM * math.cos(ua_world),
        sh[1] + arm_sx * UPPER_ARM * math.sin(ua_world),
    )
    return ua_world, fa_local, arm_sx, elbow


def pose(c):
    """Compute full 3D-projected Cable Woodchopper pose at chop progress c in [0, 1]."""
    # 1. Pelvis & Torso Root:
    # Subtle horizontal weight shift into the front-right hip as the athlete rotates across
    torso_x = quad_interp(394.0, 398.0, 400.0, c)
    torso_y = quad_interp(175.0, 174.0, 176.0, c)
    spine = math.radians(quad_interp(-92.0, -90.0, -88.0, c))

    # 3D axial rotation tracks for internal torso & head groups:
    # Anterior chest/abs/sternum shifts across the torso from left (-4.5) through front (+3.5) to right profile (+11.5)
    core_dx = quad_interp(-4.5, 3.5, 11.5, c)
    core_sx = quad_interp(0.95, 1.00, 0.58, c)
    # Right-side oblique fan rotates from far-right edge into full side-right view at c=1.0 (Panel 3)
    oblique_r_dx = quad_interp(9.0, 6.5, 2.5, c)
    oblique_r_sx = quad_interp(0.45, 0.82, 1.05, c)
    # Dorsal upper/mid back contour rotates into view on the left side of the torso at c=1.0 (Panel 3)
    back_dx = quad_interp(-11.5, -9.5, -3.5, c)
    back_sx = quad_interp(0.18, 0.45, 1.00, c)
    # Head facial features (nose/brow/chin) & ear shift horizontally as the head turns from 3/4 left to right profile
    face_dx = quad_interp(-3.2, 3.5, 7.2, c)
    ear_dx = quad_interp(5.5, -2.5, -4.5, c)

    # 2. Right (Front / Screen-Right) Support Leg:
    hip_r = quad_pt((408.0, 176.0), (412.0, 176.0), (404.0, 177.0), c)
    ankle_r = quad_pt((432.0, 289.5), (432.0, 289.5), (428.0, 289.5), c)
    thigh_r, shin_r_world, knee_r = solve_ik(hip_r, ankle_r, THIGH_R, SHIN_R, bend_sign=-1.0)
    shin_r_local = shin_r_world - thigh_r
    foot_r_world = math.radians(quad_interp(2.0, 1.0, 0.0, c))
    foot_r_local = foot_r_world - shin_r_world

    # 3. Left (Tower-Side / Screen-Left) Pivot Leg:
    # At c=0.0, foot is planted flat on FLOOR=300.0; as c -> 1.0, left hip rotates right, left knee drives inward-right,
    # and the left heel lifts high off the floor while the ball/toes pivot on FLOOR = 300.0 (matching Panel 3!)
    hip_l = quad_pt((380.0, 176.0), (384.0, 176.0), (394.0, 177.0), c)
    ankle_l = quad_pt((348.0, 289.5), (344.0, 286.0), (338.0, 278.2), c)
    # Knee bends slightly inward-right (bend_sign = -1.0) as the hip & heel pivot
    thigh_l, shin_l_world, knee_l = solve_ik(hip_l, ankle_l, THIGH_L, SHIN_L, bend_sign=-1.0)
    shin_l_local = shin_l_world - thigh_l
    # Foot world angle tilts downward from 0 deg (flat at c=0) to 32 deg (heel raised high, toes on FLOOR=300 at c=1)
    foot_l_world = math.radians(quad_interp(0.0, 12.0, 32.0, c))
    foot_l_local = foot_l_world - shin_l_world

    # 4. Shoulders & Dual-Arm Long-Arm Woodchop Kinematics (3D foreshortened, no chicken-wing):
    # Right shoulder (foreground) and Left shoulder (background/far-side as torso turns right)
    sh_r = quad_pt((410.0, 103.0), (414.0, 103.0), (404.0, 102.0), c)
    sh_l = quad_pt((376.0, 104.0), (384.0, 103.0), (410.0, 101.0), c)

    # Dead-level horizontal chop path at hip/waist height (y = 168.0) matching PULLEY_Y = 168.0:
    # At c=0.0 (Panel 1, Set Up): wrist = (298, 168)
    # At c=0.5 (Panel 2, Start The Turn): wrist = (434, 168)
    # At c=1.0 (Panel 3, Chop Across): wrist = (468, 168)
    wrist = (quad_interp(298.0, 434.0, 468.0, c), 168.0)

    # Both arms remain long and taut with a natural ~12-14 deg anatomical elbow bend:
    alpha_r = quad_interp(-6.5, 7.5, -5.5, c)
    alpha_l = quad_interp(-7.5, 7.5, -5.5, c)
    ua_r_world, fa_r_local, arm_r_sx, elbow_r = solve_long_arm(sh_r, wrist, alpha_r)
    ua_l_world, fa_l_local, arm_l_sx, elbow_l = solve_long_arm(sh_l, wrist, alpha_l)

    # D-Handle & Taut Horizontal Cable from Pulley (204, 168) to Handle Swivel (wrist_x - 16, 168)
    swivel_x = wrist[0] - 16.0
    swivel_y = wrist[1]
    cdx = swivel_x - PULLEY_X
    cdy = swivel_y - PULLEY_Y
    cable_len = math.hypot(cdx, cdy)
    cable_ang = math.atan2(cdy, cdx)

    # Moving weight stack on the cable tower rises by 42 px as the cable is pulled out
    weight_stack_y = lerp(228.0, 186.0, c)

    return {
        "c": c,
        "torso_x": torso_x,
        "torso_y": torso_y,
        "spine": spine,
        "core_dx": core_dx,
        "core_sx": core_sx,
        "oblique_r_dx": oblique_r_dx,
        "oblique_r_sx": oblique_r_sx,
        "back_dx": back_dx,
        "back_sx": back_sx,
        "face_dx": face_dx,
        "ear_dx": ear_dx,
        "hip_r": hip_r,
        "knee_r": knee_r,
        "ankle_r": ankle_r,
        "thigh_r": thigh_r,
        "shin_r_local": shin_r_local,
        "foot_r_local": foot_r_local,
        "hip_l": hip_l,
        "knee_l": knee_l,
        "ankle_l": ankle_l,
        "thigh_l": thigh_l,
        "shin_l_local": shin_l_local,
        "foot_l_local": foot_l_local,
        "sh_r": sh_r,
        "sh_l": sh_l,
        "elbow_r": elbow_r,
        "elbow_l": elbow_l,
        "wrist": wrist,
        "ua_r_world": ua_r_world,
        "fa_r_local": fa_r_local,
        "arm_r_sx": arm_r_sx,
        "ua_l_world": ua_l_world,
        "fa_l_local": fa_l_local,
        "arm_l_sx": arm_l_sx,
        "cable_len": cable_len,
        "cable_ang": cable_ang,
        "weight_stack_y": weight_stack_y,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(chop_progress(fr)) for fr in FRAMES}

# Unwrap all angular tracks across consecutive frames and verify periodic closure
_ANGLE_KEYS = (
    "spine",
    "thigh_r", "shin_r_local", "foot_r_local",
    "thigh_l", "shin_l_local", "foot_l_local",
    "ua_r_world", "fa_r_local",
    "ua_l_world", "fa_l_local",
    "cable_ang",
)
for k in _ANGLE_KEYS:
    prev = POSES[FRAMES[0]][k]
    for fr in FRAMES[1:]:
        cur = POSES[fr][k]
        while cur - prev > math.pi:
            cur -= 2.0 * math.pi
        while cur - prev < -math.pi:
            cur += 2.0 * math.pi
        POSES[fr][k] = cur
        prev = cur

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


def poly_shape(indent, name, pts, paint, radius=0, closed=True):
    v = "\n".join(
        f'{indent}        <StraightVertex x="{f(float(x))}" y="{f(float(y))}"'
        + (f' radius="{f(float(radius))}"' if radius else "")
        + "/>"
        for x, y in pts
    )
    cl = "true" if closed else "false"
    return (
        f'{indent}<Shape name="{name}">\n'
        f'{indent}    <PointsPath isClosed="{cl}" name="{name}Path">\n{v}\n{indent}    </PointsPath>\n'
        f"{indent}    {paint}\n"
        f"{indent}</Shape>"
    )


def stroke_shape(indent, name, pts, thickness, color, feather=0, cap="round"):
    fe = f'<Feather strength="{f(feather)}" name="{name}Feather"/>' if feather else ""
    paint = f'<Stroke thickness="{f(thickness)}" cap="{cap}" join="round" name="{name}Stroke">{fe}<SolidColor colorValue="{color}" name="{name}Color"/></Stroke>'
    return smooth_shape(indent, name, pts, paint, closed=False)


def ellipse_shape(indent, name, x, y, w, h, paint, rot_deg=0.0):
    rot_attr = f' rotation="{f(math.radians(rot_deg))}"' if rot_deg else ""
    return (
        f'{indent}<Shape x="{f(x)}" y="{f(y)}"{rot_attr} name="{name}">\n'
        f'{indent}    <Ellipse width="{f(w)}" height="{f(h)}" name="{name}El"/>\n'
        f"{indent}    {paint}\n"
        f"{indent}</Shape>"
    )


# ---------------------------------------------------------------- Palette
SKIN = ("FFD8E0EC", "FFA3B1C4", "FF637286")
SKIN_FAR = ("FFB4C1D4", "FF8291A6", "FF515E72")
SHORTS = ("FF1C2739", "FF162030", "FF121A28")
SHORTS_FAR = ("FF182232", "FF141C2B", "FF101724")
HIGHLIGHT = "40FFFFFF"
CORE_SHADOW = "4D0F172A"
SOFT_SHADOW = "2E0F172A"

# Dynamic warm orange -> deep crimson muscle activation matching the reference chart
MUSCLE_LOW = "CCF97316"
MUSCLE_HIGH = "F2EF4444"
MUSCLE_LINE_LOW = "8C7C2D12"
MUSCLE_LINE_HIGH = "CC991B1B"


def argb_lerp(c0, c1, t):
    a0, r0, g0, b0 = (int(c0[i : i + 2], 16) for i in (0, 2, 4, 6))
    a1, r1, g1, b1 = (int(c1[i : i + 2], 16) for i in (0, 2, 4, 6))
    return "".join(f"{round(lerp(v0, v1, t)):02X}" for v0, v1 in ((a0, a1), (r0, r1), (g0, g1), (b0, b1)))


keys = []


def key_double(obj, prop, fn):
    keys.append((obj, prop, "double", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def key_color(obj, prop, fn):
    keys.append((obj, prop, "color", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def muscle_t(p):
    # Clearly visible warm orange oblique activation at Set Up (0.35), peaking at 1.0 crimson at Chop Across
    return 0.35 + 0.65 * (p["c"] ** 0.85)


muscle_fill_ids, muscle_line_ids = [], []


def muscle_paint(name, line=0.95):
    fid, lid = nid(), nid()
    muscle_fill_ids.append(fid)
    muscle_line_ids.append(lid)
    t0 = muscle_t(POSES[0])
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{line}" join="round" name="{name}Edge"><SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- Anatomy & Equipment Builders
def cable_and_handle_rig():
    """Taut horizontal steel cable from pulley (204, 168) + D-Handle (stirrup grip) & clasped hands at wrist."""
    ind = "        "
    i2 = ind + "    "
    cable_id, handle_id = nid(), nid()
    key_double(cable_id, 15, lambda p: p["cable_ang"])
    key_double(cable_id, 16, lambda p: p["cable_len"])
    key_double(handle_id, 13, lambda p: p["wrist"][0])
    key_double(handle_id, 14, lambda p: p["wrist"][1])
    p0 = POSES[0]

    # Clasped fingers & thumb wrapping around the vertical grip cylinder of the D-handle
    fingers_pts = [
        (-3.5, -6.5), (4.5, -6.2), (5.5, 0.0), (4.5, 6.2), (-3.5, 6.5),
    ]
    thumb_pts = [
        (-5.5, -4.5), (-1.0, -7.8), (3.5, -6.8), (2.5, -3.5), (-3.5, -2.5),
    ]

    return "\n".join([
        # 1. D-Handle (Stirrup Grip) + Clasped Fingers at wrist
        f'{ind}<Node x="{f(p0["wrist"][0])}" y="{f(p0["wrist"][1])}" name="DHandleAndGrip" id="{handle_id}">',
        smooth_shape(i2, "GripThumb", thumb_pts, skin_fill("GripThumb", -8, -2, SKIN)),
        stroke_shape(i2, "KnuckleCrease1", [(1.5, -4.0), (2.2, 0.0), (1.5, 4.0)], 1.0, SOFT_SHADOW, 0.5),
        smooth_shape(i2, "GripFingers", fingers_pts, skin_fill("GripFingers", -7, 7, SKIN)),
        # Cylindrical black rubber grip sleeve
        poly_shape(i2, "DHandleGripBar", [(-1.5, -8.5), (2.5, -8.5), (2.5, 8.5), (-1.5, 8.5)], solid("GripRubber", "FF0F172A"), radius=1.5),
        # D-Handle Stirrup V-straps (upper and lower webbing/steel arms meeting at the swivel eyelet at x=-16)
        stroke_shape(i2, "DHandleStrapTop", [(-16.0, 0.0), (-5.5, -8.2), (1.0, -8.0)], 2.6, "FF1E293B", 0.0, cap="round"),
        stroke_shape(i2, "DHandleStrapBot", [(-16.0, 0.0), (-5.5, 8.2), (1.0, 8.0)], 2.6, "FF0F172A", 0.0, cap="round"),
        stroke_shape(i2, "DHandleStrapHi", [(-15.0, -0.5), (-5.5, -7.8), (0.5, -7.6)], 0.9, "FF64748B", 0.0, cap="round"),
        # Chrome swivel eyelet & carabiner at (-16, 0)
        ellipse_shape(i2, "CarabinerRing", -16.0, 0.0, 6.5, 5.0, f'<Fill name="CarabinerFill">{grad("CarabinerGrad", -3, -3, 3, 3, "FFF8FAFC", "FF64748B")}</Fill>'),
        f"{ind}</Node>",

        # 2. Taut Horizontal Steel Cable stretching from PULLEY (204, 168) to D-Handle Swivel
        f'{ind}<Node x="{f(PULLEY_X)}" y="{f(PULLEY_Y)}" rotation="{f(p0["cable_ang"])}" scaleX="{f(p0["cable_len"])}" name="CableWireNode" id="{cable_id}">',
        f'{i2}<Shape x="0.5" y="-0.4" name="CableHighlight"><Rectangle width="1" height="0.8" name="CableHiRect"/><Fill name="CableHiFill"><SolidColor colorValue="FFE2E8F0" name="CableHiCol"/></Fill></Shape>',
        f'{i2}<Shape x="0.5" y="0" name="CableCore"><Rectangle width="1" height="2.0" name="CableRect"/><Fill name="CableFill"><SolidColor colorValue="FF475569" name="CableCol"/></Fill></Shape>',
        f"{ind}</Node>",
    ])


def arm_rig(prefix, is_right):
    """Shoulder -> UpperArm -> Forearm -> Hand with 3D axial foreshortening so arms stay long without chicken-winging."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN if is_right else SKIN_FAR
    sh_id, ua_mesh_id, fa_id = nid(), nid(), nid()
    sh_key = "sh_r" if is_right else "sh_l"
    ua_key = "ua_r_world" if is_right else "ua_l_world"
    fa_key = "fa_r_local" if is_right else "fa_l_local"
    sx_key = "arm_r_sx" if is_right else "arm_l_sx"

    key_double(sh_id, 13, lambda p: p[sh_key][0])
    key_double(sh_id, 14, lambda p: p[sh_key][1])
    key_double(sh_id, 15, lambda p: p[ua_key])
    key_double(ua_mesh_id, 16, lambda p: p[sx_key])
    key_double(fa_id, 13, lambda p: p[sx_key] * UPPER_ARM)
    key_double(fa_id, 15, lambda p: p[fa_key])
    key_double(fa_id, 16, lambda p: p[sx_key])
    p0 = POSES[0]

    ua_pts = [
        (-10, 0), (-8, -9.0), (5, -10.5), (20, -10.0), (35, -8.2), (44, -6.0),
        (50, 0), (44, 6.0), (30, 8.8), (15, 9.8), (2, 9.2), (-8, 7.2),
    ]
    delt_pts = [
        (-13, 0), (-9, -10.5), (2, -12.0), (14, -9.5), (19, -1.5),
        (16, 6.8), (5, 9.8), (-8, 8.2),
    ]
    fa_pts = [
        (-6, 0), (-5, -6.8), (6, -8.2), (20, -7.0), (33, -5.0), (41, -4.0),
        (45, 0), (41, 4.0), (30, 5.5), (16, 7.2), (4, 7.5), (-5, 6.0),
    ]
    wrist_hand_pts = [
        (39, -4.5), (46, -5.2), (49, 0.0), (46, 5.2), (39, 4.5),
    ]

    out = [f'{ind}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" rotation="{f(p0[ua_key])}" name="{prefix}UpperArm" id="{sh_id}">']
    out.append(f'{i2}<Node x="{f(p0[sx_key] * UPPER_ARM)}" rotation="{f(p0[fa_key])}" scaleX="{f(p0[sx_key])}" name="{prefix}Forearm" id="{fa_id}">')
    out.append(smooth_shape(i3, f"{prefix}WristHand", wrist_hand_pts, skin_fill(prefix + "WristHand", -5, 5, skin)))
    if is_right:
        out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(6, -4.2), (18, -3.8), (32, -2.5)], 2.6, HIGHLIGHT, 3.0))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(6, 4.5), (18, 4.2), (32, 2.8)], 3.6, CORE_SHADOW, 4.0))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -8, 8, skin)))
    out.append(f"{i2}</Node>")

    if is_right:
        out.append(stroke_shape(i2, f"{prefix}DeltHi", [(-4, -6.5), (4, -8.0), (12, -5.0)], 2.8, HIGHLIGHT, 3.0))
        out.append(stroke_shape(i2, f"{prefix}DeltGroove", [(2, -9.0), (11, -6.2), (17, -1.2)], 1.2, SOFT_SHADOW, 1.0))
    out.append(smooth_shape(i2, f"{prefix}Deltoid", delt_pts, skin_fill(prefix + "Deltoid", -12, 10, skin)))
    out.append(f'{i2}<Node scaleX="{f(p0[sx_key])}" name="{prefix}UpperArmMesh" id="{ua_mesh_id}">')
    if is_right:
        out.append(stroke_shape(i3, f"{prefix}UpperArmHi", [(8, -6.2), (22, -6.0), (36, -4.5)], 2.8, HIGHLIGHT, 3.0))
        out.append(stroke_shape(i3, f"{prefix}BicepsLine", [(12, -1.5), (26, -2.0), (38, -1.2)], 1.2, SOFT_SHADOW, 1.0))
    out.append(stroke_shape(i3, f"{prefix}UpperArmSh", [(8, 6.0), (22, 6.5), (36, 4.8)], 4.0, CORE_SHADOW, 4.0))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UpperArm", -10, 10, skin)))
    out.append(f"{i2}</Node>")
    out.append(f"{ind}</Node>")
    return "\n".join(out)


def torso_and_head_rig():
    """Upright 3D axially rotating Torso (with glowing External/Internal Obliques, 6-Pack Abs, Pectorals, and Dorsal Back) + Volumetric Head."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "
    root_id, core_id, ob_r_id, back_id, face_id, ear_id = nid(), nid(), nid(), nid(), nid(), nid()
    key_double(root_id, 13, lambda p: p["torso_x"])
    key_double(root_id, 14, lambda p: p["torso_y"])
    key_double(core_id, 13, lambda p: p["core_dx"])
    key_double(core_id, 16, lambda p: p["core_sx"])
    key_double(ob_r_id, 13, lambda p: p["oblique_r_dx"])
    key_double(ob_r_id, 16, lambda p: p["oblique_r_sx"])
    key_double(back_id, 13, lambda p: p["back_dx"])
    key_double(back_id, 16, lambda p: p["back_sx"])
    key_double(face_id, 13, lambda p: p["face_dx"])
    key_double(ear_id, 13, lambda p: p["ear_dx"])
    p0 = POSES[0]

    # TorsoNode local space: origin (0,0) is at mid-pelvis (394, 175); -y is UP toward shoulders (-68) and head (-108).
    torso_pts = [
        (-15.5, -5.0), # left hip / waistband (tucked inside PelvisShorts so no skin rim peeks below)
        (-16, -18),    # left waist (oblique indentation)
        (-19, -38),    # left lower ribcage / lat flare
        (-22, -58),    # left upper lat / axilla
        (-16, -70),    # left clavicle / acromion
        (0, -72),      # suprasternal notch / base of neck
        (16, -70),     # right clavicle / acromion
        (22, -58),     # right upper lat / chest contour
        (19, -38),     # right lower ribcage
        (16, -18),     # right waist (oblique indentation)
        (15.5, -5.0),  # right hip / waistband
        (0, -4.0),     # lower abdomen tucked inside PelvisShorts
    ]
    pelvis_shorts_pts = [
        (-17.0, -8.2), (0.0, -7.8), (17.0, -8.2),
        (19.5, 4.5), (0.0, 9.5), (-19.5, 4.5),
    ]

    # Sculpted Left/Tower-Side External & Internal Oblique Fan (inside AnteriorCoreGroup so it rotates across from left flank to center-right!)
    oblique_left_pts = [
        (-15.5, -42.0), (-7.0, -39.0), (-5.5, -24.0), (-7.0, -9.0),
        (-15.0, -8.5), (-16.5, -24.0),
    ]
    # Sculpted Right-Side External & Internal Oblique Fan (inside RightObliqueGroup so at c=1.0 Panel 3 it forms the prominent right-side oblique wall!)
    oblique_right_pts = [
        (4.5, -42.0), (14.5, -39.0), (15.5, -23.0), (14.5, -8.5),
        (5.0, -9.0), (3.5, -24.0),
    ]

    # Sculpted Pectorals & 6-Pack Rectus Abdominis (inside AnteriorCoreGroup)
    pec_l_pts = [(-18, -66), (-1, -65), (-1, -46), (-12, -45), (-19, -53)]
    pec_r_pts = [(1, -65), (18, -66), (19, -53), (12, -45), (1, -46)]
    pec_paint = (
        '<Fill name="PecFill"><SolidColor colorValue="1A0F172A" name="PecCol"/></Fill>'
        '<Stroke thickness="0.95" join="round" name="PecStroke"><SolidColor colorValue="400F172A" name="PecStrokeCol"/></Stroke>'
    )
    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1C0F172A" name="AbsCol"/></Fill>'
        '<Stroke thickness="0.85" join="round" name="AbsStroke"><SolidColor colorValue="420F172A" name="AbsStrokeCol"/></Stroke>'
    )
    abs_blocks = [
        [(-7.5, -43), (-1.0, -43), (-1.0, -34), (-7.5, -34)],
        [(1.0, -43), (7.5, -43), (7.5, -34), (1.0, -34)],
        [(-7.2, -32.5), (-1.0, -32.5), (-1.0, -24), (-7.2, -24)],
        [(1.0, -32.5), (7.2, -32.5), (7.2, -24), (1.0, -24)],
        [(-6.8, -22.5), (-1.0, -22.5), (-1.0, -13), (-6.8, -13)],
        [(1.0, -22.5), (6.8, -22.5), (6.8, -13), (1.0, -13)],
    ]

    # Dorsal Upper/Mid Back Scapula & Latissimus Wing (inside DorsalBackGroup, rotating into view on the left at c=1.0 Panel 3)
    back_wing_pts = [
        (-12, -66), (4, -64), (6, -40), (-4, -18), (-13, -36),
    ]
    back_paint = (
        '<Fill name="BackWingFill"><SolidColor colorValue="1F0F172A" name="BackWingCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="BackWingStroke"><SolidColor colorValue="470F172A" name="BackWingStrokeCol"/></Stroke>'
    )

    # Head & Neck (centered above suprasternal notch at y = -72..-112)
    neck_pts = [
        (-7.5, -84.0), (7.5, -84.0), (9.5, -68.0), (-9.5, -68.0),
    ]
    head_dome_pts = [
        (-11.0, -106.0), (0.0, -112.0), (11.0, -106.0),
        (12.2, -94.0), (9.5, -82.0), (0.0, -78.5),
        (-9.5, -82.0), (-12.2, -94.0),
    ]
    hair_pts = [
        (-11.2, -102.0), (-6.0, -112.2), (6.0, -112.2), (11.2, -102.0),
        (8.5, -97.0), (0.0, -100.0), (-8.5, -97.0),
    ]

    out = [f'{ind}<Node x="{f(p0["torso_x"])}" y="{f(p0["torso_y"])}" name="TorsoAndHeadRoot" id="{root_id}">']

    # 1. Head & Neck (drawn above upper chest)
    out.append(f'{i2}<Node name="HeadGroup">')
    out.append(smooth_shape(i3, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 0, -112, 0, -96, "FF475569", "FF1E293B")}</Fill>'))
    # Rotating facial features (brow, nose bridge, chin/jawline)
    out.append(f'{i3}<Node x="{f(p0["face_dx"])}" y="0" name="FacialFeatures" id="{face_id}">')
    out.append(stroke_shape(i4, "BrowLine", [(-4.5, -96.5), (0.0, -96.0), (4.5, -96.5)], 1.3, "590F172A", 0.5))
    out.append(stroke_shape(i4, "NoseBridge", [(0.5, -96.0), (1.8, -89.5), (0.0, -88.5)], 1.2, "660F172A", 0.4))
    out.append(stroke_shape(i4, "MouthLine", [(-2.0, -84.8), (2.2, -84.8)], 1.0, "590F172A", 0.4))
    out.append(f"{i3}</Node>")
    out.append(f'{i3}<Node x="{f(p0["ear_dx"])}" y="0" name="EarNode" id="{ear_id}">')
    out.append(ellipse_shape(i4, "Ear", 0.0, -93.0, 4.2, 7.2, solid("Ear", "FFA3B1C4")))
    out.append(f"{i3}</Node>")
    out.append(stroke_shape(i3, "HeadHi", [(-5.0, -106.0), (0.0, -108.5), (5.0, -106.0)], 2.8, HIGHLIGHT, 3.0))
    out.append(stroke_shape(i3, "JawShadow", [(-7.5, -81.0), (0.0, -78.2), (7.5, -81.0)], 2.4, CORE_SHADOW, 2.0))
    out.append(smooth_shape(i3, "HeadDome", head_dome_pts, skin_fill("HeadDome", -112, -78, SKIN, x0=-10, x1=10)))
    out.append(stroke_shape(i3, "SCMLeft", [(-5.5, -81.0), (-2.0, -70.0)], 1.3, SOFT_SHADOW, 1.0))
    out.append(stroke_shape(i3, "SCMRight", [(5.5, -81.0), (2.0, -70.0)], 1.3, SOFT_SHADOW, 1.0))
    out.append(smooth_shape(i3, "NeckShape", neck_pts, skin_fill("Neck", -84, -68, SKIN)))
    out.append(f"{i2}</Node>")

    # 2. Seamless Pelvis Compression Shorts (matching lower torso contour and ThighShorts shading)
    out.append(stroke_shape(i2, "WaistbandLine", [(-16.0, -7.8), (0.0, -7.3), (16.0, -7.8)], 1.1, "590F172A", 0.4))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts_pts, skin_fill("PelvisShorts", 0, 0, SHORTS, x0=18, x1=-18)))

    # 3. Right-Side Oblique Wall (rotates into full prominence on the right flank as c -> 1.0)
    out.append(f'{i2}<Node x="{f(p0["oblique_r_dx"])}" y="0" scaleX="{f(p0["oblique_r_sx"])}" name="RightObliqueGroup" id="{ob_r_id}">')
    out.append(stroke_shape(i3, "ObliqueRSlip1", [(6.0, -35.0), (11.5, -31.0), (14.5, -26.0)], 1.1, "807C2D12", 0.4))
    out.append(stroke_shape(i3, "ObliqueRSlip2", [(5.5, -27.0), (11.5, -23.0), (14.5, -18.0)], 1.1, "807C2D12", 0.4))
    out.append(stroke_shape(i3, "ObliqueRSlip3", [(5.5, -19.0), (11.0, -15.0), (14.0, -11.0)], 1.1, "807C2D12", 0.4))
    out.append(smooth_shape(i3, "RightObliqueActivation", oblique_right_pts, muscle_paint("RightOblique", 0.95)))
    out.append(f"{i2}</Node>")

    # 4. Anterior Core Group (Pectorals, 6-Pack Abs, and Left/Tower-Side Oblique Wall translating across torso)
    out.append(f'{i2}<Node x="{f(p0["core_dx"])}" y="0" scaleX="{f(p0["core_sx"])}" name="AnteriorCoreGroup" id="{core_id}">')
    out.append(stroke_shape(i3, "ObliqueLSlip1", [(-14.5, -34.0), (-10.5, -30.0), (-6.5, -26.0)], 1.1, "807C2D12", 0.4))
    out.append(stroke_shape(i3, "ObliqueLSlip2", [(-15.0, -26.0), (-10.5, -22.0), (-6.5, -18.0)], 1.1, "807C2D12", 0.4))
    out.append(stroke_shape(i3, "ObliqueLSlip3", [(-14.5, -18.0), (-10.0, -14.0), (-6.5, -11.0)], 1.1, "807C2D12", 0.4))
    out.append(smooth_shape(i3, "LeftObliqueActivation", oblique_left_pts, muscle_paint("LeftOblique", 0.95)))
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i3, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i3, "LineaAlba", [(0.0, -45.0), (0.0, -12.0)], 1.2, "4D0F172A", 0.6))
    out.append(smooth_shape(i3, "PecLeft", pec_l_pts, pec_paint))
    out.append(smooth_shape(i3, "PecRight", pec_r_pts, pec_paint))
    out.append(f"{i2}</Node>")

    # 5. Dorsal Back / Scapula / Erector Spinae Contour (rotates into view on the left side at c = 1.0 Panel 3)
    out.append(f'{i2}<Node x="{f(p0["back_dx"])}" y="0" scaleX="{f(p0["back_sx"])}" name="DorsalBackGroup" id="{back_id}">')
    out.append(stroke_shape(i3, "SpinalGroove", [(-2.0, -64.0), (-1.5, -38.0), (-1.0, -14.0)], 1.4, "590F172A", 0.8))
    out.append(smooth_shape(i3, "BackWing", back_wing_pts, back_paint))
    out.append(f"{i2}</Node>")

    # 6. Base Volumetric Torso Silhouette
    out.append(stroke_shape(i2, "TorsoHi", [(-4.0, -60.0), (0.0, -35.0), (2.0, -15.0)], 4.5, HIGHLIGHT, 4.5))
    out.append(stroke_shape(i2, "TorsoShL", [(-16.0, -54.0), (-14.0, -30.0), (-14.0, -12.0)], 4.2, CORE_SHADOW, 4.0))
    out.append(stroke_shape(i2, "TorsoShR", [(16.0, -54.0), (14.0, -30.0), (14.0, -12.0)], 4.2, CORE_SHADOW, 4.0))
    out.append(smooth_shape(i2, "TorsoShape", torso_pts, skin_fill("Torso", -72, 8, SKIN, x0=-18, x1=18)))
    out.append(f"{ind}</Node>")
    return "\n".join(out)


def leg_rig(prefix, is_right):
    """Hip -> Thigh -> Shin -> Foot with sculpted Quadriceps, Patella, Gastrocnemius/Soleus, and Compression Shorts."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "
    i5 = i4 + "    "
    skin = SKIN if is_right else SKIN_FAR
    shorts = SHORTS if is_right else SHORTS_FAR
    thigh_len = THIGH_R if is_right else THIGH_L
    shin_len = SHIN_R if is_right else SHIN_L
    hip_key = "hip_r" if is_right else "hip_l"
    thigh_key = "thigh_r" if is_right else "thigh_l"
    shin_key = "shin_r_local" if is_right else "shin_l_local"
    foot_key = "foot_r_local" if is_right else "foot_l_local"

    hip_id, thigh_id, shin_id, foot_id = nid(), nid(), nid(), nid()
    key_double(hip_id, 13, lambda p: p[hip_key][0])
    key_double(hip_id, 14, lambda p: p[hip_key][1])
    key_double(thigh_id, 15, lambda p: p[thigh_key])
    key_double(shin_id, 15, lambda p: p[shin_key])
    key_double(foot_id, 15, lambda p: p[foot_key])
    p0 = POSES[0]

    # In Thigh local space (+x down from Hip(0) -> Knee(60), angle ~ +75..+105 deg):
    # -y is SCREEN-RIGHT (anterior/lateral contour), +y is SCREEN-LEFT (medial/posterior contour)
    thigh_pts = [
        (-14, 0), (-11, -11.5), (6, -14.2), (28, -13.8), (48, -10.8), (56, -7.8),
        (62, 0), (56, 7.8), (44, 10.2), (24, 12.8), (5, 13.8), (-11, 11.2),
    ]
    shorts_pts = [
        (-15, 0), (-12, -12.5), (5, -15.0), (22, -14.5),
        (22, 13.5), (5, 14.5), (-12, 12.0),
    ]
    shin_pts = [
        (-8, 0), (-6, -6.2), (14, -6.0), (36, -5.2), (52, -4.0), (58, -3.5),
        (61, 0), (57, 4.0), (44, 5.8), (28, 10.8), (14, 12.5), (4, 10.5), (-6, 6.8),
    ]
    # Foot local space (origin at ankle (0,0), FLOOR = 300 is at y = +10.5 when flat)
    foot_pts = [
        (-8, -1.5), (3, -2.8), (15, 2.0), (24, 5.5), (26, 9.5),
        (14, 10.6), (-6, 10.5), (-10, 5.5),
    ]

    out = [f'{ind}<Node x="{f(p0[hip_key][0])}" y="{f(p0[hip_key][1])}" name="{prefix}LegHip" id="{hip_id}">']
    out.append(f'{i2}<Node rotation="{f(p0[thigh_key])}" name="{prefix}Thigh" id="{thigh_id}">')

    # 1. Shin + Foot + KneeCap
    out.append(f'{i3}<Node x="{f(thigh_len)}" rotation="{f(p0[shin_key])}" name="{prefix}Shin" id="{shin_id}">')
    out.append(f'{i4}<Node x="{f(shin_len)}" rotation="{f(p0[foot_key])}" name="{prefix}Foot" id="{foot_id}">')
    out.append(stroke_shape(i5, f"{prefix}FootHi", [(-2, 0.5), (9, 3.0), (20, 6.0)], 2.0, HIGHLIGHT, 2.0))
    out.append(smooth_shape(i5, f"{prefix}FootShape", foot_pts, skin_fill(prefix + "Foot", -3, 11, skin)))
    out.append(f"{i4}</Node>")

    out.append(ellipse_shape(i4, f"{prefix}KneeCap", 0, -0.5, 16, 15, skin_fill(prefix + "Knee", -8, 8, skin)))
    out.append(stroke_shape(i4, f"{prefix}CalfLine", [(8, 8.5), (20, 9.5), (34, 5.2)], 1.3, SOFT_SHADOW, 1.0))
    out.append(stroke_shape(i4, f"{prefix}ShinHi", [(10, -4.0), (30, -3.5), (48, -2.5)], 2.8, HIGHLIGHT, 3.0))
    out.append(stroke_shape(i4, f"{prefix}ShinSh", [(10, 8.5), (24, 9.8), (40, 5.0)], 3.5, CORE_SHADOW, 3.5))
    out.append(smooth_shape(i4, f"{prefix}ShinShape", shin_pts, skin_fill(prefix + "Shin", -6, 12, skin)))
    out.append(f"{i3}</Node>")

    # 2. Compression Shorts + Sculpted Quadriceps (Vastus Lateralis, Rectus Femoris, Vastus Medialis Teardrop)
    out.append(stroke_shape(i3, f"{prefix}ShortsHem", [(22, -14.0), (22.5, 0.0), (22, 13.0)], 1.3, "730F172A", 0.5))
    out.append(smooth_shape(i3, f"{prefix}ThighShorts", shorts_pts, skin_fill(prefix + "Shorts", -15, 15, shorts)))
    out.append(stroke_shape(i3, f"{prefix}QuadLine1", [(18, -5.5), (36, -5.2), (50, -4.2)], 1.3, SOFT_SHADOW, 0.9))
    out.append(stroke_shape(i3, f"{prefix}QuadLine2", [(24, 3.5), (40, 3.8), (51, 2.8)], 1.3, SOFT_SHADOW, 0.9))
    out.append(stroke_shape(i3, f"{prefix}ThighHi", [(16, -9.5), (36, -9.0), (50, -6.5)], 3.2, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i3, f"{prefix}ThighSh", [(14, 9.5), (34, 8.8), (48, 6.2)], 4.0, CORE_SHADOW, 4.0))
    out.append(smooth_shape(i3, f"{prefix}ThighShape", thigh_pts, skin_fill(prefix + "Thigh", -14, 14, skin)))

    out.append(f"{i2}</Node>")
    out.append(f"{ind}</Node>")
    return "\n".join(out)


def cable_tower_rig():
    """3D Cable Pulley Machine on the left side (x = 136..206, y = 24..300) with animated weight stack."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    stack_id = nid()
    key_double(stack_id, 14, lambda p: p["weight_stack_y"])
    p0 = POSES[0]

    frame_dark = f'<Fill name="TowerDarkFill">{grad("TowerDarkGrad", 142, 24, 164, 296, "FF334155", "FF0F172A")}</Fill>'
    frame_steel = f'<Fill name="TowerSteelFill">{grad("TowerSteelGrad", 142, 24, 160, 296, "FF94A3B8", "FF334155")}</Fill>'
    rod_chrome = f'<Fill name="RodChromeFill">{grad("RodChromeGrad", -2, 0, 2, 0, "FFF8FAFC", "FF64748B")}</Fill>'
    plate_paint = (
        '<Fill name="WeightPlateFill"><SolidColor colorValue="FF0F172A" name="WeightPlateCol"/></Fill>'
        '<Stroke thickness="0.8" name="WeightPlateRim"><SolidColor colorValue="FF475569" name="WeightPlateRimCol"/></Stroke>'
    )
    carriage_paint = f'<Fill name="CarriageFill">{grad("CarriageGrad", 174, PULLEY_Y - 14, 206, PULLEY_Y + 14, "FF475569", "FF0F172A")}</Fill>'

    # Resting bottom weight plates (y = 246..288)
    resting_plates = []
    for idx in range(6):
        py = 248.0 + idx * 6.8
        resting_plates.append(
            f'{i2}<Shape x="176" y="{f(py)}" name="RestPlate{idx + 1}"><Rectangle width="26" height="5.4" cornerRadiusTL="1" name="RestPlateRect{idx + 1}"/>{plate_paint}</Shape>'
        )

    # Moving top weight stack (6 plates + header block lifted by the selector cable)
    moving_plates = []
    for idx in range(6):
        py = idx * 6.8
        moving_plates.append(
            f'{i3}<Shape x="176" y="{f(py)}" name="MovePlate{idx + 1}"><Rectangle width="26" height="5.4" cornerRadiusTL="1" name="MovePlateRect{idx + 1}"/>{plate_paint}</Shape>'
        )
    # Selector pin in the bottom plate of the moving stack
    moving_plates.append(
        f'{i3}<Shape x="186" y="{f(5 * 6.8)}" name="SelectorPin"><Ellipse width="4" height="4" name="PinEl"/><Fill name="PinFill"><SolidColor colorValue="FFEF4444" name="PinCol"/></Fill></Shape>'
    )

    return "\n".join([
        f'{ind}<Node name="CableTower">',
        # Mid-Torso Pulley Carriage & Swivel Wheel at (PULLEY_X, PULLEY_Y)
        ellipse_shape(i2, "PulleyWheelHub", PULLEY_X, PULLEY_Y, 5.5, 5.5, solid("PulleyHub", "FFE2E8F0")),
        ellipse_shape(i2, "PulleyWheel", PULLEY_X, PULLEY_Y, 15.0, 15.0,
                      '<Fill name="PulleyWheelFill"><SolidColor colorValue="FF0F172A" name="PulleyWheelCol"/></Fill>'
                      '<Stroke thickness="1.6" name="PulleyWheelRim"><SolidColor colorValue="FF64748B" name="PulleyWheelRimCol"/></Stroke>'),
        poly_shape(i2, "PulleyCarriageArm", [(160, PULLEY_Y - 9), (198, PULLEY_Y - 7), (198, PULLEY_Y + 7), (160, PULLEY_Y + 9)], carriage_paint, radius=3.0),
        poly_shape(i2, "PulleyCarriageSleeve", [(144, PULLEY_Y - 16), (164, PULLEY_Y - 16), (164, PULLEY_Y + 14), (144, PULLEY_Y + 14)], frame_steel, radius=2.5),

        # Animated Moving Weight Stack (y rises from 228 to 186 as c goes 0 -> 1)
        f'{i2}<Node x="0" y="{f(p0["weight_stack_y"])}" name="MovingWeightStack" id="{stack_id}">',
        *moving_plates,
        f"{i2}</Node>",

        # Stationary Bottom Weight Plates
        *resting_plates,

        # Vertical Selector Cable & Dual Chrome Guide Rods (x = 168 and x = 184)
        stroke_shape(i2, "TowerLiftCable", [(176, 30), (176, 250)], 1.6, "FF94A3B8", 0.0, cap="butt"),
        f'{i2}<Shape x="168" y="160" name="GuideRodLeft"><Rectangle width="3.2" height="264" name="RodLRect"/>{rod_chrome}</Shape>',
        f'{i2}<Shape x="184" y="160" name="GuideRodRight"><Rectangle width="3.2" height="264" name="RodRRect"/>{rod_chrome}</Shape>',

        # Top Header Beam & Main Vertical Structural Column (x = 142..162, y = 24..294)
        poly_shape(i2, "TowerTopCap", [(140, 22), (194, 22), (194, 32), (140, 32)], frame_dark, radius=2.5),
        poly_shape(i2, "TowerColumnFront", [(142, 26), (154, 26), (154, 294), (142, 294)], frame_steel),
        poly_shape(i2, "TowerColumnSide", [(154, 26), (162, 26), (162, 294), (154, 294)], frame_dark),

        # Heavy Floor Stabilizer Base & Rubber Feet on FLOOR = 300.0
        poly_shape(i2, "TowerBaseFootFront", [(184, 295), (204, 295), (204, 300), (184, 300)], solid("RubberF", "FF090D16"), radius=1.5),
        poly_shape(i2, "TowerBaseFootBack", [(134, 295), (154, 295), (154, 300), (134, 300)], solid("RubberB", "FF090D16"), radius=1.5),
        poly_shape(i2, "TowerBaseRail", [(136, 289), (202, 289), (202, 296), (136, 296)], frame_dark, radius=2.0),
        stroke_shape(i2, "TowerBaseHi", [(138, 290), (200, 290)], 1.2, "FF94A3B8", 0.0, cap="round"),
        f"{ind}</Node>",
    ])


def shadow():
    ind = "        "
    sid = nid()
    key_double(sid, 13, lambda p: p["torso_x"] - 4.0)
    return "\n".join([
        # Dynamic athlete shadow on FLOOR = 300.0
        f'{ind}<Shape x="390" y="{f(FLOOR + 1)}" scaleX="0.92" scaleY="0.075" name="AthleteShadow" id="{sid}">\n'
        f'{ind}    <Ellipse width="200" height="200" name="AthleteShadowEl"/>\n'
        f'{ind}    <Fill name="AthleteShadowFill"><RadialGradient startX="0" startY="0" endX="100" endY="0" name="AthleteShadowGrad">'
        f'<GradientStop colorValue="B3000000" position="0"/><GradientStop colorValue="59000000" position="0.6"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{ind}</Shape>",
        # Cable tower shadow on FLOOR = 300.0
        f'{ind}<Shape x="172" y="{f(FLOOR + 1)}" scaleX="0.65" scaleY="0.065" name="TowerShadow">\n'
        f'{ind}    <Ellipse width="200" height="200" name="TowerShadowEl"/>\n'
        f'{ind}    <Fill name="TowerShadowFill"><RadialGradient startX="0" startY="0" endX="100" endY="0" name="TowerShadowGrad">'
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


right_arm_xml = arm_rig("Right", True)
cable_handle_xml = cable_and_handle_rig()
left_arm_xml = arm_rig("Left", False)
torso_head_xml = torso_and_head_rig()
right_leg_xml = leg_rig("Right", True)
left_leg_xml = leg_rig("Left", False)
tower_xml = cable_tower_rig()
shd_xml = shadow()

for cid in muscle_fill_ids:
    key_color(cid, 37, lambda p: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, muscle_t(p)))
for cid in muscle_line_ids:
    key_color(cid, 37, lambda p: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, muscle_t(p)))


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
    <!-- Cable Woodchopper: 60 fps, 16:9 (640x360), generated by gen_cable_woodchopper.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="CableWoodchopper" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- Foreground: Right Arm, D-Handle + Horizontal Cable, Left Arm -->
{right_arm_xml}
{cable_handle_xml}
{left_arm_xml}

        <!-- Midground: 3D Rotating Torso (with glowing Obliques) & Head, Right Leg, Left Pivot Leg -->
{torso_head_xml}
{right_leg_xml}
{left_leg_xml}

        <!-- Background Equipment: 3D Cable Pulley Tower with Animated Weight Stack -->
{tower_xml}

        <!-- Floor Shadows -->
{shd_xml}

{scenery()}

        <StateMachine name="CableWoodchopperSM" id="0:7">
            <StateMachineLayer name="Motion" id="0:8">
                <AnyState x="200" y="-120"/>
                <ExitState x="400" y="-120"/>
                <EntryState>
                    <StateTransition stateToId="0:12"/>
                </EntryState>
                <AnimationState x="200" animationId="0:60" id="0:12"/>
            </StateMachineLayer>
        </StateMachine>

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="woodchop" id="0:60">
{keyed_xml()}
        </LinearAnimation>
    </Artboard>
</Rive>
"""

OUT.write_text(rml)

for fr in (0, 34, 68, 76, 120, DURATION):
    P = POSES[fr]
    print(
        f"f{fr:3d} c={P['c']:.3f} wrist=({P['wrist'][0]:.1f},{P['wrist'][1]:.1f}) "
        f"elb_r=({P['elbow_r'][0]:.1f},{P['elbow_r'][1]:.1f}) "
        f"elb_l=({P['elbow_l'][0]:.1f},{P['elbow_l'][1]:.1f}) "
        f"stack_y={P['weight_stack_y']:.1f}"
    )
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
    # Standard Rive 7.3 header + TOC for our 29-tag procedural schema
    header = bytes([
        82, 73, 86, 69, 7, 3, 0, 196, 1, 236, 1, 238, 3, 229, 4, 230, 4, 231, 4,
        232, 4, 233, 4, 234, 4, 235, 4, 236, 4, 241, 4, 242, 4, 237, 5, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0,
    ])
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
    built = HERE / "build/cable_woodchopper.riv"
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
