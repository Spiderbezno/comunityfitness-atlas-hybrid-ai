#!/usr/bin/env python3
"""Generate bench_press.rml — elevated 3/4 isometric Bench Press at 60fps (16:9 640x360).

Matches the ab_wheel_rollout / bench_dips visual standard:
- Same character palette (`SKIN`, `SKIN_FAR`, `SHORTS`, `HIGHLIGHT`, `CORE_SHADOW`,
  `MUSCLE_LOW` -> `MUSCLE_HIGH`) and 16:9 (`640x360`, `FLOOR = 300.0`) artboard.
- Elevated 3/4 isometric perspective matching the reference illustration:
  - Flat upholstered bench pad running diagonally (-28 deg) with a white/metallic
    Olympic rack (two uprights, angled rear struts, weight-storage pegs, and J-hooks).
  - Athlete lying supine on the pad, legs straddling the bench with feet planted on the floor,
    sculpted 6-pack abs and obliques, and glowing orange-to-red muscle activation on:
      * Pectoralis major (both left and right sternal/clavicular heads)
      * Anterior deltoids (left and right shoulder caps)
      * Triceps brachii (left and right upper arms)
  - 2-bone IK for both arms gripping the Olympic barbell + isometric weight plates,
    lowering smoothly to the lower chest and pressing back up to full lockout.

Run:
    python3 gen_bench_press.py            # writes bench_press.rml
    python3 gen_bench_press.py --publish  # builds .riv + copies asset & 256x256 thumbnail
"""
import math
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
REPO = HERE.parent.parent
OUT = HERE / "bench_press.rml"
ASSET_RIV = REPO / "assets/animations/bench_press.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/bench_press.png"
THUMB_ADVANCE = "0.0s"  # top lockout: maximum concentric chest/delt/triceps activation
THUMB_VIEWPORT = "1280x720"  # 2x the 640x360 artboard
THUMB_CROP = (680, 20, 240)  # square size, offsetY, offsetX in the 2x render
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

# 16:9 standard canvas matching ab_wheel_rollout, arnold_press, barbell_row, and bench_dips
W, H = 640, 360
FLOOR = 300.0

# Isometric barbell axis (+33.7 deg, perpendicular in 3/4 projection to the -28 deg bench axis)
BAR_ANGLE = math.atan2(34.0, 51.0)  # ~ +33.69 deg
BAR_COS = math.cos(BAR_ANGLE)
BAR_SIN = math.sin(BAR_ANGLE)

# Shoulder anchors in world space (athlete lying supine on the bench pad)
SHOULDER_FAR = (304.0, 144.0)   # Right (far/upper-left) shoulder
SHOULDER_NEAR = (348.0, 174.0)  # Left (near/lower-right) shoulder

# Foreshortened 2D limb lengths for the 3/4 elevated view
UPPER_ARM_FAR, FOREARM_FAR = 43.0, 41.0
UPPER_ARM_NEAR, FOREARM_NEAR = 37.0, 35.0

# Barbell center at top lockout (d=0) and bottom touching chest (d=1)
BAR_TOP = (318.0, 108.0)
BAR_BOT = (322.0, 156.0)
# Grip offset along the bar from the bar center
GRIP_SPAN = 64.0
GRIP_DX = GRIP_SPAN * BAR_COS  # ~ 53.2
GRIP_DY = GRIP_SPAN * BAR_SIN  # ~ 35.5

# Timeline (frames @60fps): lower 1.15s, bottom pause 0.25s, press up 1.15s, top hold 0.45s = 3.0s (180 frames)
LOWER_FRAMES, HOLD_BOT, PRESS_FRAMES, HOLD_TOP = 69, 15, 69, 27
DURATION = LOWER_FRAMES + HOLD_BOT + PRESS_FRAMES + HOLD_TOP
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


def press_depth(frame):
    """0.0 at top lockout, 1.0 at bottom of the bench press (bar at chest)."""
    fr = frame % DURATION
    if fr <= LOWER_FRAMES:
        return EASE(fr / LOWER_FRAMES)
    fr -= LOWER_FRAMES
    if fr <= HOLD_BOT:
        return 1.0
    fr -= HOLD_BOT
    if fr <= PRESS_FRAMES:
        return 1.0 - EASE(fr / PRESS_FRAMES)
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


