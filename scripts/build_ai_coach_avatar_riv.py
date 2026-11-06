#!/usr/bin/env python3
"""Build the 60 FPS 3D Biomech Gyro-Core Rive 7.3 Avatar (ai_coach_avatar.riv).

Visual Design Specification ("Biomech Gyro-Core" 3D Avatar — 360x360 1:1 Artboard):
  - Artboard: 360x360 (1:1 square for circular/rounded avatar containers from 36px to 140px)
  - Animation: 60 FPS, 360 frames (6.0s seamless loop)
  - Palette: CommunityFitness Dark Obsidian (#0A0D12, #111722, #1C2536),
    Neon Lime (#CCFF00, #EAFF80), and Telemetry Cyan (#00E5FF, #80F2FF)
  - Layers (front-to-back in Rive 7.3 draw order):
    1. Foreground 3D Orbital Nodes (4 Neon Lime + 4 Electric Cyan nodes orbiting in 3D perspective)
    2. Central Biomechanical Hex-Core, 3D Isometric Double-Plate Dumbbell & 5-Bar Biometric Equalizer
    3. Inner High-Energy Gimbal Ring (#CCFF00 / #00E5FF fast harmonic oscillation behind hex core)
    4. Middle 3D Telemetry Ring (#00E5FF + #80F2FF orthogonal counter-rotation + telemetry ticks)
    5. Outer 3D Gyroscope Ring (#CCFF00 + #EAFF80 3D precession + precision degree ticks)
    6. Expanding Neural Pulse Halos (concentric pulsing energy waves)
    7. Deep Obsidian-Titanium Circular Chassis (#0A0D12 aura, #111722 sphere, #1C2536 specular rim)

Run:
    python3 scripts/build_ai_coach_avatar_riv.py
"""
import math
import pathlib
import struct
import xml.etree.ElementTree as ET
import zlib

REPO = pathlib.Path(__file__).resolve().parent.parent
RML_OUT = pathlib.Path("/tmp/ai_coach_avatar.rml")
SHEET_OUT = pathlib.Path("/tmp/ai_coach_avatar_sheet.png")
SCRATCH_SHEET_OUT = pathlib.Path(
    "/Users/jorgegomes/.gemini/antigravity/brain/2bdf813a-ab3c-4cde-afd7-5c06283dd719/scratch/ai_coach_avatar_sheet.png"
)
ASSET_RIV = REPO / "assets/animations/ai_coach_avatar.riv"
ASSET_THUMB = REPO / "assets/animations/thumbnails/ai_coach_avatar.png"

W, H = 360, 360
CX, CY = 180.0, 180.0
FPS = 60
DURATION = 360  # 6.0s @ 60fps seamless 3D harmonic loop
STEP = 4        # 91 keyframes (0, 4, ..., 360) for smooth 60 FPS linear interpolation
FRAMES = list(range(0, DURATION + 1, STEP))

# 3D Perspective Camera Distance
CAM_DIST = 520.0

# Radii of the 3D Gyroscope Rings
R_OUTER = 140.0
R_MID = 110.0
R_INNER = 82.0


def f(v):
    if isinstance(v, float):
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(v)


def lerp(a, b, t):
    return a + (b - a) * t


def argb_lerp(c0, c1, t):
    t = max(0.0, min(1.0, t))
    return "".join(f"{round(lerp(a, b, t)):02X}" for a, b in zip(c0, c1))


def rot3d_ring_point(radius, local_ang, psi, theta, phi):
    """Compute exact 3D coordinates (X, Y, Z) of a point on a spinning, tilted, precessing 3D ring."""
    ang = local_ang + psi
    xl = radius * math.cos(ang)
    yl = radius * math.sin(ang)
    yt = yl * math.cos(theta)
    zt = yl * math.sin(theta)
    cs, sn = math.cos(phi), math.sin(phi)
    x_scr = xl * cs - yt * sn
    y_scr = xl * sn + yt * cs
    return x_scr, y_scr, zt


def project_3d(x3, y3, z3):
    """Perspective projection from 3D (x3, y3, z3) around center (CX, CY) to screen (sx, sy, scale, depth_t)."""
    persp = CAM_DIST / max(120.0, CAM_DIST - z3)
    sx = CX + x3 * persp
    sy = CY + y3 * persp
    depth_t = max(0.0, min(1.0, 0.5 + z3 / (2.0 * R_OUTER)))
    return sx, sy, persp, depth_t


def compute_frame_state(frame):
    """Compute all 3D gyroscope transforms, orbital node coordinates, core pulse, and equalizer bars."""
    u = (frame % DURATION) / float(DURATION)
    tau = 2.0 * math.pi * u

    # 1. Outer 3D Gyroscope Ring (Neon Lime #CCFF00):
    # Precesses +360 deg (1x), tilts smoothly in 3D (sy in 0.56..0.82 so it frames the hex core cleanly), spins +720 deg
    phi_outer = -0.45 + tau
    theta_outer = 0.78 + 0.18 * math.sin(2.0 * tau)
    psi_outer = 2.0 * tau
    sy_outer = math.cos(theta_outer)

    # 2. Middle 3D Telemetry Ring (Electric Cyan #00E5FF):
    # Counter-precesses -360 deg (-1x) on orthogonal axis, tilts (sy in 0.60..0.85), counter-spins -720 deg
    phi_mid = 1.12 - tau
    theta_mid = 0.74 + 0.17 * math.cos(2.0 * tau)
    psi_mid = -2.0 * tau + 0.35
    sy_mid = math.cos(theta_mid)

    # 3. Inner High-Energy Gimbal Ring (Hybrid #CCFF00 / #00E5FF):
    # Fast harmonic oscillation behind and around the hex core: precesses +720 deg (2x), spins -1080 deg (-3x)
    phi_inner = 0.52 + 2.0 * tau
    theta_inner = 0.88 + 0.22 * math.sin(3.0 * tau + 0.5)
    psi_inner = -3.0 * tau
    sy_inner = math.cos(theta_inner)

    # 4. Outer 3D Orbital Nodes (4 nodes at 0, 90, 180, 270 deg on Outer Ring)
    outer_nodes = []
    for k in range(4):
        lang = k * (math.pi / 2.0) + 0.28
        x3, y3, z3 = rot3d_ring_point(R_OUTER, lang, psi_outer, theta_outer, phi_outer)
        sx, sy, persp, dt = project_3d(x3, y3, z3)
        sc = (0.76 + 0.52 * dt) * persp
        outer_nodes.append((sx, sy, sc, dt))

    # 5. Middle 3D Telemetry Data Nodes (4 nodes at 45, 135, 225, 315 deg on Middle Ring)
    mid_nodes = []
    for k in range(4):
        lang = k * (math.pi / 2.0) + (math.pi / 4.0)
        x3, y3, z3 = rot3d_ring_point(R_MID, lang, psi_mid, theta_mid, phi_mid)
        sx, sy, persp, dt = project_3d(x3, y3, z3)
        sc = (0.78 + 0.50 * dt) * persp
        mid_nodes.append((sx, sy, sc, dt))

    # 6. Central Biomechanical Hex-Core & 3D Isometric Dumbbell Levitation/Breathing
    core_bob_y = CY + 3.0 * math.sin(2.0 * tau)
    core_rot = 0.05 * math.sin(tau)
    core_scale = 1.0 + 0.045 * math.sin(3.0 * tau)

    # 3D Dumbbell Isometric Parallax (left & right weight plates shift in 3D depth)
    db_tilt = math.sin(2.0 * tau)
    db_left_x = -23.5 + 2.4 * math.cos(2.0 * tau)
    db_left_y = -8.0 + 2.0 * db_tilt
    db_left_sc = 1.0 + 0.075 * db_tilt

    db_right_x = 23.5 - 2.4 * math.cos(2.0 * tau)
    db_right_y = -8.0 - 2.0 * db_tilt
    db_right_sc = 1.0 - 0.075 * db_tilt

    # Neural Core Orb Pulse (3 cycles per loop)
    orb_pulse = 0.5 + 0.5 * math.sin(3.0 * tau)
    orb_scale = 0.90 + 0.28 * orb_pulse

    # 7. 5-Bar Acoustic / Biometric Equalizer Waveforms (symmetric multi-harmonic sin waves)
    eq_bars = [
        0.48 + 0.62 * (0.5 + 0.5 * math.sin(3.0 * tau + 1.8)),  # Outer Left (-22)
        0.54 + 0.72 * (0.5 + 0.5 * math.sin(4.0 * tau + 0.7)),  # Inner Left (-11)
        0.60 + 0.85 * (0.5 + 0.5 * math.sin(5.0 * tau)),        # Center (0)
        0.54 + 0.72 * (0.5 + 0.5 * math.sin(4.0 * tau + 0.7)),  # Inner Right (+11)
        0.48 + 0.62 * (0.5 + 0.5 * math.sin(3.0 * tau + 1.8)),  # Outer Right (+22)
    ]

    # 8. Expanding Neural Pulse Halos (2 staggered concentric waves, 2 cycles per 360f)
    halo1_phase = (2.0 * u) % 1.0
    halo2_phase = (2.0 * u + 0.5) % 1.0
    halo1_scale = 0.52 + 0.62 * halo1_phase
    halo2_scale = 0.52 + 0.62 * halo2_phase
    halo1_alpha = math.sin(math.pi * halo1_phase) ** 1.25
    halo2_alpha = math.sin(math.pi * halo2_phase) ** 1.25

    return {
        "phi_outer": phi_outer,
        "sy_outer": sy_outer,
        "psi_outer": psi_outer,
        "phi_mid": phi_mid,
        "sy_mid": sy_mid,
        "psi_mid": psi_mid,
        "phi_inner": phi_inner,
        "sy_inner": sy_inner,
        "psi_inner": psi_inner,
        "outer_nodes": outer_nodes,
        "mid_nodes": mid_nodes,
        "core_bob_y": core_bob_y,
        "core_rot": core_rot,
        "core_scale": core_scale,
        "db_left_x": db_left_x,
        "db_left_y": db_left_y,
        "db_left_sc": db_left_sc,
        "db_right_x": db_right_x,
        "db_right_y": db_right_y,
        "db_right_sc": db_right_sc,
        "orb_pulse": orb_pulse,
        "orb_scale": orb_scale,
        "eq_bars": eq_bars,
        "halo1_scale": halo1_scale,
        "halo2_scale": halo2_scale,
        "halo1_alpha": halo1_alpha,
        "halo2_alpha": halo2_alpha,
    }


