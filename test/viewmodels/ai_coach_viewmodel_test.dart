// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/ai_coach_models.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/services/ai_coach_service.dart';
import 'package:comunityfitness/viewmodels/ai_coach_viewmodel.dart';

class MockExerciseRepository extends Mock implements ExerciseRepository {}

void main() {
  late MockExerciseRepository mockExerciseRepository;
  late FirebaseAiCoachService aiCoachService;
  late List<Exercise> sampleExercises;

  setUp(() {
    mockExerciseRepository = MockExerciseRepository();
    aiCoachService = FirebaseAiCoachService(enablePlatformCues: false);

    sampleExercises = const [
      Exercise(
        id: 'bench_press',
        name: 'Bench Press',
        primaryMuscleGroup: 'Chest',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: 'assets/animations/bench_press.riv',
        description: 'Compound barbell chest press.',
      ),
      Exercise(
        id: 'push_up',
        name: 'Push Up',
        primaryMuscleGroup: 'Chest',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: 'assets/animations/push_up.riv',
        description: 'Bodyweight chest and triceps press.',
      ),
      Exercise(
        id: 'pull_up',
        name: 'Pull Up',
        primaryMuscleGroup: 'Back',
        equipment: 'Bodyweight',
        animationType: 'movekit',
        animationPath: 'assets/animations/pull_up.movekit',
        description: 'Bodyweight vertical back pull.',
      ),
      Exercise(
        id: 'crunch',
        name: 'Abdominal Crunch',
        primaryMuscleGroup: 'Core',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: 'assets/animations/crunch.riv',
        description: 'Bodyweight abdominal flexion.',
      ),
    ];

    when(() => mockExerciseRepository.getExercises()).thenReturn(sampleExercises);
    when(() => mockExerciseRepository.seedIfNeeded()).thenAnswer((_) async {});
  });

  ProviderContainer makeContainer() {
    return ProviderContainer(
      overrides: [exerciseRepositoryProvider.overrideWithValue(mockExerciseRepository), aiCoachServiceProvider.overrideWithValue(aiCoachService)],
    );
  }

  test('AiCoachViewModel initializes with welcome message and Gemini 3.8 models', () {
    final container = makeContainer();
    final state = container.read(aiCoachViewModelProvider);

    expect(state.chatModelName, 'gemini-3.8-flash');
    expect(state.liveModelName, 'gemini-3.8-live');
    expect(state.messages.length, 1);
    expect(state.messages.first.role, AiChatRole.coach);
    container.dispose();
  });

  test('AiCoachViewModel requests home alternatives for an exercise', () async {
    final container = makeContainer();
    final sub = container.listen(aiCoachViewModelProvider, (_, _) {});
    final vm = container.read(aiCoachViewModelProvider.notifier);

    await vm.requestExerciseAlternatives(exercise: sampleExercises.first, customConstraint: 'At Home / No Weights');

    final state = container.read(aiCoachViewModelProvider);
    expect(state.contextExercise?.id, 'bench_press');
    expect(state.currentAlternatives, isNotEmpty);
    expect(state.currentAlternatives.any((a) => a.exerciseId == 'push_up'), isTrue);
    expect(state.messages.last.alternatives, isNotEmpty);

    sub.close();
    container.dispose();
  });

  test('AiCoachViewModel toggles muscles and generates a tailored workout plan', () async {
    final container = makeContainer();
    final sub = container.listen(aiCoachViewModelProvider, (_, _) {});
    final vm = container.read(aiCoachViewModelProvider.notifier);

    vm.toggleTargetMuscle('Abs / Core');
    vm.setEquipmentConstraint('Home / Bodyweight');
    await vm.generateWorkoutForSelectedMuscles();

    final state = container.read(aiCoachViewModelProvider);
    expect(state.selectedMuscles, contains('Abs / Core'));
    expect(state.latestWorkoutPlan, isNotNull);
    expect(state.latestWorkoutPlan!.exercises, isNotEmpty);

    sub.close();
    container.dispose();
  });

  test('AiCoachViewModel toggles Gemini 3.8 Live voice coach mode and processes turns', () async {
    final container = makeContainer();
    final sub = container.listen(aiCoachViewModelProvider, (_, _) {});
    final vm = container.read(aiCoachViewModelProvider.notifier);

    await vm.toggleLiveCoachMode();
    await Future<void>.delayed(Duration.zero);

    var state = container.read(aiCoachViewModelProvider);
    expect(state.isLiveModeActive, isTrue);
    expect(state.liveState, AiLiveCoachState.listening);

    await vm.sendLiveVoiceTurn('Give me a chest and core home workout');
    await Future<void>.delayed(Duration.zero);

    state = container.read(aiCoachViewModelProvider);
    expect(state.latestWorkoutPlan, isNotNull);

    await vm.toggleLiveCoachMode();
    await Future<void>.delayed(Duration.zero);
    state = container.read(aiCoachViewModelProvider);
    expect(state.isLiveModeActive, isFalse);
    expect(state.liveState, AiLiveCoachState.disconnected);

    sub.close();
    container.dispose();
  });
}