def pose(d):
    """Compute barbell position and both 2-bone IK arms at depth d in [0, 1]."""
    bar_x = lerp(BAR_TOP[0], BAR_BOT[0], d)
    bar_y = lerp(BAR_TOP[1], BAR_BOT[1], d)

    hand_far = (bar_x - GRIP_DX, bar_y - GRIP_DY)
    hand_near = (bar_x + GRIP_DX, bar_y + GRIP_DY)

    # Far (right) arm bends outward/down-left (bend_sign = -1.0)
    ua_far, fa_far_world, elbow_far = solve_ik(
        SHOULDER_FAR, hand_far, UPPER_ARM_FAR, FOREARM_FAR, bend_sign=-1.0
    )
    fa_far_local = fa_far_world - ua_far

    # Near (left) arm bends outward/down-right (bend_sign = +1.0)
    ua_near, fa_near_world, elbow_near = solve_ik(
        SHOULDER_NEAR, hand_near, UPPER_ARM_NEAR, FOREARM_NEAR, bend_sign=1.0
    )
    fa_near_local = fa_near_world - ua_near

    # Subtle ribcage expansion as the bar meets the chest
    chest_lift = lerp(0.0, -1.8, d)

    return {
        "d": d,
        "bar": (bar_x, bar_y),
        "hand_far": hand_far,
        "hand_near": hand_near,
        "elbow_far": elbow_far,
        "elbow_near": elbow_near,
        "ua_far": ua_far,
        "fa_far_local": fa_far_local,
        "ua_near": ua_near,
        "fa_near_local": fa_near_local,
        "chest_lift": chest_lift,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(press_depth(fr)) for fr in FRAMES}

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
    """Straight-vertex polygon with rounded corners for structural rack/bench parts."""
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
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
MUSCLE_LOW = (0x66, 0xFB, 0x92, 0x3C)   # warm orange at lockout
MUSCLE_HIGH = (0xF2, 0xEF, 0x44, 0x44)  # intense red at bottom of press
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
    return 0.22 + 0.78 * ((1.0 - p["d"]) ** 1.05)


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


