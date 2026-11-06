# Feature: Interactive Rive Body Map MEV/MAV/MRV & Multi-Language Localization

- **Feature ID**: `interactive-rive-body-map-mev-mrv`
- **Repository Locator**: `odd/tasks/interactive-rive-body-map-mev-mrv.md`
- **Engram Topic Key**: `odd/interactive-rive-body-map-mev-mrv/tasks`
- **Branch**: `feat/interactive-rive-body-map-mev-mrv`
- **Delivery Strategy**: `exception-ok` (cached)
- **Forecast Authored Changed Lines**: ~1,800 lines (3 work-unit commits)
- **Running Authored Changed Lines**: 2,507 (`0ad85eb` + `a4ac7dd` + `TASK-3`)

## Objective
Transform `MuscleAnalyticsScreen` into an interactive Front/Back anatomical Rive body map with MEV/MAV/MRV landmarks, and ensure **all new sections across Phases 1, 2, and 3** (`InteractiveBodyMap`, `MuscleAnalyticsScreen`, `ActiveWorkoutScreen`, `WorkoutAnatomicalSummarySheet`) are 100% localized across all 5 supported languages (`es`, `en`, `ca`, `fr`, `pt`) in `lib/i18n/strings.g.dart` with zero horizontal `RenderFlex` overflows on any screen size.

## Tasks Checklist

- [x] **TASK-1**: Add MEV/MAV/MRV volume landmarks and granular muscle attribution (`Legs` -> `Quads`/`Hamstrings`/`Glutes`, `Arms` -> `Biceps`/`Triceps`, excluding `isWarmup` sets)
  - **Commit**: `0ad85eb` (`12/12` unit tests passing)

- [x] **TASK-2**: Build interactive Anterior/Posterior Rive Anatomical Body Map widget and integrate into `MuscleAnalyticsScreen` with catalog drill-down
  - **Commit**: `a4ac7dd` (`2/2` widget tests passing)

- [x] **TASK-3**: Localize all new sections (`InteractiveBodyMap`, `MuscleAnalyticsScreen`, `ActiveWorkoutScreen`, `WorkoutAnatomicalSummarySheet`) into all 5 languages (`es`, `en`, `ca`, `fr`, `pt`) via `lib/i18n/strings.g.dart` and eliminate all horizontal `RenderFlex` overflows (including the Front/Back toggle buttons in `InteractiveBodyMap`)
  - **Route**: `delegated` (Trigger: Writer trigger — touches `lib/i18n/strings.g.dart` + 4 view/widget files + 2 widget test files)
  - **Risk Tier**: `medium`
  - **Verification**: `8/8` widget tests passing (`test/views/muscle_analytics_screen_test.dart`, `test/views/active_workout_screen_test.dart`), `flutter analyze` 0 issues, `dart format` 0 changes.

## Progress & Verification Evidence
- **Current Status**: COMPLETE (`TASK-1`, `TASK-2`, and `TASK-3` verified GREEN).
