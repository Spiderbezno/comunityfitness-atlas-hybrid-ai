#!/usr/bin/env python3
"""Generates rive_animations/lat_pulldown/scene.rml (and optionally publishes).

16:9 (640x360, FLOOR = 300.0) 60 fps procedural Rive animation for the
Seated Wide-Grip Lat Pulldown (`id: lat_pulldown`), matching the 2-panel
3/4 rear-left anatomical reference chart:
  - Camera: 3/4 rear-left isometric view showing our canonical CommunityFitness
    mannequin seated straddling a black padded lat-pulldown bench facing the
    vertical cable pulley station.
  - Machine & Equipment:
    - Vertical silver-white commercial cable tower (`x = 236..308, y = 18..296`)
      with dual chrome guide rods, multi-plate black weight stack (`stack_lift_y`
      rises by `-44 px` as `r: 0.0 -> 1.0`), angled overhead pulley boom with
      top pulley wheel (`PULLEY_TOP = (316.0, 26.0)`), and slanted bench pad
      extending down-right (`x = 286..412, y = 204..298`).
    - Wide cambered (angled-end) black steel lat pulldown bar with central
      chrome swivel eyelet and black rubber handgrips descending from
      `bar_y = 66.0` (overhead Y-stretch) to `bar_y = 122.0` (chin / upper-chest
      level in front of the head/neck).
  - Depth Layering (3/4 Rear-Left View):
    - Because the athlete is viewed from behind (3/4 rear-left) and pulls the
      bar down in front of his head/upper chest, `HeadAndNeck` is layered in
      FRONT of `LatBarAndCable`, so at `r = 0.0` the entire overhead bar is
      visible above the head, and at `r = 1.0` the center of the bar passes
      naturally behind the head/neck while the wide cambered ends and both
      hands remain clearly visible on either side.
  - Activated Target Muscles (all 9 labeled muscles from the reference chart):
    1. Latissimus dorsi (Primary, bilateral V-taper wings, `scale = 1.00`)
    2. Teres major (Primary, bilateral scapular cylinders, `scale = 0.96`)
    3. Trapezius (middle and lower) (Secondary, kite-shaped mid/lower traps, `scale = 0.88`)
    4. Infraspinatus (Secondary, bilateral infraspinous fossa plates, `scale = 0.84`)
    5. Teres minor (Secondary, bilateral oblique cuff bands, `scale = 0.84`)
    6. Posterior deltoid (Secondary, bilateral rear deltoid caps, `scale = 0.86`)
    7. Biceps brachii (Secondary, bilateral upper arm flexors, `scale = 0.85`)
    8. Brachialis (Secondary, bilateral distal arm flexors, `scale = 0.84`)
    9. Brachioradialis (Secondary, bilateral radial forearm flexors, `scale = 0.84`)

Usage (from this directory):
    python3 gen_lat_pulldown.py            # regenerate scene.rml
    python3 gen_lat_pulldown.py --publish  # + build .riv, copy to assets, render thumbnail
"""
import math
import pathlib
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zlib
import struct

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "scene.rml"
ASSET_RIV = REPO / "assets/animations/lat_pulldown.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/lat_pulldown.png"
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"
SCRATCH_RENDERER = pathlib.Path(
    "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch"
)

# 16:9 standard canvas
W, H = 640, 360
FLOOR = 300.0

# High pulley wheel center & bar center X coordinate
PULLEY_TOP = (316.0, 26.0)
PULLEY_MID = (294.0, 86.0)
BAR_CX = 316.0

# Reference limb lengths for 3D foreshortening scale
UPPER_ARM_L, FOREARM_L = 48.0, 44.0
UPPER_ARM_R, FOREARM_R = 48.0, 44.0

# Timeline (frames @60fps):
# 0..12: top overhead stretch hold (r=0.0)
# 12..68: smooth concentric lat pulldown (r: 0.0 -> 1.0)
# 68..88: peak contraction hold at upper chest / chin level (r=1.0)
# 88..154: controlled eccentric return to overhead stretch (r: 1.0 -> 0.0)
# 154..168: top overhead stretch hold (r=0.0)
HOLD_TOP_1 = 12
PULL_FRAMES = 56
HOLD_BOT = 20
RETURN_FRAMES = 66
HOLD_TOP_2 = 14
DURATION = HOLD_TOP_1 + PULL_FRAMES + HOLD_BOT + RETURN_FRAMES + HOLD_TOP_2  # 168 frames (2.8s)
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


EASE_PULL = cubic_bezier(0.42, 0.0, 0.58, 1.0)
EASE_RETURN = cubic_bezier(0.42, 0.0, 0.58, 1.0)


def pull_progress(frame):
    """0.0 at overhead stretch (left reference panel), 1.0 at peak contraction (right reference panel)."""
    fr = frame % DURATION
    if fr <= HOLD_TOP_1:
        return 0.0
    fr -= HOLD_TOP_1
    if fr <= PULL_FRAMES:
        return EASE_PULL(fr / PULL_FRAMES)
    fr -= PULL_FRAMES
    if fr <= HOLD_BOT:
        return 1.0
    fr -= HOLD_BOT
    if fr <= RETURN_FRAMES:
        return 1.0 - EASE_RETURN(fr / RETURN_FRAMES)
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
    """3D-foreshortened Shoulder -> Elbow -> Hand solver in world space."""
    dx1, dy1 = el[0] - sh[0], el[1] - sh[1]
    d1 = math.hypot(dx1, dy1)
    ua_rot = math.atan2(dy1, dx1)
    ua_sx = max(0.42, d1 / l1)

    dx2, dy2 = hand[0] - el[0], hand[1] - el[1]
    d2 = math.hypot(dx2, dy2)
    fa_rot = math.atan2(dy2, dx2)
    fa_sx = max(0.42, d2 / l2)
    return ua_rot, ua_sx, fa_rot, fa_sx


