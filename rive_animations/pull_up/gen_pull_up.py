#!/usr/bin/env python3
"""Generates rive_animations/pull_up/scene.rml (and optionally publishes).

16:9 (640x360, FLOOR = 300.0) 60 fps procedural Rive 7.3 animation for the
Pronated Wide-Grip Pull Up (`id: pull_up`), matching the 2-panel 3/4 rear-right
anatomical reference chart:
  - Camera: 3/4 rear-right isometric view showing our canonical CommunityFitness
    mannequin hanging from a 3D white/silver floor-mounted pull-up rack / power
    tower with two full-height vertical uprights (`x ~ 358` and `x ~ 438`),
    cantilevered horizontal top beams, and a wide dark-charcoal steel pull-up bar.
  - Grip: Stationary wide overhand (pronated, knuckles facing viewer) grip at
    `FAR_HAND = (224.0, 49.0)` and `NEAR_HAND = (338.0, 41.0)` with zero wrist drift.
  - Anatomy & Posture:
    - Sculpted 3/4 rear-right head (short dark hair cap, cranium, right ear,
      jawline profile), neck with activated Levator Scapulae.
    - Broad V-taper dorsal back with all 10 labeled muscles from the reference:
      1. Latissimus dorsi (Primary, deep crimson-red V-taper wings, `scale = 1.00`)
      2. Teres major (`scale = 0.94`)
      3. Teres minor (`scale = 0.86`)
      4. Infraspinatus (`scale = 0.86`)
      5. Trapezii (middle and lower) (`scale = 0.88`)
      6. Rhomboids (deep) (`scale = 0.84`)
      7. Levator scapulae (deep) (`scale = 0.80`)
      8. Posterior deltoid (`scale = 0.84`)
      9. Biceps brachii & Brachialis (`scale = 0.86`)
      10. Brachioradialis (`scale = 0.88`)
    - Sculpted glutes in dark compression shorts, posterior thighs (hamstrings),
      and sharply flexed knees (~70 deg) with sculpted gastrocnemius & soleus
      calves sweeping back-left and tucked bare feet hanging in the air.
  - Biomechanics (`r` in [0.0, 1.0], 168 frames / 2.8s @ 60 fps):
    - Dead Hang (`r = 0.0`, left panel): Arms extended overhead in a wide Y-hang
      to the bar, head between the upper arms (`y = 66..95`).
    - Chin-Over-Bar Peak (`r = 1.0`, right panel): Body rises by `48 px`
      (`body_dx = -2.0, body_dy = -48.0`) so the head (`y = 18..47`) and chin
      clearly clear above the horizontal bar (`y ~ 45`) while the elbows drive
      down and out to the sides (`elbow_far = (216, 86)`, `elbow_near = (342, 80)`).

Usage (from this directory):
    python3 gen_pull_up.py            # regenerate scene.rml
    python3 gen_pull_up.py --publish  # + build .riv, copy to assets, render thumbnail
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
ASSET_RIV = REPO / "assets/animations/pull_up.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/pull_up.png"

# 16:9 standard canvas
W, H = 640, 360
FLOOR = 300.0
FPS = 60

# Stationary Wide Overhand (Pronated) Hand Anchors on the Pull-Up Bar
# (Notice the bar slopes slightly up-right in 3/4 isometric perspective matching the reference)
FAR_HAND = (224.0, 49.0)   # Left (far) pronated hand on left side of bar
NEAR_HAND = (338.0, 41.0)  # Right (near) pronated hand on right side of bar

# Base Shoulder Coordinates in RisingBodyRoot Local Space (at r = 0.0, body_dx = 0, body_dy = 0)
FAR_SH_BASE = (254.0, 114.0)
NEAR_SH_BASE = (304.0, 110.0)

# Rest-Hang Reference Limb Lengths (at r = 0.0 wide Y-hang) for 3D Foreshortening Scale:
UPPER_ARM_FAR, FOREARM_FAR = 38.0, 36.5
UPPER_ARM_NEAR, FOREARM_NEAR = 39.5, 38.5

# Timeline (frames @60fps):
# 0..12: bottom dead-hang hold (r=0.0)
# 12..68: smooth concentric wide pull-up (r: 0.0 -> 1.0)
# 68..86: peak isometric hold with chin above the bar (r=1.0)
# 86..154: controlled eccentric lowering back to full hang (r: 1.0 -> 0.0)
# 154..168: bottom dead-hang hold (r=0.0)
HOLD_BOT_1 = 12
PULL_FRAMES = 56
HOLD_TOP = 18
LOWER_FRAMES = 68
HOLD_BOT_2 = 14
DURATION = HOLD_BOT_1 + PULL_FRAMES + HOLD_TOP + LOWER_FRAMES + HOLD_BOT_2  # 168 frames (2.8s)
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


def pull_progress(frame):
    """0.0 at bottom dead hang (Panel 1), 1.0 at peak chin-over-bar contraction (Panel 2)."""
    fr = frame % DURATION
    if fr <= HOLD_BOT_1:
        return 0.0
    fr -= HOLD_BOT_1
    if fr <= PULL_FRAMES:
        return EASE_UP(fr / PULL_FRAMES)
    fr -= PULL_FRAMES
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


def solve_foreshortened_arm(sh, el, hand, l1, l2):
    """3D-foreshortened Shoulder -> Elbow -> Stationary Hand solver in world space."""
    dx1, dy1 = el[0] - sh[0], el[1] - sh[1]
    d1 = math.hypot(dx1, dy1)
    ua_rot = math.atan2(dy1, dx1)
    ua_sx = max(0.38, d1 / l1)

    dx2, dy2 = hand[0] - el[0], hand[1] - el[1]
    d2 = math.hypot(dx2, dy2)
    fa_rot = math.atan2(dy2, dx2)
    fa_sx = d2 / l2
    return ua_rot, ua_sx, fa_rot, fa_sx


def pose(r):
    """Compute Wide-Grip Pronated Pull-Up pose at progress r in [0.0, 1.0]."""
    # 1. Rising Body translation:
    #    At r = 0.0: (0.0, 0.0) -> head at y = 66..95 (below bar at y ~ 45), tucked feet at y = 278
    #    At r = 1.0: (-2.0, -48.0) -> head at y = 18..47 (chin clearly above bar at y ~ 45!), tucked feet at y = 230
    body_dx = lerp(0.0, -2.0, r)
    body_dy = lerp(0.0, -48.0, r)

    # 2. World-space shoulder positions as the athlete rises toward the bar:
    #    r = 0.0: FAR_SH = (254.0, 114.0), NEAR_SH = (304.0, 110.0)
    #    r = 1.0: FAR_SH = (252.0, 66.0),  NEAR_SH = (302.0, 62.0)
    sh_far = (FAR_SH_BASE[0] + body_dx, FAR_SH_BASE[1] + body_dy)
    sh_near = (NEAR_SH_BASE[0] + body_dx, NEAR_SH_BASE[1] + body_dy)

    # 3. 3D-Foreshortened Pronated Wide-Grip Elbow Trajectories:
    #    In an overhand wide-grip pull-up, the elbows flare out laterally and drive down toward the ribs:
    #    - Near (Right) Elbow: (322, 76) at r=0 -> (338, 79) at r=0.5 -> (342, 79) at r=1.0
    #    - Far (Left) Elbow:   (237, 81) at r=0 -> (221, 85) at r=0.5 -> (216, 86) at r=1.0
    elbow_near = quad_interp_pt((322.0, 76.0), (338.0, 79.0), (342.0, 79.0), r)
    elbow_far = quad_interp_pt((237.0, 81.0), (221.0, 85.0), (216.0, 86.0), r)

    ua_far, ua_far_sx, fa_far, fa_far_sx = solve_foreshortened_arm(
        sh_far, elbow_far, FAR_HAND, UPPER_ARM_FAR, FOREARM_FAR
    )
    ua_near, ua_near_sx, fa_near, fa_near_sx = solve_foreshortened_arm(
        sh_near, elbow_near, NEAR_HAND, UPPER_ARM_NEAR, FOREARM_NEAR
    )

    # 4. Dynamic Latissimus Dorsi & Upper-Arm Flexor contraction bulge at peak pull-up
    lat_sx = lerp(1.00, 1.06, r)
    lat_sy = lerp(1.00, 0.95, r)
    biceps_bulge = lerp(1.00, 1.12, r)

    # 5. Dynamic floor shadow contraction as the athlete pulls higher off the floor
    shd_sx = lerp(1.02, 0.76, r)

    return {
        "r": r,
        "body_dx": body_dx,
        "body_dy": body_dy,
        "sh_far": sh_far,
        "sh_near": sh_near,
        "elbow_far": elbow_far,
        "elbow_near": elbow_near,
        "ua_far": ua_far,
        "ua_far_sx": ua_far_sx,
        "fa_far": fa_far,
        "fa_far_sx": fa_far_sx,
        "ua_near": ua_near,
        "ua_near_sx": ua_near_sx,
        "fa_near": fa_near,
        "fa_near_sx": fa_near_sx,
        "lat_sx": lat_sx,
        "lat_sy": lat_sy,
        "biceps_bulge": biceps_bulge,
        "shd_sx": shd_sx,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(pull_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = ("ua_far", "fa_far", "ua_near", "fa_near")
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
TENDON_NEAR = ("FFF8FAFC", "FFE2E8F0", "FFCBD5E1")
TENDON_FAR = ("FFE2E8F0", "FFCBD5E1", "FF94A3B8")
SHORTS = ("FF334155", "FF1E293B", "FF0F172A")
SHORTS_FAR = ("FF263142", "FF151E2E", "FF090D16")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "520F172A"

# Dynamic orange-to-crimson muscle activation palette (matching reference chart)
MUSCLE_LOW = (0xBF, 0xF9, 0x73, 0x16)       # warm glowing orange at bottom dead hang
MUSCLE_HIGH = (0xF5, 0xF4, 0x3F, 0x5E)      # intense crimson-red at peak pull-up contraction
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
    """Activation curve: warm orange at dead hang (0.28) -> intense crimson at chin-over-bar peak (1.00)."""
    base = 0.28 + 0.72 * (p["r"] ** 0.85)
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


# ---------------------------------------------------------------- 3D Pull-Up Power Tower / Rack & Stationary Pronated Hands
def pull_up_rack_rig():
    """3D Isometric Pull-Up Power Tower / Rack matching the reference illustration:
    - Two full-height vertical white/silver square-tube uprights (`x ~ 356` and `x ~ 432`)
      extending from `y = 22` down to `FLOOR = 300`, with floor base feet.
    - Horizontal cantilevered white/silver top support arms extending up-left from
      the vertical uprights to support the pull-up bar via drop brackets.
    - Wide dark-charcoal steel pull-up bar sloping in 3/4 perspective from
      left end `(202, 51)` to right end `(368, 39)` with rubber grip sleeves.
    """
    ind = "        "
    i2 = ind + "    "

    post_front = f'<Fill name="PostFront">{grad("PostFrontG", 350, 20, 445, 300, "FFF8FAFC", "FFCBD5E1")}</Fill>'
    post_side = f'<Fill name="PostSide">{grad("PostSideG", 350, 20, 445, 300, "FFCBD5E1", "FF64748B")}</Fill>'
    beam_top = f'<Fill name="BeamTop">{grad("BeamTopG", 210, 36, 440, 62, "FFF8FAFC", "FFCBD5E1")}</Fill>'
    beam_side = f'<Fill name="BeamSide">{grad("BeamSideG", 210, 40, 440, 68, "FFCBD5E1", "FF64748B")}</Fill>'
    steel_edge = '<Stroke thickness="0.9" join="round" name="RackRim"><SolidColor colorValue="FF94A3B8" name="RackRimCol"/></Stroke>'
    rubber_foot = (
        f'<Fill name="RubberFootFill">{grad("RFootG", 0, 286, 0, 302, "FF334155", "FF0F172A")}</Fill>'
        '<Stroke thickness="0.8" join="round" name="RFootRim"><SolidColor colorValue="FF475569" name="RFootRimCol"/></Stroke>'
    )

    bar_shaft = (
        f'<Fill name="BarShaftFill">{grad("BarShaftG", 200, 38, 370, 54, "FF334155", "FF0F172A")}</Fill>'
        '<Stroke thickness="0.9" join="round" name="BarShaftRim"><SolidColor colorValue="FF64748B" name="BarShaftRimCol"/></Stroke>'
    )
    foam_grip = (
        f'<Fill name="FoamGripFill">{grad("FoamGripG", 200, 38, 370, 54, "FF1E293B", "FF090D16")}</Fill>'
        '<Stroke thickness="0.85" join="round" name="FoamGripRim"><SolidColor colorValue="FF475569" name="FoamGripRimCol"/></Stroke>'
    )
    end_cap = solid("BarEndCap", "FF090D16")

    return "\n".join([
        f'{ind}<Node name="PullUpRackRig">',

        # 1. Wide 3/4-Perspective Dark-Charcoal Steel Pull-Up Bar (`(202, 50.8) -> (366, 39.2)`)
        ellipse_shape(i2, "LeftBarEndCap", 202.0, 50.8, 5.2, 5.2, end_cap),
        ellipse_shape(i2, "RightBarEndCap", 366.0, 39.2, 5.2, 5.2, end_cap),
        # Outer rubber grip sleeves where the hands hold the bar (`FAR_HAND=(224,49)` and `NEAR_HAND=(338,41)`)
        poly_shape(
            i2, "LeftGripSleeve",
            [(203.0, 48.2), (242.0, 45.4), (242.4, 50.6), (203.4, 53.4)],
            foam_grip, radius=1.6,
        ),
        poly_shape(
            i2, "RightGripSleeve",
            [(320.0, 39.8), (365.0, 36.6), (365.4, 41.8), (320.4, 45.0)],
            foam_grip, radius=1.6,
        ),
        stroke_shape(i2, "BarTopSpecHi", [(206.0, 49.0), (284.0, 43.5), (362.0, 38.0)], 1.2, "73F8FAFC", 0.3),
        poly_shape(
            i2, "MainPullUpBar",
            [(202.0, 48.5), (366.0, 36.8), (366.4, 41.6), (202.4, 53.2)],
            bar_shaft, radius=1.8,
        ),

        # 2. Under-Bar Drop Brackets connecting the bar to the horizontal cantilever beams
        poly_shape(i2, "LeftDropBracket", [(246.0, 47.5), (252.0, 47.0), (252.0, 57.5), (246.0, 58.0)], beam_side + steel_edge, radius=1.0),
        poly_shape(i2, "RightDropBracket", [(312.0, 42.8), (318.0, 42.4), (318.0, 53.0), (312.0, 53.4)], beam_side + steel_edge, radius=1.0),

        # 3. Left (Far) & Right (Near) Horizontal Cantilevered Support Arms extending to the vertical posts
        poly_shape(i2, "LeftCantileverSide", [(240.0, 56.5), (354.0, 49.0), (354.0, 55.5), (240.0, 62.5)], beam_side + steel_edge, radius=1.2),
        poly_shape(i2, "LeftCantileverTop", [(240.0, 53.5), (354.0, 46.0), (354.0, 49.5), (240.0, 57.0)], beam_top + steel_edge, radius=1.2),
        poly_shape(i2, "RightCantileverSide", [(306.0, 52.0), (428.0, 44.0), (428.0, 51.0), (306.0, 58.5)], beam_side + steel_edge, radius=1.2),
        poly_shape(i2, "RightCantileverTop", [(306.0, 49.0), (428.0, 41.0), (428.0, 44.5), (306.0, 52.5)], beam_top + steel_edge, radius=1.2),

        # 4. Left (Far) & Right (Near) Tall Vertical Floor-to-Ceiling Uprights (`y = 22..298`)
        #    Far upright at x = 352..368
        poly_shape(i2, "FarPostFoot", [(346.0, 290.0), (374.0, 290.0), (376.0, 296.5), (344.0, 296.5)], rubber_foot, radius=2.0),
        poly_shape(i2, "FarPostSide", [(363.0, 24.0), (369.0, 26.0), (369.0, 293.0), (363.0, 291.0)], post_side + steel_edge, radius=1.2),
        poly_shape(i2, "FarPostFront", [(352.0, 24.0), (363.0, 24.0), (363.0, 291.0), (352.0, 291.0)], post_front + steel_edge, radius=1.5),
        #    Near upright at x = 426..444
        poly_shape(i2, "NearPostFoot", [(420.0, 294.0), (450.0, 294.0), (452.0, 300.5), (418.0, 300.5)], rubber_foot, radius=2.0),
        poly_shape(i2, "NearPostSide", [(438.0, 20.0), (445.0, 22.0), (445.0, 297.0), (438.0, 295.0)], post_side + steel_edge, radius=1.2),
        poly_shape(i2, "NearPostFront", [(426.0, 20.0), (438.0, 20.0), (438.0, 295.0), (426.0, 295.0)], post_front + steel_edge, radius=1.5),

        f"{ind}</Node>",
    ])


def stationary_pronated_hands_rig():
    """Stationary Overhand (Pronated) Hands Gripping the Pull-Up Bar at FAR_HAND=(224,49.0) and NEAR_HAND=(338,41.0).
    In a 3/4 rear-right view with a pronated grip, the dorsal back of the hand and knuckles face the viewer,
    wrapping over the top of the bar while the thumb hooks underneath."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    out = [f'{ind}<Node name="StationaryPronatedHands">']
    for prefix, is_near, (hx, hy) in (("Near", True, NEAR_HAND), ("Far", False, FAR_HAND)):
        skin = SKIN if is_near else SKIN_FAR
        inward = -1.0 if is_near else 1.0
        # Dorsal hand & knuckles wrapping over the top of the bar
        dorsal_hand_pts = [
            (-6.8, -4.6), (6.5, -5.2), (7.6, 1.2), (5.8, 5.4), (-6.2, 5.0),
        ]
        # Thumb hooking underneath the inner side of the bar
        thumb_pts = [
            (inward * 3.5, 2.2), (inward * 8.2, 1.5),
            (inward * 7.8, 5.5), (inward * 2.5, 5.8),
        ]
        out.extend([
            f'{i2}<Node x="{f(hx)}" y="{f(hy)}" name="{prefix}PronatedHand">',
            smooth_shape(i3, f"{prefix}ThumbHook", thumb_pts, skin_fill(prefix + "Thumb", 1, 6, skin)),
            stroke_shape(i3, f"{prefix}Tendon1", [(-3.2, -4.2), (-2.8, 4.4)], 0.85, SOFT_SHADOW, 0.2),
            stroke_shape(i3, f"{prefix}Tendon2", [(0.2, -4.4), (0.5, 4.6)], 0.85, SOFT_SHADOW, 0.2),
            stroke_shape(i3, f"{prefix}Tendon3", [(3.5, -4.4), (3.8, 4.4)], 0.85, SOFT_SHADOW, 0.2),
            stroke_shape(i3, f"{prefix}KnuckleRidgeHi", [(-4.8, -2.8), (4.8, -3.2)], 2.0, HIGHLIGHT, 1.6),
            smooth_shape(i3, f"{prefix}DorsalHand", dorsal_hand_pts, skin_fill(prefix + "DorsalHand", -5, 6, skin)),
            f"{i2}</Node>",
        ])
    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3D-Foreshortened Pronated Wide-Grip Arms
