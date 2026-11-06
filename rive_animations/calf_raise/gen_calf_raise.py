#!/usr/bin/env python3
"""Generates rive_animations/calf_raise/scene.rml (and optionally publishes).

16:9 (640x360, FLOOR = 300.0) 60 fps procedural Rive animation for the
Standing Calf Raise (`id: calf_raise`), matching the 2-panel Fitwill 3/4 rear-right
reference chart:
  - Camera: 3/4 rear-right isometric view showing the sculpted dorsal back
    (Trapezius, Infraspinatus, Latissimus Dorsi, Erector Spinae), Rear/Lateral
    Deltoids, Triceps, Glutes in dark compression shorts, Hamstrings + IT-Band,
    and the full posterior calves (Gastrocnemius Lateral & Medial diamond heads,
    Soleus, and silver-white Achilles tendons) of both legs.
  - Equipment:
    1. 3D isometric Calf-Raise Step Platform resting on FLOOR = 300.0 with a
       beveled metallic silver-grey base and a dark non-slip rubber top mat.
    2. Dual 3D Cast-Iron Dumbbells held in neutral hammer grips at both sides
       (near-right dumbbell at the right hip/thigh; far-left dumbbell protruding
       past the left glute/hip).
  - Biomechanics (`r` in [0.0, 1.0]):
    - Bottom Stretch (`r = 0.0`): Forefoot/toes of both feet anchored on the
      back-left edge of the step platform while the heels hang off the step in
      dorsiflexion stretch (`y ~ 294`).
    - Peak Tiptoe Contraction (`r = 1.0`): High plantarflexion (`+54 deg` arc)
      driving both heels, ankles, shins, knees, thighs, glutes, torso, head, and
      dumbbells upward by `25 px` (`dx = +3.5 px, dy = -25.0 px`) onto the balls
      of the feet, while both Gastrocnemius muscle bellies dynamically shorten
      and bulge (`scaleY: 1.0 -> 0.87, scaleX: 1.0 -> 1.08, dy: 0 -> -3.5 px`)
      above the elongating silver-white Achilles tendons.

Activated muscles (`muscle_t`):
  - Primary: Gastrocnemius (Lateral Head & Medial Head) on both legs
  - Secondary: Soleus flanking the lower calf above the Achilles tendon

Usage (from this directory):
    python3 gen_calf_raise.py            # regenerate scene.rml
    python3 gen_calf_raise.py --publish  # + build .riv, copy to assets, render thumbnail
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
ASSET_RIV = REPO / "assets/animations/calf_raise.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/calf_raise.png"
THUMB_ADVANCE = "1.20s"  # Peak tiptoe contraction (r = 1.0)
THUMB_VIEWPORT = "1280x720"  # 2x the 640x360 artboard
THUMB_CROP = (660, 20, 290)  # square size, offsetY, offsetX in the 2x render
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

# 16:9 standard canvas
W, H = 640, 360
FLOOR = 300.0

# Stationary Ball-of-Foot (Metatarsal) Pivot Anchors on the Step Platform
BALL_NEAR = (323.3, 285.5)
BALL_FAR = (304.3, 282.5)
HINGE_LOCAL = (-21.0, -3.5)

# Timeline (frames @60fps): concentric raise 1.05s (63f), peak tiptoe squeeze 0.35s (21f),
# controlled eccentric lower 1.25s (75f), bottom stretch pause 0.35s (21f) = 180f (3.0s)
RAISE_FRAMES, HOLD_TOP, LOWER_FRAMES, HOLD_BOT = 63, 21, 75, 21
DURATION = RAISE_FRAMES + HOLD_TOP + LOWER_FRAMES + HOLD_BOT
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


EASE_UP = cubic_bezier(0.38, 0.0, 0.28, 1.0)
EASE_DOWN = cubic_bezier(0.42, 0.0, 0.38, 1.0)


def raise_progress(frame):
    """0.0 at bottom calf stretch (Panel 1), 1.0 at peak tiptoe contraction (Panel 2)."""
    fr = frame % DURATION
    if fr <= RAISE_FRAMES:
        return EASE_UP(fr / RAISE_FRAMES)
    fr -= RAISE_FRAMES
    if fr <= HOLD_TOP:
        return 1.0
    fr -= HOLD_TOP
    if fr <= LOWER_FRAMES:
        return 1.0 - EASE_DOWN(fr / LOWER_FRAMES)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def _hinge_offset(theta):
    lx, ly = HINGE_LOCAL
    return (
        lx * math.cos(theta) - ly * math.sin(theta),
        lx * math.sin(theta) + ly * math.cos(theta),
    )


def pose(r):
    """Compute Standing Calf Raise pose at plantarflexion progress r in [0.0, 1.0]."""
    # Foot arch plantarflexion rotation around the stationary ball-of-foot pivot on the step:
    # At r = 0.0 (bottom stretch): -12 deg (heel dipped slightly below the step top edge)
    # At r = 1.0 (peak tiptoe raise): +48 deg (high tiptoe plantarflexion, heel & ankle arc up and forward-right)
    theta_0 = math.radians(-12.0)
    arch_rot = math.radians(lerp(-12.0, 48.0, r))

    # Concentric ankle hinge trajectory around BALL_NEAR / BALL_FAR:
    # Moves upward (dy = -18.9 px) and forward-right (dx = +9.8 px) over the balls of the feet with zero joint drift
    hx0, hy0 = _hinge_offset(theta_0)
    hx, hy = _hinge_offset(arch_rot)
    body_dx = hx - hx0
    body_dy = hy - hy0

    # Dynamic Gastrocnemius belly contraction (shortens vertically and bulges laterally at peak tiptoe squeeze)
    gastroc_dy = lerp(0.0, -3.8, r)
    gastroc_sx = lerp(1.00, 1.08, r)
    gastroc_sy = lerp(1.00, 0.87, r)

    # Subtle stabilizing counter-rotation of the arms so the dumbbells hang dead-vertical under gravity
    arm_sway = math.radians(lerp(0.0, -1.0, r))

    return {
        "r": r,
        "arch_rot": arch_rot,
        "body_dx": body_dx,
        "body_dy": body_dy,
        "gastroc_dy": gastroc_dy,
        "gastroc_sx": gastroc_sx,
        "gastroc_sy": gastroc_sy,
        "arm_sway": arm_sway,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(raise_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all frames
_ANGLE_KEYS = ("arch_rot", "arm_sway")
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
    for _fr in (0, 32, 64, 72, 120, DURATION):
        _p = POSES[_fr]
        print(
            f"f{_fr:3d} r={_p['r']:.3f} body=({_p['body_dx']:+.1f},{_p['body_dy']:+.1f}) "
            f"arch_deg={math.degrees(_p['arch_rot']):+.1f} gastroc_sy={_p['gastroc_sy']:.2f}"
        )


# ---------------------------------------------------------------- RML Helpers
_id = 100


def nid():
    global _id
    _id += 1
    return f"0:{_id}"


def f(v):
    if isinstance(v, float):
        s = f"{v:.3f}".rstrip("0").rstrip(".")
        return "0" if s in ("", "-0") else s
    return str(v)


def smooth_vertices(pts, closed, indent):
    n = len(pts)
    out = []
    for i, (x, y) in enumerate(pts):
        if closed:
            p0 = pts[(i - 1) % n]
            p1 = pts[(i + 1) % n]
        else:
            p0 = pts[max(0, i - 1)]
            p1 = pts[min(n - 1, i + 1)]
        tx, ty = p1[0] - p0[0], p1[1] - p0[1]
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
TENDON_NEAR = ("FFF1F5F9", "FFCBD5E1", "FF94A3B8")
TENDON_FAR = ("FFE2E8F0", "FFB4C1D4", "FF7E8C9F")
SHORTS = ("FF243247", "FF162032", "FF0F172A")
SHORTS_FAR = ("FF1E293B", "FF131C2E", "FF0B1120")
HIGHLIGHT = "40FFFFFF"
CORE_SHADOW = "4D0F172A"
SOFT_SHADOW = "330F172A"

# Dynamic warm orange (0.0 at bottom stretch) -> intense red (1.0 at peak tiptoe raise)
MUSCLE_LOW = "CCF97316"
MUSCLE_HIGH = "F2F43F5E"
MUSCLE_LINE_LOW = "8C7C2D12"
MUSCLE_LINE_HIGH = "CC881337"


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
    """0.0 warm orange at bottom lowered position (r = 0.0), peaking at 1.0 intense crimson at top tiptoe contraction (r = 1.0)."""
    return p["r"]


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
def step_platform_rig():
    """3D Isometric Calf-Raise Step Platform on FLOOR = 300.0 (x = 276..416, y = 278..300) supporting both feet."""
    ind = "        "
    i2 = ind + "    "

    metal_front = f'<Fill name="StepFrontFill">{grad("StepFrontGrad", 330, 287, 416, 300, "FFCBD5E1", "FF475569")}</Fill>'
    metal_left = f'<Fill name="StepLeftFill">{grad("StepLeftGrad", 276, 279, 334, 300, "FF94A3B8", "FF334155")}</Fill>'
    metal_top = f'<Fill name="StepTopRimFill">{grad("StepTopRimGrad", 282, 278, 410, 289, "FFE2E8F0", "FF64748B")}</Fill>'
    rubber_mat = (
        f'<Fill name="RubberMatFill">{grad("RubberMatGrad", 289, 279, 404, 288, "FF1E293B", "FF090D16")}</Fill>'
        '<Stroke thickness="0.9" join="round" name="RubberMatRim"><SolidColor colorValue="FF475569" name="RubberMatRimCol"/></Stroke>'
    )
    bevel_foot = solid("StepFootCorner", "FF334155")

    return "\n".join([
        f'{ind}<Node name="CalfRaiseStepPlatform">',
        # 1. Non-slip black rubber top tread mat (back-left edge from (289, 280.2) to (336, 287.5) directly under both forefeet)
        poly_shape(i2, "StepRubberMat", [(289, 280.2), (356, 278.5), (404, 286.2), (336, 287.5)], rubber_mat, radius=2.0),
        stroke_shape(i2, "MatGripLine1", [(299, 281.2), (358, 279.8)], 0.8, "4064748B", 0.0),
        stroke_shape(i2, "MatGripLine2", [(314, 283.6), (374, 282.2)], 0.8, "4064748B", 0.0),
        stroke_shape(i2, "MatGripLine3", [(329, 286.0), (390, 284.6)], 0.8, "4064748B", 0.0),

        # 2. Metallic top deck bezel around the rubber mat (back-left edge from (282, 279.5) to (334, 288.2))
        poly_shape(i2, "StepTopBezel", [(282, 279.5), (358, 277.8), (410, 286.8), (334, 288.2)], metal_top, radius=2.5),

        # 3. Near-left & front-right beveled metallic side skirts dropping to FLOOR = 300.0
        stroke_shape(i2, "StepCornerCrease", [(334, 288.2), (333, 299.5)], 1.6, "FFE2E8F0", 0.5),
        stroke_shape(i2, "StepTopEdgeHi", [(283, 279.8), (334, 288.2), (409, 287.0)], 1.2, "FFF8FAFC", 0.3),
        poly_shape(i2, "StepFrontRightSkirt", [(334, 288.2), (410, 286.8), (416, 298.8), (333, 300.0)], metal_front, radius=1.5),
        poly_shape(i2, "StepNearLeftSkirt", [(282, 279.5), (334, 288.2), (333, 300.0), (276, 291.5)], metal_left, radius=1.5),

        # 4. Corner rubber bumper feet on FLOOR = 300.0
        poly_shape(i2, "StepFootNear", [(326, 297.0), (342, 297.0), (343, 300.0), (325, 300.0)], bevel_foot, radius=1.0),
        poly_shape(i2, "StepFootRight", [(404, 295.8), (416, 295.8), (417, 299.5), (403, 299.5)], bevel_foot, radius=1.0),
        poly_shape(i2, "StepFootLeft", [(276, 289.0), (286, 290.8), (286, 293.8), (275, 292.0)], bevel_foot, radius=1.0),
        f"{ind}</Node>",
    ])


def foot_rig(prefix, is_near):
    """Two-segment foot (Stationary ToesPad on step + Pivoting HeelArch with concentric talocrural dome at (-21.0, -3.5))."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN if is_near else SKIN_FAR
    bx, by = BALL_NEAR if is_near else BALL_FAR
    arch_id = nid()
    key_double(arch_id, 15, lambda p: p["arch_rot"])
    p0 = POSES[0]

    # Stationary forefoot & toes resting flat on the rubber mat of the step block
    toes_pts = [
        (-4.5, -3.0), (6.5, -3.2), (14.5, -1.8), (17.5, 0.5),
        (15.0, 2.8), (5.0, 3.0), (-4.5, 2.4),
    ]
    # Pivoting midfoot arch, high talus ankle dome (centered at (-21.0, -3.5) so it never separates from the shin/Achilles), and calcaneus heel
    arch_pts = [
        (3.5, -2.5), (-6.0, -5.2), (-14.5, -9.5), (-21.5, -10.5),
        (-26.8, -5.5), (-27.2, 0.5), (-25.5, 5.2), (-19.5, 5.8), (-9.5, 3.8), (2.5, 2.4),
    ]

    return "\n".join([
        f'{ind}<Node x="{f(bx)}" y="{f(by)}" name="{prefix}FootGroup">',
        # 1. Stationary Toes & Metatarsal Pad on the step
        stroke_shape(i2, f"{prefix}ToeCrease1", [(9.0, -1.6), (14.5, -0.4)], 0.9, SOFT_SHADOW, 0.3),
        stroke_shape(i2, f"{prefix}ToeCrease2", [(8.5, 0.6), (14.0, 1.5)], 0.9, SOFT_SHADOW, 0.3),
        smooth_shape(i2, f"{prefix}ToesPad", toes_pts, skin_fill(prefix + "Toes", -4, 3, skin)),

        # 2. Pivoting Rearfoot / Midfoot Arch & Calcaneus Heel
        f'{i2}<Node rotation="{f(p0["arch_rot"])}" name="{prefix}HeelArch" id="{arch_id}">',
        stroke_shape(i3, f"{prefix}ArchHi", [(-21.0, -3.5), (-11.0, -4.5), (-2.0, -1.8)], 2.2, HIGHLIGHT, 2.0),
        stroke_shape(i3, f"{prefix}SoleShadow", [(-24.5, 3.8), (-12.0, 3.0), (-1.0, 1.6)], 2.4, CORE_SHADOW, 2.0),
        smooth_shape(i3, f"{prefix}ArchShape", arch_pts, skin_fill(prefix + "Arch", -10, 6, skin)),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


def posterior_leg_rig(prefix, is_near):
    """Posterior-lateral lower & upper leg in 3/4 rear-right view with sculpted Hamstrings, Gastrocnemius heads, Soleus & Achilles tendon."""
    ind = "            "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN if is_near else SKIN_FAR
    tendon_pal = TENDON_NEAR if is_near else TENDON_FAR
    shorts_pal = SHORTS if is_near else SHORTS_FAR

    # 3/4 perspective offset: Far (left) leg is at x = 283, y = -3; Near (right) leg is at x = 302, y = 0
    ox = 302.0 if is_near else 283.0
    oy = 0.0 if is_near else -3.0

    gastroc_id = nid()
    key_double(gastroc_id, 14, lambda p: 246.0 + p["gastroc_dy"])
    key_double(gastroc_id, 16, lambda p: p["gastroc_sx"])
    key_double(gastroc_id, 17, lambda p: p["gastroc_sy"])
    p0 = POSES[0]

    # Upper Leg / Posterior Thigh (hip y = 174 down to popliteal knee crease y = 230)
    thigh_pts = [
        (-13.5, 172.0), (0.0, 170.0), (14.5, 172.0),
        (16.2, 188.0), (14.8, 206.0), (11.5, 222.0), (9.8, 231.0),
        (0.0, 233.0), (-9.8, 231.0), (-11.5, 222.0), (-13.8, 204.0), (-14.5, 188.0),
    ]
    thigh_shorts_pts = [
        (-14.5, 170.0), (0.0, 168.0), (15.2, 170.0),
        (16.5, 189.0), (0.0, 191.0), (-15.0, 189.0),
    ]

    # Lower Leg / Calf & Shin base silhouette (popliteal knee y = 228 down to calcaneus heel y = 290.5)
    calf_base_pts = [
        (-9.5, 228.0), (0.0, 226.0), (10.2, 228.0),
        (12.8, 240.0), (13.5, 252.0), (10.5, 265.0), (7.2, 276.0), (6.2, 289.0),
        (0.0, 291.0), (-6.2, 289.0), (-6.8, 276.0), (-10.5, 263.0), (-13.8, 249.0), (-12.5, 237.0),
    ]

    # Silver-white Achilles (Calcaneal) Tendon & Aponeurosis (from mid-calf y = 252 down to heel calcaneus y = 291)
    achilles_pts = [
        (-6.5, 252.0), (0.0, 250.0), (6.0, 252.0),
        (4.2, 266.0), (3.5, 278.0), (4.2, 289.0),
        (-0.5, 291.0), (-4.8, 289.0), (-4.0, 277.0), (-5.0, 265.0),
    ]

    # Sculpted Twin Gastrocnemius Bellies (centered around y = 246 in GastrocNode local space so scaleY compresses upward!)
    # Medial Head (inner/left diamond belly, hanging slightly lower anatomically)
    gastroc_medial_pts = [
        (-8.5, -18.0), (-0.5, -19.5), (0.2, -8.0), (-0.5, 9.5),
        (-5.5, 17.5), (-11.8, 13.5), (-14.2, 2.0), (-12.5, -10.0),
    ]
    # Lateral Head (outer/right diamond belly)
    gastroc_lateral_pts = [
        (0.2, -19.0), (8.2, -17.5), (12.2, -9.0), (13.2, 1.5),
        (10.2, 12.5), (4.2, 15.0), (-0.2, 8.5), (-0.2, -8.0),
    ]
    # Soleus muscle rim flanking the lower calf beside the Achilles tendon (y = 252..276)
    soleus_pts = [
        (-10.5, 252.0), (10.0, 252.0), (8.0, 268.0), (5.2, 276.0),
        (-5.5, 276.0), (-8.5, 268.0),
    ]

    out = [f'{ind}<Node x="{f(ox)}" y="{f(oy)}" name="{prefix}LegNode">']

    # 1. Dynamic Contracting Gastrocnemius Bellies (Medial & Lateral Heads + Pennate Striations) at y = 246
    out.append(
        f'{i2}<Node x="0" y="{f(246.0 + p0["gastroc_dy"])}" scaleX="{f(p0["gastroc_sx"])}" scaleY="{f(p0["gastroc_sy"])}" name="{prefix}GastrocNode" id="{gastroc_id}">'
    )
    # Central inter-head anatomical sulcus separating Medial & Lateral Gastrocnemius
    out.append(stroke_shape(i3, f"{prefix}GastrocSulcus", [(-0.2, -17.0), (-0.3, -2.0), (-0.5, 11.5)], 1.5, "B37C2D12", 0.5))
    # Feather specular highlights on both diamond calf bellies
    out.append(stroke_shape(i3, f"{prefix}MedialCalfHi", [(-7.5, -11.0), (-8.5, 0.5), (-6.5, 10.5)], 2.8, HIGHLIGHT, 2.8))
    out.append(stroke_shape(i3, f"{prefix}LateralCalfHi", [(6.2, -10.5), (7.2, 0.5), (5.5, 9.5)], 2.6, HIGHLIGHT, 2.8))
    # Diagonal pennate muscle fiber striations matching the Fitwill anatomical reference
    out.append(stroke_shape(i3, f"{prefix}MedialFiber1", [(-1.5, -10.0), (-7.5, -5.0), (-12.0, 0.0)], 0.95, "737C2D12", 0.3))
    out.append(stroke_shape(i3, f"{prefix}MedialFiber2", [(-1.2, -2.0), (-7.5, 3.5), (-11.5, 9.0)], 0.95, "737C2D12", 0.3))
    out.append(stroke_shape(i3, f"{prefix}LateralFiber1", [(1.2, -9.5), (6.8, -4.5), (11.2, 0.5)], 0.95, "737C2D12", 0.3))
    out.append(stroke_shape(i3, f"{prefix}LateralFiber2", [(1.0, -1.5), (6.5, 4.0), (10.0, 8.5)], 0.95, "737C2D12", 0.3))
    out.append(smooth_shape(i3, f"{prefix}GastrocLateral", gastroc_lateral_pts, muscle_paint(prefix + "GastrocLat", 0.95)))
    out.append(smooth_shape(i3, f"{prefix}GastrocMedial", gastroc_medial_pts, muscle_paint(prefix + "GastrocMed", 0.95)))
    out.append(f"{i2}</Node>")

    # 2. Silver-White Achilles Tendon & Lateral Malleolus Ankle Landmark
    out.append(ellipse_shape(i2, f"{prefix}LateralMalleolus", 4.8, 282.5, 4.5, 5.5, solid(prefix + "Malleolus", "FFCBD5E1")))
    out.append(stroke_shape(i2, f"{prefix}AchillesFiber1", [(-1.6, 258.0), (-1.4, 274.0), (-1.1, 288.0)], 1.0, "66475569", 0.3))
    out.append(stroke_shape(i2, f"{prefix}AchillesFiber2", [(1.4, 258.0), (1.1, 274.0), (0.9, 288.0)], 1.0, "66475569", 0.3))
    out.append(stroke_shape(i2, f"{prefix}AchillesHi", [(0.0, 259.0), (0.0, 275.0), (-0.2, 288.0)], 2.0, "80FFFFFF", 1.5))
    out.append(smooth_shape(i2, f"{prefix}AchillesTendon", achilles_pts, skin_fill(prefix + "Achilles", 250, 291, tendon_pal, x0=5, x1=-5)))

    # 3. Soleus Muscle Flanking the Lower Calf (sculpted anatomical contour beside the Achilles tendon)
    out.append(stroke_shape(i2, f"{prefix}SoleusGrooveL", [(-6.2, 260.0), (-5.2, 272.0), (-4.5, 282.0)], 1.1, CORE_SHADOW, 0.6))
    out.append(stroke_shape(i2, f"{prefix}SoleusGrooveR", [(5.5, 260.0), (4.6, 272.0), (4.0, 282.0)], 1.1, CORE_SHADOW, 0.6))
    out.append(smooth_shape(i2, f"{prefix}SoleusMuscle", soleus_pts, skin_fill(prefix + "Soleus", 252, 276, skin, x0=9, x1=-9)))

    # 4. Base Lower-Leg Silhouette
    out.append(smooth_shape(i2, f"{prefix}CalfBase", calf_base_pts, skin_fill(prefix + "CalfBase", 226, 286, skin, x0=12, x1=-12)))

    # 5. Upper Leg: Compression Shorts Hem + Sculpted Hamstrings (Biceps Femoris, Semitendinosus) & IT-Band
    out.append(stroke_shape(i2, f"{prefix}ShortsHem", [(-14.5, 189.0), (0.0, 190.5), (16.0, 189.0)], 1.3, "730F172A", 0.4))
    out.append(smooth_shape(i2, f"{prefix}ThighShorts", thigh_shorts_pts, skin_fill(prefix + "Shorts", 168, 191, shorts_pal, x0=15, x1=-15)))
    # Popliteal fossa (back-of-knee anatomical V-tendons: Biceps Femoris lateral tendon & Semitendinosus medial tendon)
    out.append(stroke_shape(i2, f"{prefix}PoplitealMedial", [(-6.5, 212.0), (-8.2, 224.0), (-7.5, 232.0)], 1.3, CORE_SHADOW, 0.8))
    out.append(stroke_shape(i2, f"{prefix}PoplitealLateral", [(6.2, 212.0), (7.8, 224.0), (7.2, 232.0)], 1.3, CORE_SHADOW, 0.8))
    # Central hamstring sulcus (between Semitendinosus and Biceps Femoris) + Iliotibial Band (on near-right leg)
    out.append(stroke_shape(i2, f"{prefix}HamstringSulcus", [(-0.8, 191.0), (-0.5, 208.0), (-0.2, 225.0)], 1.4, CORE_SHADOW, 0.9))
    if is_near:
        out.append(stroke_shape(i2, f"{prefix}ITBandGroove", [(9.5, 190.0), (10.2, 208.0), (8.8, 224.0)], 1.3, SOFT_SHADOW, 0.8))
        out.append(stroke_shape(i2, f"{prefix}ThighHi", [(4.5, 192.0), (5.0, 208.0), (4.2, 222.0)], 3.2, HIGHLIGHT, 3.0))
    out.append(stroke_shape(i2, f"{prefix}ThighSh", [(-7.5, 192.0), (-7.0, 208.0), (-6.0, 222.0)], 3.5, CORE_SHADOW, 3.2))
    out.append(smooth_shape(i2, f"{prefix}ThighShape", thigh_pts, skin_fill(prefix + "Thigh", 170, 232, skin, x0=15, x1=-15)))
    out.append(f"{ind}</Node>")
    return "\n".join(out)


def dorsal_torso_glutes_head_rig():
    """Sculpted 3/4 Rear-Right Dorsal Back (Trapezius, Infraspinatus, Latissimus Dorsi, Erector Spinae), Glutes in Shorts, and Head."""
    ind = "            "
    i2 = ind + "    "
    i3 = i2 + "    "

    # 1. Sculpted Glutes in Dark Compression Shorts (with left/far glute mound, right/near glute mound, and intergluteal cleft)
    glutes_shorts_pts = [
        (274.0, 150.0), (294.0, 148.5), (318.0, 150.5),
        (322.5, 166.0), (319.5, 182.0), (302.0, 186.0),
        (285.0, 184.0), (271.5, 178.0), (269.0, 163.0),
    ]

    # 2. Dorsal Torso V-Taper Silhouette (C7 neck base y = 84 down to waist y = 152)
    torso_pts = [
        (285.0, 82.0), (298.0, 80.0), (311.0, 83.0),
        (325.0, 96.0), (327.0, 114.0), (320.5, 134.0), (316.5, 152.0),
        (295.0, 154.0), (275.5, 151.0), (273.5, 134.0), (268.5, 112.0), (272.0, 94.0),
    ]
    # Anatomical back muscle plates (Trapezius diamond, Left & Right Scapular Infraspinatus, Latissimus Dorsi wings, Erector Spinae pillars)
    trap_pts = [
        (286.0, 74.0), (299.0, 73.0), (311.0, 85.0),
        (303.0, 102.0), (294.0, 118.0), (285.0, 102.0), (277.0, 88.0),
    ]
    scapula_r_pts = [
        (298.0, 92.0), (316.0, 93.0), (321.0, 109.0), (312.0, 121.0), (297.0, 114.0),
    ]
    scapula_l_pts = [
        (273.0, 93.0), (288.0, 92.0), (289.0, 113.0), (277.0, 119.0), (270.0, 107.0),
    ]
    erector_r_pts = [
        (295.0, 116.0), (305.0, 116.0), (304.0, 149.0), (294.5, 149.0),
    ]
    erector_l_pts = [
        (283.0, 116.0), (292.0, 116.0), (292.0, 149.0), (284.0, 149.0),
    ]
    back_muscle_paint = (
        '<Fill name="BackMuscleFill"><SolidColor colorValue="1A0F172A" name="BackMuscleCol"/></Fill>'
        '<Stroke thickness="0.95" join="round" name="BackMuscleEdge"><SolidColor colorValue="420F172A" name="BackMuscleEdgeCol"/></Stroke>'
    )

    # 3. 3/4 Rear-Right Head & Neck (y = 46..84)
    neck_pts = [
        (288.0, 68.0), (307.0, 68.0), (310.0, 84.0), (285.0, 84.0),
    ]
    # Cranium + right facial profile (brow, nose tip, jawline) in 3/4 rear-right view
    head_pts = [
        (285.0, 54.0), (297.0, 46.5), (309.5, 51.0),
        (312.5, 58.5), (314.2, 63.5), (312.2, 67.5), (311.8, 72.5),
        (305.5, 74.5), (293.0, 72.0), (284.5, 64.0),
    ]
    hair_pts = [
        (284.5, 56.0), (288.0, 47.0), (300.0, 46.0), (310.0, 51.5),
        (308.0, 57.0), (301.0, 56.0), (294.0, 63.0), (285.5, 64.5),
    ]

    return "\n".join([
        f'{ind}<Node name="TorsoGlutesAndHead">',
        # 1. Sculpted Glutes in Compression Shorts (drawn over upper torso waist and upper thighs)
        stroke_shape(i2, "ShortsWaistband", [(274.5, 150.5), (295.0, 149.0), (317.5, 151.0)], 1.4, "80020617", 0.4),
        # Intergluteal cleft & gluteal fold shading
        stroke_shape(i2, "GluteCleft", [(292.0, 152.0), (288.5, 167.0), (287.0, 183.0)], 2.2, "99020617", 0.8),
        stroke_shape(i2, "NearGluteHi", [(300.0, 156.0), (308.0, 166.0), (303.0, 178.0)], 4.0, "26FFFFFF", 3.5),
        stroke_shape(i2, "FarGluteHi", [(278.0, 156.0), (275.0, 166.0), (277.0, 175.0)], 3.0, "1FFFFFFF", 3.0),
        stroke_shape(i2, "GluteFoldNear", [(290.0, 183.5), (304.0, 185.5), (316.0, 181.5)], 1.8, "8C020617", 0.8),
        stroke_shape(i2, "GluteFoldFar", [(272.0, 177.5), (280.0, 182.5), (287.0, 182.0)], 1.6, "8C020617", 0.8),
        smooth_shape(i2, "GlutesShorts", glutes_shorts_pts, skin_fill("GlutesShorts", 148, 186, SHORTS, x0=318, x1=270)),

        # 2. Dorsal Back Anatomy (Trapezius, Scapulae, Latissimus Dorsi, Erector Spinae & Median Spinal Furrow)
        stroke_shape(i2, "SpinalFurrow", [(294.5, 78.0), (294.0, 114.0), (293.0, 149.0)], 1.8, CORE_SHADOW, 0.9),
        stroke_shape(i2, "LatWingRightLine", [(320.0, 114.0), (311.0, 132.0), (304.0, 148.0)], 1.3, SOFT_SHADOW, 0.8),
        stroke_shape(i2, "LatWingLeftLine", [(272.0, 113.0), (279.0, 131.0), (284.0, 148.0)], 1.3, SOFT_SHADOW, 0.8),
        smooth_shape(i2, "ErectorRight", erector_r_pts, back_muscle_paint),
        smooth_shape(i2, "ErectorLeft", erector_l_pts, back_muscle_paint),
        smooth_shape(i2, "ScapulaRight", scapula_r_pts, back_muscle_paint),
        smooth_shape(i2, "ScapulaLeft", scapula_l_pts, back_muscle_paint),
        smooth_shape(i2, "Trapezius", trap_pts, back_muscle_paint),
        stroke_shape(i2, "BackHiRight", [(306.0, 88.0), (314.0, 112.0), (310.0, 138.0)], 3.8, HIGHLIGHT, 3.8),
        stroke_shape(i2, "BackShLeft", [(274.0, 96.0), (273.0, 120.0), (277.0, 144.0)], 4.0, CORE_SHADOW, 3.8),
        smooth_shape(i2, "TorsoBackShape", torso_pts, skin_fill("TorsoBack", 80, 154, SKIN, x0=324, x1=270)),

        # 3. 3/4 Rear-Right Head & Neck
        f'{i2}<Node name="HeadAndNeck">',
        smooth_shape(i3, "HairCap", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 286, 46, 308, 65, "FF334155", "FF0F172A")}</Fill>'),
        ellipse_shape(i3, "RightEar", 302.5, 62.5, 4.2, 7.0, solid("Ear", "FFCBD5E1")),
        stroke_shape(i3, "EarHelix", [(302.2, 60.5), (303.2, 62.5), (302.0, 64.5)], 0.9, SOFT_SHADOW, 0.2),
        stroke_shape(i3, "JawlineShadow", [(303.5, 71.5), (310.5, 72.5)], 1.4, CORE_SHADOW, 0.8),
        stroke_shape(i3, "HeadCrownHi", [(292.0, 49.5), (301.0, 48.5), (308.0, 52.5)], 2.6, HIGHLIGHT, 2.5),
        smooth_shape(i3, "HeadShape", head_pts, skin_fill("Head", 46, 75, SKIN, x0=314, x1=284)),
        stroke_shape(i3, "NeckTrapCrease", [(293.0, 68.0), (294.0, 82.0)], 1.4, CORE_SHADOW, 0.8),
        stroke_shape(i3, "NeckSCMRight", [(303.5, 69.0), (306.5, 82.0)], 1.3, SOFT_SHADOW, 0.7),
        smooth_shape(i3, "NeckShape", neck_pts, skin_fill("Neck", 68, 84, SKIN, x0=308, x1=286)),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


def dumbbell_3d(indent, prefix, is_near):
    """3D Cast-Iron Double-Plate Dumbbell in 3/4 rear-right perspective (rear-left plate stack in foreground, front-right in background)."""
    i2 = indent + "    "
    plate_face = (
        f'<Fill name="{prefix}PlateFace">{grad(prefix + "PFG", -9, -15, 9, 15, "FF334155", "FF090D16")}</Fill>'
        f'<Stroke thickness="1.0" name="{prefix}PlateRim"><SolidColor colorValue="FF64748B" name="{prefix}PRCol"/></Stroke>'
    )
    plate_edge = (
        f'<Fill name="{prefix}PlateEdge"><SolidColor colorValue="FF0F172A" name="{prefix}PECol"/></Fill>'
        f'<Stroke thickness="0.9" name="{prefix}PlateEdgeRim"><SolidColor colorValue="FF475569" name="{prefix}PERCol"/></Stroke>'
    )
    chrome_bar = f'<Fill name="{prefix}BarFill">{grad(prefix + "BarG", -14, -3, 14, 3, "FFF8FAFC", "FF475569")}</Fill>'
    skin = SKIN if is_near else SKIN_FAR

    # Wrapped fingers & thumb around the knurled handle
    fingers_pts = [
        (-5.5, -4.2), (4.5, -5.0), (6.5, 0.5), (4.2, 5.2), (-5.5, 4.5),
    ]
    thumb_pts = [
        (-6.5, -2.5), (-1.5, -5.8), (3.5, -4.5), (2.0, -1.2), (-4.5, -0.5),
    ]

    out = [f'{indent}<Node name="{prefix}DumbbellAndHand">']
    # 1. Foreground: Rear-Left Double Cast-Iron Plate Stack (closest to camera in 3/4 rear-right view!)
    out.append(ellipse_shape(i2, f"{prefix}RearCollar", -14.5, 2.8, 5.5, 8.5, chrome_bar, rot_deg=-8.0))
    out.append(ellipse_shape(i2, f"{prefix}RearOuterPlateEdge", -13.2, 2.5, 13.0, 23.0, plate_edge, rot_deg=-8.0))
    out.append(ellipse_shape(i2, f"{prefix}RearOuterPlateFace", -11.8, 2.2, 13.0, 23.0, plate_face, rot_deg=-8.0))
    out.append(ellipse_shape(i2, f"{prefix}RearInnerPlateEdge", -9.5, 1.8, 16.5, 29.0, plate_edge, rot_deg=-8.0))
    out.append(ellipse_shape(i2, f"{prefix}RearInnerPlateFace", -7.8, 1.5, 16.5, 29.0, plate_face, rot_deg=-8.0))

    # 2. Midground: Hand / Fingers wrapped around the Chrome Handle
    if is_near:
        out.append(smooth_shape(i2, f"{prefix}Thumb", thumb_pts, skin_fill(prefix + "Thumb", -6, 0, skin)))
        out.append(stroke_shape(i2, f"{prefix}Knuckle1", [(-2.0, -3.5), (-1.8, 3.8)], 0.9, SOFT_SHADOW, 0.3))
        out.append(stroke_shape(i2, f"{prefix}Knuckle2", [(1.2, -3.8), (1.4, 4.0)], 0.9, SOFT_SHADOW, 0.3))
        out.append(smooth_shape(i2, f"{prefix}Fingers", fingers_pts, skin_fill(prefix + "Fingers", -5, 5, skin)))
    poly_shape_bar = [(-14.0, -0.5), (14.0, -4.5), (14.5, -1.0), (-13.5, 3.0)]
    out.append(poly_shape(i2, f"{prefix}HandleBar", poly_shape_bar, chrome_bar, radius=1.2))

    # 3. Background: Front-Right Double Cast-Iron Plate Stack (further from camera, extending out to the right!)
    out.append(ellipse_shape(i2, f"{prefix}FrontInnerPlateEdge", 8.5, -1.5, 16.5, 29.0, plate_edge, rot_deg=-8.0))
    out.append(ellipse_shape(i2, f"{prefix}FrontInnerPlateFace", 10.2, -1.8, 16.5, 29.0, plate_face, rot_deg=-8.0))
    out.append(ellipse_shape(i2, f"{prefix}FrontOuterPlateEdge", 12.2, -2.2, 13.0, 23.0, plate_edge, rot_deg=-8.0))
    out.append(ellipse_shape(i2, f"{prefix}FrontOuterPlateFace", 13.8, -2.5, 13.0, 23.0, plate_face, rot_deg=-8.0))
    out.append(ellipse_shape(i2, f"{prefix}FrontCollar", 15.2, -2.8, 5.0, 8.0, chrome_bar, rot_deg=-8.0))
    out.append(f"{indent}</Node>")
    return "\n".join(out)


def near_right_arm_rig():
    """Sculpted Near (Right) Shoulder Deltoid, Triceps Horseshoe, Forearm Extensors & 3D Cast-Iron Dumbbell at (318, 94)."""
    ind = "            "
    i2 = ind + "    "
    arm_id = nid()
    key_double(arm_id, 15, lambda p: p["arm_sway"])
    p0 = POSES[0]

    # Origin (0,0) at right shoulder (318.0, 94.0); arm hangs vertically down to wrist at (7.0, 84.0) = (325.0, 178.0)
    delt_pts = [
        (-13.0, -6.0), (0.0, -10.0), (12.5, -4.0), (14.5, 10.0),
        (9.5, 22.0), (-2.0, 24.0), (-12.5, 14.0),
    ]
    upper_arm_pts = [
        (-9.5, 8.0), (11.5, 8.0), (13.2, 24.0), (11.0, 42.0),
        (2.0, 45.0), (-8.2, 42.0), (-10.5, 26.0),
    ]
    forearm_pts = [
        (-7.5, 40.0), (10.2, 40.0), (12.0, 54.0), (10.5, 70.0),
        (9.2, 82.0), (2.5, 84.0), (-4.0, 70.0), (-7.2, 54.0),
    ]

    return "\n".join([
        f'{ind}<Node x="318" y="94" rotation="{f(p0["arm_sway"])}" name="NearRightArm" id="{arm_id}">',
        # 1. Sculpted Deltoid (Posterior, Lateral, and Anterior heads)
        stroke_shape(i2, "NearDeltPostGroove", [(-6.5, 2.0), (-3.5, 12.0), (-1.0, 21.0)], 1.3, CORE_SHADOW, 0.8),
        stroke_shape(i2, "NearDeltLatHi", [(3.5, -3.0), (6.5, 8.0), (4.5, 18.0)], 3.2, HIGHLIGHT, 3.0),
        smooth_shape(i2, "NearDeltoid", delt_pts, skin_fill("NearDelt", -10, 24, SKIN, x0=13, x1=-13)),

        # 2. Sculpted Triceps Brachii (Lateral & Long Heads) + Upper Arm
        stroke_shape(i2, "TricepsHorseshoe", [(-2.5, 19.0), (2.5, 27.0), (4.5, 38.0)], 1.4, CORE_SHADOW, 0.9),
        stroke_shape(i2, "UpperArmHi", [(5.5, 16.0), (6.5, 28.0), (5.5, 39.0)], 2.8, HIGHLIGHT, 2.8),
        stroke_shape(i2, "UpperArmSh", [(-6.5, 18.0), (-6.0, 30.0), (-5.0, 40.0)], 3.2, CORE_SHADOW, 3.0),
        smooth_shape(i2, "NearUpperArm", upper_arm_pts, skin_fill("NearUA", 8, 45, SKIN, x0=12, x1=-10)),

        # 3. Sculpted Forearm (Brachioradialis & Extensor Carpi)
        stroke_shape(i2, "ForearmExtensorGroove", [(1.5, 44.0), (3.5, 58.0), (5.0, 74.0)], 1.2, SOFT_SHADOW, 0.7),
        stroke_shape(i2, "ForearmHi", [(6.5, 45.0), (7.5, 58.0), (7.0, 74.0)], 2.4, HIGHLIGHT, 2.5),
        stroke_shape(i2, "ForearmSh", [(-4.5, 46.0), (-3.0, 60.0), (-1.0, 74.0)], 2.8, CORE_SHADOW, 2.5),
        smooth_shape(i2, "NearForearm", forearm_pts, skin_fill("NearFA", 40, 84, SKIN, x0=11, x1=-7)),

        # 4. 3D Cast-Iron Dumbbell in Neutral Hammer Grip at Wrist (6.0, 84.0)
        f'{i2}<Node x="6" y="84" name="NearDumbbellPivot">',
        dumbbell_3d(i2 + "    ", "Near", True),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


def far_left_arm_rig():
    """Far (Left) Rear Deltoid, Triceps, Forearm & Protruding Left Cast-Iron Dumbbell at (274, 96)."""
    ind = "            "
    i2 = ind + "    "
    arm_id = nid()
    key_double(arm_id, 15, lambda p: p["arm_sway"])
    p0 = POSES[0]

    delt_pts = [
        (-10.5, -4.0), (2.0, -8.0), (10.0, 0.0), (8.0, 18.0), (-4.0, 21.0), (-11.5, 10.0),
    ]
    upper_arm_pts = [
        (-10.0, 8.0), (6.0, 8.0), (5.0, 40.0), (-6.5, 42.0), (-11.2, 24.0),
    ]
    forearm_pts = [
        (-8.5, 38.0), (4.5, 38.0), (6.5, 76.0), (-2.5, 78.0), (-9.2, 54.0),
    ]

    return "\n".join([
        f'{ind}<Node x="274" y="96" rotation="{f(p0["arm_sway"])}" name="FarLeftArm" id="{arm_id}">',
        smooth_shape(i2, "FarDeltoid", delt_pts, skin_fill("FarDelt", -8, 21, SKIN_FAR, x0=8, x1=-11)),
        stroke_shape(i2, "FarTricepsLine", [(-6.5, 16.0), (-5.5, 28.0), (-4.0, 38.0)], 1.2, CORE_SHADOW, 0.8),
        smooth_shape(i2, "FarUpperArm", upper_arm_pts, skin_fill("FarUA", 8, 42, SKIN_FAR, x0=5, x1=-11)),
        smooth_shape(i2, "FarForearm", forearm_pts, skin_fill("FarFA", 38, 78, SKIN_FAR, x0=5, x1=-9)),
        # Protruding Left 3D Dumbbell at (-2.0, 80.0) = (272.0, 176.0)
        f'{i2}<Node x="-2" y="80" name="FarDumbbellPivot">',
        dumbbell_3d(i2 + "    ", "Far", False),
        f"{i2}</Node>",
        f"{ind}</Node>",
    ])


def rising_body_rig():
    """Master kinematic root for the rising body (Ankles -> Calves -> Thighs -> Glutes/Torso/Head -> Arms/Dumbbells)."""
    ind = "        "
    body_id = nid()
    key_double(body_id, 13, lambda p: p["body_dx"])
    key_double(body_id, 14, lambda p: p["body_dy"])
    p0 = POSES[0]

    return "\n".join([
        f'{ind}<Node x="{f(p0["body_dx"])}" y="{f(p0["body_dy"])}" name="RisingBodyRoot" id="{body_id}">',
        # Foreground: Near (Right) Arm & 3D Cast-Iron Dumbbell
        near_right_arm_rig(),
        # Midground: Sculpted Dorsal Torso, Glutes in Shorts, and 3/4 Rear-Right Head
        dorsal_torso_glutes_head_rig(),
        # Near (Right) Posterior Leg (Hamstrings, Twin Gastrocnemius Heads, Soleus, Achilles Tendon)
        posterior_leg_rig("Near", True),
        # Far (Left) Posterior Leg (offset back-left in 3/4 perspective)
        posterior_leg_rig("Far", False),
        # Background: Far (Left) Arm & Protruding Left Cast-Iron Dumbbell
        far_left_arm_rig(),
        f"{ind}</Node>",
    ])


def shadow():
    ind = "        "
    return "\n".join([
        f'{ind}<Shape x="336" y="{f(FLOOR + 1)}" scaleX="0.95" scaleY="0.075" name="StepAndAthleteShadow">\n'
        f'{ind}    <Ellipse width="200" height="200" name="ShadowEl"/>\n'
        f'{ind}    <Fill name="ShadowFill"><RadialGradient startX="0" startY="0" endX="100" endY="0" name="ShadowGrad">'
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


body_xml = rising_body_rig()
near_foot_xml = foot_rig("Near", True)
far_foot_xml = foot_rig("Far", False)
step_xml = step_platform_rig()
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
    <!-- Standing Calf Raise: 60 fps, 16:9 (640x360), generated by gen_calf_raise.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="CalfRaise" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- Rising Body (Ankles -> Calves -> Thighs -> Glutes/Torso/Head -> Arms/Dumbbells) -->
{body_xml}

        <!-- Articulated Feet (Stationary Toes on Step + Pivoting Rearfoot/Calcaneus Heel) -->
{near_foot_xml}
{far_foot_xml}

        <!-- 3D Isometric Calf-Raise Step Platform on FLOOR = 300.0 -->
{step_xml}

        <!-- Floor Shadow & Scenery -->
{shd_xml}
{scenery()}

        <StateMachine name="CalfRaiseSM" id="0:7">
            <StateMachineLayer name="Motion" id="0:8">
                <AnyState x="200" y="-120"/>
                <ExitState x="400" y="-120"/>
                <EntryState>
                    <StateTransition stateToId="0:12"/>
                </EntryState>
                <AnimationState x="200" animationId="0:60" id="0:12"/>
            </StateMachineLayer>
        </StateMachine>

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="calf_raise" id="0:60">
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
    assert len(header) == 52, f"Expected 52-byte Rive 7.3 TOC header, got {len(header)}"
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
    built = HERE / "build/calf_raise.riv"
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
