# Feature: Discard Empty Workouts & Recent Session Deletion (Option 1)

- **Feature ID**: `freestyle-cleanup-and-session-delete`
- **Repository Locator**: `odd/tasks/freestyle-cleanup-and-session-delete.md`
- **Engram Topic Key**: `odd/freestyle-cleanup-and-session-delete/tasks`
- **Branch**: `feat/interactive-rive-body-map-mev-mrv`
- **Delivery Strategy**: `exception-ok` (cached)
- **Forecast Authored Changed Lines**: ~180 lines (1 work-unit commit)
- **Running Authored Changed Lines**: 261

## Objective
Implement Option 1 for accidental Freestyle / empty workouts:
1. Do not save a `WorkoutSession` in `ActiveWorkoutViewModel.finishWorkout()` when `0` effective exercises have completed sets (`completedSteps.isEmpty`), and pop `ActiveWorkoutScreen` cleanly without opening the post-workout summary sheet when `session.steps.isEmpty`.
2. Allow deleting any session from the `Recent Sessions` list in `DashboardScreen` via `DashboardViewModel.deleteSession(String sessionId)` (using both `Dismissible` swipe-to-delete and an explicit trash icon button `Key('delete_recent_session_${session.id}')`), fully localized across all 5 languages (`es`, `en`, `ca`, `fr`, `pt`).

## Tasks Checklist

- [x] **TASK-1**: Discard empty (`0` completed exercises) workouts on finish and add Recent Session deletion in Dashboard
  - **Route**: `delegated` (`odd_task_writer`)
  - **Risk Tier**: `medium`
  - **Verification**: `11/11` unit & widget tests passing (`test/viewmodels/active_workout_viewmodel_test.dart`, `test/views/active_workout_screen_test.dart`), `flutter analyze` 0 issues.

## Progress & Verification Evidence
- **Current Status**: COMPLETE (`TASK-1` verified GREEN).
