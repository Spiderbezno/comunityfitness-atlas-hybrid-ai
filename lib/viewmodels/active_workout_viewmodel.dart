// 🎯 Dart imports:
import 'dart:async';

// 📦 Package imports:
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:uuid/uuid.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/ai_coach_models.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/models/workout_step.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/repositories/session_repository.dart';
import 'package:comunityfitness/repositories/user_repository.dart';
import 'package:comunityfitness/services/atlas_hybrid_ai_service.dart';
import 'package:comunityfitness/services/strength_calculator_service.dart';
import 'package:comunityfitness/utils/exercise_animation_asset.dart';
import 'package:comunityfitness/viewmodels/dashboard_viewmodel.dart';
import 'package:comunityfitness/viewmodels/data_management_viewmodel.dart';
import 'package:comunityfitness/viewmodels/muscle_analytics_viewmodel.dart';

part 'active_workout_viewmodel.g.dart';

const Object _sentinel = Object();

class ActiveStepItem {
  final String exerciseId;
  final String exerciseName;
  final String primaryMuscleGroup;
  final String equipment;
  final int sets;
  final int reps;
  final double weight;
  final int targetDurationSeconds;
  final int restDurationSeconds;
  final int orderIndex;
  final bool isWarmup;
  final String? supersetGroupId;
  final int? rir;
  final int completedSets;
  final bool isCompleted;
  final String? autopilotBadge;
  final String? swapReason;

  const ActiveStepItem({
    required this.exerciseId,
    required this.exerciseName,
    required this.primaryMuscleGroup,
    this.equipment = '',
    required this.sets,
    required this.reps,
    required this.weight,
    required this.targetDurationSeconds,
    required this.restDurationSeconds,
    required this.orderIndex,
    this.isWarmup = false,
    this.supersetGroupId,
    this.rir,
    this.completedSets = 0,
    this.isCompleted = false,
    this.autopilotBadge,
    this.swapReason,
  });

  WorkoutStep get step => WorkoutStep(
    exerciseId: exerciseId,
    sets: sets,
    reps: reps,
    weight: weight,
    targetDurationSeconds: targetDurationSeconds,
    restDurationSeconds: restDurationSeconds,
    orderIndex: orderIndex,
    isWarmup: isWarmup,
  );

  Exercise get exercise => Exercise(
    id: exerciseId,
    name: exerciseName,
    primaryMuscleGroup: primaryMuscleGroup,
    equipment: equipment,
    animationType: 'rive',
    animationPath: '',
    description: '',
  );

  ActiveStepItem copyWith({
    String? exerciseId,
    String? exerciseName,
    String? primaryMuscleGroup,
    String? equipment,
    int? sets,
    int? reps,
    double? weight,
    int? targetDurationSeconds,
    int? restDurationSeconds,
    int? orderIndex,
    bool? isWarmup,
    String? supersetGroupId,
    bool clearSuperset = false,
    int? rir,
    int? completedSets,
    bool? isCompleted,
    Object? autopilotBadge = _sentinel,
    Object? swapReason = _sentinel,
  }) {
    return ActiveStepItem(
      exerciseId: exerciseId ?? this.exerciseId,
      exerciseName: exerciseName ?? this.exerciseName,
      primaryMuscleGroup: primaryMuscleGroup ?? this.primaryMuscleGroup,
      equipment: equipment ?? this.equipment,
      sets: sets ?? this.sets,
      reps: reps ?? this.reps,
      weight: weight ?? this.weight,
      targetDurationSeconds: targetDurationSeconds ?? this.targetDurationSeconds,
      restDurationSeconds: restDurationSeconds ?? this.restDurationSeconds,
      orderIndex: orderIndex ?? this.orderIndex,
      isWarmup: isWarmup ?? this.isWarmup,
      supersetGroupId: clearSuperset ? null : (supersetGroupId ?? this.supersetGroupId),
      rir: rir ?? this.rir,
      completedSets: completedSets ?? this.completedSets,
      isCompleted: isCompleted ?? this.isCompleted,
      autopilotBadge: identical(autopilotBadge, _sentinel) ? this.autopilotBadge : autopilotBadge as String?,
      swapReason: identical(swapReason, _sentinel) ? this.swapReason : swapReason as String?,
    );
  }
}

