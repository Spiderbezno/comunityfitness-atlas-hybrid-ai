#!/usr/bin/env python3
"""Generate a 60 FPS, 16:9 (640x360) procedural Rive 7.3 scene for T-Bar Row (id: 'tbar_row').

Uses our canonical 3/4 CommunityFitness anatomical mannequin (volumetric 3/4 head with cropped dark hair,
ear, brow, eye, nose, and jawline; sculpted upper back, serratus/obliques, dark athletic compression
shorts, quadriceps/hamstrings, gastrocnemius/soleus calves, and planted bare feet).

Biomechanics & Visual Choreography (3/4 Dorso-Lateral Bent-Over Landmine T-Bar Row):
  - Equipment:
    * 3D Landmine Barbell anchored at a heavy floor pivot bracket behind the heels at (420, 296),
      angling forward-left between the athlete's straddled legs to a chrome Olympic sleeve loaded with
      3 stepped black cast-iron Olympic weight plates and a close V-grip double handle beneath the torso.
  - Bottom Stretch (f = 0 & f = 160, r = 0.0):
    * Athlete maintains a rock-solid ~35 deg bent-over hip hinge with flexed knees and neutral spine.
    * Both arms extend downward holding the close V-grip handle as the latissimus dorsi, rhomboids,
      and teres major stretch under the loaded T-Bar.
  - Peak Row Contraction (f = 72, r = 1.0):
    * Athlete drives both elbows back and up along the ribcage while retracting the scapulae, pulling
      the V-grip handle and 3 stepped Olympic plates smoothly upward around the floor landmine pivot
      toward the lower sternum / upper abdomen.
  - Highlighted Target & Synergist Muscle Groups (pulsing warm orange #FFF97316 -> crimson #FFF43F5E):
    1. Latissimus dorsi (Primary — broad V-taper dorsal wing sweeping from thoracolumbar fascia to humerus)
    2. Middle & lower trapezius / Rhomboids (Primary — diamond-shaped interscapular retractors on upper back)
    3. Teres major & Infraspinatus (Synergists — thick axillary/scapular pulling bellies beneath scapular spine)
    4. Posterior deltoid (Synergist — rear head of left & right shoulder caps)
    5. Biceps brachii & Brachioradialis (Synergists — elbow flexors driving the neutral V-grip pull)

Run:
    python3 rive_animations/tbar_row/gen_tbar_row.py            # writes scene.rml
    python3 rive_animations/tbar_row/gen_tbar_row.py --publish  # compiles assets/animations/tbar_row.riv + 256x256 thumbnail
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
ASSET_RIV = REPO / "assets/animations/tbar_row.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/tbar_row.png"

W, H = 640, 360
FLOOR = 300.0
FPS = 60
DURATION = 160  # 2.67s seamless 60fps loop
STEP = 2

# Stationary ankle anchors on FLOOR = 300.0 (straddling the landmine bar, facing left -X)
ANKLE_NEAR = (310.0, 288.0)
ANKLE_FAR = (266.0, 262.0)

# Landmine Floor Pivot Anchor behind the heels
LANDMINE_PIVOT = (420.0, 296.0)
VGRIP_RADIUS = 194.0  # Distance along landmine shaft from pivot to V-grip attachment

# Canonical Limb Rest Lengths
SHIN_NEAR_LEN = 74.0
THIGH_NEAR_LEN = 96.0
SHIN_FAR_LEN = 70.0
THIGH_FAR_LEN = 92.0
UPPER_ARM_NEAR_LEN = 64.0
FOREARM_NEAR_LEN = 56.0
UPPER_ARM_FAR_LEN = 58.0
FOREARM_FAR_LEN = 52.0

# Canonical CommunityFitness Palette
SKIN = ("FFF8FAFC", "FFD3DCE7", "FF94A3B8")
SKIN_FAR = ("FFCBD5E1", "FF94A3B8", "FF64748B")
SHORTS = ("FF475569", "FF2B3649", "FF172033")
SHORTS_FAR = ("FF334155", "FF1E293B", "FF0F172A")
PLATE_DARK = ("FF334155", "FF182232", "FF090D16")
STEEL_BAR = ("FFF1F5F9", "FF94A3B8", "FF475569")
DARK_STEEL = ("FF64748B", "FF334155", "FF0F172A")
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


EASE_ROW_UP = cubic_bezier(0.34, 0.0, 0.22, 1.0)
EASE_ROW_DOWN = cubic_bezier(0.42, 0.0, 0.36, 1.0)


def row_progress(frame):
    """Returns T-Bar row progress r in [0.0, 1.0] across 160 frames:
    - 0..12:   Bottom lat-stretch hold (r = 0.0)
    - 12..64:  Concentric T-Bar row pull (r: 0.0 -> 1.0: elbows drive high & back, bar pivots up)
    - 64..84:  Peak back-squeeze hold at sternum/upper abdomen (r = 1.0)
    - 84..148: Controlled eccentric lowering (r: 1.0 -> 0.0)
    - 148..160: Bottom stretch hold (r = 0.0)
    """
    fr = frame % (DURATION + 1)
    if fr <= 12:
        return 0.0
    if fr <= 64:
        return EASE_ROW_UP((fr - 12) / 52.0)
    if fr <= 84:
        return 1.0
    if fr <= 148:
        return 1.0 - EASE_ROW_DOWN((fr - 84) / 64.0)
    return 0.0


def lerp(a, b, t):
    return a + (b - a) * t


def quad_interp_pt(p0, p_mid, p1, t):
    """Smooth quadratic Lagrange interpolation through p0 (t=0), p_mid (t=0.5), and p1 (t=1.0)."""
    l0 = (1.0 - t) * (1.0 - 2.0 * t)
    l1 = 4.0 * t * (1.0 - t)
    l2 = t * (2.0 * t - 1.0)
    return (
        l0 * p0[0] + l1 * p_mid[0] + l2 * p1[0],
        l0 * p0[1] + l1 * p_mid[1] + l2 * p1[1],
    )


def seg_xform(p0, p1, base_len):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ang = math.atan2(dy, dx)
    sc = max(0.55, math.hypot(dx, dy) / base_len)
    return ang, sc


def pose(r):
    """Compute 3/4 Dorso-Lateral Bent-Over T-Bar Row transforms at progress r in [0.0, 1.0]."""
    # 1. Athletic Straddled Hip-Hinge Legs (facing left -X)
    knee_near = (lerp(292.0, 290.0, r), lerp(218.0, 217.0, r))
    knee_far = (lerp(250.0, 248.0, r), lerp(194.0, 193.0, r))
    hip_near = (lerp(368.0, 370.0, r), lerp(154.0, 151.0, r))
    hip_far = (lerp(344.0, 346.0, r), lerp(142.0, 139.0, r))

    shin_near_ang, shin_near_sc = seg_xform(knee_near, ANKLE_NEAR, SHIN_NEAR_LEN)
    thigh_near_ang, thigh_near_sc = seg_xform(hip_near, knee_near, THIGH_NEAR_LEN)
    shin_far_ang, shin_far_sc = seg_xform(knee_far, ANKLE_FAR, SHIN_FAR_LEN)
    thigh_far_ang, thigh_far_sc = seg_xform(hip_far, knee_far, THIGH_FAR_LEN)

    # 2. 35-Degree Hinged Torso & Retracting Shoulder Anchors
    torso_x, torso_y = hip_near
    torso_rot = math.radians(lerp(6.5, 9.5, r))
    sh_near = (lerp(254.0, 262.0, r), lerp(108.0, 101.0, r))
    sh_far = (lerp(274.0, 282.0, r), lerp(82.0, 75.0, r))

    # 3. Landmine T-Bar Pivot Kinematics around LANDMINE_PIVOT = (420, 296):
    #    - r = 0.0 (Bottom Stretch): bar_ang = -160.5 deg -> V-grip at (237.1, 231.2)
    #    - r = 1.0 (Peak Row Pull):  bar_ang = -142.5 deg -> V-grip at (266.1, 177.9)
    bar_ang = math.radians(lerp(-160.5, -142.5, r))
    vgrip_x = LANDMINE_PIVOT[0] + VGRIP_RADIUS * math.cos(bar_ang)
    vgrip_y = LANDMINE_PIVOT[1] + VGRIP_RADIUS * math.sin(bar_ang)

    # Hands gripping the close V-grip double handle prongs
    hand_near = (vgrip_x + 4.5, vgrip_y - 9.0)
    hand_far = (vgrip_x - 6.5, vgrip_y - 16.0)

    # 4. Near (Left) Arm Rowing Trajectory (drives elbow back & up past the ribs):
    #    - r = 0.0: extended down toward V-grip (`elb_near = (246.0, 168.0)`)
    #    - r = 1.0: driven high & back past dorsal torso line (`elb_near = (314.0, 108.0)`)
    elb_near = quad_interp_pt((246.0, 168.0), (282.0, 140.0), (314.0, 108.0), r)
    ua_near_ang, ua_near_sc = seg_xform(sh_near, elb_near, UPPER_ARM_NEAR_LEN)
    fa_near_ang, fa_near_sc = seg_xform(elb_near, hand_near, FOREARM_NEAR_LEN)
    delt_near_ang = math.radians(lerp(96.0, 22.0, r))

    # 5. Far (Right) Arm Rowing Trajectory:
    elb_far = quad_interp_pt((246.0, 144.0), (274.0, 114.0), (298.0, 82.0), r)
    ua_far_ang, ua_far_sc = seg_xform(sh_far, elb_far, UPPER_ARM_FAR_LEN)
    fa_far_ang, fa_far_sc = seg_xform(elb_far, hand_far, FOREARM_FAR_LEN)
    delt_far_ang = math.radians(lerp(106.0, 18.0, r))

    shd_sx = lerp(1.48, 1.56, r)

    return {
        "r": r,
        "knee_near": knee_near,
        "knee_far": knee_far,
        "hip_near": hip_near,
        "hip_far": hip_far,
        "shin_near_ang": shin_near_ang,
        "shin_near_sc": shin_near_sc,
        "thigh_near_ang": thigh_near_ang,
        "thigh_near_sc": thigh_near_sc,
        "shin_far_ang": shin_far_ang,
        "shin_far_sc": shin_far_sc,
        "thigh_far_ang": thigh_far_ang,
        "thigh_far_sc": thigh_far_sc,
        "torso_x": torso_x,
        "torso_y": torso_y,
        "torso_rot": torso_rot,
        "sh_near": sh_near,
        "sh_far": sh_far,
        "bar_ang": bar_ang,
        "vgrip_x": vgrip_x,
        "vgrip_y": vgrip_y,
        "elb_near": elb_near,
        "hand_near": hand_near,
        "ua_near_ang": ua_near_ang,
        "ua_near_sc": ua_near_sc,
        "fa_near_ang": fa_near_ang,
        "fa_near_sc": fa_near_sc,
        "delt_near_ang": delt_near_ang,
        "elb_far": elb_far,
        "hand_far": hand_far,
        "ua_far_ang": ua_far_ang,
        "ua_far_sc": ua_far_sc,
        "fa_far_ang": fa_far_ang,
        "fa_far_sc": fa_far_sc,
        "delt_far_ang": delt_far_ang,
        "shd_sx": shd_sx,
    }


FRAMES = list(range(0, DURATION + 1, STEP))
if FRAMES[-1] != DURATION:
    FRAMES.append(DURATION)
POSES = {fr: pose(row_progress(fr)) for fr in FRAMES}

# Continuous angle unwrapping across all rotation keys to prevent 2*pi branch-cut flips
_ANGLE_KEYS = (
    "shin_near_ang",
    "thigh_near_ang",
    "shin_far_ang",
    "thigh_far_ang",
    "torso_rot",
    "bar_ang",
    "ua_near_ang",
    "fa_near_ang",
    "delt_near_ang",
    "ua_far_ang",
    "fa_far_ang",
    "delt_far_ang",
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


def skin_fill(name, y0, y1, tones=SKIN, x0=0, x1=0):
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
    fid, lid = nid(), nid()
    key_color(fid, 37, lambda p: argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, fn_t(p)))
    key_color(lid, 37, lambda p: argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, fn_t(p)))
    t0 = fn_t(POSES[0])
    return (
        f'<Fill name="{name}Fill"><SolidColor colorValue="{argb_lerp(MUSCLE_LOW, MUSCLE_HIGH, t0)}" name="{name}Color" id="{fid}"/></Fill>'
        f'<Stroke thickness="{f(float(line))}" join="round" name="{name}Edge">'
        f'<SolidColor colorValue="{argb_lerp(MUSCLE_LINE_LOW, MUSCLE_LINE_HIGH, t0)}" name="{name}EdgeColor" id="{lid}"/></Stroke>'
    )


# ---------------------------------------------------------------- 1. 3D Landmine Barbell, Floor Pivot, 3 Stepped Olympic Plates & V-Grip
def build_landmine_rear_shaft_and_pivot(indent):
    """Builds the floor-anchored landmine pivot bracket at (420, 296) and the rear steel shaft running
    between the athlete's legs (drawn behind the Near leg and in front of the Far leg)."""
    i2 = indent + "    "
    i3 = i2 + "    "
    bar_id = nid()
    key_double(bar_id, 15, lambda p: p["bar_ang"])
    p0 = POSES[0]

    # Heavy cast-iron landmine floor baseplate & swivel housing at (420, 296)
    base_pts = [
        (400.0, 299.5), (404.0, 293.0), (438.0, 293.0), (442.0, 299.5),
    ]
    turret_pts = [
        (411.0, 294.5), (414.0, 285.5), (428.0, 285.5), (431.0, 294.5),
    ]
    shaft_pts = [
        (12.0, -3.0), (VGRIP_RADIUS + 8.0, -3.0),
        (VGRIP_RADIUS + 8.0, 3.0), (12.0, 3.0),
    ]
    sleeve_collar_pts = [
        (10.0, -5.0), (24.0, -5.0), (24.0, 5.0), (10.0, 5.0),
    ]

    out = [f'{indent}<Node name="LandmineRearShaftAndPivot">']
    # Swivel Joint & Baseplate on Floor (Topmost in this group so it caps the shaft pivot cleanly)
    out.append(ellipse_shape(i2, "PivotBolt", 420.0, 290.0, 5.5, 5.5, skin_fill("PivotBolt", -3, 3, STEEL_BAR)))
    out.append(stroke_shape(i2, "TurretHi", [(414.0, 287.5), (426.0, 287.5)], 1.6, HIGHLIGHT, 1.0))
    out.append(smooth_shape(i2, "LandmineTurret", turret_pts, skin_fill("Turret", 285, 295, DARK_STEEL)))
    out.append(stroke_shape(i2, "BaseplateHi", [(404.0, 294.8), (436.0, 294.8)], 1.5, "6694A3B8", 0.6))
    out.append(smooth_shape(i2, "LandmineBaseplate", base_pts, skin_fill("Baseplate", 293, 300, PLATE_DARK)))

    # Rotating Rear Landmine Barbell Shaft (starts at x=12 inside turret housing)
    out.append(
        f'{i2}<Node x="{f(LANDMINE_PIVOT[0])}" y="{f(LANDMINE_PIVOT[1] - 4.0)}" '
        f'rotation="{f(p0["bar_ang"])}" name="LandmineRearShaftNode" id="{bar_id}">'
    )
    out.append(smooth_shape(i3, "PivotSleeveCollar", sleeve_collar_pts, skin_fill("PivotCollar", -5, 5, DARK_STEEL)))
    out.append(stroke_shape(i3, "ShaftHighlight", [(24.0, -1.2), (VGRIP_RADIUS, -1.2)], 1.5, "FFFFFFFF", 0.5))
    out.append(smooth_shape(i3, "BarbellShaft", shaft_pts, skin_fill("BarShaft", -3.5, 3.5, STEEL_BAR)))
    out.append(f"{i2}</Node>")
    out.append(f"{indent}</Node>")
    return "\n".join(out)


