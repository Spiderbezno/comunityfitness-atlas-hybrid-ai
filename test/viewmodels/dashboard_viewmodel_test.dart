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
import 'package:comunityfitness/viewmodels/dashboard_viewmodel.dart';

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
    final tempDir = '/tmp/hive_db_${DateTime.now().millisecondsSinceEpoch}';
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

    routineBox = await Hive.openBox<Routine>('test_routines_dash');
    sessionBox = await Hive.openBox<WorkoutSession>('test_sessions_dash');
    exerciseBox = await Hive.openBox<Exercise>('test_exercises_dash');

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

  test('DashboardViewModel aggregates routines, readiness, and metrics', () async {
    await routineRepo.saveRoutine(
      Routine(
        id: 'r-1',
        title: 'Leg Blast',
        description: 'Squats and Calf Raises',
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
        steps: const [],
      ),
    );

    final container = ProviderContainer(
      overrides: [
        routineRepositoryProvider.overrideWithValue(routineRepo),
        sessionRepositoryProvider.overrideWithValue(sessionRepo),
        exerciseRepositoryProvider.overrideWithValue(exerciseRepo),
      ],
    );
    addTearDown(container.dispose);

    final state = container.read(dashboardViewModelProvider);

    expect(state.allRoutines.length, equals(1));
    expect(state.recommendedRoutine?.title, equals('Leg Blast'));
    expect(state.readyMuscles, isNotEmpty);
  });
}