class ActiveWorkoutState {
  final String? routineId;
  final String routineTitle;
  final DateTime startedAt;
  final List<ActiveStepItem> steps;
  final int elapsedSeconds;
  final bool isPaused;
  final int restTimerSecondsRemaining;
  final int restTimerTotalSeconds;
  final bool isRestTimerActive;
  final int activeStepIndex;
  final bool isFinished;
  final String? ghostTitle;
  final double ghostTotalVolume;
  final int ghostTotalSets;
  final double liveVolume;
  final double ghostTargetVolumeNow;
  final double ghostDeltaVolume;
  final HybridSetLogAnalysis? lastHybridAnalysis;
  final bool isHybridAnalyzing;

  const ActiveWorkoutState({
    this.routineId,
    required this.routineTitle,
    required this.startedAt,
    required this.steps,
    this.elapsedSeconds = 0,
    this.isPaused = false,
    this.restTimerSecondsRemaining = 0,
    this.restTimerTotalSeconds = 0,
    this.isRestTimerActive = false,
    this.activeStepIndex = 0,
    this.isFinished = false,
    this.ghostTitle,
    this.ghostTotalVolume = 0.0,
    this.ghostTotalSets = 0,
    this.liveVolume = 0.0,
    this.ghostTargetVolumeNow = 0.0,
    this.ghostDeltaVolume = 0.0,
    this.lastHybridAnalysis,
    this.isHybridAnalyzing = false,
  });

  ActiveWorkoutState copyWith({
    String? routineId,
    String? routineTitle,
    DateTime? startedAt,
    List<ActiveStepItem>? steps,
    int? elapsedSeconds,
    bool? isPaused,
    int? restTimerSecondsRemaining,
    int? restTimerTotalSeconds,
    bool? isRestTimerActive,
    int? activeStepIndex,
    bool? isFinished,
    Object? ghostTitle = _sentinel,
    double? ghostTotalVolume,
    int? ghostTotalSets,
    double? liveVolume,
    double? ghostTargetVolumeNow,
    double? ghostDeltaVolume,
    Object? lastHybridAnalysis = _sentinel,
    bool? isHybridAnalyzing,
  }) {
    return ActiveWorkoutState(
      routineId: routineId ?? this.routineId,
      routineTitle: routineTitle ?? this.routineTitle,
      startedAt: startedAt ?? this.startedAt,
      steps: steps ?? this.steps,
      elapsedSeconds: elapsedSeconds ?? this.elapsedSeconds,
      isPaused: isPaused ?? this.isPaused,
      restTimerSecondsRemaining: restTimerSecondsRemaining ?? this.restTimerSecondsRemaining,
      restTimerTotalSeconds: restTimerTotalSeconds ?? this.restTimerTotalSeconds,
      isRestTimerActive: isRestTimerActive ?? this.isRestTimerActive,
      activeStepIndex: activeStepIndex ?? this.activeStepIndex,
      isFinished: isFinished ?? this.isFinished,
      ghostTitle: identical(ghostTitle, _sentinel) ? this.ghostTitle : ghostTitle as String?,
      ghostTotalVolume: ghostTotalVolume ?? this.ghostTotalVolume,
      ghostTotalSets: ghostTotalSets ?? this.ghostTotalSets,
      liveVolume: liveVolume ?? this.liveVolume,
      ghostTargetVolumeNow: ghostTargetVolumeNow ?? this.ghostTargetVolumeNow,
      ghostDeltaVolume: ghostDeltaVolume ?? this.ghostDeltaVolume,
      lastHybridAnalysis: identical(lastHybridAnalysis, _sentinel) ? this.lastHybridAnalysis : lastHybridAnalysis as HybridSetLogAnalysis?,
      isHybridAnalyzing: isHybridAnalyzing ?? this.isHybridAnalyzing,
    );
  }
}

