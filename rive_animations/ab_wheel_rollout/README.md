# Ab Wheel Rollout (Rive)

`scene.rml` is generated — edit `gen_ab_wheel.py`, never the RML by hand.

```bash
python3 gen_ab_wheel.py            # regenerate scene.rml (prints rig diagnostics)
rive . --verify                    # 0 errors expected
python3 gen_ab_wheel.py --publish  # build .riv, copy to assets/animations/ab_wheel_rollout.riv,
                                   # render assets/animations/thumbnails/ab_wheel_rollout.png
```

The thumbnail is rendered at 2x (`--viewport=1280x720 --fit=contain`, `--advance=0.6s`),
cropped square and downscaled to 256 px with macOS `sips`. Flutter maps
`assets/animations/<name>.riv` to `assets/animations/thumbnails/<name>.png`
(`exerciseThumbnailAsset`), so other exercises gain a catalog thumbnail by adding a PNG there.
