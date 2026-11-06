# Barbell Upright Row (`upright_row`) — Rive 7.3 Procedural Animation

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) HD 3D-shaded procedural Rive animation for **Barbell Upright Row** (`id: "upright_row"`).

## Biomechanics & Anatomical Fidelity
- **3/4 Standing High-Elbow Vertical Pull (`r = 0.0 -> 1.0`)**:
  - **Bottom Hang (`f = 0`, `r = 0.0`)**: The athlete stands tall in a balanced 3/4 front-left stance with arms extended downward holding a loaded 3-plate Olympic barbell with a pronated shoulder-width grip across the upper thighs.
  - **Peak Upright Pull (`f = 72`, `r = 1.0`)**: The athlete pulls the barbell vertically close to the torso up to upper-chest/clavicle height, driving both elbows high and wide (`elbows` well above `wrists` and `shoulders`) in the classic V-shaped upright row posture.
- **Highlighted Target & Synergist Muscle Groups**:
  1. **Lateral deltoid** (Primary — multipennate middle head of left & right shoulder caps)
  2. **Anterior deltoid** (Primary — front clavicular head of left & right shoulder caps)
  3. **Upper trapezius** (Primary/Synergist — bilateral collar-to-neck muscular wedges elevating and upwardly rotating the scapulae)
  4. **Brachioradialis & Biceps brachii** (Synergists — pronated-grip elbow flexors on both forearms and upper arms)

## Build & Publish
```bash
python3 rive_animations/upright_row/gen_upright_row.py --publish
```
