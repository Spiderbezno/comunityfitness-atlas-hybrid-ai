// 📦 Package imports:
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/repositories/session_repository.dart';
import 'package:comunityfitness/services/strength_calculator_service.dart';

part 'muscle_analytics_viewmodel.g.dart';

class MuscleRecoveryInfo {
  final String muscle;
  final double recoveryPercentage;
  final String status; // 'recovered', 'recovering', 'fatigued'
  final int weeklySets;
  final double weeklyVolume;
  final DateTime? lastTrained;
  final int mev;
  final int mavMin;
  final int mavMax;
  final int mrv;
  final String volumeZone; // 'under_mev', 'optimal_mav', 'near_mrv', 'over_mrv'

  const MuscleRecoveryInfo({
    required this.muscle,
    required this.recoveryPercentage,
    required this.status,
    required this.weeklySets,
    required this.weeklyVolume,
    this.lastTrained,
    this.mev = 6,
    this.mavMin = 10,
    this.mavMax = 16,
    this.mrv = 20,
    this.volumeZone = 'under_mev',
  });
}

class ExercisePrInfo {
  final String exerciseId;
  final String exerciseName;
  final double estimated1RM;
  final double bestWeight;
  final int bestReps;
  final DateTime achievedAt;

  const ExercisePrInfo({
    required this.exerciseId,
    required this.exerciseName,
    required this.estimated1RM,
    required this.bestWeight,
    required this.bestReps,
    required this.achievedAt,
  });
}

class MuscleAnalyticsState {
  final Map<String, MuscleRecoveryInfo> muscleRecovery;
  final List<ExercisePrInfo> personalRecords;
  final Map<String, int> weeklyHeatmap; // 'YYYY-MM-DD' -> session count or volume
  final int totalWorkoutsThisWeek;
  final double totalVolumeThisWeek;
  final bool isLoading;

  const MuscleAnalyticsState({
    required this.muscleRecovery,
    required this.personalRecords,
    required this.weeklyHeatmap,
    required this.totalWorkoutsThisWeek,
    required this.totalVolumeThisWeek,
    this.isLoading = false,
  });

  factory MuscleAnalyticsState.initial() {
    return const MuscleAnalyticsState(
      muscleRecovery: {},
      personalRecords: [],
      weeklyHeatmap: {},
      totalWorkoutsThisWeek: 0,
      totalVolumeThisWeek: 0.0,
      isLoading: true,
    );
  }
}

@riverpod
class MuscleAnalyticsViewModel extends _$MuscleAnalyticsViewModel {
  static const standardMuscles = ['Chest', 'Back', 'Quads', 'Hamstrings', 'Shoulders', 'Biceps', 'Triceps', 'Core', 'Glutes', 'Calves'];

  @override
  MuscleAnalyticsState build() {
    final sessionRepo = ref.watch(sessionRepositoryProvider);
    final exerciseRepo = ref.watch(exerciseRepositoryProvider);

    try {
      final sessionSub = sessionRepo.watchSessions().skip(1).listen((_) => ref.invalidateSelf());
      ref.onDispose(sessionSub.cancel);
    } catch (_) {}
    try {
      final exerciseSub = exerciseRepo.watchExercises().skip(1).listen((_) => ref.invalidateSelf());
      ref.onDispose(exerciseSub.cancel);
    } catch (_) {}

    final sessions = sessionRepo.getSessions();
    final exercises = exerciseRepo.getExercises();

    return _computeAnalytics(sessions, exercises);
  }

  void refresh() {
    final sessionRepo = ref.read(sessionRepositoryProvider);
    final exerciseRepo = ref.read(exerciseRepositoryProvider);
    state = _computeAnalytics(sessionRepo.getSessions(), exerciseRepo.getExercises());
  }

