#!/usr/bin/env python3
"""Generate bicycle_crunch.rml — 3/4 supine Bicycle Crunch at 60fps (16:9 640x360).

Matches the ab_wheel_rollout / bench_dips / bench_press / bicep_curl_barbell standard:
- Same character palette (`SKIN`, `SKIN_FAR`, `SHORTS`, `HIGHLIGHT`, `CORE_SHADOW`,
  `MUSCLE_LOW` -> `MUSCLE_HIGH`), Catmull-Rom smooth curves, and 16:9 (`640x360`,
  `FLOOR = 300.0`) artboard.
- Supine 3/4 side view on a beveled exercise mat (`FLOOR = 300.0`) matching the
  three-phase FitnessRx reference illustration:
  1. Left Elbow to Right Knee (`twist = -1.0`, `frame = 0`):
     Far (left) elbow reaches up-right across toward the flexed near (right) knee
     (`~90 deg`), while the far (left) leg extends straight out at `~20 deg` above
     the mat and the near (right) elbow opens down-left toward the mat.
  2. Center Crunch (`twist = 0.0`, `frame = 50` & `frame = 150`):
     Both legs pass through the 90/90 tabletop crunch position as the upper torso
     stays curled off the mat and switches rotation side.
  3. Right Elbow to Left Knee (`twist = +1.0`, `frame = 100`):
     Near (right) elbow sweeps high up-right across toward the flexed far (left)
     knee, while the near (right) leg extends straight out at `~20 deg` above the mat.
- Muscle activations (`muscle_t` peaking at `1.0` at both cross-crunch contractions
  and maintaining `0.40` warm orange-red core tension through the center crunch):
  * Rectus abdominis (sculpted 6-pack abdominal segments, near + far columns)
  * External oblique (lateral fan-shaped abdominal wall with diagonal fiber slips)

Run:
    python3 gen_bicycle_crunch.py            # writes bicycle_crunch.rml
    python3 gen_bicycle_crunch.py --publish  # builds .riv + copies asset & 256x256 thumbnail
"""
import math
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "scene.rml"
ASSET_RIV = REPO / "assets/animations/bicycle_crunch.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/bicycle_crunch.png"
THUMB_ADVANCE = "0.0s"  # Peak Left-Elbow-to-Right-Knee cross-crunch contraction
THUMB_VIEWPORT = "1280x720"  # 2x the 640x360 artboard
THUMB_CROP = (680, 40, 260)  # square size, offsetY, offsetX in the 2x render
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

# 16:9 standard canvas
W, H = 640, 360
FLOOR = 300.0

# Anthropometric limb lengths
THIGH_LEN = 78.0
SHIN_LEN = 74.0
UPPER_ARM_LEN = 50.0
FOREARM_LEN = 46.0

# Pelvis / hip joint anchors resting on the exercise mat
HIP_NEAR = (306.0, 272.0)
HIP_FAR = (298.0, 263.0)

# Timeline: 200 frames @ 60fps (3.33s full alternating cycle)
# f0..14: Hold Left Elbow -> Right Knee (twist = -1.0)
# f14..86: Transition through Center Crunch (f50, twist = 0.0) to Right Elbow -> Left Knee (f86, twist = +1.0)
# f86..114: Hold Right Elbow -> Left Knee (twist = +1.0)
# f114..186: Transition through Center Crunch (f150, twist = 0.0) back to Left Elbow -> Right Knee (f186, twist = -1.0)
# f186..200: Hold Left Elbow -> Right Knee (twist = -1.0)
DURATION = 200
STEP = 2


def cubic_bezier(x1, y1, x2, y2):
    def bez(t, a, b):
        return 3 * a * t * (1 - t) ** 2 + 3 * b * t * t * (1 - t) + t ** 3

    def ease(x):
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if bez(mid, x1, x2) < x:
                lo = mid
            else:
                hi = mid
        return bez((lo + hi) / 2, y1, y2)

    return ease


EASE = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def twist_param(frame):
    """Returns twist in [-1.0, +1.0]:
    -1.0 = Left Elbow to Right Knee (f0..14, f186..200)
     0.0 = Center Crunch (f50, f150)
    +1.0 = Right Elbow to Left Knee (f86..114)
    """
    fr = frame % DURATION
    if fr <= 14:
        return -1.0
    if fr <= 50:
        return -1.0 + EASE((fr - 14) / 36.0)
    if fr <= 86:
        return EASE((fr - 50) / 36.0)
    if fr <= 114:
        return 1.0
    if fr <= 150:
        return 1.0 - EASE((fr - 114) / 36.0)
    if fr <= 186:
        return -EASE((fr - 150) / 36.0)
    return -1.0


