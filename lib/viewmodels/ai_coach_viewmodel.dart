// 🎯 Dart imports:
import 'dart:async';

// 📦 Package imports:
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:uuid/uuid.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/ai_coach_models.dart';
import 'package:comunityfitness/repositories/ai_coach_repository.dart';

part 'ai_coach_viewmodel.g.dart';

class AiCoachState {
  static const List<String> availableTargetMuscles = [
    'Chest',
    'Back',
    'Shoulders',
    'Biceps',
    'Triceps',
    'Quadriceps',
    'Hamstrings',
    'Glutes',
    'Calves',
    'Abs / Core',
  ];

  static const List<String> availableEquipmentFilters = ['All', 'Home / Bodyweight', 'Dumbbells Only'];

  static const List<String> alternativeQuickConstraints = ['At Home / No Weights', 'Bodyweight Only', 'Dumbbells Only', 'Joint Friendly'];

  final List<AiChatMessage> messages;
  final List<String> selectedMuscles;
  final String selectedEquipmentConstraint;
  final String selectedAlternativeConstraint;
  final ExerciseModel? contextExercise;
  final List<AiExerciseRecommendation> currentAlternatives;
  final AiWorkoutPlan? latestWorkoutPlan;
  final bool isLoading;
  final String? errorMessage;
  final bool isLiveModeActive;
  final bool isMicRecording;
  final AiLiveCoachState liveState;
  final String? liveSpokenCue;
  final String? liveInteractionStatus;
  final String chatModelName;
  final String liveModelName;

  const AiCoachState({
    required this.messages,
    this.selectedMuscles = const ['Chest', 'Back'],
    this.selectedEquipmentConstraint = 'All',
    this.selectedAlternativeConstraint = 'At Home / No Weights',
    this.contextExercise,
    this.currentAlternatives = const [],
    this.latestWorkoutPlan,
    this.isLoading = false,
    this.errorMessage,
    this.isLiveModeActive = false,
    this.isMicRecording = false,
    this.liveState = AiLiveCoachState.disconnected,
    this.liveSpokenCue,
    this.liveInteractionStatus,
    this.chatModelName = 'gemini-3.8-flash',
    this.liveModelName = 'gemini-3.8-live',
  });

  AiCoachState copyWith({
    List<AiChatMessage>? messages,
    List<String>? selectedMuscles,
    String? selectedEquipmentConstraint,
    String? selectedAlternativeConstraint,
    ExerciseModel? contextExercise,
    bool clearContextExercise = false,
    List<AiExerciseRecommendation>? currentAlternatives,
    AiWorkoutPlan? latestWorkoutPlan,
    bool? isLoading,
    String? errorMessage,
    bool clearError = false,
    bool? isLiveModeActive,
    bool? isMicRecording,
    AiLiveCoachState? liveState,
    String? liveSpokenCue,
    String? liveInteractionStatus,
    String? chatModelName,
    String? liveModelName,
  }) {
    return AiCoachState(
      messages: messages ?? this.messages,
      selectedMuscles: selectedMuscles ?? this.selectedMuscles,
      selectedEquipmentConstraint: selectedEquipmentConstraint ?? this.selectedEquipmentConstraint,
      selectedAlternativeConstraint: selectedAlternativeConstraint ?? this.selectedAlternativeConstraint,
      contextExercise: clearContextExercise ? null : (contextExercise ?? this.contextExercise),
      currentAlternatives: currentAlternatives ?? this.currentAlternatives,
      latestWorkoutPlan: latestWorkoutPlan ?? this.latestWorkoutPlan,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
      isLiveModeActive: isLiveModeActive ?? this.isLiveModeActive,
      isMicRecording: isMicRecording ?? this.isMicRecording,
      liveState: liveState ?? this.liveState,
      liveSpokenCue: liveSpokenCue ?? this.liveSpokenCue,
      liveInteractionStatus: liveInteractionStatus ?? this.liveInteractionStatus,
      chatModelName: chatModelName ?? this.chatModelName,
      liveModelName: liveModelName ?? this.liveModelName,
    );
  }
}

@riverpod
class AiCoachViewModel extends _$AiCoachViewModel {
  static const Uuid _uuid = Uuid();
  late AiCoachRepository _repository;
  StreamSubscription<AiLiveCoachEvent>? _liveSubscription;