# ---------------------------------------------------------------- bench & Olympic rack
def bench_and_rack():
    """Isometric 3/4 flat bench + white/metallic Olympic rack with weight horns & J-hooks."""
    ind = "        "
    i2 = ind + "    "
    metal_light = f'<Fill name="MetalLightFill">{grad("MetalLightGrad", 260, 40, 450, 260, "FFF8FAFC", "FFCBD5E1")}</Fill>'
    metal_side = f'<Fill name="MetalSideFill">{grad("MetalSideGrad", 260, 40, 450, 260, "FFCBD5E1", "FF64748B")}</Fill>'
    metal_dark = f'<Fill name="MetalDarkFill">{grad("MetalDarkGrad", 200, 100, 420, 280, "FF94A3B8", "FF475569")}</Fill>'
    peg_paint = f'<Fill name="PegFill">{grad("PegGrad", 0, -5, 0, 5, "FF94A3B8", "FF334155")}</Fill>'
    pad_top = f'<Fill name="PadTopFill">{grad("PadTopGrad", 180, 140, 360, 240, "FF334155", "FF1E293B")}</Fill>'
    pad_side = f'<Fill name="PadSideFill">{grad("PadSideGrad", 180, 190, 360, 265, "FF1E293B", "FF0B1120")}</Fill>'
    rubber = solid("Rubber", "FF0F172A")

    out = [f'{ind}<Node name="BenchAndRack">']

    # --- 1. Far-left rack upright assembly (behind the athlete's right shoulder/head) ---
    for px, py in ((316, 68), (326, 101), (336, 134)):
        out.append(poly_shape(i2, f"FarPeg_{px}", [(px, py), (px + 26, py + 17), (px + 23, py + 21), (px - 3, py + 4)], peg_paint, radius=1.5))
    out.append(poly_shape(i2, "FarRackRearStrut", [(292, 54), (304, 48), (350, 168), (338, 174)], metal_side, radius=1.5))
    out.append(poly_shape(i2, "FarRackTopCap", [(272, 54), (286, 47), (296, 53), (282, 60)], metal_light, radius=1.0))
    out.append(poly_shape(i2, "FarRackPostFront", [(282, 60), (296, 53), (296, 184), (282, 191)], metal_light, radius=1.0))
    out.append(poly_shape(i2, "FarRackPostSide", [(272, 54), (282, 60), (282, 191), (272, 185)], metal_side, radius=1.0))
    out.append(poly_shape(i2, "FarJHook1", [(264, 84), (274, 79), (274, 87), (264, 92)], metal_dark, radius=1.5))
    out.append(poly_shape(i2, "FarJHook2", [(264, 120), (274, 115), (274, 123), (264, 128)], metal_dark, radius=1.5))

    # --- 2. Near-right rack upright assembly (to the right of the athlete's head) ---
    for px, py in ((442, 128), (452, 160), (462, 192)):
        out.append(poly_shape(i2, f"NearPeg_{px}", [(px, py), (px + 26, py + 17), (px + 23, py + 21), (px - 3, py + 4)], peg_paint, radius=1.5))
    out.append(poly_shape(i2, "NearRackRearStrut", [(418, 114), (430, 108), (474, 220), (462, 226)], metal_side, radius=1.5))
    out.append(poly_shape(i2, "NearRackBaseFoot", [(406, 238), (476, 216), (480, 224), (410, 246)], metal_side, radius=1.5))
    out.append(poly_shape(i2, "NearRackTopCap", [(398, 114), (412, 107), (422, 113), (408, 120)], metal_light, radius=1.0))
    out.append(poly_shape(i2, "NearRackPostFront", [(408, 120), (422, 113), (422, 244), (408, 251)], metal_light, radius=1.0))
    out.append(poly_shape(i2, "NearRackPostSide", [(398, 114), (408, 120), (408, 251), (398, 245)], metal_side, radius=1.0))
    out.append(poly_shape(i2, "NearJHook1", [(390, 144), (400, 139), (400, 147), (390, 152)], metal_dark, radius=1.5))
    out.append(poly_shape(i2, "NearJHook2", [(390, 180), (400, 175), (400, 183), (390, 188)], metal_dark, radius=1.5))

    # --- 3. Bench pad & front leg support ---
    # Upholstered bench pad running from bottom-left (foot end) to top-right (head end)
    out.append(stroke_shape(i2, "BenchPadHighlight", [(204, 253), (308, 194), (412, 136)], 1.6, "40FFFFFF", 1.0))
    out.append(poly_shape(i2, "BenchPadTop", [(162, 230), (376, 112), (416, 136), (202, 256)], pad_top, radius=6.0))
    out.append(poly_shape(i2, "BenchPadRightSkirt", [(202, 256), (416, 136), (416, 150), (202, 270)], pad_side, radius=4.0))
    out.append(poly_shape(i2, "BenchPadFrontSkirt", [(162, 230), (202, 256), (202, 270), (162, 244)], pad_side, radius=4.0))

    # Bench under-frame rail + front leg at bottom-left
    out.append(poly_shape(i2, "BenchUnderRail", [(196, 264), (398, 152), (398, 162), (196, 274)], metal_side, radius=2.0))
    out.append(poly_shape(i2, "BenchFrontLegFront", [(184, 256), (198, 264), (186, 296), (172, 288)], metal_light, radius=1.5))
    out.append(poly_shape(i2, "BenchFrontLegSide", [(174, 250), (184, 256), (172, 288), (162, 282)], metal_side, radius=1.5))
    out.append(poly_shape(i2, "BenchFrontFoot", [(158, 284), (192, 294), (188, 300), (154, 290)], rubber, radius=2.0))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- athlete anatomy (supine 3/4 isometric)
