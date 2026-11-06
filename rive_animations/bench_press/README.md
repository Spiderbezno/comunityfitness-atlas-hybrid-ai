# Bench Press (`bench_press.riv`)

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) Rive animation for the **Bench Press** catalog exercise (`id: "bench_press"`).

## Build & Publish

```bash
python3 gen_bench_press.py --publish
```

This generates `bench_press.rml`, compiles `build/bench_press.riv`, copies it to `assets/animations/bench_press.riv`, and renders the 256×256 catalog thumbnail at `assets/animations/thumbnails/bench_press.png`.