@Riverpod(keepAlive: true)
class ActiveWorkoutViewModel extends _$ActiveWorkoutViewModel {
  static const _uuid = Uuid();
  Timer? _tickerTimer;

  @override
  ActiveWorkoutState build() {
    ref.onDispose(() {
      _tickerTimer?.cancel();
    });

    return ActiveWorkoutState(routineTitle: 'Quick Workout', startedAt: DateTime.now(), steps: const []);
  }

  List<WorkoutSession> _safeGetSessions() {
    try {
      return ref.read(sessionRepositoryProvider).getSessions();
    } catch (_) {
      return const <WorkoutSession>[];
    }
  }

  ActiveStepItem _resolveWithAutopilot(WorkoutStep step, Exercise? exercise) {
    final equipment = exercise?.equipment ?? '';
    if (step.isWarmup) {
      return ActiveStepItem(
        exerciseId: step.exerciseId,
        exerciseName: exercise?.name ?? 'Exercise',
        primaryMuscleGroup: exercise?.primaryMuscleGroup ?? 'Full Body',
        equipment: equipment,
        sets: step.sets,
        reps: step.reps,
        weight: step.weight,
        targetDurationSeconds: step.targetDurationSeconds,
        restDurationSeconds: step.restDurationSeconds,
        orderIndex: step.orderIndex,
        isWarmup: step.isWarmup,
      );
    }

    final sessions = _safeGetSessions();
    final prescription = StrengthCalculatorService.prescribeProgressiveOverload(
      exerciseId: step.exerciseId,
      baseReps: step.reps,
      baseWeight: step.weight,
      history: sessions,
    );

    return ActiveStepItem(
      exerciseId: step.exerciseId,
      exerciseName: exercise?.name ?? 'Exercise',
      primaryMuscleGroup: exercise?.primaryMuscleGroup ?? 'Full Body',
      equipment: equipment,
      sets: step.sets,
      reps: prescription.isOverloadApplied ? prescription.targetReps : step.reps,
      weight: prescription.isOverloadApplied ? prescription.targetWeight : step.weight,
      targetDurationSeconds: step.targetDurationSeconds,
      restDurationSeconds: step.restDurationSeconds,
      orderIndex: step.orderIndex,
      isWarmup: step.isWarmup,
      autopilotBadge: prescription.isOverloadApplied ? prescription.badgeLabel : null,
    );
  }

  ({String ghostTitle, double ghostTotalVolume, int ghostTotalSets}) _resolveGhostBaseline({
    String? routineId,
    required String routineTitle,
    required List<ActiveStepItem> steps,
  }) {
    final sessions = _safeGetSessions().where((s) => !s.isDeleted).toList()
      ..sort((a, b) => (b.completedAt ?? b.startedAt).compareTo(a.completedAt ?? a.startedAt));

    WorkoutSession? matchedSession;
    if (routineId != null) {
      for (final s in sessions) {
        if (s.routineId == routineId && s.steps.isNotEmpty) {
          matchedSession = s;
          break;
        }
      }
    }
    if (matchedSession == null) {
      for (final s in sessions) {
        if (s.steps.isNotEmpty) {
          matchedSession = s;
          break;
        }
      }
    }

    if (matchedSession != null) {
      double ghostVolume = 0.0;
      int ghostSets = 0;
      for (final s in matchedSession.steps.where((s) => !s.isWarmup)) {
        ghostSets += s.sets;
        ghostVolume += (s.weight > 0 ? s.weight : 1.0) * s.reps * s.sets;
      }
      if (ghostVolume > 0) {
        return (ghostTitle: 'Ghost: Last ${matchedSession.routineTitle}', ghostTotalVolume: ghostVolume, ghostTotalSets: ghostSets);
      }
    }

    int plannedSets = 0;
    double plannedVolume = 0.0;
    for (final item in steps.where((s) => !s.step.isWarmup)) {
      final unitWeight = item.step.weight > 0 ? item.step.weight : 1.0;
      plannedSets += item.step.sets;
      plannedVolume += unitWeight * item.step.reps * item.step.sets;
    }

    final benchmarkVolume = plannedVolume > 0 ? plannedVolume * 0.95 : 1200.0;
    final benchmarkSets = plannedSets > 0 ? plannedSets : 12;

    return (ghostTitle: 'Ghost: Community Pace Benchmark', ghostTotalVolume: benchmarkVolume, ghostTotalSets: benchmarkSets);
  }

