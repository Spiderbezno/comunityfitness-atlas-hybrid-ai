# Feature: Overload Autopilot + Busy Machine Swap

- **Feature ID**: `overload-autopilot-and-machine-swap`
- **Repository Locator**: `odd/tasks/overload-autopilot-and-machine-swap.md`
- **Engram Topic Key**: `odd/overload-autopilot-and-machine-swap/tasks`
- **Branch**: `feat/interactive-rive-body-map-mev-mrv`
- **Delivery Strategy**: `exception-ok` (cached)
- **Forecast Authored Changed Lines**: 878 lines (2 work-unit commits)
- **Running Authored Changed Lines**: 878 (`a32073f` + `377a611`)

## Objective
Add an automatic **Progressive Overload Autopilot** prescription engine that sets intelligent target weight/reps from historical `WorkoutSession` performance when starting or adding exercises to an active workout, plus a **1-Tap Busy Machine Swap** that replaces an exercise during an active session with a biomechanically equivalent exercise (prioritizing HD Rive animations on different equipment) and recalibrates target load.

## Tasks Checklist

- [x] **TASK-1**: Implement Progressive Overload Autopilot prescription engine and 1-tap Busy Machine Swap in `StrengthCalculatorService` and `ActiveWorkoutViewModel`
  - **Route**: `delegated`
  - **Risk Tier**: `medium`
  - **Commit**: `a32073f` (`feat(workout): add progressive overload autopilot and busy machine swap logic`)
  - **Verification Observed**: `00:00 +16: All tests passed!`, `flutter analyze` 0 issues.

- [x] **TASK-2**: Integrate Autopilot Overload badge and 1-tap Busy Machine Swap button into `ActiveWorkoutScreen` with widget tests
  - **Route**: `delegated`
  - **Risk Tier**: `medium`
  - **Commit**: `377a611` (`feat(workout): add autopilot overload badge and 1-tap busy machine swap UI`)
  - **Verification Observed**: `00:01 +3: All tests passed!`, `flutter analyze` 0 issues.

## Progress & Verification Evidence
- **Current Status**: Feature completed (`a32073f`, `377a611`) and verified.
- **Next Step**: Execute Fase 3 (`odd/tasks/ghost-partner-and-anatomical-card.md`).
