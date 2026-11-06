# Romanian Deadlift (`romanian_deadlift`) — Rive 7.3 Procedural Animation

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) HD 3D-shaded procedural Rive animation for **Barbell Romanian Deadlift** (`id: "romanian_deadlift"`).

## Biomechanics & Anatomical Fidelity
- **3/4 Hip-Hinge Barbell Kinematics (`r = 0.0 -> 1.0`)**:
  - **Top Standing Lockout (`f = 0`, `r = 0.0`)**: The athlete stands tall in a 3/4 stance on `FLOOR = 300.0`, holding a loaded Olympic barbell (chrome bar + 3D multi-plate black cast-iron weight stacks on both ends) across the upper thighs with straight hanging arms.
  - **Bottom Hip-Hinge Stretch (`f = 78`, `r = 1.0`)**: The athlete drives the pelvis and glutes backward into a deep hip hinge while keeping a soft `~18°` knee bend (nearly vertical shins) and a flat neutral spine (`~22°` above horizontal), sliding the barbell close along the shins to mid-shin level with the plates suspended above the floor.
- **Highlighted Target & Synergist Muscle Groups**:
  1. **Hamstrings (`Biceps femoris` & `Semitendinosus`)** (Primary — posterior thigh hip extensors)
  2. **Gluteus maximus & Gluteus medius** (Primary — posterior pelvis hip extensors)
  3. **Erector spinae & Upper-back stabilizers** (Synergists — lumbar/thoracic paraspinal columns and middle/lower trapezius)

## Build & Publish
```bash
python3 rive_animations/romanian_deadlift/gen_romanian_deadlift.py --publish
```
