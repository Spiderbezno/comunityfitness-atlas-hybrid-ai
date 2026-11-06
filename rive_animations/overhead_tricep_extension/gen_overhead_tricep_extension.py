#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive scene for Overhead Tricep Extension (id: 'overhead_tricep_extension').

Uses our canonical standing 3/4 front-left CommunityFitness mannequin (volumetric 3/4 head with
hair/ear/brow/eye/mouth, muscular neck, sculpted pectorals, 6-pack rectus abdominis, slender waist,
dark athletic compression shorts, quadriceps, gastrocnemius calves, and planted bare feet).

Matches the 2-panel 3/4 Standing Cable Rope Overhead Tricep Extension reference illustration:
  - Right Panel of Reference (f = 0 & f = 160, r = 0.0 — Deep Behind-Neck Stretch):
    * Athlete stands tall in a balanced 3/4 stance with feet planted on FLOOR = 300.0, facing away
      from a low cable anchor behind his heels.
    * Both upper arms stay elevated beside the head/ears while the elbows flex deeply so the hands
      hold the two black rubber-stoppered rope ends behind the neck/upper back, placing the long head
      of the triceps brachii under maximum stretch.
  - Left Panel of Reference (f = 72, r = 1.0 — Full Overhead Lockout):
    * Both forearms extend upward in an isolated elbow-extension arc while the upper arms remain
      anchored overhead, driving the rope handles above the crown of the head as the triceps brachii
      (long, lateral, and medial heads) reach peak contraction.
  - Diagonal Tensioned Low-Pulley Cable + Dual Braided Rope Attachment:
    * A taut steel cable runs diagonally upward from the low floor pulley behind the athlete's heels
      to the chrome swivel eyelet behind the head/shoulders, splitting into two heavy braided black
      ropes capped with flanged rubber stoppers in each hand.

Run:
    python3 gen_overhead_tricep_extension.py            # writes scene.rml
    python3 gen_overhead_tricep_extension.py --publish  # compiles assets/animations/overhead_tricep_extension.riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/overhead_tricep_extension.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/overhead_tricep_extension.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps loop
STEP = 2

# Canonical Standing 3/4 Athlete Scale for Overhead Tricep Extension:
# Scaled vertically by 0.90 anchored at FLOOR = 300.0 so full overhead rope extension stays cleanly inside y >= 22.
BODY_SCALE_Y = 0.90


def pt_y(p):
    return (p[0], FLOOR - BODY_SCALE_Y * (FLOOR - p[1]))


def pts_y(pts):
    return [pt_y(p) for p in pts]


SHOULDER_FAR = pt_y((288.0, 98.0))    # (288.0, 118.2) — Right (far / screen-left) shoulder
SHOULDER_NEAR = pt_y((348.0, 100.0))  # (348.0, 120.0) — Left (near / screen-right) shoulder
UPPER_ARM_LEN = 38.0
FOREARM_LEN = 35.0
CABLE_ANCHOR = (394.0, 294.0)         # Low floor cable pulley behind the athlete's heels

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
ROPE_DARK = ("FF334155", "FF182232", "FF090D16")
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


