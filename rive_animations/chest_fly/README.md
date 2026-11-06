# Incline Dumbbell Chest Fly (`chest_fly`)

Procedural 60 FPS 16:9 (`640x360`, `FLOOR = 300.0`) Rive animation for the **Chest Fly** (`id: "chest_fly"`).

## Camera, Equipment & Biomechanics

1. **Camera Angle**:
   - **3/4 Front-Left Isometric View** matching the 2-panel anatomical reference chart, showing the athlete reclined at `~38°` on an upholstered incline weight bench with a white/silver powder-coated steel frame resting on `FLOOR = 300.0`.
2. **Equipment**:
   - **3D Incline Weight Bench**: White/silver powder-coated steel frame (`#FFF8FAFC -> #FF64748B`) with an arched front floor stabilizer, diagonal main spine beam, rear floor stabilizer leg, telescoping backrest support strut, dark slate upholstered seat pad, and `~38°` inclined backrest pad.
   - **Dual 3D Cast-Iron Dumbbells**: Double-plate dumbbells held in neutral fly grips (palms facing inward/upward) in both hands.
3. **Wide Barrel-Hugging Fly Kinematics (`r` in `[0.0, 1.0]`, `168` frames / `2.8s` @ `60 FPS`)**:
   - **Bottom Stretch (`r = 0.0`, frames `0..12` & `154..168`)**: Arms open wide to the sides with a soft elbow bend (`~22°`), stretching the pectorals across the ribcage (`Far` wrist at `(234, 80)`, `Near` wrist at `(424, 162)`).
   - **Wide Barrel-Hugging Arc (`0.0 < r < 1.0`, frames `12..68` & `84..154`)**: Wrists sweep along a polar circular trajectory around each shoulder (`SHOULDER_FAR = (304, 114)`, `SHOULDER_NEAR = (350, 134)`) so the elbows bow wide outward at mid-rep (`r = 0.5`), maintaining a true wide fly arc rather than pressing.
   - **Peak Overhead Contraction (`r = 1.0`, frames `68..84`)**: Both arms reach overhead above the upper chest (`Far` wrist at `(318, 36)`, `Near` wrist at `(348, 48)`) holding the two 3D dumbbells parallel side-by-side while the pectorals dynamically bulge inward toward the sternum.

## Activated Muscles (`muscle_t`)

- **Primary**: **Upper Pectoralis Major (Clavicular Head)** (`scale = 1.0`) and **Sternocostal Pectoralis Major** (`scale = 0.72`) on both right (far) and left (near) sides of the chest, transitioning from warm glowing orange (`#BFF97316`) at the wide stretch to intense crimson-red (`#F5F43F5E`) at peak contraction.
- **Secondary**: **Anterior Deltoid** (`scale = 0.92`, front shoulder caps) and **Biceps Brachii (Short Head)** (`scale = 0.82`, inner/anterior upper arms stabilizing the elbow joint against horizontal adduction torque).

## Regenerating & Publishing

```bash
python3 rive_animations/chest_fly/gen_chest_fly.py --publish
```

This regenerates `scene.rml`, compiles `assets/animations/chest_fly.riv`, and renders `assets/animations/thumbnails/chest_fly.png` (`256x256`).