STATES = {fr: compute_frame_state(fr) for fr in FRAMES}

_id = 100
KEYED = []


def nid():
    global _id
    _id += 1
    return f"0:{_id}"


def key_double(oid, pkey, fn):
    kfs = "\n".join(
        f'                <KeyFrameDouble frame="{fr}" value="{f(fn(STATES[fr]))}" interpolationType="linear"/>'
        for fr in FRAMES
    )
    KEYED.append((oid, f'            <KeyedProperty propertyKey="{pkey}">\n{kfs}\n            </KeyedProperty>'))


def key_color(oid, pkey, fn):
    kfs = "\n".join(
        f'                <KeyFrameColor frame="{fr}" value="{fn(STATES[fr])}" interpolationType="linear"/>'
        for fr in FRAMES
    )
    KEYED.append((oid, f'            <KeyedProperty propertyKey="{pkey}">\n{kfs}\n            </KeyedProperty>'))


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


def straight_vertices(pts, radius=0.0, indent="            "):
    r_attr = f' radius="{f(float(radius))}"' if radius > 0 else ""
    return "\n".join(
        f'{indent}<StraightVertex x="{f(float(x))}" y="{f(float(y))}"{r_attr}/>'
        for x, y in pts
    )


def arc_pts(radius, a0_deg, a1_deg, steps=16):
    a0 = math.radians(a0_deg)
    a1 = math.radians(a1_deg)
    return [
        (radius * math.cos(lerp(a0, a1, i / steps)), radius * math.sin(lerp(a0, a1, i / steps)))
        for i in range(steps + 1)
    ]


def reg_polygon_pts(radius, sides=6, rot_deg=-90.0):
    rot = math.radians(rot_deg)
    return [
        (
            radius * math.cos(rot + 2.0 * math.pi * i / sides),
            radius * math.sin(rot + 2.0 * math.pi * i / sides),
        )
        for i in range(sides)
    ]


def grad2(name, x0, y0, x1, y1, c0, c1):
    return (
        f'<LinearGradient startX="{f(float(x0))}" startY="{f(float(y0))}" '
        f'endX="{f(float(x1))}" endY="{f(float(y1))}" name="{name}">'
        f'<GradientStop colorValue="{c0}" position="0"/>'
        f'<GradientStop colorValue="{c1}" position="1"/></LinearGradient>'
    )


def grad3(name, x0, y0, x1, y1, c0, c1, c2):
    return (
        f'<LinearGradient startX="{f(float(x0))}" startY="{f(float(y0))}" '
        f'endX="{f(float(x1))}" endY="{f(float(y1))}" name="{name}">'
        f'<GradientStop colorValue="{c0}" position="0"/>'
        f'<GradientStop colorValue="{c1}" position="0.5"/>'
        f'<GradientStop colorValue="{c2}" position="1"/></LinearGradient>'
    )


def rad_grad3(name, sx, sy, ex, ey, c0, c1, c2, p1=0.55):
    return (
        f'<RadialGradient startX="{f(float(sx))}" startY="{f(float(sy))}" '
        f'endX="{f(float(ex))}" endY="{f(float(ey))}" name="{name}">'
        f'<GradientStop colorValue="{c0}" position="0"/>'
        f'<GradientStop colorValue="{c1}" position="{f(float(p1))}"/>'
        f'<GradientStop colorValue="{c2}" position="1"/></RadialGradient>'
    )


def stroke_arc(
    indent, name, radius, a0_deg, a1_deg, width, color, feather=0.0, steps=16, cap="round", cid=None, x=0.0, y=0.0
):
    pts = arc_pts(radius, a0_deg, a1_deg, steps=steps)
    f_xml = f'<Feather strength="{f(float(feather))}" name="{name}Feather"/>' if feather > 0 else ""
    id_attr = f' id="{cid}"' if cid else ""
    pos_attr = f' x="{f(float(x))}" y="{f(float(y))}"' if (x or y) else ""
    return (
        f'{indent}<Shape{pos_attr} name="{name}">\n'
        f'{indent}    <PointsPath isClosed="false" name="{name}Path">\n'
        f"{smooth_vertices(pts, False, indent + '        ')}\n"
        f"{indent}    </PointsPath>\n"
        f'{indent}    <Stroke thickness="{f(float(width))}" cap="{cap}" join="round" name="{name}Stroke">'
        f'<SolidColor colorValue="{color}" name="{name}Col"{id_attr}/>{f_xml}</Stroke>\n'
        f"{indent}</Shape>"
    )


def stroke_line(indent, name, p0, p1, width, color, feather=0.0, cap="round"):
    f_xml = f'<Feather strength="{f(float(feather))}" name="{name}Feather"/>' if feather > 0 else ""
    return (
        f'{indent}<Shape name="{name}">\n'
        f'{indent}    <PointsPath isClosed="false" name="{name}Path">\n'
        f"{straight_vertices([p0, p1], 0.0, indent + '        ')}\n"
        f"{indent}    </PointsPath>\n"
        f'{indent}    <Stroke thickness="{f(float(width))}" cap="{cap}" join="round" name="{name}Stroke">'
        f'<SolidColor colorValue="{color}" name="{name}Col"/>{f_xml}</Stroke>\n'
        f"{indent}</Shape>"
    )


def poly_shape(indent, name, pts, paint_xml, radius=3.0, x=0.0, y=0.0):
    pos = f' x="{f(float(x))}" y="{f(float(y))}"' if (x or y) else ""
    return (
        f'{indent}<Shape{pos} name="{name}">\n'
        f'{indent}    <PointsPath isClosed="true" name="{name}Path">\n'
        f"{straight_vertices(pts, radius, indent + '        ')}\n"
        f"{indent}    </PointsPath>\n"
        f"{indent}    {paint_xml}\n"
        f"{indent}</Shape>"
    )


def ellipse_shape(indent, name, x, y, w, h, paint_xml, sid=None, sx=1.0, sy=1.0, rot=0.0):
    id_attr = f' id="{sid}"' if sid else ""
    pos_x = f' x="{f(float(x))}"' if x else ""
    pos_y = f' y="{f(float(y))}"' if y else ""
    rot_attr = f' rotation="{f(float(rot))}"' if rot else ""
    sx_attr = f' scaleX="{f(float(sx))}"' if sx != 1.0 else ""
    sy_attr = f' scaleY="{f(float(sy))}"' if sy != 1.0 else ""
    return (
        f'{indent}<Shape{pos_x}{pos_y}{rot_attr}{sx_attr}{sy_attr} name="{name}"{id_attr}>\n'
        f'{indent}    <Ellipse width="{f(float(w))}" height="{f(float(h))}" name="{name}Ellipse"/>\n'
        f"{indent}    {paint_xml}\n"
        f"{indent}</Shape>"
    )


