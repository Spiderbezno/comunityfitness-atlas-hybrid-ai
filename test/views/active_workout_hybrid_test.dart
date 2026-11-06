// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/services/atlas_hybrid_ai_service.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/viewmodels/active_workout_viewmodel.dart';
import 'package:comunityfitness/views/active_workout_screen.dart';

const Exercise _benchPressExercise = Exercise(
  id: 'ex-bench-press',
  name: 'Barbell Bench Press',
  primaryMuscleGroup: 'Chest',
  equipment: 'Barbell',
  animationType: 'rive',
  animationPath: 'assets/animations/bench_press.riv',
  description: 'Horizontal barbell press.',
);

Widget _buildActiveWorkoutHarness(FakeAtlasHybridAiService fakeService) {
  return ProviderScope(
    overrides: [
      atlasHybridAiServiceProvider.overrideWithValue(fakeService),
    ],
    child: TranslationProvider(
      child: MaterialApp(
        theme: AppTheme.darkTheme,
        home: const ActiveWorkoutScreen(),
      ),
    ),
  );
}

void main() {
  group('ActiveWorkoutScreen Hybrid AI Autoregulation Widget Tests', () {
    testWidgets(
      '1. Tapping active_step_hybrid_rpe_95_0 invokes AtlasHybridAiService, reduces weight by 5%, '
      'increases rest to 180s, and renders telemetry banner',
      (WidgetTester tester) async {
        final FakeAtlasHybridAiService fakeService = FakeAtlasHybridAiService(
          status: OnDeviceModelStatus.available,
          simulatedLatencyMs: 11,
        );

        await tester.pumpWidget(_buildActiveWorkoutHarness(fakeService));
        await tester.pump();

        final ProviderContainer container = ProviderScope.containerOf(
          tester.element(find.byType(ActiveWorkoutScreen)),
        );
        final ActiveWorkoutViewModel vm = container.read(activeWorkoutViewModelProvider.notifier);

        vm.addExercise(_benchPressExercise);
        vm.updateStepValues(0, weight: 100.0, reps: 8, restDurationSeconds: 90);
        await tester.pump();

        expect(find.byKey(const Key('active_step_hybrid_row_0')), findsOneWidget);
        expect(find.byKey(const Key('active_workout_hybrid_telemetry_banner')), findsNothing);

        final Finder rpe95Chip = find.byKey(const Key('active_step_hybrid_rpe_95_0'));
        expect(rpe95Chip, findsOneWidget);

        await tester.tap(rpe95Chip);
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));

        final ActiveWorkoutState updatedState = container.read(activeWorkoutViewModelProvider);
        expect(updatedState.steps.first.weight, equals(95.0));
        expect(updatedState.steps.first.restDurationSeconds, equals(180));
        expect(updatedState.steps.first.completedSets, equals(1));
        expect(updatedState.restTimerSecondsRemaining, equals(180));
        expect(updatedState.lastHybridAnalysis, isNotNull);
        expect(updatedState.lastHybridAnalysis!.inferenceSource, equals(HybridInferenceSource.onDevice));

        expect(find.byKey(const Key('active_workout_hybrid_telemetry_banner')), findsOneWidget);
        expect(find.textContaining('ON-DEVICE · Gemini Nano'), findsOneWidget);
        expect(find.textContaining('11ms'), findsWidgets);
        expect(find.textContaining('95.0 kg'), findsOneWidget);
      },
    );

    testWidgets(
      '2. Tapping active_step_hybrid_rpe_7_0 applies progressive overload (+2.5kg) and updates step autopilotBadge',
      (WidgetTester tester) async {
        final FakeAtlasHybridAiService fakeService = FakeAtlasHybridAiService(
          status: OnDeviceModelStatus.available,
          simulatedLatencyMs: 11,
        );

        await tester.pumpWidget(_buildActiveWorkoutHarness(fakeService));
        await tester.pump();

        final ProviderContainer container = ProviderScope.containerOf(
          tester.element(find.byType(ActiveWorkoutScreen)),
        );
        final ActiveWorkoutViewModel vm = container.read(activeWorkoutViewModelProvider.notifier);

        vm.addExercise(_benchPressExercise);
        vm.updateStepValues(0, weight: 80.0, reps: 10, restDurationSeconds: 90);
        await tester.pump();

        final Finder rpe7Chip = find.byKey(const Key('active_step_hybrid_rpe_7_0'));
        expect(rpe7Chip, findsOneWidget);

        await tester.tap(rpe7Chip);
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));

        final ActiveWorkoutState updatedState = container.read(activeWorkoutViewModelProvider);
        expect(updatedState.steps.first.weight, equals(82.5));
        expect(updatedState.steps.first.completedSets, equals(1));
        expect(updatedState.steps.first.autopilotBadge, isNotNull);
        expect(updatedState.steps.first.autopilotBadge, contains('ON-DEVICE'));
        expect(updatedState.steps.first.autopilotBadge, contains('11ms'));
        expect(updatedState.steps.first.autopilotBadge, contains('+2.5kg'));

        expect(find.byKey(const Key('autopilot_badge_0')), findsOneWidget);
        expect(find.textContaining('82.5 kg'), findsOneWidget);
      },
    );
  });
}
