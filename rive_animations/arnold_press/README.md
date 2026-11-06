# Arnold Press (Rive)

`scene.rml` is generated — edit `gen_arnold_press.py`, never the RML by hand.

```bash
python3 gen_arnold_press.py            # regenerate scene.rml (prints diagnostics)
rive . --verify                        # 0 errors expected
python3 gen_arnold_press.py --publish  # build .riv, copy to assets/animations/arnold_press.riv,
                                       # render assets/animations/thumbnails/arnold_press.png
```

Seated front-view athlete (same character as `ab_wheel_rollout`) performing the Arnold press at
60 fps (216 frames = 3.6s loop). Arms are solved in 3D and projected: the elbows open from in front
of the chest to the sides while the dumbbells turn 180 degrees (plates edge-on -> face-on -> edge-on),
then press overhead. Activations: anterior + lateral deltoid, upper trapezius and triceps.
