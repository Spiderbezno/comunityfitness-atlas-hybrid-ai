// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce/hive.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/repositories/session_repository.dart';
import 'package:comunityfitness/services/sync_service.dart';

class MockBox extends Mock implements Box<WorkoutSession> {}

class MockSyncService extends Mock implements SyncService {}

void main() {
  late MockBox mockBox;
  late MockSyncService mockSyncService;
  late SessionRepository repository;

  setUpAll(() {
    registerFallbackValue(WorkoutSession(id: 'dummy', userId: 'u1', startedAt: DateTime(2026), updatedAt: DateTime(2026), steps: []));
  });

  setUp(() {
    mockBox = MockBox();
    mockSyncService = MockSyncService();
    repository = SessionRepository(sessionBox: mockBox, syncService: mockSyncService);
  });

  group('SessionRepository', () {
    final session1 = WorkoutSession(
      id: 's1',
      userId: 'u1',
      startedAt: DateTime(2026, 1, 1),
      updatedAt: DateTime(2026, 1, 1),
      isDeleted: false,
      synced: true,
      steps: [],
    );

    final sessionDeleted = WorkoutSession(
      id: 's2',
      userId: 'u1',
      startedAt: DateTime(2026, 1, 1),
      updatedAt: DateTime(2026, 1, 1),
      isDeleted: true,
      synced: true,
      steps: [],
    );

    test('getSessions returns only non-deleted sessions', () {
      when(() => mockBox.values).thenReturn([session1, sessionDeleted]);

      final result = repository.getSessions();

      expect(result.length, 1);
      expect(result.first.id, 's1');
    });

    test('getSession returns session if exists and is not deleted', () {
      when(() => mockBox.get('s1')).thenReturn(session1);
      when(() => mockBox.get('s2')).thenReturn(sessionDeleted);
      when(() => mockBox.get('s3')).thenReturn(null);

      expect(repository.getSession('s1')?.id, 's1');
      expect(repository.getSession('s2'), null);
      expect(repository.getSession('s3'), null);
    });

    test('saveSession updates updatedAt, sets synced = false, puts in box, and triggers sync', () async {
      when(() => mockBox.put(any<dynamic>(), any())).thenAnswer((_) async {});
      when(() => mockSyncService.syncAll()).thenAnswer((_) async {});

      final sessionToSave = WorkoutSession(
        id: 's1',
        userId: 'u1',
        startedAt: DateTime(2026, 1, 1),
        updatedAt: DateTime(2026, 1, 1),
        synced: true,
        steps: [],
      );

      await repository.saveSession(sessionToSave);

      verify(
        () => mockBox.put(
          's1',
          any(
            that: isA<WorkoutSession>()
                .having((s) => s.synced, 'synced', false)
                .having((s) => s.updatedAt.isAfter(sessionToSave.updatedAt), 'updatedAt updated', true),
          ),
        ),
      ).called(1);

      verify(() => mockSyncService.syncAll()).called(1);
    });

    test('deleteSession soft-deletes (isDeleted=true, synced=false) and triggers sync', () async {
      when(() => mockBox.get('s1')).thenReturn(session1);
      when(() => mockBox.put(any<dynamic>(), any())).thenAnswer((_) async {});
      when(() => mockSyncService.syncAll()).thenAnswer((_) async {});

      await repository.deleteSession('s1');

      verify(
        () => mockBox.put(
          's1',
          any(
            that: isA<WorkoutSession>()
                .having((s) => s.isDeleted, 'isDeleted', true)
                .having((s) => s.synced, 'synced', false)
                .having((s) => s.updatedAt.isAfter(session1.updatedAt), 'updatedAt updated', true),
          ),
        ),
      ).called(1);

      verify(() => mockSyncService.syncAll()).called(1);
    });
  });
}
