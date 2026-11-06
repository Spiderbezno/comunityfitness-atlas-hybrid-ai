#!/usr/bin/env python3
"""Generate bicep_curl_barbell.rml — 3/4 front-left Barbell Bicep Curl at 60fps (16:9 640x360).

Matches the ab_wheel_rollout / bench_dips / bench_press visual standard:
- Same character palette (`SKIN`, `SKIN_FAR`, `SHORTS`, `HIGHLIGHT`, `CORE_SHADOW`,
  `MUSCLE_LOW` -> `MUSCLE_HIGH`), Catmull-Rom smooth curves, and 16:9 (`640x360`,
  `FLOOR = 300.0`) artboard.
- Standing 3/4 front-left view matching the reference illustration:
  - Feet planted shoulder-width apart in 3/4 perspective, defined quadriceps and
    gastrocnemius calves, compression shorts, sculpted 6-pack abs and obliques,
    pectorals, deltoids, and volumetric 3/4 head facing front-left.
  - Olympic barbell held with a supinated (underhand) shoulder-width grip, curling
    in a smooth circular sagittal arc from the upper thighs (`curl_t = 0.0`) up to
    clavicle/upper-chest height (`curl_t = 1.0`) while the elbows stay anchored at
    the sides of the ribcage.
  - Glowing orange-to-red muscle activation (`muscle_t` peaking at `1.0` at top
    concentric contraction) and dynamic biceps peak bulge on:
      * Biceps brachii — short head (inner/medial anterior upper arm)
      * Biceps brachii — long head (outer/lateral anterior upper arm)
      * Brachialis (distal lateral upper arm between biceps and triceps)
      * Brachioradialis (proximal radial/anterior forearm)

Run:
    python3 gen_bicep_curl_barbell.py            # writes bicep_curl_barbell.rml
    python3 gen_bicep_curl_barbell.py --publish  # builds .riv + copies asset & 256x256 thumbnail
"""
import math
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "scene.rml"
ASSET_RIV = REPO / "assets/animations/bicep_curl_barbell.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/bicep_curl_barbell.png"
THUMB_ADVANCE = "1.20s"  # peak concentric contraction at the top of the curl
THUMB_VIEWPORT = "1280x720"  # 2x the 640x360 artboard
THUMB_CROP = (680, 20, 260)  # square size, offsetY, offsetX in the 2x render
THUMB_SIZE = 256
RIVE_BIN = pathlib.Path.home() / ".rive/bin/rive"

# 16:9 standard canvas matching ab_wheel_rollout, arnold_press, barbell_row, bench_dips, bench_press
W, H = 640, 360
FLOOR = 300.0

# Shoulder anchors in world space (standing athlete facing 3/4 front-left)
SHOULDER_FAR = (296.0, 99.0)   # Right (far / screen-left) shoulder
SHOULDER_NEAR = (346.0, 102.0)  # Left (near / screen-right) shoulder

# Base limb lengths (humerus & radius/ulna)
UPPER_ARM_LEN = 49.0
FOREARM_LEN = 44.0

# Timeline (frames @60fps): curl up 1.10s (66f), top squeeze 0.30s (18f), lower 1.23s (74f), bottom pause 0.37s (22f) = 3.0s (180f)
CURL_FRAMES, HOLD_TOP, LOWER_FRAMES, HOLD_BOT = 66, 18, 74, 22
DURATION = CURL_FRAMES + HOLD_TOP + LOWER_FRAMES + HOLD_BOT
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


def curl_progress(frame):
    """0.0 at bottom extension, 1.0 at top peak contraction."""
    fr = frame % DURATION
    if fr <= CURL_FRAMES:
        return EASE(fr / CURL_FRAMES)
    fr -= CURL_FRAMES
    if fr <= HOLD_TOP:
        return 1.0
    fr -= HOLD_TOP
    if fr <= LOWER_FRAMES:
        return 1.0 - EASE(fr / LOWER_FRAMES)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def pose(c):
    """Compute standing barbell curl joint transforms at curl progress c in [0, 1]."""
    # Elbows stay anchored at the sides of the torso with a subtle 5 deg forward flexion at peak contraction
    ua_near = math.radians(lerp(90.5, 96.5, c))
    ua_far = math.radians(lerp(92.0, 98.0, c))

    elbow_near = (
        SHOULDER_NEAR[0] + UPPER_ARM_LEN * math.cos(ua_near),
        SHOULDER_NEAR[1] + UPPER_ARM_LEN * math.sin(ua_near),
    )
    elbow_far = (
        SHOULDER_FAR[0] + UPPER_ARM_LEN * math.cos(ua_far),
        SHOULDER_FAR[1] + UPPER_ARM_LEN * math.sin(ua_far),
    )

    # Sagittal curl angle theta from -66 deg (bottom extension with natural ~22 deg elbow bend)
    # through 0 deg (horizontal forward-left at mid-curl) to +74 deg (clavicle height at peak contraction).
    theta = math.radians(lerp(-66.0, 74.0, c))

    # 3/4 projection of the forearm vector from elbow to supinated wrist/palm center
    fa_dx = -36.0 * math.cos(theta) - 8.5 * math.sin(theta)
    fa_dy = -45.5 * math.sin(theta) + 2.5 * math.cos(theta)

    hand_near = (elbow_near[0] + fa_dx, elbow_near[1] + fa_dy)
    # Far hand tracks along the barbell shaft: nearly horizontal (+1 deg) at bottom,
    # slight -4.2 deg upward-right perspective slope at top matching the reference illustration.
    grip_vec = (-54.0, lerp(-1.0, 4.0, c))
    hand_far = (hand_near[0] + grip_vec[0], hand_near[1] + grip_vec[1])

    # Forearm world angles (unwrapped cleanly in [pi/2, 3*pi/2] so interpolation is monotonic)
    dfn_x, dfn_y = hand_near[0] - elbow_near[0], hand_near[1] - elbow_near[1]
    fa_near_ang = math.atan2(dfn_y, dfn_x)
    if fa_near_ang < 0:
        fa_near_ang += 2.0 * math.pi
    fa_near_scale = math.hypot(dfn_x, dfn_y) / FOREARM_LEN

    dff_x, dff_y = hand_far[0] - elbow_far[0], hand_far[1] - elbow_far[1]
    fa_far_ang = math.atan2(dff_y, dff_x)
    if fa_far_ang < 0:
        fa_far_ang += 2.0 * math.pi
    fa_far_scale = math.hypot(dff_x, dff_y) / FOREARM_LEN

    # Barbell center & angle locked to the midpoint and axis of the two hands
    bar_center = (
        0.5 * (hand_near[0] + hand_far[0]),
        0.5 * (hand_near[1] + hand_far[1]),
    )
    bar_angle = math.atan2(hand_near[1] - hand_far[1], hand_near[0] - hand_far[0])

    # Dynamic biceps peak bulge (scaleY of the biceps belly along the anterior +y axis)
    biceps_peak = lerp(1.0, 1.20, c ** 1.1)

    return {
        "c": c,
        "ua_near": ua_near,
        "ua_far": ua_far,
        "elbow_near": elbow_near,
        "elbow_far": elbow_far,
        "hand_near": hand_near,
        "hand_far": hand_far,
        "fa_near_ang": fa_near_ang,
        "fa_near_scale": fa_near_scale,
        "fa_far_ang": fa_far_ang,
        "fa_far_scale": fa_far_scale,
        "bar_center": bar_center,
        "bar_angle": bar_angle,
        "biceps_peak": biceps_peak,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(curl_progress(fr)) for fr in FRAMES}

