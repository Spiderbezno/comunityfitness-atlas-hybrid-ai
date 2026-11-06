# Pronated Wide-Grip Pull Up (`pull_up`) — Rive 7.3 Animation

## Overview
- **Exercise ID**: `pull_up` (`Pull Up` in `assets/data/exercises.json`)
- **Canvas**: `640x360` (16:9), `FLOOR = 300.0`, `60 FPS`, `168` frames (`2.80s` loop)
- **Camera**: 3/4 rear-right isometric perspective matching the 2-panel anatomical reference chart.
- **Equipment**: 3D white/silver floor-mounted pull-up rack / power tower with two full-height vertical square-tube uprights (`x = 352..369` and `x = 426..445`), cantilevered horizontal top beams, drop brackets, and a wide dark-charcoal steel pull-up bar (`(202, 50.8) -> (366, 39.2)`) with rubber grip sleeves.
- **Activated Target Muscles**:
  1. **Latissimus dorsi** (Primary, bilateral sweeping V-taper wings, `scale = 1.00`)
  2. **Teres major** (Primary, bilateral upper-lateral scapular bundles, `scale = 0.94`)
  3. **Teres minor** (Secondary, bilateral oblique cuff bands, `scale = 0.86`)
  4. **Infraspinatus** (Secondary, bilateral infraspinous fossa plates, `scale = 0.86`)
  5. **Trapezii (middle and lower)** (Secondary, kite-shaped mid/lower traps, `scale = 0.88`)
  6. **Rhomboids (deep)** (Secondary, bilateral medial scapular retractors, `scale = 0.84`)
  7. **Levator scapulae (deep)** (Secondary, bilateral neck-to-scapula bands, `scale = 0.80`)
  8. **Posterior deltoid** (Secondary, bilateral rear deltoid caps, `scale = 0.84`)
  9. **Biceps brachii & Brachialis** (Secondary, bilateral upper arm flexors, `scale = 0.86`)
  10. **Brachioradialis** (Secondary, bilateral radial forearm flexors, `scale = 0.88`)

## Usage
```bash
python3 gen_pull_up.py --publish
```