EASE_EXTEND = cubic_bezier(0.35, 0.0, 0.22, 1.0)
EASE_LOWER = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def extension_progress(frame):
    """Returns simultaneous bilateral overhead tricep-extension progress r in [0.0, 1.0] across 160 frames:
    - 0..12:   Bottom behind-neck stretch hold (r = 0.0: elbows flexed, rope held behind neck)
    - 12..64:  Concentric overhead triceps extension (r: 0.0 -> 1.0: forearms extend overhead)
    - 64..84:  Peak overhead lockout squeeze above crown of head (r = 1.0)
    - 84..148: Controlled eccentric lowering behind the neck (r: 1.0 -> 0.0)
    - 148..160: Bottom stretch hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 64:
        return EASE_EXTEND((fr - 12) / 52.0)
    if fr <= 84:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_LOWER((fr - 84) / 64.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def seg_xform(p0, p1, base_len):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ang = math.atan2(dy, dx)
    sc = max(0.55, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute Standing Cable Rope Overhead Tricep Extension transforms at progress r in [0.0, 1.0].

    Matches the 2-panel reference illustration:
      - Upper arms stay anchored elevated beside the head/ears (`ua_near` from -72 deg to -95 deg,
        `ua_far` from -116 deg to -86 deg), isolating the elbow joint.
      - At r = 0.0 (Right Panel — Deep Behind-Neck Stretch):
        * Elbows are flexed deeply behind the head (`fa_near = +158 deg`, `fa_far = +18 deg`), placing
          the hands and rope stoppers behind the neck at `(329.5, 92.6)` and `(304.2, 91.5)`.
      - At r = 1.0 (Left Panel — Full Overhead Lockout):
        * Forearms rotate smoothly through the overhead extension arc (`fa_near: +158 -> +254 deg`,
          `fa_far: +18 -> -76 deg`) to lock out above the crown of the head at `(335.1, 48.5)` and
          `(300.2, 46.5)`!
    """
    # 1. Near (Left / Screen-Right) Arm Overhead Tricep Extension (SHOULDER_NEAR = (348.0, 120.0)):
    ua_near_deg = lerp(-72.0, -95.0, r)
    fa_near_deg = lerp(158.0, 254.0, r)  # +158 deg (tucked behind neck) -> +254 deg (-106 deg overhead)
    ua_near_rad = math.radians(ua_near_deg)
    fa_near_rad = math.radians(fa_near_deg)

    # Slight foreshortening on forearm at bottom behind-neck tuck (r=0) for natural 3D depth
    fa_near_len = FOREARM_LEN * lerp(0.84, 1.00, r)
    elbow_near = (
        SHOULDER_NEAR[0] + UPPER_ARM_LEN * math.cos(ua_near_rad),
        SHOULDER_NEAR[1] + UPPER_ARM_LEN * math.sin(ua_near_rad),
    )
    hand_near = (
        elbow_near[0] + fa_near_len * math.cos(fa_near_rad),
        elbow_near[1] + fa_near_len * math.sin(fa_near_rad),
    )
    ua_near_ang, ua_near_sc = seg_xform(SHOULDER_NEAR, elbow_near, UPPER_ARM_LEN)
    fa_near_ang, fa_near_sc = seg_xform(elbow_near, hand_near, FOREARM_LEN)
    delt_near_ang = math.radians(lerp(-62.0, -76.0, r))

    # 2. Far (Right / Screen-Left) Arm Overhead Tricep Extension (SHOULDER_FAR = (288.0, 118.2)):
    persp_x = 0.90
    ua_far_deg = lerp(-116.0, -85.0, r)
    fa_far_deg = lerp(18.0, -76.0, r)  # +18 deg (tucked behind neck) -> -76 deg (extended overhead)
    ua_far_rad = math.radians(ua_far_deg)
    fa_far_rad = math.radians(fa_far_deg)

    fa_far_len = FOREARM_LEN * lerp(0.84, 1.00, r)
    elbow_far = (
        SHOULDER_FAR[0] + UPPER_ARM_LEN * persp_x * math.cos(ua_far_rad),
        SHOULDER_FAR[1] + UPPER_ARM_LEN * math.sin(ua_far_rad),
    )
    hand_far = (
        elbow_far[0] + fa_far_len * persp_x * math.cos(fa_far_rad),
        elbow_far[1] + fa_far_len * math.sin(fa_far_rad),
    )
    ua_far_ang, ua_far_sc = seg_xform(SHOULDER_FAR, elbow_far, UPPER_ARM_LEN)
    fa_far_ang, fa_far_sc = seg_xform(elbow_far, hand_far, FOREARM_LEN)
    delt_far_ang = math.radians(lerp(58.0, 72.0, r))

    # 3. Cable Swivel Eyelet & Dual Rope Geometry:
    #    The chrome swivel sits just below/behind the midpoint of the two hands Along the diagonal cable line
    mid_hx = 0.5 * (hand_near[0] + hand_far[0])
    mid_hy = 0.5 * (hand_near[1] + hand_far[1])
    swivel = (
        mid_hx + lerp(8.0, 5.0, r),
        mid_hy + lerp(14.0, 22.0, r),
    )

    cable_ang, cable_sc = seg_xform(CABLE_ANCHOR, swivel, 200.0)
    rope_near_ang, rope_near_sc = seg_xform(swivel, hand_near, 28.0)
    rope_far_ang, rope_far_sc = seg_xform(swivel, hand_far, 28.0)
    stopper_near_rot = math.radians(lerp(35.0, -28.0, r))
    stopper_far_rot = math.radians(lerp(-35.0, 28.0, r))

    return {
        "r": r,
        "elbow_near": elbow_near,
        "hand_near": hand_near,
        "ua_near_ang": ua_near_ang,
        "ua_near_sc": ua_near_sc,
        "fa_near_ang": fa_near_ang,
        "fa_near_sc": fa_near_sc,
        "delt_near_ang": delt_near_ang,
        "elbow_far": elbow_far,
        "hand_far": hand_far,
        "ua_far_ang": ua_far_ang,
        "ua_far_sc": ua_far_sc,
        "fa_far_ang": fa_far_ang,
        "fa_far_sc": fa_far_sc,
        "delt_far_ang": delt_far_ang,
        "swivel": swivel,
        "cable_ang": cable_ang,
        "cable_sc": cable_sc,
        "rope_near_ang": rope_near_ang,
        "rope_near_sc": rope_near_sc,
        "rope_far_ang": rope_far_ang,
        "rope_far_sc": rope_far_sc,
        "stopper_near_rot": stopper_near_rot,
        "stopper_far_rot": stopper_far_rot,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(extension_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = (
    "ua_near_ang",
    "fa_near_ang",
    "delt_near_ang",
    "ua_far_ang",
    "fa_far_ang",
    "delt_far_ang",
    "cable_ang",
    "rope_near_ang",
    "rope_far_ang",
    "stopper_near_rot",
    "stopper_far_rot",
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


def muscle_paint_fn(name, fn_t, line=1.0):
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


# ---------------------------------------------------------------- 1. Overhead Tricep Extension Arm & Rope Stopper
def tricep_arm_rig(prefix, far):
    """Arm with sculpted Triceps Brachii (Long Head & Lateral/Medial Head matching reference),
    Forearm, Neutral-Grip Hand, and Flanged Black Rope Stopper."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    sx, sy = SHOULDER_FAR if far else SHOULDER_NEAR
    ua_ang_k = "ua_far_ang" if far else "ua_near_ang"
    ua_sc_k = "ua_far_sc" if far else "ua_near_sc"
    el_k = "elbow_far" if far else "elbow_near"
    hand_k = "hand_far" if far else "hand_near"
    fa_ang_k = "fa_far_ang" if far else "fa_near_ang"
    fa_sc_k = "fa_far_sc" if far else "fa_near_sc"
    delt_ang_k = "delt_far_ang" if far else "delt_near_ang"
    stop_rot_k = "stopper_far_rot" if far else "stopper_near_rot"

    ua_id, fa_id, delt_id, stop_id = nid(), nid(), nid(), nid()
    key_double(ua_id, 15, lambda p: p[ua_ang_k])
    key_double(ua_id, 16, lambda p: p[ua_sc_k])

    key_double(fa_id, 13, lambda p: p[el_k][0])
    key_double(fa_id, 14, lambda p: p[el_k][1])
    key_double(fa_id, 15, lambda p: p[fa_ang_k])
    key_double(fa_id, 16, lambda p: p[fa_sc_k])

    key_double(delt_id, 15, lambda p: p[delt_ang_k])

    key_double(stop_id, 13, lambda p: p[hand_k][0])
    key_double(stop_id, 14, lambda p: p[hand_k][1])
    key_double(stop_id, 15, lambda p: p[stop_rot_k])

    p0 = POSES[0]

    # Primary Target Muscle: Triceps Brachii (Long Head + Lateral/Medial Head)
    # Already glowing warm orange at bottom stretch (r=0) and pulsing to intense crimson at overhead lockout (r=1)
    def triceps_long_t(p):
        return 0.48 + 0.52 * (p["r"] ** 0.76)

    def triceps_lat_t(p):
        return 0.44 + 0.56 * (p["r"] ** 0.80)

    # 1. Sculpted Neutral Silver-Slate Deltoid Cap at SHOULDER (unhighlighted in reference image so Triceps pop!)
    if not far:
        delt_base_pts = [
            (-13.5, -3.2), (-6.0, -10.2), (4.8, -9.8), (12.8, -3.2),
            (13.8, 6.0), (8.5, 15.2), (-1.8, 16.2), (-10.8, 9.8),
        ]
    else:
        delt_base_pts = [
            (-15.0, -3.2), (-8.0, -9.8), (4.2, -8.8), (9.8, -1.4),
            (8.8, 8.4), (0.5, 12.6), (-11.6, 8.8),
        ]

    # 2. Upper Arm & Sculpted 2-Bellied Triceps Brachii (matching the thick crimson horseshoe in the reference image)
    ua_pts = [
        (-7, 0), (-5, 8.8), (7, 11.2), (20, 11.5), (31, 9.5), (36, 6.2),
        (40, 0), (36, -6.2), (26, -9.5), (13, -10.2), (2, -9.2), (-5, -7.2),
    ]
    if not far:
        # Near (left) arm: when pointing up (-85 deg), +Y is screen-right (outer/posterior border of arm)
        triceps_long_pts = [
            (-2.0, 2.5), (10.0, 4.2), (24.0, 4.0), (34.5, 3.2),
            (36.0, 7.2), (26.0, 11.2), (11.0, 11.6), (-1.0, 8.5),
        ]
        triceps_lat_pts = [
            (6.0, -1.5), (19.0, -2.2), (31.5, -1.2), (36.5, 2.5),
            (28.0, 5.8), (15.0, 5.8), (5.0, 3.2),
        ]
        triceps_split = [(6.0, 3.8), (19.0, 4.6), (32.0, 3.5)]
        triceps_fiber1 = [(10.0, 8.2), (21.0, 8.8), (31.0, 7.2)]
        triceps_fiber2 = [(11.0, 1.2), (22.0, 1.5), (31.0, 1.8)]
    else:
        # Far (right) arm: when pointing up (-95 deg), -Y is screen-left (outer/posterior border of arm)
        triceps_long_pts = [
            (-2.0, -2.5), (10.0, -4.2), (24.0, -4.0), (34.5, -3.2),
            (36.0, -7.2), (26.0, -10.8), (11.0, -11.2), (-1.0, -8.2),
        ]
        triceps_lat_pts = [
            (6.0, 1.5), (19.0, 2.2), (31.5, 1.2), (36.5, -2.5),
            (28.0, -5.5), (15.0, -5.5), (5.0, -3.0),
        ]
        triceps_split = [(6.0, -3.6), (19.0, -4.4), (32.0, -3.4)]
        triceps_fiber1 = [(10.0, -7.8), (21.0, -8.4), (31.0, -6.8)]
        triceps_fiber2 = [(11.0, -1.2), (22.0, -1.5), (31.0, -1.8)]

    fa_pts = [
        (-4, 0), (-2, 6.2), (8, 7.5), (20, 6.2), (29, 4.4), (34, 3.4),
        (37, 0), (34, -3.4), (27, -4.4), (16, -6.0), (4, -6.6), (-2, -5.2),
    ]
    hand_pts = [
        (FOREARM_LEN - 4.5, -5.0), (FOREARM_LEN + 4.5, -4.8), (FOREARM_LEN + 6.5, 0.5),
        (FOREARM_LEN + 3.5, 5.2), (FOREARM_LEN - 4.5, 4.8),
    ]

    stopper_paint = (
        f'<Fill name="{prefix}StopperFill">{grad3(prefix + "StopperGrad", -8, 8, *ROPE_DARK, x0=-6, x1=6)}</Fill>'
        f'<Stroke thickness="1.0" name="{prefix}StopperStroke"><SolidColor colorValue="FF475569" name="{prefix}StopperStrokeCol"/></Stroke>'
    )
    cap_paint = (
        f'<Fill name="{prefix}CapFill"><SolidColor colorValue="FF090D16" name="{prefix}CapCol"/></Fill>'
        f'<Stroke thickness="0.9" name="{prefix}CapStroke"><SolidColor colorValue="FF334155" name="{prefix}CapStrokeCol"/></Stroke>'
    )

    out = [f'{ind}<Node name="{prefix}TricepArmGroup">']

    # If NOT far (Near Arm): Forearm & Hand sit behind UpperArm when tucked behind neck, OR we layer
    # DeltoidCap -> UpperArm (with big sculpted Triceps in foreground!) -> Forearm -> Stopper so that at
    # bottom behind-neck stretch (r=0) the forearm tucks cleanly BEHIND the head & upper arm just like the right panel!
    # Wait: let's check both r=0 and r=1!
    # At r=0 (behind neck), the forearm goes behind the upper arm and behind the head.
    # At r=1 (overhead lockout), the forearm extends straight up from the elbow (`x=344, y=82` -> `x=335, y=48`),
    # so only the elbow joint overlaps (`38..40` px of UpperArm and `-4..0` px of Forearm).
    # Therefore, putting UpperArm IN FRONT of Forearm makes BOTH `r=0` (behind-neck tuck) AND `r=1` (overhead lockout)
    # look 100% anatomically seamless, with the sculpted Triceps horseshoe wrapping right into the olecranon/elbow!

    # Layer A: Neutral Silver-Slate Deltoid Cap at SHOULDER
    out.append(
        f'{i2}<Node x="{f(sx)}" y="{f(sy)}" rotation="{f(p0[delt_ang_k])}" name="{prefix}DeltoidCap" id="{delt_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}DeltHi", [(-4.0, -5.0), (5.0, 2.0)], 2.2, HIGHLIGHT, 2.2))
    out.append(stroke_shape(i3, f"{prefix}DeltSh", [(4.0, 6.0), (-4.0, 11.0)], 2.8, CORE_SHADOW, 2.5))
    out.append(smooth_shape(i3, f"{prefix}DeltoidBase", delt_base_pts, skin_fill(prefix + "DeltBase", -10, 16, skin)))
    out.append(f"{i2}</Node>")

    # Layer B: Upper Arm (SHOULDER -> ELBOW) with Sculpted Long & Lateral/Medial Heads of Triceps Brachii
    out.append(
        f'{i2}<Node x="{f(sx)}" y="{f(sy)}" rotation="{f(p0[ua_ang_k])}" scaleX="{f(p0[ua_sc_k])}" name="{prefix}UpperArm" id="{ua_id}">'
    )
    ua_hi_y = 4.5 if far else -4.5
    out.append(stroke_shape(i3, f"{prefix}TricepsSplitLine", triceps_split, 1.2, "997F1D1D", 0.3))
    out.append(stroke_shape(i3, f"{prefix}TricepsFiberLong", triceps_fiber1, 1.0, "737F1D1D", 0.3))
    out.append(stroke_shape(i3, f"{prefix}TricepsFiberLat", triceps_fiber2, 0.95, "737F1D1D", 0.3))
    out.append(stroke_shape(i3, f"{prefix}TricepsHi", triceps_fiber1, 2.0, "66FFFFFF", 1.8))
    out.append(smooth_shape(i3, f"{prefix}TricepsLongHead", triceps_long_pts, muscle_paint_fn(prefix + "TriLong", triceps_long_t, 1.05)))
    out.append(smooth_shape(i3, f"{prefix}TricepsLateralHead", triceps_lat_pts, muscle_paint_fn(prefix + "TriLat", triceps_lat_t, 1.0)))
    out.append(stroke_shape(i3, f"{prefix}UpperArmHi", [(10, ua_hi_y), (22, ua_hi_y), (32, ua_hi_y * 0.8)], 2.2, HIGHLIGHT, 2.4))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UpperArm", -10, 11, skin)))
    out.append(f"{i2}</Node>")

    # Layer C: Forearm & Neutral-Grip Hand
    out.append(
        f'{i2}<Node x="{f(p0[el_k][0])}" y="{f(p0[el_k][1])}" '
        f'rotation="{f(p0[fa_ang_k])}" scaleX="{f(p0[fa_sc_k])}" name="{prefix}Forearm" id="{fa_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}Knuckle1", [(FOREARM_LEN - 2, -2.2), (FOREARM_LEN + 3.5, -2.2)], 0.95, SOFT_SHADOW, 0.0))
    out.append(stroke_shape(i3, f"{prefix}Knuckle2", [(FOREARM_LEN - 2, 1.2), (FOREARM_LEN + 3.5, 1.2)], 0.95, SOFT_SHADOW, 0.0))
    out.append(smooth_shape(i3, f"{prefix}GrippingHand", hand_pts, skin_fill(prefix + "Hand", -5, 5, skin)))
    hi_y = 2.6 if far else -2.6
    sh_y = -3.6 if far else 3.6
    out.append(stroke_shape(i3, f"{prefix}ForearmExtensorLine", [(7, 0.0), (19, 0.0), (29, 0.0)], 1.15, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(7, hi_y), (18, hi_y * 0.9), (28, hi_y * 0.65)], 2.2, HIGHLIGHT, 2.5))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(5, sh_y), (18, sh_y * 0.95), (28, sh_y * 0.7)], 3.2, CORE_SHADOW, 3.2))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -7, 8, skin)))
    out.append(f"{i2}</Node>")

    # Layer D: Black Flanged Rubber Rope Stopper emerging from the top of the fist
    stop_dir = -1.0 if far else 1.0
    out.append(
        f'{i2}<Node x="{f(p0[hand_k][0])}" y="{f(p0[hand_k][1])}" '
        f'rotation="{f(p0[stop_rot_k])}" name="{prefix}RopeStopper" id="{stop_id}">'
    )
    out.append(ellipse_shape(i3, f"{prefix}StopperCapTop", stop_dir * 4.5, -9.5, 13.5, 7.5, cap_paint, rot_deg=stop_dir * 18.0))
    out.append(ellipse_shape(i3, f"{prefix}StopperBody", stop_dir * 3.5, -7.2, 11.5, 9.0, stopper_paint, rot_deg=stop_dir * 18.0))
    out.append(polyline_stroke_shape(i3, f"{prefix}RopeStem", [(0.0, 0.0), (stop_dir * 3.0, -6.5)], 4.2, "FF0F172A", radius=0.5))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def cable_and_rope_rig():
    """Diagonal Tensioned Low-Pulley Cable + Chrome Swivel Eyelet + Dual Braided Rope Attachment
    rendered behind the athlete's torso/head, exactly matching the reference illustration."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    cable_id, swivel_id, rope_near_id, rope_far_id = nid(), nid(), nid(), nid()
    key_double(cable_id, 15, lambda p: p["cable_ang"])
    key_double(cable_id, 16, lambda p: p["cable_sc"])

    key_double(swivel_id, 13, lambda p: p["swivel"][0])
    key_double(swivel_id, 14, lambda p: p["swivel"][1])

    key_double(rope_near_id, 13, lambda p: p["swivel"][0])
    key_double(rope_near_id, 14, lambda p: p["swivel"][1])
    key_double(rope_near_id, 15, lambda p: p["rope_near_ang"])
    key_double(rope_near_id, 16, lambda p: p["rope_near_sc"])

    key_double(rope_far_id, 13, lambda p: p["swivel"][0])
    key_double(rope_far_id, 14, lambda p: p["swivel"][1])
    key_double(rope_far_id, 15, lambda p: p["rope_far_ang"])
    key_double(rope_far_id, 16, lambda p: p["rope_far_sc"])

    p0 = POSES[0]

    pulley_housing = (
        '<Fill name="PulleyFill"><SolidColor colorValue="FF1E293B" name="PulleyCol"/></Fill>'
        '<Stroke thickness="1.2" name="PulleyStroke"><SolidColor colorValue="FF64748B" name="PulleyStrokeCol"/></Stroke>'
    )
    swivel_paint = (
        '<Fill name="SwivelFill"><SolidColor colorValue="FFE2E8F0" name="SwivelCol"/></Fill>'
        '<Stroke thickness="1.0" name="SwivelStroke"><SolidColor colorValue="FF334155" name="SwivelStrokeCol"/></Stroke>'
    )

    return "\n".join([
        f'{ind}<Node name="CableAndRopeAssembly">',
        # 1. Dual Braided Black Ropes from Swivel -> Hands
        f'{i2}<Node x="{f(p0["swivel"][0])}" y="{f(p0["swivel"][1])}" rotation="{f(p0["rope_near_ang"])}" scaleX="{f(p0["rope_near_sc"])}" name="RopeNearBranch" id="{rope_near_id}">',
        polyline_stroke_shape(i3, "RopeNearHi", [(2.0, -0.8), (26.0, -0.8)], 1.2, "FF475569", radius=0.3),
        polyline_stroke_shape(i3, "RopeNearCore", [(0.0, 0.0), (28.0, 0.0)], 4.4, "FF090D16", radius=0.5),
        f"{i2}</Node>",
        f'{i2}<Node x="{f(p0["swivel"][0])}" y="{f(p0["swivel"][1])}" rotation="{f(p0["rope_far_ang"])}" scaleX="{f(p0["rope_far_sc"])}" name="RopeFarBranch" id="{rope_far_id}">',
        polyline_stroke_shape(i3, "RopeFarHi", [(2.0, -0.8), (26.0, -0.8)], 1.2, "FF475569", radius=0.3),
        polyline_stroke_shape(i3, "RopeFarCore", [(0.0, 0.0), (28.0, 0.0)], 4.4, "FF090D16", radius=0.5),
        f"{i2}</Node>",
        # 2. Chrome Swivel Eyelet
        f'{i2}<Node x="{f(p0["swivel"][0])}" y="{f(p0["swivel"][1])}" name="CableSwivelNode" id="{swivel_id}">',
        ellipse_shape(i3, "CableSwivelBall", 0.0, 0.0, 6.5, 6.5, swivel_paint),
        f"{i2}</Node>",
        # 3. Diagonal Tensioned Steel Cable from Low Floor Pulley (394, 294) to Swivel
        f'{i2}<Node x="{f(CABLE_ANCHOR[0])}" y="{f(CABLE_ANCHOR[1])}" rotation="{f(p0["cable_ang"])}" scaleX="{f(p0["cable_sc"])}" name="DiagonalCableNode" id="{cable_id}">',
        polyline_stroke_shape(i3, "SteelCableHi", [(0.0, -0.5), (200.0, -0.5)], 0.9, "FF94A3B8", radius=0.2),
        polyline_stroke_shape(i3, "SteelCableCore", [(0.0, 0.0), (200.0, 0.0)], 2.4, "FF0F172A", radius=0.2),
        f"{i2}</Node>",
        # 4. Compact Low Floor Pulley Anchor behind Athlete
        ellipse_shape(i2, "LowPulleyWheel", CABLE_ANCHOR[0], CABLE_ANCHOR[1], 12.0, 12.0, pulley_housing),
        ellipse_shape(i2, "LowPulleyHub", CABLE_ANCHOR[0], CABLE_ANCHOR[1], 4.5, 4.5, swivel_paint),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 2. Canonical Standing 3/4 Athlete Body
def torso_and_head():
    """Standing 3/4 front-left torso, sculpted pectorals, 6-pack abs, dark athletic compression shorts,
    and volumetric 3/4 head."""
    ind = "        "
    i2 = ind + "    "

    head_pts = pts_y([
        (304.0, 50.0), (301.5, 56.5), (300.0, 62.5), (301.2, 67.5),
        (301.8, 73.5), (307.5, 76.5), (316.5, 75.0), (323.5, 71.0),
        (328.5, 63.0), (328.0, 52.0), (321.0, 45.0), (311.0, 45.0),
    ])
    hair_pts = pts_y([
        (303.5, 52.0), (309.0, 44.5), (320.5, 44.2), (328.5, 50.5),
        (329.0, 61.5), (324.5, 65.5), (323.0, 57.5), (318.0, 52.5),
        (310.5, 51.0),
    ])
    head_hi = pts_y([(304.5, 54.0), (308.5, 49.0), (317.0, 48.0)])
    cheek_hi = pts_y([(303.5, 61.5), (309.5, 63.0), (315.0, 62.0)])
    jaw_sh = pts_y([(304.0, 75.5), (313.0, 76.2), (320.5, 72.5)])

    neck_pts = pts_y([
        (306.5, 73.0), (322.5, 70.0), (334.0, 86.0),
        (338.0, 94.0), (296.0, 92.0), (304.0, 83.0),
    ])
    scm_line = pts_y([(320.0, 72.5), (315.5, 82.0), (312.5, 90.5)])

    torso_pts = pts_y([
        (287.0, 91.0), (313.0, 88.5), (347.0, 93.0),
        (350.0, 113.0), (342.5, 134.0), (335.5, 154.0),
        (338.0, 174.0), (315.0, 182.0), (293.0, 174.0),
        (296.0, 152.0), (294.0, 132.0), (286.0, 111.0),
    ])
    torso_hi = pts_y([(299.0, 98.0), (301.0, 122.0), (303.0, 146.0)])
    torso_sh = pts_y([(340.0, 116.0), (334.5, 138.0), (330.5, 154.0)])

    pec_near_pts = pts_y([
        (313.5, 92.5), (339.5, 95.0), (345.5, 108.0),
        (339.5, 119.5), (325.0, 121.5), (313.0, 117.5),
    ])
    pec_far_pts = pts_y([
        (289.5, 93.0), (312.5, 92.5), (312.0, 117.0),
        (298.5, 119.0), (288.0, 112.0), (287.5, 100.5),
    ])
    pec_paint = (
        '<Fill name="PecFill"><SolidColor colorValue="120F172A" name="PecCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="PecStroke"><SolidColor colorValue="380F172A" name="PecStrokeCol"/></Stroke>'
    )

    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1A0F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="AbsEdge"><SolidColor colorValue="400F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        pts_y([(313.0, 121.0), (325.0, 121.5), (325.5, 130.0), (312.8, 129.5)]),
        pts_y([(312.6, 131.5), (324.8, 132.0), (324.2, 140.5), (312.4, 140.0)]),
        pts_y([(312.2, 142.0), (323.5, 142.5), (322.0, 151.5), (312.0, 151.0)]),
        pts_y([(301.5, 121.0), (310.5, 121.0), (310.3, 129.5), (301.2, 129.0)]),
        pts_y([(301.2, 131.0), (310.2, 131.5), (310.0, 140.0), (301.2, 139.5)]),
        pts_y([(301.5, 141.5), (309.8, 142.0), (309.5, 151.0), (302.0, 150.5)]),
    ]

    pelvis_shorts = pts_y([
        (296.0, 153.0), (313.0, 155.0), (336.0, 154.0),
        (341.0, 176.0), (322.0, 186.0), (311.0, 184.0), (292.0, 176.0),
    ])

    out = [f'{ind}<Node name="TorsoAndHead">']

    # 1. Volumetric 3/4 Head
    _, h_y0 = pt_y((0, 44))
    _, h_y1 = pt_y((0, 77))
    _, ear_y = pt_y((0, 64.5))
    out.append(smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 304, h_y0, 329, pt_y((0, 65))[1], "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i2, "Ear", 321.5, ear_y, 5.2, 7.8, solid("Ear", "FFA3B1C4"), rot_deg=12.0))
    out.append(stroke_shape(i2, "BrowShade", pts_y([(301.5, 56.8), (306.0, 57.2)]), 1.4, "590F172A", 0.8))
    out.append(stroke_shape(i2, "EyeLine", pts_y([(303.2, 58.6), (306.2, 58.8)]), 1.1, "730F172A", 0.4))
    out.append(stroke_shape(i2, "MouthLine", pts_y([(301.5, 68.5), (305.0, 68.8)]), 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i2, "HeadHi", head_hi, 3.0, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i2, "CheekHi", cheek_hi, 2.2, "80FFFFFF", 2.5))
    out.append(stroke_shape(i2, "JawShadow", jaw_sh, 2.6, CORE_SHADOW, 2.5))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill("Head", h_y0, h_y1, SKIN, x0=300, x1=328)))

    # 2. Muscular Neck & Clavicles
    out.append(stroke_shape(i2, "UnderChinShadow", pts_y([(306.5, 76.5), (313.5, 77.5), (320.0, 74.5)]), 3.0, CORE_SHADOW, 2.5))
    out.append(stroke_shape(i2, "SCMLine", scm_line, 1.4, SOFT_SHADOW, 1.5))
    out.append(stroke_shape(i2, "ClavicleLine", pts_y([(296.0, 92.5), (312.5, 92.0), (336.0, 94.5)]), 1.4, SOFT_SHADOW, 1.2))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", pt_y((0, 70))[1], pt_y((0, 94))[1], SKIN)))

    # 3. Pelvis Shorts & Waistband
    out.append(stroke_shape(i2, "WaistbandLine", pts_y([(296.5, 155.5), (314.0, 157.5), (335.5, 156.5)]), 1.8, "660F172A", 0.8))
    out.append(stroke_shape(i2, "ShortsFlyLine", pts_y([(312.0, 157.5), (311.5, 176.0)]), 1.3, "660F172A", 0.8))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill("PelvisShorts", pt_y((0, 153))[1], pt_y((0, 186))[1], SHORTS)))

    # 4. Sculpted 6-Pack Abs, Obliques, Ribcage Serratus Lines & Pectorals
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "LineaAlba", pts_y([(312.0, 118.0), (311.5, 136.0), (311.0, 153.0)]), 1.3, "470F172A", 0.8))
    out.append(stroke_shape(i2, "SerratusRibLine1", pts_y([(339.0, 118.0), (331.0, 121.0), (326.0, 122.5)]), 1.2, "380F172A", 0.9))
    out.append(stroke_shape(i2, "SerratusRibLine2", pts_y([(338.0, 124.0), (330.0, 127.0), (325.0, 128.5)]), 1.2, "380F172A", 0.9))
    out.append(stroke_shape(i2, "ObliqueLine1", pts_y([(336.0, 134.0), (330.0, 140.0), (326.0, 145.0)]), 1.3, "380F172A", 1.0))
    out.append(stroke_shape(i2, "ObliqueLine2", pts_y([(334.0, 142.0), (328.0, 148.0), (324.0, 152.0)]), 1.3, "380F172A", 1.0))

    out.append(stroke_shape(i2, "PecNearLowerSh", pts_y([(312.5, 118.0), (324.5, 122.0), (338.0, 119.5)]), 2.4, CORE_SHADOW, 2.0))
    out.append(stroke_shape(i2, "PecFarLowerSh", pts_y([(293.0, 113.0), (301.0, 119.5), (311.0, 117.5)]), 2.2, CORE_SHADOW, 2.0))
    out.append(stroke_shape(i2, "PecNearHi", pts_y([(316.0, 105.0), (328.0, 106.5), (337.0, 109.0)]), 2.6, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i2, "PecNear", pec_near_pts, pec_paint))
    out.append(smooth_shape(i2, "PecFar", pec_far_pts, pec_paint))

    # 5. Torso Base
    out.append(stroke_shape(i2, "TorsoHi", torso_hi, 4.5, HIGHLIGHT, 4.5))
    out.append(stroke_shape(i2, "TorsoSh", torso_sh, 6.0, CORE_SHADOW, 5.5))
    out.append(smooth_shape(i2, "Torso", torso_pts, skin_fill("Torso", pt_y((0, 89))[1], pt_y((0, 182))[1], SKIN, x0=294, x1=346)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def near_leg():
    """Near (left) leg planted on FLOOR=300 in 3/4 view."""
    ind = "        "
    i2 = ind + "    "

    shorts_pts = pts_y([
        (313.0, 168.0), (339.5, 166.0), (344.5, 192.0),
        (315.5, 194.0), (312.0, 178.0),
    ])
    thigh_pts = pts_y([
        (315.0, 174.0), (340.0, 172.0), (346.5, 196.0),
        (343.0, 218.0), (338.0, 232.0), (322.0, 232.0),
        (317.5, 214.0), (314.5, 194.0),
    ])
    thigh_hi = pts_y([(324.0, 192.0), (325.0, 210.0), (326.0, 224.0)])
    thigh_sh = pts_y([(341.0, 192.0), (340.0, 212.0), (336.0, 228.0)])
    quad_med_line = pts_y([(324.0, 200.0), (321.0, 214.0), (324.0, 225.0)])
    quad_lat_line = pts_y([(335.0, 194.0), (336.5, 212.0), (333.5, 226.0)])

    shin_pts = pts_y([
        (322.5, 230.0), (338.0, 230.0), (346.5, 248.0),
        (345.0, 266.0), (339.5, 288.0), (328.5, 289.0),
        (325.0, 268.0), (322.0, 248.0),
    ])
    shin_hi = pts_y([(327.0, 240.0), (328.5, 262.0), (330.0, 282.0)])
    shin_sh = pts_y([(342.0, 246.0), (341.5, 264.0), (337.5, 284.0)])
    calf_cut = pts_y([(334.0, 246.0), (338.5, 258.0), (335.5, 270.0)])

    foot_pts = pts_y([
        (328.5, 286.0), (340.0, 286.0), (343.5, 297.5),
        (334.0, 300.5), (314.0, 301.5), (309.5, 297.5),
        (316.0, 292.5),
    ])

    return "\n".join([
        f'{ind}<Node name="NearLeg">',
        stroke_shape(i2, "NearShortsHem", pts_y([(315.5, 192.5), (329.5, 193.0), (344.0, 190.5)]), 1.6, "660F172A", 0.6),
        smooth_shape(i2, "NearThighShorts", shorts_pts, skin_fill("NearThighShorts", pt_y((0, 166))[1], pt_y((0, 194))[1], SHORTS)),
        stroke_shape(i2, "NearQuadMedLine", quad_med_line, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearQuadLatLine", quad_lat_line, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearThighHi", thigh_hi, 4.0, HIGHLIGHT, 4.0),
        stroke_shape(i2, "NearThighSh", thigh_sh, 5.2, CORE_SHADOW, 5.0),
        smooth_shape(i2, "NearThigh", thigh_pts, skin_fill("NearThigh", pt_y((0, 172))[1], pt_y((0, 232))[1], SKIN)),
        ellipse_shape(i2, "NearKnee", 329.5, pt_y((0, 231.0))[1], 16.0, 14.0, skin_fill("NearKnee", -7, 7, SKIN)),
        stroke_shape(i2, "NearFootHi", pts_y([(329.0, 290.0), (319.0, 295.0), (312.5, 298.0)]), 2.2, HIGHLIGHT, 2.5),
        smooth_shape(i2, "NearFoot", foot_pts, skin_fill("NearFoot", pt_y((0, 286))[1], pt_y((0, 302))[1], SKIN)),
        stroke_shape(i2, "NearCalfCut", calf_cut, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearShinHi", shin_hi, 3.2, HIGHLIGHT, 3.5),
        stroke_shape(i2, "NearShinSh", shin_sh, 4.5, CORE_SHADOW, 4.5),
        smooth_shape(i2, "NearShin", shin_pts, skin_fill("NearShin", pt_y((0, 230))[1], pt_y((0, 289))[1], SKIN)),
        f"{ind}</Node>",
    ])


def far_leg():
    """Far (right) leg planted slightly further back-left in 3/4 perspective."""
    ind = "        "
    i2 = ind + "    "

    shorts_pts = pts_y([
        (292.0, 166.0), (315.0, 168.0), (314.0, 190.0),
        (289.5, 188.0),
    ])
    thigh_pts = pts_y([
        (291.0, 172.0), (314.0, 174.0), (313.0, 198.0),
        (309.5, 224.0), (294.5, 224.0), (289.5, 204.0),
        (288.0, 186.0),
    ])
    thigh_hi = pts_y([(294.5, 188.0), (295.5, 206.0), (297.0, 220.0)])
    thigh_sh = pts_y([(309.0, 190.0), (308.0, 208.0), (306.0, 222.0)])
    quad_line = pts_y([(302.5, 192.0), (303.5, 208.0), (301.5, 220.0)])

    shin_pts = pts_y([
        (295.0, 222.0), (309.5, 222.0), (316.0, 242.0),
        (314.5, 260.0), (309.5, 281.0), (299.0, 282.0),
        (296.5, 260.0), (294.5, 242.0),
    ])
    shin_hi = pts_y([(298.5, 232.0), (299.5, 254.0), (301.0, 274.0)])
    shin_sh = pts_y([(312.0, 240.0), (311.0, 258.0), (307.5, 276.0)])

    foot_pts = pts_y([
        (299.0, 279.0), (310.0, 279.0), (313.0, 289.5),
        (303.0, 292.5), (284.0, 293.5), (279.5, 289.5),
        (286.5, 285.0),
    ])

    return "\n".join([
        f'{ind}<Node name="FarLeg">',
        smooth_shape(i2, "FarThighShorts", shorts_pts, skin_fill("FarThighShorts", pt_y((0, 166))[1], pt_y((0, 190))[1], SHORTS_FAR)),
        stroke_shape(i2, "FarQuadLine", quad_line, 1.2, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "FarThighHi", thigh_hi, 3.4, HIGHLIGHT, 3.5),
        stroke_shape(i2, "FarThighSh", thigh_sh, 4.6, CORE_SHADOW, 4.5),
        smooth_shape(i2, "FarThigh", thigh_pts, skin_fill("FarThigh", pt_y((0, 172))[1], pt_y((0, 224))[1], SKIN_FAR)),
        ellipse_shape(i2, "FarKnee", 301.5, pt_y((0, 223.5))[1], 15.0, 13.5, skin_fill("FarKnee", -7, 7, SKIN_FAR)),
        smooth_shape(i2, "FarFoot", foot_pts, skin_fill("FarFoot", pt_y((0, 279))[1], pt_y((0, 294))[1], SKIN_FAR)),
        stroke_shape(i2, "FarShinHi", shin_hi, 2.8, HIGHLIGHT, 3.0),
        stroke_shape(i2, "FarShinSh", shin_sh, 4.0, CORE_SHADOW, 4.0),
        smooth_shape(i2, "FarShin", shin_pts, skin_fill("FarShin", pt_y((0, 222))[1], pt_y((0, 282))[1], SKIN_FAR)),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 3. Scene Assembly (RML First Child = Topmost Layer)
def build_rml():
    global _id
    _id = 0
    KEYED.clear()

    near_arm_xml = tricep_arm_rig("Near", False)
    torso_head_xml = torso_and_head()
    near_leg_xml = near_leg()
    far_leg_xml = far_leg()
    far_arm_xml = tricep_arm_rig("Far", True)
    cable_rope_xml = cable_and_rope_rig()

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
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="OverheadTricepExtension" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Left) Arm, Sculpted Triceps Brachii (Long & Lateral Heads) & Rope Stopper -->
{near_arm_xml}

        <!-- 2. Standing 3/4 Athlete Torso, Sculpted Pectorals, 6-Pack Abs & Volumetric Head -->
{torso_head_xml}

        <!-- 3. Near (Left) Standing Leg on Floor -->
{near_leg_xml}

        <!-- 4. Far (Right) Standing Leg in 3/4 Depth -->
{far_leg_xml}

        <!-- 5. Far (Right) Arm, Sculpted Triceps Brachii & Rope Stopper -->
{far_arm_xml}

        <!-- 6. Background: Diagonal Tensioned Low-Pulley Cable, Chrome Swivel & Dual Braided Ropes -->
{cable_rope_xml}

        <!-- 7. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="322" y="{f(FLOOR - 2)}" scaleX="0.96" scaleY="0.09" name="BodyShadow">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="OverheadTricepExtension" id="0:60">
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
    riv_bytes = _compile_rml_bytes(OUT)
    (BUILD / "overhead_tricep_extension.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (38, "frame_mid"), (72, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(680, 14, 305))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
