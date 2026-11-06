# Abdominal Crunch (`crunch`)

Procedural 60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) HD Rive exercise animation for **Abdominal Crunch** (`id: "crunch"`).

## Anatomy & Biomechanics
- **Camera & Floor Mat**: Side / slight 3/4 right-side supine profile on a dark beveled exercise mat on `FLOOR = 300.0`, with the athlete's head on the left and bent knees / planted bare feet on the right.
- **Anchored Lower Body (`~85°` Knee Flexion)**:
  - Glutes and hips in dark navy/slate compression shorts (`SHORTS`) resting firmly on the floor mat (`x ~ 330..394, y ~ 240..294`) with diagonal mid-thigh hems (`x ~ 408..432`).
  - Subtle 3/4 depth offset between the **Far (Left) Leg** (`SKIN_FAR`, `FAR_KNEE = (424, 166)`) and **Near (Right) Leg** (`SKIN`, `NEAR_KNEE = (434, 170)`), with sculpted distal quadriceps (`Rectus Femoris`, `Vastus Lateralis`), rounded patella, lower-leg `Tibialis Anterior` and `Gastrocnemius`/`Soleus` calf curves, ankle malleolus, and bare feet (`x ~ 480..538, y ~ 274..294`) planted flat on the mat.
- **Thoracic Spinal Flexion Crunch (`DURATION = 150` frames / `2.5s` @ `60 FPS`)**:
  - `0..12`: Bottom supine stretch hold (`r = 0.0`)
  - `12..62`: Concentric abdominal crunch upward (`r: 0.0 -> 1.0`)
  - `62..80`: Peak isometric abdominal contraction hold at top (`r = 1.0`)
  - `80..138`: Controlled eccentric lowering back to supine (`r: 1.0 -> 0.0`)
  - `138..150`: Bottom supine hold (`r = 0.0`)
  - Stationary lower lumbar base (`x ~ 274..336, y ~ 282..294`) stays pressed into the mat while the thoracic ribcage, sculpted `Pectoralis Major`, head (with dark navy hair cap), and hands-behind-head arms curl smoothly upward-right (`~34°` thoracic flexion + `+10°` cervical flexion).
- **Activated Core Muscles (`muscle_t`)**:
  - **Rectus Abdominis** (`scale = 1.0`): Sculpted 6-pack abdominal segments along the anterior contour that shorten horizontally (`scaleX: 1.00 -> 0.72`) and thicken vertically (`scaleY: 1.00 -> 1.08`) during the crunch.
  - **External & Internal Obliques** (`scale = 0.92`): Broad sculpted lateral abdominal muscle plate spanning from the costal arch to the iliac crest and shorts waistband.

## Build & Publish
```bash
python3 rive_animations/crunch/gen_crunch.py --publish
```