  ActiveWorkoutState _withUpdatedGhostPace(ActiveWorkoutState current) {
    int totalPlannedNonWarmupSets = 0;
    int completedNonWarmupSets = 0;
    double liveVolume = 0.0;

    for (final item in current.steps.where((s) => !s.step.isWarmup)) {
      final doneCount = item.completedSets;
      final unitWeight = item.step.weight > 0 ? item.step.weight : 1.0;
      liveVolume += unitWeight * item.step.reps * doneCount;
      completedNonWarmupSets += doneCount;
      totalPlannedNonWarmupSets += item.step.sets;
    }

    final progress = totalPlannedNonWarmupSets > 0 ? (completedNonWarmupSets / totalPlannedNonWarmupSets).clamp(0.0, 1.0) : 0.0;
    final ghostTargetVolumeNow = current.ghostTotalVolume * progress;
    final ghostDeltaVolume = liveVolume - ghostTargetVolumeNow;

    return current.copyWith(liveVolume: liveVolume, ghostTargetVolumeNow: ghostTargetVolumeNow, ghostDeltaVolume: ghostDeltaVolume);
  }

  void startFromRoutine(Routine routine, Map<String, Exercise> exerciseMap) {
    _tickerTimer?.cancel();

    final activeSteps = routine.steps.map((s) {
      final exercise = exerciseMap[s.exerciseId];
      return _resolveWithAutopilot(s, exercise);
    }).toList();

    final ghost = _resolveGhostBaseline(routineId: routine.id, routineTitle: routine.title, steps: activeSteps);

    state = _withUpdatedGhostPace(
      ActiveWorkoutState(
        routineId: routine.id,
        routineTitle: routine.title,
        startedAt: DateTime.now(),
        steps: activeSteps,
        elapsedSeconds: 0,
        isPaused: false,
        ghostTitle: ghost.ghostTitle,
        ghostTotalVolume: ghost.ghostTotalVolume,
        ghostTotalSets: ghost.ghostTotalSets,
      ),
    );

    _startTicker();
  }

  void startFreestyle() {
    _tickerTimer?.cancel();
    final ghost = _resolveGhostBaseline(routineTitle: 'Freestyle Workout', steps: const []);
    state = _withUpdatedGhostPace(
      ActiveWorkoutState(
        routineTitle: 'Freestyle Workout',
        startedAt: DateTime.now(),
        steps: const [],
        elapsedSeconds: 0,
        isPaused: false,
        ghostTitle: ghost.ghostTitle,
        ghostTotalVolume: ghost.ghostTotalVolume,
        ghostTotalSets: ghost.ghostTotalSets,
      ),
    );
    _startTicker();
  }

  void startFromAiPlan(AiWorkoutPlan plan) {
    _tickerTimer?.cancel();

    final activeSteps = <ActiveStepItem>[];
    for (int i = 0; i < plan.exercises.length; i++) {
      final rec = plan.exercises[i];
      final catalogEx = rec.catalogExercise;
      final equipment = catalogEx?.equipment ?? '';
      final defaultWeight = equipment.toLowerCase() == 'bodyweight' ? 0.0 : 20.0;
      activeSteps.add(
        ActiveStepItem(
          exerciseId: catalogEx?.id ?? rec.exerciseId,
          exerciseName: catalogEx?.name ?? rec.exerciseName,
          primaryMuscleGroup: catalogEx?.primaryMuscleGroup ?? (plan.targetMuscles.isNotEmpty ? plan.targetMuscles.first : 'Full Body'),
          equipment: equipment,
          sets: rec.sets,
          reps: rec.reps,
          weight: defaultWeight,
          targetDurationSeconds: 0,
          restDurationSeconds: rec.restSeconds,
          orderIndex: i,
        ),
      );
    }

    final ghost = _resolveGhostBaseline(routineTitle: plan.title, steps: activeSteps);

    state = _withUpdatedGhostPace(
      ActiveWorkoutState(
        routineTitle: plan.title,
        startedAt: DateTime.now(),
        steps: activeSteps,
        elapsedSeconds: 0,
        isPaused: false,
        ghostTitle: ghost.ghostTitle,
        ghostTotalVolume: ghost.ghostTotalVolume,
        ghostTotalSets: ghost.ghostTotalSets,
      ),
    );

    _startTicker();
  }