  MuscleAnalyticsState _computeAnalytics(List<WorkoutSession> sessions, List<Exercise> exercises) {
    final Map<String, Exercise> exerciseMap = {for (final e in exercises) e.id: e};

    final now = DateTime.now();
    final weekAgo = now.subtract(const Duration(days: 7));

    final Map<String, int> weeklySetsMap = {for (final m in standardMuscles) m: 0};
    final Map<String, double> weeklyVolumeMap = {for (final m in standardMuscles) m: 0.0};
    final Map<String, DateTime> lastTrainedMap = {};
    final Map<String, int> lastTrainedSetsMap = {};

    final Map<String, ExercisePrInfo> prMap = {};
    final Map<String, int> heatmap = {};

    int weeklyWorkouts = 0;
    double weeklyVolumeTotal = 0.0;

    for (final session in sessions) {
      final dateKey = session.startedAt.toIso8601String().substring(0, 10);
      heatmap[dateKey] = (heatmap[dateKey] ?? 0) + 1;

      final isThisWeek = session.startedAt.isAfter(weekAgo);
      if (isThisWeek) {
        weeklyWorkouts++;
      }

      for (final step in session.steps) {
        if (step.isWarmup) {
          continue;
        }
        final exercise = exerciseMap[step.exerciseId];
        final targetMuscles = exercise != null ? resolveTargetMuscles(exercise) : const <String>[];

        final stepVolume = StrengthCalculatorService.calculateVolume(sets: step.sets, reps: step.reps, weight: step.weight);

        if (isThisWeek) {
          weeklyVolumeTotal += stepVolume;
          for (final canonicalMuscle in targetMuscles) {
            weeklySetsMap[canonicalMuscle] = (weeklySetsMap[canonicalMuscle] ?? 0) + step.sets;
            weeklyVolumeMap[canonicalMuscle] = (weeklyVolumeMap[canonicalMuscle] ?? 0.0) + stepVolume;
          }
        }

        for (final canonicalMuscle in targetMuscles) {
          final lastTime = lastTrainedMap[canonicalMuscle];
          if (lastTime == null || session.startedAt.isAfter(lastTime)) {
            lastTrainedMap[canonicalMuscle] = session.startedAt;
            lastTrainedSetsMap[canonicalMuscle] = step.sets;
          } else if (session.startedAt.isAtSameMomentAs(lastTime)) {
            lastTrainedSetsMap[canonicalMuscle] = (lastTrainedSetsMap[canonicalMuscle] ?? 0) + step.sets;
          }
        }

        // 1RM PR computation
        if (step.weight > 0 && step.reps > 0) {
          final est1rm = StrengthCalculatorService.calculateEstimatedOneRepMax(weight: step.weight, reps: step.reps);
          final existingPr = prMap[step.exerciseId];
          if (existingPr == null || est1rm > existingPr.estimated1RM) {
            prMap[step.exerciseId] = ExercisePrInfo(
              exerciseId: step.exerciseId,
              exerciseName: exercise?.name ?? 'Exercise',
              estimated1RM: est1rm,
              bestWeight: step.weight,
              bestReps: step.reps,
              achievedAt: session.startedAt,
            );
          }
        }
      }
    }

    // Build muscle recovery map
    final Map<String, MuscleRecoveryInfo> recoveryMap = {};
    for (final muscle in standardMuscles) {
      final lastDate = lastTrainedMap[muscle];
      final sets = lastTrainedSetsMap[muscle] ?? 0;

      double recoveryPct = 1.0;
      if (lastDate != null) {
        final hours = now.difference(lastDate).inMinutes / 60.0;
        recoveryPct = StrengthCalculatorService.calculateMuscleRecoveryPercentage(hoursSinceTrained: hours, effectiveSets: sets);
      }

      final weeklySets = weeklySetsMap[muscle] ?? 0;
      final landmarks = StrengthCalculatorService.getVolumeLandmarks(muscle);

      recoveryMap[muscle] = MuscleRecoveryInfo(
        muscle: muscle,
        recoveryPercentage: recoveryPct,
        status: StrengthCalculatorService.getRecoveryStatus(recoveryPct),
        weeklySets: weeklySets,
        weeklyVolume: weeklyVolumeMap[muscle] ?? 0.0,
        lastTrained: lastDate,
        mev: landmarks.mev,
        mavMin: landmarks.mavMin,
        mavMax: landmarks.mavMax,
        mrv: landmarks.mrv,
        volumeZone: StrengthCalculatorService.evaluateVolumeZone(muscle, weeklySets),
      );
    }

    return MuscleAnalyticsState(
      muscleRecovery: recoveryMap,
      personalRecords: prMap.values.toList()..sort((a, b) => b.estimated1RM.compareTo(a.estimated1RM)),
      weeklyHeatmap: heatmap,
      totalWorkoutsThisWeek: weeklyWorkouts,
      totalVolumeThisWeek: weeklyVolumeTotal,
      isLoading: false,
    );
  }