def build_3d_orbital_nodes():
    """Builds the 4 Neon Lime Outer 3D Orbital Nodes and 4 Electric Cyan Middle 3D Telemetry Nodes."""
    s0 = STATES[0]
    ind = "        "
    i2 = ind + "    "
    out = []

    # 1. Outer Neon Lime 3D Orbital Nodes (#CCFF00 / #EAFF80)
    lime_low = (0x8C, 0x99, 0xCC, 0x00)
    lime_high = (0xFF, 0xEA, 0xFF, 0x80)
    for k in range(4):
        nid_node = nid()
        cid_core = nid()
        x0, y0, sc0, dt0 = s0["outer_nodes"][k]
        key_double(nid_node, 13, lambda st, idx=k: st["outer_nodes"][idx][0])
        key_double(nid_node, 14, lambda st, idx=k: st["outer_nodes"][idx][1])
        key_double(nid_node, 16, lambda st, idx=k: st["outer_nodes"][idx][2])
        key_double(nid_node, 17, lambda st, idx=k: st["outer_nodes"][idx][2])
        key_color(cid_core, 37, lambda st, idx=k: argb_lerp(lime_low, lime_high, st["outer_nodes"][idx][3]))

        c0_hex = argb_lerp(lime_low, lime_high, dt0)
        out.append(
            f'{ind}<Node x="{f(x0)}" y="{f(y0)}" scaleX="{f(sc0)}" scaleY="{f(sc0)}" '
            f'name="OuterOrbitalNode{k}" id="{nid_node}">'
        )
        out.append(
            ellipse_shape(
                i2,
                f"OuterNodeCore{k}",
                0,
                0,
                8.0,
                8.0,
                f'<Fill name="ONCoreFill{k}"><SolidColor colorValue="{c0_hex}" name="ONCoreCol{k}" id="{cid_core}"/></Fill>',
            )
        )
        out.append(
            ellipse_shape(
                i2,
                f"OuterNodeRing{k}",
                0,
                0,
                15.0,
                15.0,
                f'<Fill name="ONRingFill{k}"><SolidColor colorValue="FF111722" name="ONRingBg{k}"/></Fill>'
                f'<Stroke thickness="2.5" name="ONRingStr{k}"><SolidColor colorValue="FFCCFF00" name="ONRingCol{k}"/></Stroke>',
            )
        )
        out.append(
            ellipse_shape(
                i2,
                f"OuterNodeGlow{k}",
                0,
                0,
                22.0,
                22.0,
                f'<Stroke thickness="5.0" name="ONGlowStr{k}"><SolidColor colorValue="66CCFF00" name="ONGlowCol{k}"/>'
                f'<Feather strength="6.5" name="ONGlowFeat{k}"/></Stroke>',
            )
        )
        out.append(f"{ind}</Node>")

    # 2. Middle Electric Cyan 3D Telemetry Nodes (#00E5FF / #80F2FF)
    cyan_low = (0x8C, 0x00, 0x99, 0xB8)
    cyan_high = (0xFF, 0x80, 0xF2, 0xFF)
    for k in range(4):
        nid_node = nid()
        cid_core = nid()
        x0, y0, sc0, dt0 = s0["mid_nodes"][k]
        key_double(nid_node, 13, lambda st, idx=k: st["mid_nodes"][idx][0])
        key_double(nid_node, 14, lambda st, idx=k: st["mid_nodes"][idx][1])
        key_double(nid_node, 16, lambda st, idx=k: st["mid_nodes"][idx][2])
        key_double(nid_node, 17, lambda st, idx=k: st["mid_nodes"][idx][2])
        key_color(cid_core, 37, lambda st, idx=k: argb_lerp(cyan_low, cyan_high, st["mid_nodes"][idx][3]))

        c0_hex = argb_lerp(cyan_low, cyan_high, dt0)
        out.append(
            f'{ind}<Node x="{f(x0)}" y="{f(y0)}" scaleX="{f(sc0)}" scaleY="{f(sc0)}" '
            f'name="MidTelemetryNode{k}" id="{nid_node}">'
        )
        out.append(
            ellipse_shape(
                i2,
                f"MidNodeCore{k}",
                0,
                0,
                7.2,
                7.2,
                f'<Fill name="MNCoreFill{k}"><SolidColor colorValue="{c0_hex}" name="MNCoreCol{k}" id="{cid_core}"/></Fill>',
            )
        )
        out.append(
            ellipse_shape(
                i2,
                f"MidNodeRing{k}",
                0,
                0,
                13.5,
                13.5,
                f'<Fill name="MNRingFill{k}"><SolidColor colorValue="FF111722" name="MNRingBg{k}"/></Fill>'
                f'<Stroke thickness="2.3" name="MNRingStr{k}"><SolidColor colorValue="FF00E5FF" name="MNRingCol{k}"/></Stroke>',
            )
        )
        out.append(
            ellipse_shape(
                i2,
                f"MidNodeGlow{k}",
                0,
                0,
                20.0,
                20.0,
                f'<Stroke thickness="4.5" name="MNGlowStr{k}"><SolidColor colorValue="6600E5FF" name="MNGlowCol{k}"/>'
                f'<Feather strength="6.0" name="MNGlowFeat{k}"/></Stroke>',
            )
        )
        out.append(f"{ind}</Node>")

    return "\n".join(out)


