// 🎯 Dart imports:
import 'dart:async';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/repositories/routine_repository.dart';
import 'package:comunityfitness/viewmodels/routine_list_viewmodel.dart';

class MockRoutineRepository extends Mock implements RoutineRepository {}

void main() {
  late MockRoutineRepository mockRoutineRepository;
  late StreamController<List<Routine>> routineStreamController;

  setUp(() {
    mockRoutineRepository = MockRoutineRepository();
    routineStreamController = StreamController<List<Routine>>.broadcast();

    when(() => mockRoutineRepository.watchRoutines()).thenAnswer((_) => routineStreamController.stream);
    when(() => mockRoutineRepository.deleteRoutine(any())).thenAnswer((_) async {});
  });

  tearDown(() {
    routineStreamController.close();
  });

  ProviderContainer makeContainer() {
    return ProviderContainer(overrides: [routineRepositoryProvider.overrideWithValue(mockRoutineRepository)]);
  }

  test('RoutineListViewModel streams non-deleted routines', () async {
    final container = makeContainer();
    final subscription = container.listen(routineListViewModelProvider, (prev, next) {});

    final sampleRoutines = [
      Routine(id: 'r1', title: 'Routine 1', description: 'Desc 1', createdAt: DateTime(2026), updatedAt: DateTime(2026), steps: []),
    ];

    routineStreamController.add(sampleRoutines);
    await Future<void>.delayed(Duration.zero);

    final state = container.read(routineListViewModelProvider);
    expect(state.value, sampleRoutines);
    subscription.close();
  });

  test('RoutineListViewModel propagates multiple updates (Triangulate)', () async {
    final container = makeContainer();
    final subscription = container.listen(routineListViewModelProvider, (prev, next) {});

    final list1 = [Routine(id: 'r1', title: 'Routine A', description: 'Desc A', createdAt: DateTime(2026), updatedAt: DateTime(2026), steps: [])];

    final list2 = [
      Routine(id: 'r1', title: 'Routine A Updated', description: 'Desc A', createdAt: DateTime(2026), updatedAt: DateTime(2026), steps: []),
      Routine(id: 'r2', title: 'Routine B', description: 'Desc B', createdAt: DateTime(2026), updatedAt: DateTime(2026), steps: []),
    ];

    routineStreamController.add(list1);
    await Future<void>.delayed(Duration.zero);
    expect(container.read(routineListViewModelProvider).value, list1);

    routineStreamController.add(list2);
    await Future<void>.delayed(Duration.zero);
    expect(container.read(routineListViewModelProvider).value, list2);

    subscription.close();
  });

  test('RoutineListViewModel delegates delete command', () async {
    final container = makeContainer();
    final subscription = container.listen(routineListViewModelProvider, (prev, next) {});

    final vm = container.read(routineListViewModelProvider.notifier);
    await vm.deleteRoutine('r1');

    verify(() => mockRoutineRepository.deleteRoutine('r1')).called(1);
    subscription.close();
  });
}