  /// Resolves an [Exercise] into one or more canonical muscles from [standardMuscles].
  static List<String> resolveTargetMuscles(Exercise exercise) {
    final primaryLower = exercise.primaryMuscleGroup.toLowerCase().trim();
    final combinedText = '${exercise.id} ${exercise.name} ${exercise.description}'.toLowerCase();
    final Set<String> resolved = {};

    bool matchesAny(List<String> keywords) {
      for (final keyword in keywords) {
        if (combinedText.contains(keyword)) {
          return true;
        }
      }
      return false;
    }

    if (primaryLower == 'legs' || primaryLower == 'upper legs' || primaryLower == 'full body') {
      final isCalves = matchesAny(['calf_raise', 'calves', 'calf']);
      final isHamstrings = matchesAny([
        'romanian_deadlift',
        'deadlift',
        'leg_curl',
        'hamstring',
        'glute_ham',
        'good_morning',
        'kettlebell_swing',
        'hip_thrust',
        'glute_bridge',
      ]);
      final isGlutes = matchesAny([
        'hip_thrust',
        'glute_bridge',
        'squat',
        'lunge',
        'bulgarian_split_squat',
        'leg_press',
        'romanian_deadlift',
        'deadlift',
        'step_up',
        'thruster',
      ]);
      final isQuads = matchesAny([
        'squat',
        'leg_press',
        'leg_extension',
        'lunge',
        'bulgarian_split_squat',
        'hack_squat',
        'goblet_squat',
        'thruster',
        'box_jump',
        'burpee',
      ]);

      if (isCalves) {
        resolved.add('Calves');
      }
      if (isHamstrings) {
        resolved.add('Hamstrings');
      }
      if (isGlutes) {
        resolved.add('Glutes');
      }
      if (isQuads) {
        resolved.add('Quads');
      }
      if (resolved.isEmpty) {
        resolved.add('Quads');
      }
      return resolved.toList();
    }

    if (primaryLower == 'arms' || primaryLower == 'upper arms') {
      final isTriceps = matchesAny(['tricep', 'skull_crusher', 'pushdown', 'dip', 'close_grip', 'overhead_tricep', 'kickback', 'diamond']);
      final isBiceps = matchesAny(['curl', 'bicep', 'chin_up', 'preacher', 'hammer', 'concentration']);

      if (isTriceps) {
        resolved.add('Triceps');
      }
      if (isBiceps) {
        resolved.add('Biceps');
      }
      if (resolved.isEmpty) {
        resolved.add('Biceps');
      }
      return resolved.toList();
    }

    final canonical = _canonicalizeMuscleStatic(exercise.primaryMuscleGroup);
    if (canonical != null) {
      resolved.add(canonical);
    }
    return resolved.toList();
  }

  static String? _canonicalizeMuscleStatic(String raw) {
    final lower = raw.toLowerCase();
    for (final m in standardMuscles) {
      if (m.toLowerCase() == lower) {
        return m;
      }
    }
    if (lower.contains('chest') || lower.contains('pec')) {
      return 'Chest';
    }
    if (lower.contains('back') || lower.contains('lat')) {
      return 'Back';
    }
    if (lower.contains('quad') || lower.contains('leg')) {
      return 'Quads';
    }
    if (lower.contains('hamstring')) {
      return 'Hamstrings';
    }
    if (lower.contains('shoulder') || lower.contains('delt')) {
      return 'Shoulders';
    }
    if (lower.contains('bicep')) {
      return 'Biceps';
    }
    if (lower.contains('tricep')) {
      return 'Triceps';
    }
    if (lower.contains('core') || lower.contains('ab')) {
      return 'Core';
    }
    if (lower.contains('glute')) {
      return 'Glutes';
    }
    if (lower.contains('calf') || lower.contains('calves')) {
      return 'Calves';
    }
    return null;
  }
}
