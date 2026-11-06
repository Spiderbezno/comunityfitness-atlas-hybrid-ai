#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive 7.3 scene for Mountain Climber (id: 'mountain_climber').

Uses our canonical 3/4 front-right CommunityFitness mannequin (volumetric 3/4 head with hair/ear/brow/eye/mouth,
muscular neck, sculpted pectorals, serratus anterior, 6-pack abs & external obliques, deltoids/biceps/triceps/
forearms with hands planted flat on FLOOR = 300.0 in a high plank, dark athletic compression shorts, sculpted
quadriceps/hip-flexors/calves, and bare feet) performing alternating explosive Mountain Climbers.

Matches the 2-panel 3/4 front-right Mountain Climber reference illustration (media_1793638154854_13d71825.jpg)
and execution guide (media_1793638151842_3f1b2e04.webp):
  - Left Panel (f = 0 & f = 120, t_near = 1.0, t_far = 0.0):
    * Athlete holds a strong high plank with hands planted shoulder-width apart on the floor.
    * Near (right) knee drives forward under the chest while the far (left) leg extends straight back
      with toes planted on the floor.
  - Right Panel (f = 60, t_near = 0.0, t_far = 1.0):
    * Legs reciprocally switch in a fast climbing sprint: the far (left) knee drives forward under the
      chest while the near (right) leg extends straight back onto the ball/toes of the foot.
  - Highlighted Target Muscle Groups (pulsing from warm orange #FFF97316 to intense crimson #FFF43F5E):
    1. Rectus femoris & Iliopsoas / Hip Flexors (Primary — anterior thigh drive on both legs)
    2. Vastus lateralis & Vastus medialis (Primary/Synergist — quadriceps stabilization & drive)
    3. Rectus abdominis & External obliques (Primary Core — waist & abdominal flexion/stabilization)
    4. Serratus anterior & Anterior deltoid (Secondary — isometric high-plank shoulder bracing)

Run:
    python3 gen_mountain_climber.py            # writes scene.rml
    python3 gen_mountain_climber.py --publish  # compiles assets/animations/mountain_climber.riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/mountain_climber.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/mountain_climber.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 120  # 2.0s high-tempo alternating mountain climber loop (both legs complete a full cycle)
STEP = 2

# Segment Lengths for Exact 2-Bone IK (Hip -> Knee -> Ankle)
L_THIGH_NEAR = 76.0
L_SHIN_NEAR = 74.0
L_THIGH_FAR = 74.0
L_SHIN_FAR = 72.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("B8475569", "C72B3649", "D6172033")
SHORTS_FAR = ("C2334155", "CF1E293B", "DC0F172A")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "4D0F172A"

# Target Muscle Heat Colors: warm orange (#FFF97316) -> intense crimson (#FFF43F5E)
MUSCLE_LOW = (0xD9, 0xF9, 0x73, 0x16)
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


EASE_SWITCH = cubic_bezier(0.38, 0.0, 0.22, 1.0)


def climb_phase(frame):
    """Returns reciprocal phase s in [0.0, 1.0] across 120 frames:
    - s = 0.0 (f = 0..10 & 110..120): Left Panel — Near (Right) Knee driven to chest, Far (Left) Leg extended back
    - s: 0.0 -> 1.0 (f = 10..50):     Explosive reciprocal leg switch #1
    - s = 1.0 (f = 50..70):           Right Panel — Far (Left) Knee driven to chest, Near (Right) Leg extended back
    - s: 1.0 -> 0.0 (f = 70..110):    Explosive reciprocal leg switch #2
    """
    fr = frame % (DURATION + 1)
    if fr <= 10:
        return 0.0
    if fr <= 50:
        return EASE_SWITCH((fr - 10) / 40.0)
    if fr <= 70:
        return 1.0
    if fr <= 110:
        return 1.0 - EASE_SWITCH((fr - 70) / 40.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def solve_plank_leg_ik(hip, ankle, l1, l2):
    """2-bone IK from hip -> knee -> ankle in a rightward-facing (+X) high plank.
    Using -acos(cos_a) bends the knee toward (+X, +Y), i.e. forward-right under the chest!"""
    dx = ankle[0] - hip[0]
    dy = ankle[1] - hip[1]
    d = max(1.0, min(l1 + l2 - 2.2, math.hypot(dx, dy)))
    base_ang = math.atan2(dy, dx)
    cos_a = max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2.0 * l1 * d)))
    thigh_ang = base_ang - math.acos(cos_a)
    knee = (hip[0] + l1 * math.cos(thigh_ang), hip[1] + l1 * math.sin(thigh_ang))
    shin_ang = math.atan2(ankle[1] - knee[1], ankle[0] - knee[0])
    return thigh_ang, knee, shin_ang


