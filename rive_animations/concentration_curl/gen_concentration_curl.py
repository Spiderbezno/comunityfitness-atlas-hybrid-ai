#!/usr/bin/env python3
"""Generates rive_animations/concentration_curl/scene.rml (and optionally publishes).

16:9 (640x360, FLOOR = 300.0) 60 fps procedural Rive animation for the
Seated Dumbbell Concentration Curl (`id: concentration_curl`), matching the
2-panel 3/4 front-right anatomical reference chart:
  - Camera: 3/4 front-right isometric view showing a muscular athlete seated
    near the front-right end of a 3D flat weight bench (`(130, 174)` to
    `(356, 194)`) with a white/silver powder-coated steel frame, rear T-leg,
    horizontal cross-beam, and angled front leg (`(326, 196) -> (352, 286)`).
  - Wide-Stance Lower Body:
    - Near (Right) Leg (left-foreground): thigh extends forward from the right
      hip (`(276, 172)`) to the right knee (`(308, 198)`), lower leg (sculpted
      tibialis anterior & medial gastrocnemius) drops vertically to the bare
      right foot planted on `FLOOR = 300.0` at `(300, 296)` facing the viewer.
    - Far (Left) Leg (right side): thigh extends outward-right from the left
      hip (`(320, 170)`) to the left knee (`(396, 188)`), lower leg drops with
      a prominent inner medial gastrocnemius calf belly down to the bare left
      foot planted at `(388, 276)` angled outward to the right.
  - Forward-Hinged Torso, Bracing Right Arm & Downward-Looking Head:
    - Torso leans forward over the hips (`(292, 168)` up to right shoulder
      `(312, 86)` and left working shoulder `(362, 102)`), showing sculpted
      pectoralis major plates, rectus abdominis & obliques, broad deltoids,
      and upper trapezius/neck.
    - Volumetric 3/4 head at `(372, 54..94)` tilted downward-left looking
      directly at the working left biceps.
    - Stationary Bracing Right Arm: hangs from the right shoulder `(308, 88)`
      through a slightly bent right elbow `(276, 134)` with the right forearm
      resting across the right thigh and the right hand cupping the top of the
      right knee `(308, 192)`.
  - Biomechanics (`r` in [0.0, 1.0], 160 frames / 2.67s @ 60 fps):
    - Braced Left Upper Arm (`SHOULDER = (362.0, 104.0)` -> `ELBOW = (364.0, 166.0)`):
      braced firmly against the inner left thigh (`<= 1.5 px` micro-shift).
    - Pivoting Left Forearm & 3D Double-Plate Dumbbell (`r = 0.0 -> 1.0`):
      curls from full extension (`WRIST = (358.0, 224.0)` at `r = 0.0`) through
      mid-curl (`WRIST = (346.0, 178.0)` at `r = 0.5`) up to peak contraction
      (`WRIST = (360.0, 134.0)` at `r = 1.0`) in front of the bulging biceps.

Activated muscles (`muscle_t`):
  - Primary:
    1. Biceps brachii — short head (`scale = 1.0`, inner/medial belly)
    2. Biceps brachii — long head (`scale = 1.0`, outer/lateral peak)
    3. Brachialis (`scale = 0.92`, distal-lateral belly between biceps & triceps)
    4. Brachioradialis (`scale = 0.88`, upper-forearm belly across elbow crease)

Usage (from repo root or this directory):
    python3 gen_concentration_curl.py            # regenerate scene.rml
    python3 gen_concentration_curl.py --publish  # + build .riv, copy to assets, render thumbnail
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
ASSET_RIV = REPO / "assets/animations/concentration_curl.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/concentration_curl.png"
THUMB_ADVANCE = "1.20s"  # peak biceps contraction (frame 72, r = 1.0)
THUMB_VIEWPORT = "1280x720"  # 2x the 640x360 artboard
THUMB_CROP = (620, 40, 290)  # square size, offsetY, offsetX in the 2x render
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

# 16:9 standard canvas
W, H = 640, 360
FLOOR = 300.0

# Working Left Arm Anchors in World Space
SHOULDER_LEFT = (362.0, 104.0)
ELBOW_BASE = (364.0, 166.0)
FOREARM_REST_LEN = 58.3  # dist((364, 166), (358, 224)) at r = 0.0

# Timeline (frames @60fps):
# 0..12: bottom full-extension stretch hold (r = 0.0)
# 12..66: smooth concentric curl upward (r: 0.0 -> 1.0)
# 66..84: peak isometric biceps contraction hold (r = 1.0)
# 84..148: controlled eccentric lowering back to full extension (r: 1.0 -> 0.0)
# 148..160: bottom hold (r = 0.0)
HOLD_BOT_1 = 12
CURL_FRAMES = 54
HOLD_TOP = 18
LOWER_FRAMES = 64
HOLD_BOT_2 = 12
DURATION = HOLD_BOT_1 + CURL_FRAMES + HOLD_TOP + LOWER_FRAMES + HOLD_BOT_2  # 160 frames (2.67s)
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


def curl_progress(frame):
    """0.0 at bottom full extension (Panel 1), 1.0 at peak concentration curl contraction (Panel 2)."""
    fr = frame % DURATION
    if fr <= HOLD_BOT_1:
        return 0.0
    fr -= HOLD_BOT_1
    if fr <= CURL_FRAMES:
        return EASE_UP(fr / CURL_FRAMES)
    fr -= CURL_FRAMES
    if fr <= HOLD_TOP:
        return 1.0
    fr -= HOLD_TOP
    if fr <= LOWER_FRAMES:
        return 1.0 - EASE_DOWN(fr / LOWER_FRAMES)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def quad_interp_pt(p0, p_mid, p1, r):
    """Smooth quadratic interpolation passing through p0 (r=0), p_mid (r=0.5), and p1 (r=1.0)."""
    l0 = (1.0 - r) * (1.0 - 2.0 * r)
    l1 = 4.0 * r * (1.0 - r)
    l2 = r * (2.0 * r - 1.0)
    return (
        l0 * p0[0] + l1 * p_mid[0] + l2 * p1[0],
        l0 * p0[1] + l1 * p_mid[1] + l2 * p1[1],
    )


def pose(r):
    """Compute Seated Concentration Curl joint transforms at curl progress r in [0.0, 1.0]."""
    # 1. Braced Left Elbow against the inner left thigh (locked at x = 364.0, <= 1.5 px upward shift at r = 1.0)
    elbow = (ELBOW_BASE[0], lerp(ELBOW_BASE[1], ELBOW_BASE[1] - 1.5, r))

    # 2. Working Left Wrist trajectory curling inward toward the upper chest midline so Biceps Peak & Brachioradialis read cleanly:
    #    - Bottom (r = 0.0): (358.0, 224.0) hanging straight down
    #    - Mid    (r = 0.5): (342.0, 178.0) foreshortened mid-curl
    #    - Top    (r = 1.0): (332.0, 132.0) curled upward & inward in front of the chest, clearing the upper arm
    wrist = quad_interp_pt((358.0, 224.0), (342.0, 178.0), (332.0, 132.0), r)

    # 3. 3D-foreshortened Forearm orientation & length scale from Elbow -> Wrist
    dx, dy = wrist[0] - elbow[0], wrist[1] - elbow[1]
    fa_dist = math.hypot(dx, dy)
    fa_rot = math.atan2(dy, dx)
    if fa_rot < 0:
        fa_rot += 2.0 * math.pi  # continuous in [+1.67 rad (+95.9 deg) .. +4.28 rad (+245.3 deg)]
    fa_sx = max(0.30, fa_dist / FOREARM_REST_LEN)

    # 4. Brachioradialis local Y offset inside Forearm:
    #    At r = 0.0 (fa_rot = +95.9 deg), local -Y faces right (+X_screen).
    #    At r = 1.0 (fa_rot = +245.3 deg), local +Y faces front-right (+X_screen) just below the supinated fist!
    brach_y = lerp(-3.0, 3.6, r)

    # 5. 3D Cast-Iron Double-Plate Dumbbell orientation in world space (0 deg at bottom to -5 deg at top)
    db_rot = math.radians(lerp(0.0, -5.0, r))

    # 6. Dynamic Biceps Brachii (Short & Long Head) & Brachialis peak swelling on the braced left upper arm
    biceps_sx = lerp(1.00, 1.24, r ** 0.95)
    biceps_sy = lerp(1.00, 1.06, r ** 0.95)
    biceps_dx = lerp(0.0, -1.0, r)

    # 7. Subtle torso/head micro-focus at peak squeeze (<= 1.2 deg downward gaze nod)
    head_rot = math.radians(lerp(0.0, 1.2, r))

    return {
        "r": r,
        "elbow": elbow,
        "wrist": wrist,
        "fa_rot": fa_rot,
        "fa_sx": fa_sx,
        "brach_y": brach_y,
        "db_rot": db_rot,
        "biceps_sx": biceps_sx,
        "biceps_sy": biceps_sy,
        "biceps_dx": biceps_dx,
        "head_rot": head_rot,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(curl_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = ("fa_rot", "db_rot", "head_rot")
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
    for _fr in (0, 38, 52, 72, 116, DURATION):
        _p = POSES[_fr]
        print(
            f"f{_fr:3d} r={_p['r']:.3f} el=({_p['elbow'][0]:.1f},{_p['elbow'][1]:.1f}) "
            f"wr=({_p['wrist'][0]:.1f},{_p['wrist'][1]:.1f}) "
            f"fa_rot={math.degrees(_p['fa_rot']):+.1f} fa_sx={_p['fa_sx']:.2f} bic_sx={_p['biceps_sx']:.2f}"
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
MUSCLE_LOW = (0xBF, 0xF9, 0x73, 0x16)       # warm glowing orange at bottom stretch (#FFF97316)
MUSCLE_HIGH = (0xF5, 0xF4, 0x3F, 0x5E)      # intense crimson-red at peak biceps contraction (#FFF43F5E)
MUSCLE_LINE_LOW = (0x80, 0x9A, 0x34, 0x12)
MUSCLE_LINE_HIGH = (0xE6, 0x88, 0x13, 0x37)


def argb_lerp(a, b, t):
    return "".join(f"{round(lerp(x, y, t)):02X}" for x, y in zip(a, b))


keys = []  # (objectId, propertyKey, kind, [(frame, value)])


def key_double(obj, prop, fn):
    keys.append((obj, prop, "double", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def key_color(obj, prop, fn):
    keys.append((obj, prop, "color", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def muscle_t(p, scale=1.0):
    """Smooth activation curve peaking at r = 1.0 (peak concentration curl squeeze)."""
    base = 0.20 + 0.80 * (p["r"] ** 0.85)
    return min(1.0, max(0.0, base * scale))


muscle_fill_ids, muscle_line_ids = [], []


def muscle_paint(name, line=0.95, scale=1.0):
    fid, lid = nid(), nid()
    muscle_fill_ids.append((fid, scale))
    muscle_line_ids.append((lid, scale))
    t0 = muscle_t(POSES[0], scale)
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Col" id="{fid}"/></Fill>'
        f'<Stroke thickness="{line}" join="round" name="{name}Edge"><SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeCol" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- 1. Stationary Bracing Right Arm (Hand Cupping Right Knee)
def bracing_right_arm_rig():
    """Stationary right arm hanging from right shoulder (308, 88) -> elbow (276, 134) -> hand cupping right knee (308, 192)."""
    ind = "        "
    i2 = ind + "    "

    # 1. Right Hand cupping the top of the right patella/knee at (308, 192)
    hand_pts = [
        (296.0, 178.0), (308.0, 176.0), (316.0, 184.0),
        (317.5, 197.0), (313.5, 204.0), (305.0, 203.0),
        (298.5, 196.0), (294.5, 186.0),
    ]
    # 2. Right Forearm extending from elbow (276, 134) down-right across the thigh to wrist (303, 180)
    forearm_pts = [
        (267.0, 134.0), (281.0, 129.0), (293.0, 146.0), (308.0, 176.0),
        (296.5, 181.0), (280.0, 161.0), (267.5, 144.0),
    ]
    # 3. Right Upper Arm & Anterior/Lateral Deltoid from shoulder (308, 88) to elbow (276, 134)
    upper_arm_pts = [
        (294.0, 84.0), (314.0, 88.0), (309.0, 108.0), (291.0, 132.0),
        (277.0, 140.0), (266.5, 134.0), (273.0, 114.0), (284.0, 95.0),
    ]
    right_delt_pts = [
        (292.0, 80.0), (314.0, 78.0), (320.0, 92.0),
        (310.0, 108.0), (294.0, 109.0), (284.0, 95.0),
    ]

    return "\n".join([
        f'{ind}<Node name="BracingRightArm">',
        # Right Hand & Fingers resting over the right kneecap
        stroke_shape(i2, "RightFingerCrease1", [(304.0, 188.0), (307.0, 201.0)], 1.0, CORE_SHADOW, 0.3),
        stroke_shape(i2, "RightFingerCrease2", [(309.0, 187.0), (312.0, 201.5)], 1.0, CORE_SHADOW, 0.3),
        stroke_shape(i2, "RightFingerCrease3", [(313.5, 186.5), (315.8, 199.0)], 0.9, CORE_SHADOW, 0.3),
        stroke_shape(i2, "RightHandHi", [(302.0, 180.0), (310.0, 188.0), (312.0, 198.0)], 2.2, HIGHLIGHT, 2.0),
        smooth_shape(i2, "RightHandOnKnee", hand_pts, skin_fill("RightHand", 176, 204, SKIN, x0=316, x1=295)),

        # Right Forearm (Brachioradialis & Extensor Carpi)
        stroke_shape(i2, "RightForearmGroove", [(276.0, 138.0), (290.0, 158.0), (301.0, 175.0)], 1.2, SOFT_SHADOW, 0.7),
        stroke_shape(i2, "RightForearmHi", [(278.0, 135.0), (291.0, 154.0), (303.0, 173.0)], 2.8, HIGHLIGHT, 2.5),
        stroke_shape(i2, "RightForearmSh", [(270.0, 142.0), (282.0, 160.0), (295.0, 178.0)], 3.0, CORE_SHADOW, 2.8),
        smooth_shape(i2, "RightForearmShape", forearm_pts, skin_fill("RightForearm", 129, 181, SKIN, x0=306, x1=268)),

        # Right Deltoid & Upper Arm
        stroke_shape(i2, "RightDeltFiber1", [(304.0, 83.0), (296.0, 96.0), (292.0, 105.0)], 1.1, SOFT_SHADOW, 0.6),
        stroke_shape(i2, "RightDeltFiber2", [(311.0, 85.0), (304.0, 98.0), (300.0, 106.0)], 1.1, SOFT_SHADOW, 0.6),
        stroke_shape(i2, "RightDeltHi", [(296.0, 84.0), (305.0, 83.0), (312.0, 92.0)], 3.0, HIGHLIGHT, 2.8),
        smooth_shape(i2, "RightDeltoidCap", right_delt_pts, skin_fill("RightDelt", 78, 109, SKIN, x0=316, x1=285)),
        stroke_shape(i2, "RightBicepsGroove", [(298.0, 105.0), (288.0, 120.0), (279.0, 132.0)], 1.3, CORE_SHADOW, 0.8),
        stroke_shape(i2, "RightUpperArmHi", [(286.0, 102.0), (278.0, 118.0), (272.0, 130.0)], 2.8, HIGHLIGHT, 2.6),
        smooth_shape(i2, "RightUpperArmShape", upper_arm_pts, skin_fill("RightUpperArm", 84, 140, SKIN, x0=312, x1=268)),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 2. Near (Right) Seated Wide-Stance Leg (Screen-Left Foreground)
def near_right_leg_rig():
    """Seated right leg extending forward-left from hip (276, 172) -> knee (308, 198) -> ankle (300, 276) -> bare foot on FLOOR = 300.0."""
    ind = "        "
    i2 = ind + "    "

    # 1. Bare Right Foot planted at (300, 276..298) facing forward toward the viewer
    foot_pts = [
        (292.0, 274.0), (305.0, 274.0), (309.5, 286.0),
        (313.0, 295.5), (308.5, 298.5), (299.0, 298.8),
        (291.0, 297.5), (289.5, 292.0), (290.5, 282.0),
    ]
    # 2. Right Lower Leg / Shin & Calf (knee y = 194 down to ankle y = 278)
    shin_pts = [
        (292.0, 194.0), (305.0, 191.0), (315.5, 196.0),
        (316.5, 214.0), (313.5, 236.0), (308.0, 258.0), (305.0, 276.0),
        (292.0, 276.0), (290.0, 256.0), (286.5, 234.0), (286.0, 212.0),
    ]
    # 3. Right Thigh in Dark Compression Shorts + Sculpted Quadriceps (hip (262, 162) -> knee (314, 198))
    shorts_right_pts = [
        (262.0, 154.0), (294.0, 156.0), (312.0, 166.0),
        (304.0, 182.0), (274.0, 184.0), (258.0, 172.0),
    ]
    thigh_right_pts = [
        (264.0, 168.0), (292.0, 166.0), (312.0, 178.0),
        (316.0, 192.0), (306.0, 201.0), (290.0, 198.0),
        (271.0, 186.0), (261.0, 176.0),
    ]

    return "\n".join([
        f'{ind}<Node name="NearRightLeg">',

        # 1. Bare Right Foot & Sculpted Toes on FLOOR = 300.0
        stroke_shape(i2, "RightToe1", [(294.0, 293.0), (293.5, 297.5)], 0.9, CORE_SHADOW, 0.2),
        stroke_shape(i2, "RightToe2", [(298.0, 293.0), (298.0, 298.2)], 0.9, CORE_SHADOW, 0.2),
        stroke_shape(i2, "RightToe3", [(302.5, 293.0), (303.0, 298.2)], 0.9, CORE_SHADOW, 0.2),
        stroke_shape(i2, "RightToe4", [(307.0, 292.5), (308.0, 297.8)], 0.9, CORE_SHADOW, 0.2),
        stroke_shape(i2, "RightFootInstepHi", [(298.0, 276.0), (300.0, 286.0), (303.0, 293.0)], 2.6, HIGHLIGHT, 2.2),
        stroke_shape(i2, "RightFootSoleSh", [(290.5, 296.5), (300.0, 298.2), (311.5, 296.5)], 2.0, CORE_SHADOW, 1.5),
        smooth_shape(i2, "RightFootShape", foot_pts, skin_fill("RightFoot", 274, 299, SKIN, x0=311, x1=290)),

        # 2. Right Lower Leg (Tibialis Anterior, Tibia Crest & Medial Gastrocnemius)
        ellipse_shape(i2, "RightMedialMalleolus", 304.5, 273.5, 3.8, 4.8, solid("RMalleolus", "FFCBD5E1")),
        ellipse_shape(i2, "RightLateralMalleolus", 292.5, 274.5, 3.8, 4.8, solid("LMalleolus", "FF94A3B8")),
        stroke_shape(i2, "RightTibiaCrest", [(302.0, 202.0), (300.0, 236.0), (298.5, 270.0)], 1.4, SOFT_SHADOW, 0.8),
        stroke_shape(i2, "RightMedialCalfLine", [(308.0, 206.0), (311.0, 226.0), (305.5, 248.0)], 1.2, CORE_SHADOW, 0.7),
        stroke_shape(i2, "RightShinHi", [(298.0, 204.0), (296.5, 236.0), (296.0, 266.0)], 3.2, HIGHLIGHT, 3.0),
        stroke_shape(i2, "RightShinSh", [(289.0, 208.0), (288.5, 238.0), (291.5, 268.0)], 3.5, CORE_SHADOW, 3.2),
        smooth_shape(i2, "RightShinShape", shin_pts, skin_fill("RightShin", 191, 276, SKIN, x0=315, x1=286)),

        # 3. Right Thigh & Compression Shorts
        stroke_shape(i2, "RightQuadSulcus1", [(276.0, 172.0), (292.0, 182.0), (304.0, 192.0)], 1.4, CORE_SHADOW, 0.8),
        stroke_shape(i2, "RightQuadSulcus2", [(286.0, 169.0), (301.0, 179.0), (310.0, 189.0)], 1.2, SOFT_SHADOW, 0.7),
        stroke_shape(i2, "RightThighHi", [(280.0, 171.0), (296.0, 180.0), (307.0, 190.0)], 3.4, HIGHLIGHT, 3.0),
        stroke_shape(i2, "RightThighSh", [(266.0, 176.0), (282.0, 188.0), (296.0, 196.0)], 3.6, CORE_SHADOW, 3.2),
        smooth_shape(i2, "RightThighShape", thigh_right_pts, skin_fill("RightThigh", 166, 201, SKIN, x0=314, x1=262)),
        stroke_shape(i2, "RightShortsHem", [(263.0, 176.0), (282.0, 181.0), (304.0, 178.0)], 1.5, "99020617", 0.5),
        stroke_shape(i2, "RightShortsHi", [(268.0, 162.0), (286.0, 166.0), (300.0, 172.0)], 3.6, "26FFFFFF", 3.0),
        smooth_shape(i2, "RightShortsShape", shorts_right_pts, skin_fill("RightShorts", 154, 184, SHORTS, x0=310, x1=258)),

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 3. Working Left Forearm, Brachioradialis & 3D Double-Plate Dumbbell
def working_forearm_and_dumbbell_rig():
    """Pivoting left forearm with activated Brachioradialis (scale = 0.88), supinated grip hand, and 3D cast-iron double-plate dumbbell."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "

    fa_id, br_id, db_id = nid(), nid(), nid()
    # 1. Forearm node at braced elbow (rotates & foreshortens smoothly from elbow -> wrist)
    key_double(fa_id, 13, lambda p: p["elbow"][0])
    key_double(fa_id, 14, lambda p: p["elbow"][1])
    key_double(fa_id, 15, lambda p: p["fa_rot"])
    key_double(fa_id, 16, lambda p: p["fa_sx"])
    key_double(br_id, 14, lambda p: p["brach_y"])
    # 2. 3D Dumbbell & Supinated Hand node at wrist in world space (zero shear, stays upright!)
    key_double(db_id, 13, lambda p: p["wrist"][0])
    key_double(db_id, 14, lambda p: p["wrist"][1])
    key_double(db_id, 15, lambda p: p["db_rot"])
    p0 = POSES[0]

    fa_len = FOREARM_REST_LEN  # 58.3 px

    # Sculpted Forearm silhouette (0 .. fa_len)
    fa_pts = [
        (-6.0, 0.0), (-3.5, -8.2), (14.0, -9.8), (32.0, -7.8), (48.0, -5.2),
        (fa_len + 2.0, 0.0), (48.0, 5.2), (32.0, 7.8), (14.0, 9.8), (-3.5, 8.2),
    ]
    # Activated Brachioradialis (scale = 0.88): symmetric fusiform belly shifted by brach_y (-3.0 at r=0 -> +3.6 at r=1)
    # so it stays on the front-right (+X_screen) radial border at both full extension and peak flexion!
    brachioradialis_pts = [
        (0.0, -4.4), (10.0, -5.2), (26.0, -4.5), (44.0, -2.0),
        (44.0, 2.0), (26.0, 4.5), (10.0, 5.2), (0.0, 4.4),
    ]

    # 3D Cast-Iron Double-Plate Dumbbell materials (matching reference illustration)
    plate_face = f'<Fill name="DBFaceFill">{grad("DBFaceGrad", -10, -24, 10, 24, "FF334155", "FF090D16")}</Fill>'
    plate_rim = f'<Fill name="DBRimFill">{grad("DBRimGrad", -10, -24, 10, 24, "FF475569", "FF0F172A")}</Fill>'
    plate_edge = '<Stroke thickness="1.0" name="DBEdge"><SolidColor colorValue="FF64748B" name="DBEdgeCol"/></Stroke>'
    collar_fill = f'<Fill name="DBCollarFill">{grad("DBCollarGrad", 0, -5, 0, 5, "FFF8FAFC", "FF64748B")}</Fill>'

    def double_plate_stack(name, cx_inner, cx_outer, dir_sign):
        """Double cast-iron weight plates (inner larger plate + outer slightly smaller plate) with 3D rim thickness."""
        parts = []
        if dir_sign > 0:
            # Outer spinlock hub only visible on the right (+X, viewer-facing) side of RightDB
            parts.append(ellipse_shape(i3, f"{name}Spinlock", cx_outer + 2.8, 0.0, 3.6, 7.2, collar_fill + plate_edge))
        parts.extend([
            # Outer plate (w = 9.5, h = 28.0)
            ellipse_shape(i3, f"{name}OuterFace", cx_outer, 0.0, 9.5, 28.0, plate_face + plate_edge),
            ellipse_shape(i3, f"{name}OuterRim", cx_outer - dir_sign * 2.0, 0.0, 9.5, 28.0, plate_rim),
            # Inner main plate (w = 11.0, h = 33.0)
            ellipse_shape(i3, f"{name}InnerFace", cx_inner, 0.0, 11.0, 33.0, plate_face + plate_edge),
            ellipse_shape(i3, f"{name}InnerRim", cx_inner - dir_sign * 2.2, 0.0, 11.0, 33.0, plate_rim),
        ])
        return "\n".join(parts)

    # Supinated (underhand) left hand & 4 vertical curled fingers centered at x = -6.0..+6.0 between the inner plates
    palm_pts = [
        (-6.5, -3.5), (6.5, -3.5), (7.0, 5.2), (0.0, 7.2), (-7.0, 5.2),
    ]
    thumb_pts = [
        (2.5, -5.2), (7.2, -3.8), (7.5, 0.5), (3.0, 1.5), (1.0, -2.0),
    ]
    knuckles = [
        ellipse_shape(i3, f"LeftFinger{idx + 1}", dx, 0.5, 3.8, 9.8, skin_fill(f"LFing{idx + 1}", -5, 5, SKIN))
        for idx, dx in enumerate((-4.8, -1.6, 1.6, 4.8))
    ]
    finger_lines = [
        stroke_shape(i3, f"LeftFingerSep{idx + 1}", [(sx, -3.8), (sx, 4.5)], 0.9, CORE_SHADOW, 0.2)
        for idx, sx in enumerate((-3.2, 0.0, 3.2))
    ]

    return "\n".join([
        f'{ind}<Node name="WorkingForearmAndDumbbell">',

        # --- 1. 3D Cast-Iron Double-Plate Dumbbell & Centered Supinated Left Hand at Wrist ---
        f'{i2}<Node x="{f(p0["wrist"][0])}" y="{f(p0["wrist"][1])}" rotation="{f(p0["db_rot"])}" name="DumbbellAndHand" id="{db_id}">',
        # a) Right (+X, near/outer) double-plate stack at x = +11.5, +15.8 (in front of the right handle end)
        double_plate_stack("RightDB", 11.5, 15.8, 1.0),
        # b) Centered Supinated Hand / Fist (x = -6.5..+6.5) wrapping around the center of the handle bar
        *finger_lines,
        stroke_shape(i3, "LeftKnuckleHi", [(-4.8, -2.2), (0.0, -2.8), (4.8, -2.2)], 1.8, HIGHLIGHT, 1.5),
        smooth_shape(i3, "LeftThumbWrap", thumb_pts, skin_fill("LeftThumb", -5, 2, SKIN)),
        *knuckles,
        smooth_shape(i3, "LeftPalmCradle", palm_pts, skin_fill("LeftPalm", -4, 7, SKIN)),
        # c) Dark gunmetal steel handle bar spanning strictly between the inner plate hubs (x = -9.0 .. +9.0)
        stroke_shape(i3, "DBHandleCore", [(-9.0, 0.0), (9.0, 0.0)], 3.6, "FF64748B", 0.0, cap="butt"),
        stroke_shape(i3, "DBHandleSh", [(-9.0, 0.0), (9.0, 0.0)], 5.0, "FF1E293B", 0.0, cap="butt"),
        # d) Left (-X, far/inner) double-plate stack at x = -11.5, -15.8
        double_plate_stack("LeftDB", -11.5, -15.8, -1.0),
        f"{i2}</Node>",

        # --- 2. Pivoting Left Forearm & Activated Brachioradialis (scale = 0.88) ---
        f'{i2}<Node x="{f(p0["elbow"][0])}" y="{f(p0["elbow"][1])}" rotation="{f(p0["fa_rot"])}" scaleX="{f(p0["fa_sx"])}" name="WorkingLeftForearm" id="{fa_id}">',
        f'{i3}<Node y="{f(p0["brach_y"])}" name="BrachioradialisNode" id="{br_id}">',
        stroke_shape(i4, "BrachioradialisHi", [(6.0, 0.0), (22.0, 0.0), (36.0, 0.0)], 2.2, HIGHLIGHT, 2.0),
        stroke_shape(i4, "BrachioradialisFiber", [(4.0, -1.2), (20.0, -1.2), (35.0, -0.8)], 0.95, "737C2D12", 0.3),
        smooth_shape(i4, "BrachioradialisActivation", brachioradialis_pts, muscle_paint("Brachioradialis", 0.92, scale=0.88)),
        f"{i3}</Node>",
        stroke_shape(i3, "LeftForearmTendon", [(16.0, 0.0), (34.0, 0.0), (48.0, 0.0)], 1.2, SOFT_SHADOW, 0.8),
        stroke_shape(i3, "LeftForearmHi", [(10.0, -2.5), (28.0, -2.2), (44.0, -1.5)], 2.6, HIGHLIGHT, 2.5),
        stroke_shape(i3, "LeftForearmSh", [(10.0, 2.5), (28.0, 2.2), (44.0, 1.5)], 3.0, CORE_SHADOW, 2.8),
        smooth_shape(i3, "LeftForearmShape", fa_pts, skin_fill("LeftForearm", -10, 10, SKIN)),
        f"{i2}</Node>",

        # --- 3. Unscaled Rounded Elbow Joint Cap at Braced Elbow ---
        ellipse_shape(i2, "BracedElbowCap", p0["elbow"][0] - 0.5, p0["elbow"][1] - 1.0, 16.5, 14.5, skin_fill("ElbowCap", -7, 7, SKIN)),

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 4. Forward-Hinged Torso, Downward-Looking Head & Working Left Upper Arm
def torso_head_and_working_upper_arm_rig():
    """Forward-hinged torso (pectorals, 6-pack abs/obliques, deltoids), downward-looking 3/4 head, and braced working left upper arm (Biceps Short Head, Long Head & Brachialis)."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    head_id, bic_id = nid(), nid()
    key_double(head_id, 15, lambda p: p["head_rot"])
    key_double(bic_id, 13, lambda p: 362.0 + p["biceps_dx"])
    key_double(bic_id, 16, lambda p: p["biceps_sx"])
    key_double(bic_id, 17, lambda p: p["biceps_sy"])
    p0 = POSES[0]

    # --- A. Volumetric 3/4 Head at (372, 54..94) tilted downward-left looking at the working biceps ---
    # Local coordinates relative to Head pivot at (366.0, 74.0):
    head_pts = [
        (-8.0, -14.0), (4.0, -21.0), (18.0, -18.0),
        (25.0, -9.0), (24.5, 2.0), (19.5, 11.0),
        (16.5, 16.5), (12.0, 18.5), (9.0, 21.0),
        (2.5, 20.0), (-3.5, 14.0), (-8.5, 4.0),
    ]
    hair_pts = [
        (-4.0, -16.5), (4.5, -21.5), (18.5, -18.5), (25.5, -9.5),
        (24.5, 1.5), (18.5, 4.0), (16.5, -3.0), (10.5, -7.5), (1.0, -9.5),
    ]

    # --- B. Forward-Hinged Muscular Torso (hips ~(292, 168) up to right shoulder (312, 86) & left shoulder (362, 102)) ---
    neck_trap_pts = [
        (316.0, 76.0), (344.0, 71.0), (368.0, 76.0),
        (366.0, 98.0), (336.0, 102.0), (312.0, 88.0),
    ]
    torso_pts = [
        (306.0, 84.0), (336.0, 78.0), (364.0, 94.0),
        (358.0, 122.0), (338.0, 144.0), (320.0, 166.0),
        (286.0, 170.0), (266.0, 156.0), (278.0, 130.0), (294.0, 104.0),
    ]
    # Sculpted Right & Left Pectoralis Major plates on the forward-leaning chest
    pec_right_pts = [
        (304.0, 88.0), (332.0, 92.0), (329.0, 115.0),
        (314.0, 120.0), (298.0, 110.0),
    ]
    pec_left_pts = [
        (332.0, 92.0), (356.0, 98.0), (354.0, 121.0),
        (339.0, 124.0), (329.0, 115.0),
    ]
    # Left Anterior/Lateral Deltoid Cap at (362, 102) overlapping the top of the working left upper arm
    left_delt_pts = [
        (348.0, 86.0), (366.0, 88.0), (375.0, 100.0),
        (372.0, 115.0), (358.0, 118.0), (346.0, 106.0),
    ]

    # --- C. Braced Working Left Upper Arm (SHOULDER = (362, 104) -> ELBOW = (364, 166)) ---
    # Base Upper Arm & Triceps contour braced against the inner left thigh
    left_ua_pts = [
        (352.0, 102.0), (372.0, 102.0), (375.5, 124.0), (375.0, 148.0),
        (371.5, 166.0), (363.0, 170.0), (354.5, 165.0), (350.5, 144.0), (350.0, 120.0),
    ]
    # Relative to BicepsPeakNode at (362.0, 136.0):
    # 1. Biceps brachii (short head) (scale = 1.0): inner/medial belly on the left (-X) side of the upper arm
    biceps_short_pts = [
        (-10.5, -22.0), (-1.5, -23.0), (0.5, -6.0), (-0.5, 16.0),
        (-5.5, 26.0), (-10.5, 18.0), (-12.2, 0.0),
    ]
    # 2. Biceps brachii (long head) (scale = 1.0): outer/lateral peak belly on the right (+X) upper-middle aspect
    biceps_long_pts = [
        (-1.0, -21.0), (8.2, -18.0), (10.8, -3.0), (7.5, 14.0),
        (1.5, 22.0), (-1.2, 12.0), (-0.5, -5.0),
    ]
    # 3. Brachialis (scale = 0.92): deep fusiform belly on the lower-outer (+X) border between biceps long head and triceps
    brachialis_pts = [
        (5.5, -4.0), (11.5, 2.0), (12.5, 15.0), (8.8, 26.0),
        (3.0, 24.0), (3.5, 10.0),
    ]

    sculpt_plate = (
        '<Fill name="TorsoPlateFill"><SolidColor colorValue="1F0F172A" name="TorsoPlateCol"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="TorsoPlateEdge"><SolidColor colorValue="450F172A" name="TorsoPlateEdgeCol"/></Stroke>'
    )

    return "\n".join([
        f'{ind}<Node name="TorsoHeadAndWorkingUpperArm">',

        # --- 1. Volumetric 3/4 Downward-Looking Head (366, 74) ---
        f'{i2}<Node x="366" y="74" rotation="{f(p0["head_rot"])}" name="DownwardHead" id="{head_id}">',
        smooth_shape(i3, "HairCap", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", -6, -21, 24, 2, "FF334155", "FF0F172A")}</Fill>'),
        ellipse_shape(i3, "RightEar", 4.5, -1.5, 4.5, 7.2, solid("Ear", "FFCBD5E1")),
        stroke_shape(i3, "EarHelix", [(4.2, -3.5), (5.2, -1.5), (4.0, 0.5)], 0.9, SOFT_SHADOW, 0.2),
        stroke_shape(i3, "BrowAndEyeShadow", [(12.5, 8.5), (17.5, 10.5)], 1.5, CORE_SHADOW, 0.6),
        stroke_shape(i3, "CheekHi", [(8.0, 5.0), (14.5, 8.0)], 2.2, HIGHLIGHT, 2.0),
        stroke_shape(i3, "JawlineSh", [(1.0, 15.0), (8.5, 19.5)], 1.6, CORE_SHADOW, 0.8),
        smooth_shape(i3, "HeadShape", head_pts, skin_fill("Head", -21, 21, SKIN, x0=25, x1=-8)),
        f"{i2}</Node>",

        # --- 2. Left Deltoid Cap (overlapping the top origin of the working left upper arm) ---
        stroke_shape(i2, "LeftDeltFiber1", [(356.0, 92.0), (358.0, 104.0), (356.0, 114.0)], 1.1, SOFT_SHADOW, 0.5),
        stroke_shape(i2, "LeftDeltFiber2", [(364.0, 92.0), (366.0, 104.0), (364.0, 114.0)], 1.1, SOFT_SHADOW, 0.5),
        stroke_shape(i2, "LeftDeltHi", [(354.0, 91.0), (364.0, 93.0), (370.0, 103.0)], 2.8, HIGHLIGHT, 2.6),
        smooth_shape(i2, "LeftDeltoidCap", left_delt_pts, skin_fill("LeftDelt", 86, 118, SKIN, x0=375, x1=346)),

        # --- 3. Forward-Hinged Torso (Pectorals, 6-Pack Abs, Obliques & Upper Trapezius/Neck) ---
        stroke_shape(i2, "SternumFurrow", [(332.0, 92.0), (329.0, 116.0), (314.0, 148.0)], 1.6, CORE_SHADOW, 0.8),
        stroke_shape(i2, "AbRow1", [(302.0, 124.0), (322.0, 128.0), (338.0, 128.0)], 1.2, CORE_SHADOW, 0.7),
        stroke_shape(i2, "AbRow2", [(294.0, 138.0), (315.0, 142.0), (330.0, 141.0)], 1.2, CORE_SHADOW, 0.7),
        stroke_shape(i2, "AbLateralLineR", [(298.0, 118.0), (290.0, 136.0), (284.0, 154.0)], 1.3, CORE_SHADOW, 0.8),
        stroke_shape(i2, "PecRightHi", [(308.0, 95.0), (324.0, 99.0), (322.0, 112.0)], 3.2, HIGHLIGHT, 3.0),
        stroke_shape(i2, "PecLeftHi", [(336.0, 99.0), (350.0, 104.0), (348.0, 116.0)], 2.8, HIGHLIGHT, 2.8),
        smooth_shape(i2, "PectoralisRight", pec_right_pts, sculpt_plate),
        smooth_shape(i2, "PectoralisLeft", pec_left_pts, sculpt_plate),
        stroke_shape(i2, "ClavicleLineR", [(308.0, 86.0), (332.0, 91.0)], 1.5, HIGHLIGHT, 1.2),
        stroke_shape(i2, "ClavicleLineL", [(334.0, 91.0), (358.0, 94.0)], 1.4, HIGHLIGHT, 1.2),
        stroke_shape(i2, "NeckSCM", [(358.0, 80.0), (342.0, 88.0), (333.0, 92.0)], 1.4, CORE_SHADOW, 0.8),
        smooth_shape(i2, "NeckAndTraps", neck_trap_pts, skin_fill("NeckTrap", 71, 102, SKIN, x0=368, x1=312)),
        smooth_shape(i2, "TorsoShape", torso_pts, skin_fill("Torso", 78, 170, SKIN, x0=364, x1=266)),

        # --- 4. Braced Working Left Upper Arm: Biceps Short Head, Long Head & Brachialis ---
        f'{i2}<Node x="{f(362.0 + p0["biceps_dx"])}" y="136" scaleX="{f(p0["biceps_sx"])}" scaleY="{f(p0["biceps_sy"])}" name="BicepsPeakNode" id="{bic_id}">',
        # Inter-head anatomical septum dividing Short Head (-X inner) and Long Head (+X outer)
        stroke_shape(i3, "BicepsSeptumLine", [(-0.8, -19.0), (-0.2, -2.0), (-0.5, 15.0)], 1.2, "99881337", 0.5),
        stroke_shape(i3, "BicepsShortHi", [(-6.5, -14.0), (-6.8, 0.0), (-5.5, 14.0)], 2.2, HIGHLIGHT, 2.0),
        stroke_shape(i3, "BicepsLongHi", [(4.2, -12.0), (5.5, 0.0), (3.8, 12.0)], 2.2, HIGHLIGHT, 2.0),
        stroke_shape(i3, "BrachialisHi", [(8.2, 4.0), (9.0, 14.0), (6.8, 22.0)], 1.8, HIGHLIGHT, 1.6),
        # 3. Brachialis (scale = 0.92, distal-lateral belly between biceps long head & triceps)
        smooth_shape(i3, "BrachialisActivation", brachialis_pts, muscle_paint("Brachialis", 0.92, scale=0.92)),
        # 2. Biceps brachii — long head (scale = 1.0, outer/lateral peak)
        smooth_shape(i3, "BicepsLongHeadActivation", biceps_long_pts, muscle_paint("BicepsLong", 0.95, scale=1.0)),
        # 1. Biceps brachii — short head (scale = 1.0, inner/medial belly)
        smooth_shape(i3, "BicepsShortHeadActivation", biceps_short_pts, muscle_paint("BicepsShort", 0.95, scale=1.0)),
        f"{i2}</Node>",
        stroke_shape(i2, "LeftUpperArmSh", [(371.0, 114.0), (373.0, 138.0), (370.0, 160.0)], 3.0, CORE_SHADOW, 2.8),
        smooth_shape(i2, "WorkingLeftUpperArmShape", left_ua_pts, skin_fill("LeftUpperArm", 102, 170, SKIN, x0=375, x1=350)),

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 5. Far (Left) Wide-Stance Leg (Screen-Right Side)
def far_left_leg_rig():
    """Seated left leg extending outward-right from pelvis/hip (316, 168) -> knee (396, 188) -> prominent inner calf -> bare left foot at (388, 276)."""
    ind = "        "
    i2 = ind + "    "

    # 1. Bare Left Foot planted at (382..424, 266..282) angled outward to the right
    foot_left_pts = [
        (381.0, 264.0), (394.0, 263.5), (408.0, 271.0),
        (422.5, 276.5), (424.0, 281.0), (414.0, 282.5),
        (396.0, 280.5), (382.5, 279.0), (379.5, 272.0),
    ]
    # 2. Left Lower Leg / Prominent Inner Medial Gastrocnemius Calf Belly (knee (396, 188) -> ankle (388, 268))
    calf_left_pts = [
        (380.0, 188.0), (396.0, 184.0), (405.5, 192.0),
        (403.5, 214.0), (398.5, 238.0), (394.0, 265.0),
        (381.5, 266.0), (380.5, 244.0), (372.5, 224.0), (371.5, 204.0),
    ]
    gastroc_inner_pts = [
        (378.0, 194.0), (392.0, 194.0), (394.0, 214.0),
        (387.0, 232.0), (376.0, 228.0), (372.0, 210.0),
    ]
    # 3. Left Thigh & Pelvis Shorts extending outward-right from (296, 164) to knee (404, 190)
    thigh_left_pts = [
        (318.0, 164.0), (356.0, 166.0), (388.0, 174.0), (404.0, 184.0),
        (402.0, 196.0), (380.0, 195.0), (344.0, 192.0), (314.0, 184.0),
    ]
    pelvis_shorts_pts = [
        (264.0, 148.0), (318.0, 152.0), (348.0, 162.0),
        (340.0, 190.0), (298.0, 188.0), (260.0, 176.0),
    ]

    calf_sculpt = (
        '<Fill name="LCalfSculptFill"><SolidColor colorValue="1F0F172A" name="LCalfSculptCol"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="LCalfSculptEdge"><SolidColor colorValue="420F172A" name="LCalfSculptEdgeCol"/></Stroke>'
    )

    return "\n".join([
        f'{ind}<Node name="FarLeftLeg">',

        # 1. Bare Left Foot angled outward-right
        stroke_shape(i2, "LeftFootArchHi", [(388.0, 268.0), (404.0, 274.0), (418.0, 278.0)], 2.2, HIGHLIGHT, 1.8),
        stroke_shape(i2, "LeftFootSoleSh", [(382.0, 278.0), (402.0, 280.5), (422.0, 281.0)], 2.0, CORE_SHADOW, 1.6),
        smooth_shape(i2, "LeftFootShape", foot_left_pts, skin_fill("LeftFoot", 263, 283, SKIN_FAR, x0=422, x1=380)),

        # 2. Left Lower Leg & Prominent Inner Medial Gastrocnemius Belly
        ellipse_shape(i2, "LeftMedialMalleolus", 385.5, 263.5, 3.8, 4.8, solid("LMedMalleolus", "FFCBD5E1")),
        stroke_shape(i2, "LeftGastrocHi", [(380.0, 202.0), (382.0, 216.0), (384.0, 226.0)], 3.2, HIGHLIGHT, 3.0),
        stroke_shape(i2, "LeftShinHi", [(396.0, 196.0), (395.0, 226.0), (391.0, 256.0)], 2.6, HIGHLIGHT, 2.4),
        smooth_shape(i2, "LeftGastrocInner", gastroc_inner_pts, calf_sculpt),
        smooth_shape(i2, "LeftCalfShape", calf_left_pts, skin_fill("LeftCalf", 184, 266, SKIN_FAR, x0=405, x1=372)),

        # 3. Left Thigh (Vastus Medialis & Sartorius) & Pelvis Compression Shorts
        stroke_shape(i2, "LeftThighSulcus", [(342.0, 174.0), (368.0, 180.0), (392.0, 186.0)], 1.3, CORE_SHADOW, 0.8),
        stroke_shape(i2, "LeftThighHi", [(346.0, 170.0), (372.0, 176.0), (394.0, 182.0)], 3.2, HIGHLIGHT, 2.8),
        stroke_shape(i2, "LeftThighSh", [(338.0, 188.0), (366.0, 191.0), (390.0, 193.0)], 3.4, CORE_SHADOW, 3.0),
        smooth_shape(i2, "LeftThighShape", thigh_left_pts, skin_fill("LeftThigh", 164, 196, SKIN_FAR, x0=404, x1=314)),
        stroke_shape(i2, "LeftShortsHem", [(338.0, 162.0), (344.0, 176.0), (338.0, 189.0)], 1.4, "99020617", 0.5),
        smooth_shape(i2, "PelvisShortsShape", pelvis_shorts_pts, skin_fill("PelvisShorts", 148, 190, SHORTS_FAR, x0=348, x1=260)),

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 6. 3D Flat Weight Bench Rig
def flat_bench_rig():
    """3D isometric flat weight bench extending from back-left (130, 174) to front-right (356, 194) with white/silver steel frame."""
    ind = "        "
    i2 = ind + "    "

    steel_front = f'<Fill name="SteelFrontFill">{grad("SteelFrontGrad", 150, 180, 360, 286, "FFF8FAFC", "FFCBD5E1")}</Fill>'
    steel_side = f'<Fill name="SteelSideFill">{grad("SteelSideGrad", 150, 180, 360, 286, "FF94A3B8", "FF475569")}</Fill>'
    steel_edge = '<Stroke thickness="0.9" join="round" name="SteelEdge"><SolidColor colorValue="FF475569" name="SteelEdgeCol"/></Stroke>'
    pad_top = f'<Fill name="PadTopFill">{grad("PadTopGrad", 130, 166, 356, 194, "FF334155", "FF1E293B")}</Fill>'
    pad_side = f'<Fill name="PadSideFill">{grad("PadSideGrad", 130, 174, 356, 202, "FF1E293B", "FF090D16")}</Fill>'
    rubber_fill = solid("BenchRubber", "FF090D16")

    # 1. Padded Cushion Top & 3D Beveled Side/Front Skirt (x = 128..356, y = 166..200)
    cushion_top_pts = [
        (128.0, 172.0), (156.0, 166.0), (354.0, 182.0), (332.0, 190.0),
    ]
    cushion_side_pts = [
        (128.0, 172.0), (332.0, 190.0), (354.0, 182.0),
        (354.0, 194.0), (332.0, 201.0), (128.0, 182.0),
    ]

    # 2. Angled Front Steel Leg ((318, 196) -> (344, 284)) & Black Rubber Foot Pad
    front_leg_front = [
        (316.0, 196.0), (328.0, 195.0), (344.0, 284.0), (332.0, 285.0),
    ]
    front_leg_side = [
        (328.0, 195.0), (334.0, 193.0), (350.0, 282.0), (344.0, 284.0),
    ]
    front_foot_pad = [
        (328.0, 283.0), (354.0, 281.0), (356.0, 286.0), (330.0, 287.5),
    ]

    # 3. Lower Horizontal Steel Cross-Beam ((166, 226) -> (336, 256)) & Under-Bench Frame Rail
    cross_beam_front = [
        (166.0, 224.0), (336.0, 252.0), (336.0, 261.0), (166.0, 232.0),
    ]
    cross_beam_top = [
        (166.0, 224.0), (173.0, 221.0), (342.0, 249.0), (336.0, 252.0),
    ]
    under_rail_pts = [
        (156.0, 182.0), (324.0, 198.0), (324.0, 205.0), (156.0, 188.0),
    ]

    # 4. Rear Vertical Steel Post & T-Stabilizer Base on Left (x = 132..194, y = 182..258)
    rear_post_front = [
        (158.0, 182.0), (168.0, 183.0), (168.0, 248.0), (158.0, 248.0),
    ]
    rear_post_side = [
        (168.0, 183.0), (174.0, 181.0), (174.0, 246.0), (168.0, 248.0),
    ]
    rear_t_base = [
        (132.0, 252.0), (190.0, 242.0), (194.0, 248.0), (136.0, 258.0),
    ]
    rear_cap_left = [
        (130.0, 251.0), (140.0, 250.0), (142.0, 259.0), (132.0, 260.0),
    ]
    rear_cap_right = [
        (184.0, 241.0), (194.0, 240.0), (196.0, 249.0), (186.0, 250.0),
    ]

    return "\n".join([
        f'{ind}<Node name="FlatBenchRig">',
        # 1. Padded Cushion Top & 3D Beveled Side Skirt
        stroke_shape(i2, "CushionCrease", [(130.0, 172.5), (332.0, 190.0), (352.0, 182.5)], 1.2, "9964748B", 0.3),
        poly_shape(i2, "BenchCushionTop", cushion_top_pts, pad_top, radius=3.0),
        poly_shape(i2, "BenchCushionSide", cushion_side_pts, pad_side, radius=3.0),

        # 2. Angled Front Steel Leg & Rubber Foot Pad
        poly_shape(i2, "FrontFootPad", front_foot_pad, rubber_fill, radius=1.2),
        poly_shape(i2, "FrontLegFront", front_leg_front, steel_front + steel_edge, radius=1.0),
        poly_shape(i2, "FrontLegSide", front_leg_side, steel_side + steel_edge, radius=1.0),

        # 3. Under-Bench Frame Rail & Lower Horizontal Cross-Beam
        poly_shape(i2, "UnderBenchRail", under_rail_pts, steel_side + steel_edge, radius=1.0),
        poly_shape(i2, "CrossBeamFront", cross_beam_front, steel_front + steel_edge, radius=1.0),
        poly_shape(i2, "CrossBeamTop", cross_beam_top, steel_side + steel_edge, radius=1.0),

        # 4. Rear Vertical Post & T-Stabilizer Foot
        poly_shape(i2, "RearCapLeft", rear_cap_left, rubber_fill, radius=1.2),
        poly_shape(i2, "RearCapRight", rear_cap_right, rubber_fill, radius=1.2),
        poly_shape(i2, "RearTBase", rear_t_base, steel_front + steel_edge, radius=1.5),
        poly_shape(i2, "RearPostFront", rear_post_front, steel_front + steel_edge, radius=1.0),
        poly_shape(i2, "RearPostSide", rear_post_side, steel_side + steel_edge, radius=1.0),
        f"{ind}</Node>",
    ])


def shadow():
    ind = "        "
    return "\n".join([
        f'{ind}<Shape x="342" y="{f(FLOOR + 1)}" scaleX="1.35" scaleY="0.07" name="AthleteAndBenchShadow">\n'
        f'{ind}    <Ellipse width="180" height="180" name="ShadowEl"/>\n'
        f'{ind}    <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="90" endY="0" name="ShadowGrad">'
        f'<GradientStop colorValue="99000000" position="0"/><GradientStop colorValue="4D000000" position="0.6"/>'
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


bracing_arm_xml = bracing_right_arm_rig()
near_leg_xml = near_right_leg_rig()
working_forearm_xml = working_forearm_and_dumbbell_rig()
torso_upper_arm_xml = torso_head_and_working_upper_arm_rig()
far_leg_xml = far_left_leg_rig()
bench_xml = flat_bench_rig()
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
    <!-- Seated Dumbbell Concentration Curl: 60 fps, 16:9 (640x360), generated by gen_concentration_curl.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="ConcentrationCurl" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- Foreground 1: Stationary Bracing Right Arm & Hand Cupping Right Knee -->
        {bracing_arm_xml}

        <!-- Foreground 2: Near (Right) Wide-Stance Leg -->
        {near_leg_xml}

        <!-- Mid-Foreground 3: Working Left Forearm (Brachioradialis), Supinated Hand & 3D Double-Plate Dumbbell -->
        {working_forearm_xml}

        <!-- Midground 4: Forward-Hinged Torso, Downward-Looking Head & Working Left Upper Arm (Biceps Short/Long Head & Brachialis) -->
        {torso_upper_arm_xml}

        <!-- Mid-Background 5: Far (Left) Wide-Stance Leg -->
        {far_leg_xml}

        <!-- Background Equipment 6: 3D Flat Weight Bench -->
        {bench_xml}

        <!-- Floor Shadow & Scenery -->
        {shd_xml}
        {scenery()}

        <StateMachine name="ConcentrationCurlSM" id="0:7">
            <StateMachineLayer name="Motion" id="0:8">
                <AnyState x="200" y="-120"/>
                <ExitState x="400" y="-120"/>
                <EntryState>
                    <StateTransition stateToId="0:12"/>
                </EntryState>
                <AnimationState x="200" animationId="0:60" id="0:12"/>
            </StateMachineLayer>
        </StateMachine>

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="concentration_curl" id="0:60">
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
    built = HERE / "build/concentration_curl.riv"
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
