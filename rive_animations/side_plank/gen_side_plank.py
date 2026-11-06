#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360, FLOOR = 300.0) procedural Rive 7.3 scene for Side Plank (id: 'side_plank').

Uses our canonical 3/4 front-right CommunityFitness mannequin holding a strict Side Forearm Plank on FLOOR = 300.0:
  - Supported on the near (right) forearm planted on the studio floor mat directly beneath the right shoulder
    (`elbow = (414, 292)`, `shoulder_bot = (416, 198)`), with legs extended straight and feet stacked on the left
    (`x ~ 144`), and the far/top (left) hand resting on the upper hip (`(304, 188)`).
  - From r = 0.0 to r = 1.0, animates a controlled ~11 px hip-lift / isometric oblique brace into a rock-solid
    straight diagonal line from stacked ankles through hips to shoulders, with rhythmic breathing micro-tension.
  - Highlighted Target Muscle Groups (pulsing from warm orange #FFF97316 to intense crimson #FFF43F5E):
    1. External & Internal obliques (Primary lateral core movers bridging ribcage to pelvis)
    2. Rectus abdominis (6-pack ventral abdominal wall)
    3. Gluteus medius (Hip abductor stabilizing the bottom & top pelvis)
    4. Supporting Deltoid (Right shoulder stabilizer over the planted forearm)

Run:
    python3 rive_animations/side_plank/gen_side_plank.py            # writes scene.rml
    python3 rive_animations/side_plank/gen_side_plank.py --publish  # compiles .riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/side_plank.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/side_plank.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps side-plank hip-lift & isometric oblique pulse loop
STEP = 2

# Segment Lengths for 2-Bone IK (Hip -> Knee -> Ankle) for Bottom (Right) and Top (Left) Stacked Legs
L_THIGH_BOT = 76.0
L_SHIN_BOT = 74.0
L_THIGH_TOP = 76.0
L_SHIN_TOP = 74.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
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


EASE_LIFT = cubic_bezier(0.36, 0.0, 0.24, 1.0)
EASE_LOWER = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def side_plank_progress(frame):
    """Returns side-plank oblique hip-lift progress r in [0.0, 1.0] + subtle isometric breathing pulse across 160 frames:
    - 0..14:   Loaded lower hip hover before full lateral oblique lock (r = 0.0)
    - 14..54:  Concentric lateral oblique & gluteus medius hip lift into straight diagonal alignment (r: 0.0 -> 1.0)
    - 54..116: Peak isometric side-plank lock with 2 controlled oblique breathing pulses (r ~ 1.0)
    - 116..150: Controlled eccentric lowering back to baseline hover (r: 1.0 -> 0.0)
    - 150..160: Baseline hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 14:
        return 0.0, 0.0
    if fr <= 54:
        return EASE_LIFT((fr - 14) / 40.0), 0.0
    if fr <= 116:
        breath = math.sin(2.0 * math.pi * (fr - 54) / 62.0)
        return 1.0, breath
    if fr <= 150:
        return 1.0 - EASE_LOWER((fr - 116) / 34.0), 0.0
    return 0.0, 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def solve_leg_ik(hip, ankle, l1, l2):
    """2-bone IK from hip -> knee -> ankle for extended side-plank legs."""
    dx = ankle[0] - hip[0]
    dy = ankle[1] - hip[1]
    d = max(1.0, min(l1 + l2 - 0.6, math.hypot(dx, dy)))
    base_ang = math.atan2(dy, dx)
    cos_a = max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2.0 * l1 * d)))
    thigh_ang = base_ang - math.acos(cos_a)
    knee = (hip[0] + l1 * math.cos(thigh_ang), hip[1] + l1 * math.sin(thigh_ang))
    shin_ang = math.atan2(ankle[1] - knee[1], ankle[0] - knee[0])
    return thigh_ang, knee, shin_ang


def seg_xform(p0, p1, base_len):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ang = math.atan2(dy, dx)
    if ang < 0:
        ang += 2.0 * math.pi
    sc = max(0.45, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r_breath):
    """Compute 3/4 Side Forearm Plank transforms at (r, breath):
    - At r = 0.0: Pelvis/hips sit ~11 px lower (`hip_drop = +11.0`) with a slight lateral sag before full oblique lock.
    - At r = 1.0: Lateral obliques and gluteus medius drive the hips up into a rock-solid straight diagonal line from
      stacked ankles (`148, 280` & `146, 258`) through stacked hips (`286, 224` & `282, 200`) and ribcage (`354, 198`)
      to the supporting right shoulder (`416, 198`) directly over the planted right elbow (`414, 292`).
    """
    r, breath = r_breath
    hip_drop = lerp(11.0, 0.0, r) - 1.5 * breath
    torso_y = 198.0 + 0.72 * hip_drop
    torso_rot = math.radians(lerp(-4.2, 0.0, r) + 0.35 * breath)

    # Bottom (Right — supporting) & Top (Left — stacked above) Hips
    hip_bot = (286.0, 224.0 + hip_drop)
    hip_top = (282.0, 200.0 + hip_drop)

    # Stacked Ankles on the left (Bottom right foot planted on mat at y=298, Top left foot stacked on top of it)
    ankle_bot = (148.0, 272.0)
    ankle_top = (146.0, 250.0)

    knee_soft = lerp(3.5, 0.0, r)
    thigh_bot_ang, knee_bot, shin_bot_ang = solve_leg_ik(
        hip_bot, (ankle_bot[0] + knee_soft, ankle_bot[1] - 0.3 * knee_soft), L_THIGH_BOT, L_SHIN_BOT
    )
    thigh_top_ang, knee_top, shin_top_ang = solve_leg_ik(
        hip_top, (ankle_top[0] + knee_soft, ankle_top[1] - 0.3 * knee_soft), L_THIGH_TOP, L_SHIN_TOP
    )

    foot_bot_rot = math.radians(lerp(2.0, 6.0, r))
    foot_top_rot = math.radians(lerp(2.0, 6.0, r))

    # Supporting Bottom (Right) Upper Arm: pivots around planted Right Elbow (414, 292)
    ua_bot_rot = math.radians(lerp(-3.5, 0.0, r) + 0.25 * breath)

    # Top (Left) Arm resting hand on the upper (left) hip crest:
    sh_top = (406.0, 166.0 + 0.45 * hip_drop)
    elb_top = (356.0, 146.0 + 0.65 * hip_drop)
    hand_top = (302.0, 186.0 + 0.95 * hip_drop)
    ua_top_ang, ua_top_sc = seg_xform(sh_top, elb_top, 52.0)
    fa_top_ang, fa_top_sc = seg_xform(elb_top, hand_top, 64.0)

    return {
        "r": r,
        "breath": breath,
        "hip_drop": hip_drop,
        "torso_y": torso_y,
        "torso_rot": torso_rot,
        "hip_bot": hip_bot,
        "hip_top": hip_top,
        "ankle_bot": ankle_bot,
        "knee_bot": knee_bot,
        "thigh_bot_ang": thigh_bot_ang,
        "shin_bot_ang": shin_bot_ang,
        "foot_bot_rot": foot_bot_rot,
        "ankle_top": ankle_top,
        "knee_top": knee_top,
        "thigh_top_ang": thigh_top_ang,
        "shin_top_ang": shin_top_ang,
        "foot_top_rot": foot_top_rot,
        "ua_bot_rot": ua_bot_rot,
        "sh_top": sh_top,
        "elb_top": elb_top,
        "hand_top": hand_top,
        "ua_top_ang": ua_top_ang,
        "ua_top_sc": ua_top_sc,
        "fa_top_ang": fa_top_ang,
        "fa_top_sc": fa_top_sc,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(side_plank_progress(fr)) for fr in FRAMES}

_ANGLE_KEYS = (
    "torso_rot",
    "thigh_bot_ang",
    "shin_bot_ang",
    "foot_bot_rot",
    "thigh_top_ang",
    "shin_top_ang",
    "foot_top_rot",
    "ua_bot_rot",
    "ua_top_ang",
    "fa_top_ang",
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


def skin_fill(name, y0, y1, tones, x0=0, x1=0):
    return f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *tones, x0=x0, x1=x1)}</Fill>'


def skin_fill_outlined(name, y0, y1, tones, x0=0, x1=0, line=1.1, stroke_col="4D0F172A"):
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


# ---------------------------------------------------------------- 1. Supporting Near (Right) Forearm & Deltoid Post + Top (Left) Arm on Hip
def build_supporting_right_arm():
    """Near (Right) supporting forearm planted flat on the studio mat at (414, 292) -> (462, 294)
    with a vertical upper arm and glowing supporting Deltoid directly beneath the right shoulder."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    elbow_x, elbow_y = 414.0, 292.0
    ua_id = nid()
    key_double(ua_id, 15, lambda p: p["ua_bot_rot"])
    p0 = POSES[0]

    def delt_t(p):
        return 0.44 + 0.52 * (p["r"] ** 0.78) + 0.06 * abs(p["breath"])

    # Horizontal Forearm & Neutral Fist planted on the studio mat
    fa_pts = [
        (404.0, 283.0), (428.0, 282.0), (452.0, 285.0),
        (460.0, 292.0), (452.0, 298.5), (426.0, 299.0),
        (404.0, 297.0),
    ]
    fist_pts = [
        (452.0, 282.5), (468.0, 282.0), (472.0, 290.0),
        (468.0, 298.5), (452.0, 298.0),
    ]

    # Vertical Upper Arm & Supporting Deltoid Cap (relative to planted Elbow (414, 292))
    ua_pts = [
        (-11.0, -86.0), (11.0, -86.0), (13.0, -48.0),
        (10.0, -6.0), (6.0, 4.0), (-6.5, 4.0),
        (-10.5, -10.0), (-12.5, -50.0),
    ]
    delt_pts = [
        (-14.0, -92.0), (0.0, -100.0), (15.0, -90.0),
        (14.0, -64.0), (-1.0, -58.0), (-14.0, -68.0),
    ]
    active_delt_pts = [
        (-10.0, -92.0), (1.0, -98.0), (13.5, -88.0),
        (12.0, -66.0), (-1.0, -61.0), (-10.5, -70.0),
    ]

    return "\n".join([
        f'{ind}<Node name="SupportingRightForearmArm">',
        # 1. Planted Forearm & Fist on Floor Mat
        stroke_shape(i2, "RightFistKnuckle1", [(458.0, 286.0), (467.0, 286.0)], 0.95, SOFT_SHADOW, 0.0),
        stroke_shape(i2, "RightFistKnuckle2", [(458.0, 290.5), (467.0, 290.5)], 0.95, SOFT_SHADOW, 0.0),
        stroke_shape(i2, "RightForearmLine", [(412.0, 289.5), (434.0, 289.5), (452.0, 290.5)], 1.2, SOFT_SHADOW, 0.6),
        stroke_shape(i2, "RightForearmHi", [(412.0, 285.5), (434.0, 285.0), (452.0, 287.0)], 2.4, HIGHLIGHT, 2.5),
        stroke_shape(i2, "RightForearmSh", [(410.0, 296.0), (432.0, 296.5), (452.0, 296.5)], 3.0, CORE_SHADOW, 3.0),
        smooth_shape(i2, "PlantedRightFist", fist_pts, skin_fill_outlined("RightFist", 282, 299, SKIN, line=1.1)),
        smooth_shape(i2, "PlantedRightForearm", fa_pts, skin_fill_outlined("RightFA", 282, 299, SKIN, line=1.15)),
        # 2. Vertical Upper Arm & Glowing Supporting Deltoid
        f'{i2}<Node x="{f(elbow_x)}" y="{f(elbow_y)}" rotation="{f(p0["ua_bot_rot"])}" name="SupportingUpperArmNode" id="{ua_id}">',
        stroke_shape(i3, "RightDeltFiber1", [(-3.0, -90.0), (-2.0, -68.0)], 1.1, "737F1D1D", 0.3),
        stroke_shape(i3, "RightDeltFiber2", [(4.0, -90.0), (4.5, -68.0)], 1.1, "737F1D1D", 0.3),
        stroke_shape(i3, "RightDeltHi", [(-4.0, -94.0), (6.0, -84.0), (5.0, -68.0)], 2.4, "80FFFFFF", 2.4),
        smooth_shape(i3, "SupportingRightDeltoid", active_delt_pts, muscle_paint_fn("SupportDelt", delt_t, 1.05)),
        smooth_shape(i3, "RightDeltoidCap", delt_pts, skin_fill_outlined("RightDelt", -100, -58, SKIN, line=1.1)),
        stroke_shape(i3, "RightTricepsLine", [(-4.0, -58.0), (-3.0, -30.0), (-2.0, -10.0)], 1.2, SOFT_SHADOW, 0.8),
        stroke_shape(i3, "RightUpperArmHi", [(5.0, -58.0), (6.0, -30.0), (5.0, -10.0)], 2.6, HIGHLIGHT, 2.8),
        stroke_shape(i3, "RightUpperArmSh", [(-7.0, -56.0), (-7.0, -28.0), (-5.0, -8.0)], 3.4, CORE_SHADOW, 3.4),
        smooth_shape(i3, "RightUpperArmShape", ua_pts, skin_fill_outlined("RightUA", -86, 4, SKIN, line=1.15)),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


def build_top_left_arm_on_hip():
    """Top (Left) arm with hand resting cleanly on the upper (left) hip / iliac crest."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    ua_id, fa_id = nid(), nid()
    key_double(ua_id, 13, lambda p: p["sh_top"][0])
    key_double(ua_id, 14, lambda p: p["sh_top"][1])
    key_double(ua_id, 15, lambda p: p["ua_top_ang"])
    key_double(ua_id, 16, lambda p: p["ua_top_sc"])

    key_double(fa_id, 13, lambda p: p["elb_top"][0])
    key_double(fa_id, 14, lambda p: p["elb_top"][1])
    key_double(fa_id, 15, lambda p: p["fa_top_ang"])
    key_double(fa_id, 16, lambda p: p["fa_top_sc"])
    p0 = POSES[0]

    ua_pts = [
        (-8, 0), (-5, -8.5), (10, -9.8), (28, -9.0), (44, -6.5),
        (54, 0), (44, 6.5), (28, 8.8), (10, 9.2), (-5, 7.8),
    ]
    delt_pts = [
        (-10, 0), (-6, -10.0), (6, -11.0), (16, -7.5), (18, 0),
        (15, 7.5), (5, 10.0), (-6, 8.5),
    ]
    fa_pts = [
        (-5, 0), (-3, -6.8), (14, -7.5), (36, -6.0), (54, -4.2),
        (64, 0), (54, 4.5), (36, 6.0), (14, 7.2), (-3, 6.0),
    ]
    hand_pts = [
        (56, -5.2), (68, -6.0), (74, -2.0), (72, 4.5), (62, 5.8), (54, 4.2),
    ]

    return "\n".join([
        f'{ind}<Node name="TopLeftArmOnHip">',
        f'{i2}<Node x="{f(p0["elb_top"][0])}" y="{f(p0["elb_top"][1])}" '
        f'rotation="{f(p0["fa_top_ang"])}" scaleX="{f(p0["fa_top_sc"])}" name="TopLeftForearm" id="{fa_id}">',
        smooth_shape(i3, "TopLeftHandOnHip", hand_pts, skin_fill_outlined("TopHand", -6, 6, SKIN, line=1.05)),
        stroke_shape(i3, "TopForearmHi", [(8, -3.5), (28, -3.2), (48, -2.2)], 2.2, HIGHLIGHT, 2.2),
        smooth_shape(i3, "TopLeftForearmShape", fa_pts, skin_fill_outlined("TopFA", -8, 8, SKIN, line=1.1)),
        f"{i2}</Node>",
        f'{i2}<Node x="{f(p0["sh_top"][0])}" y="{f(p0["sh_top"][1])}" '
        f'rotation="{f(p0["ua_top_ang"])}" scaleX="{f(p0["ua_top_sc"])}" name="TopLeftUpperArm" id="{ua_id}">',
        smooth_shape(i3, "TopLeftDeltoid", delt_pts, skin_fill_outlined("TopDelt", -11, 11, SKIN_FAR, line=1.05)),
        stroke_shape(i3, "TopUpperArmHi", [(10, -4.8), (28, -4.5), (42, -3.2)], 2.4, HIGHLIGHT, 2.4),
        smooth_shape(i3, "TopLeftUpperArmShape", ua_pts, skin_fill_outlined("TopUA", -10, 10, SKIN_FAR, line=1.1)),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 2. Stacked Straight Legs (Bottom Right Leg + Top Left Leg)
def build_stacked_leg(indent, prefix, is_top):
    """Builds the Bottom (Right, supporting on floor) or Top (Left, stacked directly above) Side-Plank leg."""
    i2 = indent + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if is_top else SKIN
    shorts = SHORTS_FAR if is_top else SHORTS
    l_thigh = L_THIGH_TOP if is_top else L_THIGH_BOT
    l_shin = L_SHIN_TOP if is_top else L_SHIN_BOT

    hip_key = "hip_top" if is_top else "hip_bot"
    knee_key = "knee_top" if is_top else "knee_bot"
    ankle_key = "ankle_top" if is_top else "ankle_bot"
    thigh_ang_key = "thigh_top_ang" if is_top else "thigh_bot_ang"
    shin_ang_key = "shin_top_ang" if is_top else "shin_bot_ang"
    foot_rot_key = "foot_top_rot" if is_top else "foot_bot_rot"

    thigh_id, shin_id, foot_id = nid(), nid(), nid()
    key_double(thigh_id, 13, lambda p: p[hip_key][0])
    key_double(thigh_id, 14, lambda p: p[hip_key][1])
    key_double(thigh_id, 15, lambda p: p[thigh_ang_key])

    key_double(shin_id, 13, lambda p: p[knee_key][0])
    key_double(shin_id, 14, lambda p: p[knee_key][1])
    key_double(shin_id, 15, lambda p: p[shin_ang_key])

    key_double(foot_id, 13, lambda p: p[ankle_key][0])
    key_double(foot_id, 14, lambda p: p[ankle_key][1])
    key_double(foot_id, 15, lambda p: p[foot_rot_key])

    p0 = POSES[0]

    thigh_pts = [
        (-14.0, -11.0), (10.0, -15.5), (38.0, -15.0), (60.0, -11.5),
        (l_thigh + 2.0, -5.0), (l_thigh + 2.0, 5.0), (58.0, 10.8),
        (34.0, 14.5), (8.0, 15.5), (-14.0, 11.5),
    ]
    shorts_cuff_pts = [
        (-16.0, -12.0), (22.0, -16.2), (24.0, 15.8), (-16.0, 12.5),
    ]
    shin_pts = [
        (-7.0, -6.0), (18.0, -6.2), (44.0, -5.2), (l_shin - 3.0, -3.8),
        (l_shin + 2.0, 0.0), (l_shin - 4.0, 4.2), (50.0, 6.8),
        (30.0, 12.8), (12.0, 12.5), (-6.0, 6.5),
    ]
    foot_pts = [
        (-7.0, -4.0), (5.0, -2.0), (8.0, 8.0),
        (9.5, 22.0), (5.0, 26.5), (-2.0, 24.5),
        (-5.0, 14.0), (-8.5, 2.5),
    ]

    out = [f'{indent}<Node name="{prefix}SidePlankLeg">']

    # 1. Bare Foot (lateral edge of bottom foot on mat, top foot stacked directly above)
    out.append(
        f'{i2}<Node x="{f(p0[ankle_key][0])}" y="{f(p0[ankle_key][1])}" '
        f'rotation="{f(p0[foot_rot_key])}" name="{prefix}FootNode" id="{foot_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}FootArch", [(-2.0, 3.0), (1.0, 14.0), (3.5, 22.0)], 1.1, SOFT_SHADOW, 0.6))
    out.append(stroke_shape(i3, f"{prefix}FootHi", [(2.5, 3.0), (5.0, 14.0), (6.5, 21.0)], 1.8, HIGHLIGHT, 2.0))
    out.append(smooth_shape(i3, f"{prefix}BareFoot", foot_pts, skin_fill_outlined(prefix + "Foot", -4, 27, skin, line=1.1)))
    out.append(f"{i2}</Node>")

    # 2. Lower Leg / Calf
    out.append(
        f'{i2}<Node x="{f(p0[knee_key][0])}" y="{f(p0[knee_key][1])}" '
        f'rotation="{f(p0[shin_ang_key])}" name="{prefix}ShinNode" id="{shin_id}">'
    )
    out.append(ellipse_shape(i3, f"{prefix}KneeCap", 0.0, -1.0, 16.0, 14.0, skin_fill_outlined(prefix + "Knee", -7, 7, skin, line=1.0)))
    out.append(stroke_shape(i3, f"{prefix}GastrocLine", [(12.0, 5.8), (30.0, 8.0), (46.0, 4.2)], 1.15, SOFT_SHADOW, 0.6))
    out.append(stroke_shape(i3, f"{prefix}ShinHi", [(12.0, -3.8), (36.0, -3.4), (58.0, -2.2)], 2.2, HIGHLIGHT, 2.4))
    out.append(stroke_shape(i3, f"{prefix}CalfSh", [(12.0, 9.8), (28.0, 10.8), (48.0, 5.2)], 2.8, CORE_SHADOW, 2.8))
    out.append(smooth_shape(i3, f"{prefix}ShinShape", shin_pts, skin_fill_outlined(prefix + "Shin", -7, 13, skin, line=1.1)))
    out.append(f"{i2}</Node>")

    # 3. Extended Thigh & Shorts Cuff
    out.append(
        f'{i2}<Node x="{f(p0[hip_key][0])}" y="{f(p0[hip_key][1])}" '
        f'rotation="{f(p0[thigh_ang_key])}" name="{prefix}ThighNode" id="{thigh_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}ShortsHem", [(22.0, -15.5), (23.0, 0.0), (22.0, 15.0)], 1.4, "800F172A", 0.5))
    out.append(smooth_shape(i3, f"{prefix}ShortsCuff", shorts_cuff_pts, skin_fill_outlined(prefix + "Shorts", -16, 16, shorts, line=1.1)))
    out.append(stroke_shape(i3, f"{prefix}ITBandLine", [(24.0, -4.0), (46.0, -3.0), (62.0, -1.5)], 1.25, SOFT_SHADOW, 0.6))
    out.append(stroke_shape(i3, f"{prefix}ThighHi", [(24.0, -11.5), (46.0, -10.5), (60.0, -7.0)], 2.4, HIGHLIGHT, 2.5))
    out.append(stroke_shape(i3, f"{prefix}ThighSh", [(24.0, 11.0), (44.0, 10.0), (58.0, 7.0)], 3.2, CORE_SHADOW, 3.2))
    out.append(smooth_shape(i3, f"{prefix}ThighShape", thigh_pts, skin_fill_outlined(prefix + "Thigh", -16, 16, skin, line=1.1)))
    out.append(f"{i2}</Node>")

    out.append(f"{indent}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. Side-Plank Torso, Glowing Obliques, 6-Pack Abs, Gluteus Medius & 3/4 Head
def build_side_plank_torso_and_head():
    """3/4 Front-Facing Side-Plank Torso, Pelvis Shorts with Gluteus Medius, Lateral Obliques & 6-Pack Rectus Abdominis,
    and Canonical 3/4 Head."""
    ind = "        "
    i2 = ind + "    "

    torso_id = nid()
    key_double(torso_id, 14, lambda p: p["torso_y"])
    key_double(torso_id, 15, lambda p: p["torso_rot"])
    p0 = POSES[0]

    def oblique_bot_t(p):
        return 0.50 + 0.50 * (p["r"] ** 0.72) + 0.07 * abs(p["breath"])

    def rectus_t(p):
        return 0.45 + 0.53 * (p["r"] ** 0.76) + 0.06 * abs(p["breath"])

    def glute_med_t(p):
        return 0.46 + 0.52 * (p["r"] ** 0.76) + 0.06 * abs(p["breath"])

    # Local coordinates relative to Side-Plank Torso Pivot (354.0, 198.0):
    # Pelvis & Shorts sit on the left at x in [-92..-42], y in [-14..+38]
    # Torso spans x in [-52..+66], y in [-28..+30] (angled along the side-plank diagonal)
    # Head & Neck sit on the right at x in [+64..+122], y in [-30..+16]
    pelvis_shorts_pts = [
        (-92.0, -2.0), (-78.0, -16.0), (-48.0, -18.0),
        (-38.0, -4.0), (-42.0, 32.0), (-70.0, 36.0), (-90.0, 24.0),
    ]
    # Primary Hip Abductor: Gluteus Medius on the lower/supporting (right) lateral hip & upper (left) hip crest
    glute_med_bot_pts = [
        (-84.0, 14.0), (-60.0, 12.0), (-44.0, 20.0),
        (-46.0, 32.0), (-68.0, 34.5), (-86.0, 25.0),
    ]
    glute_med_top_pts = [
        (-80.0, -14.0), (-56.0, -16.0), (-48.0, -6.0), (-74.0, -4.0),
    ]

    torso_pts = [
        (-48.0, -16.0), (-8.0, -26.0), (34.0, -30.0), (62.0, -22.0),
        (68.0, 4.0), (50.0, 22.0), (8.0, 26.0), (-30.0, 30.0),
        (-46.0, 28.0),
    ]

    # Sculpted Pectoralis Major Chest Plates facing 3/4 toward viewer (x in [+18..+58])
    pec_bot_pts = [
        (22.0, -2.0), (42.0, -6.0), (58.0, 0.0),
        (52.0, 16.0), (34.0, 18.0), (20.0, 10.0),
    ]
    pec_top_pts = [
        (20.0, -20.0), (38.0, -26.0), (54.0, -18.0),
        (48.0, -5.0), (30.0, -4.0), (18.0, -10.0),
    ]
    pec_paint = (
        f'<Fill name="PecFill">{grad3("PecGrad", -26, 18, "FFF8FAFC", "FFDCE4EE", "FFA3B1C4")}</Fill>'
        '<Stroke thickness="1.1" join="round" name="PecStroke"><SolidColor colorValue="4D0F172A" name="PecStrokeCol"/></Stroke>'
    )

    # Primary Target Muscle #1: Lower (Right) External & Internal Oblique Lateral Wall (supporting underside of waist!)
    oblique_bot_pts = [
        (-44.0, 12.0), (-14.0, 10.0), (18.0, 8.0), (32.0, 14.0),
        (20.0, 24.0), (-10.0, 27.5), (-38.0, 29.5), (-45.0, 24.0),
    ]
    # Upper (Left) External Oblique along upper waist contour
    oblique_top_pts = [
        (-44.0, -14.0), (-14.0, -22.0), (14.0, -24.0),
        (12.0, -14.0), (-16.0, -10.0), (-42.0, -6.0),
    ]

    # Primary Target Muscle #2: Rectus Abdominis (6-pack blocks facing 3/4 viewer between Top & Bottom Obliques)
    abs_blocks = [
        # Upper (left) row of 3 abdominal blocks
        [(-36.0, -4.0), (-20.0, -7.0), (-18.0, 1.0), (-34.0, 4.0)],
        [(-17.0, -7.5), (-1.0, -10.5), (1.0, -2.0), (-15.0, 1.0)],
        [(2.0, -11.0), (18.0, -13.5), (19.5, -5.0), (4.0, -2.5)],
        # Lower (right) row of 3 abdominal blocks
        [(-34.0, 5.5), (-18.0, 2.5), (-16.0, 10.5), (-32.0, 13.5)],
        [(-15.0, 2.5), (1.0, -0.5), (3.0, 7.5), (-13.0, 10.5)],
        [(4.0, -1.0), (19.5, -3.5), (21.0, 4.5), (6.0, 7.0)],
    ]

    # Canonical 3/4 Volumetric Head & Neck aligned with the diagonal spine (x in [+56..+120])
    neck_pts = [
        (54.0, -18.0), (76.0, -18.0), (80.0, 2.0), (58.0, 6.0), (50.0, -6.0),
    ]
    head_pts = [
        (74.0, -18.0), (88.0, -29.0), (105.0, -29.0), (118.0, -18.0),
        (120.0, -4.0), (113.0, 8.0), (100.0, 14.0), (86.0, 13.0),
        (77.0, 7.0), (70.0, -3.0),
    ]
    hair_pts = [
        (80.0, -20.0), (92.0, -30.0), (108.0, -29.0), (119.0, -18.0),
        (120.0, -3.0), (112.0, 6.0), (108.0, -4.0), (102.0, -14.0),
        (90.0, -16.0),
    ]
    hair_paint = (
        f'<Fill name="HairFill">{grad("HairGrad", 80, -30, 120, 6, "FF334155", "FF0F172A")}</Fill>'
        '<Stroke thickness="1.05" join="round" name="HairStroke"><SolidColor colorValue="FF090D16" name="HairStrokeCol"/></Stroke>'
    )

    out = [
        f'{ind}<Node x="354" y="{f(p0["torso_y"])}" rotation="{f(p0["torso_rot"])}" '
        f'name="SidePlankTorsoAndHead" id="{torso_id}">'
    ]

    # 1. Volumetric 3/4 Head & Muscular Neck
    out.append(smooth_shape(i2, "Hair", hair_pts, hair_paint))
    out.append(ellipse_shape(i2, "Ear", 90.0, -14.0, 5.2, 7.4, skin_fill_outlined("Ear", -4, 4, SKIN, line=0.85), rot_deg=24.0))
    out.append(stroke_shape(i2, "BrowShade", [(100.0, -2.0), (106.0, 2.0)], 1.35, "730F172A", 0.4))
    out.append(stroke_shape(i2, "EyeLine", [(97.5, 0.5), (102.5, 3.5)], 1.1, "800F172A", 0.3))
    out.append(stroke_shape(i2, "NoseRidge", [(94.0, 4.0), (98.0, 8.0), (94.5, 9.5)], 1.15, SOFT_SHADOW, 0.3))
    out.append(stroke_shape(i2, "MouthLine", [(86.5, 9.0), (91.5, 10.5)], 1.05, "660F172A", 0.3))
    out.append(stroke_shape(i2, "HeadCrownHi", [(86.0, -20.0), (100.0, -22.0), (108.0, -14.0)], 2.8, HIGHLIGHT, 3.0))
    out.append(stroke_shape(i2, "JawShadow", [(75.0, 4.0), (86.0, 11.5), (98.0, 12.0)], 2.2, CORE_SHADOW, 2.2))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill_outlined("Head", -29, 14, SKIN, x0=70, x1=120, line=1.15)))
    out.append(stroke_shape(i2, "NeckMuscleLine", [(60.0, -8.0), (72.0, -4.0), (78.0, 0.0)], 1.4, SOFT_SHADOW, 1.0))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill_outlined("Neck", -18, 6, SKIN, line=1.05)))

    # 2. Dark Athletic Compression Shorts & Glowing Gluteus Medius (Hip Abductors)
    out.append(stroke_shape(i2, "ShortsWaistSeam", [(-44.0, -14.0), (-40.0, 8.0), (-44.0, 28.0)], 1.5, "800F172A", 0.6))
    out.append(stroke_shape(i2, "GluteMedFiber1", [(-78.0, 22.0), (-62.0, 21.0), (-48.0, 25.0)], 1.1, "737F1D1D", 0.3))
    out.append(stroke_shape(i2, "GluteMedHi", [(-78.0, 26.0), (-60.0, 27.0), (-48.0, 28.0)], 2.0, "66FFFFFF", 1.8))
    out.append(smooth_shape(i2, "GluteusMediusBottom", glute_med_bot_pts, muscle_paint_fn("GluteMedBot", glute_med_t, 1.05)))
    out.append(smooth_shape(i2, "GluteusMediusTop", glute_med_top_pts, muscle_paint_fn("GluteMedTop", glute_med_t, 0.90)))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts_pts, skin_fill_outlined("PelvisShorts", -18, 36, SHORTS, x0=-92, x1=-38, line=1.15)))

    # 3. Glowing External & Internal Obliques + 6-Pack Rectus Abdominis + Sculpted Pectorals
    out.append(stroke_shape(i2, "LineaAlba", [(-35.0, 4.5), (-8.0, 0.0), (20.0, -4.5)], 1.3, "8C7F1D1D", 0.3))
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"RectusAbBlock{idx + 1}", bpts, muscle_paint_fn(f"RectusAb{idx + 1}", rectus_t, 1.0)))

    out.append(stroke_shape(i2, "ObliqueBotSlip1", [(-36.0, 20.0), (-16.0, 18.0), (4.0, 16.0)], 1.15, "807F1D1D", 0.3))
    out.append(stroke_shape(i2, "ObliqueBotSlip2", [(-20.0, 24.0), (2.0, 21.0), (20.0, 18.0)], 1.15, "807F1D1D", 0.3))
    out.append(stroke_shape(i2, "ObliqueBotHi", [(-34.0, 23.0), (-8.0, 22.0), (18.0, 19.0)], 2.2, "66FFFFFF", 1.8))
    out.append(smooth_shape(i2, "LowerExternalOblique", oblique_bot_pts, muscle_paint_fn("ObliqueBot", oblique_bot_t, 1.15)))
    out.append(smooth_shape(i2, "UpperExternalOblique", oblique_top_pts, muscle_paint_fn("ObliqueTop", rectus_t, 0.95)))

    out.append(stroke_shape(i2, "SternalLine", [(20.0, -6.0), (38.0, -5.0), (54.0, -2.0)], 1.3, SOFT_SHADOW, 0.5))
    out.append(stroke_shape(i2, "PecHi", [(26.0, 4.0), (42.0, 3.0), (52.0, 6.0)], 2.2, HIGHLIGHT, 2.2))
    out.append(smooth_shape(i2, "PecBottomRight", pec_bot_pts, pec_paint))
    out.append(smooth_shape(i2, "PecTopLeft", pec_top_pts, pec_paint))

    out.append(stroke_shape(i2, "TorsoTopHi", [(-38.0, -14.0), (0.0, -22.0), (40.0, -24.0)], 3.4, HIGHLIGHT, 3.5))
    out.append(smooth_shape(i2, "SidePlankTorso", torso_pts, skin_fill_outlined("Torso", -30, 30, SKIN, x0=-48, x1=68, line=1.15)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    support_arm_xml = build_supporting_right_arm()
    top_arm_xml = build_top_left_arm_on_hip()
    bot_leg_xml = build_stacked_leg("        ", "BottomRight", False)
    top_leg_xml = build_stacked_leg("        ", "TopLeft", True)
    torso_xml = build_side_plank_torso_and_head()

    grouped = {}
    for oid, kp_xml in KEYED:
        grouped.setdefault(oid, []).append(kp_xml)
    keyed_objects_xml = "\n".join(
        f'        <KeyedObject objectId="{oid}">\n' + "\n".join(props) + "\n        </KeyedObject>"
        for oid, props in grouped.items()
    )

    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"
    mat_fill = (
        f'<Fill name="MatFill">{grad("MatGrad", 110, 292, 500, 300, "FF334155", "FF1E293B")}</Fill>'
        '<Stroke thickness="1.1" join="round" name="MatStroke"><SolidColor colorValue="FF475569" name="MatStrokeCol"/></Stroke>'
    )

    return f"""<Rive version="7.3">
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="SidePlank" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Supporting Near (Right) Forearm, Elbow & Glowing Deltoid -->
{support_arm_xml}

        <!-- 2. Top (Left) Arm Resting Hand on Upper Hip -->
{top_arm_xml}

        <!-- 3. Bottom (Right) Supporting Leg on Mat -->
{bot_leg_xml}

        <!-- 4. Side-Plank Torso, Glowing Obliques, 6-Pack Abs, Gluteus Medius & 3/4 Head -->
{torso_xml}

        <!-- 5. Top (Left) Stacked Leg -->
{top_leg_xml}

        <!-- 6. Beveled Studio Exercise Mat, Contact Shadow & Backdrop -->
        <Shape x="304" y="293" scaleX="1.85" scaleY="0.09" name="AthleteShadow">
            <Ellipse width="230" height="230" name="AthleteShadowEllipse"/>
            <Fill name="AthleteShadowFill"><RadialGradient startX="0" startY="0" endX="115" endY="0" name="AthleteShadowGrad">
                <GradientStop colorValue="BF000000" position="0"/>
                <GradientStop colorValue="59000000" position="0.6"/>
                <GradientStop colorValue="00000000" position="1"/>
            </RadialGradient></Fill>
        </Shape>
        {poly_shape("        ", "ExerciseMat", [(116, 293), (496, 293), (506, 299), (106, 299)], mat_fill, radius=3.0)}
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="SidePlank" id="0:60">
{keyed_objects_xml}
        </LinearAnimation>
    </Artboard>
</Rive>
"""


# ---------------------------------------------------------------- Verbatim Rive 7.3 Binary Compiler (52-byte TOC)
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
    ASSET_RIV.parent.mkdir(parents=True, exist_ok=True)
    ASSET_THUMB.parent.mkdir(parents=True, exist_ok=True)

    riv_bytes = _compile_rml_bytes(OUT)
    (BUILD / "side_plank.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/aff6e669-980f-4ec0-a386-c5be528dd2f8/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (34, "frame_mid"), (70, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(720, 0, 260))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
