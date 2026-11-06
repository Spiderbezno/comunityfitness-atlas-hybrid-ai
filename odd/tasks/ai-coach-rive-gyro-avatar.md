# Feature: AI Coach 3D Gyro-Core Rive Avatar (Concept A)

- **Feature ID**: `ai-coach-rive-gyro-avatar`
- **Repository Locator**: `odd/tasks/ai-coach-rive-gyro-avatar.md`
- **Engram Topic Key**: `odd/ai-coach-rive-gyro-avatar/tasks`
- **Branch**: `feat/interactive-rive-body-map-mev-mrv`
- **Delivery Strategy**: `exception-ok` (cached)
- **Forecast Authored Changed Lines**: ~450 lines (2 work-unit commits)
- **Running Authored Changed Lines**: 2,035 (`TASK-1` + `TASK-2`)

## Objective
Design, compile, and integrate **Concept A ("Biomech Gyro-Core" 3D Rive 7.3 Avatar)** (`assets/animations/ai_coach_avatar.riv`) for the AI Personal Trainer in `AiCoachView`, displaying the animated 60 FPS Rive avatar when giving advice in chat bubbles, when planning workouts / analyzing movements (`state.isLoading`), in the `AppBar` header, in `_LiveVoiceCoachBanner`, and in `AiExerciseAlternativeSheet`.

## Tasks Checklist

- [x] **TASK-1**: Author and compile 60 FPS 3D Gyro-Core Rive 7.3 animation (`assets/animations/ai_coach_avatar.riv`, 99 KB) and preview (`assets/animations/thumbnails/ai_coach_avatar.png`, 82 KB)
  - **Commit**: `047511e`
  - **Verification**: Valid Rive 7.3 binary (`RIVE` magic header, `101,394` bytes) and `256x256` PNG thumbnail + 6-frame contact sheet visually verified.

- [x] **TASK-2**: Build `AiCoachAvatar` widget (`lib/views/widgets/ai_coach_avatar.dart`) and integrate into `AiCoachView` (`lib/views/ai_coach_view.dart`) with widget tests
  - **Route**: `delegated` (`odd_task_writer`)
  - **Risk Tier**: `medium`
  - **Verification**: `3/3` widget tests passing in `test/views/ai_coach_view_test.dart`, `flutter analyze` 0 issues.

## Progress & Verification Evidence
- **Current Status**: COMPLETE (`TASK-1` and `TASK-2` verified GREEN).