  @override
  AiCoachState build() {
    _repository = ref.watch(aiCoachRepositoryProvider);

    _liveSubscription?.cancel();
    _liveSubscription = _repository.liveEvents.listen(_onLiveEvent);
    ref.onDispose(() {
      _liveSubscription?.cancel();
      if (_repository.currentLiveState != AiLiveCoachState.disconnected || _repository.isMicRecording) {
        unawaited(_repository.stopLiveSession());
      }
    });

    final welcomeMessage = AiChatMessage(
      id: 'welcome-coach-msg',
      role: AiChatRole.coach,
      text: t.aiCoach.welcomeMessage(chatModel: _repository.chatModelName, liveModel: _repository.liveModelName),
      timestamp: DateTime.now(),
    );

    return AiCoachState(messages: [welcomeMessage], chatModelName: _repository.chatModelName, liveModelName: _repository.liveModelName);
  }

  void refreshLocale() {
    final updatedMessages = state.messages.map((msg) {
      if (msg.id == 'welcome-coach-msg') {
        return AiChatMessage(
          id: msg.id,
          role: msg.role,
          text: t.aiCoach.welcomeMessage(chatModel: state.chatModelName, liveModel: state.liveModelName),
          timestamp: msg.timestamp,
        );
      }
      return msg;
    }).toList();
    state = state.copyWith(messages: updatedMessages);
  }

  void toggleTargetMuscle(String muscle) {
    final current = List<String>.from(state.selectedMuscles);
    if (current.contains(muscle)) {
      if (current.length > 1) {
        current.remove(muscle);
      }
    } else {
      current.add(muscle);
    }
    state = state.copyWith(selectedMuscles: current, clearError: true);
  }

  void setEquipmentConstraint(String equipmentConstraint) {
    state = state.copyWith(selectedEquipmentConstraint: equipmentConstraint, clearError: true);
  }

  void setAlternativeConstraint(String constraint) {
    state = state.copyWith(selectedAlternativeConstraint: constraint, clearError: true);
  }

  void setContextExercise(ExerciseModel? exercise) {
    if (exercise == null) {
      state = state.copyWith(clearContextExercise: true);
    } else {
      state = state.copyWith(contextExercise: exercise);
    }
  }

  String _localizedAltRequestText(String exerciseName, String constraint) {
    final localizedConstraint = t.translateConstraint(constraint);
    switch (LocaleSettings.currentLocale) {
      case AppLocale.es:
        return 'Sugiere alternativas ($localizedConstraint) para $exerciseName.';
      case AppLocale.ca:
        return 'Suggereix alternatives ($localizedConstraint) per a $exerciseName.';
      case AppLocale.fr:
        return 'Suggère des alternatives ($localizedConstraint) pour $exerciseName.';
      case AppLocale.pt:
        return 'Sugere alternativas ($localizedConstraint) para $exerciseName.';
      case AppLocale.en:
        return 'Suggest $constraint alternatives for $exerciseName.';
    }
  }

  String _localizedAltReplyIntro(int count, String constraint, String exerciseName) {
    final localizedConstraint = t.translateConstraint(constraint);
    switch (LocaleSettings.currentLocale) {
      case AppLocale.es:
        return 'Aquí tienes $count alternativas biomecánicamente equivalentes ("$localizedConstraint") para $exerciseName del catálogo de la app:';
      case AppLocale.ca:
        return 'Aquí tens $count alternatives biomecànicament equivalents ("$localizedConstraint") per a $exerciseName del catàleg de l\'app:';
      case AppLocale.fr:
        return 'Voici $count alternatives biomécaniquement équivalentes ("$localizedConstraint") pour $exerciseName du catalogue de l\'application :';
      case AppLocale.pt:
        return 'Aqui estão $count alternativas biomecanicamente equivalentes ("$localizedConstraint") para $exerciseName do catálogo da app:';
      case AppLocale.en:
        return 'Here are $count biomechanically matched "$constraint" alternatives for $exerciseName from the app catalog:';
    }
  }

