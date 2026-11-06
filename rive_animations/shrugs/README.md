# Dumbbell Shrugs (`shrugs`) — Rive 7.3 Procedural Animation

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) HD 3D-shaded procedural Rive animation for **Dumbbell Shrugs** (`id: "shrugs"`).

## Biomechanics & Anatomical Fidelity
- **3/4 Standing Scapular Elevation (`r = 0.0 -> 1.0`)**:
  - **Bottom Stretch (`f = 0`, `r = 0.0`)**: The athlete stands tall in a balanced 3/4 front-left stance holding a pair of heavy 3-plate black dumbbells at the sides of the thighs with straight arms and depressed shoulder girdles.
  - **Peak Shrug Contraction (`f = 72`, `r = 1.0`)**: Both shoulder girdles, clavicles, scapulae, and straight arms elevate vertically by `~17.5 px` toward the ears while keeping the elbows straight, driving maximum contraction in the upper trapezius and levator scapulae.
- **Highlighted Target & Synergist Muscle Groups**:
  1. **Upper trapezius** (Primary — bilateral collar-to-neck muscular wedges elevating the clavicles and acromion)
  2. **Levator scapulae** (Primary/Synergist — posterolateral neck-to-scapula elevator straps)
  3. **Middle trapezius** (Synergist — superior/medial scapular stabilizing fibers along the shoulder ridge)
  4. **Forearm flexors & Brachioradialis** (Stabilizers — heavy isometric grip stabilizers on both forearms)

## Build & Publish
```bash
python3 rive_animations/shrugs/gen_shrugs.py --publish
```