def arm_rig(prefix, is_near):
    """3D-Foreshortened Arm (Shoulder -> Elbow -> Stationary Hand on Bar) with Posterior Deltoid, Biceps Brachii, Brachialis, and Brachioradialis."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "

    skin = SKIN if is_near else SKIN_FAR
    sh_key = "sh_near" if is_near else "sh_far"
    el_key = "elbow_near" if is_near else "elbow_far"
    ua_len = UPPER_ARM_NEAR if is_near else UPPER_ARM_FAR
    fa_len = FOREARM_NEAR if is_near else FOREARM_FAR
    ua_key = "ua_near" if is_near else "ua_far"
    ua_sx_key = "ua_near_sx" if is_near else "ua_far_sx"
    fa_key = "fa_near" if is_near else "fa_far"
    fa_sx_key = "fa_near_sx" if is_near else "fa_far_sx"

    delt_id, ua_id, fa_id, bic_id = nid(), nid(), nid(), nid()
    # 1. Deltoid cap node at shoulder (unscaled scaleX = 1.0 so shoulder cap stays round)
    key_double(delt_id, 13, lambda p: p[sh_key][0])
    key_double(delt_id, 14, lambda p: p[sh_key][1])
    key_double(delt_id, 15, lambda p: p[ua_key])
    # 2. Upper arm node at shoulder (foreshortened scaleX = dist(SH, EL) / ua_len)
    key_double(ua_id, 13, lambda p: p[sh_key][0])
    key_double(ua_id, 14, lambda p: p[sh_key][1])
    key_double(ua_id, 15, lambda p: p[ua_key])
    key_double(ua_id, 16, lambda p: p[ua_sx_key])
    key_double(bic_id, 17, lambda p: p["biceps_bulge"])
    # 3. Forearm node at elbow in world space (foreshortened scaleX = dist(EL, HAND) / fa_len, zero shear!)
    key_double(fa_id, 13, lambda p: p[el_key][0])
    key_double(fa_id, 14, lambda p: p[el_key][1])
    key_double(fa_id, 15, lambda p: p[fa_key])
    key_double(fa_id, 16, lambda p: p[fa_sx_key])
    p0 = POSES[0]

    # Along the Shoulder->Elbow vector:
    # For Near (Right) arm (pointing up-right): -y is superior/biceps side, +y is inferior/triceps side.
    # For Far (Left) arm (pointing up-left): +y is superior/biceps side, -y is inferior/triceps side.
    flex_sign = -1.0 if is_near else 1.0
    ext_sign = -flex_sign

    # 1. Base Upper Arm Silhouette (0 .. ua_len)
    ua_pts = [
        (-6.5, 0.0), (-4.5, -8.8), (7.5, -9.6), (ua_len * 0.55, -9.0), (ua_len - 3.5, -6.4),
        (ua_len + 4.0, 0.0), (ua_len - 3.5, 6.4), (ua_len * 0.55, 9.0), (7.5, 9.6), (-4.5, 8.8),
    ]

    # 2. Activated Biceps Brachii & Brachialis on the superior/flexor aspect (`flex_sign`)
    biceps_pts = [
        (8.0, flex_sign * 1.2),
        (ua_len * 0.50, flex_sign * 0.8),
        (ua_len - 3.5, flex_sign * 2.2),
        (ua_len - 5.5, flex_sign * 8.2),
        (ua_len * 0.50, flex_sign * 9.6),
        (9.0, flex_sign * 7.8),
    ]
    brachialis_pts = [
        (ua_len * 0.38, -flex_sign * 0.6),
        (ua_len - 2.0, flex_sign * 0.6),
        (ua_len - 3.0, flex_sign * 5.0),
        (ua_len * 0.42, flex_sign * 4.4),
    ]

    # 3. Sculpted Triceps Brachii (non-highlighted silver anatomical contour on `ext_sign` aspect matching the reference)
    triceps_sculpt_pts = [
        (8.0, ext_sign * 1.0),
        (ua_len * 0.52, ext_sign * 1.4),
        (ua_len - 4.5, ext_sign * 2.2),
        (ua_len - 6.5, ext_sign * 7.8),
        (ua_len * 0.48, ext_sign * 8.8),
        (9.0, ext_sign * 7.6),
    ]
    sculpt_plate = (
        '<Fill name="ArmSculptFill"><SolidColor colorValue="1F0F172A" name="ArmSculptCol"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="ArmSculptEdge"><SolidColor colorValue="420F172A" name="ArmSculptEdgeCol"/></Stroke>'
    )

    # 4. Sculpted Deltoid Cap + Activated Posterior Deltoid
    delt_pts = [
        (-8.0, 0.0), (-5.2, -8.4), (3.0, -9.6), (11.5, -6.8),
        (13.5, 0.0), (11.5, 6.8), (3.0, 9.6), (-5.2, 8.4),
    ]
    post_delt_pts = [
        (-7.0, ext_sign * 0.4),
        (2.0, ext_sign * 9.4),
        (12.0, ext_sign * 6.8),
        (13.2, ext_sign * 0.8),
        (3.0, -ext_sign * 1.6),
    ]

    # 5. Sculpted Forearm (0 .. fa_len) + Activated Brachioradialis along the proximal radial border
    fa_pts = [
        (-5.5, 0.0), (-3.5, -7.2), (fa_len * 0.35, -8.2), (fa_len - 4.5, -4.6),
        (fa_len + 3.5, 0.0), (fa_len - 4.5, 4.6), (fa_len * 0.35, 8.2), (-3.5, 7.2),
    ]
    brachioradialis_pts = [
        (-1.5, flex_sign * 0.6),
        (fa_len * 0.28, flex_sign * 1.0),
        (fa_len * 0.60, flex_sign * 1.8),
        (fa_len * 0.54, flex_sign * 5.2),
        (fa_len * 0.25, flex_sign * 6.8),
        (-1.2, flex_sign * 5.0),
    ]

    out = [
        f'{ind}<Node name="{prefix}Arm">',

        # --- 1. Unscaled Posterior Deltoid & Shoulder Cap at Shoulder Origin ---
        f'{i2}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" rotation="{f(p0[ua_key])}" name="{prefix}DeltoidNode" id="{delt_id}">',
        stroke_shape(i3, f"{prefix}PostDeltHi", [(1.0, ext_sign * 4.8), (9.0, ext_sign * 4.2)], 2.0, HIGHLIGHT, 1.8),
        stroke_shape(i3, f"{prefix}PostDeltFiber", [(-2.0, ext_sign * 3.4), (9.5, ext_sign * 3.6)], 0.9, "737C2D12", 0.3),
        smooth_shape(i3, f"{prefix}PosteriorDeltActivation", post_delt_pts, muscle_paint(prefix + "PostDelt", 0.9, scale=0.84)),
        stroke_shape(i3, f"{prefix}LateralDeltHi", [(1.0, flex_sign * 3.8), (9.0, flex_sign * 3.4)], 1.8, HIGHLIGHT, 1.8),
        smooth_shape(i3, f"{prefix}DeltoidCap", delt_pts, skin_fill(prefix + "Deltoid", -10, 10, skin)),
        f"{i2}</Node>",

        # --- 2. 3D-Foreshortened Upper Arm (Shoulder -> Elbow) ---
        f'{i2}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" rotation="{f(p0[ua_key])}" scaleX="{f(p0[ua_sx_key])}" name="{prefix}UpperArm" id="{ua_id}">',
        f'{i3}<Node scaleY="{f(p0["biceps_bulge"])}" name="{prefix}BicepsNode" id="{bic_id}">',
        stroke_shape(i4, f"{prefix}BicepsHi", [(9.5, flex_sign * 5.0), (ua_len - 5.5, flex_sign * 5.0)], 2.2, HIGHLIGHT, 2.0),
        smooth_shape(i4, f"{prefix}BrachialisActivation", brachialis_pts, muscle_paint(prefix + "Brachialis", 0.85, scale=0.86)),
        smooth_shape(i4, f"{prefix}BicepsActivation", biceps_pts, muscle_paint(prefix + "Biceps", 0.9, scale=0.86)),
        f"{i3}</Node>",
        stroke_shape(i3, f"{prefix}TricepsLongHi", [(9.5, ext_sign * 4.5), (ua_len - 6.0, ext_sign * 4.2)], 2.0, HIGHLIGHT, 1.8),
        smooth_shape(i3, f"{prefix}TricepsSculpt", triceps_sculpt_pts, sculpt_plate),
        stroke_shape(i3, f"{prefix}HumerusGroove", [(8.0, 0.0), (ua_len - 4.0, 0.0)], 1.2, CORE_SHADOW, 0.6),
        smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UpperArm", -10, 10, skin)),
        f"{i2}</Node>",

        # --- 3. 3D-Foreshortened Forearm & Brachioradialis (Elbow -> Stationary Hand on Bar) ---
        f'{i2}<Node x="{f(p0[el_key][0])}" y="{f(p0[el_key][1])}" rotation="{f(p0[fa_key])}" scaleX="{f(p0[fa_sx_key])}" name="{prefix}Forearm" id="{fa_id}">',
        stroke_shape(i3, f"{prefix}BrachioradialisHi", [(3.0, flex_sign * 4.4), (fa_len * 0.55, flex_sign * 4.0)], 2.0, HIGHLIGHT, 1.8),
        smooth_shape(i3, f"{prefix}BrachioradialisActivation", brachioradialis_pts, muscle_paint(prefix + "Brachiorad", 0.9, scale=0.88)),
        stroke_shape(i3, f"{prefix}ForearmGroove", [(3.0, 0.0), (fa_len * 0.65, 0.0)], 1.1, CORE_SHADOW, 0.6),
        stroke_shape(i3, f"{prefix}ForearmExtensorHi", [(4.0, ext_sign * 3.6), (fa_len - 7.0, ext_sign * 2.6)], 2.2, HIGHLIGHT, 2.2),
        smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -8, 8, skin)),
        f"{i2}</Node>",

        f"{ind}</Node>",
    ]
    return "\n".join(out)


# ---------------------------------------------------------------- Rising Body: Dorsal Back, Glutes, Flexed-Knee Hanging Legs & 3/4 Head
def flexed_hanging_leg_rig(prefix, is_near):
    """Posterior Thigh (Hamstrings), Sharply Flexed Knee (~70 deg), Swept-Back Calf (Gastrocnemius/Soleus) & Tucked Bare Foot matching the Pull-Up reference."""
    ind = "            "
    i2 = ind + "    "

    skin = SKIN if is_near else SKIN_FAR
    tendon_pal = TENDON_NEAR if is_near else TENDON_FAR
    shorts_pal = SHORTS if is_near else SHORTS_FAR

    # 3/4 rear-right perspective offset aligned with GlutesShorts (x = 256..304):
    # Near (Right) leg at x = 290.0, y = 0.0; Far (Left) leg at x = 271.0, y = -3.0
    ox = 290.0 if is_near else 271.0
    oy = 0.0 if is_near else -3.0

    # 1. Upper Leg / Posterior Thigh angling slightly down-right from glutes (y = 180) to flexed knee (8.0, 236.0)
    thigh_shorts_pts = [
        (-13.2, 180.0), (0.0, 178.0), (14.0, 180.0),
        (16.2, 196.0), (2.0, 198.5), (-12.5, 196.0),
    ]
    thigh_pts = [
        (-12.2, 184.0), (0.5, 182.0), (13.8, 184.0),
        (16.2, 198.0), (17.5, 215.0), (16.8, 229.0), (13.5, 237.5),
        (4.5, 239.0), (-4.0, 235.0), (-6.8, 224.0), (-9.8, 210.0), (-11.8, 197.0),
    ]

    # 2. Sharply Flexed Lower Leg / Calf sweeping back-left and slightly down from knee `(6, 234)` to ankle `(-34, 256)`
    calf_pts = [
        (11.5, 230.0), (14.5, 236.5), (7.5, 242.5),
        (-4.0, 248.5), (-18.0, 253.5), (-32.0, 257.5),
        (-36.5, 254.0), (-34.5, 246.5), (-22.0, 240.0),
        (-9.0, 231.5), (2.5, 228.5),
    ]
    gastroc_upper_pts = [
        (7.5, 229.5), (1.0, 229.0), (-10.0, 232.0), (-21.0, 239.5),
        (-16.0, 245.5), (-3.5, 241.5), (6.5, 236.5),
    ]
    gastroc_lower_pts = [
        (11.5, 234.5), (6.5, 241.5), (-5.0, 247.5), (-18.0, 252.0),
        (-21.0, 246.0), (-8.0, 240.5), (4.0, 235.5),
    ]
    achilles_pts = [
        (-18.5, 241.5), (-16.0, 251.5), (-32.5, 257.0), (-36.0, 253.5), (-34.0, 247.0),
    ]

    # 3. Plantarflexed Bare Foot hanging down from the ankle `(-34, 252)` to toes `(-29, 282)`
    foot_pts = [
        (-37.5, 246.5), (-31.0, 248.0), (-26.5, 256.5), (-24.5, 269.5),
        (-26.0, 280.5), (-30.5, 282.5), (-34.8, 278.0), (-36.5, 266.0), (-39.5, 253.5),
    ]

    calf_muscle_paint = (
        '<Fill name="CalfSculptFill"><SolidColor colorValue="1F0F172A" name="CalfSculptCol"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="CalfSculptEdge"><SolidColor colorValue="420F172A" name="CalfSculptEdgeCol"/></Stroke>'
    )

    out = [f'{ind}<Node x="{f(ox)}" y="{f(oy)}" name="{prefix}HangingLeg">']

    # 1. Upper Leg: Shorts Hem, Hamstrings (Biceps Femoris & Semitendinosus) & IT Band
    out.append(stroke_shape(i2, f"{prefix}ShortsHem", [(-12.2, 195.5), (2.0, 197.5), (15.8, 195.5)], 1.3, "80020617", 0.4))
    out.append(smooth_shape(i2, f"{prefix}ThighShorts", thigh_shorts_pts, skin_fill(prefix + "Shorts", 178, 199, shorts_pal, x0=16, x1=-13)))
    out.append(stroke_shape(i2, f"{prefix}HamstringSulcus", [(1.0, 198.0), (3.5, 216.0), (5.5, 232.0)], 1.4, CORE_SHADOW, 0.8))
    if is_near:
        out.append(stroke_shape(i2, f"{prefix}ITBandGroove", [(10.5, 198.0), (12.8, 216.0), (12.5, 232.0)], 1.2, SOFT_SHADOW, 0.7))
        out.append(stroke_shape(i2, f"{prefix}ThighHi", [(6.2, 200.0), (8.2, 217.0), (8.8, 231.0)], 3.0, HIGHLIGHT, 2.8))
    out.append(stroke_shape(i2, f"{prefix}ThighSh", [(-5.5, 200.0), (-3.2, 217.0), (-1.2, 231.0)], 3.4, CORE_SHADOW, 3.0))
    out.append(smooth_shape(i2, f"{prefix}ThighShape", thigh_pts, skin_fill(prefix + "Thigh", 182, 240, skin, x0=17, x1=-12)))

    # 2. Swept-Back Lower Leg (drawn in front of the flexed knee in 3/4 rear view!)
    out.append(ellipse_shape(i2, f"{prefix}LateralMalleolus", -32.0, 252.5, 3.8, 3.8, solid(prefix + "Malleolus", "FF94A3B8")))
    out.append(stroke_shape(i2, f"{prefix}AchillesHi", [(-20.0, 247.5), (-31.5, 252.0)], 1.4, "59FFFFFF", 1.0))
    out.append(smooth_shape(i2, f"{prefix}AchillesTendon", achilles_pts, calf_muscle_paint))
    out.append(stroke_shape(i2, f"{prefix}CalfInterSulcus", [(5.5, 234.0), (-6.5, 239.5), (-18.5, 245.5)], 1.3, CORE_SHADOW, 0.7))
    out.append(stroke_shape(i2, f"{prefix}UpperCalfHi", [(0.0, 231.5), (-10.0, 235.5), (-17.5, 241.0)], 2.4, HIGHLIGHT, 2.2))
    out.append(stroke_shape(i2, f"{prefix}LowerCalfHi", [(4.0, 238.5), (-6.0, 244.5), (-15.5, 249.0)], 2.2, HIGHLIGHT, 2.2))
    out.append(smooth_shape(i2, f"{prefix}GastrocLower", gastroc_lower_pts, calf_muscle_paint))
    out.append(smooth_shape(i2, f"{prefix}GastrocUpper", gastroc_upper_pts, calf_muscle_paint))
    out.append(smooth_shape(i2, f"{prefix}CalfBase", calf_pts, skin_fill(prefix + "Calf", 228, 258, skin, x0=14, x1=-36)))

    # 3. Plantarflexed Bare Foot hanging at the ankle
    out.append(stroke_shape(i2, f"{prefix}FootArchHi", [(-30.0, 252.0), (-27.0, 266.0), (-27.5, 278.5)], 1.8, HIGHLIGHT, 1.5))
    out.append(stroke_shape(i2, f"{prefix}FootSoleSh", [(-36.5, 254.0), (-34.5, 268.0), (-31.5, 279.5)], 2.2, CORE_SHADOW, 1.6))
    out.append(smooth_shape(i2, f"{prefix}HangingFoot", foot_pts, skin_fill(prefix + "Foot", 246, 283, skin, x0=-24, x1=-39)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def dorsal_torso_glutes_head_rig():
    """Sculpted 3/4 Rear-Right V-Taper Dorsal Back with all labeled dorsal muscles:
    Latissimus dorsi, Teres major, Teres minor, Infraspinatus, Trapezii (middle and lower),
    Rhomboids (deep), and Levator scapulae (deep), plus Glutes in Shorts and 3/4 Head."""
    ind = "            "
    i2 = ind + "    "
    i3 = i2 + "    "

    lat_id = nid()
    key_double(lat_id, 16, lambda p: p["lat_sx"])
    key_double(lat_id, 17, lambda p: p["lat_sy"])
    p0 = POSES[0]

    # 1. Sculpted Glutes in Dark Compression Shorts (y = 162..195, aligned with x = 256..304)
    glutes_shorts_pts = [
        (260.0, 162.5), (279.0, 161.5), (301.0, 163.5),
        (305.5, 177.0), (302.5, 191.5), (286.5, 195.0),
        (270.0, 193.0), (257.5, 188.0), (255.5, 174.5),
    ]

    # 2. Broad V-Taper Dorsal Torso Silhouette (neck base y = 102 down to waist y = 165)
    torso_pts = [
        (269.0, 103.0), (281.0, 101.0), (294.5, 103.5),
        (311.5, 112.5), (315.5, 128.5), (307.5, 147.5), (300.0, 164.5),
        (279.0, 166.5), (260.5, 163.5), (257.5, 147.5), (250.5, 128.0), (253.5, 113.0),
    ]

    # 3. Activated Dorsal Back Muscles:
    #    a) Latissimus Dorsi Right (Near) & Left (Far) V-taper wings (relative to (280, 139))
    lat_r_pts = [
        (-1.0, -4.0), (14.0, -14.5), (31.5, -14.5), (33.0, -2.0),
        (24.5, 13.5), (12.0, 22.0), (-1.0, 26.5),
    ]
    lat_l_pts = [
        (-2.0, -4.0), (-15.0, -14.0), (-27.0, -14.0), (-27.5, -3.0),
        (-21.5, 11.5), (-11.0, 20.0), (-2.0, 25.5),
    ]
    #    b) Teres Major Right (Near) & Left (Far) cylindrical bundles at the upper-outer border of the lats (relative to (280, 139))
    teres_major_r_pts = [
        (13.0, -18.5), (26.0, -21.5), (32.5, -14.0), (26.0, -9.0), (13.0, -11.0),
    ]
    teres_major_l_pts = [
        (-13.0, -18.5), (-23.5, -21.5), (-28.0, -14.5), (-22.5, -9.5), (-13.0, -11.5),
    ]
    #    c) Teres Minor Right & Left oblique rotator-cuff bands just superior to Teres Major (relative to (280, 139))
    teres_minor_r_pts = [
        (12.5, -23.0), (24.5, -25.5), (28.5, -20.5), (14.5, -18.0),
    ]
    teres_minor_l_pts = [
        (-12.5, -23.0), (-22.5, -25.0), (-25.5, -20.5), (-14.0, -18.0),
    ]
    #    d) Infraspinatus Right & Left triangular scapular fossa plates (in Torso coords)
    infraspinatus_r_pts = [
        (283.5, 110.5), (303.5, 109.5), (305.5, 117.5), (292.5, 121.0), (283.0, 117.5),
    ]
    infraspinatus_l_pts = [
        (257.5, 110.5), (274.0, 111.5), (274.5, 118.0), (265.0, 121.0), (256.5, 117.5),
    ]
    upper_scapula_r_pts = [
        (291.5, 103.5), (306.5, 108.5), (304.5, 112.0), (288.5, 111.0),
    ]
    upper_scapula_l_pts = [
        (255.5, 109.5), (268.5, 103.5), (270.0, 111.0), (256.5, 112.5),
    ]
    #    e) Rhomboids (deep) between Middle/Lower Trapezius and Scapula
    rhomboid_r_pts = [
        (282.0, 118.5), (293.5, 120.5), (291.5, 131.5), (281.0, 129.5),
    ]
    rhomboid_l_pts = [
        (265.5, 120.5), (276.0, 118.5), (276.0, 129.5), (266.5, 131.0),
    ]
    #    f) Middle Trapezius & Lower Trapezius flanking the median spinal furrow
    mid_trap_pts = [
        (269.0, 102.5), (279.5, 100.5), (291.5, 103.0),
        (294.5, 114.5), (287.0, 124.0), (279.0, 126.0), (271.0, 124.0), (264.0, 114.5),
    ]
    lower_trap_pts = [
        (271.5, 122.0), (279.0, 124.0), (286.5, 122.0),
        (284.5, 138.0), (279.0, 151.0), (273.5, 138.0),
    ]
    #    g) Levator Scapulae (deep) at the lateral superior neck/scapular border
    levator_l_pts = [
        (268.5, 92.5), (272.5, 93.0), (268.0, 107.5), (262.5, 106.0),
    ]
    levator_r_pts = [
        (287.5, 92.5), (292.0, 93.0), (296.5, 105.5), (291.0, 107.0),
    ]
    #    h) Thoracolumbar Fascia & Erector Spinae pillars at the lower back (y = 142..164)
    erector_r_pts = [
        (279.5, 141.0), (290.5, 143.0), (293.0, 163.5), (279.0, 164.5),
    ]
    erector_l_pts = [
        (267.5, 143.0), (278.0, 141.0), (278.5, 164.5), (265.5, 163.0),
    ]
    sculpt_plate = (
        '<Fill name="SculptPlateFill"><SolidColor colorValue="1F0F172A" name="SculptPlateCol"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="SculptPlateEdge"><SolidColor colorValue="450F172A" name="SculptPlateEdgeCol"/></Stroke>'
    )

    # 4. Sculpted 3/4 Rear-Right Head & Neck (y = 66..95 in local space -> rises by -48 px to y = 18..47 at r = 1.0, clearing above the bar!)
    neck_pts = [
        (270.5, 88.0), (290.5, 88.0), (293.5, 105.0), (267.5, 105.0),
    ]
    head_pts = [
        (268.0, 74.5), (280.0, 67.0), (292.5, 71.5),
        (295.5, 79.0), (297.2, 84.0), (295.2, 88.0), (294.8, 93.0),
        (288.5, 95.0), (276.0, 92.5), (267.5, 84.5),
    ]
    hair_pts = [
        (267.5, 76.5), (271.0, 67.5), (283.0, 66.5), (293.0, 72.0),
        (291.0, 77.5), (284.0, 76.5), (277.0, 83.5), (268.5, 85.0),
    ]

    return "\n".join([
        f'{ind}<Node name="TorsoGlutesAndHead">',

        # --- 1. Sculpted Glutes in Dark Compression Shorts ---
        stroke_shape(i2, "ShortsWaistband", [(260.5, 163.0), (280.0, 162.0), (300.5, 164.0)], 1.4, "80020617", 0.4),
        stroke_shape(i2, "GluteCleft", [(277.0, 164.5), (273.5, 178.0), (272.0, 192.0)], 2.2, "99020617", 0.8),
        stroke_shape(i2, "NearGluteHi", [(285.0, 168.5), (292.0, 177.0), (287.0, 188.0)], 3.8, "26FFFFFF", 3.2),
        stroke_shape(i2, "FarGluteHi", [(264.0, 168.5), (261.0, 177.0), (263.0, 185.0)], 2.8, "1FFFFFFF", 2.8),
        stroke_shape(i2, "GluteFoldNear", [(274.0, 192.5), (288.0, 194.5), (299.5, 191.0)], 1.8, "8C020617", 0.8),
        stroke_shape(i2, "GluteFoldFar", [(258.0, 187.5), (265.0, 191.5), (272.0, 191.0)], 1.6, "8C020617", 0.8),
        smooth_shape(i2, "GlutesShorts", glutes_shorts_pts, skin_fill("GlutesShorts", 162, 195, SHORTS, x0=302, x1=256)),

        # --- 2. Activated Dorsal Back Muscles (All Labeled Muscles from the Reference Chart) ---
        stroke_shape(i2, "MedianSpinalFurrow", [(279.0, 98.0), (279.0, 132.0), (278.5, 163.0)], 1.8, CORE_SHADOW, 0.8),
        stroke_shape(i2, "TrapDivisionLine", [(271.0, 123.0), (279.0, 125.0), (287.0, 123.0)], 1.1, "99881337", 0.4),
        stroke_shape(i2, "MidTrapFiberL", [(278.0, 108.5), (268.0, 113.5)], 0.9, "737C2D12", 0.3),
        stroke_shape(i2, "MidTrapFiberR", [(280.0, 108.5), (290.0, 113.5)], 0.9, "737C2D12", 0.3),
        smooth_shape(i2, "LowerTrapeziusActivation", lower_trap_pts, muscle_paint("LowerTrap", 0.9, scale=0.88)),
        smooth_shape(i2, "MiddleTrapeziusActivation", mid_trap_pts, muscle_paint("MidTrap", 0.9, scale=0.88)),
        smooth_shape(i2, "RhomboidRightActivation", rhomboid_r_pts, muscle_paint("RhomboidR", 0.85, scale=0.84)),
        smooth_shape(i2, "RhomboidLeftActivation", rhomboid_l_pts, muscle_paint("RhomboidL", 0.85, scale=0.84)),
        smooth_shape(i2, "InfraspinatusRightActivation", infraspinatus_r_pts, muscle_paint("InfraR", 0.85, scale=0.86)),
        smooth_shape(i2, "InfraspinatusLeftActivation", infraspinatus_l_pts, muscle_paint("InfraL", 0.85, scale=0.84)),
        smooth_shape(i2, "UpperScapulaRight", upper_scapula_r_pts, sculpt_plate),
        smooth_shape(i2, "UpperScapulaLeft", upper_scapula_l_pts, sculpt_plate),

        # Dynamic Flaring Latissimus Dorsi, Teres Major & Teres Minor Node centered at (280, 139)
        f'{i2}<Node x="280" y="139" scaleX="{f(p0["lat_sx"])}" scaleY="{f(p0["lat_sy"])}" name="LatAndTeresNode" id="{lat_id}">',
        stroke_shape(i3, "TeresRightHi", [(16.0, -16.0), (26.5, -15.0)], 2.0, HIGHLIGHT, 1.8),
        smooth_shape(i3, "TeresMinorRightActivation", teres_minor_r_pts, muscle_paint("TeresMinR", 0.85, scale=0.86)),
        smooth_shape(i3, "TeresMinorLeftActivation", teres_minor_l_pts, muscle_paint("TeresMinL", 0.85, scale=0.84)),
        smooth_shape(i3, "TeresMajorRightActivation", teres_major_r_pts, muscle_paint("TeresMajR", 0.95, scale=0.94)),
        smooth_shape(i3, "TeresMajorLeftActivation", teres_major_l_pts, muscle_paint("TeresMajL", 0.9, scale=0.92)),
        # Diagonal pennate striations & highlights on the sweeping Latissimus Dorsi wings
        stroke_shape(i3, "LatRightHi", [(12.0, -6.0), (21.5, 1.0), (14.5, 13.5)], 3.2, HIGHLIGHT, 3.0),
        stroke_shape(i3, "LatRightFiber1", [(2.0, 4.0), (15.0, -3.0), (27.0, -6.0)], 0.95, "737C2D12", 0.3),
        stroke_shape(i3, "LatRightFiber2", [(2.0, 13.5), (14.0, 5.5), (24.0, 1.5)], 0.95, "737C2D12", 0.3),
        stroke_shape(i3, "LatLeftFiber1", [(-3.0, 4.0), (-14.0, -3.0), (-23.5, -6.0)], 0.9, "737C2D12", 0.3),
        smooth_shape(i3, "LatRightActivation", lat_r_pts, muscle_paint("LatRight", 1.0, scale=1.00)),
        smooth_shape(i3, "LatLeftActivation", lat_l_pts, muscle_paint("LatLeft", 0.95, scale=0.96)),
        f"{i2}</Node>",

        # Serratus Anterior ribs + Erector Spinae & Thoracolumbar Fascia
        stroke_shape(i2, "SerratusRib1", [(304.5, 142.0), (311.5, 140.0)], 1.1, CORE_SHADOW, 0.5),
        stroke_shape(i2, "SerratusRib2", [(302.5, 147.5), (308.5, 145.5)], 1.1, CORE_SHADOW, 0.5),
        smooth_shape(i2, "ErectorRight", erector_r_pts, sculpt_plate),
        smooth_shape(i2, "ErectorLeft", erector_l_pts, sculpt_plate),
        stroke_shape(i2, "TorsoRightHi", [(290.0, 145.0), (294.0, 158.0)], 2.8, HIGHLIGHT, 2.5),
        stroke_shape(i2, "TorsoLeftSh", [(260.0, 145.0), (262.0, 159.0)], 3.2, CORE_SHADOW, 2.8),
        smooth_shape(i2, "TorsoBackShape", torso_pts, skin_fill("TorsoBack", 101, 167, SKIN, x0=314, x1=251)),

        # --- 3. Sculpted 3/4 Rear-Right Head, Neck & Levator Scapulae ---
        f'{i2}<Node name="HeadAndNeck">',
        smooth_shape(i3, "HairCap", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 269, 67, 291, 85, "FF334155", "FF0F172A")}</Fill>'),
        ellipse_shape(i3, "RightEar", 285.5, 83.0, 4.2, 7.0, solid("Ear", "FFCBD5E1")),
        stroke_shape(i3, "EarHelix", [(285.2, 81.0), (286.2, 83.0), (285.0, 85.0)], 0.9, SOFT_SHADOW, 0.2),
        stroke_shape(i3, "JawlineShadow", [(286.5, 92.0), (293.5, 93.0)], 1.4, CORE_SHADOW, 0.8),
        stroke_shape(i3, "HeadCrownHi", [(275.0, 70.0), (284.0, 69.0), (291.0, 73.0)], 2.6, HIGHLIGHT, 2.5),
        smooth_shape(i3, "HeadShape", head_pts, skin_fill("Head", 67, 95, SKIN, x0=297, x1=267)),
        smooth_shape(i3, "LevatorScapulaeLeft", levator_l_pts, muscle_paint("LevatorL", 0.8, scale=0.80)),
        smooth_shape(i3, "LevatorScapulaeRight", levator_r_pts, muscle_paint("LevatorR", 0.8, scale=0.80)),
        stroke_shape(i3, "NeckTrapCrease", [(276.0, 88.5), (277.0, 103.5)], 1.4, CORE_SHADOW, 0.8),
        stroke_shape(i3, "NeckSCMRight", [(286.5, 89.5), (289.5, 103.5)], 1.3, SOFT_SHADOW, 0.7),
        smooth_shape(i3, "NeckShape", neck_pts, skin_fill("Neck", 88, 105, SKIN, x0=292, x1=269)),
        f"{i2}</Node>",

        f"{ind}</Node>",
    ])


def rising_body_rig():
    """Master kinematic root for the rising torso, head, glutes, and flexed-knee hanging legs."""
    ind = "        "
    body_id = nid()
    key_double(body_id, 13, lambda p: p["body_dx"])
    key_double(body_id, 14, lambda p: p["body_dy"])
    p0 = POSES[0]

    return "\n".join([
        f'{ind}<Node x="{f(p0["body_dx"])}" y="{f(p0["body_dy"])}" name="RisingBodyRoot" id="{body_id}">',
        # 1. Sculpted Dorsal Torso (Activated Lats, Teres Major/Minor, Infraspinatus, Traps, Rhomboids, Levator Scapulae), Glutes & 3/4 Head
        dorsal_torso_glutes_head_rig(),
        # 2. Near (Right) Flexed-Knee Hanging Leg (in front of Far leg)
        flexed_hanging_leg_rig("Near", True),
        # 3. Far (Left) Flexed-Knee Hanging Leg (offset back-left in 3/4 perspective)
        flexed_hanging_leg_rig("Far", False),
        f"{ind}</Node>",
    ])


def shadow():
    ind = "        "
    shd_id = nid()
    key_double(shd_id, 16, lambda p: p["shd_sx"])
    p0 = POSES[0]
    return "\n".join([
        f'{ind}<Shape x="276" y="{f(FLOOR + 1)}" scaleX="{f(p0["shd_sx"])}" scaleY="0.065" name="HangingAthleteShadow" id="{shd_id}">\n'
        f'{ind}    <Ellipse width="160" height="160" name="ShadowEl"/>\n'
        f'{ind}    <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="80" endY="0" name="ShadowGrad">'
        f'<GradientStop colorValue="99000000" position="0"/><GradientStop colorValue="4D000000" position="0.6"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{ind}</Shape>",
        f'{ind}<Shape x="398" y="{f(FLOOR + 1)}" scaleX="1.15" scaleY="0.06" name="RackBaseShadow">\n'
        f'{ind}    <Ellipse width="150" height="150" name="RackShadowEl"/>\n'
        f'{ind}    <Fill name="RackShadowFill"><RadialGradient startX="0" startY="0" endX="75" endY="0" name="RackShadowGrad">'
        f'<GradientStop colorValue="8C000000" position="0"/><GradientStop colorValue="40000000" position="0.6"/>'
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
body_xml = rising_body_rig()
far_arm_xml = arm_rig("Far", False)
hands_xml = stationary_pronated_hands_rig()
rack_xml = pull_up_rack_rig()
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


rml = f"""<Rive version="7.3">
    <!-- Pronated Wide-Grip Pull Up: 60 fps, 16:9 (640x360), generated by gen_pull_up.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="PullUp" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- 1. Foreground: Near (Right) Pronated Arm (Posterior Delt, Biceps, Brachialis, Brachioradialis) -->
{near_arm_xml}

        <!-- 2. Midground: Rising Body (Dorsal Back with Lats/Teres/Infraspinatus/Traps/Rhomboids/Levator Scapulae, 3/4 Head, Glutes & Flexed-Knee Legs) -->
{body_xml}

        <!-- 3. Mid-Background: Far (Left) Pronated Arm + Stationary Pronated Hands on the Bar -->
{far_arm_xml}
{hands_xml}

        <!-- 4. Background Equipment: 3D Floor-Mounted Pull-Up Power Tower / Rack -->
{rack_xml}

        <!-- 5. Dynamic Floor Shadow & Scenery -->
{shd_xml}
{scenery()}

        <StateMachine name="PullUpSM" id="0:7">
            <StateMachineLayer name="Motion" id="0:8">
                <AnyState x="200" y="-120"/>
                <ExitState x="400" y="-120"/>
                <EntryState>
                    <StateTransition stateToId="0:12"/>
                </EntryState>
                <AnimationState x="200" animationId="0:60" id="0:12"/>
            </StateMachineLayer>
        </StateMachine>

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="pull_up" id="0:60">
{keyed_xml()}
        </LinearAnimation>
    </Artboard>
</Rive>
"""


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
            if "cap" in at and cap_map.get(at["cap"], 0) != 0:
                out.extend(prop_u(48, cap_map[at["cap"]]))
            if "join" in at and join_map.get(at["join"], 0) != 0:
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
    BUILD.mkdir(parents=True, exist_ok=True)
    ASSET_THUMB.parent.mkdir(parents=True, exist_ok=True)
    riv_bytes = _compile_rml_bytes(OUT)
    (BUILD / "pull_up.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (40, "frame_mid"), (76, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(680, 12, 270))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(rml, encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {len(keys)} keyed properties)")
    if "--publish" in sys.argv:
        publish()
