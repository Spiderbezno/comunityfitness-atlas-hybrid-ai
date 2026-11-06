# Barbell Squat (`squat`) — Rive 7.3 Procedural Animation

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) HD 3D-shaded procedural Rive animation for **Barbell Back Squat** (`id: "squat"`).

## Biomechanics & Anatomical Fidelity
- **3/4 High-Bar Back Squat Kinematics (`r = 0.0 -> 1.0`)**:
  - **Top Standing Lockout (`f = 0`, `r = 0.0`)**: The athlete stands tall in a 3/4 stance on `FLOOR = 300.0` with a loaded Olympic barbell (chrome bar + 3D multi-plate black cast-iron weight stacks on both ends) resting across the upper trapezius behind the neck, hands gripping the bar outside the shoulders.
  - **Bottom Parallel / Below-Parallel Squat (`f = 78`, `r = 1.0`)**: Hips and knees flex deeply into a full athletic squat while keeping the chest proud and spine neutral, with the barbell tracking vertically over mid-foot.
- **Highlighted Target & Synergist Muscle Groups**:
  1. **Quadriceps femoris (`Rectus femoris`, `Vastus lateralis`, `Vastus medialis`)** (Primary — anterior & lateral knee extensors on both thighs)
  2. **Gluteus maximus** (Primary — posterior pelvis & hip extensors)
  3. **Adductor magnus & Hamstrings** (Synergists — posterior/medial thigh hip extensors and stabilizers)

## Build & Publish
```bash
python3 rive_animations/squat/gen_squat.py --publish
```