  Future<void> requestExerciseAlternatives({required ExerciseModel exercise, String? customConstraint}) async {
    final constraint = (customConstraint != null && customConstraint.trim().isNotEmpty)
        ? customConstraint.trim()
        : state.selectedAlternativeConstraint;

    final userMsg = AiChatMessage(
      id: _uuid.v4(),
      role: AiChatRole.user,
      text: _localizedAltRequestText(exercise.name, constraint),
      timestamp: DateTime.now(),
    );

    state = state.copyWith(
      contextExercise: exercise,
      selectedAlternativeConstraint: constraint,
      messages: [...state.messages, userMsg],
      isLoading: true,
      clearError: true,
    );

    try {
      final alternatives = await _repository.getExerciseAlternatives(exercise: exercise, constraint: constraint);
      if (!ref.mounted) {
        return;
      }

      final coachMsg = AiChatMessage(
        id: _uuid.v4(),
        role: AiChatRole.coach,
        text: _localizedAltReplyIntro(alternatives.length, constraint, exercise.name),
        timestamp: DateTime.now(),
        alternatives: alternatives,
      );

      state = state.copyWith(currentAlternatives: alternatives, messages: [...state.messages, coachMsg], isLoading: false);
    } catch (e) {
      if (!ref.mounted) {
        return;
      }
      state = state.copyWith(isLoading: false, errorMessage: t.aiCoach.errors.loadAlternatives);
    }
  }

  Future<void> generateWorkoutForSelectedMuscles({String userPrompt = ''}) async {
    final muscles = state.selectedMuscles.isEmpty ? const ['Chest', 'Back'] : state.selectedMuscles;
    final equipment = state.selectedEquipmentConstraint;

    final translatedMuscles = muscles.map((m) => t.translateMuscle(m)).join(', ');
    final translatedEq = t.translateEquipment(equipment);

    final promptSummary = userPrompt.trim().isNotEmpty
        ? userPrompt.trim()
        : t.aiCoach.plannerCard.buildPlanButton(muscles: translatedMuscles, equipment: translatedEq);

    final userMsg = AiChatMessage(id: _uuid.v4(), role: AiChatRole.user, text: promptSummary, timestamp: DateTime.now());

    state = state.copyWith(messages: [...state.messages, userMsg], isLoading: true, clearError: true);

    try {
      final plan = await _repository.generateMuscleWorkoutPlan(targetMuscles: muscles, equipmentConstraint: equipment, userPrompt: userPrompt);
      if (!ref.mounted) {
        return;
      }

      final coachMsg = AiChatMessage(id: _uuid.v4(), role: AiChatRole.coach, text: plan.coachSummary, timestamp: DateTime.now(), workoutPlan: plan);

      state = state.copyWith(latestWorkoutPlan: plan, messages: [...state.messages, coachMsg], isLoading: false);
    } catch (e) {
      if (!ref.mounted) {
        return;
      }
      state = state.copyWith(isLoading: false, errorMessage: t.aiCoach.errors.buildPlan);
    }
  }

  Future<void> sendChatMessage(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty) {
      return;
    }

    if (state.isLiveModeActive) {
      await sendLiveVoiceTurn(trimmed);
      return;
    }

    final userMsg = AiChatMessage(id: _uuid.v4(), role: AiChatRole.user, text: trimmed, timestamp: DateTime.now());

    final updatedHistory = [...state.messages, userMsg];
    state = state.copyWith(messages: updatedHistory, isLoading: true, clearError: true);

