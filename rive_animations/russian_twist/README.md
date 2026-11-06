# Russian Twist (`russian_twist`)

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) procedural Rive 7.3 animation for **Russian Twist** (`id: "russian_twist"`).

## Biomechanics & Reference Anatomy
- **3/4 V-Sit Rotational Core Mechanics**:
  - **Seated V-Sit Balance on Studio Mat (`FLOOR = 300.0`)**: The athlete balances on the ischial tuberosities/glutes (`(306, 274)`) with the torso reclined at `~45 deg` and knees flexed (`~85 deg`) so the bare feet hover elevated off the floor (`y ~ 256`).
  - **Full Cross-Body Axial Rotation (`r: 0.0 -> 1.0`)**:
    - `r = 0.0` (**Near / Right Hip Rotation**): Upper torso, shoulders, head, and both arms rotate toward the near right hip (`(284, 246)`), lowering the sculpted cast-iron weight plate / medicine ball beside the right flank.
    - `r = 1.0` (**Far / Left Hip Rotation**): Torso, shoulders, and clasped hands sweep in an arc across the abdominal midline to the far left hip (`(336, 192)`), while the elevated legs counter-stabilize.
- **Highlighted Target Muscle Groups** (`#FFF97316` -> `#FFF43F5E`):
  1. **External & Internal Obliques** (Primary Core — axial thoracolumbar rotation & anti-flexion flank wall)
  2. **Rectus Abdominis (6-pack)** (Primary Core — isometric V-sit anti-extension abdominal wall)
  3. **Hip Flexors / Rectus Femoris** (Secondary — isometric V-sit thigh elevation & counter-rotation stabilization)

## Build & Publish
```bash
python3 rive_animations/russian_twist/gen_russian_twist.py --publish
```
