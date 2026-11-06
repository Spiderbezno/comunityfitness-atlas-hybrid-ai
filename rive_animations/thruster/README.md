# Barbell Thruster (`thruster`) — Procedural Rive 7.3 Animation

## Overview
- **Artboard**: `thruster` (`640x360`, 60 FPS, 180 frames / 3.0s loop)
- **Perspective**: 3/4 front-left oblique view (`FLOOR = 300.0`)
- **Equipment**: Loaded 3D Olympic Barbell with stepped 45-lb, 25-lb, and 10-lb plates, chrome collars, and sleeves
- **Primary Muscles**: Full Body (`Quadriceps femoris`, `Gluteus maximus`, `Anterior & Lateral Deltoids`, `Triceps brachii`)

## Biomechanics & Keyframes
- **Frames 0–16 (`r = 0.0`)**: Deep below-parallel Front Squat bottom position with the barbell racked on the anterior deltoids/clavicles and elbows angled forward-up.
- **Frames 16–76 (`r: 0.0 -> 1.0`)**: Explosive Front Squat leg drive out of the hole (`r: 0.0 -> 0.56`) transferring momentum directly into a full Overhead Press lockout (`r: 0.36 -> 1.0`).
- **Frames 76–96 (`r = 1.0`)**: Full standing Overhead Lockout hold directly over mid-foot.
- **Frames 96–162 (`r: 1.0 -> 0.0`)**: Controlled eccentric return to the front rack and deep squat bottom position.
- **Frames 162–180 (`r = 0.0`)**: Bottom Front Squat hold for seamless looping.

## Build & Publish
```bash
python3 rive_animations/thruster/gen_thruster.py --publish
```