def build_landmine_front_plates_and_vgrip(indent):
    """Builds the front end of the Landmine T-Bar (3 stepped black Olympic weight plates, chrome sleeve
    collar, and close V-grip double handle with knurled rubber grips) pivoting around (420, 296)."""
    i2 = indent + "    "
    i3 = i2 + "    "
    front_id = nid()
    key_double(front_id, 15, lambda p: p["bar_ang"])
    p0 = POSES[0]

    plate_face = (
        '<Fill name="TBarPlateFaceFill">' + grad3("TBarPlateFaceGrad", -34, 34, *PLATE_DARK, x0=-14, x1=14) + "</Fill>"
        '<Stroke thickness="1.25" name="TBarPlateFaceStroke"><SolidColor colorValue="FF475569" name="TBarPlateFaceStrokeCol"/></Stroke>'
    )
    plate_rim = (
        '<Fill name="TBarPlateRimFill"><SolidColor colorValue="FF020617" name="TBarPlateRimCol"/></Fill>'
        '<Stroke thickness="1.0" name="TBarPlateRimStroke"><SolidColor colorValue="FF1E293B" name="TBarPlateRimStrokeCol"/></Stroke>'
    )
    plate_groove = (
        '<Stroke thickness="1.15" name="TBarPlateGrooveStroke"><SolidColor colorValue="FF334155" name="TBarPlateGrooveCol"/></Stroke>'
    )
    hub_paint = (
        '<Fill name="TBarHubFill">' + grad("TBarHubGrad", -5, -8, 5, 8, "FFF8FAFC", "FF475569") + "</Fill>"
        '<Stroke thickness="0.95" name="TBarHubStroke"><SolidColor colorValue="FF0F172A" name="TBarHubStrokeCol"/></Stroke>'
    )

    # Local coordinates along the landmine shaft (origin at LANDMINE_PIVOT = (420, 296), pointing along +X):
    #   V-grip hook attaches at x = VGRIP_RADIUS (194.0)
    #   Olympic sleeve & 3 stepped plates sit at x = 212..252
    sleeve_tip_pts = [
        (206.0, -5.0), (256.0, -5.0), (256.0, 5.0), (206.0, 5.0),
    ]
    collar_pts = [
        (204.0, -7.8), (211.0, -7.8), (211.0, 7.8), (204.0, 7.8),
    ]

    out = [
        f'{indent}<Node x="{f(LANDMINE_PIVOT[0])}" y="{f(LANDMINE_PIVOT[1])}" '
        f'rotation="{f(p0["bar_ang"])}" name="LandmineFrontAssembly" id="{front_id}">'
    ]

    # 1. Outer Chrome Sleeve Tip & Spring Collar Lock (in front of the 3rd plate at x = 250)
    out.append(ellipse_shape(i2, "FrontSleeveCap", 255.0, 0.0, 6.5, 11.0, hub_paint))
    out.append(polyline_stroke_shape(i2, "OuterSleeveHi", [(244.0, -1.8), (254.5, -1.8)], 1.6, "FFFFFFFF"))
    out.append(polyline_stroke_shape(i2, "OuterSleeveShaft", [(243.0, 0.0), (255.0, 0.0)], 9.2, "FF94A3B8"))

    # 2. 3 Stepped Black Olympic Weight Plates (45 lb inner, 35 lb middle, 25 lb outer)
    # Plate 3 (Outer 25 lb plate at x = 239)
    out.append(ellipse_shape(i2, "OlympicPlate3Hub", 240.0, 0.0, 7.5, 13.5, hub_paint))
    out.append(ellipse_shape(i2, "OlympicPlate3Groove", 239.5, 0.0, 17.5, 34.0, plate_groove))
    out.append(ellipse_shape(i2, "OlympicPlate3Face", 239.5, 0.0, 24.0, 46.0, plate_face))
    out.append(ellipse_shape(i2, "OlympicPlate3Rim", 236.5, 0.0, 24.0, 46.0, plate_rim))

    # Plate 2 (Middle 35 lb plate at x = 228)
    out.append(ellipse_shape(i2, "OlympicPlate2Groove", 228.5, 0.0, 21.5, 42.0, plate_groove))
    out.append(ellipse_shape(i2, "OlympicPlate2Face", 228.5, 0.0, 28.5, 56.0, plate_face))
    out.append(ellipse_shape(i2, "OlympicPlate2Rim", 225.2, 0.0, 28.5, 56.0, plate_rim))

    # Plate 1 (Inner 45 lb deep-dish Olympic plate at x = 216)
    out.append(ellipse_shape(i2, "OlympicPlate1Groove", 216.5, 0.0, 25.5, 51.0, plate_groove))
    out.append(ellipse_shape(i2, "OlympicPlate1Face", 216.5, 0.0, 33.5, 66.0, plate_face))
    out.append(ellipse_shape(i2, "OlympicPlate1Rim", 213.0, 0.0, 33.5, 66.0, plate_rim))

    # Inner Sleeve Collar at x = 207
    out.append(smooth_shape(i2, "InnerSleeveCollar", collar_pts, skin_fill("InnerCollar", -8, 8, STEEL_BAR)))
    out.append(smooth_shape(i2, "OlympicSleeveBase", sleeve_tip_pts, skin_fill("OlympicSleeve", -5, 5, STEEL_BAR)))

    # 3. Close V-Grip Double Handle Bracket at x = VGRIP_RADIUS (194.0)
    #     Since bar_ang is around -150 deg, +Y in bar-local space points UP-RIGHT toward the athlete's chest/hands!
    vg = VGRIP_RADIUS
    # Near (Left) V-grip handle prong & rubber knurled grip
    out.append(polyline_stroke_shape(i2, "VGripNearRubber", [(vg - 6.0, 8.0), (vg + 4.0, 15.0)], 6.2, "FF0F172A", radius=1.0))
    out.append(polyline_stroke_shape(i2, "VGripNearFlange", [(vg + 4.5, 13.0), (vg + 2.5, 17.5)], 3.2, "FFCBD5E1", radius=0.5))
    out.append(polyline_stroke_shape(i2, "VGripNearStrut", [(vg, 0.0), (vg - 5.5, 8.5)], 4.0, "FFCBD5E1", radius=0.8))
    # Far (Right) V-grip handle prong
    out.append(polyline_stroke_shape(i2, "VGripFarRubber", [(vg + 3.0, 14.0), (vg + 12.0, 20.0)], 5.6, "FF1E293B", radius=1.0))
    out.append(polyline_stroke_shape(i2, "VGripFarStrut", [(vg, 0.0), (vg + 4.0, 14.5)], 3.6, "FF94A3B8", radius=0.8))
    # Saddle Clasp around Barbell Shaft
    out.append(ellipse_shape(i2, "VGripSaddleClasp", vg, 0.0, 11.0, 10.5, skin_fill("VGripClasp", -5, 5, DARK_STEEL)))

    out.append(f"{indent}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 2. T-Bar Row Arm + Shoulder Cap + Activated Biceps/Brachioradialis
def build_tbar_row_arm(indent, prefix, is_far=False):
    """Builds the Near (Left) or Far (Right) rowing arm with highlighted Posterior Deltoid,
    Biceps Brachii, and Brachioradialis, plus neutral-grip fist on the V-grip handle."""
    i2 = indent + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if is_far else SKIN

    sh_key = "sh_far" if is_far else "sh_near"
    el_key = "elb_far" if is_far else "elb_near"
    hand_key = "hand_far" if is_far else "hand_near"
    ua_len = UPPER_ARM_FAR_LEN if is_far else UPPER_ARM_NEAR_LEN
    fa_len = FOREARM_FAR_LEN if is_far else FOREARM_NEAR_LEN
    ua_ang_key = "ua_far_ang" if is_far else "ua_near_ang"
    ua_sc_key = "ua_far_sc" if is_far else "ua_near_sc"
    fa_ang_key = "fa_far_ang" if is_far else "fa_near_ang"
    fa_sc_key = "fa_far_sc" if is_far else "fa_near_sc"
    delt_ang_key = "delt_far_ang" if is_far else "delt_near_ang"

    delt_id, ua_id, fa_id, fist_id = nid(), nid(), nid(), nid()
    key_double(delt_id, 13, lambda p: p[sh_key][0])
    key_double(delt_id, 14, lambda p: p[sh_key][1])
    key_double(delt_id, 15, lambda p: p[delt_ang_key])

    key_double(ua_id, 13, lambda p: p[sh_key][0])
    key_double(ua_id, 14, lambda p: p[sh_key][1])
    key_double(ua_id, 15, lambda p: p[ua_ang_key])
    key_double(ua_id, 16, lambda p: p[ua_sc_key])

    key_double(fa_id, 13, lambda p: p[el_key][0])
    key_double(fa_id, 14, lambda p: p[el_key][1])
    key_double(fa_id, 15, lambda p: p[fa_ang_key])
    key_double(fa_id, 16, lambda p: p[fa_sc_key])

    key_double(fist_id, 13, lambda p: p[hand_key][0])
    key_double(fist_id, 14, lambda p: p[hand_key][1])
    p0 = POSES[0]

    def post_delt_t(p):
        return 0.48 + 0.50 * (p["r"] ** 0.74)

    def biceps_t(p):
        return 0.42 + 0.54 * (p["r"] ** 0.78)

    def brachio_t(p):
        return 0.44 + 0.52 * (p["r"] ** 0.76)

    delt_base_pts = [
        (-13.0, -3.5), (-8.0, -15.0), (6.0, -16.2), (22.0, -11.5),
        (31.0, 0.0), (22.0, 12.2), (6.0, 15.8), (-8.0, 13.5),
    ]
    post_delt_pts = [
        (-10.5, -2.0), (-6.8, -14.8), (6.5, -16.0), (22.5, -11.2),
        (28.5, -2.0), (11.0, -0.8),
    ]

    ua_pts = [
        (-7.0, 0.0), (-4.0, -11.5), (14.0, -12.8), (ua_len * 0.58, -11.5), (ua_len - 5.0, -8.2),
        (ua_len + 5.0, 0.0), (ua_len - 5.0, 8.2), (ua_len * 0.58, 12.2), (14.0, 12.8), (-4.0, 11.2),
    ]
    # Biceps brachii & Brachialis along the ventral (+Y) aspect of the upper arm
    biceps_pts = [
        (10.0, 1.5), (ua_len * 0.52, 1.2), (ua_len - 7.0, 2.8),
        (ua_len - 9.0, 8.8), (ua_len * 0.50, 12.0), (12.0, 11.2),
    ]

    fa_pts = [
        (-6.5, 0.0), (-3.5, -9.8), (fa_len * 0.34, -10.8), (fa_len - 6.0, -6.5),
        (fa_len + 4.5, 0.0), (fa_len - 6.0, 6.5), (fa_len * 0.34, 10.5), (-3.5, 9.5),
    ]
    # Brachioradialis belly along the radial/dorsal border of the forearm
    brachio_pts = [
        (-2.0, -2.0), (fa_len * 0.36, -9.8), (fa_len * 0.76, -5.8),
        (fa_len * 0.72, -0.5), (fa_len * 0.32, 1.8),
    ]
    fist_pts = [
        (-7.5, -6.5), (7.5, -6.5), (9.5, 0.0), (7.5, 6.8), (-7.5, 6.8), (-9.5, 0.0),
    ]

    out = [f'{indent}<Node name="{prefix}TBarRowArmGroup">']

    # 1. Shoulder Cap with Highlighted Posterior Deltoid
    out.append(
        f'{i2}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" '
        f'rotation="{f(p0[delt_ang_key])}" name="{prefix}DeltoidNode" id="{delt_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}PostDeltHi", [(-2.0, -8.5), (20.0, -6.5)], 2.6, HIGHLIGHT, 2.4))
    out.append(stroke_shape(i3, f"{prefix}PostLatGroove", [(-5.0, -0.5), (25.0, 0.0)], 1.3, "997C2D12", 0.4))
    out.append(smooth_shape(i3, f"{prefix}PosteriorDeltoid", post_delt_pts, muscle_paint_fn(prefix + "PostDelt", post_delt_t, 1.05)))
    out.append(smooth_shape(i3, f"{prefix}DeltoidBaseCap", delt_base_pts, skin_fill(prefix + "DeltCap", -16, 16, skin)))
    out.append(f"{i2}</Node>")

    # 2. Neutral-Grip Fist on V-Grip Handle
    out.append(
        f'{i2}<Node x="{f(p0[hand_key][0])}" y="{f(p0[hand_key][1])}" name="{prefix}GripFistNode" id="{fist_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}Knuckle1", [(-3.5, -4.5), (-3.5, 4.5)], 1.0, SOFT_SHADOW, 0.2))
    out.append(stroke_shape(i3, f"{prefix}Knuckle2", [(0.5, -4.8), (0.5, 4.8)], 1.0, SOFT_SHADOW, 0.2))
    out.append(stroke_shape(i3, f"{prefix}Knuckle3", [(4.2, -4.5), (4.2, 4.5)], 1.0, SOFT_SHADOW, 0.2))
    out.append(stroke_shape(i3, f"{prefix}FistHi", [(-5.0, -3.0), (5.0, -3.0)], 1.8, HIGHLIGHT, 1.5))
    out.append(smooth_shape(i3, f"{prefix}GripFist", fist_pts, skin_fill(prefix + "Fist", -7, 7, skin)))
    out.append(f"{i2}</Node>")

    # 3. Forearm with Highlighted Brachioradialis
    out.append(
        f'{i2}<Node x="{f(p0[el_key][0])}" y="{f(p0[el_key][1])}" '
        f'rotation="{f(p0[fa_ang_key])}" scaleX="{f(p0[fa_sc_key])}" name="{prefix}ForearmNode" id="{fa_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}BrachioHi", [(4.0, -5.2), (fa_len * 0.52, -4.5)], 2.2, HIGHLIGHT, 2.0))
    out.append(smooth_shape(i3, f"{prefix}Brachioradialis", brachio_pts, muscle_paint_fn(prefix + "Brachio", brachio_t, 0.95)))
    out.append(stroke_shape(i3, f"{prefix}ExtensorGroove", [(6.0, 2.0), (fa_len * 0.72, 1.5)], 1.15, SOFT_SHADOW, 0.6))
    out.append(stroke_shape(i3, f"{prefix}ForearmSh", [(5.0, 5.5), (fa_len * 0.42, 6.2), (fa_len - 8.0, 3.8)], 3.0, CORE_SHADOW, 2.8))
    out.append(smooth_shape(i3, f"{prefix}ForearmShape", fa_pts, skin_fill(prefix + "FA", -11, 11, skin)))
    out.append(f"{i2}</Node>")

    # 4. Upper Arm with Highlighted Biceps Brachii & Sculpted Triceps
    out.append(
        f'{i2}<Node x="{f(p0[sh_key][0])}" y="{f(p0[sh_key][1])}" '
        f'rotation="{f(p0[ua_ang_key])}" scaleX="{f(p0[ua_sc_key])}" name="{prefix}UpperArmNode" id="{ua_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}BicepsPeakHi", [(16.0, 6.8), (ua_len * 0.56, 7.5)], 2.2, HIGHLIGHT, 2.0))
    out.append(smooth_shape(i3, f"{prefix}BicepsBrachii", biceps_pts, muscle_paint_fn(prefix + "Biceps", biceps_t, 0.96)))
    out.append(stroke_shape(i3, f"{prefix}TricepsGroove", [(15.0, -3.2), (ua_len - 8.0, -2.0)], 1.3, CORE_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}UpperArmHi", [(15.0, -6.8), (ua_len * 0.55, -7.2), (ua_len - 8.0, -4.5)], 2.8, HIGHLIGHT, 2.6))
    out.append(smooth_shape(i3, f"{prefix}UpperArmShape", ua_pts, skin_fill(prefix + "UA", -13, 13, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{indent}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 3. 35-Degree Hinged Torso, Full Back Target Muscles & Head
def build_hinged_torso_and_head(indent):
    """Builds the 3/4 dorso-lateral hinged torso (origin at hip_near = `(368, 154)`), highlighting:
      - Latissimus Dorsi (Primary — sweeping dorsal wing from thoracolumbar fascia to humerus)
      - Middle & Lower Trapezius + Rhomboids (Primary — diamond interscapular fan on upper back)
      - Teres Major & Infraspinatus (Synergists — thick scapular/axillary bellies behind shoulder)
      - Sculpted Serratus anterior, Obliques, Compression Shorts & Volumetric 3/4 Head."""
    i2 = indent + "    "
    torso_id = nid()
    key_double(torso_id, 13, lambda p: p["torso_x"])
    key_double(torso_id, 14, lambda p: p["torso_y"])
    key_double(torso_id, 15, lambda p: p["torso_rot"])
    p0 = POSES[0]

    def lats_t(p):
        return 0.48 + 0.52 * (p["r"] ** 0.72)

    def traps_t(p):
        return 0.46 + 0.52 * (p["r"] ** 0.74)

    def teres_infra_t(p):
        return 0.44 + 0.52 * (p["r"] ** 0.76)

    torso_pts = [
        (-134.0, -48.0),  # Left neck / clavicle base
        (-96.0, -68.0),   # Right (far) shoulder / upper trap ridge
        (-52.0, -56.0),   # Mid-thoracic dorsal contour
        (-14.0, -34.0),   # Thoracolumbar fascia contour
        (16.0, -18.0),    # Iliac crest / upper glute border
        (8.0, 20.0),      # Lower hip / inguinal crease
        (-36.0, 14.0),    # Lower abdominal / oblique line
        (-78.0, 12.0),    # Ribcage / serratus lower border
        (-116.0, -2.0),   # Pectoral / axillary lower border
        (-136.0, -26.0),  # Anterior shoulder / neck junction
    ]

    # Target Muscle #1: Latissimus Dorsi (broad sweeping V-taper fan across the mid/lower lateral back)
    lat_pts = [
        (-96.0, -24.0),   # Axillary / humeral insertion beneath teres major
        (-56.0, -42.0),   # Upper-medial border beneath lower trapezius
        (-8.0, -28.0),    # Thoracolumbar fascia / iliac origin
        (-10.0, 4.0),     # Posterior oblique border
        (-58.0, 5.0),     # Lateral costal sweep over serratus
        (-98.0, -8.0),    # Axillary fold
    ]

    # Target Muscle #2: Middle & Lower Trapezius + Rhomboids (interscapular fan on upper thoracic back)
    traps_rhomboids_pts = [
        (-136.0, -48.0),  # C7 apex
        (-102.0, -66.0),  # Upper-right scapular border
        (-66.0, -56.0),   # Mid-thoracic T6-T10 ridge
        (-44.0, -41.0),   # Lower trapezius apex
        (-86.0, -37.0),   # Medial scapular border
        (-116.0, -34.0),  # Left acromion root
    ]

    # Target Muscle #3: Near (Left) Teres Major & Infraspinatus (thick pulling cuff behind left shoulder)
    infra_teres_near_pts = [
        (-112.0, -38.0),
        (-82.0, -40.0),
        (-72.0, -22.0),
        (-96.0, -12.0),
        (-114.0, -22.0),
    ]
    infra_teres_far_pts = [
        (-102.0, -64.0),
        (-74.0, -58.0),
        (-66.0, -46.0),
        (-92.0, -48.0),
    ]

    neck_pts = [
        (-128.0, -50.0), (-154.0, -62.0), (-162.0, -42.0),
        (-146.0, -24.0), (-124.0, -28.0),
    ]
    skull_pts = [
        (-152.0, -76.0), (-176.0, -82.0), (-196.0, -72.0),
        (-202.0, -52.0), (-196.0, -34.0), (-186.0, -24.0),
        (-170.0, -24.0), (-156.0, -34.0), (-148.0, -56.0),
    ]
    hair_pts = [
        (-150.0, -56.0), (-148.0, -74.0), (-168.0, -83.0),
        (-192.0, -76.0), (-201.0, -58.0), (-192.0, -52.0),
        (-176.0, -56.0), (-164.0, -48.0),
    ]
    ear_pts = [
        (-168.0, -52.0), (-162.0, -54.0), (-159.0, -44.0),
        (-164.0, -38.0), (-170.0, -42.0),
    ]

    out = [
        f'{indent}<Node x="{f(p0["torso_x"])}" y="{f(p0["torso_y"])}" '
        f'rotation="{f(p0["torso_rot"])}" name="HingedTorsoRoot" id="{torso_id}">'
    ]

    # 1. Head & Neck (Topmost on Torso)
    out.append(smooth_shape(i2, "LeftEar", ear_pts, skin_fill("Ear", -55, -38, SKIN)))
    out.append(stroke_shape(i2, "EarInner", [(-165.0, -50.0), (-163.0, -43.0)], 1.0, CORE_SHADOW, 0.2))
    out.append(smooth_shape(i2, "CroppedHair", hair_pts, skin_fill("Hair", -84, -46, SHORTS)))
    out.append(stroke_shape(i2, "BrowRidge", [(-197.0, -44.0), (-188.0, -42.0)], 1.4, CORE_SHADOW, 0.2))
    out.append(stroke_shape(i2, "EyeDark", [(-193.0, -39.0), (-188.0, -38.5)], 1.6, "FF334155", 0.2))
    out.append(stroke_shape(i2, "NoseBridge", [(-199.0, -42.0), (-198.0, -31.0), (-192.0, -30.0)], 1.2, SOFT_SHADOW, 0.3))
    out.append(stroke_shape(i2, "JawShadow", [(-186.0, -25.0), (-168.0, -26.0), (-158.0, -35.0)], 1.8, CORE_SHADOW, 1.2))
    out.append(stroke_shape(i2, "SkullHi", [(-188.0, -68.0), (-166.0, -66.0)], 3.0, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i2, "HeadSkull", skull_pts, skin_fill("Skull", -82, -24, SKIN)))

    out.append(stroke_shape(i2, "SCMHighlight", [(-154.0, -48.0), (-130.0, -34.0)], 2.2, HIGHLIGHT, 1.8))
    out.append(stroke_shape(i2, "NeckCrease", [(-152.0, -42.0), (-128.0, -30.0)], 1.3, SOFT_SHADOW, 0.7))
    out.append(smooth_shape(i2, "MuscularNeck", neck_pts, skin_fill("Neck", -62, -24, SKIN)))

    # 2. Highlighted Back Muscles: Middle/Lower Trapezius + Rhomboids, Teres Major/Infraspinatus, and Latissimus Dorsi
    out.append(stroke_shape(i2, "ThoracicSpineGroove", [(-132.0, -50.0), (-92.0, -54.0), (-50.0, -44.0)], 1.4, "997C2D12", 0.5))
    out.append(stroke_shape(i2, "TrapsFiber1", [(-118.0, -44.0), (-86.0, -52.0)], 1.1, HIGHLIGHT, 1.2))
    out.append(stroke_shape(i2, "TrapsFiber2", [(-104.0, -38.0), (-68.0, -48.0)], 1.1, HIGHLIGHT, 1.2))
    out.append(smooth_shape(i2, "MiddleLowerTrapeziusRhomboids", traps_rhomboids_pts, muscle_paint_fn("TrapsRhomboids", traps_t, 0.95)))

    out.append(stroke_shape(i2, "InfraNearHi", [(-104.0, -30.0), (-80.0, -28.0)], 2.0, HIGHLIGHT, 1.8))
    out.append(stroke_shape(i2, "TeresMajorSep", [(-106.0, -22.0), (-76.0, -20.0)], 1.25, "997C2D12", 0.4))
    out.append(smooth_shape(i2, "NearTeresMajorInfraspinatus", infra_teres_near_pts, muscle_paint_fn("InfraTeresNear", teres_infra_t, 0.98)))
    out.append(smooth_shape(i2, "FarTeresMajorInfraspinatus", infra_teres_far_pts, muscle_paint_fn("InfraTeresFar", teres_infra_t, 0.90)))

    # 3. Pelvis/Glute Compression Shorts & Activated Latissimus Dorsi Wing
    pelvis_shorts_pts = [
        (-16.0, -34.0),
        (14.0, -32.0),
        (34.0, -14.0),
        (30.0, 14.0),
        (-4.0, 32.0),
        (-28.0, 14.0),
    ]
    out.append(stroke_shape(i2, "ShortsWaistbandSeam", [(-14.0, -31.0), (-20.0, -8.0), (-25.0, 12.0)], 1.6, CORE_SHADOW, 0.5))
    out.append(stroke_shape(i2, "PelvisGluteHi", [(2.0, -20.0), (22.0, -8.0), (16.0, 10.0)], 4.0, "26FFFFFF", 3.5))
    out.append(smooth_shape(i2, "PelvisGluteShorts", pelvis_shorts_pts, skin_fill("PelvisShorts", -34, 32, SHORTS, -28, 34)))

    # Latissimus Dorsi striations & glowing muscle belly
    out.append(stroke_shape(i2, "LatFiber1", [(-88.0, -16.0), (-52.0, -26.0), (-20.0, -18.0)], 1.15, "807F1D1D", 0.4))
    out.append(stroke_shape(i2, "LatFiber2", [(-84.0, -6.0), (-48.0, -12.0), (-18.0, -6.0)], 1.15, "807F1D1D", 0.4))
    out.append(stroke_shape(i2, "LatHi", [(-78.0, -22.0), (-34.0, -26.0)], 3.0, HIGHLIGHT, 2.8))
    out.append(smooth_shape(i2, "LatissimusDorsi", lat_pts, muscle_paint_fn("Lats", lats_t, 1.05)))

    out.append(stroke_shape(i2, "SerratusDig1", [(-94.0, -4.0), (-80.0, -1.0)], 1.25, CORE_SHADOW, 0.6))
    out.append(stroke_shape(i2, "SerratusDig2", [(-86.0, 2.0), (-70.0, 5.0)], 1.25, CORE_SHADOW, 0.6))
    out.append(stroke_shape(i2, "ObliqueDivision", [(-56.0, 2.0), (-26.0, 10.0)], 1.35, CORE_SHADOW, 0.8))
    out.append(smooth_shape(i2, "TorsoBase", torso_pts, skin_fill("Torso", -68, 20, SKIN)))

    out.append(f"{indent}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 4. Straddled Bent-Over Athletic Legs & Compression Shorts
def build_bent_over_leg(indent, prefix, is_far=False):
    """Builds the Near (Left) or Far (Right) leg in a straddled bent-over hip-hinge stance facing left (-X)."""
    i2 = indent + "    "
    i3 = i2 + "    "
    skin = SKIN_FAR if is_far else SKIN
    shorts = SHORTS_FAR if is_far else SHORTS
    l_thigh = THIGH_FAR_LEN if is_far else THIGH_NEAR_LEN
    l_shin = SHIN_FAR_LEN if is_far else SHIN_NEAR_LEN

    hip_key = "hip_far" if is_far else "hip_near"
    knee_key = "knee_far" if is_far else "knee_near"
    ankle_pt = ANKLE_FAR if is_far else ANKLE_NEAR
    thigh_ang_key = "thigh_far_ang" if is_far else "thigh_near_ang"
    thigh_sc_key = "thigh_far_sc" if is_far else "thigh_near_sc"
    shin_ang_key = "shin_far_ang" if is_far else "shin_near_ang"
    shin_sc_key = "shin_far_sc" if is_far else "shin_near_sc"

    thigh_id, shin_id = nid(), nid()
    key_double(thigh_id, 13, lambda p: p[hip_key][0])
    key_double(thigh_id, 14, lambda p: p[hip_key][1])
    key_double(thigh_id, 15, lambda p: p[thigh_ang_key])
    key_double(thigh_id, 16, lambda p: p[thigh_sc_key])

    key_double(shin_id, 13, lambda p: p[knee_key][0])
    key_double(shin_id, 14, lambda p: p[knee_key][1])
    key_double(shin_id, 15, lambda p: p[shin_ang_key])
    key_double(shin_id, 16, lambda p: p[shin_sc_key])
    p0 = POSES[0]

    thigh_pts = [
        (-22.0, -24.0),
        (12.0, -24.0),
        (46.0, -18.5),
        (74.0, -12.5),
        (l_thigh + 4.0, -6.5),
        (l_thigh + 4.0, 8.5),
        (72.0, 15.5),
        (38.0, 19.5),
        (6.0, 18.5),
        (-18.0, 10.0),
    ]
    shorts_pts = [
        (-23.0, -24.5),
        (14.0, -24.5),
        (42.0, -19.2),
        (38.0, 19.8),
        (4.0, 19.0),
        (-19.0, 10.5),
    ]

    shin_pts = [
        (-6.0, -9.0),
        (18.0, -17.5),
        (42.0, -14.0),
        (l_shin, -5.8),
        (l_shin + 4.0, 0.0),
        (l_shin, 6.2),
        (42.0, 8.5),
        (14.0, 9.5),
        (-6.0, 8.0),
    ]

    ax, ay = ankle_pt
    foot_pts = [
        (ax + 12.0, ay - 2.0),
        (ax + 14.0, ay + 9.5),
        (ax - 8.0, ay + 11.5),
        (ax - 34.0, ay + 11.5),
        (ax - 38.0, ay + 6.5),
        (ax - 22.0, ay + 0.5),
        (ax - 4.0, ay - 4.5),
    ]

    out = [f'{indent}<Node name="{prefix}LegGroup">']

    # 1. Thigh + Compression Shorts
    out.append(
        f'{i2}<Node x="{f(p0[hip_key][0])}" y="{f(p0[hip_key][1])}" '
        f'rotation="{f(p0[thigh_ang_key])}" scaleX="{f(p0[thigh_sc_key])}" name="{prefix}ThighNode" id="{thigh_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}GluteSeam", [(-16.0, -18.0), (12.0, -14.0), (34.0, 2.0)], 1.4, SOFT_SHADOW, 0.6))
    out.append(stroke_shape(i3, f"{prefix}GluteHi", [(-14.0, -14.0), (18.0, -12.0)], 3.4, "26FFFFFF", 3.2))
    out.append(smooth_shape(i3, f"{prefix}CompressionShorts", shorts_pts, skin_fill(prefix + "Shorts", -25, 20, shorts)))
    out.append(stroke_shape(i3, f"{prefix}VastusGroove", [(40.0, 2.5), (l_thigh - 8.0, 1.5)], 1.4, CORE_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}HamstringGroove", [(42.0, -8.5), (l_thigh - 10.0, -5.0)], 1.25, SOFT_SHADOW, 0.7))
    out.append(stroke_shape(i3, f"{prefix}QuadHi", [(40.0, 9.5), (l_thigh - 8.0, 6.5)], 3.2, HIGHLIGHT, 3.0))
    out.append(smooth_shape(i3, f"{prefix}ThighShape", thigh_pts, skin_fill(prefix + "Thigh", -24, 20, skin)))
    out.append(f"{i2}</Node>")

    # 2. Planted Bare Foot on Floor
    if not is_far:
        out.append(stroke_shape(i2, f"{prefix}ToeLine1", [(ax - 24.0, ay + 6.5), (ax - 35.0, ay + 8.0)], 0.95, SOFT_SHADOW, 0.2))
        out.append(stroke_shape(i2, f"{prefix}ToeLine2", [(ax - 22.0, ay + 8.5), (ax - 33.0, ay + 10.0)], 0.95, SOFT_SHADOW, 0.2))
    out.append(stroke_shape(i2, f"{prefix}FootInstepHi", [(ax - 4.0, ay - 1.0), (ax - 26.0, ay + 4.5)], 2.2, HIGHLIGHT, 2.0))
    out.append(smooth_shape(i2, f"{prefix}PlantedFoot", foot_pts, skin_fill(prefix + "Foot", ay - 5, ay + 12, skin)))

    # 3. Shin & Sculpted Gastrocnemius/Soleus Calf
    out.append(
        f'{i2}<Node x="{f(p0[knee_key][0])}" y="{f(p0[knee_key][1])}" '
        f'rotation="{f(p0[shin_ang_key])}" scaleX="{f(p0[shin_sc_key])}" name="{prefix}ShinNode" id="{shin_id}">'
    )
    out.append(stroke_shape(i3, f"{prefix}GastrocGroove", [(10.0, -5.0), (42.0, -4.0), (l_shin - 8.0, -1.5)], 1.3, CORE_SHADOW, 0.8))
    out.append(stroke_shape(i3, f"{prefix}ShinHi", [(8.0, 3.5), (l_shin - 8.0, 2.5)], 2.6, HIGHLIGHT, 2.5))
    out.append(stroke_shape(i3, f"{prefix}CalfHi", [(12.0, -11.5), (36.0, -9.5)], 2.4, HIGHLIGHT, 2.2))
    out.append(smooth_shape(i3, f"{prefix}ShinShape", shin_pts, skin_fill(prefix + "Shin", -18, 10, skin)))
    out.append(f"{i2}</Node>")

    out.append(f"{indent}</Node>")
    return "\n".join(out)


# ---------------------------------------------------------------- 5. Scene Assembly & Verbatim Rive 7.3 Compiler
def build_rml():
    shd_id = nid()
    key_double(shd_id, 16, lambda p: p["shd_sx"])
    p0 = POSES[0]

    near_arm_xml = build_tbar_row_arm("        ", "Near", is_far=False)
    torso_xml = build_hinged_torso_and_head("        ")
    landmine_front_xml = build_landmine_front_plates_and_vgrip("        ")
    near_leg_xml = build_bent_over_leg("        ", "Near", is_far=False)
    landmine_rear_xml = build_landmine_rear_shaft_and_pivot("        ")
    far_leg_xml = build_bent_over_leg("        ", "Far", is_far=True)
    far_arm_xml = build_tbar_row_arm("        ", "Far", is_far=True)

    by_obj = {}
    for oid, kp_xml in KEYED:
        by_obj.setdefault(oid, []).append(kp_xml)
    keyed_objects_xml = "\n".join(
        f'        <KeyedObject objectId="{oid}">\n' + "\n".join(kps) + "\n        </KeyedObject>"
        for oid, kps in by_obj.items()
    )

    band_h = H - FLOOR
    band_fill = '<Fill name="FloorBandFill">' + grad("FloorBandGrad", 0, -band_h / 2, 0, band_h / 2, "FF172033", "FF0B1120") + "</Fill>"

    return f"""<Rive version="7.3">
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="TBarRow" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. Foreground: Near (Left) Rowing Arm, Posterior Deltoid, Biceps & Brachioradialis -->
{near_arm_xml}

        <!-- 2. 35-Degree Hinged Torso, Highlighted Lats / Traps / Rhomboids / Teres Major & 3/4 Head -->
{torso_xml}

        <!-- 3. Front Landmine T-Bar Assembly (3 Stepped Olympic Weight Plates & Close V-Grip Handle) -->
{landmine_front_xml}

        <!-- 4. Near (Left) Straddled Leg, Compression Shorts & Planted Foot -->
{near_leg_xml}

        <!-- 5. Rear Landmine Barbell Shaft & Floor Pivot Anchor at (420, 296) (straddled between legs) -->
{landmine_rear_xml}

        <!-- 6. Far (Right) Straddled Leg in 3/4 Depth -->
{far_leg_xml}

        <!-- 7. Far (Right) Rowing Arm -->
{far_arm_xml}

        <!-- 8. Studio Floor Shadow & Ambient Backdrop -->
        <Shape x="315" y="{f(FLOOR - 2)}" scaleX="{f(p0['shd_sx'])}" scaleY="0.11" name="AthleteShadow" id="{shd_id}">
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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="TBarRow" id="0:60">
{keyed_objects_xml}
        </LinearAnimation>
    </Artboard>
</Rive>
"""


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
    (BUILD / "tbar_row.riv").write_bytes(riv_bytes)
    ASSET_RIV.write_bytes(riv_bytes)

    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/4e7c145c-8979-4261-8c65-b2223a6aa784/scratch")
    sys.path.insert(0, "/Users/jorgegomes/.gemini/antigravity/brain/760234ee-c5d7-4c8b-8560-779749a55462/scratch")
    from render_rml import downsample_box, render_buffer, write_png  # type: ignore

    for fr, tag in ((0, "frame_start"), (38, "frame_mid"), (72, "frame_peak")):
        rw, rh, buf = render_buffer(OUT, fr, scale=2)
        rgb640 = downsample_box(rw, rh, buf, 640, 360)
        write_png(BUILD / f"{tag}.png", 640, 360, rgb640)
        if tag == "frame_peak":
            thumb_rgb = downsample_box(rw, rh, buf, 256, 256, crop=(720, 0, 220))
            write_png(ASSET_THUMB, 256, 256, thumb_rgb)

    print(f"Published {ASSET_RIV} ({len(riv_bytes):,} bytes) + {ASSET_THUMB}")


if __name__ == "__main__":
    OUT.write_text(build_rml(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes, {_id} keyed objects)")
    if "--publish" in sys.argv:
        publish()