  void addExercise(Exercise exercise) {
    final defaultWeight = exercise.equipment.toLowerCase() == 'bodyweight' ? 0.0 : 20.0;
    final baseStep = WorkoutStep(
      exerciseId: exercise.id,
      sets: 3,
      reps: 10,
      weight: defaultWeight,
      targetDurationSeconds: 0,
      restDurationSeconds: 60,
      orderIndex: state.steps.length,
    );
    final newStep = _resolveWithAutopilot(baseStep, exercise);

    state = _withUpdatedGhostPace(state.copyWith(steps: [...state.steps, newStep]));
  }

  bool swapExerciseForBusyEquipment(int index) {
    if (index < 0 || index >= state.steps.length) {
      return false;
    }
    final currentItem = state.steps[index];
    List<Exercise> allExercises = const [];
    try {
      allExercises = ref.read(exerciseRepositoryProvider).getExercises();
    } catch (_) {
      return false;
    }
    if (allExercises.isEmpty) {
      return false;
    }

    Exercise? catalogCurrent;
    for (final ex in allExercises) {
      if (ex.id == currentItem.exerciseId) {
        catalogCurrent = ex;
        break;
      }
    }
    final currentExercise =
        catalogCurrent ??
        Exercise(
          id: currentItem.exerciseId,
          name: currentItem.exerciseName,
          primaryMuscleGroup: currentItem.primaryMuscleGroup,
          equipment: currentItem.equipment.isNotEmpty ? currentItem.equipment : (currentItem.weight <= 0 ? 'Bodyweight' : 'Barbell'),
          animationType: 'rive',
          animationPath: '',
          description: '',
        );

    final currentMuscles = MuscleAnalyticsViewModel.resolveTargetMuscles(currentExercise).toSet();
    final currentPrimaryLower = currentExercise.primaryMuscleGroup.toLowerCase();

    final candidates = allExercises.where((c) {
      if (c.id == currentExercise.id) {
        return false;
      }
      final candidateMuscles = MuscleAnalyticsViewModel.resolveTargetMuscles(c);
      final sharesResolvedMuscle = candidateMuscles.any(currentMuscles.contains);
      final sharesPrimary = c.primaryMuscleGroup.toLowerCase() == currentPrimaryLower;
      return sharesResolvedMuscle || sharesPrimary;
    }).toList();

    if (candidates.isEmpty) {
      return false;
    }

    final currentEquipLower = currentExercise.equipment.toLowerCase();
    final diffEquipCandidates = candidates.where((c) => c.equipment.toLowerCase() != currentEquipLower).toList();
    var pool = diffEquipCandidates.isNotEmpty ? diffEquipCandidates : candidates;

    final existingIds = state.steps.map((s) => s.exerciseId).toSet();
    final unusedPool = pool.where((c) => !existingIds.contains(c.id)).toList();
    if (unusedPool.isNotEmpty) {
      pool = unusedPool;
    }

    pool.sort((a, b) {
      final aHd = exerciseRiveAsset(a) != null;
      final bHd = exerciseRiveAsset(b) != null;
      if (aHd != bHd) {
        return aHd ? -1 : 1;
      }
      return a.id.compareTo(b.id);
    });

    final candidate = pool.first;
    final candidateEquipLower = candidate.equipment.toLowerCase();
    final scaledWeight = candidateEquipLower == 'bodyweight'
        ? 0.0
        : _scaleWeightForEquipmentSwap(currentItem.weight, currentExercise.equipment, candidate.equipment);

    final sessions = _safeGetSessions();
    final prescription = StrengthCalculatorService.prescribeProgressiveOverload(
      exerciseId: candidate.id,
      baseReps: currentItem.reps,
      baseWeight: scaledWeight,
      history: sessions,
    );

    final newWeight = candidateEquipLower == 'bodyweight' ? 0.0 : (prescription.isOverloadApplied ? prescription.targetWeight : scaledWeight);
    final newReps = prescription.isOverloadApplied ? prescription.targetReps : currentItem.reps;

    final updatedList = List<ActiveStepItem>.from(state.steps);
    updatedList[index] = currentItem.copyWith(
      exerciseId: candidate.id,
      exerciseName: candidate.name,
      primaryMuscleGroup: candidate.primaryMuscleGroup,
      equipment: candidate.equipment,
      weight: newWeight,
      reps: newReps,
      autopilotBadge: prescription.isOverloadApplied ? prescription.badgeLabel : null,
      swapReason: 'Swapped from ${currentExercise.name} (${currentExercise.equipment} busy)',
    );

    state = _withUpdatedGhostPace(state.copyWith(steps: updatedList));
    return true;
  }

