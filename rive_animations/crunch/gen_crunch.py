#!/usr/bin/env python3
"""Generate crunch.rml — 60 FPS, 16:9 (640x360, FLOOR = 300.0) HD procedural Rive animation for Abdominal Crunch.

Matches the repository visual standard and the 2-panel Abdominal Crunch reference illustration:
- Side / slight 3/4 right-side supine profile on a dark beveled exercise mat on FLOOR = 300.0,
  with the athlete's head on the left and bent knees / planted bare feet on the right.
- Stationary Pelvis & Bent Legs (~85 deg knee flexion):
  * Dark navy/slate compression shorts (`SHORTS`) resting on the mat (`x ~ 330..394, y ~ 240..294`)
    with diagonal mid-thigh hems (`x ~ 410..432`) and inner seam creases.
  * Far (Left) Leg (`SKIN_FAR`) slightly behind/up-left (`FAR_KNEE = (424, 166)`) and Near (Right) Leg
    (`SKIN`) in foreground (`NEAR_KNEE = (434, 170)`), with sculpted quadriceps (`Rectus Femoris`,
    `Vastus Lateralis`), rounded patella, lower-leg `Tibialis Anterior` + `Gastrocnemius`/`Soleus`
    calf curve, ankle malleolus, and bare feet (`x ~ 480..538, y ~ 274..294`) planted flat on the mat.
- Thoracic Spinal Flexion Crunch Kinematics (`DURATION = 150` frames / `2.5s` @ `60 FPS`):
  * `0..12`: Bottom supine stretch hold (`r = 0.0`, top panel of reference)
  * `12..62`: Smooth concentric abdominal crunch upward (`r: 0.0 -> 1.0`)
  * `62..80`: Peak isometric abdominal contraction hold at the top (`r = 1.0`, bottom panel of reference)
  * `80..138`: Controlled eccentric lowering back to supine (`r: 1.0 -> 0.0`)
  * `138..150`: Bottom supine hold (`r = 0.0`)
- Seamless Core Compression & Muscle Activation (`MUSCLE_LOW` #FFF97316 -> `MUSCLE_HIGH` #FFF43F5E):
  * Stationary lower lumbar base stays pressed into the floor mat (`x ~ 274..336, y ~ 282..294`).
  * Thoracic ribcage, sculpted `Pectoralis Major`, head (with dark navy hair cap and upward/forward
    facial profile), and hands-behind-head arms curl smoothly upward-right (`~34 deg` thoracic flexion).
  * `CoreMuscleGroup` (anchored at the stationary shorts waistband `x = 334`) compresses horizontally
    (`scaleX: 1.00 -> 0.72`), thickens vertically (`scaleY: 1.00 -> 1.08`), and tilts upward (`+9 deg`)
    so the **Rectus Abdominis** (`scale = 1.0`) 6-pack blocks and **External & Internal Oblique**
    (`scale = 0.92`) lateral plate stay 100% seamlessly connected between the costal arch of the chest
    and the shorts waistband with zero gap or hinge crease.

Run:
    python3 rive_animations/crunch/gen_crunch.py            # writes scene.rml
    python3 rive_animations/crunch/gen_crunch.py --publish  # builds .riv + copies asset & 256x256 thumbnail
"""
import math
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "scene.rml"
ASSET_RIV = REPO / "assets/animations/crunch.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/crunch.png"
THUMB_ADVANCE = "1.15s"      # Frame 69: Peak isometric top crunch contraction (r = 1.0)
THUMB_VIEWPORT = "1280x720"  # 2x the 640x360 artboard
THUMB_CROP = (560, 120, 260)  # square size, offsetY, offsetX in the 2x render
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

# 16:9 standard canvas
W, H = 640, 360
FLOOR = 300.0

# Timeline: 150 frames @ 60 FPS (2.50s cycle)
DURATION = 150
STEP = 2

# Reference rest lengths for articulated upper arm & forearm
UPPER_ARM_LEN = 52.0
FOREARM_LEN = 28.0

# Thoracolumbar pivot & stationary waist anchor at shorts waistband
THORACIC_PIVOT = (284.0, 272.0)
CORE_WAIST_ANCHOR = (334.0, 264.0)


def cubic_bezier(x1, y1, x2, y2):
    def bez(t, a, b):
        return 3 * a * t * (1 - t) ** 2 + 3 * b * t * t * (1 - t) + t ** 3

    def ease(x):
        if x <= 0.0:
            return 0.0
        if x >= 1.0:
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if bez(mid, x1, x2) < x:
                lo = mid
            else:
                hi = mid
        return bez((lo + hi) / 2, y1, y2)

    return ease


EASE_CONCENTRIC = cubic_bezier(0.36, 0.0, 0.24, 1.0)
EASE_ECCENTRIC = cubic_bezier(0.38, 0.0, 0.34, 1.0)


