// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/services/ai_coach_service.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/views/ai_coach_view.dart';

class MockExerciseRepository extends Mock implements ExerciseRepository {}

void main() {
  late MockExerciseRepository mockExerciseRepository;
  late FirebaseAiCoachService aiCoachService;
  late List<Exercise> sampleCatalog;

  setUp(() {
    mockExerciseRepository = MockExerciseRepository();
    aiCoachService = FirebaseAiCoachService(enablePlatformCues: false);

    sampleCatalog = const [
      Exercise(
        id: 'bench_press',
        name: 'Bench Press',
        primaryMuscleGroup: 'Chest',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: 'assets/animations/bench_press.riv',
        description: 'Barbell chest press.',
      ),
      Exercise(
        id: 'push_up',
        name: 'Push Up',
        primaryMuscleGroup: 'Chest',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: 'assets/animations/push_up.riv',
        description: 'Bodyweight chest press.',
      ),
      Exercise(
        id: 'pull_up',
        name: 'Pull Up',
        primaryMuscleGroup: 'Back',
        equipment: 'Bodyweight',
        animationType: 'movekit',
        animationPath: 'assets/animations/pull_up.movekit',
        description: 'Bodyweight vertical pull.',
      ),
      Exercise(
        id: 'remote_0001',
        name: 'Incline Archer Push Up',
        primaryMuscleGroup: 'Chest',
        equipment: 'Bodyweight',
        animationType: 'gif',
        animationPath: 'https://example.com/videos/remote_0001.gif',
        description: 'Bodyweight archer chest variation.',
      ),
    ];

    when(() => mockExerciseRepository.getExercises()).thenReturn(sampleCatalog);
    when(() => mockExerciseRepository.seedIfNeeded()).thenAnswer((_) async {});
  });

  testWidgets('AiCoachView renders Gemini 3.8 model badge, builds muscle workout plan, and toggles Live Voice mode', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [exerciseRepositoryProvider.overrideWithValue(mockExerciseRepository), aiCoachServiceProvider.overrideWithValue(aiCoachService)],
        child: MaterialApp(theme: AppTheme.darkTheme, home: const AiCoachView()),
      ),
    );

    await tester.pumpAndSettle();

    // Verify ATLAS model badge and 3D Gyro-Core Rive avatars are displayed
    expect(find.byKey(const Key('ai_coach_header_avatar')), findsOneWidget);
    expect(find.byKey(const Key('ai_coach_message_avatar_welcome-coach-msg')), findsOneWidget);
    expect(find.byKey(const Key('ai_coach_model_badge')), findsOneWidget);
    expect(find.text('ATLAS • Biomechanical AI Coach'), findsOneWidget);
    expect(find.text('ATLAS • AI COACH'), findsOneWidget);

    // Tap "Build Chest & Back Plan (All)" button
    final generateBtn = find.byKey(const Key('generate_ai_workout_button'));
    expect(generateBtn, findsOneWidget);
    await tester.ensureVisible(generateBtn);
    await tester.pumpAndSettle();
    await tester.tap(generateBtn);
    await tester.pumpAndSettle();

    // Verify recommended exercises from catalog appear
    expect(find.text('Push Up'), findsWidgets);
    expect(find.text('Pull Up'), findsWidgets);

    // Toggle Gemini 3.8 Live Voice Coach mode
    final liveToggle = find.byKey(const Key('ai_live_coach_toggle'));
    await tester.tap(liveToggle);
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('ai_live_voice_banner')), findsOneWidget);

    // Tap the bottom-right microphone button when input is empty -> starts mic recording
    final sendOrMicBtn = find.byKey(const Key('ai_coach_send_button'));
    expect(sendOrMicBtn, findsOneWidget);
    await tester.tap(sendOrMicBtn);
    await tester.pumpAndSettle();

    expect(find.text('LISTENING TO YOUR MIC — SPEAK TO ATLAS'), findsOneWidget);

    // Tap again to stop recording and send voice turn
    await tester.tap(sendOrMicBtn);
    await tester.pumpAndSettle();

    expect(find.text('LISTENING TO YOUR MIC — SPEAK TO ATLAS'), findsNothing);
  });

  testWidgets('AiExerciseAlternativeSheet loads home no-weights alternatives for target exercise', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [exerciseRepositoryProvider.overrideWithValue(mockExerciseRepository), aiCoachServiceProvider.overrideWithValue(aiCoachService)],
        child: MaterialApp(
          theme: AppTheme.darkTheme,
          home: Scaffold(body: AiExerciseAlternativeSheet(exercise: sampleCatalog.first)),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.byKey(const Key('ai_alternatives_sheet_avatar')), findsOneWidget);
    expect(find.text('AI Alternatives for Bench Press'), findsOneWidget);
    expect(find.text('Push Up'), findsWidgets);
    expect(find.byKey(const Key('ai_rec_asset_thumb_push_up')), findsOneWidget);
    expect(find.byKey(const Key('ai_rec_network_thumb_remote_0001')), findsOneWidget);
    expect(find.byKey(const Key('ai_rec_3d_badge_push_up')), findsOneWidget);
    expect(find.byKey(const Key('ai_rec_demo_badge_remote_0001')), findsOneWidget);
    expect(find.text('3D Form'), findsWidgets);
    expect(find.text('Demo'), findsWidgets);
  });

  testWidgets('AiCoachView omits duplicate language button in AppBar and reflects active Español locale', (tester) async {
    LocaleSettings.setLocale(AppLocale.es);
    addTearDown(() => LocaleSettings.setLocale(AppLocale.en));

    await tester.pumpWidget(
      TranslationProvider(
        child: ProviderScope(
          overrides: [exerciseRepositoryProvider.overrideWithValue(mockExerciseRepository), aiCoachServiceProvider.overrideWithValue(aiCoachService)],
          child: MaterialApp(theme: AppTheme.darkTheme, home: const AiCoachView()),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.byKey(const Key('ai_coach_language_button')), findsNothing);
    expect(find.text('ENTRENADOR PERSONAL IA'), findsOneWidget);
    expect(find.text('¿QUÉ MÚSCULOS QUIERES ENTRENAR HOY?'), findsOneWidget);
    expect(find.text('Pecho'), findsWidgets);
    expect(find.text('Espalda'), findsWidgets);
  });
}
