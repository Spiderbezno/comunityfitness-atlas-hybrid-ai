# Forearm Plank (`plank`)

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) procedural Rive 7.3 animation for **Forearm Plank** (`id: "plank"`).

## Biomechanics & Reference Anatomy
- **Textbook Hollow-Body Forearm Plank Alignment (Avoiding the 4 Compensations)**:
  - **Elbows planted directly under shoulders** (`x = 408, y = 294`) with horizontal forearms and neutral fists resting flat on `FLOOR = 300.0`.
  - **Neutral spine & ribs-down lock**: Eliminates lumbar hyperextension (`quiebre lumbar`), dropped pelvis (`pelvis caída`), flared ribs (`costillas disparadas`), and thoracic hyperkyphosis (`hipercifosis`).
  - **Active engagement cycle (`r: 0.0 -> 1.0`)**: Smoothly lifts from a soft setup hover into a locked isometric forearm plank with rhythmic diaphragmatic core breathing and full anti-extension tension.
- **Highlighted Target Muscle Groups**:
  1. **Rectus abdominis** (Primary Core — ventral 6-pack abdominal wall with tendinous inscriptions)
  2. **External obliques** (Primary Core — lateral waist & rib-down stabilization)
  3. **Serratus anterior & Anterior deltoid** (Secondary — scapular protraction through the planted elbows)
  4. **Gluteus maximus & Quadriceps (`Rectus femoris` / `Vastus lateralis`)** (Secondary — posterior pelvic tilt & knee lock)

## Build & Publish
```bash
python3 rive_animations/plank/gen_plank.py --publish
```
