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
import 'package:comunityfitness/viewmodels/active_workout_viewmodel.dart';
import 'package:comunityfitness/viewmodels/dashboard_viewmodel.dart';

class FakeSyncService extends Fake implements SyncService {
  @override
  Future<void> syncAll() async {}
}

class FakeRoutineRepository extends Fake implements RoutineRepository {
  @override
  List<Routine> getRoutines() => const [];

  @override
  Stream<List<Routine>> watchRoutines() => const Stream.empty();
}

class FakeExerciseRepository extends Fake implements ExerciseRepository {
  final List<Exercise> exercises;

  FakeExerciseRepository(this.exercises);

  @override
  List<Exercise> getExercises() => exercises;
}

void main() {
  late Box<WorkoutSession> sessionBox;
  late SessionRepository sessionRepo;

  setUpAll(() async {
    final tempDir = '/tmp/hive_test_${DateTime.now().millisecondsSinceEpoch}';
    Hive.init(tempDir);
    if (!Hive.isAdapterRegistered(4)) {
      Hive.registerAdapter(WorkoutSessionAdapter());
    }
    if (!Hive.isAdapterRegistered(3)) {
      Hive.registerAdapter(WorkoutStepAdapter());
    }
    sessionBox = await Hive.openBox<WorkoutSession>('test_sessions');
    sessionRepo = SessionRepository(sessionBox: sessionBox, syncService: FakeSyncService());
  });

  tearDownAll(() async {
    await sessionBox.close();
  });

  tearDown(() async {
    await sessionBox.clear();
  });

  test('ActiveWorkoutViewModel executes workout flow, supersets, and finish', () async {
    final container = ProviderContainer(overrides: [sessionRepositoryProvider.overrideWithValue(sessionRepo)]);
    addTearDown(container.dispose);

    final vm = container.read(activeWorkoutViewModelProvider.notifier);

    final testRoutine = Routine(
      id: 'r-100',
      title: 'Upper Hypertrophy',
      description: 'Chest and Triceps',
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      steps: [
        const WorkoutStep(exerciseId: 'ex-bench', sets: 3, reps: 10, weight: 70.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 0),
        const WorkoutStep(exerciseId: 'ex-dips', sets: 3, reps: 12, weight: 0.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 1),
      ],
    );

    final exerciseMap = {
      'ex-bench': const Exercise(
        id: 'ex-bench',
        name: 'Barbell Bench Press',
        primaryMuscleGroup: 'Chest',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: '',
        description: 'Flat bench',
      ),
      'ex-dips': const Exercise(
        id: 'ex-dips',
        name: 'Tricep Dips',
        primaryMuscleGroup: 'Triceps',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: '',
        description: 'Parallel bar dips',
      ),
    };

    // 1. Start from routine
    vm.startFromRoutine(testRoutine, exerciseMap);
    var state = container.read(activeWorkoutViewModelProvider);
    expect(state.routineTitle, equals('Upper Hypertrophy'));
    expect(state.steps.length, equals(2));
    expect(state.steps[0].exerciseName, equals('Barbell Bench Press'));

    // 2. Pair as Superset
    vm.pairAsSuperset(0, 1);
    state = container.read(activeWorkoutViewModelProvider);
    expect(state.steps[0].supersetGroupId, isNotNull);
    expect(state.steps[0].supersetGroupId, equals(state.steps[1].supersetGroupId));

    // 3. Update step values (e.g. weight, rir, isWarmup)
    vm.updateStepValues(0, weight: 75.0, reps: 8, rir: 2, isWarmup: false);
    state = container.read(activeWorkoutViewModelProvider);
    expect(state.steps[0].weight, equals(75.0));
    expect(state.steps[0].reps, equals(8));
    expect(state.steps[0].rir, equals(2));

    // 4. Complete sets
    vm.toggleSetCompleted(0);
    state = container.read(activeWorkoutViewModelProvider);
    expect(state.steps[0].completedSets, equals(1));
    expect(state.isRestTimerActive, isTrue);
    expect(state.restTimerSecondsRemaining, equals(60));

    // 5. Rest timer controls
    vm.addRestTime(30);
    state = container.read(activeWorkoutViewModelProvider);
    expect(state.restTimerSecondsRemaining, equals(90));

    vm.skipRestTimer();
    state = container.read(activeWorkoutViewModelProvider);
    expect(state.isRestTimerActive, isFalse);

    // Complete all remaining sets
    vm.toggleSetCompleted(0); // 2
    vm.toggleSetCompleted(0); // 3 (Done)
    state = container.read(activeWorkoutViewModelProvider);
    expect(state.steps[0].isCompleted, isTrue);

    // 6. Finish workout
    final session = await vm.finishWorkout();
    expect(session.routineTitle, equals('Upper Hypertrophy'));
    expect(sessionBox.values.length, equals(1));
    expect(sessionBox.get(session.id)?.routineTitle, equals('Upper Hypertrophy'));
  });

  test('startFromRoutine and addExercise apply Progressive Overload Autopilot from session history', () async {
    final priorDate = DateTime(2026, 4, 10, 12);
    await sessionRepo.saveSession(
      WorkoutSession(
        id: 'hist-1',
        userId: 'u-1',
        routineId: 'r-100',
        routineTitle: 'Prior Upper',
        startedAt: priorDate.subtract(const Duration(minutes: 40)),
        completedAt: priorDate,
        updatedAt: priorDate,
        steps: const [
          WorkoutStep(exerciseId: 'ex-bench', sets: 3, reps: 10, weight: 70.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 0),
          WorkoutStep(exerciseId: 'ex-curl', sets: 3, reps: 10, weight: 15.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 1),
        ],
      ),
    );

    final container = ProviderContainer(overrides: [sessionRepositoryProvider.overrideWithValue(sessionRepo)]);
    addTearDown(container.dispose);

    final vm = container.read(activeWorkoutViewModelProvider.notifier);

    const benchExercise = Exercise(
      id: 'ex-bench',
      name: 'Barbell Bench Press',
      primaryMuscleGroup: 'Chest',
      equipment: 'Barbell',
      animationType: 'rive',
      animationPath: 'assets/animations/barbell_bench_press.riv',
      description: 'Flat bench press',
    );
    const curlExercise = Exercise(
      id: 'ex-curl',
      name: 'Dumbbell Bicep Curl',
      primaryMuscleGroup: 'Biceps',
      equipment: 'Dumbbell',
      animationType: 'rive',
      animationPath: 'assets/animations/dumbbell_bicep_curl.riv',
      description: 'Standing curl',
    );

    final routine = Routine(
      id: 'r-100',
      title: 'Upper Hypertrophy',
      description: 'Chest',
      createdAt: priorDate,
      updatedAt: priorDate,
      steps: const [
        WorkoutStep(exerciseId: 'ex-bench', sets: 3, reps: 10, weight: 70.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 0),
      ],
    );

    vm.startFromRoutine(routine, {'ex-bench': benchExercise});
    var state = container.read(activeWorkoutViewModelProvider);
    expect(state.steps[0].weight, equals(72.5));
    expect(state.steps[0].reps, equals(10));
    expect(state.steps[0].autopilotBadge, equals('+2.5 kg Autopilot'));

    vm.addExercise(curlExercise);
    state = container.read(activeWorkoutViewModelProvider);
    expect(state.steps[1].weight, equals(17.5));
    expect(state.steps[1].reps, equals(10));
    expect(state.steps[1].autopilotBadge, equals('+2.5 kg Autopilot'));
  });

  test('swapExerciseForBusyEquipment replaces exercise with different-equipment HD Rive alternative and preserves completedSets', () async {
    const barbellBench = Exercise(
      id: 'barbell_bench_press',
      name: 'Barbell Bench Press',
      primaryMuscleGroup: 'Chest',
      equipment: 'Barbell',
      animationType: 'rive',
      animationPath: 'assets/animations/barbell_bench_press.riv',
      description: 'Flat barbell bench press',
    );
    const inclineBarbell = Exercise(
      id: 'incline_barbell_bench',
      name: 'Incline Barbell Bench Press',
      primaryMuscleGroup: 'Chest',
      equipment: 'Barbell',
      animationType: 'rive',
      animationPath: 'assets/animations/barbell_bench_press.riv',
      description: 'Incline barbell press',
    );
    const dumbbellPress = Exercise(
      id: 'incline_dumbbell_press',
      name: 'Incline Dumbbell Press',
      primaryMuscleGroup: 'Chest',
      equipment: 'Dumbbell',
      animationType: 'rive',
      animationPath: 'assets/animations/incline_dumbbell_press.riv',
      description: 'Incline dumbbell chest press',
    );

    final fakeExerciseRepo = FakeExerciseRepository(const [barbellBench, inclineBarbell, dumbbellPress]);
    final container = ProviderContainer(
      overrides: [sessionRepositoryProvider.overrideWithValue(sessionRepo), exerciseRepositoryProvider.overrideWithValue(fakeExerciseRepo)],
    );
    addTearDown(container.dispose);

    final vm = container.read(activeWorkoutViewModelProvider.notifier);
    final routine = Routine(
      id: 'r-swap',
      title: 'Chest Day',
      description: 'Chest',
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      steps: const [
        WorkoutStep(
          exerciseId: 'barbell_bench_press',
          sets: 3,
          reps: 10,
          weight: 80.0,
          targetDurationSeconds: 0,
          restDurationSeconds: 60,
          orderIndex: 0,
        ),
      ],
    );

    vm.startFromRoutine(routine, {'barbell_bench_press': barbellBench});
    vm.toggleSetCompleted(0); // 1 completed set

    final swapped = vm.swapExerciseForBusyEquipment(0);
    expect(swapped, isTrue);

    final step = container.read(activeWorkoutViewModelProvider).steps[0];
    expect(step.exerciseId, equals('incline_dumbbell_press'));
    expect(step.exerciseName, equals('Incline Dumbbell Press'));
    expect(step.completedSets, equals(1));
    expect(step.weight, equals(35.0)); // 80 * 0.45 = 36.0 -> rounded to nearest 2.5 = 35.0
    expect(step.swapReason, equals('Swapped from Barbell Bench Press (Barbell busy)'));
  });

  test('Ghost Partner resolves prior session baseline, updates live pacing delta on set completion, and falls back to benchmark', () async {
    final priorDate = DateTime(2026, 4, 12, 10);
    await sessionRepo.saveSession(
      WorkoutSession(
        id: 'ghost-hist-1',
        userId: 'u-1',
        routineId: 'r-push',
        routineTitle: 'Push Day',
        startedAt: priorDate.subtract(const Duration(minutes: 45)),
        completedAt: priorDate,
        updatedAt: priorDate,
        steps: const [
          WorkoutStep(exerciseId: 'ex-bench', sets: 2, reps: 10, weight: 80.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 0),
        ],
      ),
    );

    final container = ProviderContainer(overrides: [sessionRepositoryProvider.overrideWithValue(sessionRepo)]);
    addTearDown(container.dispose);

    final vm = container.read(activeWorkoutViewModelProvider.notifier);

    const benchExercise = Exercise(
      id: 'ex-bench',
      name: 'Barbell Bench Press',
      primaryMuscleGroup: 'Chest',
      equipment: 'Barbell',
      animationType: 'rive',
      animationPath: 'assets/animations/barbell_bench_press.riv',
      description: 'Flat bench press',
    );

    final routine = Routine(
      id: 'r-push',
      title: 'Push Day',
      description: 'Chest focus',
      createdAt: priorDate,
      updatedAt: priorDate,
      steps: const [
        WorkoutStep(exerciseId: 'ex-bench', sets: 2, reps: 10, weight: 80.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 0),
      ],
    );

    // 1. Start routine with prior session history -> Ghost baseline resolved
    vm.startFromRoutine(routine, {'ex-bench': benchExercise});
    var state = container.read(activeWorkoutViewModelProvider);
    expect(state.ghostTitle, equals('Ghost: Last Push Day'));
    expect(state.ghostTotalSets, equals(2));
    expect(state.ghostTotalVolume, equals(1600.0)); // 2 * 10 * 80.0
    expect(state.liveVolume, equals(0.0));
    expect(state.ghostTargetVolumeNow, equals(0.0));
    expect(state.ghostDeltaVolume, equals(0.0));

    // 2. Complete 1st set (with Autopilot +2.5 kg -> 82.5 kg * 10 = 825 kg vs Ghost target 800 kg)
    vm.toggleSetCompleted(0);
    state = container.read(activeWorkoutViewModelProvider);
    expect(state.liveVolume, equals(825.0));
    expect(state.ghostTargetVolumeNow, equals(800.0));
    expect(state.ghostDeltaVolume, equals(25.0));
    expect(state.ghostDeltaVolume, greaterThan(0));

    // 3. Clear history and start freestyle -> falls back to Community Pace Benchmark
    await sessionBox.clear();
    vm.startFreestyle();
    state = container.read(activeWorkoutViewModelProvider);
    expect(state.ghostTitle, equals('Ghost: Community Pace Benchmark'));
    expect(state.ghostTotalVolume, equals(1200.0));
    expect(state.ghostTotalSets, equals(12));
  });

  test(
    'finishWorkout discards empty session when 0 exercises completed, saves when >= 1 exercise completed, and DashboardViewModel deletes session',
    () async {
      final container = ProviderContainer(
        overrides: [
          sessionRepositoryProvider.overrideWithValue(sessionRepo),
          routineRepositoryProvider.overrideWithValue(FakeRoutineRepository()),
          exerciseRepositoryProvider.overrideWithValue(FakeExerciseRepository(const [])),
        ],
      );
      addTearDown(container.dispose);

      final vm = container.read(activeWorkoutViewModelProvider.notifier);

      // 1. Start freestyle with 0 exercises and finish -> should NOT save to SessionRepository
      vm.startFreestyle();
      final emptySession = await vm.finishWorkout();
      expect(emptySession.steps, isEmpty);
      expect(container.read(activeWorkoutViewModelProvider).isFinished, isTrue);
      expect(sessionRepo.getSessions(), isEmpty);

      // 2. Start freestyle, add an exercise, complete 1 set, and finish -> SHOULD save to SessionRepository
      const benchExercise = Exercise(
        id: 'ex-bench',
        name: 'Barbell Bench Press',
        primaryMuscleGroup: 'Chest',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: '',
        description: 'Flat bench press',
      );
      vm.startFreestyle();
      vm.addExercise(benchExercise);
      vm.toggleSetCompleted(0);

      final savedSession = await vm.finishWorkout();
      expect(savedSession.steps.length, equals(1));
      expect(sessionRepo.getSessions().length, equals(1));
      expect(sessionRepo.getSessions().first.id, equals(savedSession.id));

      // 3. DashboardViewModel.deleteSession removes the session from SessionRepository and state
      final dashSub = container.listen(dashboardViewModelProvider, (_, _) {});
      addTearDown(dashSub.close);
      final dashStateBefore = container.read(dashboardViewModelProvider);
      expect(dashStateBefore.recentSessions.length, equals(1));

      await container.read(dashboardViewModelProvider.notifier).deleteSession(savedSession.id);
      expect(sessionRepo.getSessions(), isEmpty);
      final dashStateAfter = container.read(dashboardViewModelProvider);
      expect(dashStateAfter.recentSessions, isEmpty);
    },
  );
}
