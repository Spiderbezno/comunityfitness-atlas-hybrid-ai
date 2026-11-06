// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce/hive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/models/workout_step.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/repositories/session_repository.dart';
import 'package:comunityfitness/services/sync_service.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/views/muscle_analytics_screen.dart';

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
    final tempDir = '/tmp/hive_view_ana_${DateTime.now().millisecondsSinceEpoch}';
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

    sessionBox = await Hive.openBox<WorkoutSession>('test_sessions_view_ana');
    exerciseBox = await Hive.openBox<Exercise>('test_exercises_view_ana');

    sessionRepo = SessionRepository(sessionBox: sessionBox, syncService: FakeSyncService());
    exerciseRepo = ExerciseRepository(exerciseBox: exerciseBox);
  });

  tearDownAll(() async {
    await sessionBox.close();
    await exerciseBox.close();
  });

  tearDown(() async {
    LocaleSettings.setLocale(AppLocale.en);
    await sessionBox.clear();
    await exerciseBox.clear();
  });

  testWidgets('MuscleAnalyticsScreen renders muscle readiness and PR curves', (tester) async {
    LocaleSettings.setLocale(AppLocale.en);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [sessionRepositoryProvider.overrideWithValue(sessionRepo), exerciseRepositoryProvider.overrideWithValue(exerciseRepo)],
        child: TranslationProvider(
          child: MaterialApp(theme: AppTheme.darkTheme, home: const MuscleAnalyticsScreen()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Muscle Balance & Recovery'), findsOneWidget);
    expect(find.text('Muscle Recovery'), findsOneWidget);
    expect(find.text('Estimated 1RM Records'), findsOneWidget);
    expect(find.text('Chest'), findsWidgets);
    expect(find.text('Back'), findsWidgets);
  });

  testWidgets('InteractiveBodyMap toggles Anterior/Posterior and displays MEV/MAV/MRV telemetry', (tester) async {
    await tester.runAsync(() async {
      await exerciseRepo.saveExercise(
        const Exercise(
          id: 'barbell_squat',
          name: 'Barbell Squat',
          description: 'Compound leg movement for quads and glutes.',
          primaryMuscleGroup: 'Legs',
          equipment: 'Barbell',
          animationPath: 'assets/animations/barbell_squat.riv',
          animationType: 'rive',
        ),
      );

      await sessionRepo.saveSession(
        WorkoutSession(
          id: 'sess_quads',
          userId: 'u1',
          routineId: 'r1',
          routineTitle: 'Leg Day',
          startedAt: DateTime.now().subtract(const Duration(hours: 24)),
          completedAt: DateTime.now().subtract(const Duration(hours: 23)),
          updatedAt: DateTime.now().subtract(const Duration(hours: 23)),
          steps: [
            const WorkoutStep(
              exerciseId: 'barbell_squat',
              sets: 12,
              reps: 10,
              weight: 100.0,
              targetDurationSeconds: 0,
              restDurationSeconds: 90,
              orderIndex: 0,
            ),
          ],
        ),
      );
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [sessionRepositoryProvider.overrideWithValue(sessionRepo), exerciseRepositoryProvider.overrideWithValue(exerciseRepo)],
        child: MaterialApp(theme: AppTheme.darkTheme, home: const MuscleAnalyticsScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('body_map_anterior_tab')), findsOneWidget);
    expect(find.byKey(const Key('body_map_posterior_tab')), findsOneWidget);
    expect(find.byKey(const Key('selected_muscle_telemetry_card')), findsOneWidget);
    expect(find.byKey(const Key('train_selected_muscle_button')), findsOneWidget);

    // Default selected muscle is Chest (0 sets -> Under MEV)
    expect(find.text('Explore Chest Exercises'), findsOneWidget);
    expect(find.textContaining('Under MEV'), findsWidgets);

    // Tap Quads node on Anterior view (12 sets -> Optimal MAV for Quads: MEV 8, MAV 12-18, MRV 20)
    await tester.tap(find.byKey(const Key('body_map_muscle_Quads')));
    await tester.pumpAndSettle();

    expect(find.text('Explore Quads Exercises'), findsOneWidget);
    expect(find.textContaining('Optimal MAV'), findsWidgets);
    expect(find.textContaining('MEV 8'), findsWidgets);
    expect(find.textContaining('MAV 12-18'), findsWidgets);
    expect(find.textContaining('MRV 20'), findsWidgets);

    // Switch to Posterior view and select Back (Back: MEV 10, MAV 14-20, MRV 25)
    await tester.tap(find.byKey(const Key('body_map_posterior_tab')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('body_map_muscle_Back')), findsOneWidget);
    expect(find.byKey(const Key('body_map_muscle_Glutes')), findsOneWidget);
    expect(find.byKey(const Key('body_map_muscle_Hamstrings')), findsOneWidget);
    expect(find.byKey(const Key('body_map_muscle_Triceps')), findsOneWidget);

    await tester.tap(find.byKey(const Key('body_map_muscle_Back')));
    await tester.pumpAndSettle();

    expect(find.text('Explore Back Exercises'), findsOneWidget);
    expect(find.textContaining('MEV 10'), findsWidgets);
    expect(find.textContaining('MAV 14-20'), findsWidgets);
    expect(find.textContaining('MRV 25'), findsWidgets);
  });

  testWidgets('InteractiveBodyMap localizes Front/Back tabs in EN and ES without RenderFlex overflow on narrow 320x640 screen', (tester) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    LocaleSettings.setLocale(AppLocale.en);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [sessionRepositoryProvider.overrideWithValue(sessionRepo), exerciseRepositoryProvider.overrideWithValue(exerciseRepo)],
        child: TranslationProvider(
          child: MaterialApp(theme: AppTheme.darkTheme, home: const MuscleAnalyticsScreen()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.descendant(of: find.byKey(const Key('body_map_anterior_tab')), matching: find.text('Front')), findsOneWidget);
    expect(find.descendant(of: find.byKey(const Key('body_map_posterior_tab')), matching: find.text('Back')), findsOneWidget);

    LocaleSettings.setLocale(AppLocale.es);
    await tester.pumpAndSettle();

    expect(find.text('Mapa Anatómico de Volumen 3D'), findsOneWidget);
    expect(find.descendant(of: find.byKey(const Key('body_map_anterior_tab')), matching: find.text('Frontal')), findsOneWidget);
    expect(find.descendant(of: find.byKey(const Key('body_map_posterior_tab')), matching: find.text('Posterior')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