def pose(s):
    """Compute full 3/4 High-Plank Mountain Climber transforms at phase s in [0.0, 1.0]."""
    # t_near = 1.0 when Near (Right) knee is driven forward to chest (s = 0.0, Left Panel)
    # t_far  = 1.0 when Far (Left) knee is driven forward to chest (s = 1.0, Right Panel)
    t_near = 1.0 - s
    t_far = s

    # Subtle athletic mid-switch hip/core pulse when both feet pass mid-air (s = 0.5)
    mid_pulse = math.sin(math.pi * s) ** 2
    hip_near = (264.0 + 2.0 * s, 162.0 - 4.0 * mid_pulse)
    hip_far = (252.0 - 2.0 * s, 152.0 - 4.0 * mid_pulse)
    torso_dy = -2.5 * mid_pulse

    # Near (Right) Leg:
    # - Extended back (t_near = 0.0, Right Panel): ankle at (154, 260), toes planted on FLOOR = 300.0
    # - Driven forward (t_near = 1.0, Left Panel): ankle at (218, 250), knee at ~(292, 232) under chest!
    ankle_near = (
        lerp(154.0, 218.0, t_near),
        lerp(260.0, 250.0, t_near) - 6.0 * math.sin(math.pi * t_near),
    )
    thigh_near_ang, knee_near, shin_near_ang = solve_plank_leg_ik(
        hip_near, ankle_near, L_THIGH_NEAR, L_SHIN_NEAR
    )
    foot_near_rot = math.radians(lerp(8.0, 22.0, t_near))

    # Far (Left) Leg:
    # - Extended back (t_far = 0.0, Left Panel): ankle at (142, 250), toes planted on FLOOR = 290.0 (3/4 depth)
    # - Driven forward (t_far = 1.0, Right Panel): ankle at (228, 240), knee at ~(302, 220) under chest!
    ankle_far = (
        lerp(142.0, 228.0, t_far),
        lerp(250.0, 240.0, t_far) - 6.0 * math.sin(math.pi * t_far),
    )
    thigh_far_ang, knee_far, shin_far_ang = solve_plank_leg_ik(
        hip_far, ankle_far, L_THIGH_FAR, L_SHIN_FAR
    )
    foot_far_rot = math.radians(lerp(8.0, 22.0, t_far))

    return {
        "s": s,
        "t_near": t_near,
        "t_far": t_far,
        "mid_pulse": mid_pulse,
        "hip_near": hip_near,
        "hip_far": hip_far,
        "torso_dy": torso_dy,
        "ankle_near": ankle_near,
        "knee_near": knee_near,
        "thigh_near_ang": thigh_near_ang,
        "shin_near_ang": shin_near_ang,
        "foot_near_rot": foot_near_rot,
        "ankle_far": ankle_far,
        "knee_far": knee_far,
        "thigh_far_ang": thigh_far_ang,
        "shin_far_ang": shin_far_ang,
        "foot_far_rot": foot_far_rot,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(climb_phase(fr)) for fr in FRAMES}


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


def muscle_paint_fn(name, fn_t, line=0.95):
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