def build_central_biomech_core():
    """Builds the levitating Dark-Chrome Hexagonal Core, 3D Isometric Dumbbell Emblem, and 5-Bar Equalizer."""
    s0 = STATES[0]
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "

    core_id = nid()
    key_double(core_id, 14, lambda st: st["core_bob_y"])
    key_double(core_id, 15, lambda st: st["core_rot"])
    key_double(core_id, 16, lambda st: st["core_scale"])
    key_double(core_id, 17, lambda st: st["core_scale"])

    out = [
        f'{ind}<Node x="{f(CX)}" y="{f(s0["core_bob_y"])}" rotation="{f(s0["core_rot"])}" '
        f'scaleX="{f(s0["core_scale"])}" scaleY="{f(s0["core_scale"])}" '
        f'name="CentralBiomechCoreNode" id="{core_id}">'
    ]

    # ---------------- A. 5-Bar Dynamic Acoustic / Biometric Equalizer (lower chamber y = +24) ----------------
    eq_xs = [-22.0, -11.0, 0.0, 11.0, 22.0]
    eq_base_hs = [13.5, 18.0, 22.5, 18.0, 13.5]
    eq_cols = ["FFCCFF00", "FF00E5FF", "FFEAFF80", "FF00E5FF", "FFCCFF00"]
    eq_glows = ["66CCFF00", "6600E5FF", "80CCFF00", "6600E5FF", "66CCFF00"]

    for idx in range(5):
        bar_id = nid()
        key_double(bar_id, 17, lambda st, bi=idx: st["eq_bars"][bi])
        bx = eq_xs[idx]
        bh = eq_base_hs[idx]
        bcol = eq_cols[idx]
        bglow = eq_glows[idx]
        sy0 = s0["eq_bars"][idx]
        out.append(
            f'{i2}<Node x="{f(bx)}" y="24" scaleY="{f(sy0)}" name="EqBarNode{idx}" id="{bar_id}">\n'
            f'{i3}<Shape name="EqBarCore{idx}">\n'
            f'{i3}    <Rectangle width="5.2" height="{f(bh)}" cornerRadiusTL="2.6" name="EqBarRect{idx}"/>\n'
            f'{i3}    <Fill name="EqBarFill{idx}"><SolidColor colorValue="{bcol}" name="EqBarCol{idx}"/></Fill>\n'
            f'{i3}</Shape>\n'
            f'{i3}<Shape name="EqBarGlow{idx}">\n'
            f'{i3}    <Rectangle width="7.2" height="{f(bh + 2.0)}" cornerRadiusTL="3.6" name="EqBarGlowRect{idx}"/>\n'
            f'{i3}    <Stroke thickness="3.2" name="EqBarGlowStr{idx}"><SolidColor colorValue="{bglow}" name="EqBarGlowCol{idx}"/>'
            f'<Feather strength="3.5" name="EqBarFeat{idx}"/></Stroke>\n'
            f'{i3}</Shape>\n'
            f'{i2}</Node>'
        )

    # ---------------- B. 3D Isometric Dumbbell & Neural Pulse Core (upper/center chamber y = -8) ----------------
    # Central Neural Pulse Orb on the Dumbbell Bridge
    orb_id = nid()
    orb_col_id = nid()
    key_double(orb_id, 16, lambda st: st["orb_scale"])
    key_double(orb_id, 17, lambda st: st["orb_scale"])
    key_color(
        orb_col_id,
        37,
        lambda st: argb_lerp((0xFF, 0x00, 0xE5, 0xFF), (0xFF, 0xEA, 0xFF, 0x80), st["orb_pulse"]),
    )
    orb_c0 = argb_lerp((0xFF, 0x00, 0xE5, 0xFF), (0xFF, 0xEA, 0xFF, 0x80), s0["orb_pulse"])

    out.append(
        f'{i2}<Node x="0" y="-8" scaleX="{f(s0["orb_scale"])}" scaleY="{f(s0["orb_scale"])}" '
        f'name="NeuralPulseOrbNode" id="{orb_id}">'
    )
    out.append(
        ellipse_shape(
            i3,
            "NeuralOrbHotCenter",
            0,
            0,
            7.5,
            7.5,
            '<Fill name="NeuralOrbHotFill"><SolidColor colorValue="FFFFFFFF" name="NeuralOrbHotCol"/></Fill>',
        )
    )
    out.append(
        ellipse_shape(
            i3,
            "NeuralOrbRing",
            0,
            0,
            15.0,
            15.0,
            f'<Fill name="NeuralOrbFill"><SolidColor colorValue="{orb_c0}" name="NeuralOrbCol" id="{orb_col_id}"/></Fill>'
            '<Stroke thickness="2.2" name="NeuralOrbStr"><SolidColor colorValue="FFFFFFFF" name="NeuralOrbStrCol"/></Stroke>',
        )
    )
    out.append(
        ellipse_shape(
            i3,
            "NeuralOrbHalo",
            0,
            0,
            25.0,
            25.0,
            '<Stroke thickness="5.5" name="NeuralOrbHaloStr"><SolidColor colorValue="8000E5FF" name="NeuralOrbHaloCol"/>'
            '<Feather strength="6.5" name="NeuralOrbHaloFeat"/></Stroke>',
        )
    )
    out.append(f"{i2}</Node>")

    # Left & Right 3D Isometric Double-Tiered Weight Plates (with 3D parallax rocking)
    for side, x_key, y_key, sc_key in (
        ("Left", "db_left_x", "db_left_y", "db_left_sc"),
        ("Right", "db_right_x", "db_right_y", "db_right_sc"),
    ):
        plate_id = nid()
        key_double(plate_id, 13, lambda st, k=x_key: st[k])
        key_double(plate_id, 14, lambda st, k=y_key: st[k])
        key_double(plate_id, 16, lambda st, k=sc_key: st[k])
        key_double(plate_id, 17, lambda st, k=sc_key: st[k])

        px0, py0, psc0 = s0[x_key], s0[y_key], s0[sc_key]
        bevel_dx = -4.2 if side == "Left" else 4.2

        # Main 3D Isometric Weight Plate Polygon
        plate_pts = [
            (-5.8, -18.5),
            (5.8, -18.5),
            (8.8, -12.0),
            (8.8, 12.0),
            (5.8, 18.5),
            (-5.8, 18.5),
            (-8.8, 12.0),
            (-8.8, -12.0),
        ]
        # Secondary Outer Olympic Plate Tier (gives unmistakable double-plate dumbbell silhouette)
        outer_tier_pts = [
            (x * 0.78 + bevel_dx, y * 0.80 + 1.2) for x, y in plate_pts
        ]

        out.append(
            f'{i2}<Node x="{f(px0)}" y="{f(py0)}" scaleX="{f(psc0)}" scaleY="{f(psc0)}" '
            f'name="DumbbellPlate{side}Node" id="{plate_id}">'
        )
        # Collar Locking Ring on Front Face
        out.append(
            ellipse_shape(
                i3,
                f"PlateCollar{side}",
                0,
                0,
                7.0,
                12.0,
                '<Fill name="CollarFill"><SolidColor colorValue="FF111722" name="CollarBg"/></Fill>'
                '<Stroke thickness="2.0" name="CollarRim"><SolidColor colorValue="FF00E5FF" name="CollarCol"/></Stroke>',
            )
        )
        # Main 3D Neon Lime Weight Plate Face
        out.append(
            poly_shape(
                i3,
                f"PlateFace{side}",
                plate_pts,
                f'<Fill name="PlateFill{side}">{grad3(f"PlateGrad{side}", -8, -18, 8, 18, "FFEAFF80", "FFCCFF00", "FF8AB800")}</Fill>'
                f'<Stroke thickness="1.6" join="round" name="PlateEdge{side}"><SolidColor colorValue="FFFFFFFF" name="PlateEdgeCol{side}"/></Stroke>',
                radius=2.6,
            )
        )
        # Secondary 3D Extruded Plate Tier
        out.append(
            poly_shape(
                i3,
                f"PlateBevel{side}",
                outer_tier_pts,
                f'<Fill name="PlateBevFill{side}"><SolidColor colorValue="FF6E9400" name="PlateBevCol{side}"/></Fill>'
                f'<Stroke thickness="1.4" join="round" name="PlateBevStr{side}"><SolidColor colorValue="FFCCFF00" name="PlateBevEdge{side}"/></Stroke>',
                radius=2.2,
            )
        )
        # Neon Lime Plate Halo
        out.append(
            ellipse_shape(
                i3,
                f"PlateGlow{side}",
                0,
                0,
                22.0,
                38.0,
                '<Stroke thickness="4.8" name="PlateGlowStr"><SolidColor colorValue="59CCFF00" name="PlateGlowCol"/>'
                '<Feather strength="5.5" name="PlateGlowFeat"/></Stroke>',
            )
        )
        out.append(f"{i2}</Node>")

    # Electric Cyan Neural Energy Bridge Bar (connecting Left & Right Weight Plates)
    out.append(stroke_line(i2, "DumbbellBridgeHot", (-24.0, -8.0), (24.0, -8.0), 3.2, "FFFFFFFF"))
    out.append(stroke_line(i2, "DumbbellBridgeCore", (-26.0, -8.0), (26.0, -8.0), 6.8, "FF00E5FF"))
    out.append(stroke_line(i2, "DumbbellBridgeGlow", (-26.0, -8.0), (26.0, -8.0), 12.0, "7300E5FF", feather=6.0))

    # ---------------- C. Volumetric Dark-Chrome Hexagonal Core Housing ----------------
    hex_outer = reg_polygon_pts(61.0, 6, rot_deg=-90.0)
    hex_inner = reg_polygon_pts(50.5, 6, rot_deg=-90.0)

    # Subtle HUD divider line between upper Dumbbell Core and lower Equalizer
    out.append(stroke_line(i2, "CoreHudDivider", (-31.0, 10.5), (31.0, 10.5), 1.5, "7300E5FF"))

    # Inner Recessed Obsidian Hex Chamber
    out.append(
        poly_shape(
            i2,
            "HexInnerChamber",
            hex_inner,
            f'<Fill name="HexInnerFill">{rad_grad3("HexInnerGrad", 0, -10, 52, 0, "FF162032", "FF0D131F", "FF070A10")}</Fill>'
            '<Stroke thickness="2.0" join="round" name="HexInnerRim">'
            f'{grad2("HexInnerRimGrad", -50, -50, 50, 50, "FF00E5FF", "FFCCFF00")}</Stroke>',
            radius=5.0,
        )
    )

    # Outer Volumetric Dark-Chrome Hexagonal Chassis
    out.append(
        poly_shape(
            i2,
            "HexOuterChassis",
            hex_outer,
            f'<Fill name="HexOuterFill">{grad3("HexOuterGrad", -55, -60, 55, 60, "FF28354E", "FF151D2C", "FF0A0E17")}</Fill>'
            '<Stroke thickness="3.4" join="round" name="HexOuterRim">'
            f'{grad3("HexOuterRimGrad", -60, -60, 60, 60, "FFEAFF80", "FF00E5FF", "FF1C2536")}</Stroke>',
            radius=7.0,
        )
    )

    # Outer Hex Ambient Energy Glow
    out.append(
        poly_shape(
            i2,
            "HexOuterGlow",
            reg_polygon_pts(64.5, 6, rot_deg=-90.0),
            '<Stroke thickness="7.5" join="round" name="HexGlowStr"><SolidColor colorValue="5900E5FF" name="HexGlowCol"/>'
            '<Feather strength="8.0" name="HexGlowFeat"/></Stroke>',
            radius=8.0,
        )
    )

    out.append(f"{ind}</Node>")
    return "\n".join(out)


