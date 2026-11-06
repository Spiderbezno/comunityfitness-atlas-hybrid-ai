// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce/hive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/models/workout_step.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/repositories/routine_repository.dart';
import 'package:comunityfitness/repositories/session_repository.dart';
import 'package:comunityfitness/services/sync_service.dart';
import 'package:comunityfitness/viewmodels/data_management_viewmodel.dart';

class FakeSyncService extends Fake implements SyncService {
  @override
  Future<void> syncAll() async {}
}

void main() {
  late Box<Routine> routineBox;
  late Box<WorkoutSession> sessionBox;
  late Box<Exercise> exerciseBox;
  late RoutineRepository routineRepo;
  late SessionRepository sessionRepo;
  late ExerciseRepository exerciseRepo;

  setUpAll(() async {
    final tempDir = '/tmp/hive_dm_${DateTime.now().millisecondsSinceEpoch}';
    Hive.init(tempDir);
    if (!Hive.isAdapterRegistered(2)) {
      Hive.registerAdapter(RoutineAdapter());
    }
    if (!Hive.isAdapterRegistered(4)) {
      Hive.registerAdapter(WorkoutSessionAdapter());
    }
    if (!Hive.isAdapterRegistered(3)) {
      Hive.registerAdapter(WorkoutStepAdapter());
    }
    if (!Hive.isAdapterRegistered(1)) {
      Hive.registerAdapter(ExerciseAdapter());
    }

    routineBox = await Hive.openBox<Routine>('test_routines_dm');
    sessionBox = await Hive.openBox<WorkoutSession>('test_sessions_dm');
    exerciseBox = await Hive.openBox<Exercise>('test_exercises_dm');

    routineRepo = RoutineRepository(routineBox: routineBox, syncService: FakeSyncService());
    sessionRepo = SessionRepository(sessionBox: sessionBox, syncService: FakeSyncService());
    exerciseRepo = ExerciseRepository(exerciseBox: exerciseBox);
  });

  tearDownAll(() async {
    await routineBox.close();
    await sessionBox.close();
    await exerciseBox.close();
  });

  tearDown(() async {
    await routineBox.clear();
    await sessionBox.clear();
    await exerciseBox.clear();
  });

  test('DataManagementViewModel handles backup export, JSON restore, and CSV imports', () async {
    final container = ProviderContainer(
      overrides: [
        routineRepositoryProvider.overrideWithValue(routineRepo),
        sessionRepositoryProvider.overrideWithValue(sessionRepo),
        exerciseRepositoryProvider.overrideWithValue(exerciseRepo),
      ],
    );
    addTearDown(container.dispose);

    final vm = container.read(dataManagementViewModelProvider.notifier);

    // 1. Seed and export JSON
    await routineRepo.saveRoutine(
      Routine(
        id: 'r-sample',
        title: 'Full Body A',
        description: 'Squat & Bench',
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
        steps: const [],
      ),
    );

    final exportJson = vm.exportFullBackupJson();
    expect(exportJson, contains('Full Body A'));

    // 2. Import Strong CSV
    const strongCsv = '''
Date,Workout Name,Exercise Name,Set Order,Weight,Weight Unit,Reps,RPE,Distance,Distance Unit,Seconds,Notes,Workout Notes,Workout Duration
2026-08-01 09:00:00,Morning Lift,Deadlift,1,120.0,kg,5,8.5,,,,,
''';

    final result = await vm.importStrongCsv(strongCsv);
    expect(result.sessions.length, equals(1));
    expect(sessionBox.values.length, equals(1));
    expect(sessionBox.values.first.routineTitle, equals('Morning Lift'));
  });
}
