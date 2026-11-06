// 📦 Package imports:
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';

part 'exercise_catalog_viewmodel.g.dart';

class ExerciseCatalogState {
  static const Object _sentinel = Object();

  final List<Exercise> exercises;
  final String searchQuery;
  final String? selectedMuscleGroup;
  final String? selectedEquipment;
  final List<Exercise> allExercises;

  ExerciseCatalogState({
    required this.exercises,
    required this.searchQuery,
    this.selectedMuscleGroup,
    this.selectedEquipment,
    required this.allExercises,
  });

  ExerciseCatalogState copyWith({
    List<Exercise>? exercises,
    String? searchQuery,
    Object? selectedMuscleGroup = _sentinel,
    Object? selectedEquipment = _sentinel,
    List<Exercise>? allExercises,
  }) {
    return ExerciseCatalogState(
      exercises: exercises ?? this.exercises,
      searchQuery: searchQuery ?? this.searchQuery,
      selectedMuscleGroup: identical(selectedMuscleGroup, _sentinel) ? this.selectedMuscleGroup : selectedMuscleGroup as String?,
      selectedEquipment: identical(selectedEquipment, _sentinel) ? this.selectedEquipment : selectedEquipment as String?,
      allExercises: allExercises ?? this.allExercises,
    );
  }
}

@riverpod
class ExerciseCatalogViewModel extends _$ExerciseCatalogViewModel {
  late final ExerciseRepository _exerciseRepository;
  bool _disposed = false;

  @override
  ExerciseCatalogState build() {
    _disposed = false;
    _exerciseRepository = ref.watch(exerciseRepositoryProvider);

    ref.onDispose(() {
      _disposed = true;
    });

    try {
      final sub = _exerciseRepository.watchExercises().skip(1).listen((all) {
        if (!_disposed) {
          state = state.copyWith(allExercises: all);
          _applyFilters(search: state.searchQuery, muscle: state.selectedMuscleGroup, equipment: state.selectedEquipment);
        }
      });
      ref.onDispose(sub.cancel);
    } catch (_) {}

    final initialState = ExerciseCatalogState(exercises: [], searchQuery: '', allExercises: []);

    _init();

    return initialState;
  }

  Future<void> _init() async {
    await _exerciseRepository.seedIfNeeded();
    if (_disposed) {
      return;
    }
    final all = _exerciseRepository.getExercises();
    if (_disposed) {
      return;
    }
    state = state.copyWith(allExercises: all);
    _applyFilters(search: state.searchQuery, muscle: state.selectedMuscleGroup, equipment: state.selectedEquipment);
  }

  void setSearchQuery(String query) {
    _applyFilters(search: query, muscle: state.selectedMuscleGroup, equipment: state.selectedEquipment);
  }

  void selectMuscleGroup(String? muscle) {
    _applyFilters(search: state.searchQuery, muscle: muscle, equipment: state.selectedEquipment);
  }

  void selectEquipment(String? equipment) {
    _applyFilters(search: state.searchQuery, muscle: state.selectedMuscleGroup, equipment: equipment);
  }

  void _applyFilters({required String search, String? muscle, String? equipment}) {
    var filtered = state.allExercises;

    if (search.isNotEmpty) {
      final query = search.toLowerCase();
      filtered = filtered.where((e) => e.name.toLowerCase().contains(query)).toList();
    }

    if (muscle != null && muscle.isNotEmpty) {
      filtered = filtered.where((e) => e.primaryMuscleGroup.toLowerCase() == muscle.toLowerCase()).toList();
    }

    if (equipment != null && equipment.isNotEmpty) {
      filtered = filtered.where((e) => e.equipment.toLowerCase() == equipment.toLowerCase()).toList();
    }

    state = ExerciseCatalogState(
      exercises: filtered,
      searchQuery: search,
      selectedMuscleGroup: muscle,
      selectedEquipment: equipment,
      allExercises: state.allExercises,
    );
  }
}