def lerp(a, b, t):
    return a + (b - a) * t


def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def pose(tw):
    """Compute full supine bicycle crunch kinematics at twist tw in [-1.0, +1.0]."""
    # Leg extension weights:
    # At tw = -1 (Left Elbow -> Right Knee): Far leg extended (1.0), Near leg flexed (0.0)
    # At tw =  0 (Center Crunch): BOTH legs flexed in tabletop (0.0, 0.0)
    # At tw = +1 (Right Elbow -> Left Knee): Near leg extended (1.0), Far leg flexed (0.0)
    ext_far = ((-tw) ** 1.12) if tw < 0.0 else 0.0
    ext_near = (tw ** 1.12) if tw > 0.0 else 0.0

    # Near (Right) Leg angles:
    # At tw = -1 (active crunch side), right thigh pulls closer to chest (-108 deg);
    # at tw =  0 (center tabletop), right thigh is at -95 deg;
    # at tw = +1 (extended bicycle pedal), right thigh extends to -16 deg.
    flex_near_pull = max(0.0, -tw)
    thigh_near_flexed = lerp(-95.0, -108.0, flex_near_pull)
    thigh_near = math.radians(lerp(thigh_near_flexed, -16.0, ext_near))
    shin_near_world = math.radians(lerp(-6.0 + 4.0 * flex_near_pull, -11.0, ext_near))
    shin_near_local = shin_near_world - thigh_near
    foot_near_world = math.radians(lerp(-66.0, -58.0, ext_near))
    foot_near_local = foot_near_world - shin_near_world

    # Far (Left) Leg angles:
    # At tw = +1 (active crunch side), left thigh pulls closer to chest (-110 deg);
    # at tw =  0 (center tabletop), left thigh is at -98 deg;
    # at tw = -1 (extended bicycle pedal), left thigh extends to -18 deg.
    flex_far_pull = max(0.0, tw)
    thigh_far_flexed = lerp(-98.0, -110.0, flex_far_pull)
    thigh_far = math.radians(lerp(thigh_far_flexed, -18.0, ext_far))
    shin_far_world = math.radians(lerp(-9.0 + 4.0 * flex_far_pull, -13.0, ext_far))
    shin_far_local = shin_far_world - thigh_far
    foot_far_world = math.radians(lerp(-68.0, -60.0, ext_far))
    foot_far_local = foot_far_world - shin_far_world

    # Spine & Head curl:
    # Spine origin is at HIP_NEAR (306, 272). Local +x runs along the spine toward the shoulders (~ -151 deg).
    # Neck flexes forward (+43..+47 deg) so the chin is tucked toward the chest/knees (neck world angle ~ -106 deg).
    crunch_lift = abs(tw)
    spine = math.radians(lerp(-153.5, -149.0, crunch_lift) + 1.5 * tw)
    neck_local = math.radians(lerp(43.0, 47.0, crunch_lift) - 2.0 * tw)
    neck_world_ang = spine + neck_local

    # Neck base in world space
    neck_world = add(HIP_NEAR, rot((94.0, -1.0), spine))

    # Shoulder anchors in world space (near right shoulder + far left shoulder)
    sh_near = add(HIP_NEAR, rot((84.0, lerp(-10.0, -3.0, (tw + 1.0) / 2.0)), spine))
    sh_far = add(HIP_NEAR, rot((88.0, lerp(11.0, 4.0, (tw + 1.0) / 2.0)), spine))

    # Elbow trajectories across the 3 phases (tw = -1, 0, +1):
    #   tw = -1 (Left Elbow -> Right Knee): Near elbow open down-left (174, 254), Far elbow reaches Right Knee (266, 178)
    #   tw =  0 (Center Crunch): Near elbow open down-left below jaw (182, 238), Far elbow open above head (218, 158)
    #   tw = +1 (Right Elbow -> Left Knee): Near elbow reaches Left Knee (264, 204), Far elbow flared back-left (172, 196)
    if tw <= 0.0:
        u = tw + 1.0  # 0 at tw=-1 -> 1 at tw=0
        elb_near = (lerp(174.0, 182.0, u), lerp(254.0, 238.0, u))
        elb_far = (lerp(266.0, 218.0, u), lerp(178.0, 158.0, u))
    else:
        u = tw  # 0 at tw=0 -> 1 at tw=+1
        elb_near = (lerp(182.0, 264.0, u), lerp(238.0, 204.0, u))
        elb_far = (lerp(218.0, 172.0, u), lerp(158.0, 196.0, u))

    # Hands cup the back/side of the head behind the ear (never extending past the cranium)
    u_pos = max(0.0, tw)
    hand_near = add(neck_world, rot((lerp(21.0, 17.0, u_pos), lerp(-5.0, 1.5, u_pos)), neck_world_ang))
    hand_far = add(neck_world, rot((lerp(26.0, 23.0, u_pos), lerp(3.0, -3.0, u_pos)), neck_world_ang))

    def seg_xform(p0, p1, base_len):
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        ang = math.atan2(dy, dx)
        sc = math.hypot(dx, dy) / base_len
        return ang, sc

    ua_near_ang, ua_near_sc = seg_xform(sh_near, elb_near, UPPER_ARM_LEN)
    fa_near_ang, fa_near_sc = seg_xform(elb_near, hand_near, FOREARM_LEN)
    ua_far_ang, ua_far_sc = seg_xform(sh_far, elb_far, UPPER_ARM_LEN)
    fa_far_ang, fa_far_sc = seg_xform(elb_far, hand_far, FOREARM_LEN)

    return {
        "tw": tw,
        "ext_near": ext_near,
        "ext_far": ext_far,
        "spine": spine,
        "neck_local": neck_local,
        "thigh_near": thigh_near,
        "shin_near_local": shin_near_local,
        "foot_near_local": foot_near_local,
        "thigh_far": thigh_far,
        "shin_far_local": shin_far_local,
        "foot_far_local": foot_far_local,
        "sh_near": sh_near,
        "elb_near": elb_near,
        "hand_near": hand_near,
        "ua_near_ang": ua_near_ang,
        "ua_near_sc": ua_near_sc,
        "fa_near_ang": fa_near_ang,
        "fa_near_sc": fa_near_sc,
        "sh_far": sh_far,
        "elb_far": elb_far,
        "hand_far": hand_far,
        "ua_far_ang": ua_far_ang,
        "ua_far_sc": ua_far_sc,
        "fa_far_ang": fa_far_ang,
        "fa_far_sc": fa_far_sc,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)


