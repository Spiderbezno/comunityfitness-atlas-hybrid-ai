# Side Plank (`side_plank`)

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) procedural Rive 7.3 animation for **Side Plank** (`id: "side_plank"`).

## Biomechanics & Reference Anatomy
- **3/4 Side Forearm Plank Alignment**:
  - **Planted Near (Right) Forearm under Right Shoulder**: The right elbow (`(414, 292)`) sits directly beneath the supporting right shoulder (`(416, 198)`) with the forearm planted flat on the studio mat (`FLOOR = 300.0`).
  - **Stacked Straight Legs & Top Hand on Hip**: Both legs extend straight to stacked feet on the left (`x ~ 144`), while the top (left) arm rests cleanly on the upper iliac crest (`(304, 188)`).
  - **Controlled Oblique Hip-Lift & Isometric Pulse (`r: 0.0 -> 1.0`)**: Elevates the pelvis and lateral waist by `~11 px` from a loaded bottom hover into a rock-solid straight diagonal line from ankles through hips to shoulders.
- **Highlighted Target Muscle Groups** (`#FFF97316` -> `#FFF43F5E`):
  1. **External & Internal Obliques** (Primary Core — lateral anti-flexion bridge along the lower & upper waist)
  2. **Rectus Abdominis (6-pack)** (Primary Core — anterior abdominal wall bracing the diagonal spine)
  3. **Gluteus Medius** (Primary Hip Abductor — lateral pelvic stabilization)
  4. **Supporting Deltoid** (Secondary — glenohumeral & scapular stabilization over the planted elbow)

## Build & Publish
```bash
python3 rive_animations/side_plank/gen_side_plank.py --publish
```
