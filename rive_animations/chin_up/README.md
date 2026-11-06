# Chin Up (`chin_up`)

Procedural 60 FPS 16:9 (`640x360`, `FLOOR = 300.0`) Rive animation for the **Chin Up** (`id: "chin_up"`).

## Camera, Equipment & Biomechanics

1. **Camera Angle**:
   - **3/4 Rear-Right Isometric View** matching the 2-panel anatomical reference chart, showing the athlete hanging from a 3D wall-mounted chin-up bar above `FLOOR = 300.0`.
2. **Equipment**:
   - **3D Wall-Mounted Chin-Up Bar Rig (`y ~ 46..50`)**: Two vertical white/silver wall-mounting plates (`(263..281, 18..76)` and `(427..445, 21..81)`), two horizontal white/silver support beams with under-bar drop brackets, and a dark-charcoal steel bar (`(160, 52) -> (416, 57)`) with angled outer handles and foam grip sleeves.
   - **Stationary Supinated (Underhand) Grip**: Both hands remain anchored on the bar (`FAR_HAND = (254.0, 46.5)`, `NEAR_HAND = (306.0, 48.0)`) in an underhand grip (palms facing the athlete) with zero wrist drift.
3. **Dead Hang to Chin-Over-Bar Kinematics (`r` in `[0.0, 1.0]`, `168` frames / `2.8s` @ `60 FPS`)**:
   - **Dead Hang (`r = 0.0`, frames `0..12` & `154..168`)**: Arms extended overhead to the bar, head nested between the upper arms (`y = 66..96`), and flexed knees (`~18°`) with hanging bare feet cleanly in the air (`y ~ 290`, `10 px` above `FLOOR = 300.0`).
   - **Chin-Over-Bar Peak (`r = 1.0`, frames `68..86`)**: The body rises by `48 px` (`body_dx = -6.0, body_dy = -48.0`) so the head and chin (`y = 18..46`) clearly clear above the horizontal bar (`y = 47`) while the elbows drive down and outward (`NEAR_EL = (330.6, 73.6)`) into the acute V-bent chin-up posture.

## Activated Muscles (`muscle_t`)

- **Primary**: **Latissimus Dorsi** (`scale = 1.0`), **Teres Major** (`scale = 0.96`), **Biceps Brachii** (`scale = 0.96`), **Brachialis** (`scale = 0.88`), and **Brachioradialis** (`scale = 0.88`), transitioning from warm glowing orange (`#BFF97316`) at the dead hang to intense crimson-red (`#F5F43F5E`) at peak contraction.
- **Secondary**: **Middle & Lower Trapezius** (`scale = 0.86`), **Rhomboids** (`scale = 0.82`), **Posterior Deltoid** (`scale = 0.76`), **Lower Pectoralis Major** (`scale = 0.75`), and **Triceps Brachii (Long Head)** (`scale = 0.72`).

## Regenerating & Publishing

```bash
python3 rive_animations/chin_up/gen_chin_up.py --publish
```

This regenerates `scene.rml`, compiles `assets/animations/chin_up.riv`, and renders `assets/animations/thumbnails/chin_up.png` (`256x256`).
