# Bicycle Crunch (`bicycle_crunch.riv`)

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) Rive animation for the **Bicycle Crunch** catalog exercise (`id: "bicycle_crunch"`).

## Build & Publish

```bash
python3 gen_bicycle_crunch.py --publish
```

This generates `bicycle_crunch.rml`, compiles `build/bicycle_crunch.riv`, copies it to `assets/animations/bicycle_crunch.riv`, and renders the 256×256 catalog thumbnail at `assets/animations/thumbnails/bicycle_crunch.png`.
