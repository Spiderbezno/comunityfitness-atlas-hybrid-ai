# Bench Dips (`bench_dips.riv`)

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) Rive animation for the **Bench Dips** catalog exercise (`id: "bench_dips"`).

## Build & Publish

```bash
python3 gen_bench_dips.py --publish
```

This generates `bench_dips.rml`, compiles `build/bench_dips.riv`, copies it to `assets/animations/bench_dips.riv`, and renders the 256×256 catalog thumbnail at `assets/animations/thumbnails/bench_dips.png`.
