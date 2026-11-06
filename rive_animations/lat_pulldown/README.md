# Lat Pulldown (`lat_pulldown`) — HD 3D Rive 7.3 Animation

Procedural 60 FPS (`640x360`, `FLOOR = 300.0`) Rive 7.3 animation for **Lat Pulldown** (`id: "lat_pulldown"`), featuring our canonical 3/4 rear-left CommunityFitness mannequin seated at a commercial lat pulldown cable station.

## Biomechanics & Activated Muscles
- **Perspective**: 3/4 rear-left isometric view showing the full dorsal anatomy, seated bench with slanted rear stabilizer leg, vertical cable tower with dual chrome guide rods, animated weight stack, overhead pulley boom, and wide cambered lat pulldown bar.
- **Movement (`168` frames / `2.8s` @ `60 FPS`)**:
  - **Overhead Stretch (`r = 0.0`)**: Arms extended in a wide overhead Y-grip (`bar_y = 66.0`), scapulae upwardly rotated, lats stretched, weight stack at rest.
  - **Peak Contraction (`r = 1.0`)**: Wide cambered bar pulled down smoothly in front of the head/upper chest (`bar_y = 122.0`), elbows driven down and inward (`(246, 168)` and `(386, 170)`) into the classic W-frame contraction while the weight stack rises along the chrome guide rods.
- **Target Muscles Highlighted**:
  - **Primary**: `Latissimus dorsi`, `Teres major`
  - **Secondary**: `Trapezius (middle and lower)`, `Infraspinatus`, `Teres minor`, `Posterior deltoid`, `Biceps brachii`, `Brachialis`, `Brachioradialis`

## Usage
```bash
python3 gen_lat_pulldown.py --publish
```
