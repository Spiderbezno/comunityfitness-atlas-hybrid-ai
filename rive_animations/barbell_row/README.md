# Barbell Row (Rive)

Bent-over barbell row seen from behind the athlete's left shoulder (rear three-quarter view), 60 fps, 3.0 s loop.

The character is the same one used in `ab_wheel_rollout` and `arnold_press`. Activations go from orange to red as the bar reaches the lower chest:

- Latissimus dorsi
- Trapezius (mid/lower)
- Infraspinatus and teres major
- Posterior deltoid
- Biceps/brachialis

## How it works

- The body (legs, hips, torso and head) is posed in 3D and projected straight into artboard coordinates.
- The arms are solved with two-bone IK toward the bar. Each segment is a keyed node (rotation, foreshortening via `scaleX`, outline flip via `scaleY`).
- The barbell plates are projected circles stacked into slabs.

## Usage

```sh
python3 gen_barbell_row.py            # regenerate scene.rml
python3 gen_barbell_row.py --publish  # + build .riv, copy to assets, render the 256px thumbnail
```

The publish step writes:

- `assets/animations/barbell_row.riv`
- `assets/animations/thumbnails/barbell_row.png`
