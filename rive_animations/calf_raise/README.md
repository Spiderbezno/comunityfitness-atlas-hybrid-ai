# Standing Calf Raise (`calf_raise`)

Procedural 60 FPS 16:9 (`640x360`, `FLOOR = 300.0`) Rive animation for the **Standing Calf Raise** (`id: "calf_raise"`).

## Camera, Equipment & Biomechanics

1. **Camera Angle**:
   - **3/4 Rear-Right Isometric View** showcasing the dorsal back (`Trapezius`, `Infraspinatus`, `Latissimus Dorsi`, `Erector Spinae`), `Deltoids`, `Triceps Brachii`, glutes in dark compression shorts, posterior thighs (`Hamstrings` and `Iliotibial Band`), and the posterior calves of both legs.
2. **Equipment**:
   - **3D Calf-Raise Step Platform**: Beveled metallic silver-grey platform (`#FFCBD5E1 -> #FF475569`) with a dark non-slip rubber top mat resting on `FLOOR = 300.0`.
   - **Dual 3D Cast-Iron Dumbbells**: Held in neutral hammer grips at both sides (near-right dumbbell at the right hip/thigh; far-left dumbbell protruding to the left of the far glute).
3. **Plantarflexion & Gastrocnemius Contraction (`r` in `[0.0, 1.0]`)**:
   - **Forefoot / Toes Anchor**: The balls and toes of both feet (`BALL_NEAR = (323.3, 285.5)`, `BALL_FAR = (304.3, 282.5)`) remain anchored on the black non-slip rubber mat along the back-left edge of the step platform.
   - **Bottom Stretch (`r = 0.0`)**: Heels hang off the left edge of the step in dorsiflexion stretch (`arch_rot = -12°`).
   - **Peak Tiptoe Contraction (`r = 1.0`)**: Ankles plantarflex through a `60°` arc (`arch_rot = +48°`) along a concentric circular radius (`HINGE_LOCAL = (-21.0, -3.5)`) around the balls of the feet, lifting the heels, ankles, shins, knees, thighs, pelvis, torso, head, and dumbbells both **upward (`dy = -18.9 px`) and forward-right (`dx = +9.8 px`)** with zero joint separation, while both **Gastrocnemius** bellies dynamically shorten and bulge (`scaleY: 1.0 -> 0.87, scaleX: 1.0 -> 1.08, dy: 0 -> -3.8 px`) above the elongating silver-white **Achilles tendons**.

## Activated Muscles (`muscle_t`)

- **Primary**: **Gastrocnemius (Medial Head & Lateral Head)** on both legs, with central inter-head sulcus and pennate striations transitioning from `#CCF97316` warm orange at the bottom stretch (`r = 0.0`) to `#F2F43F5E` intense crimson at the peak tiptoe contraction (`r = 1.0`).
- **Secondary**: **Soleus** flanking the lower calf beside the silver-white **Achilles (Calcaneal) Tendon**.

## Regenerating & Publishing

```bash
python3 rive_animations/calf_raise/gen_calf_raise.py --publish
```

This regenerates `scene.rml`, compiles `assets/animations/calf_raise.riv`, and renders `assets/animations/thumbnails/calf_raise.png` (`256x256`).
