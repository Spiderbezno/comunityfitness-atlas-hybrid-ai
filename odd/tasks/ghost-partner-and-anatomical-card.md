# Feature: Ghost Partner Mode + Post-Workout Anatomical Share Card

- **Feature ID**: `ghost-partner-and-anatomical-card`
- **Repository Locator**: `odd/tasks/ghost-partner-and-anatomical-card.md`
- **Engram Topic Key**: `odd/ghost-partner-and-anatomical-card/tasks`
- **Branch**: `feat/interactive-rive-body-map-mev-mrv`
- **Delivery Strategy**: `exception-ok` (cached)
- **Forecast Authored Changed Lines**: 1,105 lines (2 work-unit commits)
- **Running Authored Changed Lines**: 1,105 (`cb11851` + `TASK-2`)

## Objective
Add **Ghost Partner Mode** during active workouts (real-time pacing delta of completed sets and tonnage against your previous session for that routine or a benchmark Ghost workout) and a **Post-Workout Anatomical Summary & Share Card** displayed upon finishing a workout (or tapping a recent session on the Dashboard) showing activated muscle groups on the anatomical map, Ghost delta, total tonnage, and 1RM PRs.

## Tasks Checklist

- [x] **TASK-1**: Add Ghost Partner live pacing delta state and computation in `ActiveWorkoutViewModel` with unit tests
  - **Route**: `delegated`
  - **Risk Tier**: `medium`
  - **Commit**: `cb11851` (`feat(workout): add Ghost Partner live pacing delta state and computation`)
  - **Verification Observed**: `00:00 +4: All tests passed!`, `flutter analyze` 0 issues.

- [x] **TASK-2**: Build Ghost Partner Live HUD Banner and Post-Workout Anatomical Summary Card (`WorkoutAnatomicalSummarySheet`) integrated into `ActiveWorkoutScreen` and `DashboardScreen` with widget tests
  - **Route**: `delegated`
  - **Risk Tier**: `medium`
  - **Verification Observed**: `00:01 +6: All tests passed!`, `flutter analyze` 0 issues, live on iPhone 18 Pro simulator.

## Progress & Verification Evidence
- **Current Status**: All 3 phases (`interactive-rive-body-map-mev-mrv`, `overload-autopilot-and-machine-swap`, `ghost-partner-and-anatomical-card`) completed, verified (`26/26` unit & widget tests passing), and synced to the iPhone 18 Pro simulator.
- **Next Step**: Ready for user testing in the simulator.
