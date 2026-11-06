# Bulgarian Split Squat (`bulgarian_split_squat`)

Procedural 60 FPS 16:9 (`640x360`, `FLOOR = 300.0`) Rive animation of the **Bulgarian Split Squat** in a 3/4 front-right view with a 3D isometric flat weight bench on the left.

## Anatomy & Kinematics
- **Front (Near / Right) Leg**: Planted flat on `FLOOR = 300.0` (`x ~ 412`), solved every frame with two-bone IK (`Hip -> Knee -> Ankle`) from upright extension at top (`d = 0.0`) to a `~90°` knee bend with thigh parallel to the floor at bottom (`d = 1.0`).
- **Rear (Far / Left) Leg**: Instep/toes anchored on top of the 3/4 weight bench pad (`x ~ 290, y ~ 196`), solved every frame with two-bone IK (`Hip -> Knee -> Ankle`) so the rear knee drops smoothly toward the floor (`y ~ 266`) in front of the bench at the bottom of the squat.
- **Activated Muscles**:
  - **Quadriceps femoris** (vastus lateralis, rectus femoris, vastus medialis teardrop on the front thigh + rectus femoris on the rear thigh)
  - **Gluteus maximus** (posterior hip activation)
  - **Adductor magnus & Hamstrings** (posterior/medial thigh activation strips on both legs)
  - **Gastrocnemius & Soleus** (calf activation on both legs)

## Build & Publish
```bash
python3 gen_bulgarian_split_squat.py --publish
```
