# T-Bar Row (`tbar_row`) — Rive 7.3 Procedural Animation

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) HD 3D-shaded procedural Rive animation for **Landmine T-Bar Row** (`id: "tbar_row"`).

## Biomechanics & Anatomical Fidelity
- **3/4 Dorso-Lateral Bent-Over Hip-Hinge & Landmine Pivot (`r = 0.0 -> 1.0`)**:
  - **Bottom Stretch (`f = 0`, `r = 0.0`)**: The athlete maintains a stable `~35°` bent-over hip hinge straddling a floor-anchored landmine barbell (`pivot = (420, 296)`), with arms extended downward holding a close V-grip double handle beneath the chest while the lats and rhomboids stretch.
  - **Peak Row Contraction (`f = 72`, `r = 1.0`)**: Driving both elbows high and back along the ribcage while retracting the scapulae, the athlete pulls the 3 stepped Olympic weight plates and V-grip handle smoothly upward around the floor landmine pivot toward the lower sternum.
- **Highlighted Target & Synergist Muscle Groups**:
  1. **Latissimus dorsi** (Primary — broad V-taper dorsal wing sweeping from the thoracolumbar fascia to the humerus)
  2. **Middle & lower trapezius / Rhomboids** (Primary — diamond-shaped interscapular retractors on the upper thoracic back)
  3. **Teres major & Infraspinatus** (Synergists — thick scapular/axillary pulling bellies behind the shoulder joint)
  4. **Posterior deltoid** (Synergist — rear head of left & right shoulder caps)
  5. **Biceps brachii & Brachioradialis** (Synergists — elbow flexors driving the neutral V-grip pull)

## Build & Publish
```bash
python3 rive_animations/tbar_row/gen_tbar_row.py --publish
```
