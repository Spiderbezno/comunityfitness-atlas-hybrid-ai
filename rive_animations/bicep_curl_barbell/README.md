# Barbell Bicep Curl (`bicep_curl_barbell.riv`)

60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) Rive animation for the **Barbell Bicep Curl** catalog exercise (`id: "bicep_curl_barbell"`).

## Build & Publish

```bash
python3 gen_bicep_curl_barbell.py --publish
```

This generates `bicep_curl_barbell.rml`, compiles `build/bicep_curl_barbell.riv`, copies it to `assets/animations/bicep_curl_barbell.riv`, and renders the 256×256 catalog thumbnail at `assets/animations/thumbnails/bicep_curl_barbell.png`.
