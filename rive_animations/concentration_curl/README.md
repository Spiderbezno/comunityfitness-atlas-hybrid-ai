# Concentration Curl (`concentration_curl`)

Procedural 60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) HD Rive exercise animation for **Concentration Curl** (`id: "concentration_curl"`).

## Anatomy & Biomechanics
- **Camera & Equipment**: 3/4 front-right isometric view featuring a 3D flat weight bench (`(130, 174)` to `(356, 194)`) with dark-slate upholstery, white/silver steel frame, rear T-leg, horizontal cross-beam, and angled front leg (`(316, 196) -> (344, 284)`).
- **Wide-Stance Seated Athlete**:
  - **Near (Right) Leg**: Extends forward-left from the right hip `(276, 172)` to the right knee `(308, 198)` with the bare right foot planted on `FLOOR = 300.0` at `(300, 296)`.
  - **Far (Left) Leg**: Extends outward-right from the left hip `(320, 170)` to the left knee `(396, 188)` with a prominent inner gastrocnemius calf belly and bare left foot planted at `(388, 276)`.
  - **Forward-Hinged Torso & Bracing Right Arm**: Torso leans forward over the hips with sculpted pectorals, rectus abdominis/obliques, downward-looking 3/4 head `(366, 74)`, and stationary right arm bracing with the right hand cupping the right knee `(308, 192)`.
- **Working Left Arm & 3D Double-Plate Dumbbell (`160` frames / `2.67s` @ `60 FPS`)**:
  - **Braced Left Upper Arm**: Locked against the inner left thigh (`SHOULDER = (362, 104)` to `ELBOW = (364, 166)`).
  - **Pivoting Left Forearm**: Curls from full extension (`WRIST = (358, 224)` at `r = 0.0`) through `WRIST = (342, 178)` (`r = 0.5`) up and inward to peak contraction (`WRIST = (332, 132)` at `r = 1.0`).
- **Activated Muscles (`muscle_t`)**:
  - **Biceps brachii — short head** (`scale = 1.0`)
  - **Biceps brachii — long head** (`scale = 1.0`)
  - **Brachialis** (`scale = 0.92`)
  - **Brachioradialis** (`scale = 0.88`)

## Build & Publish
```bash
python3 rive_animations/concentration_curl/gen_concentration_curl.py --publish
```
