# Push Up (`push_up`) — Rive 7.3 Animation

## Overview
- **Exercise ID**: `push_up` (`Push Up` in `assets/data/exercises.json`)
- **Canvas**: `640x360` (16:9), `FLOOR = 300.0`, `60 FPS`, `160` frames (`2.67s` loop)
- **Camera**: 3/4 front-right isometric view matching the 2-panel anatomical reference chart.
- **Activated Target Muscles**:
  1. **Pectoralis major (lower)** (Primary — sternocostal chest head, `scale = 1.00`)
  2. **Pectoralis major (upper)** (Primary — clavicular chest head, `scale = 0.96`)
  3. **Anterior deltoid** (Primary/Synergist — front shoulder cap, `scale = 0.92`)
  4. **Triceps brachii** (Primary/Synergist — lateral & long head along dorsal upper arm, `scale = 0.94`)

## Usage
```bash
python3 gen_push_up.py --publish
```