    try {
      final reply = await _repository.sendMessage(message: trimmed, history: updatedHistory, contextExercise: state.contextExercise);
      if (!ref.mounted) {
        return;
      }

      state = state.copyWith(
        messages: [...state.messages, reply],
        currentAlternatives: reply.alternatives ?? state.currentAlternatives,
        latestWorkoutPlan: reply.workoutPlan ?? state.latestWorkoutPlan,
        isLoading: false,
      );
    } catch (e) {
      if (!ref.mounted) {
        return;
      }
      state = state.copyWith(isLoading: false, errorMessage: t.aiCoach.errors.coachReply);
    }
  }

  Future<void> toggleLiveCoachMode() async {
    if (state.isLiveModeActive) {
      await _repository.stopLiveSession();
      if (!ref.mounted) {
        return;
      }
      state = state.copyWith(isLiveModeActive: false, isMicRecording: false, liveState: AiLiveCoachState.disconnected);
    } else {
      state = state.copyWith(isLiveModeActive: true, liveState: AiLiveCoachState.connecting, clearError: true);
      await _repository.startLiveSession(activeExercise: state.contextExercise);
      if (!ref.mounted) {
        return;
      }
      state = state.copyWith(isMicRecording: _repository.isMicRecording);
    }
  }

  Future<void> toggleMicRecording() async {
    if (!state.isMicRecording) {
      state = state.copyWith(isLiveModeActive: true, isMicRecording: true, clearError: true);
      await _repository.startMicRecording(activeExercise: state.contextExercise);
      return;
    }

    final translatedMuscles = state.selectedMuscles.map((m) => t.translateMuscle(m)).join(' & ');
    final translatedEq = t.translateEquipment(state.selectedEquipmentConstraint);

    final fallbackPrompt = state.contextExercise != null
        ? _localizedAltRequestText(state.contextExercise!.name, state.selectedAlternativeConstraint)
        : t.aiCoach.plannerCard.buildPlanButton(muscles: translatedMuscles, equipment: translatedEq);

    state = state.copyWith(isMicRecording: false, isLoading: true, clearError: true);

    final recognizedOrFallback = await _repository.stopMicRecording(activeExercise: state.contextExercise, fallbackUtterance: fallbackPrompt);
    if (!ref.mounted) {
      return;
    }

    if (recognizedOrFallback.trim().isEmpty) {
      state = state.copyWith(isMicRecording: _repository.isMicRecording, isLoading: false);
      return;
    }

    final userMsg = AiChatMessage(
      id: _uuid.v4(),
      role: AiChatRole.user,
      text: '🎙️ $recognizedOrFallback',
      timestamp: DateTime.now(),
      isLiveTranscript: true,
    );

    // Insert user spoken bubble right before the latest coach response if one was emitted
    final msgs = List<AiChatMessage>.from(state.messages);
    if (msgs.isNotEmpty && msgs.last.role == AiChatRole.coach && msgs.last.isLiveTranscript) {
      final lastCoach = msgs.removeLast();
      msgs.add(userMsg);
      msgs.add(lastCoach);
    } else {
      msgs.add(userMsg);
    }

    state = state.copyWith(isLoading: false, messages: msgs);
  }

  Future<void> sendLiveVoiceTurn(String utterance) async {
    final trimmed = utterance.trim();
    if (trimmed.isEmpty) {
      return;
    }

    final userMsg = AiChatMessage(id: _uuid.v4(), role: AiChatRole.user, text: trimmed, timestamp: DateTime.now(), isLiveTranscript: true);

    state = state.copyWith(messages: [...state.messages, userMsg], isLoading: true, clearError: true);

    await _repository.sendLiveTurn(userUtterance: trimmed, activeExercise: state.contextExercise);
    if (!ref.mounted) {
      return;
    }

    state = state.copyWith(isLoading: false);
  }

  void _onLiveEvent(AiLiveCoachEvent event) {
    if (!ref.mounted) {
      return;
    }
    final updatedMessages = List<AiChatMessage>.from(state.messages);

    if (event.userTranscript != null && event.userTranscript!.trim().isNotEmpty) {
      final userText = '🎙️ ${event.userTranscript!.trim()}';
      if (updatedMessages.isEmpty || updatedMessages.last.text != userText) {
        updatedMessages.add(AiChatMessage(id: _uuid.v4(), role: AiChatRole.user, text: userText, timestamp: event.timestamp, isLiveTranscript: true));
      }
    }

    final isLiveInterimMic = event.transcript != null && event.transcript!.startsWith('🎙️ "');

    final shouldAppendTranscript =
        event.state == AiLiveCoachState.listening &&
        !isLiveInterimMic &&
        event.transcript != null &&
        event.transcript!.isNotEmpty &&
        (updatedMessages.isEmpty || updatedMessages.last.text != event.transcript);

    if (shouldAppendTranscript) {
      updatedMessages.add(
        AiChatMessage(
          id: _uuid.v4(),
          role: AiChatRole.coach,
          text: event.transcript!,
          timestamp: event.timestamp,
          workoutPlan: event.workoutPlan,
          alternatives: event.alternatives,
          isLiveTranscript: true,
        ),
      );
    }

    state = state.copyWith(
      liveState: event.state,
      isLiveModeActive: event.state != AiLiveCoachState.disconnected,
      isMicRecording: event.isMicRecording ?? state.isMicRecording,
      liveSpokenCue: event.spokenCue ?? event.transcript ?? state.liveSpokenCue,
      liveInteractionStatus: event.interactionStatus ?? state.liveInteractionStatus,
      messages: updatedMessages,
      latestWorkoutPlan: event.workoutPlan ?? state.latestWorkoutPlan,
      currentAlternatives: event.alternatives ?? state.currentAlternatives,
    );
  }
}
