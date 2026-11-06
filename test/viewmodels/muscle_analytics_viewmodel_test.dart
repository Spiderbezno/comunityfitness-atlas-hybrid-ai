// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce/hive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/models/workout_step.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/repositories/session_repository.dart';
import 'package:comunityfitness/services/sync_service.dart';
import 'package:comunityfitness/viewmodels/muscle_analytics_viewmodel.dart';

class FakeSyncService extends Fake implements SyncService {
  @override
  Future<void> syncAll() async {}
}

void main() {
  late Box<WorkoutSession> sessionBox;
  late Box<Exercise> exerciseBox;
  late SessionRepository sessionRepo;
  late ExerciseRepository exerciseRepo;

  setUpAll(() async {
    final tempDir = '/tmp/hive_analytics_${DateTime.now().millisecondsSinceEpoch}';
    Hive.init(tempDir);
    if (!Hive.isAdapterRegistered(4)) {
      Hive.registerAdapter(WorkoutSessionAdapter());
    }
    if (!Hive.isAdapterRegistered(3)) {
      Hive.registerAdapter(WorkoutStepAdapter());
    }
    if (!Hive.isAdapterRegistered(1)) {
      Hive.registerAdapter(ExerciseAdapter());
    }
    sessionBox = await Hive.openBox<WorkoutSession>('test_sessions_analytics');
    exerciseBox = await Hive.openBox<Exercise>('test_exercises_analytics');

    sessionRepo = SessionRepository(sessionBox: sessionBox, syncService: FakeSyncService());
    exerciseRepo = ExerciseRepository(exerciseBox: exerciseBox);
  });

  tearDownAll(() async {
    await sessionBox.close();
    await exerciseBox.close();
  });

  tearDown(() async {
    await sessionBox.clear();
    await exerciseBox.clear();
  });

  test('MuscleAnalyticsViewModel computes muscle recovery, volume, and PR records', () async {
    final now = DateTime.now();

    // 1. Seed exercises
    await exerciseRepo.saveExercise(
      const Exercise(
        id: 'ex-bench',
        name: 'Bench Press',
        primaryMuscleGroup: 'Chest',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: '',
        description: 'Flat bench press',
      ),
    );

    await exerciseRepo.saveExercise(
      const Exercise(
        id: 'ex-squat',
        name: 'Squat',
        primaryMuscleGroup: 'Quads',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: '',
        description: 'Back squat',
      ),
    );

    // 2. Seed sessions
    await sessionRepo.saveSession(
      WorkoutSession(
        id: 's-1',
        userId: 'user-1',
        routineTitle: 'Chest Day',
        startedAt: now.subtract(const Duration(hours: 48)),
        completedAt: now.subtract(const Duration(hours: 47)),
        updatedAt: now,
        steps: [
          const WorkoutStep(exerciseId: 'ex-bench', sets: 4, reps: 8, weight: 80.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 0),
        ],
      ),
    );

    final container = ProviderContainer(
      overrides: [sessionRepositoryProvider.overrideWithValue(sessionRepo), exerciseRepositoryProvider.overrideWithValue(exerciseRepo)],
    );
    addTearDown(container.dispose);

    final state = container.read(muscleAnalyticsViewModelProvider);

    expect(state.totalWorkoutsThisWeek, equals(1));
    expect(state.totalVolumeThisWeek, equals(2560.0)); // 4 * 8 * 80
    expect(state.muscleRecovery['Chest']?.weeklySets, equals(4));
    expect(state.muscleRecovery['Chest']?.weeklyVolume, equals(2560.0));
    expect(state.muscleRecovery['Chest']?.recoveryPercentage, greaterThan(0.8));

    // PR checks
    expect(state.personalRecords.length, equals(1));
    expect(state.personalRecords.first.exerciseId, equals('ex-bench'));
    expect(state.personalRecords.first.estimated1RM, greaterThan(90.0));
  });

  test('resolveTargetMuscles maps granular lower-body and arm exercises accurately', () {
    const rdl = Exercise(
      id: 'romanian_deadlift',
      name: 'Romanian Deadlift',
      primaryMuscleGroup: 'Legs',
      equipment: 'Barbell',
      animationType: 'rive',
      animationPath: '',
      description: 'Hip hinge targeting hamstrings and glutes',
    );
    expect(MuscleAnalyticsViewModel.resolveTargetMuscles(rdl), containsAll(['Hamstrings', 'Glutes']));
    expect(MuscleAnalyticsViewModel.resolveTargetMuscles(rdl), isNot(contains('Quads')));

    const legCurl = Exercise(
      id: 'leg_curl',
      name: 'Seated Leg Curl',
      primaryMuscleGroup: 'Legs',
      equipment: 'Machine',
      animationType: 'rive',
      animationPath: '',
      description: 'Isolated hamstring curl',
    );
    expect(MuscleAnalyticsViewModel.resolveTargetMuscles(legCurl), equals(['Hamstrings']));

    const squat = Exercise(
      id: 'barbell_squat',
      name: 'Barbell Squat',
      primaryMuscleGroup: 'Legs',
      equipment: 'Barbell',
      animationType: 'rive',
      animationPath: '',
      description: 'Compound quad and glute movement',
    );
    expect(MuscleAnalyticsViewModel.resolveTargetMuscles(squat), containsAll(['Quads', 'Glutes']));

    const skullCrusher = Exercise(
      id: 'skull_crusher',
      name: 'EZ-Bar Skull Crusher',
      primaryMuscleGroup: 'Arms',
      equipment: 'Barbell',
      animationType: 'rive',
      animationPath: '',
      description: 'Lying tricep extension',
    );
    expect(MuscleAnalyticsViewModel.resolveTargetMuscles(skullCrusher), equals(['Triceps']));

    const barbellCurl = Exercise(
      id: 'barbell_curl',
      name: 'Barbell Curl',
      primaryMuscleGroup: 'Arms',
      equipment: 'Barbell',
      animationType: 'rive',
      animationPath: '',
      description: 'Standing bicep curl',
    );
    expect(MuscleAnalyticsViewModel.resolveTargetMuscles(barbellCurl), equals(['Biceps']));

    const calfRaise = Exercise(
      id: 'calf_raise',
      name: 'Standing Calf Raise',
      primaryMuscleGroup: 'Legs',
      equipment: 'Machine',
      animationType: 'rive',
      animationPath: '',
      description: 'Calf isolation',
    );
    expect(MuscleAnalyticsViewModel.resolveTargetMuscles(calfRaise), equals(['Calves']));
  });

  test('MuscleAnalyticsViewModel excludes warmup sets and populates MEV/MAV/MRV volume landmarks', () async {
    final now = DateTime.now();

    await exerciseRepo.saveExercise(
      const Exercise(
        id: 'romanian_deadlift',
        name: 'Romanian Deadlift',
        primaryMuscleGroup: 'Legs',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: '',
        description: 'Posterior chain hip hinge',
      ),
    );
    await exerciseRepo.saveExercise(
      const Exercise(
        id: 'skull_crusher',
        name: 'Skull Crusher',
        primaryMuscleGroup: 'Arms',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: '',
        description: 'Triceps extension',
      ),
    );

    await sessionRepo.saveSession(
      WorkoutSession(
        id: 's-volume',
        userId: 'user-1',
        routineTitle: 'Posterior & Arms',
        startedAt: now.subtract(const Duration(hours: 12)),
        completedAt: now.subtract(const Duration(hours: 11)),
        updatedAt: now,
        steps: [
          const WorkoutStep(
            exerciseId: 'romanian_deadlift',
            sets: 3,
            reps: 10,
            weight: 60.0,
            isWarmup: true,
            targetDurationSeconds: 0,
            restDurationSeconds: 60,
            orderIndex: 0,
          ),
          const WorkoutStep(
            exerciseId: 'romanian_deadlift',
            sets: 8,
            reps: 8,
            weight: 100.0,
            isWarmup: false,
            targetDurationSeconds: 0,
            restDurationSeconds: 90,
            orderIndex: 1,
          ),
          const WorkoutStep(
            exerciseId: 'skull_crusher',
            sets: 4,
            reps: 12,
            weight: 35.0,
            isWarmup: false,
            targetDurationSeconds: 0,
            restDurationSeconds: 60,
            orderIndex: 2,
          ),
        ],
      ),
    );

    final container = ProviderContainer(
      overrides: [sessionRepositoryProvider.overrideWithValue(sessionRepo), exerciseRepositoryProvider.overrideWithValue(exerciseRepo)],
    );
    addTearDown(container.dispose);

    final state = container.read(muscleAnalyticsViewModelProvider);

    final hamstrings = state.muscleRecovery['Hamstrings']!;
    final glutes = state.muscleRecovery['Glutes']!;
    final quads = state.muscleRecovery['Quads']!;
    final triceps = state.muscleRecovery['Triceps']!;

    // Warmup 3 sets ignored, 8 working sets credited to both Hamstrings and Glutes
    expect(hamstrings.weeklySets, equals(8));
    expect(hamstrings.mev, equals(6));
    expect(hamstrings.mavMin, equals(10));
    expect(hamstrings.mavMax, equals(16));
    expect(hamstrings.mrv, equals(20));
    expect(hamstrings.volumeZone, equals('optimal_mav'));

    expect(glutes.weeklySets, equals(8));
    expect(glutes.volumeZone, equals('optimal_mav'));

    expect(quads.weeklySets, equals(0));
    expect(quads.volumeZone, equals('under_mev'));

    expect(triceps.weeklySets, equals(4));
    expect(triceps.mev, equals(6));
    expect(triceps.mavMax, equals(14));
    expect(triceps.mrv, equals(18));
    expect(triceps.volumeZone, equals('under_mev'));
  });
}