  static double _scaleWeightForEquipmentSwap(double currentWeight, String fromEquipment, String toEquipment) {
    if (currentWeight <= 0) {
      return 20.0;
    }
    final fromLower = fromEquipment.toLowerCase();
    final toLower = toEquipment.toLowerCase();
    if (fromLower == toLower) {
      return _roundToNearestPlate(currentWeight);
    }

    double factor = 1.0;
    if (toLower.contains('dumbbell') && fromLower.contains('barbell')) {
      factor = 0.45;
    } else if ((toLower.contains('cable') || toLower.contains('machine')) && fromLower.contains('barbell')) {
      factor = 0.85;
    } else if (toLower.contains('barbell') && fromLower.contains('dumbbell')) {
      factor = 1.0 / 0.45;
    } else if (toLower.contains('dumbbell') && (fromLower.contains('cable') || fromLower.contains('machine'))) {
      factor = 0.55;
    }

    return _roundToNearestPlate(currentWeight * factor);
  }

  static double _roundToNearestPlate(double weight) {
    final rounded = (weight / 2.5).round() * 2.5;
    return rounded < 2.5 ? 2.5 : rounded;
  }

  void removeStep(int index) {
    if (index < 0 || index >= state.steps.length) {
      return;
    }
    final updated = List<ActiveStepItem>.from(state.steps)..removeAt(index);
    final groupCounts = <String, int>{};
    for (final step in updated) {
      final groupId = step.supersetGroupId;
      if (groupId != null) {
        groupCounts[groupId] = (groupCounts[groupId] ?? 0) + 1;
      }
    }
    for (int i = 0; i < updated.length; i++) {
      final step = updated[i];
      final groupId = step.supersetGroupId;
      final clearGroup = groupId != null && (groupCounts[groupId] ?? 0) < 2;
      updated[i] = step.copyWith(orderIndex: i, clearSuperset: clearGroup);
    }
    state = _withUpdatedGhostPace(state.copyWith(steps: updated));
  }

  void toggleSetCompleted(int stepIndex) {
    if (stepIndex < 0 || stepIndex >= state.steps.length) {
      return;
    }
    final step = state.steps[stepIndex];
    final newCompletedSets = (step.completedSets + 1) > step.sets ? 0 : step.completedSets + 1;
    final isDone = newCompletedSets == step.sets;

    final updatedStep = step.copyWith(completedSets: newCompletedSets, isCompleted: isDone);

    final updatedList = List<ActiveStepItem>.from(state.steps);
    updatedList[stepIndex] = updatedStep;

    state = _withUpdatedGhostPace(state.copyWith(steps: updatedList));

    if (newCompletedSets > 0 && step.restDurationSeconds > 0) {
      startRestTimer(step.restDurationSeconds);
    }
  }

