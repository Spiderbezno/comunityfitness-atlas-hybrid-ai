# Burpee (`burpee`)

Procedural 60 FPS 16:9 (`640x360`, `FLOOR = 300.0`) Rive animation for the **Burpee** exercise.

## Camera & Biomechanics
- **Camera**: 3/4 rear-left isometric view matching the 4-stage anatomical reference chart, showcasing the athlete's sculpted dorsal back, deltoids, triceps, glutes, quadriceps, hamstrings, and calves.
- **4-Phase Movement Cycle (`240` frames / `4.0s` @ 60 FPS)**:
  1. **Phase 1 — Squat Thrust / Crouch 1 (`f = 0..14`)**: Deep squat crouch with both hands planted flat on `FLOOR = 300.0`, knees tucked toward the chest behind the triceps, and heels lifted on the balls of the feet.
  2. **Phase 2 — High Plank & Push-up Dip (`f = 44..112`)**: Explosive kick-back into a rigid straight-body high plank (`f = 44..58`), followed by a controlled chest-to-floor push-up dip (`f = 82..88`) and press back to high plank (`f = 112`).
  3. **Phase 3 — Frog Jump In / Crouch Return (`f = 138..150`)**: Feet hop forward under the hips into the coiled low squat crouch, loading the quadriceps, glutes, and calves.
  4. **Phase 4 — Explosive Vertical Jump with Overhead Reach (`f = 164..196`)**: Triple extension through the hips, knees, and ankles into an airborne vertical jump with pointed toes and both arms reaching high overhead before landing softly (`f = 214`) and returning smoothly to Crouch 1 (`f = 240`).
- **Activated Muscles**:
  - **Deltoids & Triceps brachii** (plank stabilization, push-up press, and overhead jump reach)
  - **Trapezius, Rhomboids & Erector spinae** (dorsal spinal stabilization)
  - **Gluteus maximus** (visible through semi-translucent compression shorts)
  - **Quadriceps (vastus lateralis / rectus femoris) & Hamstrings**
  - **Gastrocnemius & Soleus** (explosive plantarflexion during kick-back and vertical jump)

## Usage
```bash
python3 gen_burpee.py            # Regenerate scene.rml
python3 gen_burpee.py --publish  # Compile burpee.riv and render 256x256 thumbnail
```
