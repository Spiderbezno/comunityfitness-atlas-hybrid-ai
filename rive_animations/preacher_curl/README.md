# Preacher Curl (`preacher_curl`)

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) procedural Rive 7.3 animation for **Seated EZ-Bar Preacher Curl** (`id: "preacher_curl"`).

## Biomechanics & Reference Anatomy
- **Left Panel (`r = 0.0`, Frames `0..12` & `148..160` — Full Arm Extension on Preacher Pad)**:
  - Seated 3/4 front-right athlete leaning chest-first against a 3D angled preacher bench with white/silver steel uprights and black barbell catch cradles.
  - Both upper arms and elbows rest immobilized down the sloped preacher cushion while the forearms extend forward-downward holding a loaded cambered EZ-curl barbell with a supinated grip.
- **Right Panel (`r = 1.0`, Frames `64..84` — Peak Biceps Contraction)**:
  - With the upper arms strictly anchored on the pad to prevent shoulder momentum, both forearms curl the EZ-bar upward in a clean arc to chin/shoulder height.
- **Highlighted Target Muscle Groups**:
  1. **Biceps brachii (short head & long head)** (Primary — prominent two-headed anterior upper-arm belly on both arms)
  2. **Brachialis** (Primary — deep distal-lateral elbow flexor wedged beneath the biceps on the preacher pad)
  3. **Brachioradialis** (Secondary/Synergist — radial forearm belly extending across the elbow crease)

## Build & Publish
```bash
python3 rive_animations/preacher_curl/gen_preacher_curl.py --publish
```
