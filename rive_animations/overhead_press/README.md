# Dumbbell Overhead Press (`overhead_press`)

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) procedural Rive 7.3 animation for **Dumbbell Overhead Press** (`id: "overhead_press"`).

## Biomechanics & Reference Anatomy
- **Left Panel (`r = 0.0`, Frames `0..12` & `148..160` — Goalpost Shoulder-Rack Position)**:
  - Standing 3/4 front-left athlete with bare feet planted on `FLOOR = 300.0`.
  - Upper arms abducted outward near shoulder level (`~14°` below horizontal), forearms vertical (`~90°` elbow bend) holding a pair of 3D double-plate black dumbbells just above shoulder/ear level with a pronated grip.
- **Right Panel (`r = 1.0`, Frames `64..84` — Full Overhead Lockout)**:
  - Both arms press the dumbbells vertically overhead until the elbows lock out alongside the head/ears and the inner dumbbell plates converge above the crown of the head.
- **All 4 Labeled Target Muscle Groups**:
  1. **Lateral deltoids** (Primary — multipennate middle head of both shoulder caps)
  2. **Anterior deltoids** (Primary — front clavicular head of both shoulder caps)
  3. **Triceps brachii** (Primary/Synergist — lateral/long head on the outer-posterior aspect of both upper arms)
  4. **Serratus anterior** (Secondary/Stabilizer — 3 saw-toothed slips on the lateral ribcage below the outer pectoralis major)

## Build & Publish
```bash
python3 rive_animations/overhead_press/gen_overhead_press.py --publish
```