def unwrap_into(poses, key):
    vals = [poses[fr][key] for fr in FRAMES]
    out = [vals[0]]
    for v in vals[1:]:
        while v - out[-1] > math.pi:
            v -= 2.0 * math.pi
        while v - out[-1] < -math.pi:
            v += 2.0 * math.pi
        out.append(v)
    for fr, v in zip(FRAMES, out):
        poses[fr][key] = v


POSES = {fr: pose(twist_param(fr)) for fr in FRAMES}
for k in ("ua_near_ang", "fa_near_ang", "ua_far_ang", "fa_far_ang"):
    unwrap_into(POSES, k)

# ---------------------------------------------------------------- helpers
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


# ---------------------------------------------------------------- palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF334155", "FF1E293B", "FF0F172A")
SHORTS_FAR = ("FF1E293B", "FF111827", "FF090D16")
SHOE_UPPER = ("FFFFFFFF", "FFE2E8F0", "FF94A3B8")
SHOE_FAR = ("FFE2E8F0", "FFCBD5E1", "FF64748B")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "4D0F172A"
MUSCLE_LOW = (0x66, 0xFB, 0x92, 0x3C)   # warm orange at low tension
MUSCLE_HIGH = (0xF2, 0xEF, 0x44, 0x44)  # intense crimson-red at peak cross-crunch
MUSCLE_LINE_LOW = (0x4D, 0xC2, 0x41, 0x0C)
MUSCLE_LINE_HIGH = (0xCC, 0x8B, 0x1A, 0x1A)


def argb_lerp(a, b, t):
    return "".join(f"{round(lerp(x, y, t)):02X}" for x, y in zip(a, b))


def skin_fill(name, y0, y1, tones, x0=0, x1=0):
    return f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *tones, x0=x0, x1=x1)}</Fill>'


keys = []  # (objectId, propertyKey, kind, [(frame, value)])


