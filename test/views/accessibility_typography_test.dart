// 🎯 Dart imports:
import 'dart:io';
import 'dart:math' as math;

// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce/hive.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/models/workout_step.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/repositories/routine_repository.dart';
import 'package:comunityfitness/repositories/session_repository.dart';
import 'package:comunityfitness/services/atlas_hybrid_ai_service.dart';
import 'package:comunityfitness/services/sync_service.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/views/dashboard_screen.dart';
import 'package:comunityfitness/views/exercise_catalog_screen.dart';
import 'package:comunityfitness/views/muscle_analytics_screen.dart';
import 'package:comunityfitness/views/widgets/atlas_hybrid_ai_panel.dart';

class _FakeSyncService extends Fake implements SyncService {
  @override
  Future<void> syncAll() async {}
}

class _MockExerciseRepository extends Mock implements ExerciseRepository {}

double _relativeLuminance(Color color) {
  double linearize(double channel) {
    if (channel <= 0.03928) {
      return channel / 12.92;
    }
    return math.pow((channel + 0.055) / 1.055, 2.4).toDouble();
  }

  return 0.2126 * linearize(color.r) + 0.7152 * linearize(color.g) + 0.0722 * linearize(color.b);
}

double _contrastRatio(Color foreground, Color background) {
  final double l1 = _relativeLuminance(foreground);
  final double l2 = _relativeLuminance(background);
  final double lighter = math.max(l1, l2);
  final double darker = math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

Widget _scaledMediaQuery({required double textScale, required Widget child}) {
  return Builder(
    builder: (BuildContext context) {
      return MediaQuery(
        data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(textScale)),
        child: child,
      );
    },
  );
}

void _verifyNoOverflowExceptions(WidgetTester tester, List<String> captured) {
  if (captured.isNotEmpty) {
    // Consume pending binding exception after surfacing full RenderFlex context.
    tester.takeException();
    fail(captured.join('\n---\n'));
  }
  expect(tester.takeException(), isNull);
}

List<String> _captureFlutterErrors(void Function(FlutterErrorDetails details)? originalOnError, List<String> captured) {
  FlutterError.onError = (FlutterErrorDetails details) {
    captured.add('${details.exceptionAsString()}\n${details.context ?? ''}\n${details.informationCollector?.call().take(4).join('\n') ?? ''}');
    originalOnError?.call(details);
  };
  return captured;
}