def pose(r):
    """Compute Seated Wide-Grip Lat Pulldown pose at progress r in [0.0, 1.0]."""
    # 1. Cambered Lat Bar vertical position & weight stack counter-lift
    #    At r = 0.0: bar_y = 66.0 (overhead stretch, clear above head top y = 92)
    #    At r = 1.0: bar_y = 122.0 (pulled down 56 px to upper-chest / chin level)
    bar_y = lerp(66.0, 122.0, r)
    stack_lift_y = lerp(0.0, -44.0, r)
    cable_len = max(12.0, bar_y - PULLEY_TOP[1] - 4.0)

    # 2. Wide Overhand (Pronated) Hand Positions on the Cambered Bar Ends
    hand_l = (BAR_CX - 98.0, bar_y + 10.5)   # (218.0, 76.5 -> 132.5)
    hand_r = (BAR_CX + 98.0, bar_y + 13.5)   # (414.0, 79.5 -> 135.5)

    # 3. Subtle Thoracic Extension & Scapular Depression at Peak Contraction
    torso_dy = lerp(0.0, 2.0, r)
    sh_l = (284.0, lerp(132.0, 136.5, r))
    sh_r = (350.0, lerp(134.0, 138.5, r))

    # 4. 3D-Foreshortened Elbow Trajectories (overhead Y-reach -> wide arc -> tight W-frame tuck at flanks)
    elbow_l = quad_interp_pt((248.0, 105.0), (234.0, 140.0), (245.0, 169.0), r)
    elbow_r = quad_interp_pt((384.0, 108.0), (398.0, 143.0), (387.0, 171.0), r)

    ua_l, ua_l_sx, fa_l, fa_l_sx = solve_foreshortened_arm(
        sh_l, elbow_l, hand_l, UPPER_ARM_L, FOREARM_L
    )
    ua_r, ua_r_sx, fa_r, fa_r_sx = solve_foreshortened_arm(
        sh_r, elbow_r, hand_r, UPPER_ARM_R, FOREARM_R
    )

    # 5. Dynamic Dorsal Muscle Contraction & Scapular Retraction
    lat_sx = lerp(1.00, 1.055, r)
    lat_sy = lerp(1.00, 0.955, r)
    trap_sx = lerp(1.00, 0.92, r)   # mid/lower traps narrow as scapulae retract toward spine
    biceps_bulge = lerp(1.00, 1.12, r)

    return {
        "r": r,
        "bar_y": bar_y,
        "stack_lift_y": stack_lift_y,
        "cable_len": cable_len,
        "hand_l": hand_l,
        "hand_r": hand_r,
        "torso_dy": torso_dy,
        "sh_l": sh_l,
        "sh_r": sh_r,
        "elbow_l": elbow_l,
        "elbow_r": elbow_r,
        "ua_l": ua_l,
        "ua_l_sx": ua_l_sx,
        "fa_l": fa_l,
        "fa_l_sx": fa_l_sx,
        "ua_r": ua_r,
        "ua_r_sx": ua_r_sx,
        "fa_r": fa_r,
        "fa_r_sx": fa_r_sx,
        "lat_sx": lat_sx,
        "lat_sy": lat_sy,
        "trap_sx": trap_sx,
        "biceps_bulge": biceps_bulge,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(pull_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = ("ua_l", "fa_l", "ua_r", "fa_r")
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
SHORTS = ("FF475569", "FF263349", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
FRAME_WHITE = ("FFF8FAFC", "FFE2E8F0", "FF94A3B8")
FRAME_FAR = ("FFE2E8F0", "FFCBD5E1", "FF64748B")
PAD_DARK = ("FF334155", "FF1E293B", "FF090D16")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "520F172A"

# Dynamic orange-to-crimson muscle activation palette
MUSCLE_LOW = (0xBF, 0xF9, 0x73, 0x16)       # warm glowing orange at overhead stretch
MUSCLE_HIGH = (0xF5, 0xF4, 0x3F, 0x5E)      # intense crimson-red at peak pulldown contraction
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
    """Activation curve: warm orange at overhead stretch (0.32) -> intense crimson at peak contraction (1.00)."""
    base = 0.32 + 0.68 * (p["r"] ** 0.85)
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


# ---------------------------------------------------------------- 1. Rear Bench Extension & Under-Seat Bench Pad
def bench_foreground_rig():
    """Rear extension of the black padded bench & slanted silver-white rear support leg projecting behind the glutes (bottom-right)."""
    ind = "        "
    i2 = ind + "    "
    frame_paint = (
        f'<Fill name="BenchLegFill">{grad3("BenchLegG", 232, 298, *FRAME_WHITE, x0=362, x1=398)}</Fill>'
        '<Stroke thickness="1.0" join="round" name="BenchLegRim"><SolidColor colorValue="FF64748B" name="BenchLegRimCol"/></Stroke>'
    )
    pad_top_paint = (
        f'<Fill name="BenchPadTopFill">{grad3("BenchPadTopG", 212, 242, *PAD_DARK, x0=316, x1=412)}</Fill>'
        '<Stroke thickness="1.0" join="round" name="BenchPadTopRim"><SolidColor colorValue="FF020617" name="BenchPadTopRimCol"/></Stroke>'
    )
    pad_side_paint = (
        '<Fill name="BenchPadSideFill"><SolidColor colorValue="FF090D16" name="BenchPadSideCol"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="BenchPadSideRim"><SolidColor colorValue="FF020617" name="BenchPadSideRimCol"/></Stroke>'
    )
    foot_cap = solid("RearBenchFootCap", "FF090D16")

    return "\n".join([
        f'{ind}<Node name="BenchForegroundRig">',
        # Top highlight seam along the rear bench cushion edge
        stroke_shape(i2, "BenchPadEdgeHi", [(322.0, 219.5), (408.0, 236.0)], 1.3, "52F8FAFC", 0.4),
        # Rear portion of the black vinyl bench pad extending from behind the glutes (x=316, y=218) out to (x=412, y=244)
        poly_shape(
            i2, "BenchPadSideFace",
            [(314, 220), (394, 242), (412, 236), (412, 246), (394, 252), (314, 229)],
            pad_side_paint, radius=2.2,
        ),
        poly_shape(
            i2, "BenchPadTopFace",
            [(314, 220), (334, 213), (412, 234), (394, 242)],
            pad_top_paint, radius=2.5,
        ),
        # Slanted silver-white rear support post & rubber floor cap
        poly_shape(i2, "RearBenchRubberFoot", [(381, 294), (397, 294), (398, 299), (380, 299)], foot_cap, radius=1.2),
        stroke_shape(i2, "RearLegSpecHi", [(372.0, 244.0), (386.0, 294.0)], 1.6, "B3FFFFFF", 0.4),
        poly_shape(
            i2, "RearSlantedLeg",
            [(366, 242), (378, 240), (394, 296), (382, 297)],
            frame_paint, radius=1.5,
        ),
        f"{ind}</Node>",
    ])


def bench_under_seat_rig():
    """Front portion of the bench cushion & steel under-frame directly beneath the seated glutes and thighs."""
    ind = "        "
    i2 = ind + "    "
    pad_under_paint = (
        f'<Fill name="BenchUnderPadFill">{grad3("BenchUnderPadG", 206, 228, *PAD_DARK, x0=282, x1=344)}</Fill>'
        '<Stroke thickness="1.0" join="round" name="BenchUnderPadRim"><SolidColor colorValue="FF020617" name="BenchUnderPadRimCol"/></Stroke>'
    )
    rail_paint = (
        f'<Fill name="BenchRailFill">{grad3("BenchRailG", 218, 250, *FRAME_FAR, x0=284, x1=378)}</Fill>'
        '<Stroke thickness="0.9" join="round" name="BenchRailRim"><SolidColor colorValue="FF475569" name="BenchRailRimCol"/></Stroke>'
    )
    return "\n".join([
        f'{ind}<Node name="BenchUnderSeatRig">',
        poly_shape(
            i2, "FrontBenchCushionUnderGlutes",
            [(282, 212), (304, 205), (344, 216), (344, 228), (282, 221)],
            pad_under_paint, radius=2.2,
        ),
        poly_shape(
            i2, "UnderBenchSteelRail",
            [(286, 220), (376, 245), (374, 251), (286, 226)],
            rail_paint, radius=1.2,
        ),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 2. Seated Legs (Near Left Leg & Far Right Leg)
def seated_left_near_leg_rig():
    """Near (Left) Seated Leg in 3/4 rear-left perspective: thigh angled forward-left from hip (298, 204) to knee (262, 216),
    sculpted gastrocnemius/soleus calf descending to bare left foot planted flat at y = 286..296."""
    ind = "        "
    i2 = ind + "    "

    thigh_shorts_pts = [
        (280.0, 196.0), (304.0, 192.0), (314.0, 208.0),
        (294.0, 222.0), (274.0, 214.0),
    ]
    thigh_pts = [
        (260.0, 204.0), (284.0, 198.0), (298.0, 214.0),
        (278.0, 226.0), (258.0, 222.0), (254.0, 212.0),
    ]
    calf_pts = [
        (255.0, 216.0), (266.0, 214.0), (275.0, 220.0),
        (278.0, 236.0), (275.0, 254.0), (269.0, 272.0), (267.0, 285.0),
        (259.0, 286.0), (257.0, 272.0), (254.0, 252.0), (253.0, 232.0),
    ]
    gastroc_lat_pts = [
        (255.0, 220.0), (264.0, 219.0), (265.0, 236.0),
        (262.0, 252.0), (256.0, 250.0), (254.0, 234.0),
    ]
    gastroc_med_pts = [
        (264.0, 219.0), (274.0, 222.0), (276.0, 238.0),
        (273.0, 253.0), (266.0, 252.0), (264.0, 236.0),
    ]
    achilles_pts = [
        (259.0, 252.0), (269.0, 252.0), (266.0, 285.0), (259.5, 285.0),
    ]
    foot_pts = [
        (241.0, 291.5), (252.0, 286.0), (260.0, 283.0), (268.0, 284.0),
        (269.5, 291.0), (262.0, 294.0), (249.0, 295.0), (239.5, 294.0),
    ]
    calf_sculpt = (
        '<Fill name="NearCalfSculptFill"><SolidColor colorValue="1F0F172A" name="NearCalfSculptCol"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="NearCalfSculptEdge"><SolidColor colorValue="420F172A" name="NearCalfSculptEdgeCol"/></Stroke>'
    )

    return "\n".join([
        f'{ind}<Node name="LeftNearSeatedLeg">',
        # 1. Bare Left Foot planted flat on floor (pointing forward-left)
        stroke_shape(i2, "LeftFootArchHi", [(244.0, 291.0), (255.0, 287.0), (264.0, 286.5)], 1.6, HIGHLIGHT, 1.4),
        stroke_shape(i2, "LeftFootSoleSh", [(241.0, 294.2), (255.0, 294.5), (267.5, 292.5)], 1.8, CORE_SHADOW, 1.2),
        smooth_shape(i2, "LeftFootShape", foot_pts, skin_fill("LeftFoot", 282, 296, SKIN, x0=269, x1=240)),
        # 2. Sculpted Left Calf (Gastrocnemius, Soleus & Achilles Tendon)
        ellipse_shape(i2, "LeftLateralMalleolus", 261.0, 283.0, 3.8, 4.6, solid("LeftMal", "FFCBD5E1")),
        stroke_shape(i2, "LeftAchillesHi", [(263.5, 255.0), (263.0, 282.0)], 1.7, "80FFFFFF", 1.2),
        smooth_shape(i2, "LeftAchillesTendon", achilles_pts, skin_fill("LeftAchilles", 252, 285, TENDON_NEAR, x0=269, x1=259)),
        stroke_shape(i2, "LeftCalfSulcus", [(264.0, 221.0), (264.5, 238.0), (264.0, 253.0)], 1.2, CORE_SHADOW, 0.7),
        stroke_shape(i2, "LeftCalfMedHi", [(270.0, 226.0), (271.5, 240.0), (269.0, 250.0)], 2.2, HIGHLIGHT, 2.0),
        stroke_shape(i2, "LeftCalfLatHi", [(259.0, 226.0), (259.5, 240.0), (258.5, 249.0)], 2.0, HIGHLIGHT, 1.8),
        smooth_shape(i2, "LeftGastrocMedial", gastroc_med_pts, calf_sculpt),
        smooth_shape(i2, "LeftGastrocLateral", gastroc_lat_pts, calf_sculpt),
        smooth_shape(i2, "LeftCalfBase", calf_pts, skin_fill("LeftCalf", 214, 286, SKIN, x0=278, x1=253)),
        # 3. Seated Left Thigh & Shorts Leg
        stroke_shape(i2, "LeftShortsHem", [(275.0, 213.0), (285.0, 204.0), (296.0, 196.0)], 1.3, "80020617", 0.4),
        smooth_shape(i2, "LeftThighShorts", thigh_shorts_pts, skin_fill("LeftThighShorts", 192, 222, SHORTS, x0=314, x1=274)),
        stroke_shape(i2, "LeftThighVastusHi", [(262.0, 208.0), (274.0, 204.0), (284.0, 203.0)], 2.6, HIGHLIGHT, 2.2),
        stroke_shape(i2, "LeftITBandLine", [(262.0, 214.0), (276.0, 212.0), (288.0, 211.0)], 1.2, CORE_SHADOW, 0.7),
        smooth_shape(i2, "LeftThighShape", thigh_pts, skin_fill("LeftThigh", 198, 226, SKIN, x0=298, x1=254)),
        f"{ind}</Node>",
    ])


def seated_right_far_leg_rig():
    """Far (Right) Seated Leg on the far side of the bench (`x = 324..348, y = 210..286`), matching the reference chart."""
    ind = "        "
    i2 = ind + "    "
    calf_pts = [
        (327.0, 214.0), (341.0, 214.0), (344.0, 232.0),
        (341.0, 252.0), (338.0, 276.0), (331.0, 277.0),
        (328.0, 254.0), (326.0, 232.0),
    ]
    foot_pts = [
        (321.0, 281.0), (331.0, 275.0), (339.0, 276.0),
        (341.0, 283.0), (332.0, 285.5), (321.0, 284.5),
    ]
    return "\n".join([
        f'{ind}<Node name="RightFarSeatedLeg">',
        smooth_shape(i2, "RightFarFoot", foot_pts, skin_fill("RightFarFoot", 275, 286, SKIN_FAR, x0=341, x1=321)),
        stroke_shape(i2, "RightFarCalfSulcus", [(334.5, 222.0), (334.5, 252.0), (334.0, 274.0)], 1.1, CORE_SHADOW, 0.6),
        smooth_shape(i2, "RightFarCalf", calf_pts, skin_fill("RightFarCalf", 214, 278, SKIN_FAR, x0=344, x1=326)),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 3. Dorsal Torso, Glutes & Foreground Head
def dorsal_torso_and_glutes_rig():
    """3/4 Rear-Left Dorsal Torso (with all 6 back target muscles: Latissimus dorsi, Teres major,
    Trapezius middle & lower, Infraspinatus, Teres minor) and Glutes in Dark Athletic Shorts."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    torso_id, lat_id, trap_id = nid(), nid(), nid()
    key_double(torso_id, 14, lambda p: p["torso_dy"])
    key_double(lat_id, 16, lambda p: p["lat_sx"])
    key_double(lat_id, 17, lambda p: p["lat_sy"])
    key_double(trap_id, 16, lambda p: p["trap_sx"])
    p0 = POSES[0]

    # 1. Sculpted Glutes in Dark Athletic Compression Shorts seated on the bench pad (x = 290..346, y = 188..224)
    glutes_shorts_pts = [
        (294.0, 190.0), (317.0, 188.5), (341.0, 191.0),
        (346.0, 205.0), (341.0, 219.5), (324.0, 223.5),
        (306.0, 221.5), (291.0, 216.0), (289.0, 202.0),
    ]

    # 2. Broad V-Taper Dorsal Back Silhouette (neck base y = 122 down to waist y = 193, centered at spine x = 317)
    torso_pts = [
        (303.0, 123.0), (317.0, 121.0), (331.0, 123.5),
        (352.0, 133.5), (355.0, 150.0), (346.5, 171.0), (339.5, 191.5),
        (317.0, 193.5), (295.0, 190.5), (288.5, 170.0), (280.0, 149.0), (283.0, 132.0),
    ]

    # 3. Thoracolumbar Fascia / Erector Spinae diamond at lower back (silver-white aponeurosis matching reference chart)
    fascia_pts = [
        (317.0, 158.0), (328.5, 173.0), (333.0, 191.0),
        (317.0, 193.0), (301.0, 190.5), (305.5, 173.0),
    ]

    # 4. Activated Latissimus Dorsi & Teres Major (relative to center (317, 162))
    lat_l_pts = [
        (-2.0, -5.0), (-16.0, -16.0), (-33.5, -15.0), (-34.5, -2.0),
        (-27.0, 14.0), (-15.0, 25.0), (-2.0, 29.0),
    ]
    lat_r_pts = [
        (2.0, -5.0), (16.0, -16.0), (33.5, -14.5), (34.5, -1.5),
        (27.0, 14.5), (15.0, 25.5), (2.0, 29.0),
    ]
    teres_major_l_pts = [
        (-15.0, -21.0), (-29.0, -24.5), (-35.5, -15.5), (-28.0, -10.5), (-15.0, -13.0),
    ]
    teres_major_r_pts = [
        (15.0, -21.0), (29.0, -24.0), (35.5, -15.0), (28.0, -10.0), (15.0, -13.0),
    ]
    teres_minor_l_pts = [
        (-14.5, -25.0), (-27.5, -28.0), (-31.5, -22.5), (-25.0, -18.5), (-14.5, -20.5),
    ]
    teres_minor_r_pts = [
        (14.5, -25.0), (27.5, -27.5), (31.5, -22.0), (25.0, -18.0), (14.5, -20.0),
    ]

    # 5. Activated Infraspinatus (left & right scapular fossa plates above Teres minor)
    infraspinatus_l_pts = [
        (289.0, 133.0), (304.5, 134.0), (304.0, 143.0), (291.5, 144.5), (285.5, 139.0),
    ]
    infraspinatus_r_pts = [
        (329.5, 134.5), (345.0, 133.5), (348.5, 139.5), (342.5, 145.0), (330.0, 143.5),
    ]

    # 6. Activated Trapezius (Middle and Lower) kite-shaped region centered at (317, 146)
    mid_trap_pts = [
        (-13.0, -22.5), (0.0, -25.0), (13.0, -22.0),
        (16.5, -9.5), (10.5, 1.0), (0.0, 3.0), (-10.5, 1.0), (-16.5, -9.5),
    ]
    lower_trap_pts = [
        (-10.0, 0.0), (0.0, 2.0), (10.0, 0.0),
        (7.5, 15.0), (0.0, 28.5), (-7.5, 15.0),
    ]

    return "\n".join([
        f'{ind}<Node y="{f(p0["torso_dy"])}" name="DorsalTorsoAndGlutes" id="{torso_id}">',

        # --- 1. Sculpted Glutes in Dark Athletic Shorts on Bench ---
        stroke_shape(i2, "ShortsWaistband", [(294.5, 190.5), (317.0, 189.0), (340.5, 191.5)], 1.5, "80020617", 0.4),
        stroke_shape(i2, "GluteCleft", [(317.0, 191.5), (316.0, 206.0), (315.5, 220.5)], 2.2, "99020617", 0.8),
        stroke_shape(i2, "LeftGluteHi", [(302.0, 196.0), (298.0, 206.0), (303.0, 215.0)], 3.6, "26FFFFFF", 3.0),
        stroke_shape(i2, "RightGluteHi", [(330.0, 196.5), (335.0, 206.5), (330.0, 216.0)], 3.4, "22FFFFFF", 3.0),
        stroke_shape(i2, "GluteFoldLeft", [(292.0, 215.5), (304.0, 221.0), (315.0, 220.0)], 1.8, "8C020617", 0.8),
        stroke_shape(i2, "GluteFoldRight", [(316.5, 220.5), (328.0, 222.5), (340.5, 218.5)], 1.8, "8C020617", 0.8),
        smooth_shape(i2, "GlutesShorts", glutes_shorts_pts, skin_fill("GlutesShorts", 188, 224, SHORTS, x0=290, x1=346)),

        # --- 2. Activated Middle & Lower Trapezius (centered at spine x=317, y=146) ---
        f'{i2}<Node x="317" y="146" scaleX="{f(p0["trap_sx"])}" name="TrapeziusMidLowerNode" id="{trap_id}">',
        stroke_shape(i3, "MedianSpinalFurrow", [(0.0, -24.0), (0.0, 4.0), (0.0, 28.0)], 1.7, CORE_SHADOW, 0.7),
        stroke_shape(i3, "TrapFiberL1", [(-1.5, -14.0), (-13.0, -8.0)], 0.9, "737C2D12", 0.3),
        stroke_shape(i3, "TrapFiberR1", [(1.5, -14.0), (13.0, -8.0)], 0.9, "737C2D12", 0.3),
        stroke_shape(i3, "TrapFiberL2", [(-1.5, 6.0), (-7.5, 1.0)], 0.9, "737C2D12", 0.3),
        stroke_shape(i3, "TrapFiberR2", [(1.5, 6.0), (7.5, 1.0)], 0.9, "737C2D12", 0.3),
        smooth_shape(i3, "LowerTrapeziusActivation", lower_trap_pts, muscle_paint("LowerTrap", 0.9, scale=0.88)),
        smooth_shape(i3, "MiddleTrapeziusActivation", mid_trap_pts, muscle_paint("MidTrap", 0.9, scale=0.88)),
        f"{i2}</Node>",

        # --- 3. Activated Infraspinatus (Scapular Fossa Plates) ---
        stroke_shape(i2, "InfraLeftHi", [(291.0, 137.0), (301.0, 138.5)], 1.6, HIGHLIGHT, 1.5),
        stroke_shape(i2, "InfraRightHi", [(333.0, 138.5), (343.0, 137.5)], 1.6, HIGHLIGHT, 1.5),
        smooth_shape(i2, "InfraspinatusLeftActivation", infraspinatus_l_pts, muscle_paint("InfraspinatusL", 0.85, scale=0.84)),
        smooth_shape(i2, "InfraspinatusRightActivation", infraspinatus_r_pts, muscle_paint("InfraspinatusR", 0.85, scale=0.84)),

        # --- 4. Dynamic Flaring Latissimus Dorsi, Teres Major & Teres Minor (centered at x=317, y=162) ---
        f'{i2}<Node x="317" y="162" scaleX="{f(p0["lat_sx"])}" scaleY="{f(p0["lat_sy"])}" name="LatAndTeresNode" id="{lat_id}">',
        smooth_shape(i3, "TeresMinorLeftActivation", teres_minor_l_pts, muscle_paint("TeresMinorL", 0.85, scale=0.84)),
        smooth_shape(i3, "TeresMinorRightActivation", teres_minor_r_pts, muscle_paint("TeresMinorR", 0.85, scale=0.84)),
        stroke_shape(i3, "TeresMajorLeftHi", [(-18.0, -18.0), (-29.5, -16.5)], 1.9, HIGHLIGHT, 1.6),
        stroke_shape(i3, "TeresMajorRightHi", [(18.0, -18.0), (29.5, -16.0)], 1.9, HIGHLIGHT, 1.6),
        smooth_shape(i3, "TeresMajorLeftActivation", teres_major_l_pts, muscle_paint("TeresMajorL", 0.95, scale=0.96)),
        smooth_shape(i3, "TeresMajorRightActivation", teres_major_r_pts, muscle_paint("TeresMajorR", 0.95, scale=0.96)),
        # Sweeping V-Taper Latissimus Dorsi Wings with Pennate Fiber Striations
        stroke_shape(i3, "LatLeftHi", [(-14.0, -6.0), (-24.0, 2.0), (-16.0, 16.0)], 3.2, HIGHLIGHT, 2.8),
        stroke_shape(i3, "LatRightHi", [(14.0, -6.0), (24.0, 2.0), (16.0, 16.0)], 3.2, HIGHLIGHT, 2.8),
        stroke_shape(i3, "LatLeftFiber1", [(-4.0, 5.0), (-17.0, -3.0), (-29.0, -6.0)], 0.95, "737C2D12", 0.3),
        stroke_shape(i3, "LatLeftFiber2", [(-4.0, 15.0), (-16.0, 6.5), (-26.0, 2.0)], 0.95, "737C2D12", 0.3),
        stroke_shape(i3, "LatRightFiber1", [(4.0, 5.0), (17.0, -3.0), (29.0, -6.0)], 0.95, "737C2D12", 0.3),
        stroke_shape(i3, "LatRightFiber2", [(4.0, 15.0), (16.0, 6.5), (26.0, 2.0)], 0.95, "737C2D12", 0.3),
        smooth_shape(i3, "LatLeftActivation", lat_l_pts, muscle_paint("LatLeft", 1.0, scale=1.00)),
        smooth_shape(i3, "LatRightActivation", lat_r_pts, muscle_paint("LatRight", 1.0, scale=1.00)),
        f"{i2}</Node>",

        # --- 5. Thoracolumbar Fascia & Base Dorsal Torso Silhouette ---
        stroke_shape(i2, "LumbarSpinalGroove", [(317.0, 162.0), (317.0, 191.0)], 1.6, CORE_SHADOW, 0.7),
        smooth_shape(i2, "ThoracolumbarFascia", fascia_pts, skin_fill("Fascia", 158, 193, TENDON_NEAR, x0=301, x1=333)),
        stroke_shape(i2, "TorsoLeftHi", [(292.0, 168.0), (297.0, 186.0)], 2.6, HIGHLIGHT, 2.4),
        stroke_shape(i2, "TorsoRightSh", [(341.0, 168.0), (337.0, 186.0)], 2.8, CORE_SHADOW, 2.4),
        smooth_shape(i2, "TorsoBackShape", torso_pts, skin_fill("TorsoBack", 121, 194, SKIN, x0=280, x1=355)),

        f"{ind}</Node>",
    ])


def head_and_neck_foreground_rig():
    """Canonical 3/4 Rear-Left Head & Neck layered in FRONT of the Lat Pulldown Bar so that when the bar descends
    in front of the face/upper chest at r = 1.0, the back of the head & neck naturally occlude the center of the bar."""
    ind = "        "
    i2 = ind + "    "
    head_id = nid()
    key_double(head_id, 14, lambda p: p["torso_dy"])
    p0 = POSES[0]

    neck_pts = [
        (306.5, 110.0), (326.5, 110.0), (329.5, 126.0), (303.5, 126.0),
    ]
    # 3/4 rear-left cranium & left cheek/jawline contour
    head_pts = [
        (303.5, 98.5), (316.5, 91.0), (328.5, 98.0),
        (330.0, 108.0), (324.5, 116.5), (309.0, 117.0),
        (301.0, 113.5), (299.8, 107.5), (301.2, 102.5),
    ]
    # Full occipital cropped athletic hair cap covering the crown and back of the skull down to the tapered nape (y = 91..114.5),
    # with a clean sideburn cut above the left ear (303.5, 108.0)
    hair_pts = [
        (302.5, 100.5), (307.5, 91.8), (318.5, 90.8), (328.5, 97.5),
        (330.0, 107.5), (326.0, 114.2), (318.0, 115.2), (310.5, 114.0),
        (306.5, 109.5), (305.0, 104.5), (302.2, 103.5),
    ]

    return "\n".join([
        f'{ind}<Node y="{f(p0["torso_dy"])}" name="HeadAndNeckForeground" id="{head_id}">',
        stroke_shape(i2, "HairCrownHi", [(309.5, 94.0), (318.5, 93.2), (325.5, 97.5)], 2.2, "40FFFFFF", 2.0),
        smooth_shape(i2, "HairCap", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 304, 91, 329, 115, "FF334155", "FF0F172A")}</Fill>'),
        ellipse_shape(i2, "LeftEar", 304.2, 108.0, 4.2, 6.8, solid("LeftEar", "FFCBD5E1")),
        stroke_shape(i2, "LeftEarHelix", [(304.5, 106.0), (303.5, 108.0), (304.6, 110.0)], 0.9, SOFT_SHADOW, 0.2),
        stroke_shape(i2, "LeftJawlineSh", [(300.8, 112.5), (306.5, 115.8)], 1.2, CORE_SHADOW, 0.6),
        smooth_shape(i2, "HeadShape", head_pts, skin_fill("Head", 91, 117, SKIN, x0=300, x1=330)),
        stroke_shape(i2, "NeckNapeFurrow", [(317.0, 113.5), (317.0, 125.0)], 1.4, CORE_SHADOW, 0.7),
        stroke_shape(i2, "NeckLeftSCMHi", [(308.0, 113.5), (305.5, 124.5)], 1.6, HIGHLIGHT, 1.4),
        smooth_shape(i2, "NeckShape", neck_pts, skin_fill("Neck", 110, 126, SKIN, x0=303, x1=330)),
        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 4. Bilateral Arms (Posterior Deltoid, Biceps, Brachialis, Brachioradialis)
def pulldown_arm_rig(side):
    """3D-Foreshortened Arm (`side` in ('Left', 'Right')) with Posterior deltoid, Biceps brachii,
    Brachialis, and Brachioradialis muscle activations."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "

    is_left = side == "Left"
    skin = SKIN if is_left else SKIN_FAR
    sh_key = "sh_l" if is_left else "sh_r"
    el_key = "elbow_l" if is_left else "elbow_r"
    ua_len = UPPER_ARM_L if is_left else UPPER_ARM_R
    fa_len = FOREARM_L if is_left else FOREARM_R
    ua_key = "ua_l" if is_left else "ua_r"
    ua_sx_key = "ua_l_sx" if is_left else "ua_r_sx"
    fa_key = "fa_l" if is_left else "fa_r"
    fa_sx_key = "fa_l_sx" if is_left else "fa_r_sx"

    delt_id, ua_id, fa_id, bic_id = nid(), nid(), nid(), nid()
    key_double(delt_id, 13, lambda p: p[sh_key][0])
    key_double(delt_id, 14, lambda p: p[sh_key][1])
    key_double(delt_id, 15, lambda p: p[ua_key])

    key_double(ua_id, 13, lambda p: p[sh_key][0])
    key_double(ua_id, 14, lambda p: p[sh_key][1])
    key_double(ua_id, 15, lambda p: p[ua_key])
    key_double(ua_id, 16, lambda p: p[ua_sx_key])
    key_double(bic_id, 17, lambda p: p["biceps_bulge"])

    key_double(fa_id, 13, lambda p: p[el_key][0])
    key_double(fa_id, 14, lambda p: p[el_key][1])
    key_double(fa_id, 15, lambda p: p[fa_key])
    key_double(fa_id, 16, lambda p: p[fa_sx_key])
    p0 = POSES[0]

    # For Left arm (pointing up-left / down-left at ~ -140..+140 deg), local +Y is top/outer (biceps/radial side),
    # local -Y is bottom/inner (posterior deltoid / triceps side). Mirror for Right arm.
    top_sign = 1.0 if is_left else -1.0
    bot_sign = -top_sign

    # 1. Base Upper Arm Silhouette (0 .. ua_len)
    ua_pts = [
        (-6.5, 0.0), (-4.5, -8.5), (9.0, -9.5), (ua_len * 0.56, -8.8), (ua_len - 4.0, -6.2),
        (ua_len + 3.5, 0.0), (ua_len - 4.0, 6.2), (ua_len * 0.56, 8.8), (9.0, 9.5), (-4.5, 8.5),
    ]

    # 2. Activated Biceps brachii & Brachialis on the upper/radial aspect (`top_sign`)
    biceps_pts = [
        (9.0, top_sign * 0.6),
        (ua_len * 0.50, top_sign * 0.4),
        (ua_len - 5.0, top_sign * 1.8),
        (ua_len - 7.0, top_sign * 7.8),
        (ua_len * 0.48, top_sign * 9.2),
        (10.0, top_sign * 7.4),
    ]
    brachialis_pts = [
        (ua_len * 0.46, -top_sign * 0.4),
        (ua_len - 3.0, top_sign * 0.5),
        (ua_len - 4.0, top_sign * 5.0),
        (ua_len * 0.48, top_sign * 4.4),
    ]

    # 3. Sculpted Deltoid Cap + Activated Posterior deltoid (`bot_sign`)
    delt_pts = [
        (-8.0, 0.0), (-5.0, -8.2), (3.5, -9.2), (12.0, -6.6),
        (14.0, 0.0), (12.0, 6.6), (3.5, 9.2), (-5.0, 8.2),
    ]
    post_delt_pts = [
        (-7.0, bot_sign * 0.4),
        (2.5, bot_sign * 9.2),
        (12.5, bot_sign * 6.6),
        (13.5, bot_sign * 0.8),
        (3.5, -bot_sign * 1.6),
    ]

    # 4. Sculpted Forearm (0 .. fa_len) + Activated Brachioradialis along the inner/thumb border
    fa_pts = [
        (-5.5, 0.0), (-3.5, -6.8), (fa_len * 0.36, -7.8), (fa_len - 4.5, -4.4),
        (fa_len + 3.0, 0.0), (fa_len - 4.5, 4.4), (fa_len * 0.36, 7.8), (-3.5, 6.8),
    ]
    brachioradialis_pts = [
        (-2.0, top_sign * 0.4),
        (fa_len * 0.38, top_sign * 1.0),
        (fa_len * 0.74, top_sign * 2.5),
        (fa_len * 0.66, top_sign * 6.4),
        (fa_len * 0.32, top_sign * 7.6),
        (-1.5, top_sign * 5.4),
    ]

    return "\n".join([
        f'{ind}<Node name="{side}PulldownArm">',

        # --- 1. Shoulder Cap & Activated Posterior Deltoid ---
        f'{i2}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" rotation="{f(p0[ua_key])}" name="{side}DeltoidNode" id="{delt_id}">',
        stroke_shape(i3, f"{side}PostDeltHi", [(1.5, bot_sign * 4.6), (10.0, bot_sign * 4.0)], 2.0, HIGHLIGHT, 1.8),
        stroke_shape(i3, f"{side}PostDeltFiber", [(-1.5, bot_sign * 3.2), (10.0, bot_sign * 3.4)], 0.9, "737C2D12", 0.3),
        smooth_shape(i3, f"{side}PosteriorDeltActivation", post_delt_pts, muscle_paint(side + "PostDelt", 0.9, scale=0.86)),
        stroke_shape(i3, f"{side}LatDeltHi", [(1.5, top_sign * 3.8), (10.0, top_sign * 3.4)], 1.8, HIGHLIGHT, 1.8),
        smooth_shape(i3, f"{side}DeltoidCap", delt_pts, skin_fill(side + "Deltoid", -10, 10, skin)),
        f"{i2}</Node>",

        # --- 2. 3D-Foreshortened Upper Arm (Biceps brachii & Brachialis) ---
        f'{i2}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" rotation="{f(p0[ua_key])}" scaleX="{f(p0[ua_sx_key])}" name="{side}UpperArm" id="{ua_id}">',
        f'{i3}<Node scaleY="{f(p0["biceps_bulge"])}" name="{side}BicepsNode" id="{bic_id}">',
        stroke_shape(i4, f"{side}BicepsHi", [(11.0, top_sign * 4.8), (ua_len - 7.0, top_sign * 4.8)], 2.1, HIGHLIGHT, 1.8),
        smooth_shape(i4, f"{side}BrachialisActivation", brachialis_pts, muscle_paint(side + "Brachialis", 0.85, scale=0.84)),
        smooth_shape(i4, f"{side}BicepsActivation", biceps_pts, muscle_paint(side + "Biceps", 0.9, scale=0.85)),
        f"{i3}</Node>",
        stroke_shape(i3, f"{side}TricepsHi", [(10.0, bot_sign * 4.2), (ua_len - 7.0, bot_sign * 4.0)], 2.0, HIGHLIGHT, 1.8),
        stroke_shape(i3, f"{side}HumerusGroove", [(9.0, 0.0), (ua_len - 5.0, 0.0)], 1.2, CORE_SHADOW, 0.6),
        smooth_shape(i3, f"{side}UpperArmShape", ua_pts, skin_fill(side + "UpperArm", -10, 10, skin)),
        f"{i2}</Node>",

        # --- 3. 3D-Foreshortened Forearm (Brachioradialis) ---
        f'{i2}<Node x="{f(p0[el_key][0])}" y="{f(p0[el_key][1])}" rotation="{f(p0[fa_key])}" scaleX="{f(p0[fa_sx_key])}" name="{side}Forearm" id="{fa_id}">',
        stroke_shape(i3, f"{side}BrachioradialisHi", [(3.5, top_sign * 4.2), (fa_len * 0.56, top_sign * 3.8)], 2.0, HIGHLIGHT, 1.8),
        smooth_shape(i3, f"{side}BrachioradialisActivation", brachioradialis_pts, muscle_paint(side + "Brachiorad", 0.9, scale=0.84)),
        stroke_shape(i3, f"{side}ForearmGroove", [(3.5, 0.0), (fa_len * 0.68, 0.0)], 1.1, CORE_SHADOW, 0.6),
        stroke_shape(i3, f"{side}ForearmExtHi", [(4.5, bot_sign * 3.4), (fa_len - 7.0, bot_sign * 2.4)], 2.0, HIGHLIGHT, 2.0),
        smooth_shape(i3, f"{side}ForearmShape", fa_pts, skin_fill(side + "Forearm", -8, 8, skin)),
        f"{i2}</Node>",

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 5. Wide Cambered Lat Pulldown Bar, Hands & Vertical Steel Cable
def lat_bar_hands_and_cable_rig():
    """Animated Wide Cambered Lat Pulldown Bar, Pronated Hands wrapping the angled rubber grips,
    and Vertical Steel Cable connecting PULLEY_TOP (316, 26) to the central swivel eyelet."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    bar_id, cab_id = nid(), nid()
    key_double(bar_id, 14, lambda p: p["bar_y"])
    key_double(cab_id, 17, lambda p: p["cable_len"] / 40.0)
    p0 = POSES[0]

    bar_shaft = (
        f'<Fill name="LatBarShaftFill">{grad("LatBarShaftG", -115, -4, 115, 18, "FF334155", "FF090D16")}</Fill>'
        '<Stroke thickness="0.9" join="round" name="LatBarRim"><SolidColor colorValue="FF475569" name="LatBarRimCol"/></Stroke>'
    )
    rubber_grip = (
        '<Fill name="RubberGripFill"><SolidColor colorValue="FF090D16" name="RubberGripCol"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="RubberGripRim"><SolidColor colorValue="FF334155" name="RubberGripRimCol"/></Stroke>'
    )
    swivel_paint = (
        f'<Fill name="SwivelFill">{grad("SwivelG", -4, -6, 4, 4, "FFF8FAFC", "FF64748B")}</Fill>'
        '<Stroke thickness="0.9" join="round" name="SwivelRim"><SolidColor colorValue="FF334155" name="SwivelRimCol"/></Stroke>'
    )

    # Pronated dorsal hand shapes relative to L_HAND (-98, +10.5) and R_HAND (+98, +13.5)
    hand_l_pts = [(-6.8, -4.5), (6.2, -3.2), (6.8, 4.2), (-5.8, 4.8)]
    hand_r_pts = [(-6.2, -3.2), (6.8, -4.5), (5.8, 4.8), (-6.8, 4.2)]

    return "\n".join([
        f'{ind}<Node name="LatBarHandsAndCable">',

        # 1. Moving Cambered Bar & Pronated Hands at (BAR_CX = 316.0, y = bar_y)
        f'{i2}<Node x="{f(BAR_CX)}" y="{f(p0["bar_y"])}" name="MovingLatBarNode" id="{bar_id}">',

        # Left Pronated Hand at (-98.0, 10.5)
        f'{i3}<Node x="-98.0" y="10.5" rotation="0.28" name="LeftPronatedHand">',
        stroke_shape(i3 + "    ", "LeftKnuckleHi", [(-4.5, -2.2), (4.5, -1.5)], 1.8, HIGHLIGHT, 1.4),
        stroke_shape(i3 + "    ", "LeftFingerCrease1", [(-2.2, -3.8), (-2.0, 4.2)], 0.9, SOFT_SHADOW, 0.2),
        stroke_shape(i3 + "    ", "LeftFingerCrease2", [(1.8, -3.5), (2.0, 4.2)], 0.9, SOFT_SHADOW, 0.2),
        smooth_shape(i3 + "    ", "LeftHandDorsum", hand_l_pts, skin_fill("LeftHand", -5, 5, SKIN)),
        f"{i3}</Node>",

        # Right Pronated Hand at (+98.0, 13.5)
        f'{i3}<Node x="98.0" y="13.5" rotation="-0.28" name="RightPronatedHand">',
        stroke_shape(i3 + "    ", "RightKnuckleHi", [(-4.5, -1.5), (4.5, -2.2)], 1.8, HIGHLIGHT, 1.4),
        stroke_shape(i3 + "    ", "RightFingerCrease1", [(-1.8, -3.5), (-2.0, 4.2)], 0.9, SOFT_SHADOW, 0.2),
        stroke_shape(i3 + "    ", "RightFingerCrease2", [(2.2, -3.8), (2.0, 4.2)], 0.9, SOFT_SHADOW, 0.2),
        smooth_shape(i3 + "    ", "RightHandDorsum", hand_r_pts, skin_fill("RightHand", -5, 5, SKIN_FAR)),
        f"{i3}</Node>",

        # Wide Cambered Steel Bar with Angled Rubber Ends & Central Swivel Hanger
        ellipse_shape(i3, "LeftBarEndCap", -115.0, 16.5, 5.2, 5.2, solid("LBarCap", "FF020617")),
        ellipse_shape(i3, "RightBarEndCap", 115.0, 19.5, 5.2, 5.2, solid("RBarCap", "FF020617")),
        poly_shape(i3, "LeftRubberGrip", [(-115, 14.2), (-74, 0.5), (-72, 5.0), (-113, 18.8)], rubber_grip, radius=1.6),
        poly_shape(i3, "RightRubberGrip", [(74, 3.5), (115, 17.2), (113, 21.8), (72, 8.0)], rubber_grip, radius=1.6),
        stroke_shape(i3, "LatBarTopSpecHi", [(-70.0, -0.5), (0.0, 1.0), (70.0, 2.5)], 1.1, "73F8FAFC", 0.3),
        poly_shape(
            i3, "CamberedLatBarShaft",
            [
                (-115, 14.5), (-72, 0.0), (72, 3.0), (115, 17.5),
                (113, 21.5), (71, 7.2), (-71, 4.2), (-113, 18.5),
            ],
            bar_shaft, radius=1.8,
        ),
        ellipse_shape(i3, "CentralSwivelCollar", 0.0, -2.5, 6.8, 7.5, swivel_paint),
        f"{i2}</Node>",

        # 2. Vertical Steel Cable descending from PULLEY_TOP (316, 26) to the Bar Swivel
        f'{i2}<Node x="{f(PULLEY_TOP[0])}" y="{f(PULLEY_TOP[1] + 2.0)}" scaleY="{f(p0["cable_len"] / 40.0)}" name="VerticalPullCable" id="{cab_id}">',
        poly_shape(i3, "SteelCableCore", [(-1.2, 0.0), (1.2, 0.0), (1.2, 40.0), (-1.2, 40.0)], solid("CableCore", "FF0F172A"), radius=0.4),
        f"{i2}</Node>",

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 6. Commercial Lat Pulldown Tower & Animated Weight Stack
def lat_pulldown_tower_rig():
    """3D Isometric Lat Pulldown Cable Tower in front of the athlete (`x = 228..322, y = 18..296`)
    with twin vertical columns, chrome guide rods, animated black weight stack, overhead pulley boom,
    and front under-bench frame."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    stack_id = nid()
    key_double(stack_id, 14, lambda p: p["stack_lift_y"])

    frame_main = (
        f'<Fill name="TowerMainFill">{grad3("TowerMainG", 24, 296, *FRAME_WHITE, x0=235, x1=310)}</Fill>'
        '<Stroke thickness="1.0" join="round" name="TowerMainRim"><SolidColor colorValue="FF64748B" name="TowerMainRimCol"/></Stroke>'
    )
    frame_far = (
        f'<Fill name="TowerFarFill">{grad3("TowerFarG", 24, 296, *FRAME_FAR, x0=230, x1=295)}</Fill>'
        '<Stroke thickness="1.0" join="round" name="TowerFarRim"><SolidColor colorValue="FF475569" name="TowerFarRimCol"/></Stroke>'
    )
    stack_paint = (
        f'<Fill name="WeightStackFill">{grad3("WeightStackG", 190, 268, *PAD_DARK, x0=248, x1=282)}</Fill>'
        '<Stroke thickness="1.0" join="round" name="WeightStackRim"><SolidColor colorValue="FF020617" name="WeightStackRimCol"/></Stroke>'
    )
    pulley_paint = (
        f'<Fill name="PulleyFill">{grad("PulleyG", -8, -8, 8, 8, "FF94A3B8", "FF1E293B")}</Fill>'
        '<Stroke thickness="1.0" join="round" name="PulleyRim"><SolidColor colorValue="FF0F172A" name="PulleyRimCol"/></Stroke>'
    )
    hub_paint = solid("PulleyHub", "FFF8FAFC")
    rod_paint = solid("GuideRod", "FF94A3B8")

    plate_grooves = [
        stroke_shape(i3, f"StackPlateGroove{idx}", [(249.0, float(y)), (281.0, float(y))], 1.1, "FF020617", 0.0)
        for idx, y in enumerate(range(198, 264, 6))
    ]

    return "\n".join([
        f'{ind}<Node name="LatPulldownTowerRig">',

        # 1. Overhead Pulley Boom, Top Pulley Wheel (316, 26) & Mid Redirect Pulley (294, 86)
        ellipse_shape(i2, "TopPulleyHub", PULLEY_TOP[0], PULLEY_TOP[1], 4.8, 4.8, hub_paint),
        ellipse_shape(i2, "TopPulleyWheel", PULLEY_TOP[0], PULLEY_TOP[1], 14.5, 14.5, pulley_paint),
        ellipse_shape(i2, "MidPulleyHub", PULLEY_MID[0], PULLEY_MID[1], 4.2, 4.2, hub_paint),
        ellipse_shape(i2, "MidPulleyWheel", PULLEY_MID[0], PULLEY_MID[1], 12.5, 12.5, pulley_paint),
        stroke_shape(i2, "OverheadBoomHi", [(291.0, 118.0), (313.0, 22.0)], 1.8, "B3FFFFFF", 0.4),
        poly_shape(
            i2, "OverheadPulleyBoom",
            [(286, 122), (309, 18), (320, 22), (298, 126)],
            frame_main, radius=2.5,
        ),

        # 2. Front Upright Column, Bench Support Pillar & Cross Collars
        poly_shape(i2, "TowerUpperCollar", [(238, 116), (300, 118), (300, 134), (238, 132)], frame_main, radius=1.5),
        poly_shape(i2, "TowerLowerCollar", [(238, 182), (300, 184), (300, 198), (238, 196)], frame_main, radius=1.5),
        stroke_shape(i2, "MainUprightHi", [(287.0, 56.0), (287.0, 290.0)], 2.0, "B3FFFFFF", 0.4),
        poly_shape(i2, "MainUprightColumn", [(283, 52), (295, 52), (295, 292), (283, 292)], frame_main, radius=1.5),
        poly_shape(i2, "TowerTopCap", [(232, 46), (298, 50), (296, 56), (230, 52)], frame_main, radius=2.0),

        # 3. Animated Black Weight Stack sliding up along the Chrome Guide Rods as r: 0.0 -> 1.0
        f'{i2}<Node x="0" y="0" name="WeightStackGroup" id="{stack_id}">',
        poly_shape(i3, "StackLiftCable", [(264, 128), (266, 128), (266, 192), (264, 192)], solid("StackCab", "FF0F172A"), radius=0.3),
        *plate_grooves,
        ellipse_shape(i3, "WeightSelectorPin", 276.0, 232.0, 3.8, 3.8, solid("SelectorPin", "FFF97316")),
        poly_shape(i3, "WeightStackBlock", [(248, 192), (282, 192), (282, 266), (248, 266)], stack_paint, radius=2.0),
        f"{i2}</Node>",

        # 4. Internal Return Cable, Chrome Guide Rods, Rear Upright Column & Base Stabilizer Feet
        stroke_shape(i2, "InternalReturnCable", [(265.0, 192.0), (265.0, 62.0), PULLEY_TOP], 1.6, "FF0F172A", 0.0),
        poly_shape(i2, "GuideRodLeft", [(255, 54), (258, 54), (258, 286), (255, 286)], rod_paint, radius=0.5),
        poly_shape(i2, "GuideRodRight", [(272, 54), (275, 54), (275, 286), (272, 286)], rod_paint, radius=0.5),
        poly_shape(i2, "RearUprightColumn", [(240, 52), (250, 52), (250, 288), (240, 288)], frame_far, radius=1.5),
        poly_shape(i2, "TowerBaseLeft", [(230, 284), (296, 280), (298, 288), (232, 292)], frame_far, radius=1.5),
        poly_shape(i2, "TowerBaseFront", [(282, 282), (324, 288), (322, 295), (280, 290)], frame_main, radius=1.5),

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- 7. Ground Shadow & Studio Backdrop
def floor_shadow_and_scenery():
    ind = "        "
    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"
    return "\n".join([
        f'{ind}<Shape x="316" y="{f(FLOOR - 2)}" scaleX="1.45" scaleY="0.11" name="StationFloorShadow">\n'
        f'{ind}    <Ellipse width="180" height="180" name="ShadowEl"/>\n'
        f'{ind}    <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="90" endY="0" name="ShadowGrad">'
        f'<GradientStop colorValue="99000000" position="0"/><GradientStop colorValue="4D000000" position="0.6"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{ind}</Shape>",
        f'{ind}<Shape x="{W / 2}" y="{f(FLOOR + 1)}" name="FloorLine"><Rectangle width="{W - 40}" height="2" cornerRadiusTL="1" name="FloorRect"/>'
        f'<Fill name="FloorFill"><LinearGradient startX="{-(W - 40) / 2}" startY="0" endX="{(W - 40) / 2}" endY="0" name="FloorGrad">'
        f'<GradientStop colorValue="00475569" position="0"/><GradientStop colorValue="FF475569" position="0.2"/>'
        f'<GradientStop colorValue="FF475569" position="0.8"/><GradientStop colorValue="00475569" position="1"/></LinearGradient></Fill></Shape>',
        f'{ind}<Shape x="{W / 2}" y="{f((FLOOR + H) / 2 + 1)}" name="FloorBand"><Rectangle width="{W}" height="{f(band_h)}" name="FloorBandRect"/>'
        f"{band_fill}</Shape>",
        f'{ind}<Shape x="{W / 2}" y="{H / 2}" name="Backdrop"><Rectangle width="{W}" height="{H}" name="BackdropRect"/>'
        f'<Fill name="BackdropFill"><RadialGradient startX="0" startY="-40" endX="0" endY="{H * 0.75}" name="BackdropGrad">'
        f'<GradientStop colorValue="FF1E293B" position="0"/><GradientStop colorValue="FF0F172A" position="1"/></RadialGradient></Fill></Shape>',
    ])


# Build scene layers (Painter's Order: top of <Artboard> = foreground, bottom = background)
bench_fg_xml = bench_foreground_rig()
left_leg_xml = seated_left_near_leg_rig()
torso_glutes_xml = dorsal_torso_and_glutes_rig()
bench_under_xml = bench_under_seat_rig()
head_fg_xml = head_and_neck_foreground_rig()
left_arm_xml = pulldown_arm_rig("Left")
right_arm_xml = pulldown_arm_rig("Right")
bar_cable_xml = lat_bar_hands_and_cable_rig()
right_leg_xml = seated_right_far_leg_rig()
tower_xml = lat_pulldown_tower_rig()
scenery_xml = floor_shadow_and_scenery()

for _cid, _sc in muscle_fill_ids:
    key_color(_cid, 37, lambda p, sc=_sc: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, muscle_t(p, sc)))
for _cid, _sc in muscle_line_ids:
    key_color(_cid, 37, lambda p, sc=_sc: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, muscle_t(p, sc)))


def build_keyed_xml():
    out = []
    by_obj = {}
    for obj, prop, kind, kfs in keys:
        by_obj.setdefault(obj, []).append((prop, kind, kfs))
    for obj, props in by_obj.items():
        out.append(f'            <KeyedObject objectId="{obj}">')
        for prop, kind, kfs in props:
            out.append(f'                <KeyedProperty propertyKey="{prop}">')
            tag = "KeyFrameDouble" if kind == "double" else "KeyFrameColor"
            for fr, val in kfs:
                v = f(val) if kind == "double" else val
                out.append(f'                    <{tag} frame="{fr}" value="{v}"/>')
            out.append("                </KeyedProperty>")
        out.append("            </KeyedObject>")
    return "\n".join(out)


def generate():
    keyed_xml = build_keyed_xml()
    rml = f"""<Rive version="7.3">
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="LatPulldown" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>
{bench_fg_xml}
{left_leg_xml}
{torso_glutes_xml}
{bench_under_xml}
{head_fg_xml}
{left_arm_xml}
{right_arm_xml}
{bar_cable_xml}
{right_leg_xml}
{tower_xml}
{scenery_xml}
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
        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="LatPulldown" id="0:60">
{keyed_xml}
        </LinearAnimation>
    </Artboard>
</Rive>
"""
    ET.fromstring(rml)
    OUT.write_text(rml, encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {len(keys)} keyed properties across {len(FRAMES)} keyframes)")


def _compile_rml_bytes(rml_path):
    """Pure-Python Rive 7.3 binary compiler matching `rive build rml` byte-for-byte."""
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
    build_dir = HERE / "build"
    build_dir.mkdir(exist_ok=True)
    riv_bytes = _compile_rml_bytes(OUT)
    built_riv = build_dir / "lat_pulldown.riv"
    built_riv.write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    legacy_mk = REPO / "assets/animations/lat_pulldown.movekit"
    if legacy_mk.exists():
        legacy_mk.unlink()

    sys.path.insert(0, str(SCRATCH_RENDERER))
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for label, fr in (("frame_start.png", 0), ("frame_mid.png", 40), ("frame_peak.png", 76)):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        out_png = build_dir / label
        write_png(out_png, 640, 360, rgb640)
        if label == "frame_peak.png":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(620, 20, 320))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    generate()
    if "--publish" in sys.argv:
        publish()
