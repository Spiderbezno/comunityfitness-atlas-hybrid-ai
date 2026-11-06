# Skull Crusher (`skull_crusher`)

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) procedural Rive 7.3 animation for **Skull Crusher** (`id: "skull_crusher"`, Lying Barbell Tricep Extension).

## Biomechanics & Reference Anatomy
- **3/4 Supine Flat-Bench Barbell Tricep Extension**:
  - **Flat Padded Weight Bench (`y ~ 214`, `FLOOR = 300.0`)**: The athlete lies supine on a horizontal upholstered weight bench with steel support legs on the floor and both feet planted flat for stability.
  - **Locked Humeri (`~100 deg`) & Pure Circular Elbow Arc (`r: 0.0 -> 1.0`)**:
    - Both upper arms remain angled slightly back toward the head (`~100 deg` from the torso) to keep constant stretch tension on the long head of the triceps.
    - `r = 0.0` (**Bottom Stretch**): Elbows flex deeply so the forearms lower the loaded barbell in a controlled arc just above the forehead/crown (`(388, 152)`).
    - `r = 1.0` (**Top Lockout**): Forearms extend powerfully upward around the fixed elbows to full lockout (`(354, 92)`).
- **Highlighted Target Muscle Groups** (`#FFF97316` -> `#FFF43F5E`):
  1. **Triceps Brachii — Long Head, Lateral Head & Medial Head** (Primary Mover — full 3-head horseshoe contraction)
  2. **Forearm Stabilizers (`Anconeus` & Wrist Extensors)** (Secondary — elbow joint & wrist stabilization under load)

## Build & Publish
```bash
python3 rive_animations/skull_crusher/gen_skull_crusher.py --publish
```