# Half distance between hands along the barbell shaft (~27.0 px)
GRIP_HALF_SPAN = 0.5 * math.hypot(
    POSES[0]["hand_near"][0] - POSES[0]["hand_far"][0],
    POSES[0]["hand_near"][1] - POSES[0]["hand_far"][1],
)

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
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
HIGHLIGHT = "D9FFFFFF"
CORE_SHADOW = "8C0F172A"
SOFT_SHADOW = "4D0F172A"
MUSCLE_LOW = (0x66, 0xFB, 0x92, 0x3C)   # warm orange at bottom extension (curl_t = 0)
MUSCLE_HIGH = (0xF2, 0xEF, 0x44, 0x44)  # intense red at top peak contraction (curl_t = 1)
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
    """0.0 at bottom extension -> 1.0 at top peak contraction."""
    return p["c"] ** 1.05


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


# ---------------------------------------------------------------- Olympic Barbell & Supinated Grip Wraps
def barbell_rig():
    """Olympic barbell with 3/4 isometric 35-lb plates, collars, sleeves, and supinated hand wraps."""
    ind = "        "
    i2 = ind + "    "
    bar_id = nid()
    key_double(bar_id, 13, lambda p: p["bar_center"][0])
    key_double(bar_id, 14, lambda p: p["bar_center"][1])
    key_double(bar_id, 15, lambda p: p["bar_angle"])
    p0 = POSES[0]

    plate_face = f'<Fill name="PlateFaceFill">{grad("PlateFaceGrad", -16, -34, 16, 34, "FF334155", "FF0F172A")}</Fill>'
    plate_rim = f'<Fill name="PlateRimFill">{grad("PlateRimGrad", -16, -34, 16, 34, "FF475569", "FF111827")}</Fill>'
    plate_recess = f'<Fill name="PlateRecessFill">{grad("PlateRecessGrad", -12, -25, 12, 25, "FF1E293B", "FF0B1120")}</Fill>'
    plate_edge = '<Stroke thickness="1.2" name="PlateStroke"><SolidColor colorValue="FF64748B" name="PlateStrokeCol"/></Stroke>'
    recess_edge = '<Stroke thickness="1.0" name="RecessStroke"><SolidColor colorValue="4094A3B8" name="RecessStrokeCol"/></Stroke>'
    collar_fill = f'<Fill name="CollarFill">{grad("CollarGrad", 0, -8, 0, 8, "FFE2E8F0", "FF64748B")}</Fill>'
    collar_rim = '<Stroke thickness="0.9" name="CollarStroke"><SolidColor colorValue="FF475569" name="CollarStrokeCol"/></Stroke>'

    def iso_plate(name, cx, w=34.0, h=66.0):
        """3/4 Olympic plate centered at local x = cx with left-side 3D rim and right-facing hub."""
        return "\n".join([
            # Raised center collar hub on the right-facing surface
            ellipse_shape(i2, name + "HubFront", cx + 3.2, 0, 9.5, 16.5, collar_fill + collar_rim),
            poly_shape(i2, name + "HubBody", [(cx, -8.2), (cx + 3.2, -8.2), (cx + 3.2, 8.2), (cx, 8.2)], collar_fill, radius=1.0),
            # Inner recessed ring & outer face
            ellipse_shape(i2, name + "Recess", cx, 0, w * 0.72, h * 0.72, plate_recess + recess_edge),
            ellipse_shape(i2, name + "Face", cx, 0, w, h, plate_face + plate_edge),
            # 3D plate thickness rim on the -x side
            ellipse_shape(i2, name + "RimMid", cx - 2.6, 0, w, h, plate_rim),
            ellipse_shape(i2, name + "RimBack", cx - 5.2, 0, w, h, plate_rim),
        ])

    def finger_wrap(name, gx, tones, flip_thumb=False):
        """Supinated (underhand) curled fingers + thumb wrapping around the barbell shaft at x = gx."""
        t_sign = -1.0 if flip_thumb else 1.0
        knuckles = []
        for idx, dx in enumerate((-5.4, -1.8, 1.8, 5.4)):
            ky = 0.8 if idx in (1, 2) else 1.2
            knuckles.append(
                ellipse_shape(i2, f"{name}Finger{idx + 1}", gx + dx, ky, 4.4, 9.0, skin_fill(f"{name}F{idx + 1}", -5, 5, tones))
            )
        thumb_pts = [
            (gx + t_sign * 5.0, -4.2),
            (gx + t_sign * 9.5, -2.2),
            (gx + t_sign * 9.8, 3.0),
            (gx + t_sign * 4.5, 4.8),
            (gx + t_sign * 2.5, 0.5),
        ]
        palm_pts = [
            (gx - 7.5, 1.0),
            (gx + 7.5, 1.0),
            (gx + 6.8, 6.8),
            (gx, 7.6),
            (gx - 6.8, 6.8),
        ]
        return "\n".join([
            stroke_shape(i2, f"{name}KnuckleHi", [(gx - 5.0, -1.5), (gx, -2.0), (gx + 5.0, -1.5)], 1.8, HIGHLIGHT, 1.5),
            smooth_shape(i2, f"{name}Thumb", thumb_pts, skin_fill(f"{name}Thumb", -5, 5, tones)),
            *knuckles,
            smooth_shape(i2, f"{name}PalmCradle", palm_pts, skin_fill(f"{name}Palm", 0, 8, tones)),
        ])

    gf = -GRIP_HALF_SPAN
    gn = GRIP_HALF_SPAN

    # Plates placed at +/- 92.0 so the shaft between hands (+/- 27.0) and plates is clearly visible
    # and the Near Plate sits cleanly to the right of the Near Biceps/Deltoid at every curl angle.
    return "\n".join([
        f'{ind}<Node x="{f(p0["bar_center"][0])}" y="{f(p0["bar_center"][1])}" rotation="{f(p0["bar_angle"])}" name="Barbell" id="{bar_id}">',

        # 1. Near (screen-right) outer Olympic sleeve & end cap (in front of the Near Plate face)
        ellipse_shape(i2, "NearSleeveEndCap", 142.0, 0, 4.2, 8.2, solid("NearSleeveEnd", "FF1E293B") + collar_rim),
        stroke_shape(i2, "NearSleeveHi", [(96.0, -1.8), (141.0, -1.8)], 1.6, "D9FFFFFF", 0.0, cap="butt"),
        stroke_shape(i2, "NearSleeveCore", [(95.0, 0.0), (142.0, 0.0)], 6.2, "FF94A3B8", 0.0, cap="butt"),
        stroke_shape(i2, "NearSleeveEdge", [(95.0, 0.0), (142.0, 0.0)], 8.2, "FF334155", 0.0, cap="butt"),

        # 2. Near (screen-right) 35-lb Olympic plate (in front of the main barbell shaft)
        iso_plate("NearPlate", 92.0, w=34.0, h=66.0),

        # 3. Supinated (underhand) finger wraps on both hands (curled in front of the barbell shaft)
        finger_wrap("NearHandWrap", gn, SKIN, flip_thumb=False),
        finger_wrap("FarHandWrap", gf, SKIN_FAR, flip_thumb=True),

        # 4. Main chrome barbell shaft (running from the Far Plate center hub at -89 to the Near Plate at +89)
        stroke_shape(i2, "BarShaftHi", [(-88.0, -1.3), (88.0, -1.3)], 1.3, "E6FFFFFF", 0.0, cap="butt"),
        stroke_shape(i2, "BarShaftCore", [(-89.0, 0.0), (89.0, 0.0)], 4.0, "FFCBD5E1", 0.0, cap="butt"),
        stroke_shape(i2, "BarShaftShadow", [(-89.0, 0.0), (89.0, 0.0)], 5.6, "FF334155", 0.0, cap="butt"),

        # 5. Far (screen-left) 35-lb Olympic plate & outer sleeve (behind the main barbell shaft)
        iso_plate("FarPlate", -92.0, w=32.0, h=62.0),
        ellipse_shape(i2, "FarSleeveEndCap", -124.0, 0, 3.8, 7.6, solid("FarSleeveEnd", "FF1E293B") + collar_rim),
        stroke_shape(i2, "FarSleeveHi", [(-123.0, -1.5), (-96.0, -1.5)], 1.4, "B3FFFFFF", 0.0, cap="butt"),
        stroke_shape(i2, "FarSleeveCore", [(-124.0, 0.0), (-95.0, 0.0)], 5.6, "FF94A3B8", 0.0, cap="butt"),
        stroke_shape(i2, "FarSleeveEdge", [(-124.0, 0.0), (-95.0, 0.0)], 7.6, "FF334155", 0.0, cap="butt"),

        f"{ind}</Node>",
    ])


