# Dumbbell Front Raise (`front_raise`) — 16:9 HD Procedural Rive Animation

## Overview
- **Exercise ID**: `front_raise` (`"name": "Dumbbell Front Raise"` in `assets/data/exercises.json`)
- **Canvas**: `640x360` (16:9 widescreen), `FLOOR = 300.0`
- **Framerate & Duration**: `60 FPS`, `160 frames` (`2.67s` seamless loop)
- **Published Assets**:
  - `assets/animations/front_raise.riv` (Rive 7.3 binary, 52-byte TOC header)
  - `assets/animations/thumbnails/front_raise.png` (`256x256` catalog thumbnail)

## Anatomy & Biomechanics
- **Standing 3/4 Front-Left Proportions**: Reuses the exact standing athletic male proportions, volumetric 3/4 head, neck, sculpted chest, 6-pack rectus abdominis, slender athletic waist, compression shorts, quadriceps, calves, and planted feet from `bicep_curl_barbell`.
- **100% Stationary Body**: Feet, calves, thighs, hips/shorts, abs, chest, neck, and head remain completely rock-solid throughout the repetition.
- **Alternating Standing Dumbbell Front Raise**:
  - **Start / End (`f = 0` & `f = 160`, `r = 0.0`, Left Panel)**: Far (right) arm is raised straight forward-left to shoulder height (`90°` shoulder flexion) holding a black double-plate dumbbell in a pronated overhand grip; Near (left) arm hangs down naturally in front of the left thigh/hip holding the second black dumbbell.
  - **Midpoint Peak (`f = 72`, `r = 1.0`, Right Panel)**: Near (left) arm raises smoothly in a clean forward arc up to shoulder height (`90°` shoulder flexion, parallel to the floor) while the Far (right) arm lowers smoothly in front of the right thigh.
- **Target Muscle Activation (`#FFF97316` -> `#FFF43F5E`)**:
  1. `Anterior deltoid` (Primary Mover — front head of left & right shoulder caps, pulsing in phase with each arm's elevation)
  2. `Lateral deltoid` (Synergist — middle head of left & right shoulder caps)
  3. `Pectoralis major (upper)` (Synergist — clavicular upper chest head right below the collarbones)
  4. `Serratus anterior` (Stabilizer — 3 finger-like ribs on the lateral ribcage below the outer pectoral)

## Build & Render
```bash
python3 rive_animations/front_raise/gen_front_raise.py --publish
```
