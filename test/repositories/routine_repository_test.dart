// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce/hive.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/repositories/routine_repository.dart';
import 'package:comunityfitness/services/sync_service.dart';

class MockBox extends Mock implements Box<Routine> {}

class MockSyncService extends Mock implements SyncService {}

void main() {
  late MockBox mockBox;
  late MockSyncService mockSyncService;
  late RoutineRepository repository;

  setUpAll(() {
    registerFallbackValue(Routine(id: 'dummy', title: 'Dummy', description: 'Desc', createdAt: DateTime(2026), updatedAt: DateTime(2026), steps: []));
  });

  setUp(() {
    mockBox = MockBox();
    mockSyncService = MockSyncService();
    repository = RoutineRepository(routineBox: mockBox, syncService: mockSyncService);
  });

  group('RoutineRepository', () {
    final routine1 = Routine(
      id: 'r1',
      title: 'Routine 1',
      description: 'Desc 1',
      createdAt: DateTime(2026, 1, 1),
      updatedAt: DateTime(2026, 1, 1),
      isDeleted: false,
      synced: true,
      steps: [],
    );

    final routineDeleted = Routine(
      id: 'r2',
      title: 'Routine 2',
      description: 'Desc 2',
      createdAt: DateTime(2026, 1, 1),
      updatedAt: DateTime(2026, 1, 1),
      isDeleted: true,
      synced: true,
      steps: [],
    );

    test('getRoutines returns only non-deleted routines', () {
      when(() => mockBox.values).thenReturn([routine1, routineDeleted]);

      final result = repository.getRoutines();

      expect(result.length, 1);
      expect(result.first.id, 'r1');
    });

    test('getRoutine returns routine if exists and is not deleted', () {
      when(() => mockBox.get('r1')).thenReturn(routine1);
      when(() => mockBox.get('r2')).thenReturn(routineDeleted);
      when(() => mockBox.get('r3')).thenReturn(null);

      expect(repository.getRoutine('r1')?.id, 'r1');
      expect(repository.getRoutine('r2'), null);
      expect(repository.getRoutine('r3'), null);
    });

    test('saveRoutine updates updatedAt, sets synced = false, puts in box, and triggers sync', () async {
      when(() => mockBox.put(any<dynamic>(), any())).thenAnswer((_) async {});
      when(() => mockSyncService.syncAll()).thenAnswer((_) async {});

      final routineToSave = Routine(
        id: 'r1',
        title: 'New Title',
        description: 'New Desc',
        createdAt: DateTime(2026, 1, 1),
        updatedAt: DateTime(2026, 1, 1),
        synced: true,
        steps: [],
      );

      await repository.saveRoutine(routineToSave);

      verify(
        () => mockBox.put(
          'r1',
          any(
            that: isA<Routine>()
                .having((r) => r.synced, 'synced', false)
                .having((r) => r.updatedAt.isAfter(routineToSave.updatedAt), 'updatedAt updated', true),
          ),
        ),
      ).called(1);

      verify(() => mockSyncService.syncAll()).called(1);
    });

    test('deleteRoutine soft-deletes (isDeleted=true, synced=false) and triggers sync', () async {
      when(() => mockBox.get('r1')).thenReturn(routine1);
      when(() => mockBox.put(any<dynamic>(), any())).thenAnswer((_) async {});
      when(() => mockSyncService.syncAll()).thenAnswer((_) async {});

      await repository.deleteRoutine('r1');

      verify(
        () => mockBox.put(
          'r1',
          any(
            that: isA<Routine>()
                .having((r) => r.isDeleted, 'isDeleted', true)
                .having((r) => r.synced, 'synced', false)
                .having((r) => r.updatedAt.isAfter(routine1.updatedAt), 'updatedAt updated', true),
          ),
        ),
      ).called(1);

      verify(() => mockSyncService.syncAll()).called(1);
    });
  });
}
