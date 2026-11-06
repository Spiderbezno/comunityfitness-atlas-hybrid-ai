# Dumbbell Row (`dumbbell_row`) — Procedural 60 FPS Rive Animation

High-definition 16:9 (`640x360`, `FLOOR = 300.0`) procedural Rive animation for **Dumbbell Row** (`id: "dumbbell_row"` in `assets/data/exercises.json`), engineered in a 3/4 front-left isometric view on a flat utility bench.

## Biomechanics & Anatomical Highlights
- **3-Point Bench Support Posture**:
  - **Far (Right) Support Arm**: Palm planted flat on the front-left of the bench pad (`FAR_HAND = (218, 206)`) with elbow extended (`FAR_EL = (225, 168)`) supporting the hinged upper torso.
  - **Far (Right) Kneeling Leg**: Right knee (`FAR_KNEE = (312, 194)`) and horizontal shin (`(312, 194) -> (358, 190)`) resting atop the rear-right of the bench pad.
  - **Near (Left) Standing Leg**: Planted firmly on the studio floor (`NEAR_FOOT = (376, 294)` on `FLOOR = 300.0`) with sculpted quadriceps, patella, and tibialis/gastrocnemius.
  - **Working Near (Left) Arm & 3D Dumbbell Trajectory (`DURATION = 160` frames @ `60 FPS`)**:
    - **Bottom Stretch (`r = 0.0`, frames `0..12` & `148..160`)**: Left arm extended straight down (`NEAR_SH = (284, 122) -> NEAR_EL = (280, 174) -> NEAR_HAND = (276, 224)`) for full scapular protraction and lat stretch.
    - **Top Contraction (`r = 1.0`, frames `64..84`)**: Left elbow driven high above the back (`NEAR_EL = (336, 96)`) with the heavy 3D dumbbell pulled tight beside the lateral ribcage/hip (`NEAR_HAND = (324, 152)`).
- **8 Highlighted Target Muscle Groups** (pulsing smoothly from warm orange `#FFF97316` at bottom stretch to vivid crimson `#FFF43F5E` at top contraction):
  1. **Latissimus dorsi** (`scale = 1.00`, primary mover)
  2. **Teres major** (`scale = 0.96`)
  3. **Teres minor** (`scale = 0.90`)
  4. **Infraspinatus** (`scale = 0.90`)
  5. **Trapezius (middle and lower)** (`scale = 0.88`)
  6. **Posterior deltoid** (`scale = 0.95`)
  7. **Brachialis** (`scale = 0.90`)
  8. **Brachioradialis** (`scale = 0.90`)

## Building & Publishing
```bash
python3 rive_animations/dumbbell_row/gen_dumbbell_row.py --publish
```