# ---------------------------------------------------------------- Near & Far Arms with Biceps, Brachialis & Brachioradialis
def arm_rig(prefix, far):
    """UpperArm + Forearm rig with Biceps brachii (short + long head), Brachialis, and Brachioradialis."""
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if far else SKIN
    sx, sy = SHOULDER_FAR if far else SHOULDER_NEAR
    ua_key = "ua_far" if far else "ua_near"
    elbow_key = "elbow_far" if far else "elbow_near"
    fa_ang_key = "fa_far_ang" if far else "fa_near_ang"
    fa_scale_key = "fa_far_scale" if far else "fa_near_scale"

    ua_id, bic_id, fa_id, br_id = nid(), nid(), nid(), nid()
    key_double(ua_id, 15, lambda p: p[ua_key])
    key_double(bic_id, 17, lambda p: p["biceps_peak"])
    key_double(fa_id, 13, lambda p: p[elbow_key][0])
    key_double(fa_id, 14, lambda p: p[elbow_key][1])
    key_double(fa_id, 15, lambda p: p[fa_ang_key])
    key_double(fa_id, 16, lambda p: p[fa_scale_key])
    key_double(br_id, 14, lambda p: lerp(1.5, 3.2, p["c"]) if far else lerp(-0.8, 3.8, p["c"]))
    p0 = POSES[0]

    # Limb local frame: +x runs along the bone (0..49 for UpperArm, 0..44 for Forearm).
    # Because the athlete faces LEFT (-X_screen), local +y is ANTERIOR/MEDIAL (chest-facing)
    # and local -y is POSTERIOR/LATERAL (outer/triceps side).
    ua_pts = [
        (-10, 0), (-8, 9.0), (6, 11.2), (22, 11.8), (37, 9.8), (46, 6.8),
        (52, 0), (46, -6.8), (33, -10.2), (18, -11.0), (3, -10.5), (-8, -8.0),
    ]
    # Biceps brachii (short head = medial/inner +y contour; long head = central/anterior-lateral belly)
    biceps_short_pts = [
        (9, 4.2), (19, 9.2), (31, 10.0), (41, 8.0), (44, 4.5),
        (35, 3.6), (22, 3.2), (11, 2.8),
    ]
    biceps_long_pts = [
        (7, -0.8), (17, 4.2), (29, 5.2), (40, 3.8), (44, 0.8),
        (36, -1.8), (23, -2.2), (11, -1.8),
    ]
    # Brachialis: fusiform muscle on the distal lateral aspect between biceps long head and triceps
    brachialis_pts = [
        (19, -1.8), (30, -0.5), (41, -0.8), (44, -3.5),
        (35, -6.4), (23, -5.8), (17, -3.6),
    ]

    # Sculpted deltoid cap overlapping the proximal humerus
    delt_pts = [
        (-13, 0.5), (-9, 10.5), (2, 12.2), (13, 8.8), (19, 1.5),
        (17, -6.5), (8, -11.2), (-3, -11.8), (-11, -8.0),
    ]
    delt_hi = [(-5, -5.5), (4, -7.2), (12, -4.0)]
    delt_feather = [(3, 9.5), (12, 6.0), (16, 0.0), (12, -6.0)]

    # Forearm contour
    fa_pts = [
        (-6, 0), (-4, 7.5), (10, 9.2), (25, 7.2), (37, 5.2), (44, 4.2),
        (47, 0), (44, -4.2), (35, -5.0), (20, -7.0), (6, -7.8), (-4, -6.5),
    ]
    # Brachioradialis: sleek tapering belly in local node (animated in local y across 3D supinated curl)
    brachioradialis_pts = [
        (-2, -1.2), (6, 3.8), (18, 4.0), (30, 1.8), (34, 0.0),
        (23, -2.0), (10, -2.6), (0, -2.0),
    ]
    br_y0 = 1.5 if far else -0.8
    fa_hi = [(8, -3.2), (22, -2.8), (35, -1.8)]
    fa_sh = [(6, -6.2), (22, -5.5), (35, -3.8)]

    out = [f'{ind}<Node name="{prefix}ArmGroup">']

    # 1. Forearm & Brachioradialis (drawn in front of the elbow joint so the crease folds naturally)
    out.append(
        f'{i2}<Node x="{f(p0[elbow_key][0])}" y="{f(p0[elbow_key][1])}" '
        f'rotation="{f(p0[fa_ang_key])}" scaleX="{f(p0[fa_scale_key])}" name="{prefix}Forearm" id="{fa_id}">'
    )
    out.append(f'{i3}<Node y="{f(br_y0)}" name="{prefix}BrachNode" id="{br_id}">')
    out.append(smooth_shape(i3 + "    ", f"{prefix}Brachioradialis", brachioradialis_pts, muscle_paint(prefix + "Brachioradialis", 0.9)))
    out.append(f"{i3}</Node>")
    if not far:
        out.append(stroke_shape(i3, f"{prefix}ForearmTendon", [(14, 1.5), (27, 1.0), (38, 0.5)], 1.1, SOFT_SHADOW, 1.0))
        out.append(stroke_shape(i3, f"{prefix}ForearmHi", fa_hi, 2.8, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", fa_sh, 4.0, CORE_SHADOW, 4.5))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "Forearm", -8, 10, skin)))
    out.append(f"{i2}</Node>")

    # 2. Upper Arm, Deltoid Cap, Biceps (Short + Long Heads) & Brachialis
    out.append(
        f'{i2}<Node x="{f(sx)}" y="{f(sy)}" rotation="{f(p0[ua_key])}" name="{prefix}UpperArm" id="{ua_id}">'
    )
    # Deltoid cap on top of the proximal upper arm so biceps emerge cleanly from underneath
    if not far:
        out.append(stroke_shape(i3, f"{prefix}DeltAnteriorGroove", delt_feather, 1.3, SOFT_SHADOW, 1.2))
        out.append(stroke_shape(i3, f"{prefix}DeltHi", delt_hi, 3.2, HIGHLIGHT, 3.5))
    else:
        out.append(stroke_shape(i3, f"{prefix}DeltHi", [(-4, 6.0), (5, 7.8), (12, 5.0)], 2.6, "80FFFFFF", 3.0))
    out.append(smooth_shape(i3, f"{prefix}Deltoid", delt_pts, skin_fill(prefix + "Deltoid", -12, 13, skin)))

    # Dynamic Biceps brachii group (scales along +y at peak contraction for realistic biceps peak)
    out.append(f'{i3}<Node scaleY="{f(p0["biceps_peak"])}" name="{prefix}BicepsPeak" id="{bic_id}">')
    i4 = i3 + "    "
    if not far:
        # Separation line between short head (+y inner) and long head (outer)
        out.append(stroke_shape(i4, f"{prefix}BicepsSeptum", [(12, 3.5), (26, 4.2), (39, 3.2)], 1.1, "668B1A1A", 0.6))
        out.append(stroke_shape(i4, f"{prefix}BicepsPeakHi", [(16, 5.2), (28, 6.2), (37, 4.8)], 2.2, "59FFFFFF", 2.5))
    out.append(smooth_shape(i4, f"{prefix}BicepsShortHead", biceps_short_pts, muscle_paint(prefix + "BicepsShort", 0.9)))
    out.append(smooth_shape(i4, f"{prefix}BicepsLongHead", biceps_long_pts, muscle_paint(prefix + "BicepsLong", 0.95)))
    out.append(f"{i3}</Node>")

    # Brachialis (distal lateral upper arm between biceps long head and triceps)
    if not far:
        out.append(smooth_shape(i3, f"{prefix}Brachialis", brachialis_pts, muscle_paint(prefix + "Brachialis", 0.9)))
        out.append(stroke_shape(i3, f"{prefix}TricepsHi", [(14, -7.2), (30, -7.5), (42, -5.5)], 2.6, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i3, f"{prefix}UpperArmSh", [(12, -9.2), (28, -9.5), (42, -7.2)], 4.5, CORE_SHADOW, 5.0))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UpperArm", -11, 12, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{ind}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- Standing 3/4 Athlete Body (Torso, Head, Legs)
def torso_and_head():
    """Standing 3/4 front-left torso, pectorals, sculpted 6-pack abs, compression shorts, and volumetric 3/4 head."""
    ind = "        "
    i2 = ind + "    "

    # Volumetric 3/4 head facing front-left (30x35 px cranial + facial volume)
    head_pts = [
        (304.0, 50.0),  # upper forehead
        (301.5, 56.5),  # left brow ridge
        (300.0, 62.5),  # nose bridge & tip (facing left-front)
        (301.2, 67.5),  # upper lip / mouth
        (301.8, 73.5),  # strong chin tip
        (307.5, 76.5),  # under-chin / anterior jawline
        (316.5, 75.0),  # mandible angle (gonion)
        (323.5, 71.0),  # beneath ear / mastoid
        (328.5, 63.0),  # occiput / back of skull
        (328.0, 52.0),  # posterior crown
        (321.0, 45.0),  # top cranial dome
        (311.0, 45.0),  # anterior crown
    ]
    hair_pts = [
        (303.5, 52.0), (309.0, 44.5), (320.5, 44.2), (328.5, 50.5),
        (329.0, 61.5), (324.5, 65.5), (323.0, 57.5), (318.0, 52.5),
        (310.5, 51.0),
    ]
    head_hi = [(304.5, 54.0), (308.5, 49.0), (317.0, 48.0)]
    cheek_hi = [(303.5, 61.5), (309.5, 63.0), (315.0, 62.0)]
    jaw_sh = [(304.0, 75.5), (313.0, 76.2), (320.5, 72.5)]

    # Muscular neck & upper trapezius flare connecting into the clavicles
    neck_pts = [
        (306.5, 73.0), (322.5, 70.0), (334.0, 86.0),
        (338.0, 94.0), (296.0, 92.0), (304.0, 83.0),
    ]
    scm_line = [(320.0, 72.5), (315.5, 82.0), (312.5, 90.5)]

    # 3/4 Torso silhouette from clavicles (y=89) through broad lats/pecs to waist (y=156) and pelvis (y=182)
    torso_pts = [
        (294.0, 91.0),   # far right clavicle
        (313.0, 89.0),   # suprasternal notch
        (344.0, 94.0),   # near left clavicle
        (346.0, 114.0),  # near lateral pec / lat border
        (340.0, 134.0),  # near serratus / external oblique taper
        (335.0, 154.0),  # near waist / iliac crest
        (338.0, 174.0),  # near outer hip
        (316.0, 182.0),  # pelvis base
        (294.0, 174.0),  # far outer hip
        (297.0, 152.0),  # far waist
        (296.0, 132.0),  # far oblique contour
        (292.0, 112.0),  # far lateral chest contour
    ]
    torso_hi = [(302.0, 98.0), (303.0, 122.0), (304.0, 146.0)]
    torso_sh = [(339.0, 116.0), (334.0, 138.0), (330.0, 154.0)]

    # Sculpted Near (left) and Far (right) Pectoralis Major plates
    pec_near_pts = [
        (312.5, 93.0), (336.0, 95.5), (342.0, 108.0),
        (337.5, 119.5), (324.0, 121.5), (312.0, 117.5),
    ]
    pec_far_pts = [
        (295.0, 93.5), (311.5, 93.0), (311.0, 117.0),
        (300.5, 119.0), (292.5, 112.5), (292.5, 101.0),
    ]
    pec_paint = (
        '<Fill name="PecFill"><SolidColor colorValue="120F172A" name="PecCol"/></Fill>'
        '<Stroke thickness="1.0" join="round" name="PecStroke"><SolidColor colorValue="380F172A" name="PecStrokeCol"/></Stroke>'
    )

    # Sculpted 6-pack abs (far column + near column along the 3/4 linea alba at x ~ 311.5)
    abs_paint = (
        '<Fill name="AbsFill"><SolidColor colorValue="1A0F172A" name="AbsColor"/></Fill>'
        '<Stroke thickness="0.9" join="round" name="AbsEdge"><SolidColor colorValue="400F172A" name="AbsEdgeColor"/></Stroke>'
    )
    abs_blocks = [
        # Near (left of body / right of sternum) 3 rectus abdominis blocks
        [(313.0, 121.0), (325.0, 121.5), (325.5, 130.0), (312.8, 129.5)],
        [(312.6, 131.5), (324.8, 132.0), (324.2, 140.5), (312.4, 140.0)],
        [(312.2, 142.0), (323.5, 142.5), (322.0, 151.5), (312.0, 151.0)],
        # Far (right of body / left of sternum) 3 foreshortened rectus abdominis blocks
        [(301.5, 121.0), (310.5, 121.0), (310.3, 129.5), (301.2, 129.0)],
        [(301.2, 131.0), (310.2, 131.5), (310.0, 140.0), (301.2, 139.5)],
        [(301.5, 141.5), (309.8, 142.0), (309.5, 151.0), (302.0, 150.5)],
    ]

    # Athletic compression shorts over the pelvis (bridging into NearLeg and FarLeg shorts)
    pelvis_shorts = [
        (296.0, 153.0), (313.0, 155.0), (336.0, 154.0),
        (341.0, 176.0), (322.0, 186.0), (311.0, 184.0), (292.0, 176.0),
    ]

    out = [f'{ind}<Node name="TorsoAndHead">']

    # 1. Volumetric 3/4 Head (drawn on top of the neck)
    out.append(smooth_shape(i2, "Hair", hair_pts, f'<Fill name="HairFill">{grad("HairGrad", 304, 44, 329, 65, "FF475569", "FF1E293B")}</Fill>'))
    out.append(ellipse_shape(i2, "Ear", 321.5, 64.5, 5.5, 8.5, solid("Ear", "FFA3B1C4"), rot_deg=12.0))
    out.append(stroke_shape(i2, "BrowShade", [(301.5, 56.8), (306.0, 57.2)], 1.4, "590F172A", 0.8))
    out.append(stroke_shape(i2, "EyeLine", [(303.2, 58.6), (306.2, 58.8)], 1.1, "730F172A", 0.4))
    out.append(stroke_shape(i2, "MouthLine", [(301.5, 68.5), (305.0, 68.8)], 1.0, "590F172A", 0.4))
    out.append(stroke_shape(i2, "HeadHi", head_hi, 3.0, HIGHLIGHT, 3.5))
    out.append(stroke_shape(i2, "CheekHi", cheek_hi, 2.2, "80FFFFFF", 2.5))
    out.append(stroke_shape(i2, "JawShadow", jaw_sh, 2.6, CORE_SHADOW, 2.5))
    out.append(smooth_shape(i2, "Head", head_pts, skin_fill("Head", 45, 77, SKIN, x0=300, x1=328)))

    # 2. Muscular Neck & Clavicles
    out.append(stroke_shape(i2, "UnderChinShadow", [(306.5, 76.5), (313.5, 77.5), (320.0, 74.5)], 3.2, CORE_SHADOW, 2.5))
    out.append(stroke_shape(i2, "SCMLine", scm_line, 1.5, SOFT_SHADOW, 1.5))
    out.append(stroke_shape(i2, "ClavicleLine", [(296.0, 92.5), (312.5, 92.0), (336.0, 94.5)], 1.5, SOFT_SHADOW, 1.2))
    out.append(smooth_shape(i2, "Neck", neck_pts, skin_fill("Neck", 70, 94, SKIN)))

    # 3. Pelvis Shorts & Waistband
    out.append(stroke_shape(i2, "WaistbandLine", [(296.5, 155.5), (314.0, 157.5), (335.5, 156.5)], 1.8, "660F172A", 0.8))
    out.append(stroke_shape(i2, "ShortsFlyLine", [(312.0, 157.5), (311.5, 176.0)], 1.3, "660F172A", 0.8))
    out.append(smooth_shape(i2, "PelvisShorts", pelvis_shorts, skin_fill("PelvisShorts", 153, 186, SHORTS)))

    # 4. Pectorals, 6-Pack Abs, Serratus & Obliques
    for idx, bpts in enumerate(abs_blocks):
        out.append(smooth_shape(i2, f"AbBlock{idx + 1}", bpts, abs_paint))
    out.append(stroke_shape(i2, "LineaAlba", [(312.0, 118.0), (311.5, 136.0), (311.0, 153.0)], 1.3, "470F172A", 0.8))
    out.append(stroke_shape(i2, "ObliqueLine1", [(336.0, 126.0), (330.0, 134.0), (326.0, 141.0)], 1.3, "380F172A", 1.0))
    out.append(stroke_shape(i2, "ObliqueLine2", [(334.0, 136.0), (328.0, 144.0), (324.0, 150.0)], 1.3, "380F172A", 1.0))
    out.append(stroke_shape(i2, "PecNearLowerSh", [(312.5, 118.0), (324.5, 122.0), (338.0, 119.5)], 2.4, CORE_SHADOW, 2.0))
    out.append(stroke_shape(i2, "PecFarLowerSh", [(293.0, 113.0), (301.0, 119.5), (311.0, 117.5)], 2.2, CORE_SHADOW, 2.0))
    out.append(stroke_shape(i2, "PecNearHi", [(316.0, 99.0), (328.0, 100.5), (337.0, 105.0)], 2.8, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i2, "PecNear", pec_near_pts, pec_paint))
    out.append(smooth_shape(i2, "PecFar", pec_far_pts, pec_paint))

    # 5. Torso Base
    out.append(stroke_shape(i2, "TorsoHi", torso_hi, 4.5, HIGHLIGHT, 4.5))
    out.append(stroke_shape(i2, "TorsoSh", torso_sh, 6.0, CORE_SHADOW, 5.5))
    out.append(smooth_shape(i2, "Torso", torso_pts, skin_fill("Torso", 89, 182, SKIN, x0=294, x1=346)))

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def near_leg():
    """Near (left) leg planted on FLOOR=300 in 3/4 view with sculpted quadriceps and gastrocnemius calf."""
    ind = "        "
    i2 = ind + "    "

    shorts_pts = [
        (313.0, 168.0), (339.5, 166.0), (344.5, 192.0),
        (315.5, 194.0), (312.0, 178.0),
    ]
    thigh_pts = [
        (315.0, 174.0), (340.0, 172.0), (346.5, 196.0),
        (343.0, 218.0), (338.0, 232.0), (322.0, 232.0),
        (317.5, 214.0), (314.5, 194.0),
    ]
    thigh_hi = [(324.0, 192.0), (325.0, 210.0), (326.0, 224.0)]
    thigh_sh = [(341.0, 192.0), (340.0, 212.0), (336.0, 228.0)]
    quad_med_line = [(324.0, 200.0), (321.0, 214.0), (324.0, 225.0)]
    quad_lat_line = [(335.0, 194.0), (336.5, 212.0), (333.5, 226.0)]

    shin_pts = [
        (322.5, 230.0), (338.0, 230.0), (346.5, 248.0),
        (345.0, 266.0), (339.5, 288.0), (328.5, 289.0),
        (325.0, 268.0), (322.0, 248.0),
    ]
    shin_hi = [(327.0, 240.0), (328.5, 262.0), (330.0, 282.0)]
    shin_sh = [(342.0, 246.0), (341.5, 264.0), (337.5, 284.0)]
    calf_cut = [(334.0, 246.0), (338.5, 258.0), (335.5, 270.0)]

    foot_pts = [
        (328.5, 286.0), (340.0, 286.0), (343.5, 297.5),
        (334.0, 300.5), (314.0, 301.5), (309.5, 297.5),
        (316.0, 292.5),
    ]

    return "\n".join([
        f'{ind}<Node name="NearLeg">',
        stroke_shape(i2, "NearShortsHem", [(315.5, 192.5), (329.5, 193.0), (344.0, 190.5)], 1.6, "660F172A", 0.6),
        smooth_shape(i2, "NearThighShorts", shorts_pts, skin_fill("NearThighShorts", 166, 194, SHORTS)),
        stroke_shape(i2, "NearQuadMedLine", quad_med_line, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearQuadLatLine", quad_lat_line, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearThighHi", thigh_hi, 4.0, HIGHLIGHT, 4.0),
        stroke_shape(i2, "NearThighSh", thigh_sh, 5.2, CORE_SHADOW, 5.0),
        smooth_shape(i2, "NearThigh", thigh_pts, skin_fill("NearThigh", 172, 232, SKIN)),
        ellipse_shape(i2, "NearKnee", 329.5, 231.0, 16.5, 15.0, skin_fill("NearKnee", -8, 8, SKIN)),
        stroke_shape(i2, "NearFootHi", [(329.0, 290.0), (319.0, 295.0), (312.5, 298.0)], 2.2, HIGHLIGHT, 2.5),
        smooth_shape(i2, "NearFoot", foot_pts, skin_fill("NearFoot", 286, 302, SKIN)),
        stroke_shape(i2, "NearCalfCut", calf_cut, 1.3, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "NearShinHi", shin_hi, 3.2, HIGHLIGHT, 3.5),
        stroke_shape(i2, "NearShinSh", shin_sh, 4.5, CORE_SHADOW, 4.5),
        smooth_shape(i2, "NearShin", shin_pts, skin_fill("NearShin", 230, 289, SKIN)),
        f"{ind}</Node>",
    ])


def far_leg():
    """Far (right) leg planted slightly further back-left in 3/4 perspective."""
    ind = "        "
    i2 = ind + "    "

    shorts_pts = [
        (292.0, 166.0), (315.0, 168.0), (314.0, 190.0),
        (289.5, 188.0),
    ]
    thigh_pts = [
        (291.0, 172.0), (314.0, 174.0), (313.0, 198.0),
        (309.5, 224.0), (294.5, 224.0), (289.5, 204.0),
        (288.0, 186.0),
    ]
    thigh_hi = [(294.5, 188.0), (295.5, 206.0), (297.0, 220.0)]
    thigh_sh = [(309.0, 190.0), (308.0, 208.0), (306.0, 222.0)]
    quad_line = [(302.5, 192.0), (303.5, 208.0), (301.5, 220.0)]

    shin_pts = [
        (295.0, 222.0), (309.5, 222.0), (316.0, 242.0),
        (314.5, 260.0), (309.5, 281.0), (299.0, 282.0),
        (296.5, 260.0), (294.5, 242.0),
    ]
    shin_hi = [(298.5, 232.0), (299.5, 254.0), (301.0, 274.0)]
    shin_sh = [(312.0, 240.0), (311.0, 258.0), (307.5, 276.0)]

    foot_pts = [
        (299.0, 279.0), (310.0, 279.0), (313.0, 289.5),
        (303.0, 292.5), (284.0, 293.5), (279.5, 289.5),
        (286.5, 285.0),
    ]

    return "\n".join([
        f'{ind}<Node name="FarLeg">',
        smooth_shape(i2, "FarThighShorts", shorts_pts, skin_fill("FarThighShorts", 166, 190, SHORTS_FAR)),
        stroke_shape(i2, "FarQuadLine", quad_line, 1.2, SOFT_SHADOW, 1.2),
        stroke_shape(i2, "FarThighHi", thigh_hi, 3.4, HIGHLIGHT, 3.5),
        stroke_shape(i2, "FarThighSh", thigh_sh, 4.6, CORE_SHADOW, 4.5),
        smooth_shape(i2, "FarThigh", thigh_pts, skin_fill("FarThigh", 172, 224, SKIN_FAR)),
        ellipse_shape(i2, "FarKnee", 301.5, 223.5, 15.5, 14.0, skin_fill("FarKnee", -7, 7, SKIN_FAR)),
        smooth_shape(i2, "FarFoot", foot_pts, skin_fill("FarFoot", 279, 294, SKIN_FAR)),
        stroke_shape(i2, "FarShinHi", shin_hi, 2.8, HIGHLIGHT, 3.0),
        stroke_shape(i2, "FarShinSh", shin_sh, 4.0, CORE_SHADOW, 4.0),
        smooth_shape(i2, "FarShin", shin_pts, skin_fill("FarShin", 222, 282, SKIN_FAR)),
        f"{ind}</Node>",
    ])


def shadow():
    ind = "        "
    bar_sh_id = nid()
    key_double(bar_sh_id, 13, lambda p: p["bar_center"][0])
    key_double(bar_sh_id, 16, lambda p: lerp(1.18, 0.96, p["c"]))
    p0 = POSES[0]
    return "\n".join([
        # Dynamic barbell ground shadow (widens slightly when bar is lowered, tightens when curled high)
        f'{ind}<Shape x="{f(p0["bar_center"][0])}" y="{f(FLOOR + 1)}" scaleX="1.18" scaleY="0.065" name="BarShadow" id="{bar_sh_id}">\n'
        f'{ind}    <Ellipse width="210" height="210" name="BarShadowEllipse"/>\n'
        f'{ind}    <Fill name="BarShadowFill"><RadialGradient startX="0" startY="0" endX="105" endY="0" name="BarShadowGrad">'
        f'<GradientStop colorValue="80000000" position="0"/><GradientStop colorValue="33000000" position="0.6"/>'
        f'<GradientStop colorValue="00000000" position="1"/></RadialGradient></Fill>\n'
        f"{ind}</Shape>",
        # Standing athlete ground shadow under both planted feet
        f'{ind}<Shape x="314" y="{f(FLOOR - 2)}" scaleX="0.82" scaleY="0.09" name="BodyShadow">\n'
        f'{ind}    <Ellipse width="190" height="190" name="BodyShadowEllipse"/>\n'
        f'{ind}    <Fill name="BodyShadowFill"><RadialGradient startX="0" startY="0" endX="95" endY="0" name="BodyShadowGrad">'
        f'<GradientStop colorValue="BF000000" position="0"/><GradientStop colorValue="59000000" position="0.6"/>'
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


barbell_xml = barbell_rig()
near_arm_xml = arm_rig("Near", False)
torso_head_xml = torso_and_head()
near_leg_xml = near_leg()
far_leg_xml = far_leg()
far_arm_xml = arm_rig("Far", True)
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
    <!-- Barbell Bicep Curl: 3/4 front-left view, 60 fps, 16:9 (640x360), generated by gen_bicep_curl_barbell.py (do not edit by hand) -->
    <Artboard defaultStateMachineId="0:7" styleId="0:5" clip="true" width="{W}" height="{H}" name="BarbellBicepCurl" id="0:2">
        <LayoutComponentStyle name="Artboard Style" id="0:5"/>

        <!-- Olympic Barbell, 3/4 Weight Plates & Supinated Hand Wraps -->
{barbell_xml}

        <!-- Near (left) arm with Biceps (short + long head), Brachialis & Brachioradialis -->
{near_arm_xml}

        <!-- Standing 3/4 Athlete Torso, Sculpted Chest, 6-Pack Abs & Volumetric Head -->
{torso_head_xml}

        <!-- Near (left) leg in foreground -->
{near_leg_xml}

        <!-- Far (right) leg in 3/4 depth -->
{far_leg_xml}

        <!-- Far (right) arm with Biceps & Brachioradialis -->
{far_arm_xml}

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

        <LinearAnimation fps="60" duration="{DURATION}" loopValue="loop" name="Curl" id="0:60">
{keyed_xml()}
        </LinearAnimation>
    </Artboard>
</Rive>
"""

OUT.write_text(rml)

for fr in (0, 32, 66, 74, 120, DURATION):
    P = POSES[fr]
    print(
        f"f{fr:3d} c={P['c']:.3f} bar=({P['bar_center'][0]:.1f},{P['bar_center'][1]:.1f}) "
        f"elb_near=({P['elbow_near'][0]:.1f},{P['elbow_near'][1]:.1f}) "
        f"hand_near=({P['hand_near'][0]:.1f},{P['hand_near'][1]:.1f})"
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
    # Standard Rive 7.3 header + TOC for our 29-tag procedural schema
    header = bytes([
        82, 73, 86, 69, 7, 3, 0, 196, 1, 236, 1, 238, 3, 229, 4, 230, 4, 231, 4,
        232, 4, 233, 4, 234, 4, 235, 4, 236, 4, 241, 4, 242, 4, 237, 5, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0,
    ])
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
    built = HERE / "build/bicep_curl_barbell.riv"
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
    except PermissionError:
        built.write_bytes(_compile_rml_bytes(OUT))
        shutil.copyfile(built, ASSET_RIV)
    print("published", ASSET_RIV, ASSET_THUMB)


if "--publish" in sys.argv:
    publish()