  void updateStepValues(int stepIndex, {double? weight, int? reps, int? rir, bool? isWarmup, int? restDurationSeconds}) {
    if (stepIndex < 0 || stepIndex >= state.steps.length) {
      return;
    }
    final step = state.steps[stepIndex];
    final updatedStep = step.copyWith(weight: weight, reps: reps, rir: rir, isWarmup: isWarmup, restDurationSeconds: restDurationSeconds);

    final updatedList = List<ActiveStepItem>.from(state.steps);
    updatedList[stepIndex] = updatedStep;
    state = _withUpdatedGhostPace(state.copyWith(steps: updatedList));
  }

  Future<void> autoregulateStepWithHybridAi(
    int stepIndex, {
    required double rpe,
    String? customNote,
    HybridInferenceMode mode = HybridInferenceMode.preferOnDevice,
  }) async {
    if (stepIndex < 0 || stepIndex >= state.steps.length) {
      return;
    }

    final item = state.steps[stepIndex];
    state = state.copyWith(isHybridAnalyzing: true);

    final hybridService = ref.read(atlasHybridAiServiceProvider);
    final rawSetText = '${item.exerciseName} ${item.weight}kg x ${item.reps} @ RPE $rpe ${customNote ?? ""}'.trim();

    final analysis = await hybridService.analyzeSetOfflineFirst(
      rawSetText: rawSetText,
      activeExercise: item.exercise,
      mode: mode,
    );

    if (stepIndex >= state.steps.length) {
      state = state.copyWith(isHybridAnalyzing: false);
      return;
    }

    final currentItem = state.steps[stepIndex];
    double adjustedWeight = currentItem.weight;
    int adjustedRest = currentItem.restDurationSeconds;
    String loadLabel = 'Keep ${currentItem.weight}kg';

    if (rpe >= 9.5) {
      if (currentItem.weight > 0) {
        adjustedWeight = ((currentItem.weight * 0.95) * 2).round() / 2.0;
        loadLabel = '-5% Load (${adjustedWeight}kg)';
      } else {
        loadLabel = '-5% Load';
      }
      if (adjustedRest < 180) {
        adjustedRest = 180;
      }
    } else if (rpe <= 7.5 && currentItem.weight > 0) {
      adjustedWeight = currentItem.weight + 2.5;
      loadLabel = '+2.5kg (${adjustedWeight}kg)';
    }

    final String sourceLabel = switch (analysis.inferenceSource) {
      HybridInferenceSource.onDevice => t.hybridAi.sourceOnDeviceShort,
      HybridInferenceSource.inCloud => t.hybridAi.sourceInCloudShort,
      HybridInferenceSource.localOfflineFallback => t.hybridAi.sourceOfflineEngine,
    };

    final badgeText = '$sourceLabel · ${analysis.latencyMs}ms · $loadLabel · ${analysis.nextSetRecommendation}';
    final int newCompletedSets = currentItem.completedSets < currentItem.sets ? currentItem.completedSets + 1 : currentItem.sets;
    final bool isDone = newCompletedSets >= currentItem.sets;

    final updatedStep = currentItem.copyWith(
      weight: adjustedWeight,
      restDurationSeconds: adjustedRest,
      completedSets: newCompletedSets,
      isCompleted: isDone,
      autopilotBadge: badgeText,
    );

    final updatedList = List<ActiveStepItem>.from(state.steps);
    updatedList[stepIndex] = updatedStep;

    state = _withUpdatedGhostPace(
      state.copyWith(
        steps: updatedList,
        lastHybridAnalysis: analysis,
        isHybridAnalyzing: false,
      ),
    );

    if (adjustedRest > 0) {
      startRestTimer(adjustedRest);
    }
  }

