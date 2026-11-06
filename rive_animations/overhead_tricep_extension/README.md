# Overhead Tricep Extension (`overhead_tricep_extension`)

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) procedural Rive 7.3 animation for **Standing Cable Rope Overhead Tricep Extension** (`id: "overhead_tricep_extension"`).

## Biomechanics & Reference Anatomy
- **Bottom Behind-Neck Stretch (`r = 0.0`, Frames `0..12` & `148..160` — Right Panel of Reference)**:
  - Standing 3/4 front-left athlete with bare feet planted on `FLOOR = 300.0` in front of a low floor cable pulley (`(394, 294)`).
  - Upper arms remain elevated beside the head/ears while the elbows flex deeply so the hands hold the two flanged black rope ends behind the neck/upper back, placing the long head of the triceps brachii under deep stretch.
- **Top Overhead Lockout (`r = 1.0`, Frames `64..84` — Left Panel of Reference)**:
  - Both forearms extend overhead in an isolated elbow-extension arc until the arms lock out above the crown of the head, pulling the diagonal steel cable and dual braided rope taut.
- **Target Muscle Group**:
  - **Triceps brachii** (Primary — sculpted long head and lateral/medial heads on both upper arms, pulsing from warm orange `#FFF97316` to intense crimson `#FFF43F5E`).

## Build & Publish
```bash
python3 rive_animations/overhead_tricep_extension/gen_overhead_tricep_extension.py --publish
```