void main() {
  late Directory tempDir;
  late Box<Routine> routineBox;
  late Box<WorkoutSession> sessionBox;
  late Box<Exercise> exerciseBox;
  late RoutineRepository routineRepo;
  late SessionRepository sessionRepo;
  late ExerciseRepository exerciseRepo;

  setUpAll(() async {
    tempDir = await Directory.systemTemp.createTemp('hive_a11y_test_');
    Hive.init(tempDir.path);
    if (!Hive.isAdapterRegistered(1)) {
      Hive.registerAdapter(ExerciseAdapter());
    }
    if (!Hive.isAdapterRegistered(2)) {
      Hive.registerAdapter(RoutineAdapter());
    }
    if (!Hive.isAdapterRegistered(3)) {
      Hive.registerAdapter(WorkoutStepAdapter());
    }
    if (!Hive.isAdapterRegistered(4)) {
      Hive.registerAdapter(WorkoutSessionAdapter());
    }

    routineBox = await Hive.openBox<Routine>('a11y_routines');
    sessionBox = await Hive.openBox<WorkoutSession>('a11y_sessions');
    exerciseBox = await Hive.openBox<Exercise>('a11y_exercises');

    routineRepo = RoutineRepository(routineBox: routineBox, syncService: _FakeSyncService());
    sessionRepo = SessionRepository(sessionBox: sessionBox, syncService: _FakeSyncService());
    exerciseRepo = ExerciseRepository(exerciseBox: exerciseBox);
  });

  tearDownAll(() async {
    await routineBox.close();
    await sessionBox.close();
    await exerciseBox.close();
    if (tempDir.existsSync()) {
      await tempDir.delete(recursive: true);
    }
  });

  tearDown(() async {
    LocaleSettings.setLocale(AppLocale.en);
    await routineBox.clear();
    await sessionBox.clear();
    await exerciseBox.clear();
  });

  group('Accessibility Typography & WCAG AA Contrast Tokens', () {
    test('font scale is monotonically increasing and meets accessible legibility floor', () {
      expect(AppDimensions.fontBadge, greaterThanOrEqualTo(10.0));
      expect(AppDimensions.fontXXS, greaterThanOrEqualTo(12.0));
      expect(AppDimensions.fontXXS, lessThanOrEqualTo(AppDimensions.fontXS));
      expect(AppDimensions.fontXS, lessThan(AppDimensions.fontS));
      expect(AppDimensions.fontS, greaterThanOrEqualTo(14.0));
      expect(AppDimensions.fontS, lessThan(AppDimensions.fontM));
      expect(AppDimensions.fontM, lessThan(AppDimensions.fontL));
      expect(AppDimensions.fontL, lessThan(AppDimensions.fontXL));
      expect(AppDimensions.fontXL, lessThan(AppDimensions.fontXXL));
    });

    test('text colors achieve WCAG AA contrast (>= 4.5:1) across all dark surfaces', () {
      final List<Color> surfaces = <Color>[AppColors.background, AppColors.surface, AppColors.surfaceElevated];
      final List<Color> textColors = <Color>[AppColors.textPrimary, AppColors.textSecondary, AppColors.textMuted];

      for (final Color fg in textColors) {
        for (final Color bg in surfaces) {
          expect(_contrastRatio(fg, bg), greaterThanOrEqualTo(4.5));
        }
      }
    });
  });

  group('Narrow Viewport & 1.5x TextScale Overflow Regression Suite', () {
    for (final double scale in <double>[1.0, 1.5]) {
      testWidgets('DashboardScreen renders cleanly without overflow at ${scale}x (ES & EN)', (WidgetTester tester) async {
        tester.view.physicalSize = const Size(360, 740);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final List<String> captured = <String>[];
        final void Function(FlutterErrorDetails)? prevOnError = FlutterError.onError;
        _captureFlutterErrors(prevOnError, captured);
        addTearDown(() => FlutterError.onError = prevOnError);

        LocaleSettings.setLocale(AppLocale.es);
        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              routineRepositoryProvider.overrideWithValue(routineRepo),
              sessionRepositoryProvider.overrideWithValue(sessionRepo),
              exerciseRepositoryProvider.overrideWithValue(exerciseRepo),
            ],
            child: TranslationProvider(
              child: MaterialApp(
                theme: AppTheme.darkTheme,
                home: _scaledMediaQuery(textScale: scale, child: const DashboardScreen()),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        _verifyNoOverflowExceptions(tester, captured);

        LocaleSettings.setLocale(AppLocale.en);
        await tester.pumpAndSettle();
        _verifyNoOverflowExceptions(tester, captured);
      });

      testWidgets('MuscleAnalyticsScreen & InteractiveBodyMap render cleanly at ${scale}x (Front & Back)', (WidgetTester tester) async {
        tester.view.physicalSize = const Size(360, 740);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        LocaleSettings.setLocale(AppLocale.es);
        await tester.pumpWidget(
          ProviderScope(
            overrides: [sessionRepositoryProvider.overrideWithValue(sessionRepo), exerciseRepositoryProvider.overrideWithValue(exerciseRepo)],
            child: TranslationProvider(
              child: MaterialApp(
                theme: AppTheme.darkTheme,
                home: _scaledMediaQuery(textScale: scale, child: const MuscleAnalyticsScreen()),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);

        await tester.tap(find.byKey(const Key('body_map_posterior_tab')));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      });

      testWidgets('ExerciseCatalogScreen renders cleanly without overflow at ${scale}x', (WidgetTester tester) async {
        tester.view.physicalSize = const Size(360, 740);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final List<String> captured = <String>[];
        final void Function(FlutterErrorDetails)? prevOnError = FlutterError.onError;
        _captureFlutterErrors(prevOnError, captured);
        addTearDown(() => FlutterError.onError = prevOnError);

        final _MockExerciseRepository mockRepo = _MockExerciseRepository();
        when(() => mockRepo.seedIfNeeded()).thenAnswer((_) async {});
        when(() => mockRepo.getExercises()).thenReturn(const <Exercise>[
          Exercise(
            id: 'incline_dumbbell_press',
            name: 'Incline Alternating Dumbbell Chest Press with Pause',
            primaryMuscleGroup: 'Chest',
            equipment: 'Dumbbell',
            animationType: 'rive',
            animationPath: 'assets/animations/does_not_exist.riv',
            description: 'Compound chest exercise',
          ),
          Exercise(
            id: 'bulgarian_split_squat',
            name: 'Elevated Rear-Foot Bulgarian Split Squat',
            primaryMuscleGroup: 'Quadriceps',
            equipment: 'Barbell',
            animationType: 'static',
            animationPath: '',
            description: 'Single-leg quad builder',
          ),
        ]);

        await tester.pumpWidget(
          ProviderScope(
            overrides: [exerciseRepositoryProvider.overrideWithValue(mockRepo)],
            child: TranslationProvider(
              child: MaterialApp(
                theme: AppTheme.darkTheme,
                home: _scaledMediaQuery(textScale: scale, child: const ExerciseCatalogScreen()),
              ),
            ),
          ),
        );
        await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 100)));
        await tester.pumpAndSettle();

        expect(find.text('Incline Alternating Dumbbell Chest Press with Pause'), findsOneWidget);
        _verifyNoOverflowExceptions(tester, captured);
      });

      testWidgets('AtlasHybridAiPanel renders cleanly without overflow at ${scale}x', (WidgetTester tester) async {
        tester.view.physicalSize = const Size(360, 740);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final List<String> captured = <String>[];
        final void Function(FlutterErrorDetails)? prevOnError = FlutterError.onError;
        _captureFlutterErrors(prevOnError, captured);
        addTearDown(() => FlutterError.onError = prevOnError);

        final FakeAtlasHybridAiService fakeService = FakeAtlasHybridAiService(status: OnDeviceModelStatus.available);

        await tester.pumpWidget(
          ProviderScope(
            overrides: [atlasHybridAiServiceProvider.overrideWithValue(fakeService)],
            child: TranslationProvider(
              child: MaterialApp(
                theme: AppTheme.darkTheme,
                home: _scaledMediaQuery(
                  textScale: scale,
                  child: const Scaffold(body: SingleChildScrollView(child: AtlasHybridAiPanel())),
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.byKey(const Key('hybrid_telemetry_badge')), findsOneWidget);
        _verifyNoOverflowExceptions(tester, captured);
      });
    }
  });
}
