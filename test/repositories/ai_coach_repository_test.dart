// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/ai_coach_models.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/repositories/ai_coach_repository.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/services/ai_coach_service.dart';

class MockExerciseRepository extends Mock implements ExerciseRepository {}

void main() {
  late MockExerciseRepository mockExerciseRepository;
  late FirebaseAiCoachService aiCoachService;
  late AiCoachRepository repository;
  late List<Exercise> sampleCatalog;

  setUp(() {
    mockExerciseRepository = MockExerciseRepository();
    aiCoachService = FirebaseAiCoachService(enablePlatformCues: false);
    repository = AiCoachRepository(aiCoachService: aiCoachService, exerciseRepository: mockExerciseRepository);

    sampleCatalog = const [
      Exercise(
        id: 'bench_press',
        name: 'Bench Press',
        primaryMuscleGroup: 'Chest',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: 'assets/animations/bench_press.riv',
        description: 'A compound exercise that builds chest strength and mass.',
      ),
      Exercise(
        id: 'push_up',
        name: 'Push Up',
        primaryMuscleGroup: 'Chest',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: 'assets/animations/push_up.riv',
        description: 'A classic upper body exercise targeting the chest, shoulders, and triceps.',
      ),
      Exercise(
        id: 'push_up_diamond',
        name: 'Diamond Push Up',
        primaryMuscleGroup: 'Chest',
        equipment: 'Bodyweight',
        animationType: 'movekit',
        animationPath: 'assets/animations/push_up_diamond.movekit',
        description: 'A push up variation placing more emphasis on triceps and inner chest.',
      ),
      Exercise(
        id: 'dips',
        name: 'Chest Dips',
        primaryMuscleGroup: 'Chest',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: 'assets/animations/dips.riv',
        description: 'An advanced bodyweight exercise for the lower chest and triceps.',
      ),
      Exercise(
        id: 'pull_up',
        name: 'Pull Up',
        primaryMuscleGroup: 'Back',
        equipment: 'Bodyweight',
        animationType: 'movekit',
        animationPath: 'assets/animations/pull_up.movekit',
        description: 'A fundamental vertical pulling exercise for back width.',
      ),
      Exercise(
        id: 'plank',
        name: 'Plank',
        primaryMuscleGroup: 'Core',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: 'assets/animations/plank.riv',
        description: 'Isometric core stability exercise.',
      ),
    ];

    when(() => mockExerciseRepository.getExercises()).thenReturn(sampleCatalog);
    when(() => mockExerciseRepository.seedIfNeeded()).thenAnswer((_) async {});
  });

  group('AiCoachService & AiCoachRepository', () {
    test('uses gemini-3.8-flash and gemini-3.8-live models', () {
      expect(repository.chatModelName, 'gemini-3.8-flash');
      expect(repository.liveModelName, 'gemini-3.8-live');
    });

    test('suggests bodyweight home alternatives for Barbell Bench Press and hydrates catalogExercise', () async {
      final benchPress = sampleCatalog.first;
      final alternatives = await repository.getExerciseAlternatives(exercise: benchPress, constraint: 'At Home / No Weights');

      expect(alternatives, isNotEmpty);
      expect(alternatives.every((a) => a.catalogExercise?.equipment == 'Bodyweight'), isTrue);
      expect(alternatives.any((a) => a.exerciseId == 'push_up'), isTrue);
      expect(alternatives.first.homeAdaptationTip, isNotEmpty);
      expect(alternatives.first.keyBiomechanicalCues, isNotEmpty);
    });

    test('generates a workout plan filtered by target muscles and home equipment constraint', () async {
      final plan = await repository.generateMuscleWorkoutPlan(
        targetMuscles: const ['Chest', 'Back', 'Abs / Core'],
        equipmentConstraint: 'Home / Bodyweight',
        userPrompt: 'No weights at home',
      );

      expect(plan.exercises, isNotEmpty);
      expect(plan.targetMuscles, containsAll(['Chest', 'Back', 'Abs / Core']));
      expect(plan.exercises.any((e) => e.exerciseId == 'push_up'), isTrue);
      expect(plan.exercises.any((e) => e.exerciseId == 'pull_up'), isTrue);
      expect(plan.exercises.any((e) => e.exerciseId == 'plank'), isTrue);
    });

    test('emits live personal trainer events (connecting -> listening -> thinking -> listening -> disconnected)', () async {
      final events = <AiLiveCoachEvent>[];
      final sub = repository.liveEvents.listen(events.add);

      await repository.startLiveSession(activeExercise: sampleCatalog.first);
      await repository.sendLiveTurn(userUtterance: 'Give me a home alternative for Bench Press with no weights', activeExercise: sampleCatalog.first);
      await repository.stopLiveSession();

      await Future<void>.delayed(Duration.zero);

      expect(
        events.map((e) => e.state),
        containsAllInOrder([
          AiLiveCoachState.connecting,
          AiLiveCoachState.listening,
          AiLiveCoachState.thinking,
          AiLiveCoachState.listening,
          AiLiveCoachState.disconnected,
        ]),
      );

      await sub.cancel();
    });

    test('FirebaseAiGoogleClient fails closed without network request when App Check token is null or empty', () async {
      var networkCalls = 0;

      final nullTokenClient = FirebaseAiGoogleClient(
        appCheckTokenProvider: () async => null,
        authTokenProvider: () async => 'valid-auth-token',
        apiKeyOverride: 'test-api-key',
        projectIdOverride: 'test-project',
        httpTransport: (uri, headers, body) async {
          networkCalls++;
          return (statusCode: 200, body: '{}');
        },
      );

      final res1 = await nullTokenClient.generateStructuredText(model: 'gemini-3.8-flash', systemInstruction: 'sys', prompt: 'prompt');
      expect(res1, isNull);
      expect(networkCalls, 0);

      final emptyTokenClient = FirebaseAiGoogleClient(
        appCheckTokenProvider: () async => '   ',
        authTokenProvider: () async => 'valid-auth-token',
        apiKeyOverride: 'test-api-key',
        projectIdOverride: 'test-project',
        httpTransport: (uri, headers, body) async {
          networkCalls++;
          return (statusCode: 200, body: '{}');
        },
      );

      final res2 = await emptyTokenClient.generateStructuredText(model: 'gemini-3.8-flash', systemInstruction: 'sys', prompt: 'prompt');
      expect(res2, isNull);
      expect(networkCalls, 0);
    });

    test('FirebaseAiGoogleClient fails closed without network request when Auth token is null or empty', () async {
      var networkCalls = 0;

      final nullAuthClient = FirebaseAiGoogleClient(
        appCheckTokenProvider: () async => 'valid-app-check-token',
        authTokenProvider: () async => null,
        apiKeyOverride: 'test-api-key',
        projectIdOverride: 'test-project',
        httpTransport: (uri, headers, body) async {
          networkCalls++;
          return (statusCode: 200, body: '{}');
        },
      );

      final res1 = await nullAuthClient.generateStructuredText(model: 'gemini-3.8-flash', systemInstruction: 'sys', prompt: 'prompt');
      expect(res1, isNull);
      expect(networkCalls, 0);

      final emptyAuthClient = FirebaseAiGoogleClient(
        appCheckTokenProvider: () async => 'valid-app-check-token',
        authTokenProvider: () async => '',
        apiKeyOverride: 'test-api-key',
        projectIdOverride: 'test-project',
        httpTransport: (uri, headers, body) async {
          networkCalls++;
          return (statusCode: 200, body: '{}');
        },
      );

      final res2 = await emptyAuthClient.generateStructuredText(model: 'gemini-3.8-flash', systemInstruction: 'sys', prompt: 'prompt');
      expect(res2, isNull);
      expect(networkCalls, 0);
    });

    test('FirebaseAiGoogleClient attaches both X-Firebase-AppCheck and X-Firebase-Auth headers when both tokens are valid', () async {
      Map<String, String>? capturedHeaders;

      final validClient = FirebaseAiGoogleClient(
        appCheckTokenProvider: () async => 'app-check-jwt-token',
        authTokenProvider: () async => 'firebase-auth-id-token',
        apiKeyOverride: 'test-api-key',
        projectIdOverride: 'test-project',
        httpTransport: (uri, headers, body) async {
          capturedHeaders = headers;
          return (statusCode: 200, body: '{"candidates":[{"content":{"parts":[{"text":"{\\"alternatives\\":[]}"}]}}]}');
        },
      );

      final res = await validClient.generateStructuredText(model: 'gemini-3.8-flash', systemInstruction: 'sys', prompt: 'prompt');

      expect(res, '{"alternatives":[]}');
      expect(capturedHeaders, isNotNull);
      expect(capturedHeaders!['X-Firebase-AppCheck'], 'app-check-jwt-token');
      expect(capturedHeaders!['X-Firebase-Auth'], 'firebase-auth-id-token');
    });
  });
}
