# Decline Bench Press (`decline_bench_press`)

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) HD procedural Rive exercise animation for **Decline Bench Press** (`id: "decline_bench_press"` in `assets/data/exercises.json`).

## Anatomical & Biomechanical Highlights
- **Viewpoint**: 3/4 front-left isometric view matching the 2-panel anatomical reference illustration.
- **3D Decline Weight Bench with Leg-Hold Rollers & Barbell Rack Uprights**:
  - Upholstered dark-slate decline pad elevated at the front-left hip/knee end and sloping downward-right toward the lower shoulder/head end, with a white/silver headrest pad.
  - Dual white/silver foam **Upper Knee Rollers** tucked beneath the knees and dual **Lower Shin/Ankle Rollers** resting across the front of the lower shins to anchor the athlete on the decline slope.
  - White/silver powder-coated steel frame with front support post, diagonal floor base rail, and two vertical **Barbell Rack Uprights** with J-hook slots flanking the shoulder/head end.
- **Primary & Secondary Muscle Activation (`MUSCLE_LOW` `#FFF97316` -> `MUSCLE_HIGH` `#FFF43F5E`)**:
  1. **Pectoralis major (lower)** (`scale = 1.00`): Primary sternocostal-abdominal lower chest plates on both sides.
  2. **Pectoralis major (upper)** (`scale = 0.82`): Clavicular upper-chest bands above the lower pectoral plates.
  3. **Anterior deltoid** (`scale = 0.88`): Front shoulder caps on both near and far shoulders.
  4. **Triceps brachii** (`scale = 0.88`): Lateral and long heads along the outer/posterior aspect of both upper arms.

## Build & Publish
```bash
python3 rive_animations/decline_bench_press/gen_decline_bench_press.py --publish
```