def crunch_progress(frame):
    """Returns thoracic crunch progress r in [0.0, 1.0] across 150 frames:
    - 0..12: Bottom supine stretch hold (r = 0.0)
    - 12..62: Concentric abdominal crunch upward (r: 0.0 -> 1.0)
    - 62..80: Peak isometric abdominal contraction hold at top (r = 1.0)
    - 80..138: Controlled eccentric lowering back to supine (r: 1.0 -> 0.0)
    - 138..150: Bottom supine hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 62:
        return EASE_CONCENTRIC((fr - 12) / 50.0)
    if fr <= 80:
        return 1.0
    if fr <= 138:
        return 1.0 - EASE_ECCENTRIC((fr - 80) / 58.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def quad_interp_pt(p0, p_mid, p1, r):
    """Smooth quadratic Lagrange interpolation through p0 (r=0), p_mid (r=0.5), and p1 (r=1.0)."""
    l0 = (1.0 - r) * (1.0 - 2.0 * r)
    l1 = 4.0 * r * (1.0 - r)
    l2 = r * (2.0 * r - 1.0)
    return (
        l0 * p0[0] + l1 * p_mid[0] + l2 * p1[0],
        l0 * p0[1] + l1 * p_mid[1] + l2 * p1[1],
    )


def pose(r):
    """Compute supine Abdominal Crunch kinematics at progress r in [0.0, 1.0]."""
    # 1. Pivoting Thoracic Ribcage, Pectorals & Head (lower lumbar back stays anchored on the mat!)
    #    In screen space (+X right, +Y down), rotating a point on the left (dx < 0) upward (-Y)
    #    and rightward (+X) is a positive (clockwise) rotation angle.
    thoracic_x = THORACIC_PIVOT[0] + lerp(0.0, 6.0, r)
    thoracic_y = THORACIC_PIVOT[1] + lerp(0.0, -3.0, r)
    thoracic_rot = math.radians(lerp(0.0, 34.0, r))

    # 2. Additional cervical/head forward flexion as the upper torso curls up
    neck_rot = math.radians(lerp(0.0, 10.0, r))

    # 3. Dynamically Compressing & Thickening Abdominal & Oblique Core Group
    #    Anchored at CORE_WAIST_ANCHOR = (334.0, 264.0) (flush against the stationary shorts waistband):
    #    - Horizontally shortens (scaleX: 1.00 -> 0.72) as the ribcage curls toward the pelvis
    #    - Vertically thickens (scaleY: 1.00 -> 1.08) as the 6-pack blocks bunch up
    #    - Rotates upward (+9.0 deg) so the left costal edge tracks the rising Pectoralis Major seamlessly
    core_sx = lerp(1.00, 0.72, r)
    core_sy = lerp(1.00, 1.08, r)
    core_rot = math.radians(lerp(0.0, 9.0, r))

    # 4. Articulated Hands-Behind-Head Arms (Near Right Arm + Far Left Arm)
    #    - At r = 0.0 (Top panel of reference):
    #      Near upper arm & elbow lie horizontally along the side of the head/neck on the mat:
    #        sh_near = (210.0, 268.0), elb_near = (158.0, 274.0), hand_near = (152.0, 264.0)
    #    - At r = 1.0 (Bottom panel of reference):
    #      Shoulder lifts with the ribcage, elbow curls high up-left above the shoulder, and the
    #      forearm reaches back-left to the white/skin hand cupping the back of the dark hair cap,
    #      leaving the nose & chin profile cleanly visible to the right of the upper arm:
    #        sh_near = (220.0, 218.0), elb_near = (196.0, 162.0), hand_near = (178.0, 184.0)
    sh_near = quad_interp_pt((210.0, 268.0), (212.0, 242.0), (220.0, 218.0), r)
    elb_near = quad_interp_pt((158.0, 274.0), (170.0, 214.0), (196.0, 162.0), r)
    hand_near = quad_interp_pt((152.0, 264.0), (160.0, 222.0), (178.0, 184.0), r)

    sh_far = quad_interp_pt((216.0, 256.0), (218.0, 232.0), (226.0, 208.0), r)
    elb_far = quad_interp_pt((168.0, 254.0), (182.0, 198.0), (208.0, 154.0), r)
    hand_far = quad_interp_pt((158.0, 252.0), (166.0, 212.0), (184.0, 174.0), r)

    def seg_xform(p0, p1, base_len):
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        ang = math.atan2(dy, dx)
        if ang < 0:
            ang += 2.0 * math.pi
        sc = max(0.32, math.hypot(dx, dy) / base_len)
        return ang, sc

    ua_near_ang, ua_near_sc = seg_xform(sh_near, elb_near, UPPER_ARM_LEN)
    fa_near_ang, fa_near_sc = seg_xform(elb_near, hand_near, FOREARM_LEN)
    ua_far_ang, ua_far_sc = seg_xform(sh_far, elb_far, UPPER_ARM_LEN)
    fa_far_ang, fa_far_sc = seg_xform(elb_far, hand_far, FOREARM_LEN)

    # 5. Dynamic contact shadow on the exercise mat (condenses rightward as upper back lifts off mat)
    shadow_x = lerp(334.0, 358.0, r)
    shadow_sx = lerp(1.24, 1.06, r)

    return {
        "r": r,
        "thoracic_x": thoracic_x,
        "thoracic_y": thoracic_y,
        "thoracic_rot": thoracic_rot,
        "neck_rot": neck_rot,
        "core_sx": core_sx,
        "core_sy": core_sy,
        "core_rot": core_rot,
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
        "shadow_x": shadow_x,
        "shadow_sx": shadow_sx,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(crunch_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = (
    "thoracic_rot",
    "neck_rot",
    "core_rot",
    "ua_near_ang",
    "fa_near_ang",
    "ua_far_ang",
    "fa_far_ang",
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

if __name__ == "__main__":
    for _fr in (0, 36, 69, 110, DURATION):
        _p = POSES[_fr if _fr in POSES else min(POSES.keys(), key=lambda k: abs(k - _fr))]
        print(
            f"f{_fr:3d} r={_p['r']:.3f} th_rot={math.degrees(_p['thoracic_rot']):+.1f} "
            f"core_sx={_p['core_sx']:.2f} elb_near=({_p['elb_near'][0]:.1f},{_p['elb_near'][1]:.1f}) "
            f"hand_near=({_p['hand_near'][0]:.1f},{_p['hand_near'][1]:.1f})"
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
    """Catmull-Rom spline through pts, emitted as CubicMirroredVertex elements."""
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


def stroke_shape(indent, name, pts, width, color, feather=0.0, cap="round", cid=None):
    idattr = f' id="{cid}"' if cid else ""
    f_xml = f'<Feather strength="{f(float(feather))}" name="{name}Feather"/>' if feather > 0 else ""
    return (
        f'{indent}<Shape name="{name}">\n'
        f'{indent}    <PointsPath isClosed="false" name="{name}Path">\n'
        f"{smooth_vertices(pts, False, indent + '        ')}\n"
        f"{indent}    </PointsPath>\n"
        f'{indent}    <Stroke thickness="{f(float(width))}" cap="{cap}" join="round" name="{name}Stroke">'
        f'<SolidColor colorValue="{color}" name="{name}Color"{idattr}/>{f_xml}</Stroke>\n'
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


# ---------------------------------------------------------------- Palette & Muscle Activation
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF334155", "FF1E293B", "FF0F172A")
SHORTS_FAR = ("FF1E293B", "FF111827", "FF090D16")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
ANATOMY_LINE = "520F172A"

# Muscle activation colors: warm orange (#FFF97316) at bottom stretch -> intense coral-crimson (#FFF43F5E) at peak crunch
MUSCLE_LOW = (0xEC, 0xF9, 0x73, 0x16)
MUSCLE_HIGH = (0xFF, 0xF4, 0x3F, 0x5E)
MUSCLE_LINE_LOW = (0x80, 0x9A, 0x34, 0x12)
MUSCLE_LINE_HIGH = (0xE6, 0x88, 0x13, 0x37)


def argb_lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return "".join(f"{round(lerp(x, y, t)):02X}" for x, y in zip(a, b))


def skin_fill(name, y0, y1, tones, x0=0, x1=0):
    return f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *tones, x0=x0, x1=x1)}</Fill>'


def skin_fill_outlined(name, y0, y1, tones, x0=0, x1=0, line=1.0, stroke_col="400F172A"):
    return (
        f'<Fill name="{name}Fill">{grad3(name + "Grad", y0, y1, *tones, x0=x0, x1=x1)}</Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{stroke_col}" name="{name}EdgeCol"/></Stroke>'
    )


keys = []  # (objectId, propertyKey, kind, [(frame, value)])


def key_double(obj, prop, fn):
    keys.append((obj, prop, "double", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def key_color(obj, prop, fn):
    keys.append((obj, prop, "color", [(fr, fn(POSES[fr])) for fr in FRAMES]))


def muscle_t(p):
    """Core muscle activation intensity in [0.28, 1.0]: warm orange baseline at supine stretch -> glowing crimson at top crunch."""
    return 0.28 + 0.72 * (p["r"] ** 0.85)


muscle_fill_ids = []  # (cid, scale)
muscle_line_ids = []  # (cid, scale)


def muscle_paint(name, scale=1.0, line=1.1):
    fid, lid = nid(), nid()
    muscle_fill_ids.append((fid, scale))
    muscle_line_ids.append((lid, scale))
    t0 = muscle_t(POSES[0]) * scale
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- Anatomy & Rig Builders
def stationary_legs_and_pelvis():
    """Stationary bent knees (~85 deg flexion), bare feet planted on FLOOR=300, and navy compression shorts."""
    ind = "        "
    i2 = ind + "    "

    # --- 1. Far (Left) Leg in 3/4 background depth (slightly up-left of Near Leg) ---
    far_foot_pts = [
        (472, 276), (488, 272), (508, 280), (524, 283), (528, 286),
        (526, 291), (504, 291), (482, 291), (470, 289), (469, 282),
    ]
    far_shin_pts = [
        (416, 168), (430, 164), (442, 174), (456, 206), (472, 246),
        (486, 274), (472, 278), (456, 256), (438, 232), (426, 202), (414, 182),
    ]
    far_thigh_pts = [
        (354, 244), (382, 204), (408, 172), (424, 162), (436, 168),
        (430, 188), (408, 218), (382, 254),
    ]
    far_shorts_pts = [
        (328, 238), (362, 214), (396, 184), (416, 208),
        (386, 252), (356, 282), (328, 278),
    ]

    # --- 2. Near (Right) Foreground Leg & Pelvis (matching the 2-panel reference silhouette) ---
    # Bare right foot planted flat on the floor mat (x = 480..538, y = 274..294)
    near_foot_pts = [
        (484, 276),  # posterior Achilles / ankle heel entry
        (498, 272),  # anterior ankle instep
        (514, 280),  # dorsal midfoot arch
        (528, 284),  # forefoot / metatarsal bridge
        (537, 284),  # upturned big toe tip (matching reference!)
        (539, 289),  # distal toe pad
        (535, 293),  # ball of foot
        (514, 293),  # plantar midfoot arch
        (490, 294),  # plantar heel pad on mat
        (481, 290),  # rounded back of heel
        (481, 282),  # posterior calcaneus
    ]
    # Sculpted lower leg (Tibialis Anterior front curve + Gastrocnemius/Soleus posterior calf curve)
    near_shin_pts = [
        (426, 172),  # superior patella / knee top
        (440, 166),  # rounded knee cap apex
        (452, 176),  # tibial tuberosity below knee
        (466, 206),  # anterior Tibialis Anterior belly
        (480, 244),  # lower anterior shin
        (498, 274),  # anterior ankle joint
        (484, 278),  # posterior Achilles tendon at ankle
        (472, 262),  # lower Soleus taper
        (452, 236),  # prominent Gastrocnemius calf belly
        (440, 202),  # popliteal hollow behind knee
        (428, 188),  # upper knee joint
    ]
    # Exposed distal quadriceps & knee (from mid-thigh shorts hem up to the bent knee)
    near_thigh_pts = [
        (394, 200),  # anterior thigh under shorts hem
        (414, 176),  # distal Rectus Femoris / Vastus Lateralis
        (430, 166),  # superior patellar curve
        (444, 170),  # knee patella front
        (440, 198),  # posterior popliteal knee crease
        (424, 224),  # posterior hamstring under shorts hem
        (402, 234),  # inner thigh base
    ]
    # Dark navy/slate compression shorts covering pelvis, glutes on mat, and upper half of right thigh
    near_shorts_pts = [
        (332, 240),  # anterior waistband top at iliac crest
        (356, 234),  # upper hip / inguinal crease
        (384, 206),  # mid-anterior thigh shorts contour
        (408, 186),  # anterior-top corner of diagonal thigh hem
        (432, 214),  # posterior-bottom corner of diagonal thigh hem
        (412, 244),  # posterior mid-thigh hamstring contour
        (396, 276),  # lower glute / posterior thigh curve
        (376, 293),  # gluteus maximus resting on the mat
        (348, 294),  # lower sacral/glute contact on mat
        (330, 291),  # lower waistband at lumbar junction
        (332, 266),  # mid waistband
    ]

    return (
        "\n".join([
            f'{ind}<Node name="FarLegGroup">',
            smooth_shape(i2, "FarFoot", far_foot_pts, skin_fill_outlined("FarFoot", 272, 292, SKIN_FAR)),
            smooth_shape(i2, "FarShin", far_shin_pts, skin_fill_outlined("FarShin", 164, 278, SKIN_FAR)),
            smooth_shape(i2, "FarThigh", far_thigh_pts, skin_fill_outlined("FarThigh", 162, 254, SKIN_FAR)),
            smooth_shape(i2, "FarShorts", far_shorts_pts, skin_fill("FarShorts", 184, 284, SHORTS_FAR)),
            f"{ind}</Node>",
        ]),
        "\n".join([
            f'{ind}<Node name="NearLegAndPelvisGroup">',
            # 1. Bare Right Foot + Ankle Malleolus Crease (matching reference ankle hook line)
            stroke_shape(i2, "AnkleMalleolus", [(491, 271), (492, 278), (497, 281)], 1.4, ANATOMY_LINE, 0.0),
            stroke_shape(i2, "FootHi", [(498, 276), (516, 283), (533, 286)], 2.2, HIGHLIGHT, 2.5),
            smooth_shape(i2, "NearFoot", near_foot_pts, skin_fill_outlined("NearFoot", 272, 294, SKIN, line=1.2)),
            # 2. Sculpted Right Shin & Calf + Internal Tibial/Calf Definition Lines (matching reference)
            stroke_shape(i2, "TibialLine", [(454, 206), (462, 230), (470, 256)], 1.4, ANATOMY_LINE, 0.0),
            stroke_shape(i2, "PoplitealHook", [(444, 188), (439, 198), (446, 216)], 1.5, ANATOMY_LINE, 0.0),
            stroke_shape(i2, "ShinHi", [(446, 178), (464, 210), (482, 252)], 3.0, HIGHLIGHT, 3.0),
            stroke_shape(i2, "CalfSh", [(444, 208), (456, 238), (478, 268)], 4.0, CORE_SHADOW, 4.0),
            smooth_shape(i2, "NearShin", near_shin_pts, skin_fill_outlined("NearShin", 166, 278, SKIN, line=1.2)),
            # 3. Distal Quadriceps & Knee Patella + Vastus Medialis Crease Line (matching reference)
            stroke_shape(i2, "QuadCrease", [(404, 204), (414, 190), (424, 180)], 1.4, ANATOMY_LINE, 0.0),
            stroke_shape(i2, "HamstringCrease", [(424, 218), (430, 204)], 1.4, ANATOMY_LINE, 0.0),
            stroke_shape(i2, "KneeHi", [(406, 188), (424, 172), (440, 172)], 3.2, HIGHLIGHT, 3.0),
            smooth_shape(i2, "NearThigh", near_thigh_pts, skin_fill_outlined("NearThigh", 166, 230, SKIN, line=1.2)),
            # 4. Navy/Slate Compression Shorts + Hip/Thigh Seam Creases
            stroke_shape(i2, "ShortsHipSeam", [(346, 242), (374, 218), (402, 194)], 1.4, "80090D16", 0.5),
            stroke_shape(i2, "ShortsGluteFold", [(392, 266), (402, 236), (414, 214)], 1.5, "80090D16", 0.5),
            stroke_shape(i2, "ShortsHi", [(354, 238), (382, 214), (406, 194)], 2.8, "33FFFFFF", 3.0),
            smooth_shape(i2, "NearShorts", near_shorts_pts, skin_fill_outlined("NearShorts", 186, 294, SHORTS, line=1.2, stroke_col="80090D16")),
            f"{ind}</Node>",
        ]),
    )


def arm_rig(prefix, far):
    """Articulated Hands-Behind-Head Arm (UpperArm: shoulder -> elbow, Forearm: elbow -> hand cupping head)."""
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

    # Upper arm local frame: +X runs from Shoulder (0,0) -> Elbow (UPPER_ARM_LEN=52, 0)
    ua_pts = [
        (-10, 0), (-7, -9.2), (8, -11.0), (26, -10.2), (42, -8.2), (50, -5.8),
        (55, 0), (50, 6.2), (38, 9.5), (22, 11.2), (6, 10.5), (-7, 8.2),
    ]
    delt_pts = [
        (-13, 0), (-9, -11.0), (4, -12.8), (17, -9.2), (21, 0),
        (16, 9.2), (4, 11.8), (-9, 9.0),
    ]
    # Forearm local frame: +X runs from Elbow (0,0) -> Hand cupping cranium (FOREARM_LEN=28, 0)
    fa_pts = [
        (-6, 0), (-4, -7.2), (6, -8.6), (17, -7.2), (26, -5.2),
        (31, 0), (26, 5.2), (16, 7.2), (5, 7.8), (-4, 6.2),
    ]
    # Sculpted hand cupping the back of the head/hair (matching the bottom panel of the reference image!)
    hand_pts = [
        (-4, -6.2), (4, -7.5), (11, -5.2), (13, 0.0), (10, 5.8), (3, 7.0), (-4, 5.5),
    ]

    out = [f'{ind}<Node name="{prefix}ArmGroup">']

    # Upper Arm + Deltoid drawn in front of Forearm so the raised elbow & triceps/biceps read cleanly
    out.append(
        f'{i2}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" '
        f'rotation="{f(p0[ua_ang_key])}" scaleX="{f(p0[ua_sc_key])}" name="{prefix}UpperArm" id="{ua_id}">'
    )
    if not far:
        out.append(stroke_shape(i3, f"{prefix}DeltCrease", [(4, -8.5), (14, -4.5), (18, 3.0)], 1.3, ANATOMY_LINE, 0.0))
        out.append(stroke_shape(i3, f"{prefix}BicepsCrease", [(16, -6.8), (32, -6.2), (44, -3.5)], 1.3, ANATOMY_LINE, 0.0))
        out.append(stroke_shape(i3, f"{prefix}UpperArmHi", [(6, -6.8), (24, -6.5), (40, -4.8)], 2.8, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i3, f"{prefix}Deltoid", delt_pts, skin_fill_outlined(prefix + "Deltoid", -12, 12, skin, line=1.1)))
    out.append(stroke_shape(i3, f"{prefix}UpperArmSh", [(8, 6.8), (26, 7.2), (42, 5.2)], 4.0, CORE_SHADOW, 4.0))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill_outlined(prefix + "UpperArm", -11, 11, skin, line=1.2)))
    out.append(f"{i2}</Node>")

    # Forearm + Hand cupping the back of the dark hair cap
    out.append(
        f'{i2}<Node x="{f(p0[elb_key][0])}" y="{f(p0[elb_key][1])}" '
        f'rotation="{f(p0[fa_ang_key])}" scaleX="{f(p0[fa_sc_key])}" name="{prefix}Forearm" id="{fa_id}">'
    )
    if not far:
        out.append(stroke_shape(i3, f"{prefix}HandKnuckle", [(24, -3.5), (27, 0.0), (24, 3.8)], 1.2, ANATOMY_LINE, 0.0))
    out.append(smooth_shape(i3, f"{prefix}Hand", hand_pts, skin_fill_outlined(prefix + "Hand", -7, 7, skin, line=1.2), x=FOREARM_LEN - 5.0))
    if not far:
        out.append(stroke_shape(i3, f"{prefix}ForearmHi", [(4, -4.8), (15, -4.2), (24, -2.8)], 2.4, HIGHLIGHT, 2.5))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(4, 4.8), (15, 4.2), (24, 2.8)], 3.4, CORE_SHADOW, 3.5))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill_outlined(prefix + "Forearm", -8, 8, skin, line=1.2)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def torso_core_and_head_rig():
    """Stationary Lumbar Base, Pivoting Thoracic Ribcage/Pectorals/Head, and Compressing Rectus Abdominis + Oblique Core."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    i4 = i3 + "    "

    th_id, neck_id, core_id = nid(), nid(), nid()
    key_double(th_id, 13, lambda p: p["thoracic_x"])
    key_double(th_id, 14, lambda p: p["thoracic_y"])
    key_double(th_id, 15, lambda p: p["thoracic_rot"])

    key_double(neck_id, 15, lambda p: p["neck_rot"])

    key_double(core_id, 15, lambda p: p["core_rot"])
    key_double(core_id, 16, lambda p: p["core_sx"])
    key_double(core_id, 17, lambda p: p["core_sy"])

    p0 = POSES[0]

    # --- A. Stationary Lumbar & Waist Base (remains pressed into the mat at x = 284..338, y = 240..294) ---
    # Left cap stays at x >= 278 so when ThoracicTorso lifts at r = 1.0, the dorsal back forms a single unbroken curve!
    lumbar_base_pts = [
        (278, 246),  # mid-abdominal bridge inside ThoracicTorso & CoreMuscleGroup
        (306, 240),  # anterior lower waist under Rectus Abdominis
        (335, 241),  # front waist meeting shorts waistband top
        (336, 266),  # mid waist inside shorts waistband
        (333, 291),  # lower sacral/lumbar edge at shorts waistband bottom
        (308, 293),  # lower lumbar back pressed flat on the mat!
        (286, 293),  # thoracolumbar tangent point on the mat!
        (278, 274),  # smooth inner pivot transition inside THORACIC_PIVOT (284, 272)
    ]

    # --- B. Dynamically Compressing & Thickening Core Muscle Group (origin at CORE_WAIST_ANCHOR = (334, 264)) ---
    # Extending leftward from x = 0 (at shorts waistband x=334) to x = -84 (at Pectoralis Major costal border x=250):
    # 1. Broad External & Internal Oblique lateral abdominal plate (scale = 0.92, matching the coral/red fan in reference)
    ext_oblique_pts = [
        (-80, -11),  # upper-left attachment under the 5th-8th ribs / Pectoralis Major
        (-54, -12),  # upper border along the sub-rectus linea semilunaris
        (-28, -11),  # mid-upper border below Rectus Abdominis
        (-4, -10),   # anterior-superior border near shorts waistband
        (-3, 4),     # posterior-right edge parallel to shorts waistband
        (-15, 21),   # iliac crest / inguinal border at bottom of waist
        (-34, 22),   # lower-middle aponeurosis border
        (-52, 6),    # diagonal lower-left flank border (matching the curved flank arch in reference!)
        (-68, -4),   # upper-left serratus/oblique taper
    ]
    # 2. Sculpted Rectus Abdominis 6-Pack Blocks along the top/anterior profile (scale = 1.00)
    #    4 foreground (near right) segments + 3 background (far left) segments peeking along the top contour
    rectus_near_blocks = [
        [(-82, -23), (-64, -24), (-62, -13), (-78, -12)],  # Upper-most infrasternal segment (under PecMajor)
        [(-62, -24), (-43, -24), (-42, -12), (-60, -13)],  # Upper-middle supraumbilical segment
        [(-41, -24), (-22, -23), (-22, -11), (-40, -12)],  # Lower-middle umbilical segment
        [(-20, -23), (-3, -21), (-4, -10), (-20, -11)],    # Lower infraumbilical segment at shorts waistband
    ]
    rectus_far_blocks = [
        [(-80, -27), (-63, -28), (-64, -23), (-81, -22)],
        [(-61, -28), (-43, -28), (-43, -23), (-61, -23)],
        [(-41, -28), (-23, -27), (-23, -22), (-41, -23)],
    ]
    # White/skin aponeurosis flank crease lines flanking the External Oblique (matching the dark curved lines in reference)
    oblique_left_crease = [(-74, -2), (-54, 7), (-37, 22)]
    oblique_right_crease = [(-13, 21), (-7, 10), (-2, 1)]

    # --- C. Pivoting Thoracic Ribcage, Pectoralis Major & Head (origin at THORACIC_PIVOT = (284, 272)) ---
    # Local frame: (0,0) = (284, 272).
    # At r = 0.0 (rot = 0 deg):
    #   x = -80 is at world x = 204 (neck/clavicles), x = +20 is at world x = 304 (blending into LumbarBase)
    #   y = -36 is at world y = 236 (chest top), y = +21 is at world y = 293 (upper back on mat)
    thoracic_torso_pts = [
        (-82, -16),  # anterior neck/clavicle entry
        (-68, -32),  # upper sternum / clavicular pec dome
        (-44, -36),  # mid Pectoralis Major dome
        (-24, -29),  # lower costal arch / xiphoid process
        (6, -26),    # upper abdominal transition into LumbarBase
        (20, -4),    # rounded right pivot cap (stays inside LumbarBase throughout 0..34 deg curl!)
        (14, 18),    # thoracolumbar dorsal tangent at world (290, 292) at r=1.0
        (-10, 21),   # lower-thoracic dorsal spine
        (-44, 21),   # mid/upper-thoracic scapular back
        (-74, 17),   # posterior shoulder / trapezius base
        (-86, 2),    # base of posterior neck
    ]
    # Sculpted Pectoralis Major chest plate (matching the rounded chest contour in both panels of reference)
    pec_pts = [
        (-74, -18),  # clavicular/deltopectoral origin
        (-62, -33),  # superior pectoral curve
        (-40, -35),  # anterior pectoral belly
        (-25, -27),  # medial sternocostal border
        (-26, -14),  # lower-right costal border (where Rectus Abdominis & Oblique attach!)
        (-42, -9),   # inframammary / lower pectoral fold
        (-64, -8),   # lateral pectoral border toward armpit/deltoid
    ]
    pec_paint = (
        f'<Fill name="PecFill">{grad3("PecGrad", -35, -8, "FFF8FAFC", "FFDCE4EE", "FFA3B1C4")}</Fill>'
        '<Stroke thickness="1.3" join="round" name="PecStroke"><SolidColor colorValue="590F172A" name="PecStrokeCol"/></Stroke>'
    )

    # --- D. Head, Neck & Dark Navy Hair Cap (child of ThoracicGroup at x = -80, y = -6) ---
    # Local frame at r = 0.0 (world origin = (204, 266)):
    # Face profile looks UPWARD (-Y) at r = 0.0 and curls UP-RIGHT (-Y, +X) at r = 1.0!
    neck_pts = [
        (4, -10), (14, -12), (16, 12), (-8, 12), (-12, -8),
    ]
    head_pts = [
        (-4, -14),   # base of anterior neck / throat
        (-12, -24),  # strong chin tip (pointing up at ceiling at r=0, up-right at r=1!)
        (-20, -22),  # lower & upper lips
        (-28, -22),  # nose bridge
        (-34, -26),  # sculpted nose tip (projecting upward!)
        (-42, -21),  # brow ridge / glabella
        (-52, -19),  # forehead sloping back toward hairline
        (-62, -10),  # crown / anterior hairline
        (-66, 4),    # posterior parietal cranium
        (-56, 18),   # occiput (back of skull resting on mat at r=0)
        (-36, 20),   # lower occiput / nuchal line
        (-16, 14),   # posterior neck base
    ]
    # Sculpted dark navy/slate Hair Cap wrapping the crown and back/bottom of the cranium (matching reference!)
    hair_pts = [
        (-50, -20),  # front hairline peak above forehead
        (-63, -14),  # upper crown hair volume
        (-72, -1),   # rounded posterior crown of hair cap
        (-69, 14),   # back of hair cap
        (-54, 23),   # lower occipital hair curve (resting on mat at r=0)
        (-34, 22),   # nape of neck hair border
        (-26, 15),   # temple/ear hairline sideburn
        (-38, 8),    # inner hairline around ear
        (-46, -4),   # mid temple hairline
    ]
    hair_paint = (
        f'<Fill name="HairFill">{grad("HairGrad", -70, -14, -30, 22, "FF1E293B", "FF0F172A")}</Fill>'
        '<Stroke thickness="1.2" join="round" name="HairStroke"><SolidColor colorValue="FF090D16" name="HairStrokeCol"/></Stroke>'
    )

    out = [f'{ind}<Node name="TorsoAndHeadRoot">']

    # 1. Dynamically Compressing & Thickening Core Muscle Group (drawn on top of torso skin so Rectus & Obliques pop cleanly!)
    out.append(
        f'{i2}<Node x="{f(CORE_WAIST_ANCHOR[0])}" y="{f(CORE_WAIST_ANCHOR[1])}" '
        f'rotation="{f(p0["core_rot"])}" scaleX="{f(p0["core_sx"])}" scaleY="{f(p0["core_sy"])}" '
        f'name="CoreMuscleGroup" id="{core_id}">'
    )
    # Tendinous intersections & linea alba creases over Rectus Abdominis
    out.append(stroke_shape(i3, "LineaAlba", [(-80, -23), (-42, -23), (-4, -21)], 1.2, "80881337", 0.4))
    for idx, pts in enumerate(rectus_near_blocks):
        out.append(smooth_shape(i3, f"RectusNear{idx + 1}", pts, muscle_paint(f"RectusNear{idx + 1}", scale=1.00, line=1.2)))
    for idx, pts in enumerate(rectus_far_blocks):
        out.append(smooth_shape(i3, f"RectusFar{idx + 1}", pts, muscle_paint(f"RectusFar{idx + 1}", scale=0.96, line=1.0)))
    # External & Internal Oblique lateral abdominal plate + diagonal fiber slips + flanking aponeurosis creases
    out.append(stroke_shape(i3, "ObliqueSlip1", [(-68, -6), (-48, 0), (-26, 4)], 1.1, "66881337", 0.5))
    out.append(stroke_shape(i3, "ObliqueSlip2", [(-54, -8), (-34, -1), (-14, 5)], 1.1, "66881337", 0.5))
    out.append(smooth_shape(i3, "ExternalOblique", ext_oblique_pts, muscle_paint("ExternalOblique", scale=0.92, line=1.15)))
    out.append(stroke_shape(i3, "ObliqueLeftCrease", oblique_left_crease, 1.5, ANATOMY_LINE, 0.0))
    out.append(stroke_shape(i3, "ObliqueRightCrease", oblique_right_crease, 1.4, ANATOMY_LINE, 0.0))
    out.append(f"{i2}</Node>")

    # 2. Pivoting Thoracic Ribcage, Pectoralis Major & Head/Neck
    out.append(
        f'{i2}<Node x="{f(p0["thoracic_x"])}" y="{f(p0["thoracic_y"])}" '
        f'rotation="{f(p0["thoracic_rot"])}" name="ThoracicGroup" id="{th_id}">'
    )
    # Sculpted Pectoralis Major & Serratus/Latissimus border
    out.append(stroke_shape(i3, "PecHi", [(-62, -28), (-42, -30), (-28, -22)], 2.8, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i3, "PecMajor", pec_pts, pec_paint))
    out.append(stroke_shape(i3, "LatCrease", [(-58, 2), (-38, 0), (-22, 6)], 1.4, ANATOMY_LINE, 0.0))

    # Head, Face Profile & Dark Navy Hair Cap
    out.append(f'{i3}<Node x="-80" y="-6" rotation="{f(p0["neck_rot"])}" name="HeadAndNeck" id="{neck_id}">')
    out.append(smooth_shape(i4, "HairCap", hair_pts, hair_paint))
    out.append(stroke_shape(i4, "EyeBrow", [(-43, -18), (-39, -15)], 1.4, "730F172A", 0.3))
    out.append(stroke_shape(i4, "JawLine", [(-13, -20), (-16, -8), (-24, 2)], 1.6, CORE_SHADOW, 1.5))
    out.append(stroke_shape(i4, "HeadHi", [(-52, -16), (-36, -21), (-16, -20)], 2.6, HIGHLIGHT, 2.5))
    out.append(smooth_shape(i4, "HeadShape", head_pts, skin_fill_outlined("Head", -26, 20, SKIN, line=1.2)))
    out.append(smooth_shape(i4, "NeckShape", neck_pts, skin_fill("Neck", -12, 12, SKIN)))
    out.append(f"{i3}</Node>")

    # Thoracic Torso Silhouette
    out.append(stroke_shape(i3, "ThoracicBackStroke", [(-74, 17), (-44, 21), (-10, 21), (14, 18)], 1.3, "4D0F172A", 0.0))
    out.append(stroke_shape(i3, "ThoracicSh", [(-68, 13), (-38, 16), (-6, 16)], 5.0, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i3, "ThoracicTorso", thoracic_torso_pts, skin_fill("ThoracicTorso", -34, 21, SKIN)))
    out.append(f"{i2}</Node>")

    # 3. Stationary Lumbar & Lower Waist Base (pressed flat against the mat at y = 293)
    out.append(stroke_shape(i2, "LumbarBackStroke", [(286, 293), (308, 293), (332, 291)], 1.3, "4D0F172A", 0.0))
    out.append(stroke_shape(i2, "LumbarSh", [(286, 288), (308, 289), (330, 287)], 4.8, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i2, "LumbarBase", lumbar_base_pts, skin_fill("LumbarBase", 240, 293, SKIN)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def exercise_mat_and_shadow():
    """Beveled dark exercise mat on FLOOR=300 plus dynamic contact shadow matching the reference oval shadow."""
    ind = "        "
    i2 = ind + "    "
    mat_top = f'<Fill name="MatTopFill">{grad("MatTopGrad", 104, 286, 556, 298, "FF334155", "FF1E293B")}</Fill>'
    mat_edge = f'<Fill name="MatEdgeFill">{grad("MatEdgeGrad", 104, 296, 556, 301, "FF475569", "FF0F172A")}</Fill>'

    sh_id = nid()
    key_double(sh_id, 13, lambda p: p["shadow_x"])
    key_double(sh_id, 16, lambda p: p["shadow_sx"])
    p0 = POSES[0]

    return "\n".join([
        f'{ind}<Node name="ExerciseMat">',
        # Contact shadow of supine athlete on the mat surface
        f'{i2}<Shape x="{f(p0["shadow_x"])}" y="293" scaleX="{f(p0["shadow_sx"])}" scaleY="0.062" name="MatContactShadow" id="{sh_id}">\n'
        f'{i2}    <Ellipse width="330" height="220" name="MatContactEllipse"/>\n'
        f'{i2}    <Fill name="MatContactFill"><RadialGradient startX="0" startY="0" endX="165" endY="0" name="MatContactGrad">'
        f'<GradientStop colorValue="CC000000" position="0"/><GradientStop colorValue="66000000" position="0.65"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{i2}</Shape>",
        # 3/4 perspective exercise mat top & front bevel
        stroke_shape(i2, "MatTopHi", [(108, 295.5), (330, 295.5), (552, 295.5)], 1.2, "40FFFFFF", 0.5, cap="butt"),
        poly_shape(i2, "MatTop", [(118, 286), (542, 286), (558, 296), (102, 296)], mat_top, radius=3.0),
        poly_shape(i2, "MatFrontEdge", [(102, 295), (558, 295), (558, 300), (102, 300)], mat_edge, radius=1.5),
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


far_leg_xml, near_leg_xml = stationary_legs_and_pelvis()
near_arm_xml = arm_rig("Near", False)
torso_core_head_xml = torso_core_and_head_rig()
mat_xml = exercise_mat_and_shadow()

for cid, sc in muscle_fill_ids:
    key_color(cid, 37, (lambda s: lambda p: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, muscle_t(p) * s))(sc))
for cid, sc in muscle_line_ids:
    key_color(cid, 37, (lambda s: lambda p: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, muscle_t(p) * s))(sc))


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
    <!-- Abdominal Crunch: supine side/3-4 profile, 60 fps, 16:9 (640x360), generated by gen_crunch.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="Crunch" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- 1. Foreground Near (Right) Arm cradling back of head & lifting elbow during crunch -->
{near_arm_xml}

        <!-- 2. Foreground Near (Right) Bent Leg, Planted Bare Foot & Compression Shorts -->
{near_leg_xml}

        <!-- 3. Stationary Lumbar Base, Pivoting Thoracic Ribcage/Pectorals/Head & Compressing Rectus Abdominis + Oblique Core -->
{torso_core_head_xml}

        <!-- 4. Background Far (Left) Bent Leg in 3/4 depth -->
{far_leg_xml}

        <!-- 5. Beveled Exercise Mat & Dynamic Contact Shadow -->
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

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="Crunch" id="0:60">
{keyed_xml()}
        </LinearAnimation>
    </Artboard>
</Rive>
"""

OUT.write_text(rml)
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
    """Build the .riv, copy it into the Flutter assets, and render the catalog thumbnail."""
    built = HERE / "build/crunch.riv"
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
