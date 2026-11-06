# Cable Face Pull (`face_pull`) — 16:9 HD Procedural Rive Animation

## Overview
- **Exercise ID**: `face_pull` (`"name": "Cable Face Pull"` in `assets/data/exercises.json`)
- **Canvas**: `640x360` (16:9 widescreen), `FLOOR = 300.0`
- **Framerate & Duration**: `60 FPS`, `160 frames` (`2.67s` seamless loop)
- **Published Assets**:
  - `assets/animations/face_pull.riv` (Rive 7.3 binary, 52-byte TOC header)
  - `assets/animations/thumbnails/face_pull.png` (`256x256` catalog thumbnail rendered at peak contraction `f = 72`)

## Biomechanics & Reference Alignment
Matches the 2-panel 3/4 rear-left **Cable Face Pull** anatomical reference illustration:
1. **Viewpoint & Stationary Body**:
   - 3/4 rear-left view of a muscular male athlete standing upright in a stable split/athletic stance on `FLOOR = 300.0`, facing the high cable pulley machine on the left.
   - Feet, calves, hamstrings/quads, glutes/compression shorts, V-tapered torso/spine, lats, neck, and head remain **100% stationary** throughout the repetition.
2. **High Cable Pulley Machine & Weight Stack (`Left Side`)**:
   - White powder-coated steel cable column with angled base stabilizer, dual foam knee-hold rollers, twin vertical chrome guide rods, overhead angled pulley boom with 3 pulley wheels, and a multi-plate black weight stack that lifts upward during the concentric pull (`r: 0.0 -> 1.0`) and lowers smoothly during the eccentric return.
3. **Arm, Rope & External Rotation Kinematics**:
   - **Start / Full Extension (`f = 0`, `r = 0.0`)**: Both arms extended straight forward-left at shoulder height toward the high pulley (`L_EL = (268, 82)`, `L_HAND = (232, 76)`), hands close together gripping the dual braided rope attachment, weight stack at rest.
   - **Peak Contraction (`f = 72`, `r = 1.0`)**: Elbows pulled high and flared wide at shoulder level (`L_EL = (272, 62)`, `R_EL = (398, 68)`), shoulders externally rotated so forearms angle upward and hands pull the dual rope ends apart beside the temples/ears (`L_HAND = (312, 44)`, `R_HAND = (368, 48)`), cable taut, weight stack lifted.
4. **Target Muscle Activation (`#FFF97316` -> `#FFF43F5E`)**:
   - **Primary**: `Posterior deltoid` (`scale = 1.00`), `Trapezius (middle and lower)` (`scale = 0.98`), `Lateral deltoid` (`scale = 0.95`), `Infraspinatus` (`scale = 0.92`), `Teres minor` (`scale = 0.92`).
   - **Secondary**: `Brachioradialis` (`scale = 0.88`), `Brachialis` (`scale = 0.86`).

## Build & Render
```bash
python3 rive_animations/face_pull/gen_face_pull.py --publish
```