# ---------------------------------------------------------------- 1. Posting Arms & Spread Hands on Floor
def build_posting_arm(indent, prefix, is_far):
    """Sculpted high-plank posting arm (Deltoid -> Upper Arm -> Forearm -> Spread Hand on FLOOR = 300.0),
    matching the 3/4 front-right Mountain Climber reference illustration."""
    i2 = indent + "    "
    skin = SKIN_FAR if is_far else SKIN

    def delt_t(p):
        return 0.45 + 0.35 * p["mid_pulse"]

    if is_far:
        # Far (Left) Arm planted in 3/4 depth at (448, 276)
        delt_pts = [
            (402.0, 158.0), (420.0, 156.0), (430.0, 170.0),
            (426.0, 188.0), (410.0, 190.0), (398.0, 174.0),
        ]
        ua_pts = [
            (408.0, 180.0), (426.0, 178.0), (436.0, 224.0),
            (420.0, 228.0), (408.0, 204.0),
        ]
        fa_pts = [
            (420.0, 220.0), (436.0, 218.0), (450.0, 268.0),
            (438.0, 272.0), (422.0, 244.0),
        ]
        hand_pts = [
            (438.0, 266.0), (454.0, 264.0), (476.0, 268.0),
            (478.0, 274.0), (458.0, 278.0), (436.0, 274.0),
        ]
    else:
        # Near (Right) Arm planted in foreground on FLOOR = 300.0 at (408, 296)
        delt_pts = [
            (366.0, 162.0), (388.0, 158.0), (400.0, 174.0),
            (394.0, 196.0), (374.0, 198.0), (362.0, 180.0),
        ]
        ua_pts = [
            (370.0, 186.0), (392.0, 184.0), (400.0, 238.0),
            (380.0, 242.0), (370.0, 214.0),
        ]
        fa_pts = [
            (380.0, 232.0), (400.0, 230.0), (414.0, 290.0),
            (398.0, 294.0), (382.0, 262.0),
        ]
        hand_pts = [
            (396.0, 288.0), (416.0, 286.0), (442.0, 292.0),
            (444.0, 299.0), (420.0, 301.0), (394.0, 298.0),
        ]

    out = [f'{indent}<Node name="{prefix}PostingArmGroup">']

    # 1. Spread Hand & Fingers Braced on the Floor
    if not is_far:
        out.append(stroke_shape(i2, "NearFingerLine1", [(418.0, 292.0), (438.0, 294.0)], 1.0, SOFT_SHADOW, 0.0))
        out.append(stroke_shape(i2, "NearFingerLine2", [(416.0, 296.0), (436.0, 298.0)], 1.0, SOFT_SHADOW, 0.0))
        out.append(stroke_shape(i2, "NearHandHi", [(402.0, 290.0), (424.0, 292.0)], 2.0, HIGHLIGHT, 2.0))
    else:
        out.append(stroke_shape(i2, "FarFingerLine1", [(454.0, 269.0), (472.0, 271.0)], 0.95, SOFT_SHADOW, 0.0))
    out.append(
        smooth_shape(
            i2,
            f"{prefix}PlantedHand",
            hand_pts,
            skin_fill(prefix + "Hand", hand_pts[0][1] - 4, hand_pts[4][1], skin),
        )
    )

    # 2. Sculpted Forearm (Brachioradialis & Extensor ridges)
    if not is_far:
        out.append(stroke_shape(i2, "NearForearmCrest", [(392.0, 238.0), (400.0, 264.0), (406.0, 286.0)], 1.2, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i2, "NearForearmHi", [(394.0, 238.0), (402.0, 264.0), (408.0, 286.0)], 2.6, HIGHLIGHT, 2.8))
        out.append(stroke_shape(i2, "NearForearmSh", [(384.0, 240.0), (390.0, 266.0), (398.0, 288.0)], 3.2, CORE_SHADOW, 3.2))
    out.append(
        smooth_shape(
            i2,
            f"{prefix}Forearm",
            fa_pts,
            skin_fill(prefix + "FA", fa_pts[1][1], fa_pts[3][1], skin),
        )
    )

    # 3. Sculpted Deltoid (on top of upper arm shoulder cap)
    if not is_far:
        out.append(stroke_shape(i2, "NearDeltGroove1", [(374.0, 174.0), (376.0, 192.0)], 1.15, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i2, "NearDeltGroove2", [(386.0, 172.0), (388.0, 190.0)], 1.15, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i2, "NearDeltHi", [(378.0, 164.0), (388.0, 174.0), (386.0, 190.0)], 2.8, HIGHLIGHT, 3.0))
        out.append(
            smooth_shape(
                i2,
                "NearAnteriorDelt",
                [(384.0, 164.0), (398.0, 172.0), (394.0, 192.0), (384.0, 188.0)],
                muscle_paint_fn("NearAntDelt", delt_t, 0.9),
            )
        )
    out.append(
        smooth_shape(
            i2,
            f"{prefix}Deltoid",
            delt_pts,
            skin_fill(prefix + "Delt", delt_pts[1][1], delt_pts[4][1], skin),
        )
    )

    # 4. Sculpted Upper Arm (Triceps & Biceps)
    if not is_far:
        out.append(stroke_shape(i2, "NearTricepsGroove", [(380.0, 196.0), (384.0, 218.0), (386.0, 234.0)], 1.2, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i2, "NearUpperArmHi", [(388.0, 194.0), (392.0, 216.0), (394.0, 234.0)], 2.8, HIGHLIGHT, 3.0))
        out.append(stroke_shape(i2, "NearUpperArmSh", [(374.0, 196.0), (376.0, 218.0), (380.0, 236.0)], 3.6, CORE_SHADOW, 3.6))
    out.append(
        smooth_shape(
            i2,
            f"{prefix}UpperArm",
            ua_pts,
            skin_fill(prefix + "UA", ua_pts[1][1], ua_pts[3][1], skin),
        )
    )

    out.append(f"{indent}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 2. Dynamic Reciprocal Legs (Near & Far Climbing Legs)
def build_climbing_leg(indent, prefix, is_far):
    """Builds either the Near (Right) or Far (Left) Mountain Climber leg driven by 2-bone IK:
    - Highlights the anterior Rectus femoris / Iliopsoas hip-flexor strip and Vastus lateralis /
      Vastus medialis quadriceps heads in glowing crimson-orange (matching media_1793638154854_13d71825.jpg)."""
    i2 = indent + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if is_far else SKIN
    shorts = SHORTS_FAR if is_far else SHORTS
    l_thigh = L_THIGH_FAR if is_far else L_THIGH_NEAR
    l_shin = L_SHIN_FAR if is_far else L_SHIN_NEAR

    hip_key = "hip_far" if is_far else "hip_near"
    knee_key = "knee_far" if is_far else "knee_near"
    ankle_key = "ankle_far" if is_far else "ankle_near"
    thigh_ang_key = "thigh_far_ang" if is_far else "thigh_near_ang"
    shin_ang_key = "shin_far_ang" if is_far else "shin_near_ang"
    foot_rot_key = "foot_far_rot" if is_far else "foot_near_rot"
    t_key = "t_far" if is_far else "t_near"

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

    # Both legs stay actively highlighted in orange-crimson across the whole exercise (just like both panels of
    # media_1793638154854_13d71825.jpg!), peaking in intense crimson when driving the knee toward the chest (t -> 1.0).
    def rectus_t(p):
        return 0.56 + 0.44 * (p[t_key] ** 0.8)

    def vastus_t(p):
        return 0.48 + 0.48 * (p[t_key] ** 0.8)

    # Local Thigh Coordinates: (0,0) = HIP, +X = toward KNEE (length l_thigh).
    # Since thigh_ang is in [+68 deg, +132 deg] (pointing down-right when tucked, down-left when extended):
    # local -Y points FORWARD-RIGHT / ANTERIOR (Rectus femoris, Vastus lateralis, Vastus medialis!)
    # local +Y points BACK-LEFT / POSTERIOR (Hamstrings & Glute insertion).
    thigh_pts = [
        (-14.0, -11.5), (10.0, -17.5), (38.0, -17.2), (62.0, -13.0),
        (l_thigh + 2.0, -5.5), (l_thigh + 2.0, 5.5), (60.0, 11.5),
        (34.0, 15.8), (8.0, 17.2), (-14.0, 12.5),
    ]
    shorts_cuff_pts = [
        (-16.0, -12.5), (20.0, -18.0), (22.0, 17.5), (-16.0, 13.5),
    ]
    # Rectus femoris / Hip-flexor anterior band (-Y local, separated from vastus lateralis by a silver tendon groove)
    rectus_pts = [
        (12.0, -16.8), (36.0, -16.8), (58.0, -13.2), (l_thigh - 6.0, -7.8),
        (l_thigh - 8.0, -3.5), (46.0, -6.8), (18.0, -8.5),
    ]
    # Vastus lateralis / medialis sweep (central-anterior thigh belly, matching the bold red muscle belly in reference)
    vastus_pts = [
        (18.0, -7.2), (42.0, -5.8), (62.0, -3.5), (l_thigh - 7.0, 1.2),
        (56.0, 6.2), (32.0, 6.8), (16.0, 2.5),
    ]

    # Local Shin Coordinates: (0,0) = KNEE, +X = toward ANKLE (length l_shin).
    #Since shin_ang is around +145 deg to +165 deg (pointing down-left toward the foot):
    # local -Y is ANTERIOR/LOWER shin (Tibia); local +Y is POSTERIOR/UPPER calf (Gastrocnemius & Soleus)!
    shin_pts = [
        (-7.0, -6.5), (18.0, -6.8), (46.0, -5.8), (l_shin - 3.0, -4.2),
        (l_shin + 2.0, 0.0), (l_shin - 4.0, 4.8), (52.0, 7.5),
        (32.0, 14.5), (14.0, 14.2), (-6.0, 7.2),
    ]

    # Dorsiflexed Bare Foot extending downward (+Y) from ANKLE (0,0) to the toes on the floor:
    foot_pts = [
        (-7.5, -3.5), (4.5, -2.0), (7.5, 10.0),
        (9.5, 28.0), (5.5, 34.0), (-0.5, 32.0),
        (-3.5, 18.0), (-8.5, 3.5),
    ]

    out = [f'{indent}<Node name="{prefix}ClimbingLegGroup">']

    # 1. Bare Foot (dorsiflexed toes pressing the floor when extended, hovering under hip when driving knee)
    out.append(
        f'{i2}<Node x="{f(p0[ankle_key][0])}" y="{f(p0[ankle_key][1])}" '
        f'rotation="{f(p0[foot_rot_key])}" name="{prefix}FootNode" id="{foot_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}FootArch", [(-2.0, 4.0), (1.0, 18.0), (3.5, 29.0)], 1.15, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}FootHi", [(2.5, 4.0), (5.5, 18.0), (7.0, 28.0)], 2.0, HIGHLIGHT, 2.2))
    out.append(smooth_shape(i3, f"{prefix}BareFoot", foot_pts, skin_fill(prefix + "Foot", -4, 34, skin)))
    out.append(f"{i2}</Node>")

    # 2. Lower Leg / Calf (Gastrocnemius & Tibialis contours)
    out.append(
        f'{i2}<Node x="{f(p0[knee_key][0])}" y="{f(p0[knee_key][1])}" '
        f'rotation="{f(p0[shin_ang_key])}" name="{prefix}ShinNode" id="{shin_id}">'
    )
    out.append(ellipse_shape(i3, f"{prefix}KneeCap", 0.0, -1.0, 17.5, 15.5, skin_fill(prefix + "Knee", -8, 8, skin)))
    out.append(stroke_shape(i3, f"{prefix}GastrocLine", [(12.0, 6.5), (30.0, 8.8), (48.0, 4.8)], 1.2, SOFT_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}ShinHi", [(12.0, -4.2), (38.0, -3.8), (62.0, -2.5)], 2.4, HIGHLIGHT, 2.5))
    out.append(stroke_shape(i3, f"{prefix}CalfSh", [(12.0, 11.2), (30.0, 12.2), (50.0, 6.0)], 3.0, CORE_SHADOW, 3.0))
    out.append(smooth_shape(i3, f"{prefix}ShinShape", shin_pts, skin_fill(prefix + "Shin", -7, 15, skin)))
    out.append(f"{i2}</Node>")

    # 3. Thigh with Glowing Quadriceps & Hip Flexors (Rectus femoris + Vastus lateralis/medialis)
    out.append(
        f'{i2}<Node x="{f(p0[hip_key][0])}" y="{f(p0[hip_key][1])}" '
        f'rotation="{f(p0[thigh_ang_key])}" name="{prefix}ThighNode" id="{thigh_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}ShortsHem", [(20.0, -17.2), (21.0, 0.0), (20.0, 16.8)], 1.4, "800F172A", 0.6))
    out.append(smooth_shape(i3, f"{prefix}ShortsCuff", shorts_cuff_pts, skin_fill(prefix + "Shorts", -18, 18, shorts)))
    out.append(stroke_shape(i3, f"{prefix}TendonStrip", [(18.0, -7.5), (42.0, -6.2), (62.0, -4.0)], 2.2, HIGHLIGHT, 1.8))
    out.append(stroke_shape(i3, f"{prefix}QuadHi", [(22.0, -13.5), (44.0, -12.5), (60.0, -8.5)], 2.4, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i3, f"{prefix}VastusQuad", vastus_pts, muscle_paint_fn(prefix + "Vastus", vastus_t, 1.0)))
    out.append(smooth_shape(i3, f"{prefix}RectusFemoris", rectus_pts, muscle_paint_fn(prefix + "Rectus", rectus_t, 1.05)))
    out.append(stroke_shape(i3, f"{prefix}ThighPostSh", [(14.0, 12.5), (36.0, 11.5), (56.0, 8.0)], 3.6, CORE_SHADOW, 3.6))
    out.append(smooth_shape(i3, f"{prefix}ThighShape", thigh_pts, skin_fill(prefix + "Thigh", -18, 17, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{indent}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. Braced High-Plank Torso, Core Muscles & 3/4 Head
def build_plank_torso_and_head():
    """Canonical 3/4 front-right CommunityFitness torso in a high plank:
    - Dark compression shorts wrapping the elevated pelvis & glutes
    - Braced ribcage with sculpted Serratus anterior, Rectus abdominis, and External obliques
      pulsing with core activation
    - Volumetric 3/4 Head & Neck looking down-right toward the floor ahead of the hands."""
    ind = "        "
    i2 = ind + "    "

    torso_id = nid()
    key_double(torso_id, 14, lambda p: p["torso_dy"])
    p0 = POSES[0]

    def core_t(p):
        return 0.48 + 0.46 * p["mid_pulse"] + 0.18 * abs(p["t_near"] - p["t_far"])

    # Pelvis & Dark Athletic Compression Shorts at the top-left of the plank arch (x ~ 232..288, y ~ 124..182)
    pelvis_shorts_pts = [
        (232.0, 144.0), (246.0, 124.0), (274.0, 124.0),
        (288.0, 134.0), (282.0, 178.0), (254.0, 182.0), (234.0, 168.0),
    ]

    # Braced High-Plank Torso from waist (274, 130..178) to shoulders (404, 154..192)
    torso_pts = [
        (268.0, 130.0), (312.0, 128.0), (358.0, 136.0), (402.0, 156.0),
        (408.0, 178.0), (386.0, 194.0), (344.0, 188.0), (304.0, 180.0),
        (272.0, 176.0),
    ]

    # Core / Waist Target Muscles (External Obliques + Rectus Abdominis + Serratus Anterior) along the lower ribcage/waist
    oblique_pts = [
        (282.0, 152.0), (314.0, 154.0), (338.0, 166.0),
        (332.0, 182.0), (302.0, 178.0), (278.0, 172.0),
    ]
    abs_strip_pts = [
        (286.0, 168.0), (322.0, 172.0), (354.0, 182.0),
        (348.0, 189.0), (314.0, 183.0), (282.0, 176.0),
    ]
    serratus_pts = [
        (332.0, 152.0), (358.0, 158.0), (352.0, 176.0), (326.0, 168.0),
    ]

    # Volumetric 3/4 Head & Muscular Neck angled down-right at (416..468, 166..218)
    neck_pts = [
        (398.0, 158.0), (422.0, 168.0), (428.0, 192.0),
        (402.0, 192.0), (392.0, 176.0),
    ]
    head_pts = [
        (424.0, 172.0), (438.0, 166.0), (454.0, 168.0), (466.0, 178.0),
        (468.0, 192.0), (460.0, 204.0), (448.0, 212.0), (436.0, 212.0),
        (426.0, 206.0), (418.0, 194.0), (418.0, 182.0),
    ]
    hair_pts = [
        (430.0, 170.0), (444.0, 165.5), (458.0, 169.0), (467.5, 180.0),
        (467.0, 194.0), (458.0, 203.0), (455.0, 194.0), (448.0, 184.0),
        (436.0, 176.0),
    ]

    out = [f'{ind}<Node y="{f(p0["torso_dy"])}" name="PlankTorsoAndHeadNode" id="{torso_id}">']

    # 1. Volumetric 3/4 Head & Neck (looking down at the floor ahead of the hands)
    out.append(smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 430, 166, 468, 202, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i2, "Ear", 436.0, 190.0, 5.5, 7.8, solid("Ear", "FFA3B1C4"), rot_deg=35.0))
    out.append(stroke_shape(i2, "BrowShade", [(450.0, 204.0), (455.0, 200.5)], 1.3, "590F172A", 0.6))
    out.append(stroke_shape(i2, "EyeLine", [(447.5, 204.5), (451.5, 202.0)], 1.05, "730F172A", 0.4))
    out.append(stroke_shape(i2, "MouthLine", [(435.5, 208.0), (439.5, 206.0)], 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i2, "HeadCrownHi", [(432.0, 172.0), (446.0, 171.0), (456.0, 178.0)], 2.8, HIGHLIGHT, 3.2))
    out.append(stroke_shape(i2, "JawShadow", [(422.0, 198.0), (432.0, 208.0), (444.0, 209.0)], 2.4, CORE_SHADOW, 2.4))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill("Head", 166, 212, SKIN, x0=418, x1=468)))
    out.append(stroke_shape(i2, "NeckMuscleLine", [(404.0, 170.0), (418.0, 178.0), (426.0, 186.0)], 1.5, SOFT_SHADOW, 1.2))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", 158, 192, SKIN)))

    # 2. Dark Athletic Compression Shorts on Elevated Hips
    out.append(stroke_shape(i2, "ShortsWaistSeam", [(276.0, 128.0), (282.0, 152.0), (278.0, 176.0)], 1.5, "800F172A", 0.8))
    out.append(stroke_shape(i2, "ShortsGluteHi", [(244.0, 132.0), (264.0, 130.0), (276.0, 138.0)], 2.6, "40FFFFFF", 2.8))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts_pts, skin_fill("PelvisShorts", 124, 182, SHORTS, x0=232, x1=288)))

    # 3. Sculpted High-Plank Torso, Serratus Anterior, External Obliques & Rectus Abdominis
    out.append(stroke_shape(i2, "SerratusRib1", [(334.0, 154.0), (348.0, 164.0)], 1.2, "730F172A", 0.6))
    out.append(stroke_shape(i2, "SerratusRib2", [(322.0, 152.0), (336.0, 162.0)], 1.2, "730F172A", 0.6))
    out.append(stroke_shape(i2, "ObliqueRib1", [(296.0, 154.0), (312.0, 166.0)], 1.2, "730F172A", 0.6))
    out.append(stroke_shape(i2, "ObliqueRib2", [(284.0, 154.0), (300.0, 166.0)], 1.2, "730F172A", 0.6))
    out.append(smooth_shape(i2, "SerratusAnterior", serratus_pts, muscle_paint_fn("Serratus", core_t, 0.9)))
    out.append(smooth_shape(i2, "ExternalObliques", oblique_pts, muscle_paint_fn("Obliques", core_t, 0.95)))
    out.append(smooth_shape(i2, "RectusAbdominis", abs_strip_pts, muscle_paint_fn("RectusAbs", core_t, 0.95)))
    out.append(stroke_shape(i2, "LatDorsiCrest", [(292.0, 140.0), (334.0, 144.0), (370.0, 156.0)], 1.4, SOFT_SHADOW, 1.2))
    out.append(stroke_shape(i2, "TorsoBackHi", [(284.0, 133.0), (330.0, 134.0), (376.0, 148.0)], 3.8, HIGHLIGHT, 4.2))
    out.append(stroke_shape(i2, "TorsoBellySh", [(286.0, 172.0), (330.0, 178.0), (374.0, 186.0)], 3.8, CORE_SHADOW, 3.8))
    out.append(smooth_shape(i2, "PlankTorso", torso_pts, skin_fill("Torso", 128, 194, SKIN, x0=268, x1=408)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def build_rml():
    global _id, KEYED
    _id = 0
    KEYED = []

    near_arm_xml = build_posting_arm("        ", "Near", False)
    near_leg_xml = build_climbing_leg("        ", "Near", False)
    torso_xml = build_plank_torso_and_head()
    far_leg_xml = build_climbing_leg("        ", "Far", True)
    far_arm_xml = build_posting_arm("        ", "Far", True)

    grouped = {}
    for oid, kp_xml in KEYED:
        grouped.setdefault(oid, []).append(kp_xml)
    keyed_objects_xml = "\n".join(
        f'        <KeyedObject objectId="{oid}">\n' + "\n".join(props) + "\n        </KeyedObject>"
        for oid, props in grouped.items()
    )

    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"

    return f"""<Rive version="7.3">
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="MountainClimber" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Right) Posting Arm Braced on Floor -->
{near_arm_xml}

        <!-- 2. Near (Right) Climbing Leg (Rectus femoris, Vastus lateralis/medialis, Calf & Bare Foot) -->
{near_leg_xml}

        <!-- 3. High-Plank Torso, Pelvis Shorts, Glowing Core (Obliques/Abs/Serratus) & 3/4 Head -->
{torso_xml}

        <!-- 4. Far (Left) Climbing Leg (Reciprocal Knee Drive to Chest) -->
{far_leg_xml}

        <!-- 5. Background: Far (Left) Posting Arm -->
{far_arm_xml}

        <!-- 6. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="310" y="{f(FLOOR - 2)}" scaleX="1.75" scaleY="0.10" name="AthleteShadow">
            <Ellipse width="220" height="220" name="AthleteShadowEllipse"/>
            <Fill name="AthleteShadowFill"><RadialGradient startX="0" startY="0" endX="110" endY="0" name="AthleteShadowGrad">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="MountainClimber" id="0:60">
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
    (BUILD / "mountain_climber.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (30, "frame_mid"), (60, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_start":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(716, 2, 248))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
