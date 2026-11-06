# Rear Delt Fly (`rear_delt_fly`) — Rive 7.3 Procedural Animation

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) HD 3D-shaded procedural Rive animation for **Bent-Over Dumbbell Rear Delt Fly** (`id: "rear_delt_fly"`).

## Biomechanics & Anatomical Fidelity
- **3/4 Dorso-Lateral Hip-Hinge Stance (`r = 0.0 -> 1.0`)**:
  - **Bottom Hanging Start (`f = 0`, `r = 0.0`)**: The athlete hinges at the hips (`~22°` above horizontal, facing left `-X`) with slightly flexed knees and a neutral spine, holding two 3-plate black dumbbells hanging vertically beneath the shoulders.
  - **Peak Transverse Abduction (`f = 72`, `r = 1.0`)**: Maintaining a stable torso hinge, both arms sweep wide in horizontal abduction—the near (left) arm abducting outward and back-right (`+X, +Y`) toward the viewer while the far (right) arm abducts outward and up-right (`+X, -Y`) above the upper back.
- **Highlighted Target & Synergist Muscle Groups**:
  1. **Posterior deltoid** (Primary — rear head of left & right shoulders)
  2. **Lateral deltoid** (Synergist — multipennate middle deltoid head)
  3. **Infraspinatus & Teres minor** (Synergists — deep posterior cuff beneath the scapular spine)
  4. **Middle & Lower Trapezius / Rhomboids** (Synergists — interscapular fan across the upper thoracic back)

## Build & Publish
```bash
python3 rive_animations/rear_delt_fly/gen_rear_delt_fly.py --publish
```
