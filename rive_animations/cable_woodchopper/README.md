# Cable Woodchopper (`cable_woodchopper`)

Procedural 60 FPS 16:9 (`640x360`, `FLOOR = 300.0`) Rive animation for the **Cable Woodchopper** (`id: "cable_woodchopper"`).

## Biomechanics & 4-Phase Reference Structure

1. **Set Up (`c = 0.0`)**:
   - Wide athletic stance away from the cable pulley tower on the left, with both feet planted on `FLOOR = 300.0`.
   - Trunk, pelvis, and shoulders turned slightly toward the left pulley tower; both arms extended holding the stirrup D-handle at mid-torso height (`PULLEY = (204.0, 162.0)`).
2. **Start The Turn (`c = 0.5`)**:
   - Hips and trunk rotate axially from left to right through the front-facing view.
   - Both arms sweep the D-handle horizontally across the midline at oblique/mid-torso height; back (left) heel begins to lift.
3. **Chop Across (`c = 1.0`)**:
   - Full hip and trunk axial rotation to the right.
   - Arms pull the handle across past the right flank while the back (left) foot pivots onto the ball of the foot with the heel lifted high and the left knee driving inward-right.
   - The cable tower's top weight stack rises along the dual chrome guide rods as the cable extends.
4. **Control Back (`c = 1.0 -> 0.0`)**:
   - Smooth eccentric return along the same horizontal path back to the Set Up position as the weight stack lowers.

## Activated Muscles (`muscle_t`)

- **Primary**: External & Internal Obliques (sculpted lateral abdominal wall with diagonal fiber striations on both flanks, transitioning from `#CCF97316` warm orange to `#F2EF4444` peak crimson).
- **Secondary**: Rectus Abdominis / Transversus Abdominis core wall, Serratus Anterior, and Anterior/Lateral Deltoids.

## Regenerating & Publishing

```bash
python3 rive_animations/cable_woodchopper/gen_cable_woodchopper.py --publish
```

This regenerates `scene.rml`, compiles `assets/animations/cable_woodchopper.riv`, and renders `assets/animations/thumbnails/cable_woodchopper.png` (`256x256`).