def far_leg():
    """Right (far/left-on-screen) leg straddling the bench pad, foot planted on the floor."""
    ind = "        "
    i2 = ind + "    "
    thigh_pts = [(252, 174), (222, 172), (194, 181), (176, 196), (182, 210), (208, 204), (238, 198), (258, 190)]
    thigh_hi = [(242, 179), (214, 180), (190, 190)]
    thigh_sh = [(240, 194), (210, 200), (186, 205)]
    shorts_pts = [(262, 172), (230, 171), (214, 177), (224, 202), (254, 194)]
    shin_pts = [(176, 196), (168, 214), (168, 238), (172, 254), (182, 254), (188, 236), (190, 214), (186, 200)]
    foot_pts = [(172, 251), (156, 258), (146, 265), (152, 271), (172, 267), (184, 259)]
    return "\n".join([
        f'{ind}<Node name="FarLeg">',
        smooth_shape(i2, "FarThighShorts", shorts_pts, skin_fill("FarShorts", 171, 202, SHORTS_FAR)),
        stroke_shape(i2, "FarThighHi", thigh_hi, 3.5, HIGHLIGHT, 3.5),
        stroke_shape(i2, "FarThighSh", thigh_sh, 5.0, CORE_SHADOW, 5.0),
        smooth_shape(i2, "FarThigh", thigh_pts, skin_fill("FarThigh", 172, 210, SKIN_FAR)),
        ellipse_shape(i2, "FarKnee", 180, 200, 17, 15, skin_fill("FarKnee", -8, 8, SKIN_FAR)),
        smooth_shape(i2, "FarShin", shin_pts, skin_fill("FarShin", 196, 254, SKIN_FAR)),
        smooth_shape(i2, "FarFoot", foot_pts, skin_fill("FarFoot", 251, 271, SKIN_FAR)),
        f"{ind}</Node>",
    ])


def near_leg():
    """Left (near/foreground) leg straddling the right side of the bench, foot planted forward."""
    ind = "        "
    i2 = ind + "    "
    thigh_pts = [(274, 196), (292, 208), (288, 234), (276, 258), (258, 260), (252, 238), (254, 212), (262, 198)]
    thigh_hi = [(274, 204), (274, 228), (268, 250)]
    thigh_sh = [(285, 214), (282, 238), (273, 254)]
    shorts_pts = [(260, 190), (290, 202), (292, 220), (252, 224), (252, 202)]
    shin_pts = [(258, 256), (276, 256), (278, 280), (270, 306), (258, 306), (254, 282)]
    shin_hi = [(264, 262), (264, 284), (262, 300)]
    foot_pts = [(258, 302), (271, 302), (274, 320), (264, 328), (252, 324), (253, 308)]
    return "\n".join([
        f'{ind}<Node name="NearLeg">',
        smooth_shape(i2, "NearFoot", foot_pts, skin_fill("NearFoot", 302, 328, SKIN)),
        stroke_shape(i2, "NearShinHi", shin_hi, 3.2, HIGHLIGHT, 3.5),
        smooth_shape(i2, "NearShin", shin_pts, skin_fill("NearShin", 256, 306, SKIN)),
        ellipse_shape(i2, "NearKnee", 266, 256, 18, 16, skin_fill("NearKnee", -8, 8, SKIN)),
        smooth_shape(i2, "NearThighShorts", shorts_pts, skin_fill("NearThighShorts", 190, 224, SHORTS)),
        stroke_shape(i2, "NearThighHi", thigh_hi, 4.2, HIGHLIGHT, 4.0),
        stroke_shape(i2, "NearThighSh", thigh_sh, 5.5, CORE_SHADOW, 5.5),
        smooth_shape(i2, "NearThigh", thigh_pts, skin_fill("NearThigh", 196, 260, SKIN)),
        f"{ind}</Node>",
    ])


