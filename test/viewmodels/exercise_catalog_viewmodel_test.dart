// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/viewmodels/exercise_catalog_viewmodel.dart';

class MockExerciseRepository extends Mock implements ExerciseRepository {}

void main() {
  late MockExerciseRepository mockExerciseRepository;
  late List<Exercise> sampleExercises;

  setUp(() {
    mockExerciseRepository = MockExerciseRepository();
    sampleExercises = [
      const Exercise(
        id: '1',
        name: 'Push Up',
        primaryMuscleGroup: 'Chest',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: 'assets/pushup.riv',
        description: 'A classic chest exercise.',
      ),
      const Exercise(
        id: '2',
        name: 'Squat',
        primaryMuscleGroup: 'Legs',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: 'assets/squat.riv',
        description: 'A classic leg exercise.',
      ),
      const Exercise(
        id: '3',
        name: 'Bench Press',
        primaryMuscleGroup: 'Chest',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: 'assets/bench_press.riv',
        description: 'Barbell press.',
      ),
    ];

    when(() => mockExerciseRepository.getExercises()).thenReturn(sampleExercises);
    when(() => mockExerciseRepository.seedIfNeeded()).thenAnswer((_) async {});
  });

  ProviderContainer makeContainer() {
    return ProviderContainer(overrides: [exerciseRepositoryProvider.overrideWithValue(mockExerciseRepository)]);
  }

  test('ExerciseCatalogViewModel initializes by seeding and loading all exercises', () async {
    final container = makeContainer();
    final subscription = container.listen(exerciseCatalogViewModelProvider, (prev, next) {});

    // Allow seedIfNeeded to run
    await Future<void>.delayed(Duration.zero);

    final state = container.read(exerciseCatalogViewModelProvider);
    expect(state.exercises.length, 3);
    verify(() => mockExerciseRepository.seedIfNeeded()).called(1);
    subscription.close();
  });

  test('ExerciseCatalogViewModel filters exercises by search query', () async {
    final container = makeContainer();
    final subscription = container.listen(exerciseCatalogViewModelProvider, (prev, next) {});
    await Future<void>.delayed(Duration.zero);

    final vm = container.read(exerciseCatalogViewModelProvider.notifier);
    vm.setSearchQuery('push');

    final state = container.read(exerciseCatalogViewModelProvider);
    expect(state.exercises.length, 1);
    expect(state.exercises.first.name, 'Push Up');
    subscription.close();
  });

  test('ExerciseCatalogViewModel filters by muscle group and equipment (Triangulate)', () async {
    final container = makeContainer();
    final subscription = container.listen(exerciseCatalogViewModelProvider, (prev, next) {});
    await Future<void>.delayed(Duration.zero);

    final vm = container.read(exerciseCatalogViewModelProvider.notifier);

    // Filter by Chest
    vm.selectMuscleGroup('Chest');
    var state = container.read(exerciseCatalogViewModelProvider);
    expect(state.exercises.length, 2);
    expect(state.exercises.any((e) => e.name == 'Push Up'), true);
    expect(state.exercises.any((e) => e.name == 'Bench Press'), true);

    // Filter by Chest + Barbell
    vm.selectEquipment('Barbell');
    state = container.read(exerciseCatalogViewModelProvider);
    expect(state.exercises.length, 1);
    expect(state.exercises.first.name, 'Bench Press');

    // Clear filters
    vm.selectMuscleGroup(null);
    vm.selectEquipment(null);
    state = container.read(exerciseCatalogViewModelProvider);
    expect(state.exercises.length, 3);

    subscription.close();
  });
}
