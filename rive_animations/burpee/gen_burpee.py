#!/usr/bin/env python3
"""Generates rive_animations/burpee/scene.rml (and optionally publishes).

Rear three-quarter (3/4 back-left) view of a stylized male athlete performing
full Burpees at 60 fps on a 16:9 (640x360, FLOOR = 300.0) artboard, matching
the 4-stage anatomical reference illustration:
  1. Phase 1 — Squat Thrust / Crouch 1 (deep squat crouch, hands flat on floor,
     knees tucked toward chest, heels lifted on balls of feet).
  2. Phase 2 — High Plank & Push-up Dip (feet kick back explosively into a
     rigid straight-body high plank, perform a crisp chest-to-floor push-up dip,
     and press back to high plank).
  3. Phase 3 — Frog Jump In / Crouch 2 (feet hop forward under the hips into
     the coiled low squat crouch, loading the quads and glutes).
  4. Phase 4 — Explosive Vertical Jump with Overhead Reach (athlete explodes
     straight up off the floor with pointed toes, full hip/knee extension, and
     both arms reaching high overhead before landing softly back into Crouch 1).

Matches the exact character design of barbell_row, bench_dips, bench_press,
bicep_curl_barbell, bicycle_crunch, and bulgarian_split_squat (palette, 3-stop
linear gradients, Catmull-Rom smooth curves, feathered highlights / core
shadows, volumetric 3/4 head, and dynamic orange-to-red muscle activation).

Usage (from this directory):
    python3 gen_burpee.py            # regenerate scene.rml
    python3 gen_burpee.py --publish  # + build .riv, copy to assets, render thumbnail
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
ASSET_RIV = REPO / "assets/animations/burpee.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/burpee.png"
THUMB_ADVANCE = "0.90s"  # High plank kick-out phase
THUMB_VIEWPORT = "1280x720"  # 2x the 640x360 artboard
THUMB_CROP = (640, 60, 340)  # square size, offsetY, offsetX in the 2x render
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

# 16:9 standard canvas
W, H = 640, 360
FLOOR = 300.0

# Anthropometric limb segment lengths (consistent across all 4 burpee phases)
THIGH = 55.0
SHIN = 53.5
UPPER_ARM = 38.0
FOREARM = 35.0

# Spine local anchor offsets (Origin at Hip_near; +x runs up spine toward head)
SHOULDER_NEAR_X = 54.0
SHOULDER_FAR_X = 55.0
NECK_IN_SPINE = (61.0, 0.5)

# Timeline: 240 frames @ 60fps (4.0s full 4-phase burpee cycle)
DURATION = 240
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
EASE_OUT = cubic_bezier(0.18, 0.0, 0.22, 1.0)
EASE_IN = cubic_bezier(0.65, 0.0, 0.85, 1.0)


def lerp(a, b, t):
    return a + (b - a) * t


def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def solve_ik(root, target, l1, l2, bend_sign):
    """2D two-bone IK from root -> mid -> target.
    bend_sign = +1 or -1 selects which side of the (root -> target) chord the joint bends toward.
    """
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = math.hypot(dx, dy)
    d_clamped = min(max(d, abs(l1 - l2) + 0.5), l1 + l2 - 0.15)
    base_ang = math.atan2(dy, dx)
    cos_a = max(-1.0, min(1.0, (l1 * l1 + d_clamped * d_clamped - l2 * l2) / (2.0 * l1 * d_clamped)))
    ang1 = base_ang + bend_sign * math.acos(cos_a)
    mid = (root[0] + l1 * math.cos(ang1), root[1] + l1 * math.sin(ang1))
    ang2 = math.atan2(target[1] - mid[1], target[0] - mid[0])
    return ang1, ang2, mid


# Keyframes of high-level control parameters across the 4 phases:
KEY_STATES = {
    # Phase 1: Deep Squat Crouch (hands flat on floor, knees tucked high toward chest, heels lifted)
    "crouch": {
        "hip_near": (334.0, 250.0),
        "hip_far": (346.0, 245.0),
        "spine_deg": -144.0,
        "head_world_deg": -26.0,
        "sh_near_y": -6.5,
        "sh_far_y": 1.0,
        "ankle_near": (320.0, 287.0),
        "ankle_far": (335.0, 281.0),
        "foot_near_deg": 146.0,
        "foot_far_deg": 146.0,
        "wrist_near": (256.0, 293.0),
        "wrist_far": (274.0, 287.0),
        "hand_near_deg": 176.0,
        "hand_far_deg": 176.0,
        "ua_near_deg": 103.0,
        "fa_near_deg": 112.0,
        "ua_far_deg": 99.0,
        "fa_far_deg": 108.0,
        "muscle": 0.45,
    },
    # Phase 2a: Rigid High Plank (feet kicked back, straight line from head to heels, hands under shoulders)
    "plank": {
        "hip_near": (328.0, 236.0),
        "hip_far": (341.0, 230.0),
        "spine_deg": -161.0,
        "head_world_deg": -20.0,
        "sh_near_y": -6.5,
        "sh_far_y": 1.0,
        "ankle_near": (426.0, 285.0),
        "ankle_far": (440.0, 279.0),
        "foot_near_deg": 128.0,
        "foot_far_deg": 128.0,
        "wrist_near": (256.0, 293.0),
        "wrist_far": (274.0, 287.0),
        "hand_near_deg": 176.0,
        "hand_far_deg": 176.0,
        "ua_near_deg": 98.0,
        "fa_near_deg": 104.0,
        "ua_far_deg": 94.0,
        "fa_far_deg": 100.0,
        "muscle": 0.92,
    },
    # Phase 2b: Textbook Push-up Dip (shoulders shift forward over hands, elbows bend back ~45 deg above floor)
    "pushup": {
        "hip_near": (314.0, 254.0),
        "hip_far": (327.0, 248.0),
        "spine_deg": -171.0,
        "head_world_deg": -12.0,
        "sh_near_y": -6.5,
        "sh_far_y": 1.0,
        "ankle_near": (420.0, 286.0),
        "ankle_far": (434.0, 280.0),
        "foot_near_deg": 124.0,
        "foot_far_deg": 124.0,
        "wrist_near": (256.0, 293.0),
        "wrist_far": (274.0, 287.0),
        "hand_near_deg": 176.0,
        "hand_far_deg": 176.0,
        "ua_near_deg": 42.0,
        "fa_near_deg": 126.0,
        "ua_far_deg": 38.0,
        "fa_far_deg": 122.0,
        "muscle": 1.00,
    },
    # Phase 3: Frog Jump In / Crouch Return (feet hopped back under hips, coiled to launch)
    "crouch_return": {
        "hip_near": (332.0, 248.0),
        "hip_far": (344.0, 243.0),
        "spine_deg": -142.0,
        "head_world_deg": -24.0,
        "sh_near_y": -6.5,
        "sh_far_y": 1.0,
        "ankle_near": (318.0, 287.0),
        "ankle_far": (333.0, 281.0),
        "foot_near_deg": 146.0,
        "foot_far_deg": 146.0,
        "wrist_near": (256.0, 293.0),
        "wrist_far": (274.0, 287.0),
        "hand_near_deg": 176.0,
        "hand_far_deg": 176.0,
        "ua_near_deg": 104.0,
        "fa_near_deg": 113.0,
        "ua_far_deg": 100.0,
        "fa_far_deg": 109.0,
        "muscle": 0.54,
    },
    # Transition: Explosive Launch / Triple Extension on ground (arms swinging forward-up through 180 deg)
    "launch": {
        "hip_near": (316.0, 190.0),
        "hip_far": (327.0, 186.0),
        "spine_deg": -104.0,
        "head_world_deg": -4.0,
        "sh_near_y": -9.0,
        "sh_far_y": 9.0,
        "ankle_near": (316.0, 288.0),
        "ankle_far": (328.0, 283.0),
        "foot_near_deg": 138.0,
        "foot_far_deg": 138.0,
        "wrist_near": (256.0, 140.0),
        "wrist_far": (274.0, 134.0),
        "hand_near_deg": 215.0,
        "hand_far_deg": 220.0,
        "ua_near_deg": 190.0,
        "fa_near_deg": 212.0,
        "ua_far_deg": 196.0,
        "fa_far_deg": 218.0,
        "muscle": 0.86,
    },
    # Phase 4: Explosive Vertical Jump Apex (airborne, legs straight & extended, arms high overhead framing head)
    "jump": {
        "hip_near": (314.0, 158.0),
        "hip_far": (324.0, 155.0),
        "spine_deg": -90.0,
        "head_world_deg": 0.0,
        "sh_near_y": -10.5,
        "sh_far_y": 11.5,
        "ankle_near": (314.0, 266.0),
        "ankle_far": (325.0, 262.0),
        "foot_near_deg": 112.0,
        "foot_far_deg": 112.0,
        "wrist_near": (292.0, 26.0),
        "wrist_far": (328.0, 24.0),
        "hand_near_deg": 258.0,
        "hand_far_deg": 266.0,
        "ua_near_deg": 254.0,
        "fa_near_deg": 260.0,
        "ua_far_deg": 268.0,
        "fa_far_deg": 264.0,
        "muscle": 1.00,
    },
    # Transition: Soft Landing Absorption (athletic half-squat as arms swing forward-down)
    "land": {
        "hip_near": (322.0, 204.0),
        "hip_far": (333.0, 200.0),
        "spine_deg": -115.0,
        "head_world_deg": -10.0,
        "sh_near_y": -8.0,
        "sh_far_y": 5.0,
        "ankle_near": (318.0, 288.0),
        "ankle_far": (331.0, 282.0),
        "foot_near_deg": 146.0,
        "foot_far_deg": 146.0,
        "wrist_near": (256.0, 210.0),
        "wrist_far": (274.0, 204.0),
        "hand_near_deg": 195.0,
        "hand_far_deg": 195.0,
        "ua_near_deg": 156.0,
        "fa_near_deg": 176.0,
        "ua_far_deg": 158.0,
        "fa_far_deg": 178.0,
        "muscle": 0.66,
    },
}

# Timeline schedule: (frame, state_name, ease_fn_to_next)
SCHEDULE = [
    (0, "crouch", EASE),
    (14, "crouch", EASE),
    (44, "plank", EASE),
    (58, "plank", EASE),
    (80, "pushup", EASE),
    (88, "pushup", EASE),
    (110, "plank", EASE),
    (138, "crouch_return", EASE),
    (150, "crouch_return", EASE_IN),
    (164, "launch", EASE_OUT),
    (184, "jump", EASE),
    (196, "jump", EASE_IN),
    (214, "land", EASE_OUT),
    (240, "crouch", EASE),
]


def interp_state(frame):
    """Interpolate control state at `frame` in [0, DURATION]."""
    fr = max(0, min(DURATION, frame))
    for i in range(len(SCHEDULE) - 1):
        f0, s0_name, ease_fn = SCHEDULE[i]
        f1, s1_name, _ = SCHEDULE[i + 1]
        if f0 <= fr <= f1:
            t = 0.0 if f1 == f0 else ease_fn((fr - f0) / (f1 - f0))
            s0, s1 = KEY_STATES[s0_name], KEY_STATES[s1_name]
            out = {}
            for k in s0:
                v0, v1 = s0[k], s1[k]
                if isinstance(v0, tuple):
                    out[k] = (lerp(v0[0], v1[0], t), lerp(v0[1], v1[1], t))
                else:
                    out[k] = lerp(v0, v1, t)
            return out
    return dict(KEY_STATES["crouch"])


def solve_frame_pose(frame):
    """Compute exact 2D joint angles and positions for `frame` with continuous unwrapping."""
    st = interp_state(frame)
    hip_near = st["hip_near"]
    hip_far = st["hip_far"]
    ankle_near = st["ankle_near"]
    ankle_far = st["ankle_far"]
    sh_near_y = st["sh_near_y"]
    sh_far_y = st["sh_far_y"]

    # Spine & Head
    spine = math.radians(st["spine_deg"])
    head_world = math.radians(st["head_world_deg"])
    neck_local = head_world - spine

    # Near (left) Leg IK: Hip_near -> Knee_near -> Ankle_near (knee bends toward anterior-left: bend_sign = +1.0)
    thigh_near, shin_near_world, knee_near = solve_ik(
        hip_near, ankle_near, THIGH, SHIN, bend_sign=+1.0
    )
    if thigh_near < -0.4:
        thigh_near += 2.0 * math.pi
    if shin_near_world < -0.4:
        shin_near_world += 2.0 * math.pi
    shin_near_local = shin_near_world - thigh_near
    foot_near_world = math.radians(st["foot_near_deg"])
    foot_near_local = foot_near_world - shin_near_world

    # Far (right) Leg IK: Hip_far -> Knee_far -> Ankle_far
    thigh_far, shin_far_world, knee_far = solve_ik(
        hip_far, ankle_far, THIGH, SHIN, bend_sign=+1.0
    )
    if thigh_far < -0.4:
        thigh_far += 2.0 * math.pi
    if shin_far_world < -0.4:
        shin_far_world += 2.0 * math.pi
    shin_far_local = shin_far_world - thigh_far
    foot_far_world = math.radians(st["foot_far_deg"])
    foot_far_local = foot_far_world - shin_far_world

    # Both shoulders are anchored on the Spine (origin at hip_near)
    sh_near = add(hip_near, rot((SHOULDER_NEAR_X, sh_near_y), spine))
    sh_far = add(hip_near, rot((SHOULDER_FAR_X, sh_far_y), spine))

    if frame <= 150:
        w_ik = 1.0
    elif frame <= 164:
        w_ik = 1.0 - EASE((frame - 150) / 14.0)
    elif frame >= 224:
        w_ik = EASE((frame - 224) / 16.0)
    else:
        w_ik = 0.0

    # Floor IK solution (elbow bends backward-right: bend_sign = -1.0)
    ua_n_ik, fa_n_ik, _ = solve_ik(sh_near, st["wrist_near"], UPPER_ARM, FOREARM, bend_sign=-1.0)
    ua_f_ik, fa_f_ik, _ = solve_ik(sh_far, st["wrist_far"], UPPER_ARM, FOREARM, bend_sign=-1.0)
    if ua_n_ik < 0:
        ua_n_ik += 2.0 * math.pi
    if fa_n_ik < 0:
        fa_n_ik += 2.0 * math.pi
    if ua_f_ik < 0:
        ua_f_ik += 2.0 * math.pi
    if fa_f_ik < 0:
        fa_f_ik += 2.0 * math.pi

    ua_n_fk = math.radians(st["ua_near_deg"])
    fa_n_fk = math.radians(st["fa_near_deg"])
    ua_f_fk = math.radians(st["ua_far_deg"])
    fa_f_fk = math.radians(st["fa_far_deg"])

    ua_near_world = lerp(ua_n_fk, ua_n_ik, w_ik)
    fa_near_world = lerp(fa_n_fk, fa_n_ik, w_ik)
    ua_far_world = lerp(ua_f_fk, ua_f_ik, w_ik)
    fa_far_world = lerp(fa_f_fk, fa_f_ik, w_ik)

    ua_near_local = ua_near_world - spine
    fa_near_local = fa_near_world - ua_near_world
    hand_near_world = math.radians(st["hand_near_deg"])
    hand_near_local = hand_near_world - fa_near_world

    ua_far_local = ua_far_world - spine
    fa_far_local = fa_far_world - ua_far_world
    hand_far_world = math.radians(st["hand_far_deg"])
    hand_far_local = hand_far_world - fa_far_world

    return {
        "hip_near": hip_near,
        "hip_far": hip_far,
        "knee_near": knee_near,
        "knee_far": knee_far,
        "ankle_near": ankle_near,
        "ankle_far": ankle_far,
        "sh_near_y": sh_near_y,
        "sh_far_y": sh_far_y,
        "spine": spine,
        "neck_local": neck_local,
        "thigh_near": thigh_near,
        "shin_near_local": shin_near_local,
        "foot_near_local": foot_near_local,
        "thigh_far": thigh_far,
        "shin_far_local": shin_far_local,
        "foot_far_local": foot_far_local,
        "ua_near_local": ua_near_local,
        "fa_near_local": fa_near_local,
        "hand_near_local": hand_near_local,
        "ua_far_local": ua_far_local,
        "fa_far_local": fa_far_local,
        "hand_far_local": hand_far_local,
        "muscle": st["muscle"],
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)

POSES = {fr: solve_frame_pose(fr) for fr in FRAMES}

# Unwrap all angular tracks across consecutive frames and verify periodic loop closure
_ANGLE_KEYS = (
    "spine", "neck_local",
    "thigh_near", "shin_near_local", "foot_near_local",
    "thigh_far", "shin_far_local", "foot_far_local",
    "ua_near_local", "fa_near_local", "hand_near_local",
    "ua_far_local", "fa_far_local", "hand_far_local",
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
SKIN_FAR = ("FF9AA8BC", "FF6D7B90", "FF434E61")
SHORTS = ("731E293B", "800F172A", "8C020617")
SHORTS_FAR = ("73162030", "800B1120", "8C020617")
HIGHLIGHT = "40FFFFFF"
CORE_SHADOW = "4D0F172A"
SOFT_SHADOW = "2E0F172A"

# Dynamic orange -> deep crimson muscle activation
MUSCLE_LOW = "CCF97316"
MUSCLE_HIGH = "F2EF4444"
MUSCLE_LINE_LOW = "8C7F1D1D"
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
    return p["muscle"]


muscle_fill_ids, muscle_line_ids = [], []


def muscle_paint(name, line=0.9):
    fid, lid = nid(), nid()
    muscle_fill_ids.append(fid)
    muscle_line_ids.append(lid)
    t0 = muscle_t(POSES[0])
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{line}" join="round" name="{name}Edge"><SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- Anatomy Rigs
def arm_branch(indent, prefix, far):
    """UpperArm -> Forearm -> Hand with glowing Deltoid & Triceps brachii."""
    skin = SKIN_FAR if far else SKIN
    ua_id, fa_id, hand_id = nid(), nid(), nid()
    ua_key = "ua_far_local" if far else "ua_near_local"
    fa_key = "fa_far_local" if far else "fa_near_local"
    hand_key = "hand_far_local" if far else "hand_near_local"
    sh_y_key = "sh_far_y" if far else "sh_near_y"
    sx = SHOULDER_FAR_X if far else SHOULDER_NEAR_X

    key_double(ua_id, 14, lambda p: p[sh_y_key])
    key_double(ua_id, 15, lambda p: p[ua_key])
    key_double(fa_id, 15, lambda p: p[fa_key])
    key_double(hand_id, 15, lambda p: p[hand_key])
    p0 = POSES[0]
    i2 = indent + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "

    # In UpperArm local space (+x from Shoulder(0) -> Elbow(38)):
    # -y is POSTERIOR / LATERAL (Triceps brachii & Posterior/Lateral Deltoid)
    # +y is ANTERIOR / MEDIAL (Biceps brachii & Anterior Deltoid)
    ua_pts = [
        (-9, 0), (-7, -8.5), (6, -9.8), (18, -9.2), (30, -7.5), (36, -5.5),
        (40, 0), (36, 5.5), (26, 8.2), (14, 9.0), (2, 8.5), (-7, 6.8),
    ]
    delt_pts = [
        (-11, 0), (-8, -9.0), (2, -10.5), (13, -8.5), (17, -1.5),
        (14, 5.8), (5, 8.2), (-7, 7.2),
    ]
    # Triceps brachii horseshoe on the posterior/lateral (-y) upper arm
    triceps_pts = [
        (10, -8.6), (22, -8.2), (31, -6.2), (33, -1.8),
        (23, -0.5), (12, -1.5),
    ]

    fa_pts = [
        (-5, 0), (-4, -6.2), (6, -7.5), (18, -6.5), (28, -4.8), (34, -3.8),
        (37, 0), (34, 3.8), (25, 5.2), (14, 6.8), (4, 7.0), (-4, 5.5),
    ]

    # In Hand local space (+x extends along palm/fingers from Wrist(0) to fingertips(15)):
    hand_pts = [
        (-3, -3.2), (5, -3.8), (14, -3.2), (16, -1.2),
        (13, 1.8), (6, 3.2), (-2, 2.8),
    ]
    thumb_pts = [
        (0, -2.5), (5, -6.8), (9, -6.2), (7, -2.8),
    ]

    out = [f'{indent}<Node x="{f(sx)}" y="{f(p0[sh_y_key])}" rotation="{f(p0[ua_key])}" name="{prefix}UpperArm" id="{ua_id}">']

    # 1. Forearm + Hand
    out.append(f'{i2}<Node x="{f(UPPER_ARM)}" rotation="{f(p0[fa_key])}" name="{prefix}Forearm" id="{fa_id}">')
    out.append(f'{i3}<Node x="{f(FOREARM)}" rotation="{f(p0[hand_key])}" name="{prefix}HandNode" id="{hand_id}">')
    out.append(smooth_shape(i4, f"{prefix}Thumb", thumb_pts, skin_fill(prefix + "Thumb", -7, -2, skin)))
    out.append(smooth_shape(i4, f"{prefix}Hand", hand_pts, skin_fill(prefix + "Hand", -4, 4, skin)))
    out.append(f"{i3}</Node>")

    if not far:
        out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(5, -4.0), (16, -3.6), (27, -2.5)], 2.4, HIGHLIGHT, 3.0))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(5, 4.2), (16, 4.0), (27, 2.8)], 3.4, CORE_SHADOW, 4.0))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -8, 7, skin)))
    out.append(f"{i2}</Node>")

    # 2. Deltoid + Triceps Activation + UpperArm
    if not far:
        out.append(stroke_shape(i2, f"{prefix}DeltHi", [(-4, -5.5), (4, -6.8), (12, -4.2)], 2.5, "59FFFFFF", 2.5))
    out.append(smooth_shape(i2, f"{prefix}DeltActivation", delt_pts, muscle_paint(prefix + "Delt", 0.9)))
    out.append(smooth_shape(i2, f"{prefix}TricepsActivation", triceps_pts, muscle_paint(prefix + "Triceps", 0.85)))
    out.append(stroke_shape(i2, f"{prefix}UpperArmSh", [(6, 5.5), (18, 6.0), (29, 4.5)], 3.8, CORE_SHADOW, 4.0))
    out.append(smooth_shape(i2, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UpperArm", -10, 9, skin)))

    out.append(f"{indent}</Node>")
    return "\n".join(out)


def leg_branch(indent, prefix, far):
    """Hip -> Thigh -> Shin -> Foot in 3/4 rear-left view matching the anatomical reference chart."""
    skin = SKIN_FAR if far else SKIN
    shorts = SHORTS_FAR if far else SHORTS
    hip_id, thigh_id, shin_id, foot_id = nid(), nid(), nid(), nid()
    hip_key = "hip_far" if far else "hip_near"
    thigh_key = "thigh_far" if far else "thigh_near"
    shin_key = "shin_far_local" if far else "shin_near_local"
    foot_key = "foot_far_local" if far else "foot_near_local"

    key_double(hip_id, 13, lambda p: p[hip_key][0])
    key_double(hip_id, 14, lambda p: p[hip_key][1])
    key_double(thigh_id, 15, lambda p: p[thigh_key])
    key_double(shin_id, 15, lambda p: p[shin_key])
    key_double(foot_id, 15, lambda p: p[foot_key])
    p0 = POSES[0]

    i2 = indent + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "
    i5 = i4 + "    "

    # In Thigh local space (+x from Hip(0) -> Knee(55)):
    # +y is ANTERIOR / LATERAL (Quadriceps femoris: Vastus lateralis & Rectus femoris — glowing orange-red)
    # -y is POSTERIOR (Gluteus maximus at proximal hip [-14..+13] — glowing orange-red;
    #                  and silver/grey Hamstrings / IT band from x = 14..50 matching reference chart!)
    thigh_pts = [
        (-13.5, 0), (-11, 10.5), (5, 13.8), (24, 14.0), (40, 11.5), (50, 8.2),
        (58, 0), (50, -7.8), (38, -9.8), (22, -12.5), (4, -14.2), (-11, -11.8),
    ]
    shorts_thigh_pts = [
        (-14.2, 0), (-11.5, 11.2), (5, 14.4), (19, 14.0),
        (19, -12.8), (4, -14.8), (-11.5, -12.2),
    ]
    # Sculpted Quadriceps (+y) along the anterior/lateral thigh
    quad_pts = [
        (8, 3.2), (24, 3.5), (40, 3.5), (46, 7.5),
        (36, 11.5), (20, 13.4), (8, 12.8),
    ]
    # Rounded Gluteus maximus cheek at the proximal posterior hip (-y)
    glute_pts = [
        (-13.5, 2.5), (-10.5, -11.5), (2, -14.2), (13, -12.2),
        (13, -1.5), (-2, 2.2),
    ]

    # In Shin local space (+x from Knee(0) -> Ankle(53.5)):
    # +y is ANTERIOR (straight silver tibia bone)
    # -y is POSTERIOR (rounded Gastrocnemius & Soleus calf belly above the silver Achilles tendon)
    shin_pts = [
        (-8, 0), (-6, 5.8), (12, 5.5), (30, 4.8), (46, 3.8), (52, 3.2),
        (55, 0), (52, -3.8), (40, -5.2), (26, -10.5), (14, -12.5), (4, -10.5), (-6, -6.5),
    ]
    # Sculpted diamond Gastrocnemius & Soleus on the upper-mid posterior (-y) calf
    gastroc_pts = [
        (5, -4.2), (16, -4.8), (27, -4.5), (29, -8.8),
        (16, -12.0), (5, -9.5),
    ]
    soleus_pts = [
        (23, -3.5), (33, -3.2), (38, -4.8), (27, -8.8),
    ]

    # In Foot local space (+x runs from Ankle(0) to Toes(22)):
    foot_pts = [
        (-6, 1.5), (-3, 7.2), (2, 6.8), (8, 2.5), (17, 1.0), (22, -0.8),
        (20, -3.6), (10, -4.0), (-1, -3.6), (-5, -1.8),
    ]

    out = [f'{indent}<Node x="{f(p0[hip_key][0])}" y="{f(p0[hip_key][1])}" name="{prefix}LegHip" id="{hip_id}">']
    out.append(f'{i2}<Node rotation="{f(p0[thigh_key])}" name="{prefix}Thigh" id="{thigh_id}">')

    # 1. Shin + Foot + KneeCap
    out.append(f'{i3}<Node x="{f(THIGH)}" rotation="{f(p0[shin_key])}" name="{prefix}Shin" id="{shin_id}">')
    out.append(f'{i4}<Node x="{f(SHIN)}" rotation="{f(p0[foot_key])}" name="{prefix}Foot" id="{foot_id}">')
    if not far:
        out.append(stroke_shape(i5, f"{prefix}FootHi", [(2, 2.0), (10, 0.8), (18, -0.5)], 1.8, HIGHLIGHT, 2.0))
    out.append(smooth_shape(i5, f"{prefix}FootShape", foot_pts, skin_fill(prefix + "Foot", -4, 7, skin)))
    out.append(f"{i4}</Node>")

    out.append(ellipse_shape(i4, f"{prefix}KneeCap", 0, 1, 15, 14, skin_fill(prefix + "Knee", -7, 7, skin)))
    out.append(smooth_shape(i4, f"{prefix}SoleusActivation", soleus_pts, muscle_paint(prefix + "Soleus", 0.8)))
    out.append(smooth_shape(i4, f"{prefix}GastrocActivation", gastroc_pts, muscle_paint(prefix + "Gastroc", 0.9)))
    out.append(stroke_shape(i4, f"{prefix}AchillesLine", [(30, -2.2), (42, -2.0), (50, -1.8)], 1.1, SOFT_SHADOW, 0.8))
    if not far:
        out.append(stroke_shape(i4, f"{prefix}ShinHi", [(10, 3.5), (28, 3.2), (44, 2.2)], 2.6, HIGHLIGHT, 3.0))
    out.append(stroke_shape(i4, f"{prefix}ShinSh", [(10, -8.5), (24, -9.5), (38, -4.5)], 3.4, CORE_SHADOW, 3.5))
    out.append(smooth_shape(i4, f"{prefix}ShinShape", shin_pts, skin_fill(prefix + "Shin", -12, 6, skin)))
    out.append(f"{i3}</Node>")

    # 2. Sleek Compression Shorts + Gluteus Maximus, Quadriceps & Sculpted Silver Hamstrings
    out.append(stroke_shape(i3, f"{prefix}ShortsHem", [(19, -12.4), (19.5, 0.0), (19, 13.6)], 1.1, "590F172A", 0.5))
    out.append(smooth_shape(i3, f"{prefix}ThighShorts", shorts_thigh_pts, skin_fill(prefix + "ThighShorts", -15, 15, shorts)))
    out.append(stroke_shape(i3, f"{prefix}ITBandHi", [(12, 1.2), (28, 1.4), (44, 1.5)], 2.2, "73FFFFFF", 1.8))
    out.append(stroke_shape(i3, f"{prefix}HamstringGroove", [(16, -5.5), (30, -5.2), (44, -4.5)], 1.3, "470F172A", 1.0))
    out.append(smooth_shape(i3, f"{prefix}QuadActivation", quad_pts, muscle_paint(prefix + "Quad", 0.9)))
    out.append(smooth_shape(i3, f"{prefix}GluteActivation", glute_pts, muscle_paint(prefix + "Glute", 0.95)))
    out.append(stroke_shape(i3, f"{prefix}ThighSh", [(12, -9.5), (28, -8.5), (44, -5.5)], 4.0, CORE_SHADOW, 4.0))
    out.append(smooth_shape(i3, f"{prefix}ThighShape", thigh_pts, skin_fill(prefix + "Thigh", -14, 14, skin)))

    out.append(f"{i2}</Node>")
    out.append(f"{indent}</Node>")
    return "\n".join(out)


def torso_and_near_arm_rig():
    """Near (left) Arm + Near (left) Leg + 3/4 Rear-Left Torso (with Trapezius/Erector Spinae) + Head."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "
    hip_id, torso_root_id, spine_id, neck_id, near_arm_spine_id = nid(), nid(), nid(), nid(), nid()
    key_double(hip_id, 13, lambda p: p["hip_near"][0])
    key_double(hip_id, 14, lambda p: p["hip_near"][1])
    key_double(torso_root_id, 13, lambda p: p["hip_near"][0])
    key_double(torso_root_id, 14, lambda p: p["hip_near"][1])
    key_double(spine_id, 15, lambda p: p["spine"])
    key_double(neck_id, 15, lambda p: p["neck_local"])
    key_double(near_arm_spine_id, 15, lambda p: p["spine"])
    p0 = POSES[0]

    # In Spine local space (+x from Hip_near(0,0) up the spine to Neck(61, 0.5)):
    # Concentric ball-and-socket base at (0,0) (x = -8..62, y = -11..+14) so flexing the hip never protrudes behind the glutes!
    torso_pts = [
        (-8, 12.5),    # sacrum / upper gluteal flare
        (-8, -9.5),    # anterior-left waist/iliac crest
        (8, -11.8),    # lower left flank / external oblique
        (24, -11.5),   # mid left ribcage
        (42, -14.0),   # upper left latissimus / serratus
        (55, -13.0),   # left shoulder / acromion
        (62, -6.0),    # left base of neck
        (62, 8.0),     # right base of neck
        (53, 15.5),    # upper right latissimus / teres major flare
        (36, 14.2),    # mid back / right lat taper
        (18, 12.5),    # lumbar curve / erector spinae
        (4, 15.0),     # posterior-right iliac crest bridging smoothly to far glute
    ]
    # Sculpted Trapezius / Rhomboids / Erector Spinae diamond band along the dorsal spine (+y side of Spine)
    back_trap_pts = [
        (10, 3.8), (28, 2.2), (48, 0.5), (60, 2.2),
        (57, 9.8), (42, 12.0), (26, 10.5), (10, 7.8),
    ]
    # Left Latissimus Dorsi wing contour on the mid-upper back
    lat_wing_pts = [
        (22, -10.0), (42, -12.5), (51, -4.0), (42, 2.2), (26, 1.2),
    ]
    lat_paint = (
        '<Fill name="LatFill"><SolidColor colorValue="1A0F172A" name="LatCol"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="LatStroke"><SolidColor colorValue="3D0F172A" name="LatStrokeCol"/></Stroke>'
    )

    # Volumetric 3/4 Rear-Left Head & Neck in Neck local space:
    neck_pts = [
        (-6.5, -14.0), (5.5, -12.0), (6.5, 0.5),
        (0.0, 2.2), (-6.0, 0.0), (-7.2, -7.0),
    ]
    head_pts = [
        (-9.5, -31.0),   # upper left forehead / temple
        (-11.2, -25.5),  # left brow ridge
        (-12.2, -20.5),  # nose tip profile (facing forward-left)
        (-11.0, -16.0),  # lips / mouth
        (-10.2, -11.5),  # chin
        (-4.5, -10.0),   # jawline under chin
        (3.5, -12.5),    # occiput / nape of skull
        (9.5, -19.5),    # back of head (visible in 3/4 rear view)
        (9.2, -28.5),    # posterior crown
        (3.5, -34.0),    # top cranial dome
        (-4.5, -33.8),   # anterior crown
    ]
    hair_pts = [
        (-9.8, -29.0), (-4.5, -34.5), (4.0, -34.5), (9.8, -29.0),
        (10.0, -19.0), (5.5, -14.0), (1.0, -16.5), (-2.5, -23.0),
        (-6.5, -27.5),
    ]

    out = [
        # 1. Near (Left) Arm in foreground (connected to hip_near + spine rotation)
        f'{ind}<Node x="{f(p0["hip_near"][0])}" y="{f(p0["hip_near"][1])}" name="NearBodyRoot" id="{hip_id}">',
        f'{i2}<Node rotation="{f(p0["spine"])}" name="NearArmSpine" id="{near_arm_spine_id}">',
        arm_branch(i3, "Near", False),
        f"{i2}</Node>",
        f"{ind}</Node>",

        # 2. Near (Left) Leg (between Near Arm and Torso so tucked knee in Crouch sits behind the triceps!)
        leg_branch(ind, "Near", False),

        # 3. 3/4 Rear-Left Torso & Head
        f'{ind}<Node x="{f(p0["hip_near"][0])}" y="{f(p0["hip_near"][1])}" name="TorsoRoot" id="{torso_root_id}">',
        f'{i2}<Node rotation="{f(p0["spine"])}" name="Spine" id="{spine_id}">',
    ]

    # Torso back muscles, latissimus wing, and oblique ribs
    out.append(stroke_shape(i3, "SpinalFurrow", [(10, 5.8), (32, 5.2), (55, 4.8)], 1.3, "737F1D1D", 0.6))
    out.append(smooth_shape(i3, "TrapeziusErectorActivation", back_trap_pts, muscle_paint("TrapErector", 0.95)))
    out.append(smooth_shape(i3, "LatWing", lat_wing_pts, lat_paint))
    out.append(stroke_shape(i3, "RibOblique1", [(30, -9.2), (24, -5.2), (18, -3.2)], 1.2, "380F172A", 0.8))
    out.append(stroke_shape(i3, "RibOblique2", [(21, -9.2), (15, -5.5), (10, -3.8)], 1.2, "380F172A", 0.8))
    out.append(stroke_shape(i3, "TorsoHi", [(14, 8.0), (36, 9.0), (52, 11.0)], 3.8, HIGHLIGHT, 4.0))
    out.append(stroke_shape(i3, "TorsoSh", [(12, -8.5), (34, -9.5), (50, -10.0)], 4.5, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i3, "Torso", torso_pts, skin_fill("Torso", -14, 15, SKIN)))

    # Head & Neck
    nx, ny = NECK_IN_SPINE
    out.append(f'{i3}<Node x="{f(nx)}" y="{f(ny)}" rotation="{f(p0["neck_local"])}" name="Neck" id="{neck_id}">')
    out.append(ellipse_shape(i4, "Ear", -2.5, -18.5, 4.5, 7.0, solid("Ear", "FFA3B1C4"), rot_deg=10.0))
    out.append(smooth_shape(i4, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", -10, -34, 10, -15, "FF475569", "FF1E293B")}</Fill>'))
    out.append(stroke_shape(i4, "HeadHi", [(-8.0, -28.0), (-2.0, -32.0), (5.0, -30.0)], 2.5, HIGHLIGHT, 3.0))
    out.append(stroke_shape(i4, "JawShadow", [(-8.5, -11.0), (-2.0, -10.5), (3.0, -12.5)], 2.2, CORE_SHADOW, 2.0))
    out.append(smooth_shape(i4, "Head", head_pts, skin_fill("Head", -34, -10, SKIN, x0=-12, x1=10)))
    out.append(smooth_shape(i4, "NeckShape", neck_pts, skin_fill("Neck", -14, 4, SKIN)))
    out.append(f"{i3}</Node>")

    out.append(f"{i2}</Node>")
    out.append(f"{ind}</Node>")
    return "\n".join(out)


def far_limbs_rig():
    """Far (right) Leg and Far (right) Arm on the far side of the athlete."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    hip_id, spine_id = nid(), nid()
    # Anchor FarArmRoot to hip_near (same spine origin as TorsoRoot!) so FarUpperArm aligns with the torso's right shoulder
    key_double(hip_id, 13, lambda p: p["hip_near"][0])
    key_double(hip_id, 14, lambda p: p["hip_near"][1])
    key_double(spine_id, 15, lambda p: p["spine"])
    p0 = POSES[0]
    return "\n".join([
        leg_branch(ind, "Far", True),
        f'{ind}<Node x="{f(p0["hip_near"][0])}" y="{f(p0["hip_near"][1])}" name="FarArmRoot" id="{hip_id}">',
        f'{i2}<Node rotation="{f(p0["spine"])}" name="FarArmSpine" id="{spine_id}">',
        arm_branch(i3, "Far", True),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


def shadow():
    """Dynamic floor shadow that stretches wide during the Plank/Push-up and narrows/fades during the Vertical Jump."""
    ind = "        "
    sid = nid()
    key_double(sid, 13, lambda p: (p["ankle_near"][0] + min(p["hip_near"][0], 265.0)) * 0.5)
    key_double(sid, 16, lambda p: max(0.52, min(1.45, (p["ankle_near"][0] - 245.0) / 135.0 + 0.45)))
    key_double(sid, 17, lambda p: 0.045 if p["ankle_near"][1] < 270.0 else 0.08)
    p0 = POSES[0]
    x0 = (p0["ankle_near"][0] + min(p0["hip_near"][0], 265.0)) * 0.5
    sx0 = max(0.52, min(1.45, (p0["ankle_near"][0] - 245.0) / 135.0 + 0.45))
    return (
        f'{ind}<Shape x="{f(x0)}" y="{f(FLOOR + 1)}" scaleX="{f(sx0)}" scaleY="0.08" name="BodyShadow" id="{sid}">\n'
        f'{ind}    <Ellipse width="220" height="200" name="ShadowEllipse"/>\n'
        f'{ind}    <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="110" endY="0" name="ShadowGrad">'
        f'<GradientStop colorValue="B3000000" position="0"/><GradientStop colorValue="59000000" position="0.6"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{ind}</Shape>"
    )


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


near_xml = torso_and_near_arm_rig()
far_xml = far_limbs_rig()
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
    <!-- Burpee: 3/4 rear-left view, 60 fps, 16:9 (640x360), generated by gen_burpee.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="Burpee" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- Foreground: Near (left) arm, Near (left) leg, 3/4 Rear-Left Torso & Head -->
{near_xml}

        <!-- Background: Far (right) leg & Far (right) arm -->
{far_xml}

        <!-- Dynamic Floor Shadow -->
{shd_xml}

{scenery()}

        <StateMachine name="BurpeeSM" id="0:7">
            <StateMachineLayer name="Motion" id="0:8">
                <AnyState x="200" y="-120"/>
                <ExitState x="400" y="-120"/>
                <EntryState>
                    <StateTransition stateToId="0:12"/>
                </EntryState>
                <AnimationState x="200" animationId="0:60" id="0:12"/>
            </StateMachineLayer>
        </StateMachine>

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="burpee" id="0:60">
{keyed_xml()}
        </LinearAnimation>
    </Artboard>
</Rive>
"""

OUT.write_text(rml)

for fr in (0, 12, 54, 84, 146, 164, 190, 214, DURATION):
    P = POSES[fr]
    print(
        f"f{fr:3d} m={P['muscle']:.2f} hip=({P['hip_near'][0]:.1f},{P['hip_near'][1]:.1f}) "
        f"knee=({P['knee_near'][0]:.1f},{P['knee_near'][1]:.1f}) "
        f"ank=({P['ankle_near'][0]:.1f},{P['ankle_near'][1]:.1f})"
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
    built = HERE / "build/burpee.riv"
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