def supine_torso_and_head():
    """Supine torso, shorts, sculpted 6-pack abs, activated pectorals, neck, and full 3D head."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    chest_id = nid()
    key_double(chest_id, 14, lambda p: p["chest_lift"])

    # Pelvis / athletic shorts bridging both hips on the bench pad
    pelvis_shorts = [(238, 178), (262, 172), (286, 188), (286, 214), (260, 220), (236, 200)]

    # Supine torso from waist (256, 188) up-right to broad shoulders (304, 144) & (348, 174)
    torso_pts = [
        (250, 180), (268, 164), (286, 150), (306, 136), (328, 134),
        (348, 144), (358, 162), (348, 182), (326, 196), (302, 206),
        (278, 210), (258, 202),
    ]
    torso_hi = [(270, 172), (294, 156), (320, 143)]
    torso_sh = [(338, 184), (310, 198), (282, 204)]

    # Sculpted 6-pack abs (two isometric rows of 3 blocks along the -28 deg midline)
    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1C0F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="AbsEdge"><SolidColor colorValue="400F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        # Upper-left (right side of body) 3 rectus abdominis blocks
        [(290, 162), (301, 156), (308, 162), (297, 169)],
        [(277, 170), (288, 163), (295, 170), (284, 177)],
        [(264, 178), (275, 171), (282, 178), (271, 185)],
        # Lower-right (left side of body) 3 rectus abdominis blocks
        [(299, 171), (310, 164), (317, 171), (306, 178)],
        [(286, 179), (297, 172), (304, 179), (293, 186)],
        [(273, 187), (284, 180), (291, 187), (280, 194)],
    ]

    # Target Muscle Activations: Pectoralis major (Right / upper-left & Left / lower-right)
    pec_right_pts = [
        (300, 150), (307, 139), (321, 137), (333, 144),
        (324, 156), (310, 160),
    ]
    pec_left_pts = [
        (325, 158), (335, 146), (350, 156), (351, 172),
        (338, 182), (323, 177), (315, 167),
    ]
    # Subtle muscle fiber striations across both pectorals
    pec_striation_r = [(308, 146), (320, 145), (328, 148)]
    pec_striation_l = [(325, 164), (336, 163), (346, 168)]

    # Volumetric 3/4 isometric head resting on the upper bench pad (44x39 px round cranium + jawline)
    neck_pts = [(336, 142), (350, 126), (368, 134), (350, 150)]
    head_pts = [
        (350, 124),  # under chin
        (349, 114),  # chin tip (facing up-left)
        (353, 105),  # 3/4 nose & upper lip contour
        (360, 98),   # forehead brow
        (372, 94),   # high round cranial dome
        (385, 96),   # top-right crown
        (393, 106),  # back of skull
        (392, 119),  # occiput on bench pad
        (382, 129),  # skull base behind ear
        (370, 133),  # mandible / jaw angle
        (358, 131),  # jawline to chin
    ]
    hair_pts = [
        (362, 97), (373, 93.5), (386, 95.5), (394, 105),
        (393, 119), (385, 125), (386, 113), (380, 103), (369, 99),
    ]
    head_hi = [(354, 112), (361, 102), (373, 98)]
    jaw_sh = [(355, 122), (367, 127), (378, 124)]

    out = [f'{ind}<Node name="SupineBody">']

    # Head & Neck (drawn behind the chest/clavicles so the neck base tucks cleanly into the sternum)
    out.append(smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 362, 94, 394, 125, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i2, "Ear", 377, 125, 7.5, 5.5, solid("Ear", "FFA3B1C4"), rot_deg=-25.0))
    out.append(stroke_shape(i2, "HeadHi", head_hi, 3.2, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i2, "JawShadow", jaw_sh, 2.5, "330F172A", 2.5))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill("Head", 94, 133, SKIN)))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", 126, 150, SKIN_FAR)))

    # Animated Pectorals (subtle chest expansion with the press)
    out.append(f'{i2}<Node y="0" name="ChestGroup" id="{chest_id}">')
    out.append(stroke_shape(i3, "PecStriationL", pec_striation_l, 1.0, "408B1A1A", 0.5))
    out.append(stroke_shape(i3, "PecStriationR", pec_striation_r, 1.0, "408B1A1A", 0.5))
    out.append(smooth_shape(i3, "PecLeftActivation", pec_left_pts, muscle_paint("PecLeft", 1.0)))
    out.append(smooth_shape(i3, "PecRightActivation", pec_right_pts, muscle_paint("PecRight", 1.0)))
    out.append(f"{i2}</Node>")

    # Sculpted 6-pack abs & obliques
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "LineaAlba", [(324, 156), (296, 172), (270, 188)], 1.2, "380F172A", 0.8))
    out.append(stroke_shape(i2, "SerratusLine1", [(310, 186), (302, 180)], 1.2, "330F172A", 0.8))
    out.append(stroke_shape(i2, "SerratusLine2", [(300, 192), (292, 186)], 1.2, "330F172A", 0.8))

    # Pelvic shorts + Torso base
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill("PelvisShorts", 172, 220, SHORTS)))
    out.append(stroke_shape(i2, "TorsoHi", torso_hi, 4.5, HIGHLIGHT, 4.5))
    out.append(stroke_shape(i2, "TorsoSh", torso_sh, 6.0, CORE_SHADOW, 6.0))
    out.append(smooth_shape(i2, "Torso", torso_pts, skin_fill("Torso", 134, 210, SKIN)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def arm_rig(prefix, far):
    """2-bone IK arm (UpperArm -> Forearm -> Hand) with Anterior Deltoid & Triceps activation."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    sx, sy = SHOULDER_FAR if far else SHOULDER_NEAR
    ua_len = UPPER_ARM_FAR if far else UPPER_ARM_NEAR
    fa_len = FOREARM_FAR if far else FOREARM_NEAR
    ua_key = "ua_far" if far else "ua_near"
    fa_key = "fa_far_local" if far else "fa_near_local"

    ua_id, fa_id = nid(), nid()
    key_double(ua_id, 15, lambda p: p[ua_key])
    key_double(fa_id, 15, lambda p: p[fa_key])
    p0 = POSES[0]

    # Upper arm contour along +x (0 .. ua_len)
    ua_pts = [
        (-10, 0), (-7, -9), (6, -11.5), (ua_len * 0.55, -10.5), (ua_len - 4, -7.5),
        (ua_len + 5, 0), (ua_len - 4, 7.5), (ua_len * 0.55, 10.5), (6, 11.5), (-7, 9),
    ]
    # Triceps brachii activation on the outer/extensor aspect of the upper arm
    tri_sign = -1.0 if far else 1.0
    tri_pts = [
        (5, tri_sign * 2.5),
        (ua_len * 0.45, tri_sign * 3.0),
        (ua_len - 5, tri_sign * 3.5),
        (ua_len - 8, tri_sign * 9.5),
        (ua_len * 0.45, tri_sign * 10.8),
        (6, tri_sign * 9.5),
    ]
    delt_pts = [(-12, 0), (-8, -11), (4, -13), (16, -9), (18, 0), (15, 9), (3, 12), (-8, 9)]
    front_delt_pts = [(-6, -tri_sign * 2), (4, -tri_sign * 9.5), (15, -tri_sign * 6.5), (16, tri_sign * 2), (4, tri_sign * 5)]

    fa_pts = [
        (-6, 0), (-4, -7.5), (fa_len * 0.35, -8.5), (fa_len - 5, -5.5),
        (fa_len + 4, 0), (fa_len - 5, 5.5), (fa_len * 0.35, 8.5), (-4, 7.5),
    ]
    hand_pts = [(-5, -6.5), (5, -7.0), (10, -2.0), (10, 4.5), (4, 7.0), (-5, 5.5)]

    out = [f'{ind}<Node x="{f(sx)}" y="{f(sy)}" rotation="{f(p0[ua_key])}" name="{prefix}UpperArm" id="{ua_id}">']

    # Forearm + Hand (drawn in front of the elbow joint)
    out.append(f'{i2}<Node x="{f(ua_len)}" rotation="{f(p0[fa_key])}" name="{prefix}Forearm" id="{fa_id}">')
    out.append(smooth_shape(i3, f"{prefix}Hand", hand_pts, skin_fill(prefix + "Hand", -7, 7, skin), x=fa_len))
    out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(4, -4.5), (fa_len - 8, -3.5)], 2.8, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -9, 9, skin)))
    out.append(f"{i2}</Node>")

    # Anterior Deltoid cap + activation
    out.append(smooth_shape(i2, f"{prefix}FrontDeltActivation", front_delt_pts, muscle_paint(prefix + "FrontDelt", 0.9)))
    out.append(smooth_shape(i2, f"{prefix}Deltoid", delt_pts, skin_fill(prefix + "Deltoid", -13, 12, skin)))

    # Upper arm + Triceps brachii activation
    out.append(smooth_shape(i2, f"{prefix}TricepsActivation", tri_pts, muscle_paint(prefix + "Triceps", 0.9)))
    out.append(stroke_shape(i2, f"{prefix}UpperArmHi", [(6, -5 * tri_sign), (ua_len - 10, -4 * tri_sign)], 3.0, HIGHLIGHT, 3.5))
    out.append(smooth_shape(i2, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UpperArm", -12, 12, skin)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def barbell_rig():
    """Animated Olympic barbell: far plates + chrome shaft + near plates + finger wraps."""
    ind = "        "
    i2 = ind + "    "
    bar_id = nid()
    key_double(bar_id, 13, lambda p: p["bar"][0])
    key_double(bar_id, 14, lambda p: p["bar"][1])
    p0 = POSES[0]

    plate_dark = f'<Fill name="PlateDarkFill">{grad("PlateDarkGrad", -20, -34, 20, 34, "FF334155", "FF0F172A")}</Fill>'
    plate_rim = f'<Fill name="PlateRimFill">{grad("PlateRimGrad", -20, -34, 20, 34, "FF475569", "FF1E293B")}</Fill>'
    plate_edge = '<Stroke thickness="1.2" name="PlateStroke"><SolidColor colorValue="FF64748B" name="PlateStrokeCol"/></Stroke>'
    hub_paint = solid("Hub", "FF94A3B8")

    # Unit vectors along and perpendicular to the bar
    ux, uy = BAR_COS, BAR_SIN
    nx, ny = -BAR_SIN, BAR_COS

    def bar_pt(along, perp=0.0):
        return (along * ux + perp * nx, along * uy + perp * ny)

    # Isometric 45-lb plate helper: w < h so major axis (h) is along local Y,
    # and rotating by BAR_ANGLE orients the plate face perpendicular to the bar shaft!
    plate_rot_deg = math.degrees(BAR_ANGLE)

    def iso_plate(name, along_pos, w=34.0, h=62.0):
        px, py = bar_pt(along_pos)
        bx, by = bar_pt(along_pos - 4.0)
        return "\n".join([
            ellipse_shape(i2, name + "Rim", bx, by, w, h, plate_rim, rot_deg=plate_rot_deg),
            ellipse_shape(i2, name + "Face", px, py, w, h, plate_dark + plate_edge, rot_deg=plate_rot_deg),
            ellipse_shape(i2, name + "Hub", px, py, w * 0.24, h * 0.24, hub_paint, rot_deg=plate_rot_deg),
        ])

    # Bar shaft polygon from far sleeve (-104) to near sleeve (+104)
    s_far = bar_pt(-104.0)
    s_near = bar_pt(104.0)
    sleeve_far_end = bar_pt(-146.0)
    sleeve_near_end = bar_pt(146.0)

    # Knurled grip wraps at +/- GRIP_SPAN
    gf = bar_pt(-GRIP_SPAN)
    gn = bar_pt(GRIP_SPAN)

    return "\n".join([
        f'{ind}<Node x="{f(p0["bar"][0])}" y="{f(p0["bar"][1])}" name="Barbell" id="{bar_id}">',

        # 1. Near (bottom-right) outer sleeve & 45-lb plates (in front of the main shaft)
        stroke_shape(i2, "NearSleeveOuter", [bar_pt(102.0), sleeve_near_end], 7.0, "FFCBD5E1", 0.0, cap="round"),
        stroke_shape(i2, "NearSleeveCore", [bar_pt(102.0), sleeve_near_end], 4.5, "FF64748B", 0.0, cap="round"),
        iso_plate("NearPlateOuter", 110.0, w=33.0, h=60.0),
        iso_plate("NearPlateInner", 100.0, w=35.0, h=64.0),

        # 2. Finger knuckles wrapping over the top of the bar at both hands
        ellipse_shape(i2, "NearFingerWrap", gn[0], gn[1], 14, 10, skin_fill("NearWrap", -5, 5, SKIN), rot_deg=math.degrees(BAR_ANGLE)),
        ellipse_shape(i2, "FarFingerWrap", gf[0], gf[1], 13, 9, skin_fill("FarWrap", -5, 5, SKIN_FAR), rot_deg=math.degrees(BAR_ANGLE)),

        # 3. Main chrome barbell shaft across the chest
        stroke_shape(i2, "BarShaftShadow", [s_far, s_near], 5.2, "FF334155", 0.0, cap="butt"),
        stroke_shape(i2, "BarShaftCore", [s_far, s_near], 3.8, "FFCBD5E1", 0.0, cap="butt"),
        stroke_shape(i2, "BarShaftHi", [bar_pt(-102.0, -1.0), bar_pt(102.0, -1.0)], 1.4, "FFFFFFFF", 0.0, cap="butt"),

        # 4. Far (top-left) 45-lb plates & outer sleeve (behind the main shaft)
        iso_plate("FarPlateInner", -100.0, w=34.0, h=62.0),
        iso_plate("FarPlateOuter", -110.0, w=32.0, h=58.0),
        stroke_shape(i2, "FarSleeveOuter", [bar_pt(-102.0), sleeve_far_end], 6.5, "FFCBD5E1", 0.0, cap="round"),
        stroke_shape(i2, "FarSleeveCore", [bar_pt(-102.0), sleeve_far_end], 4.0, "FF64748B", 0.0, cap="round"),

        f"{ind}</Node>",
    ])


def shadow():
    ind = "        "
    return "\n".join([
        # Floor shadow under the bench, rack, and planted feet
        f'{ind}<Shape x="295" y="{f(FLOOR - 6)}" scaleX="1.45" scaleY="0.11" name="BenchRackShadow">\n'
        f'{ind}    <Ellipse width="220" height="220" name="BenchRackShadowEllipse"/>\n'
        f'{ind}    <Fill name="BenchRackShadowFill"><RadialGradient startX="0" startY="0" endX="110" endY="0" name="BenchRackShadowGrad">'
        f'<GradientStop colorValue="99000000" position="0"/><GradientStop colorValue="4D000000" position="0.6"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{ind}</Shape>",
        f'{ind}<Shape x="262" y="{f(FLOOR + 14)}" scaleX="0.45" scaleY="0.06" name="NearFootShadow">\n'
        f'{ind}    <Ellipse width="120" height="120" name="NearFootShadowEllipse"/>\n'
        f'{ind}    <Fill name="NearFootShadowFill"><RadialGradient startX="0" startY="0" endX="60" endY="0" name="NearFootShadowGrad">'
        f'<GradientStop colorValue="99000000" position="0"/><GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
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


barbell_xml = barbell_rig()
near_arm_xml = arm_rig("Near", False)
near_leg_xml = near_leg()
torso_xml = supine_torso_and_head()
far_arm_xml = arm_rig("Far", True)
far_leg_xml = far_leg()
bench_rack_xml = bench_and_rack()
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
    <!-- Bench Press: 3/4 isometric view, 60 fps, 16:9 (640x360), generated by gen_bench_press.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="BenchPress" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- Olympic Barbell & Weight Plates (in front of chest/arms) -->
{barbell_xml}

        <!-- Near (left) arm -->
{near_arm_xml}

        <!-- Near (left) leg straddling bench in foreground -->
{near_leg_xml}

        <!-- Supine Athlete Torso, Activated Pectorals, Sculpted Abs & Head -->
{torso_xml}

        <!-- Far (right) arm -->
{far_arm_xml}

        <!-- Far (right) leg straddling bench -->
{far_leg_xml}

        <!-- 3/4 Flat Bench & Olympic Rack -->
{bench_rack_xml}

        <!-- Floor shadows -->
{shd_xml}

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

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="Press" id="0:60">
{keyed_xml()}
        </LinearAnimation>
    </Artboard>
</Rive>
"""

OUT.write_text(rml)

for fr in (0, 34, 68, 84, 120, DURATION):
    P = POSES[fr]
    print(
        f"f{fr:3d} d={P['d']:.3f} bar=({P['bar'][0]:.1f},{P['bar'][1]:.1f}) "
        f"elb_far=({P['elbow_far'][0]:.1f},{P['elbow_far'][1]:.1f}) "
        f"elb_near=({P['elbow_near'][0]:.1f},{P['elbow_near'][1]:.1f})"
    )
print("keyed props:", len(keys), "bytes:", len(rml))


def publish():
    """Build the .riv, copy it into the Flutter assets and render the catalog thumbnail."""
    subprocess.run([str(RIVE_BIN), ".", "--once"], cwd=HERE, check=True)
    built = HERE / "build/bench_press.riv"
    shutil.copyfile(built, ASSET_RIV)
    ASSET_THUMB.parent.mkdir(parents=True, exist_ok=True)
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
    print("published", ASSET_RIV, ASSET_THUMB)


if "--publish" in sys.argv:
    publish()
