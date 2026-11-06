# Tricep Pushdown (`tricep_pushdown`)

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) procedural Rive 7.3 animation for **Tricep Pushdown** (`id: "tricep_pushdown"`).

## Biomechanics & Reference Anatomy
- **3/4 Standing High-Pulley Cable Tricep Pushdown**:
  - **Braced Athletic Stance (`~8 deg` forward torso lean on `FLOOR = 300.0`)**: The athlete stands facing a high-pulley cable tower on the right (`x ~ 440`) with knees slightly soft and spine neutral.
  - **Pinned Humeri & Pure Circular Forearm Arc (`r: 0.0 -> 1.0`)**:
    - Both upper arms remain pinned vertically at the sides of the ribcage (`NEAR_EL = (298, 146)`) so zero shoulder flexion/extension occurs.
    - `r = 0.0` (**Top Eccentric Start**): Elbows flexed (`~ -26 deg` above horizontal) with the angled V-bar handle at chest height (`(357, 120)`).
    - `r = 1.0` (**Bottom Peak Lockout**): Forearms sweep downward in a circular arc around the fixed elbows to full vertical extension beside the thighs (`(330, 175)`), lifting the weight stack along the chrome guide rods.
- **Highlighted Target Muscle Groups** (`#FFF97316` -> `#FFF43F5E`):
  1. **Triceps Brachii — Lateral Head, Long Head & Medial Head** (Primary Mover — prominent lateral horseshoe & posterior long-head belly)
  2. **Anconeus & Forearm Extensors** (Secondary — terminal elbow lockout & isometric wrist stabilization)

## Build & Publish
```bash
python3 rive_animations/tricep_pushdown/gen_tricep_pushdown.py --publish
```