def build_3d_gyro_rings():
    """Builds the Inner Gimbal Ring, Middle 3D Telemetry Ring, and Outer 3D Gyroscope Ring."""
    s0 = STATES[0]
    ind = "        "
    i2 = ind + "    "
    i3 = i2 + "    "
    out = []

    # ---------------- 1. Inner High-Energy Gimbal Ring (R = 82, #CCFF00 / #00E5FF) ----------------
    in_tilt_id = nid()
    in_spin_id = nid()
    key_double(in_tilt_id, 15, lambda st: st["phi_inner"])
    key_double(in_tilt_id, 17, lambda st: st["sy_inner"])
    key_double(in_spin_id, 15, lambda st: st["psi_inner"])

    out.append(
        f'{ind}<Node x="{f(CX)}" y="{f(CY)}" rotation="{f(s0["phi_inner"])}" '
        f'scaleY="{f(s0["sy_inner"])}" name="InnerGimbalTiltNode" id="{in_tilt_id}">'
    )
    out.append(f'{i2}<Node rotation="{f(s0["psi_inner"])}" name="InnerGimbalSpinNode" id="{in_spin_id}">')
    # Opposed High-Energy Plasma Arcs (Neon Lime + Electric Cyan)
    out.append(stroke_arc(i3, "InnerArcLimeHi", R_INNER, -65, 65, 3.6, "FFEAFF80", steps=14))
    out.append(stroke_arc(i3, "InnerArcCyanHi", R_INNER, 115, 245, 3.6, "FF80F2FF", steps=14))
    # 6 Precision Calibration Ticks on Inner Gimbal
    for deg in range(0, 360, 60):
        rad = math.radians(deg)
        p0 = ((R_INNER - 5.5) * math.cos(rad), (R_INNER - 5.5) * math.sin(rad))
        p1 = ((R_INNER + 5.5) * math.cos(rad), (R_INNER + 5.5) * math.sin(rad))
        col = "FFCCFF00" if (deg // 60) % 2 == 0 else "FF00E5FF"
        out.append(stroke_line(i3, f"InnerTick{deg}", p0, p1, 2.2, col))
    # Full Inner Gimbal Track
    out.append(
        ellipse_shape(
            i3,
            "InnerGimbalTrack",
            0,
            0,
            R_INNER * 2,
            R_INNER * 2,
            f'<Stroke thickness="2.4" name="InnerTrackStr">{grad2("InnerTrackGrad", -R_INNER, 0, R_INNER, 0, "BFCCFF00", "BF00E5FF")}</Stroke>',
        )
    )
    out.append(f"{i2}</Node>")
    out.append(f"{ind}</Node>")

    # ---------------- 2. Middle 3D Telemetry Ring (R = 110, Electric Cyan #00E5FF + #80F2FF) ----------------
    mid_tilt_id = nid()
    mid_spin_id = nid()
    key_double(mid_tilt_id, 15, lambda st: st["phi_mid"])
    key_double(mid_tilt_id, 17, lambda st: st["sy_mid"])
    key_double(mid_spin_id, 15, lambda st: st["psi_mid"])

    out.append(
        f'{ind}<Node x="{f(CX)}" y="{f(CY)}" rotation="{f(s0["phi_mid"])}" '
        f'scaleY="{f(s0["sy_mid"])}" name="MidTelemetryTiltNode" id="{mid_tilt_id}">'
    )
    # Front-hemisphere specular highlight on Middle Ring
    out.append(stroke_arc(i2, "MidFrontSpecCore", R_MID, 18, 162, 2.8, "FF80F2FF", steps=18))
    out.append(f'{i2}<Node rotation="{f(s0["psi_mid"])}" name="MidTelemetrySpinNode" id="{mid_spin_id}">')
    # 4 Segmented Telemetry Arcs on Inner Rail (R = 101)
    for k in range(4):
        base_d = k * 90
        out.append(stroke_arc(i3, f"MidTeleSubArc{k}", R_MID - 8.5, base_d + 12, base_d + 68, 2.0, "CC80F2FF", steps=10))
    # 8 Radial Telemetry Ticks around Middle Ring
    for k in range(8):
        deg = k * 45
        rad = math.radians(deg)
        r_in = R_MID - 8.0 if k % 2 == 0 else R_MID - 4.8
        r_out = R_MID + 8.0 if k % 2 == 0 else R_MID + 4.8
        p0 = (r_in * math.cos(rad), r_in * math.sin(rad))
        p1 = (r_out * math.cos(rad), r_out * math.sin(rad))
        out.append(stroke_line(i3, f"MidTick{deg}", p0, p1, 2.6 if k % 2 == 0 else 1.9, "FF80F2FF"))
    # Main Electric Cyan Ring Track + Feathered Cyan Glow
    out.append(
        ellipse_shape(
            i3,
            "MidTelemetryCoreTrack",
            0,
            0,
            R_MID * 2,
            R_MID * 2,
            '<Stroke thickness="4.0" name="MidCoreStr"><SolidColor colorValue="FF00E5FF" name="MidCoreCol"/></Stroke>',
        )
    )
    out.append(
        ellipse_shape(
            i3,
            "MidTelemetryGlowTrack",
            0,
            0,
            R_MID * 2,
            R_MID * 2,
            '<Stroke thickness="8.5" name="MidGlowStr"><SolidColor colorValue="5900E5FF" name="MidGlowCol"/>'
            '<Feather strength="7.5" name="MidGlowFeat"/></Stroke>',
        )
    )
    out.append(f"{i2}</Node>")
    out.append(f"{ind}</Node>")

    # ---------------- 3. Outer 3D Gyroscope Ring (R = 140, Neon Lime #CCFF00 + #EAFF80) ----------------
    out_tilt_id = nid()
    out_spin_id = nid()
    key_double(out_tilt_id, 15, lambda st: st["phi_outer"])
    key_double(out_tilt_id, 17, lambda st: st["sy_outer"])
    key_double(out_spin_id, 15, lambda st: st["psi_outer"])

    out.append(
        f'{ind}<Node x="{f(CX)}" y="{f(CY)}" rotation="{f(s0["phi_outer"])}" '
        f'scaleY="{f(s0["sy_outer"])}" name="OuterGyroTiltNode" id="{out_tilt_id}">'
    )
    # Front-hemisphere specular highlight on Outer Ring
    out.append(stroke_arc(i2, "OuterFrontSpecCore", R_OUTER, 18, 162, 3.0, "FFEAFF80", steps=18))
    out.append(f'{i2}<Node rotation="{f(s0["psi_outer"])}" name="OuterGyroSpinNode" id="{out_spin_id}">')
    # 4 Cardinal Reinforced Gyro Caliper Arcs (R = 147)
    for k in range(4):
        base_d = k * 90
        out.append(stroke_arc(i3, f"OuterCaliperArc{k}", R_OUTER + 6.5, base_d - 16, base_d + 16, 3.2, "FFEAFF80", steps=8))
    # 12 Precision Degree Tick Marks around Outer Gyroscope Ring
    for k in range(12):
        deg = k * 30
        rad = math.radians(deg)
        is_major = k % 3 == 0
        r_in = R_OUTER - (9.0 if is_major else 5.5)
        r_out = R_OUTER + (8.0 if is_major else 4.5)
        p0 = (r_in * math.cos(rad), r_in * math.sin(rad))
        p1 = (r_out * math.cos(rad), r_out * math.sin(rad))
        out.append(
            stroke_line(
                i3,
                f"OuterTick{deg}",
                p0,
                p1,
                2.8 if is_major else 2.0,
                "FFEAFF80" if is_major else "FFCCFF00",
            )
        )
    # Inner Concentric Bevel Rail (R = 130)
    out.append(
        ellipse_shape(
            i3,
            "OuterGyroInnerRail",
            0,
            0,
            (R_OUTER - 10.0) * 2,
            (R_OUTER - 10.0) * 2,
            '<Stroke thickness="1.6" name="OuterSubRailStr"><SolidColor colorValue="99EAFF80" name="OuterSubRailCol"/></Stroke>',
        )
    )
    # Main Neon Lime Gyroscope Track + Feathered Halo
    out.append(
        ellipse_shape(
            i3,
            "OuterGyroMainTrack",
            0,
            0,
            R_OUTER * 2,
            R_OUTER * 2,
            '<Stroke thickness="4.5" name="OuterMainStr"><SolidColor colorValue="FFCCFF00" name="OuterMainCol"/></Stroke>',
        )
    )
    out.append(
        ellipse_shape(
            i3,
            "OuterGyroGlowTrack",
            0,
            0,
            R_OUTER * 2,
            R_OUTER * 2,
            '<Stroke thickness="9.5" name="OuterGlowStr"><SolidColor colorValue="59CCFF00" name="OuterGlowCol"/>'
            '<Feather strength="8.5" name="OuterGlowFeat"/></Stroke>',
        )
    )
    out.append(f"{i2}</Node>")
    out.append(f"{ind}</Node>")

    return "\n".join(out)


def build_neural_pulse_halos():
    """Builds the 2 staggered Expanding Neural Pulse Halos that radiate outward from the core."""
    s0 = STATES[0]
    ind = "        "
    out = []

    # Halo 1: Neon Lime (#CCFF00) expanding wave
    h1_id = nid()
    h1_cid = nid()
    key_double(h1_id, 16, lambda st: st["halo1_scale"])
    key_double(h1_id, 17, lambda st: st["halo1_scale"])
    key_color(
        h1_cid,
        37,
        lambda st: argb_lerp((0x00, 0xCC, 0xFF, 0x00), (0x8C, 0xCC, 0xFF, 0x00), st["halo1_alpha"]),
    )
    h1_c0 = argb_lerp((0x00, 0xCC, 0xFF, 0x00), (0x8C, 0xCC, 0xFF, 0x00), s0["halo1_alpha"])
    out.append(
        ellipse_shape(
            ind,
            "NeuralPulseHaloLime",
            CX,
            CY,
            272.0,
            272.0,
            f'<Stroke thickness="3.4" name="Halo1Str"><SolidColor colorValue="{h1_c0}" name="Halo1Col" id="{h1_cid}"/>'
            '<Feather strength="4.5" name="Halo1Feat"/></Stroke>',
            sid=h1_id,
            sx=s0["halo1_scale"],
            sy=s0["halo1_scale"],
        )
    )

    # Halo 2: Electric Cyan (#00E5FF) expanding wave (staggered 180 deg)
    h2_id = nid()
    h2_cid = nid()
    key_double(h2_id, 16, lambda st: st["halo2_scale"])
    key_double(h2_id, 17, lambda st: st["halo2_scale"])
    key_color(
        h2_cid,
        37,
        lambda st: argb_lerp((0x00, 0x00, 0xE5, 0xFF), (0x8C, 0x00, 0xE5, 0xFF), st["halo2_alpha"]),
    )
    h2_c0 = argb_lerp((0x00, 0x00, 0xE5, 0xFF), (0x8C, 0x00, 0xE5, 0xFF), s0["halo2_alpha"])
    out.append(
        ellipse_shape(
            ind,
            "NeuralPulseHaloCyan",
            CX,
            CY,
            272.0,
            272.0,
            f'<Stroke thickness="3.4" name="Halo2Str"><SolidColor colorValue="{h2_c0}" name="Halo2Col" id="{h2_cid}"/>'
            '<Feather strength="4.5" name="Halo2Feat"/></Stroke>',
            sid=h2_id,
            sx=s0["halo2_scale"],
            sy=s0["halo2_scale"],
        )
    )

    return "\n".join(out)


def build_obsidian_chassis():
    """Builds the Deep Obsidian-Titanium Circular Chassis (#0A0D12 aura, #111722 sphere, #1C2536 rim)."""
    ind = "        "
    out = []

    # 1. Top-Left Volumetric Sphere Specular Sheen & Bottom-Right Rim Reflection
    out.append(
        stroke_arc(ind, "SphereTopLeftRimSheen", 156.0, 200, 315, 4.2, "7380F2FF", feather=5.0, steps=20, x=CX, y=CY)
    )
    out.append(
        stroke_arc(
            ind, "SphereBottomRightRimSheen", 156.0, 20, 125, 3.8, "66CCFF00", feather=5.0, steps=18, x=CX, y=CY
        )
    )

    # 2. 8 Outer Titanium Bezel Calibration Notches (at R = 157..167)
    for k in range(8):
        deg = k * 45
        rad = math.radians(deg)
        p0 = (CX + 157.0 * math.cos(rad), CY + 157.0 * math.sin(rad))
        p1 = (CX + 167.0 * math.cos(rad), CY + 167.0 * math.sin(rad))
        col = "B3CCFF00" if k % 2 == 0 else "B300E5FF"
        out.append(stroke_line(ind, f"ChassisBezelNotch{deg}", p0, p1, 2.8, col))

    # 3. Subtle 3D Spherical Latitude / Longitude Telemetry Grid Lines inside Sphere
    out.append(
        ellipse_shape(
            ind,
            "SphereGridMeridianV",
            CX,
            CY,
            138.0,
            308.0,
            '<Stroke thickness="1.2" name="GridMVStr"><SolidColor colorValue="591C2536" name="GridMVCol"/></Stroke>',
        )
    )
    out.append(
        ellipse_shape(
            ind,
            "SphereGridMeridianH",
            CX,
            CY,
            308.0,
            138.0,
            '<Stroke thickness="1.2" name="GridMHStr"><SolidColor colorValue="591C2536" name="GridMHCol"/></Stroke>',
        )
    )
    out.append(
        ellipse_shape(
            ind,
            "SphereInnerCoreGlow",
            CX,
            CY,
            216.0,
            216.0,
            f'<Fill name="InnerCoreAuraFill">{rad_grad3("InnerCoreAuraGrad", 0, 0, 108, 0, "4000E5FF", "1FCCFF00", "000A0D12")}</Fill>',
        )
    )

    # 4. Main Volumetric Obsidian-Titanium Sphere Body (#1C2536 highlight -> #111722 body -> #0A0D12 edge)
    out.append(
        ellipse_shape(
            ind,
            "ObsidianSphereBody",
            CX,
            CY,
            320.0,
            320.0,
            f'<Fill name="SphereBodyFill">{rad_grad3("SphereBodyGrad", -38, -42, 168, 0, "FF1C2536", "FF111722", "FF0A0D12", p1=0.52)}</Fill>'
            f'<Stroke thickness="4.8" name="SphereTitaniumBezel">{grad3("BezelGrad", -160, -160, 160, 160, "FF2B384E", "FF1C2536", "FF0D121B")}</Stroke>',
        )
    )

    # 5. Outer Titanium Ring & Deep Obsidian Full-Bleed Backdrop (#0A0D12)
    out.append(
        ellipse_shape(
            ind,
            "OuterAmbientAura",
            CX,
            CY,
            346.0,
            346.0,
            '<Stroke thickness="8.0" name="OuterAuraStr"><SolidColor colorValue="4000E5FF" name="OuterAuraCol"/>'
            '<Feather strength="9.0" name="OuterAuraFeat"/></Stroke>',
        )
    )
    out.append(
        f'{ind}<Shape x="{f(CX)}" y="{f(CY)}" name="ObsidianBackdrop">\n'
        f'{ind}    <Rectangle width="{W}" height="{H}" name="ObsidianBackdropRect"/>\n'
        f'{ind}    <Fill name="ObsidianBackdropFill">{rad_grad3("BackdropGrad", 0, -20, 220, 0, "FF111722", "FF0A0D12", "FF06080C", p1=0.65)}</Fill>\n'
        f"{ind}</Shape>"
    )

    return "\n".join(out)


def build_rml():
    global _id, KEYED
    _id = 100
    KEYED = []

    nodes_xml = build_3d_orbital_nodes()
    core_xml = build_central_biomech_core()
    rings_xml = build_3d_gyro_rings()
    halos_xml = build_neural_pulse_halos()
    chassis_xml = build_obsidian_chassis()

    grouped = {}
    for oid, kp_xml in KEYED:
        grouped.setdefault(oid, []).append(kp_xml)
    keyed_objects_xml = "\n".join(
        f'        <KeyedObject objectId="{oid}">\n' + "\n".join(props) + "\n        </KeyedObject>"
        for oid, props in grouped.items()
    )

    return f"""<Rive version="7.3">
    <Artboard width="{W}" height="{H}" clip="true" styleId="0:5" name="AiCoachGyroAvatar" id="0:6">
        <LayoutComponentStyle name="ArtboardStyle" id="0:5"/>

        <!-- 1. 3D Perspective Orbital Nodes (Neon Lime #CCFF00 & Electric Cyan #00E5FF) -->
{nodes_xml}

        <!-- 2. Central Biomechanical Hex-Core, 3D Isometric Dumbbell Emblem & 5-Bar Equalizer -->
{core_xml}

        <!-- 3. 3D Precessing & Counter-Rotating Gyroscope Rings -->
{rings_xml}

        <!-- 4. Expanding Neural Pulse Halos -->
{halos_xml}

        <!-- 5. Deep Obsidian-Titanium Circular Chassis & Volumetric Sphere -->
{chassis_xml}

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

        <LinearAnimation fps="{FPS}" duration="{DURATION}" loopValue="loop" name="GyroCoreLoop" id="0:60">
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


# ---------------------------------------------------------------- Fast Row-Culled RML Renderer
def _parse_color(hex_str):
    hex_str = hex_str.strip()
    if len(hex_str) == 8:
        a = int(hex_str[0:2], 16) / 255.0
        r = int(hex_str[2:4], 16) / 255.0
        g = int(hex_str[4:6], 16) / 255.0
        b = int(hex_str[6:8], 16) / 255.0
        return (r, g, b, a)
    return (1.0, 1.0, 1.0, 1.0)


def _eval_keys(root, target_frame):
    out = {}
    anim = root.find(".//LinearAnimation")
    if anim is None:
        return out
    for ko in anim.findall("KeyedObject"):
        oid = ko.attrib["objectId"]
        for kp in ko.findall("KeyedProperty"):
            pkey = int(kp.attrib["propertyKey"])
            frames = []
            for kf in kp:
                fr = float(kf.attrib["frame"])
                val = kf.attrib["value"]
                if kf.tag == "KeyFrameDouble":
                    frames.append((fr, float(val), "double"))
                elif kf.tag == "KeyFrameColor":
                    frames.append((fr, _parse_color(val), "color"))
            if not frames:
                continue
            if target_frame <= frames[0][0]:
                out[(oid, pkey)] = frames[0][1]
            elif target_frame >= frames[-1][0]:
                out[(oid, pkey)] = frames[-1][1]
            else:
                for i in range(len(frames) - 1):
                    f0, v0, kind = frames[i]
                    f1, v1, _ = frames[i + 1]
                    if f0 <= target_frame <= f1:
                        t = (target_frame - f0) / max(1e-6, f1 - f0)
                        if kind == "double":
                            out[(oid, pkey)] = lerp(v0, v1, t)
                        else:
                            out[(oid, pkey)] = tuple(lerp(c0, c1, t) for c0, c1 in zip(v0, v1))
                        break
    return out


def _mat_mul(m1, m2):
    a1, b1, c1, d1, tx1, ty1 = m1
    a2, b2, c2, d2, tx2, ty2 = m2
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * tx2 + c1 * ty2 + tx1,
        b1 * tx2 + d1 * ty2 + ty1,
    )


def _make_mat(x, y, rot, sx, sy):
    cs, sn = math.cos(rot), math.sin(rot)
    return (cs * sx, sn * sx, -sn * sy, cs * sy, x, y)


def _xform(m, pt):
    a, b, c, d, tx, ty = m
    x, y = pt
    return (a * x + c * y + tx, b * x + d * y + ty)


def _cubic_eval(p0, p1, p2, p3, t):
    u = 1.0 - t
    return (
        u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
    )


def _path_to_poly(path_el, steps=12):
    pts = []
    verts = list(path_el)
    if not verts:
        return []
    is_closed = path_el.attrib.get("isClosed", "true") == "true"
    n = len(verts)
    count = n if is_closed else n - 1
    for i in range(count):
        v0 = verts[i]
        v1 = verts[(i + 1) % n]
        x0, y0 = float(v0.attrib.get("x", 0)), float(v0.attrib.get("y", 0))
        x1, y1 = float(v1.attrib.get("x", 0)), float(v1.attrib.get("y", 0))
        if v0.tag == "CubicMirroredVertex":
            r0 = float(v0.attrib.get("rotation", 0))
            d0 = float(v0.attrib.get("distance", 0))
            c0 = (x0 + d0 * math.cos(r0), y0 + d0 * math.sin(r0))
        else:
            c0 = (x0, y0)
        if v1.tag == "CubicMirroredVertex":
            r1 = float(v1.attrib.get("rotation", 0))
            d1 = float(v1.attrib.get("distance", 0))
            c1 = (x1 - d1 * math.cos(r1), y1 - d1 * math.sin(r1))
        else:
            c1 = (x1, y1)
        for s in range(steps):
            pts.append(_cubic_eval((x0, y0), c0, c1, (x1, y1), s / steps))
    if not is_closed:
        v_last = verts[-1]
        pts.append((float(v_last.attrib.get("x", 0)), float(v_last.attrib.get("y", 0))))
    return pts


def _eval_stops(stops, t):
    if t <= stops[0][0]:
        return stops[0][1]
    if t >= stops[-1][0]:
        return stops[-1][1]
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        if p0 <= t <= p1:
            u = (t - p0) / max(1e-6, p1 - p0)
            return tuple(lerp(a, b, u) for a, b in zip(c0, c1))
    return stops[-1][1]


def _make_shader(p_el, mat, kvals):
    sc = p_el.find("SolidColor")
    if sc is not None:
        sc_id = sc.attrib.get("id")
        col = kvals.get((sc_id, 37), _parse_color(sc.attrib.get("colorValue", "FFFFFFFF")))
        return ("solid", col)
    lg = p_el.find("LinearGradient")
    if lg is not None:
        sx = float(lg.attrib.get("startX", 0))
        sy = float(lg.attrib.get("startY", 0))
        ex = float(lg.attrib.get("endX", 0))
        ey = float(lg.attrib.get("endY", 0))
        p0 = _xform(mat, (sx, sy))
        p1 = _xform(mat, (ex, ey))
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        l2 = max(1e-6, dx * dx + dy * dy)
        stops = [(float(st.attrib.get("position", 0)), _parse_color(st.attrib["colorValue"])) for st in lg.findall("GradientStop")]
        return ("linear", p0[0], p0[1], dx / l2, dy / l2, stops)
    rg = p_el.find("RadialGradient")
    if rg is not None:
        sx = float(rg.attrib.get("startX", 0))
        sy = float(rg.attrib.get("startY", 0))
        ex = float(rg.attrib.get("endX", 100))
        ey = float(rg.attrib.get("endY", 0))
        p0 = _xform(mat, (sx, sy))
        p1 = _xform(mat, (ex, ey))
        p2 = _xform(mat, (sx, sy + math.hypot(ex - sx, ey - sy)))
        rx = max(1e-3, math.hypot(p1[0] - p0[0], p1[1] - p0[1]))
        ry = max(1e-3, math.hypot(p2[0] - p0[0], p2[1] - p0[1]))
        stops = [(float(st.attrib.get("position", 0)), _parse_color(st.attrib["colorValue"])) for st in rg.findall("GradientStop")]
        return ("radial", p0[0], p0[1], rx, ry, stops)
    return ("solid", (1, 1, 1, 1))


def _sample_shader(shader, x, y):
    kind = shader[0]
    if kind == "solid":
        return shader[1]
    if kind == "linear":
        _, x0, y0, vx, vy, stops = shader
        t = (x - x0) * vx + (y - y0) * vy
        return _eval_stops(stops, t)
    if kind == "radial":
        _, x0, y0, rx, ry, stops = shader
        t = math.hypot((x - x0) / rx, (y - y0) / ry)
        return _eval_stops(stops, t)
    return (1, 1, 1, 1)


def write_png(path, w, h, rgb_buf):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        row_start = y * w * 3
        raw.extend(rgb_buf[row_start : row_start + w * 3])

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def render_buffer(rml_path, frame_num, scale=2):
    tree = ET.parse(rml_path)
    root = tree.getroot()
    ab = root.find("Artboard")
    W_px = int(float(ab.attrib.get("width", 360))) * scale
    H_px = int(float(ab.attrib.get("height", 360))) * scale
    kvals = _eval_keys(root, frame_num)
    draws = []

    def walk(el, parent_mat):
        oid = el.attrib.get("id")
        x = kvals.get((oid, 13), float(el.attrib.get("x", 0)))
        y = kvals.get((oid, 14), float(el.attrib.get("y", 0)))
        rot = kvals.get((oid, 15), float(el.attrib.get("rotation", 0)))
        sx = kvals.get((oid, 16), float(el.attrib.get("scaleX", 1)))
        sy = kvals.get((oid, 17), float(el.attrib.get("scaleY", 1)))
        mat = _mat_mul(parent_mat, _make_mat(x, y, rot, sx, sy))

        if el.tag == "Shape":
            poly = []
            is_closed = True
            for child in el:
                if child.tag == "PointsPath":
                    is_closed = child.attrib.get("isClosed", "true") == "true"
                    poly = [_xform(mat, p) for p in _path_to_poly(child)]
                elif child.tag == "Ellipse":
                    ew = float(child.attrib.get("width", 10)) / 2.0
                    eh = float(child.attrib.get("height", 10)) / 2.0
                    poly = [_xform(mat, (ew * math.cos(2 * math.pi * k / 56), eh * math.sin(2 * math.pi * k / 56))) for k in range(56)]
                elif child.tag == "Rectangle":
                    rw = float(child.attrib.get("width", 10)) / 2.0
                    rh = float(child.attrib.get("height", 10)) / 2.0
                    poly = [_xform(mat, p) for p in ((-rw, -rh), (rw, -rh), (rw, rh), (-rw, rh))]

            paints = [c for c in el if c.tag in ("Fill", "Stroke")]
            for p_el in paints:
                shader = _make_shader(p_el, mat, kvals)
                if p_el.tag == "Fill" and is_closed and len(poly) >= 3:
                    draws.append(("fill", poly, shader))
                elif p_el.tag == "Stroke" and len(poly) >= 2:
                    th = float(p_el.attrib.get("thickness", 1.0)) * scale
                    fe_el = p_el.find("Feather")
                    feather = float(fe_el.attrib.get("strength", 0.0)) * scale if fe_el is not None else 0.0
                    draws.append(("stroke", poly, is_closed, th, feather, shader))

        for child in el:
            if child.tag in ("Node", "Shape"):
                walk(child, mat)

    root_mat = (float(scale), 0.0, 0.0, float(scale), 0.0, 0.0)
    for child in ab:
        if child.tag in ("Node", "Shape"):
            walk(child, root_mat)

    buf = [0.04, 0.05, 0.07] * (W_px * H_px)

    def blend_px(ix, iy, r, g, b, a):
        if 0 <= ix < W_px and 0 <= iy < H_px and a > 0.002:
            idx = (iy * W_px + ix) * 3
            u = 1.0 - a
            buf[idx] = buf[idx] * u + r * a
            buf[idx + 1] = buf[idx + 1] * u + g * a
            buf[idx + 2] = buf[idx + 2] * u + b * a

    for item in reversed(draws):
        if item[0] == "fill":
            _, poly, shader = item
            min_y = max(0, int(min(p[1] for p in poly)))
            max_y = min(H_px - 1, int(max(p[1] for p in poly)) + 1)
            n = len(poly)
            for y in range(min_y, max_y + 1):
                yc = y + 0.5
                xs = []
                for i in range(n):
                    x0, y0 = poly[i]
                    x1, y1 = poly[(i + 1) % n]
                    if (y0 <= yc < y1) or (y1 <= yc < y0):
                        xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
                xs.sort()
                for k in range(0, len(xs) - 1, 2):
                    x_start = max(0, int(xs[k]))
                    x_end = min(W_px - 1, int(xs[k + 1]))
                    for x in range(x_start, x_end + 1):
                        r, g, b, a = _sample_shader(shader, x + 0.5, yc)
                        blend_px(x, y, r, g, b, a)
        elif item[0] == "stroke":
            _, poly, is_closed, th, feather, shader = item
            rad = max(0.8, th / 2.0 + feather * 0.85)
            core_r = max(0.4, th / 2.0)
            cnt = len(poly) if is_closed else len(poly) - 1
            segs = []
            by0, by1 = H_px, 0
            for i in range(cnt):
                x0, y0 = poly[i]
                x1, y1 = poly[(i + 1) % len(poly)]
                dx, dy = x1 - x0, y1 - y0
                sy_min = min(y0, y1) - rad
                sy_max = max(y0, y1) + rad
                sx_min = min(x0, x1) - rad
                sx_max = max(x0, x1) + rad
                segs.append((x0, y0, dx, dy, dx * dx + dy * dy, sy_min, sy_max, sx_min, sx_max))
                by0 = min(by0, int(sy_min))
                by1 = max(by1, int(sy_max) + 1)
            by0 = max(0, by0)
            by1 = min(H_px - 1, by1)
            r2_max = rad * rad
            for y in range(by0, by1 + 1):
                yc = y + 0.5
                row_segs = [s for s in segs if s[5] <= yc <= s[6]]
                if not row_segs:
                    continue
                bx0 = max(0, int(min(s[7] for s in row_segs)))
                bx1 = min(W_px - 1, int(max(s[8] for s in row_segs)) + 1)
                for x in range(bx0, bx1 + 1):
                    xc = x + 0.5
                    min_d2 = r2_max + 1.0
                    for x0, y0, dx, dy, l2, _, _, sx0, sx1 in row_segs:
                        if xc < sx0 or xc > sx1:
                            continue
                        if l2 < 1e-6:
                            d2 = (xc - x0) ** 2 + (yc - y0) ** 2
                        else:
                            t = max(0.0, min(1.0, ((xc - x0) * dx + (yc - y0) * dy) / l2))
                            d2 = (xc - (x0 + t * dx)) ** 2 + (yc - (y0 + t * dy)) ** 2
                        if d2 < min_d2:
                            min_d2 = d2
                    if min_d2 <= r2_max:
                        d = math.sqrt(min_d2)
                        if feather > 0.1:
                            falloff = max(0.0, 1.0 - max(0.0, d - core_r * 0.3) / max(1e-3, rad - core_r * 0.3))
                            falloff = falloff * falloff * (3.0 - 2.0 * falloff) * 0.65
                        else:
                            falloff = 1.0 if d <= core_r else max(0.0, 1.0 - (d - core_r))
                        r, g, b, a = _sample_shader(shader, xc, yc)
                        blend_px(x, y, r, g, b, a * falloff)
    return W_px, H_px, buf


def downsample_box(w, h, buf, out_w, out_h, crop=None):
    if crop is not None:
        csize, off_y, off_x = crop
        sx0, sy0, sw, sh = off_x, off_y, csize, csize
    else:
        sx0, sy0, sw, sh = 0, 0, w, h

    out = bytearray(out_w * out_h * 3)
    scale_x = sw / out_w
    scale_y = sh / out_h
    for oy in range(out_h):
        y0 = int(sy0 + oy * scale_y)
        y1 = max(y0 + 1, int(sy0 + (oy + 1) * scale_y))
        for ox in range(out_w):
            x0 = int(sx0 + ox * scale_x)
            x1 = max(x0 + 1, int(sx0 + (ox + 1) * scale_x))
            sr = sg = sb = 0.0
            cnt = 0
            for yy in range(max(0, y0), min(h, y1)):
                for xx in range(max(0, x0), min(w, x1)):
                    idx = (yy * w + xx) * 3
                    sr += buf[idx]
                    sg += buf[idx + 1]
                    sb += buf[idx + 2]
                    cnt += 1
            if cnt > 0:
                sr /= cnt
                sg /= cnt
                sb /= cnt
            oidx = (oy * out_w + ox) * 3
            out[oidx] = int(max(0.0, min(1.0, sr)) * 255)
            out[oidx + 1] = int(max(0.0, min(1.0, sg)) * 255)
            out[oidx + 2] = int(max(0.0, min(1.0, sb)) * 255)
    return out


def build_contact_sheet(frames_rgb, tile_size=256):
    """Assemble a 3x2 contact sheet of 6 rendered frames (each tile_size x tile_size)."""
    cols, rows = 3, 2
    sheet_w = cols * tile_size
    sheet_h = rows * tile_size
    sheet = bytearray(sheet_w * sheet_h * 3)
    for idx, rgb in enumerate(frames_rgb):
        col = idx % cols
        row = idx // cols
        ox = col * tile_size
        oy = row * tile_size
        for y in range(tile_size):
            src_start = y * tile_size * 3
            dst_start = ((oy + y) * sheet_w + ox) * 3
            sheet[dst_start : dst_start + tile_size * 3] = rgb[src_start : src_start + tile_size * 3]
    return sheet_w, sheet_h, sheet


def main():
    rml_text = build_rml()
    RML_OUT.write_text(rml_text, encoding="utf-8")

    riv_bytes = _compile_rml_bytes(RML_OUT)
    assert riv_bytes[:4] == b"RIVE", "Invalid RIVE magic header"
    assert len(riv_bytes) > 25_000, f"Expected > 25 KB, got {len(riv_bytes)} bytes"

    ASSET_RIV.parent.mkdir(parents=True, exist_ok=True)
    ASSET_RIV.write_bytes(riv_bytes)

    sample_frames = (0, 60, 120, 180, 240, 300)
    tiles = []
    for fr in sample_frames:
        rw, rh, buf = render_buffer(RML_OUT, fr, scale=2)
        tile_256 = downsample_box(rw, rh, buf, 256, 256)
        tiles.append(tile_256)
        if fr == 60:
            ASSET_THUMB.parent.mkdir(parents=True, exist_ok=True)
            write_png(ASSET_THUMB, 256, 256, tile_256)

    sw, sh, sheet_rgb = build_contact_sheet(tiles, tile_size=256)
    write_png(SHEET_OUT, sw, sh, sheet_rgb)
    print(
        f"Built {ASSET_RIV} ({len(riv_bytes):,} bytes, header={riv_bytes[:4]!r}), "
        f"thumbnail={ASSET_THUMB}, sheet={SHEET_OUT}"
    )


if __name__ == "__main__":
    main()
