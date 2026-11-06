// ignore_for_file: prefer_initializing_formals

// 📦 Package imports:
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/ai_coach_models.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/services/ai_coach_service.dart';

part 'ai_coach_repository.g.dart';

/// Pure function that hydrates each [AiExerciseRecommendation] with its
/// corresponding [Exercise] from the local catalog.
List<AiExerciseRecommendation> hydrateRecommendations(List<AiExerciseRecommendation> recommendations, List<ExerciseModel> catalog) {
  final byId = {for (final e in catalog) e.id: e};
  final byName = {for (final e in catalog) e.name.toLowerCase(): e};

  return recommendations.map((rec) {
    if (rec.catalogExercise != null) {
      return rec;
    }
    final match = byId[rec.exerciseId] ?? byName[rec.exerciseName.toLowerCase()];
    if (match == null) {
      return rec;
    }
    return rec.copyWith(exerciseId: match.id, exerciseName: match.name, catalogExercise: match);
  }).toList();
}

/// Pure function that hydrates all exercises inside an [AiWorkoutPlan]
/// with their corresponding [Exercise] entries from the catalog.
AiWorkoutPlan hydrateWorkoutPlan(AiWorkoutPlan plan, List<ExerciseModel> catalog) {
  return plan.copyWith(exercises: hydrateRecommendations(plan.exercises, catalog));
}

/// Pure function that filters the exercise catalog by target muscle groups
/// and equipment constraints.
List<ExerciseModel> filterCatalogForTargets({
  required List<ExerciseModel> catalog,
  required List<String> targetMuscles,
  required String equipmentConstraint,
}) {
  return FirebaseAiCoachService.filterCatalogByMusclesAndEquipment(
    targetMuscles: targetMuscles,
    equipmentConstraint: equipmentConstraint,
    catalog: catalog,
  );
}

@riverpod
AiCoachRepository aiCoachRepository(Ref ref) {
  final service = ref.watch(aiCoachServiceProvider);
  final exerciseRepository = ref.watch(exerciseRepositoryProvider);
  return AiCoachRepository(aiCoachService: service, exerciseRepository: exerciseRepository);
}

class AiCoachRepository {
  final AiCoachService _aiCoachService;
  final ExerciseRepository _exerciseRepository;

  AiCoachRepository({required AiCoachService aiCoachService, required ExerciseRepository exerciseRepository})
    : _aiCoachService = aiCoachService,
      _exerciseRepository = exerciseRepository;

  String get chatModelName => _aiCoachService.chatModelName;
  String get liveModelName => _aiCoachService.liveModelName;

  Stream<AiLiveCoachEvent> get liveEvents => _aiCoachService.liveEvents;
  AiLiveCoachState get currentLiveState => _aiCoachService.currentLiveState;
  bool get isMicRecording => _aiCoachService.isMicRecording;

  Future<List<ExerciseModel>> loadCatalog() async {
    var exercises = _exerciseRepository.getExercises();
    if (exercises.isEmpty) {
      await _exerciseRepository.seedIfNeeded();
      exercises = _exerciseRepository.getExercises();
    }
    return exercises;
  }

  Future<List<AiExerciseRecommendation>> getExerciseAlternatives({required ExerciseModel exercise, required String constraint}) async {
    final catalog = await loadCatalog();
    final raw = await _aiCoachService.suggestAlternatives(exercise: exercise, constraint: constraint, catalog: catalog);
    return hydrateRecommendations(raw, catalog);
  }

  Future<AiWorkoutPlan> generateMuscleWorkoutPlan({
    required List<String> targetMuscles,
    required String equipmentConstraint,
    String userPrompt = '',
  }) async {
    final catalog = await loadCatalog();
    final rawPlan = await _aiCoachService.planWorkoutByMuscles(
      targetMuscles: targetMuscles,
      equipmentConstraint: equipmentConstraint,
      userPrompt: userPrompt,
      catalog: catalog,
    );
    return hydrateWorkoutPlan(rawPlan, catalog);
  }

  Future<AiChatMessage> sendMessage({required String message, required List<AiChatMessage> history, ExerciseModel? contextExercise}) async {
    final catalog = await loadCatalog();
    final reply = await _aiCoachService.sendCoachMessage(message: message, history: history, catalog: catalog, contextExercise: contextExercise);

    return reply.copyWith(
      workoutPlan: reply.workoutPlan != null ? hydrateWorkoutPlan(reply.workoutPlan!, catalog) : null,
      alternatives: reply.alternatives != null ? hydrateRecommendations(reply.alternatives!, catalog) : null,
    );
  }

  Future<void> startLiveSession({ExerciseModel? activeExercise}) async {
    final catalog = await loadCatalog();
    await _aiCoachService.startLiveCoachSession(catalog: catalog, activeExercise: activeExercise);
  }

  Future<void> sendLiveTurn({required String userUtterance, ExerciseModel? activeExercise}) async {
    final catalog = await loadCatalog();
    await _aiCoachService.sendLiveVoiceOrTextTurn(userUtterance: userUtterance, catalog: catalog, activeExercise: activeExercise);
  }

  Future<bool> startMicRecording({ExerciseModel? activeExercise}) async {
    final catalog = await loadCatalog();
    return _aiCoachService.startLiveMicRecording(catalog: catalog, activeExercise: activeExercise);
  }

  Future<String> stopMicRecording({ExerciseModel? activeExercise, String? fallbackUtterance}) async {
    final catalog = await loadCatalog();
    return _aiCoachService.stopLiveMicRecording(catalog: catalog, activeExercise: activeExercise, fallbackUtterance: fallbackUtterance);
  }

  Future<void> stopLiveSession() async {
    await _aiCoachService.stopLiveCoachSession();
  }
}