def key_double(obj, prop, fn):
    keys.append((obj, prop, "double", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def key_color(obj, prop, fn):
    keys.append((obj, prop, "color", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def muscle_t(p):
    """Peaks at 1.0 at both cross-crunch contractions (|tw| = 1.0), dips to 0.40 at Center Crunch (tw = 0)."""
    return 0.40 + 0.60 * (abs(p["tw"]) ** 1.2)


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


# ---------------------------------------------------------------- Anatomy & Rig Builders
def arm_rig(prefix, far):
    """Articulated arm (UpperArm: shoulder -> elbow, Forearm: elbow -> hand behind head)."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    sh_key = "sh_far" if far else "sh_near"
    elb_key = "elb_far" if far else "elb_near"
    ua_ang_key = "ua_far_ang" if far else "ua_near_ang"
    ua_sc_key = "ua_far_sc" if far else "ua_near_sc"
    fa_ang_key = "fa_far_ang" if far else "fa_near_ang"
    fa_sc_key = "fa_far_sc" if far else "fa_near_sc"

    ua_id, fa_id = nid(), nid()
    key_double(ua_id, 13, lambda p: p[sh_key][0])
    key_double(ua_id, 14, lambda p: p[sh_key][1])
    key_double(ua_id, 15, lambda p: p[ua_ang_key])
    key_double(ua_id, 16, lambda p: p[ua_sc_key])

    key_double(fa_id, 13, lambda p: p[elb_key][0])
    key_double(fa_id, 14, lambda p: p[elb_key][1])
    key_double(fa_id, 15, lambda p: p[fa_ang_key])
    key_double(fa_id, 16, lambda p: p[fa_sc_key])
    p0 = POSES[0]

    ua_pts = [
        (-9, 0), (-7, -8.5), (6, -10.5), (24, -10.0), (40, -7.8), (48, -5.8),
        (53, 0), (48, 5.8), (36, 8.8), (20, 10.2), (5, 9.8), (-7, 7.5),
    ]
    delt_pts = [
        (-12, 0), (-8, -10.5), (3, -12.5), (15, -9.0), (19, 0),
        (14, 8.5), (3, 11.2), (-8, 8.5),
    ]
    fa_pts = [
        (-5, 0), (-4, -6.8), (7, -8.2), (20, -6.5), (31, -4.5),
        (36, 0), (31, 4.5), (19, 6.5), (6, 7.2), (-4, 5.8),
    ]
    hand_pts = [
        (-2, -4.8), (5, -5.5), (11, -3.0), (12, 2.0), (6, 5.0), (-2, 4.5),
    ]

    out = [f'{ind}<Node name="{prefix}ArmGroup">']

    # Forearm + Hand cupping back of cranium (terminates strictly at x=FOREARM_LEN=44)
    out.append(
        f'{i2}<Node x="{f(p0[elb_key][0])}" y="{f(p0[elb_key][1])}" '
        f'rotation="{f(p0[fa_ang_key])}" scaleX="{f(p0[fa_sc_key])}" name="{prefix}Forearm" id="{fa_id}">'
    )
    out.append(smooth_shape(i3, f"{prefix}Hand", hand_pts, skin_fill(prefix + "Hand", -5, 5, skin), x=FOREARM_LEN - 12.0))
    if not far:
        out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(5, -4.5), (18, -4.0), (30, -2.5)], 2.4, HIGHLIGHT, 3.0))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(5, 4.5), (18, 4.0), (30, 2.5)], 3.6, CORE_SHADOW, 4.0))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -8, 7, skin)))
    out.append(f"{i2}</Node>")

    # Upper Arm + Deltoid cap
    out.append(
        f'{i2}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" '
        f'rotation="{f(p0[ua_ang_key])}" scaleX="{f(p0[ua_sc_key])}" name="{prefix}UpperArm" id="{ua_id}">'
    )
    if not far:
        out.append(stroke_shape(i3, f"{prefix}DeltHi", [(-4, -6.5), (5, -8.0), (13, -5.0)], 2.8, HIGHLIGHT, 3.0))
        out.append(stroke_shape(i3, f"{prefix}UpperArmHi", [(8, -6.2), (24, -6.0), (38, -4.5)], 2.8, HIGHLIGHT, 3.5))
    out.append(smooth_shape(i3, f"{prefix}Deltoid", delt_pts, skin_fill(prefix + "Deltoid", -12, 11, skin)))
    out.append(stroke_shape(i3, f"{prefix}UpperArmSh", [(8, 6.5), (24, 6.8), (40, 5.0)], 4.2, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UpperArm", -11, 10, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def leg_rig(prefix, far):
    """Articulated Leg (Hip -> Thigh -> Shin -> Athletic Shoe) with white-panel shorts matching reference."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "
    skin = SKIN_FAR if far else SKIN
    shorts = SHORTS_FAR if far else SHORTS
    shoe_tones = SHOE_FAR if far else SHOE_UPPER
    hx, hy = HIP_FAR if far else HIP_NEAR
    th_key = "thigh_far" if far else "thigh_near"
    sh_key = "shin_far_local" if far else "shin_near_local"
    ft_key = "foot_far_local" if far else "foot_near_local"

    th_id, sh_id, ft_id = nid(), nid(), nid()
    key_double(th_id, 15, lambda p: p[th_key])
    key_double(sh_id, 15, lambda p: p[sh_key])
    key_double(ft_id, 15, lambda p: p[ft_key])
    p0 = POSES[0]

    # Limb local frame: +x runs Hip(0) -> Knee(78) -> Ankle(74).
    # Since thigh angles are in [-100 deg, -16 deg], local +y faces UP-RIGHT (anterior quad / shin)
    # and local -y faces DOWN-LEFT (posterior hamstring / calf)!
    thigh_pts = [
        (-18, 0), (-14, 12.5), (8, 17.2), (32, 17.5), (55, 14.5), (70, 10.5),
        (82, 0), (72, -9.5), (54, -12.0), (32, -15.5), (10, -18.5), (-14, -14.0),
    ]
    thigh_hi = [(12, 12.5), (36, 13.0), (60, 9.5)]
    thigh_sh = [(10, -13.5), (36, -11.0), (60, -7.5)]
    shorts_thigh_pts = [
        (-22, 0), (-16, 14.5), (8, 19.2), (42, 18.8),
        (45, -14.5), (16, -19.5), (-6, -21.0), (-19, -14.0),
    ]
    # Crisp white athletic side panel on the shorts (matching the FitnessRx illustration)
    stripe_pts = [
        (4, 15.5), (39, 15.8), (41, 4.5), (10, 5.5),
    ]

    shin_pts = [
        (-10, 0), (-8, 8.2), (14, 8.8), (40, 7.2), (62, 5.2), (73, 4.5),
        (77, 0), (72, -5.2), (56, -7.0), (34, -12.5), (16, -14.8), (2, -12.0), (-8, -8.5),
    ]
    shin_hi = [(12, 5.2), (38, 4.8), (62, 3.2)]
    shin_sh = [(16, -10.5), (36, -9.0), (58, -5.0)]

    # Detailed athletic cross-trainer shoe (+x runs along foot sole/instep)
    shoe_pts = [
        (-10, -6.5), (-8, 7.0), (8, 8.5), (24, 6.2), (31, 1.5),
        (28, -4.5), (12, -6.5), (-4, -7.2),
    ]
    sole_pts = [
        (-10, -6.2), (10, -6.2), (28, -4.2), (29, -1.5), (10, -3.2), (-9, -3.2),
    ]

    out = [f'{ind}<Node x="{f(hx)}" y="{f(hy)}" rotation="{f(p0[th_key])}" name="{prefix}Thigh" id="{th_id}">']

    # 1. Shin + Athletic Shoe
    out.append(f'{i2}<Node x="{f(THIGH_LEN)}" rotation="{f(p0[sh_key])}" name="{prefix}Shin" id="{sh_id}">')
    out.append(f'{i3}<Node x="{f(SHIN_LEN)}" rotation="{f(p0[ft_key])}" name="{prefix}Foot" id="{ft_id}">')
    out.append(smooth_shape(i4, f"{prefix}ShoeSole", sole_pts, solid(prefix + "Sole", "FF0F172A")))
    out.append(stroke_shape(i4, f"{prefix}ShoeStripe", [(0, 2.5), (12, 0.5), (21, -1.0)], 2.0, "FF1E293B", 0.0))
    out.append(smooth_shape(i4, f"{prefix}ShoeBody", shoe_pts, skin_fill(prefix + "Shoe", -7, 9, shoe_tones)))
    out.append(f"{i3}</Node>")

    out.append(ellipse_shape(i3, f"{prefix}KneeCap", 0, 1, 20, 18, skin_fill(prefix + "Knee", -9, 9, skin)))
    if not far:
        out.append(stroke_shape(i3, f"{prefix}ShinHi", shin_hi, 3.4, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i3, f"{prefix}ShinSh", shin_sh, 4.5, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i3, f"{prefix}ShinShape", shin_pts, skin_fill(prefix + "Shin", -14, 9, skin)))
    out.append(f"{i2}</Node>")

    # 2. Compression Shorts + White Side Panel + Thigh
    out.append(smooth_shape(i2, f"{prefix}ShortsStripe", stripe_pts, solid(prefix + "Stripe", "D9F8FAFC" if not far else "B3CBD5E1")))
    out.append(smooth_shape(i2, f"{prefix}ThighShorts", shorts_thigh_pts, skin_fill(prefix + "ThighShorts", -20, 19, shorts)))
    if not far:
        out.append(stroke_shape(i2, f"{prefix}ThighHi", thigh_hi, 4.0, HIGHLIGHT, 4.0))
    out.append(stroke_shape(i2, f"{prefix}ThighSh", thigh_sh, 5.5, CORE_SHADOW, 5.5))
    out.append(smooth_shape(i2, f"{prefix}ThighShape", thigh_pts, skin_fill(prefix + "Thigh", -18, 18, skin)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def torso_and_head_rig():
    """Supine curled Torso, Head & Neck, Rectus Abdominis (6-pack), and External Oblique activations."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "
    spine_id, neck_id, twist_id = nid(), nid(), nid()
    key_double(spine_id, 15, lambda p: p["spine"])
    key_double(neck_id, 15, lambda p: p["neck_local"])
    # Subtle 3/4 ribcage/muscle shift with torso twist (-3.5 px to +3.5 px along local y)
    key_double(twist_id, 14, lambda p: lerp(-2.5, 3.5, (p["tw"] + 1.0) / 2.0))
    p0 = POSES[0]

    # Spine local frame: origin at HIP_NEAR (306, 272).
    # Since spine angle is ~ -151 deg (pointing up-left), local +x runs from Pelvis(0) -> Clavicles(96),
    # local +y points UP-RIGHT (anterior belly / chest / nose!), and local -y points DOWN-LEFT (back on mat!).
    torso_pts = [
        (-22, -6), (-24, 8), (-12, 19), (8, 21.5), (30, 19.5), (52, 20.5),
        (74, 24.5), (92, 22.0), (102, 12.0), (102, -4.0), (92, -16.5),
        (72, -20.5), (48, -17.5), (24, -16.5), (2, -19.0), (-14, -16.0),
    ]
    torso_hi = [(18, 15.0), (45, 16.0), (74, 18.5)]
    torso_sh = [(14, -13.0), (46, -13.0), (76, -15.0)]
    pelvis_shorts = [
        (-25, -8), (-24, 10), (-10, 20.5), (18, 22.0),
        (20, -18.5), (-2, -20.0), (-18, -16.5),
    ]

    # Activated Rectus Abdominis (4 sculpted upper/lower blocks along the anterior +y contour)
    rectus_near_blocks = [
        [(20, 8.5), (31, 8.5), (31, 18.2), (20, 18.8)],
        [(33, 8.2), (44, 8.2), (44, 18.0), (33, 18.0)],
        [(46, 8.5), (57, 9.2), (57, 19.0), (46, 18.2)],
        [(59, 9.8), (70, 11.2), (70, 21.2), (59, 19.5)],
    ]
    rectus_far_blocks = [
        [(21, 18.8), (31, 18.2), (31, 22.2), (21, 22.5)],
        [(33, 18.0), (44, 18.0), (44, 22.0), (33, 22.0)],
        [(46, 18.2), (57, 19.0), (57, 23.2), (46, 22.2)],
    ]

    # Activated External Oblique (broad lateral fan from lower ribs (x=66) to iliac crest (x=18))
    ext_oblique_pts = [
        (18, -3.5), (34, -6.5), (52, -5.5), (67, -1.0),
        (64, 9.5), (48, 8.2), (32, 8.0), (18, 8.2),
    ]
    oblique_slips = [
        [(62, 0.5), (50, 4.5), (38, 6.5)],
        [(52, -2.5), (40, 2.0), (28, 4.5)],
        [(42, -4.0), (30, 0.0), (20, 2.5)],
    ]

    # Sculpted Pectoralis Major & Latissimus border (neutral skin tone with athletic definition)
    pec_pts = [
        (68, 4.0), (88, 6.5), (94, 16.5), (84, 23.5), (70, 21.5), (65, 12.0),
    ]
    pec_paint = (
        '<Fill name="PecFill"><SolidColor colorValue="140F172A" name="PecCol"/></Fill>'
        '<Stroke thickness="0.95" join="round" name="PecStroke"><SolidColor colorValue="380F172A" name="PecStrokeCol"/></Stroke>'
    )

    # Volumetric 3/4 Head & Neck in Neck local space (+x up toward crown, +y forward-right toward knees)
    neck_pts = [(-6, -8.5), (14, -8.5), (16, 9.5), (-6, 9.5)]
    head_pts = [
        (8, -4.5),    # base of occiput
        (14, -15.0),  # lower back of skull
        (27, -17.0),  # posterior parietal cranium
        (39, -11.5),  # top-back of skull
        (43, 0.5),    # crown of skull
        (39, 12.5),   # upper forehead
        (31, 16.8),   # brow ridge (facing forward-right toward the knees)
        (23, 20.2),   # nose bridge & tip (projecting right toward the knees)
        (17, 17.8),   # upper/lower lips
        (11, 16.2),   # strong chin (tucked toward chest)
        (9, 7.5),     # jawline / mandible
        (11, 0.5),    # jaw angle below ear
    ]
    hair_pts = [
        (13, -14.2), (26, -17.6), (39, -12.2), (44, 0.5),
        (40, 11.8), (34, 8.2), (33, -1.0), (25, -6.8), (15, -5.5),
    ]
    head_hi = [(38, 1.5), (34, 11.0), (25, 15.2)]

    out = [f'{ind}<Node x="{f(HIP_NEAR[0])}" y="{f(HIP_NEAR[1])}" name="PelvisRoot">']
    out.append(f'{i2}<Node rotation="{f(p0["spine"])}" name="Spine" id="{spine_id}">')

    # 1. Head & Neck (drawn above the upper chest)
    out.append(f'{i3}<Node x="94" y="-1" rotation="{f(p0["neck_local"])}" name="Neck" id="{neck_id}">')
    out.append(smooth_shape(i4, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 44, 0, 14, -16, "FF334155", "FF0F172A")}</Fill>'))
    out.append(ellipse_shape(i4, "Ear", 19, -1.5, 6.5, 9.5, solid("Ear", "FFA3B1C4"), rot_deg=-20.0))
    out.append(stroke_shape(i4, "EyeBrow", [(31.5, 12.5), (29.5, 16.2)], 1.4, "660F172A", 0.5))
    out.append(stroke_shape(i4, "JawLine", [(11.5, 14.5), (10.0, 7.5), (13.5, 1.0)], 2.2, CORE_SHADOW, 2.0))
    out.append(stroke_shape(i4, "HeadHi", head_hi, 3.2, HIGHLIGHT, 3.5))
    out.append(smooth_shape(i4, "Head", head_pts, skin_fill("Head", -17, 20, SKIN)))
    out.append(smooth_shape(i4, "NeckShape", neck_pts, skin_fill("Neck", -9, 10, SKIN)))
    out.append(f"{i3}</Node>")

    # 2. Activated Core Muscles (Rectus Abdominis + External Oblique) & Pectorals
    tc_y0 = lerp(-2.5, 3.5, (p0["tw"] + 1.0) / 2.0)
    out.append(f'{i3}<Node y="{f(tc_y0)}" name="TorsoCoreGroup" id="{twist_id}">')
    for idx, slip in enumerate(oblique_slips):
        out.append(stroke_shape(i4, f"ObliqueSlip{idx + 1}", slip, 1.1, "738B1A1A", 0.6))
    out.append(smooth_shape(i4, "ExternalObliqueActivation", ext_oblique_pts, muscle_paint("ExtOblique", 0.95)))
    for idx, pts in enumerate(rectus_near_blocks):
        out.append(smooth_shape(i4, f"RectusNear{idx + 1}", pts, muscle_paint(f"RectusNear{idx + 1}", 0.9)))
    for idx, pts in enumerate(rectus_far_blocks):
        out.append(smooth_shape(i4, f"RectusFar{idx + 1}", pts, muscle_paint(f"RectusFar{idx + 1}", 0.85)))
    out.append(stroke_shape(i4, "LineaAlba", [(20, 18.2), (45, 18.2), (70, 20.5)], 1.2, "668B1A1A", 0.6))
    out.append(stroke_shape(i4, "PecHi", [(72, 10.0), (84, 12.5), (90, 17.5)], 2.6, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i4, "PecMajor", pec_pts, pec_paint))
    out.append(f"{i3}</Node>")

    # 3. Pelvic Shorts & Torso Silhouette
    out.append(smooth_shape(i3, "PelvisShorts", pelvis_shorts, skin_fill("PelvisShorts", -20, 22, SHORTS)))
    out.append(stroke_shape(i3, "TorsoHi", torso_hi, 4.2, HIGHLIGHT, 4.5))
    out.append(stroke_shape(i3, "TorsoSh", torso_sh, 5.8, CORE_SHADOW, 5.5))
    out.append(smooth_shape(i3, "Torso", torso_pts, skin_fill("Torso", -20, 24, SKIN)))

    out.append(f"{i2}</Node>")
    out.append(f"{ind}</Node>")
    return "\n".join(out)


def exercise_mat_and_shadow():
    """3/4 beveled exercise mat on FLOOR=300 plus dynamic athlete shadow."""
    ind = "        "
    i2 = ind + "    "
    mat_top = f'<Fill name="MatTopFill">{grad("MatTopGrad", 110, 282, 530, 300, "FF334155", "FF1E293B")}</Fill>'
    mat_edge = f'<Fill name="MatEdgeFill">{grad("MatEdgeGrad", 110, 296, 530, 303, "FF475569", "FF0F172A")}</Fill>'

    sh_id = nid()
    key_double(sh_id, 13, lambda p: lerp(310.0, 336.0, max(p["ext_near"], p["ext_far"])))
    key_double(sh_id, 16, lambda p: lerp(1.10, 1.38, max(p["ext_near"], p["ext_far"])))
    p0 = POSES[0]
    sx0 = lerp(1.10, 1.38, max(p0["ext_near"], p0["ext_far"]))
    cx0 = lerp(310.0, 336.0, max(p0["ext_near"], p0["ext_far"]))

    return "\n".join([
        f'{ind}<Node name="ExerciseMat">',
        # Contact shadow of athlete on the mat surface
        f'{i2}<Shape x="{f(cx0)}" y="291" scaleX="{f(sx0)}" scaleY="0.065" name="MatContactShadow" id="{sh_id}">\n'
        f'{i2}    <Ellipse width="220" height="220" name="MatContactEllipse"/>\n'
        f'{i2}    <Fill name="MatContactFill"><RadialGradient startX="0" startY="0" endX="110" endY="0" name="MatContactGrad">'
        f'<GradientStop colorValue="BF000000" position="0"/><GradientStop colorValue="59000000" position="0.6"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{i2}</Shape>",
        # 3/4 perspective exercise mat top & front bevel
        stroke_shape(i2, "MatTopHi", [(112, 295.5), (320, 295.5), (528, 295.5)], 1.2, "40FFFFFF", 0.5, cap="butt"),
        poly_shape(i2, "MatTop", [(124, 284), (512, 284), (534, 296), (106, 296)], mat_top, radius=3.0),
        poly_shape(i2, "MatFrontEdge", [(106, 295), (534, 295), (534, 300), (106, 300)], mat_edge, radius=1.5),
        f"{ind}</Node>",
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


near_leg_xml = leg_rig("Near", False)
near_arm_xml = arm_rig("Near", False)
torso_head_xml = torso_and_head_rig()
far_arm_xml = arm_rig("Far", True)
far_leg_xml = leg_rig("Far", True)
mat_xml = exercise_mat_and_shadow()

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
    <!-- Bicycle Crunch: 3/4 supine view, 60 fps, 16:9 (640x360), generated by gen_bicycle_crunch.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="BicycleCrunch" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- Near (right) leg in foreground -->
{near_leg_xml}

        <!-- Near (right) arm cradling head & sweeping toward left knee -->
{near_arm_xml}

        <!-- Curled Torso, Activated Rectus Abdominis + External Oblique, Head & Neck -->
{torso_head_xml}

        <!-- Far (left) arm cradling head & sweeping toward right knee -->
{far_arm_xml}

        <!-- Far (left) leg in 3/4 depth -->
{far_leg_xml}

        <!-- 3/4 Beveled Exercise Mat & Contact Shadow -->
{mat_xml}

{scenery()}

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

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="BicycleCrunch" id="0:60">
{keyed_xml()}
        </LinearAnimation>
    </Artboard>
</Rive>
"""

OUT.write_text(rml)

for fr in (0, 50, 100, 150, DURATION):
    P = POSES[fr]
    print(
        f"f{fr:3d} tw={P['tw']:+.2f} ext=({P['ext_near']:.2f},{P['ext_far']:.2f}) "
        f"elb_near=({P['elb_near'][0]:.1f},{P['elb_near'][1]:.1f}) "
        f"elb_far=({P['elb_far'][0]:.1f},{P['elb_far'][1]:.1f})"
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
    header = bytes([
        82, 73, 86, 69, 7, 3, 0, 196, 1, 236, 1, 238, 3, 229, 4, 230, 4, 231, 4,
        232, 4, 233, 4, 234, 4, 235, 4, 236, 4, 241, 4, 242, 4, 237, 5, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0,
    ])
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
    """Build the .riv, copy it into the Flutter assets and render the catalog thumbnail."""
    built = HERE / "build/bicycle_crunch.riv"
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
