# Diamond Push Up (`push_up_diamond`) — Rive 7.3 Animation

## Overview
- **Exercise ID**: `push_up_diamond` (`Diamond Push Up` in `assets/data/exercises.json`)
- **Canvas**: `640x360` (16:9), `FLOOR = 300.0`, `60 FPS`, `160` frames (`2.67s` loop)
- **Camera**: 3/4 front-right isometric view matching the 2-panel anatomical reference chart.
- **Activated Target Muscles**:
  1. **Triceps brachii** (Primary — lateral & long head crescent on upper arm, `scale = 1.00`)
  2. **Lower pectoralis major** (Primary/Synergist — sternocostal inner/lower chest head, `scale = 0.90`)
  3. **Upper pectoralis major** (Primary/Synergist — clavicular upper/inner chest head, `scale = 0.88`)
  4. **Anterior deltoid** (Primary/Synergist — front shoulder cap, `scale = 0.88`)
  5. **Biceps brachii, short head** (Dynamic Stabilizer — inner/ventral upper arm stabilizer, `scale = 0.78`)

## Usage
```bash
python3 gen_push_up_diamond.py --publish
```
