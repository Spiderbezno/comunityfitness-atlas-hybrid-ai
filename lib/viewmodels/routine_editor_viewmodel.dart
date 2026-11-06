// 📦 Package imports:
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:uuid/uuid.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/models/workout_step.dart';
import 'package:comunityfitness/repositories/routine_repository.dart';
import 'package:comunityfitness/viewmodels/dashboard_viewmodel.dart';
import 'package:comunityfitness/viewmodels/data_management_viewmodel.dart';
import 'package:comunityfitness/viewmodels/routine_list_viewmodel.dart';

part 'routine_editor_viewmodel.g.dart';

class RoutineEditorState {
  final String title;
  final String description;
  final List<WorkoutStep> steps;
  final bool isSaving;
  final String? validationError;
  final bool saveSuccess;

  RoutineEditorState({
    required this.title,
    required this.description,
    required this.steps,
    required this.isSaving,
    this.validationError,
    required this.saveSuccess,
  });

  RoutineEditorState copyWith({
    String? title,
    String? description,
    List<WorkoutStep>? steps,
    bool? isSaving,
    String? validationError,
    bool? saveSuccess,
  }) {
    return RoutineEditorState(
      title: title ?? this.title,
      description: description ?? this.description,
      steps: steps ?? this.steps,
      isSaving: isSaving ?? this.isSaving,
      validationError: validationError,
      saveSuccess: saveSuccess ?? this.saveSuccess,
    );
  }
}

@riverpod
class RoutineEditorViewModel extends _$RoutineEditorViewModel {
  late final RoutineRepository _routineRepository;

  @override
  RoutineEditorState build(String? routineId) {
    _routineRepository = ref.watch(routineRepositoryProvider);

    if (routineId != null) {
      final existing = _routineRepository.getRoutine(routineId);
      if (existing != null) {
        return RoutineEditorState(
          title: existing.title,
          description: existing.description,
          steps: List.from(existing.steps)..sort((a, b) => a.orderIndex.compareTo(b.orderIndex)),
          isSaving: false,
          saveSuccess: false,
        );
      }
    }

    return RoutineEditorState(title: '', description: '', steps: [], isSaving: false, saveSuccess: false);
  }

  void setTitle(String value) {
    state = state.copyWith(title: value);
  }

  void setDescription(String value) {
    state = state.copyWith(description: value);
  }

  void addStep(WorkoutStep step) {
    final updatedSteps = List<WorkoutStep>.from(state.steps)..add(step.copyWith(orderIndex: state.steps.length));
    state = state.copyWith(steps: updatedSteps);
  }

  void removeStep(int index) {
    final updatedSteps = List<WorkoutStep>.from(state.steps)..removeAt(index);
    for (var i = 0; i < updatedSteps.length; i++) {
      updatedSteps[i] = updatedSteps[i].copyWith(orderIndex: i);
    }
    state = state.copyWith(steps: updatedSteps);
  }

  void reorderSteps(int oldIndex, int newIndex) {
    final updatedSteps = List<WorkoutStep>.from(state.steps);
    if (oldIndex < newIndex) {
      newIndex -= 1;
    }
    final step = updatedSteps.removeAt(oldIndex);
    updatedSteps.insert(newIndex, step);

    for (var i = 0; i < updatedSteps.length; i++) {
      updatedSteps[i] = updatedSteps[i].copyWith(orderIndex: i);
    }
    state = state.copyWith(steps: updatedSteps);
  }

  void updateStep(int index, WorkoutStep step) {
    final updatedSteps = List<WorkoutStep>.from(state.steps);
    updatedSteps[index] = step.copyWith(orderIndex: index);
    state = state.copyWith(steps: updatedSteps);
  }

  Future<bool> saveRoutine() async {
    if (state.title.trim().isEmpty) {
      state = state.copyWith(validationError: 'Title cannot be empty');
      return false;
    }

    if (state.steps.isEmpty) {
      state = state.copyWith(validationError: 'Routine must contain at least one step');
      return false;
    }

    state = state.copyWith(isSaving: true, validationError: null);

    try {
      final now = DateTime.now();
      final currentId = routineId;
      final routine = Routine(
        id: currentId ?? const Uuid().v4(),
        title: state.title.trim(),
        description: state.description.trim(),
        createdAt: currentId != null ? (_routineRepository.getRoutine(currentId)?.createdAt ?? now) : now,
        updatedAt: now,
        synced: false,
        isDeleted: false,
        steps: state.steps,
      );

      await _routineRepository.saveRoutine(routine);
      state = state.copyWith(isSaving: false, saveSuccess: true);
      ref.invalidate(dashboardViewModelProvider);
      ref.invalidate(dataManagementViewModelProvider);
      ref.invalidate(routineListViewModelProvider);
      return true;
    } catch (e) {
      state = state.copyWith(isSaving: false, validationError: e.toString());
      return false;
    }
  }
}
