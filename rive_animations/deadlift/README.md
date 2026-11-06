# Deadlift (`deadlift`)

Procedural 60 FPS, 16:9 (`640x360`, `FLOOR = 300.0`) HD Rive exercise animation for **Deadlift** (`id: "deadlift"`).

## Anatomy & Biomechanics
- **Camera & Viewpoint**: 3/4 rear-left isometric view on `FLOOR = 300.0`, with the athlete facing forward-left so the posterior chain (`Gluteus Maximus`, `Gluteus Medius`, `Hamstrings`, `Gastrocnemius`/`Soleus`, `Erector Spinae`, `Latissimus Dorsi`, `Trapezius`), lateral `Quadriceps` + white `Iliotibial (IT) Band`, and 3D Olympic barbell are clearly visible.
- **3D Olympic Barbell with 45-lb Bumper Plates (3-Layer Depth Split)**:
  - `FarBarbellPlate` (behind `FarRightLeg`): Far-right 45-lb Olympic bumper plate (`56x88`, rotated `-12°`) with 3D rim bevel, 4 radial spoke ridges, and collar.
  - `MidBarbellShaft` (between `FarRightLeg` and `NearLeftLeg`): Gunmetal/chrome steel bar shaft and pronated far hand.
  - `NearBarbellPlateAndSleeve` (foreground): Large near-left 45-lb Olympic bumper plate (`64x104`, rotated `-12°`, resting on `FLOOR = 300.0` at bottom setup `r = 0.0`), 4 radial spoke ridges, `45` marking, chrome collar, and protruding outer sleeve.
- **Conventional Deadlift Kinematics (`DURATION = 168` frames / `2.8s` @ `60 FPS`)**:
  - `0..14`: Bottom floor setup hold (`r = 0.0`, Panel A of reference)
  - `14..70`: Smooth, powerful concentric pull from floor to standing lockout (`r: 0.0 -> 1.0`)
  - `70..88`: Standing lockout hold at top (`r = 1.0`, Panel B of reference)
  - `88..154`: Controlled eccentric hip-hinge and knee-flexion lowering back to the floor (`r: 1.0 -> 0.0`)
  - `154..168`: Bottom floor setup hold (`r = 0.0`)
- **Activated Posterior-Chain & Leg Muscles (`muscle_t`)**:
  - **Gluteus Maximus & Gluteus Medius** (`scale = 1.00 / 0.92`, visible through semi-translucent dark compression shorts)
  - **Hamstrings (`Biceps Femoris` & `Semitendinosus`)** (`scale = 1.00`)
  - **Quadriceps (`Vastus Lateralis` & `Rectus Femoris`)** (`scale = 0.92`, separated from hamstrings by the white lateral IT band)
  - **Gastrocnemius & Soleus (Calves)** (`scale = 0.88`, above white Achilles tendons)
  - **Erector Spinae** (`scale = 0.78`)

## Build & Publish
```bash
python3 rive_animations/deadlift/gen_deadlift.py --publish
```
