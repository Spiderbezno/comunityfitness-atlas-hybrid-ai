// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/models/workout_step.dart';
import 'package:comunityfitness/repositories/routine_repository.dart';
import 'package:comunityfitness/viewmodels/routine_editor_viewmodel.dart';

class MockRoutineRepository extends Mock implements RoutineRepository {}

void main() {
  late MockRoutineRepository mockRoutineRepository;

  setUpAll(() {
    registerFallbackValue(Routine(id: 'dummy', title: 'Dummy', description: 'Desc', createdAt: DateTime(2026), updatedAt: DateTime(2026), steps: []));
  });

  setUp(() {
    mockRoutineRepository = MockRoutineRepository();
    when(() => mockRoutineRepository.getRoutine(any())).thenReturn(null);
    when(() => mockRoutineRepository.saveRoutine(any())).thenAnswer((_) async {});
  });

  ProviderContainer makeContainer() {
    return ProviderContainer(overrides: [routineRepositoryProvider.overrideWithValue(mockRoutineRepository)]);
  }

  test('RoutineEditorViewModel starts empty when routineId is null', () {
    final container = makeContainer();
    final subscription = container.listen(routineEditorViewModelProvider(null), (prev, next) {});

    final state = container.read(routineEditorViewModelProvider(null));
    expect(state.title, '');
    expect(state.description, '');
    expect(state.steps.isEmpty, true);
    subscription.close();
  });

  test('RoutineEditorViewModel validates non-empty title and steps > 0 on save', () async {
    final container = makeContainer();
    final subscription = container.listen(routineEditorViewModelProvider(null), (prev, next) {});

    final vm = container.read(routineEditorViewModelProvider(null).notifier);

    // Save with empty title and no steps
    var result = await vm.saveRoutine();
    expect(result, false);
    expect(container.read(routineEditorViewModelProvider(null)).validationError, isNotNull);

    // Save with title but no steps
    vm.setTitle('My Routine');
    result = await vm.saveRoutine();
    expect(result, false);
    expect(container.read(routineEditorViewModelProvider(null)).validationError, isNotNull);

    // Add a step and save
    vm.addStep(
      const WorkoutStep(exerciseId: 'ex1', sets: 3, reps: 10, weight: 20.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 0),
    );
    result = await vm.saveRoutine();
    expect(result, true);
    expect(container.read(routineEditorViewModelProvider(null)).validationError, isNull);

    verify(() => mockRoutineRepository.saveRoutine(any())).called(1);
    subscription.close();
  });

  test('RoutineEditorViewModel loads existing routine and updates on save (Triangulate)', () async {
    final existingRoutine = Routine(
      id: 'existing-123',
      title: 'Leg Day',
      description: 'Heavy squats',
      createdAt: DateTime(2026, 1, 1),
      updatedAt: DateTime(2026, 1, 1),
      steps: [
        const WorkoutStep(exerciseId: 'ex2', sets: 4, reps: 8, weight: 100.0, targetDurationSeconds: 0, restDurationSeconds: 120, orderIndex: 0),
      ],
    );

    when(() => mockRoutineRepository.getRoutine('existing-123')).thenReturn(existingRoutine);

    final container = makeContainer();
    final subscription = container.listen(routineEditorViewModelProvider('existing-123'), (prev, next) {});

    final state = container.read(routineEditorViewModelProvider('existing-123'));
    expect(state.title, 'Leg Day');
    expect(state.description, 'Heavy squats');
    expect(state.steps.length, 1);
    expect(state.steps.first.exerciseId, 'ex2');

    final vm = container.read(routineEditorViewModelProvider('existing-123').notifier);
    vm.setTitle('Leg Day V2');

    final saveResult = await vm.saveRoutine();
    expect(saveResult, true);

    verify(
      () => mockRoutineRepository.saveRoutine(
        any(
          that: isA<Routine>()
              .having((r) => r.id, 'id', 'existing-123')
              .having((r) => r.title, 'title', 'Leg Day V2')
              .having((r) => r.createdAt, 'createdAt', existingRoutine.createdAt),
        ),
      ),
    ).called(1);

    subscription.close();
  });
}
