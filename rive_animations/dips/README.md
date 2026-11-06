# Chest Dips (`dips`) — Procedural 60 FPS Rive Animation

High-definition 16:9 (`640x360`, `FLOOR = 300.0`) procedural Rive animation for **Chest Dips** (`id: "dips"` in `assets/data/exercises.json`), engineered in a 3/4 front-left isometric view on a commercial Dip Station / Captain's Chair.

## Biomechanics & Anatomical Highlights
- **Chest Dip Form ("More Forward Lean" + "Feet Behind the Body")**:
  - **Top Support (`d = 0.0`, frames `0..12` & `146..160`)**: Arms extended nearly straight down with hands locked onto the parallel dip handles (`FAR_HAND = (284, 162)`, `NEAR_HAND = (348, 166)`), torso upright (`~10°` forward tilt), and knees flexed below the hips.
  - **Bottom Deep Chest Dip (`d = 1.0`, frames `62..82`)**: Pronounced `~38°` forward torso lean (`MID_SH` dives forward-left while `HIP_CENTER` shifts back-right), elbows flexed to `~90°` above/behind the shoulders, thighs descending vertically from the hips, and lower legs bent horizontally behind the body.
- **Activated Muscle Groups** (pulsing smoothly between warm amber `#F97316` at top support and vivid crimson `#EF4444` / `#DC2626` at the bottom chest dip):
  1. **Pectoralis major (lower & upper heads)** (`scale = 1.00`, primary mover)
  2. **Anterior deltoid** (`scale = 0.92`, front shoulder cap)
  3. **Pectoralis minor / Serratus anterior / Lateral chest wall** (`scale = 0.85`, lateral sub-axillary band)
  4. **Triceps brachii (lateral & long heads)** (`scale = 0.85`, upper-extensor border of the upper arms)

## Building & Publishing
```bash
python3 rive_animations/dips/gen_dips.py --publish
```
