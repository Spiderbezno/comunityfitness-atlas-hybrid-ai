// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';

typedef ExerciseModel = Exercise;

enum AiChatRole { user, coach }

enum AiLiveCoachState { disconnected, connecting, listening, thinking, speaking }

class AiAlternativeRequest {
  final Exercise exercise;
  final String constraint;

  const AiAlternativeRequest({required this.exercise, required this.constraint});

  Exercise get targetExercise => exercise;

  AiAlternativeRequest copyWith({Exercise? exercise, String? constraint}) {
    return AiAlternativeRequest(exercise: exercise ?? this.exercise, constraint: constraint ?? this.constraint);
  }
}

class AiExerciseRecommendation {
  final String exerciseId;
  final String exerciseName;
  final String matchReason;
  final String homeAdaptationTip;
  final int sets;
  final int reps;
  final int restSeconds;
  final List<String> keyBiomechanicalCues;
  final Exercise? catalogExercise;

  const AiExerciseRecommendation({
    required this.exerciseId,
    required this.exerciseName,
    required this.matchReason,
    required this.homeAdaptationTip,
    required this.sets,
    required this.reps,
    required this.restSeconds,
    required this.keyBiomechanicalCues,
    this.catalogExercise,
  });

  AiExerciseRecommendation copyWith({
    String? exerciseId,
    String? exerciseName,
    String? matchReason,
    String? homeAdaptationTip,
    int? sets,
    int? reps,
    int? restSeconds,
    List<String>? keyBiomechanicalCues,
    Exercise? catalogExercise,
  }) {
    return AiExerciseRecommendation(
      exerciseId: exerciseId ?? this.exerciseId,
      exerciseName: exerciseName ?? this.exerciseName,
      matchReason: matchReason ?? this.matchReason,
      homeAdaptationTip: homeAdaptationTip ?? this.homeAdaptationTip,
      sets: sets ?? this.sets,
      reps: reps ?? this.reps,
      restSeconds: restSeconds ?? this.restSeconds,
      keyBiomechanicalCues: keyBiomechanicalCues ?? this.keyBiomechanicalCues,
      catalogExercise: catalogExercise ?? this.catalogExercise,
    );
  }

  factory AiExerciseRecommendation.fromJson(Map<String, dynamic> json) {
    final rawCues = json['keyBiomechanicalCues'];
    final cues = rawCues is List ? rawCues.map((e) => e.toString()).toList() : const <String>[];

    return AiExerciseRecommendation(
      exerciseId: (json['exerciseId'] ?? '').toString(),
      exerciseName: (json['exerciseName'] ?? '').toString(),
      matchReason: (json['matchReason'] ?? '').toString(),
      homeAdaptationTip: (json['homeAdaptationTip'] ?? '').toString(),
      sets: (json['sets'] is num) ? (json['sets'] as num).toInt() : 3,
      reps: (json['reps'] is num) ? (json['reps'] as num).toInt() : 12,
      restSeconds: (json['restSeconds'] is num) ? (json['restSeconds'] as num).toInt() : 60,
      keyBiomechanicalCues: cues,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'exerciseId': exerciseId,
      'exerciseName': exerciseName,
      'matchReason': matchReason,
      'homeAdaptationTip': homeAdaptationTip,
      'sets': sets,
      'reps': reps,
      'restSeconds': restSeconds,
      'keyBiomechanicalCues': keyBiomechanicalCues,
    };
  }
}

class AiWorkoutPlan {
  final String title;
  final List<String> targetMuscles;
  final String coachSummary;
  final List<AiExerciseRecommendation> exercises;

  const AiWorkoutPlan({required this.title, required this.targetMuscles, required this.coachSummary, required this.exercises});

  AiWorkoutPlan copyWith({String? title, List<String>? targetMuscles, String? coachSummary, List<AiExerciseRecommendation>? exercises}) {
    return AiWorkoutPlan(
      title: title ?? this.title,
      targetMuscles: targetMuscles ?? this.targetMuscles,
      coachSummary: coachSummary ?? this.coachSummary,
      exercises: exercises ?? this.exercises,
    );
  }

  factory AiWorkoutPlan.fromJson(Map<String, dynamic> json) {
    final rawMuscles = json['targetMuscles'];
    final muscles = rawMuscles is List ? rawMuscles.map((e) => e.toString()).toList() : const <String>[];

    final rawExercises = json['exercises'];
    final exercises = rawExercises is List
        ? rawExercises.whereType<Map<String, dynamic>>().map(AiExerciseRecommendation.fromJson).toList()
        : const <AiExerciseRecommendation>[];

    return AiWorkoutPlan(
      title: (json['title'] ?? 'Custom AI Workout Plan').toString(),
      targetMuscles: muscles,
      coachSummary: (json['coachSummary'] ?? '').toString(),
      exercises: exercises,
    );
  }

  Map<String, dynamic> toJson() {
    return {'title': title, 'targetMuscles': targetMuscles, 'coachSummary': coachSummary, 'exercises': exercises.map((e) => e.toJson()).toList()};
  }
}

class AiChatMessage {
  final String id;
  final AiChatRole role;
  final String text;
  final DateTime timestamp;
  final AiWorkoutPlan? workoutPlan;
  final List<AiExerciseRecommendation>? alternatives;
  final bool isLiveTranscript;

  const AiChatMessage({
    required this.id,
    required this.role,
    required this.text,
    required this.timestamp,
    this.workoutPlan,
    this.alternatives,
    this.isLiveTranscript = false,
  });

  AiChatMessage copyWith({
    String? id,
    AiChatRole? role,
    String? text,
    DateTime? timestamp,
    AiWorkoutPlan? workoutPlan,
    List<AiExerciseRecommendation>? alternatives,
    bool? isLiveTranscript,
  }) {
    return AiChatMessage(
      id: id ?? this.id,
      role: role ?? this.role,
      text: text ?? this.text,
      timestamp: timestamp ?? this.timestamp,
      workoutPlan: workoutPlan ?? this.workoutPlan,
      alternatives: alternatives ?? this.alternatives,
      isLiveTranscript: isLiveTranscript ?? this.isLiveTranscript,
    );
  }
}

class AiLiveCoachEvent {
  final AiLiveCoachState state;
  final String? transcript;
  final String? userTranscript;
  final String? spokenCue;
  final String? interactionStatus;
  final bool? isMicRecording;
  final AiWorkoutPlan? workoutPlan;
  final List<AiExerciseRecommendation>? alternatives;
  final DateTime timestamp;

  const AiLiveCoachEvent({
    required this.state,
    required this.timestamp,
    this.transcript,
    this.userTranscript,
    this.spokenCue,
    this.interactionStatus,
    this.isMicRecording,
    this.workoutPlan,
    this.alternatives,
  });
}