  void pairAsSuperset(int indexA, int indexB) {
    if (indexA < 0 || indexA >= state.steps.length) {
      return;
    }
    if (indexB < 0 || indexB >= state.steps.length) {
      return;
    }

    final groupId = 'ss-${_uuid.v4().substring(0, 8)}';
    final updatedList = List<ActiveStepItem>.from(state.steps);
    updatedList[indexA] = updatedList[indexA].copyWith(supersetGroupId: groupId);
    updatedList[indexB] = updatedList[indexB].copyWith(supersetGroupId: groupId);

    state = state.copyWith(steps: updatedList);
  }

  void unpairSuperset(int index) {
    if (index < 0 || index >= state.steps.length) {
      return;
    }
    final targetGroupId = state.steps[index].supersetGroupId;
    if (targetGroupId == null) {
      return;
    }

    final updatedList = state.steps.map((step) {
      if (step.supersetGroupId == targetGroupId) {
        return step.copyWith(clearSuperset: true);
      }
      return step;
    }).toList();

    state = state.copyWith(steps: updatedList);
  }

  void startRestTimer(int seconds) {
    state = state.copyWith(restTimerSecondsRemaining: seconds, restTimerTotalSeconds: seconds, isRestTimerActive: true);
  }

  void addRestTime(int additionalSeconds) {
    if (!state.isRestTimerActive) {
      startRestTimer(additionalSeconds);
      return;
    }
    state = state.copyWith(
      restTimerSecondsRemaining: state.restTimerSecondsRemaining + additionalSeconds,
      restTimerTotalSeconds: state.restTimerTotalSeconds + additionalSeconds,
    );
  }

  void skipRestTimer() {
    state = state.copyWith(restTimerSecondsRemaining: 0, isRestTimerActive: false);
  }

  void togglePause() {
    state = state.copyWith(isPaused: !state.isPaused);
  }

  void _startTicker() {
    _tickerTimer?.cancel();
    _tickerTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (state.isPaused || state.isFinished) {
        return;
      }

      final int newElapsed = state.elapsedSeconds + 1;
      int newRest = state.restTimerSecondsRemaining;
      bool restActive = state.isRestTimerActive;

      if (restActive && newRest > 0) {
        newRest -= 1;
        if (newRest <= 0) {
          restActive = false;
        }
      }

      state = state.copyWith(elapsedSeconds: newElapsed, restTimerSecondsRemaining: newRest, isRestTimerActive: restActive);
    });
  }

  String _resolveCurrentUserId() {
    try {
      final uid = ref.read(userRepositoryProvider).getCurrentUser()?.id;
      if (uid != null && uid.trim().isNotEmpty) {
        return uid;
      }
    } catch (_) {}
    return 'local-user';
  }

  Future<WorkoutSession> finishWorkout() async {
    _tickerTimer?.cancel();
    final now = DateTime.now();

    final completedSteps = state.steps.where((s) => s.completedSets > 0 && !s.isWarmup).toList();
    final workoutSteps = <WorkoutStep>[];
    for (int i = 0; i < completedSteps.length; i++) {
      final s = completedSteps[i];
      workoutSteps.add(
        WorkoutStep(
          exerciseId: s.exerciseId,
          sets: s.completedSets,
          reps: s.reps,
          weight: s.weight,
          targetDurationSeconds: s.targetDurationSeconds,
          restDurationSeconds: s.restDurationSeconds,
          orderIndex: i,
          isWarmup: s.isWarmup,
        ),
      );
    }

    final session = WorkoutSession(
      id: _uuid.v4(),
      userId: _resolveCurrentUserId(),
      routineId: state.routineId,
      routineTitle: state.routineTitle,
      startedAt: state.startedAt,
      completedAt: now,
      updatedAt: now,
      steps: workoutSteps,
    );

    if (completedSteps.isEmpty) {
      state = state.copyWith(isFinished: true);
      return session;
    }

    await ref.read(sessionRepositoryProvider).saveSession(session);
    state = state.copyWith(isFinished: true);
    ref.invalidate(dashboardViewModelProvider);
    ref.invalidate(muscleAnalyticsViewModelProvider);
    ref.invalidate(dataManagementViewModelProvider);
    return session;
  }
}
