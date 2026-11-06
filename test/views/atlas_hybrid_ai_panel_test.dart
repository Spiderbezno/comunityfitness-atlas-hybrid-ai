// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// 🌎 Project imports:
import 'package:comunityfitness/services/atlas_hybrid_ai_service.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/viewmodels/atlas_hybrid_ai_viewmodel.dart';
import 'package:comunityfitness/views/widgets/atlas_hybrid_ai_panel.dart';

Widget _buildTestHarness(FakeAtlasHybridAiService fakeService) {
  return ProviderScope(
    overrides: [
      atlasHybridAiServiceProvider.overrideWithValue(fakeService),
    ],
    child: MaterialApp(
      theme: AppTheme.darkTheme,
      home: const Scaffold(
        body: SingleChildScrollView(
          child: AtlasHybridAiPanel(),
        ),
      ),
    ),
  );
}

void main() {
  group('AtlasHybridAiPanel Widget Tests', () {
    testWidgets('1. Initial render shows telemetry badge and preferOnDevice selected', (WidgetTester tester) async {
      final FakeAtlasHybridAiService fakeService = FakeAtlasHybridAiService(
        status: OnDeviceModelStatus.available,
      );

      await tester.pumpWidget(_buildTestHarness(fakeService));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('hybrid_telemetry_badge')), findsOneWidget);
      expect(find.textContaining('On-Device Ready'), findsOneWidget);

      final ChoiceChip preferOnDeviceChip = tester.widget<ChoiceChip>(
        find.byKey(const Key('hybrid_mode_preferOnDevice')),
      );
      expect(preferOnDeviceChip.selected, isTrue);
    });

    testWidgets('2. Tapping the 4 HybridInferenceMode chips updates the active mode', (WidgetTester tester) async {
      final FakeAtlasHybridAiService fakeService = FakeAtlasHybridAiService(
        status: OnDeviceModelStatus.available,
      );

      await tester.pumpWidget(_buildTestHarness(fakeService));
      await tester.pumpAndSettle();

      final ProviderContainer container = ProviderScope.containerOf(
        tester.element(find.byType(AtlasHybridAiPanel)),
      );

      await tester.tap(find.byKey(const Key('hybrid_mode_onlyOnDevice')));
      await tester.pumpAndSettle();
      expect(
        container.read(atlasHybridAiViewModelProvider).selectedMode,
        equals(HybridInferenceMode.onlyOnDevice),
      );

      await tester.tap(find.byKey(const Key('hybrid_mode_preferInCloud')));
      await tester.pumpAndSettle();
      expect(
        container.read(atlasHybridAiViewModelProvider).selectedMode,
        equals(HybridInferenceMode.preferInCloud),
      );

      await tester.tap(find.byKey(const Key('hybrid_mode_onlyInCloud')));
      await tester.pumpAndSettle();
      expect(
        container.read(atlasHybridAiViewModelProvider).selectedMode,
        equals(HybridInferenceMode.onlyInCloud),
      );

      await tester.tap(find.byKey(const Key('hybrid_mode_preferOnDevice')));
      await tester.pumpAndSettle();
      expect(
        container.read(atlasHybridAiViewModelProvider).selectedMode,
        equals(HybridInferenceMode.preferOnDevice),
      );
    });

    testWidgets(
      '3. Entering a set log and tapping hybrid_analyze_set_button renders hybrid_analysis_result_card with ON-DEVICE telemetry',
      (WidgetTester tester) async {
        final FakeAtlasHybridAiService fakeService = FakeAtlasHybridAiService(
          status: OnDeviceModelStatus.available,
          simulatedLatencyMs: 14,
        );

        await tester.pumpWidget(_buildTestHarness(fakeService));
        await tester.pumpAndSettle();

        await tester.enterText(
          find.byKey(const Key('hybrid_set_input_field')),
          'Barbell Back Squat 140kg x 5 @ RPE 9.5',
        );
        await tester.ensureVisible(find.byKey(const Key('hybrid_analyze_set_button')));
        await tester.pumpAndSettle();
        await tester.tap(find.byKey(const Key('hybrid_analyze_set_button')));
        await tester.pumpAndSettle();

        expect(find.byKey(const Key('hybrid_analysis_result_card')), findsOneWidget);
        expect(find.text('Barbell Back Squat'), findsOneWidget);
        expect(find.text('140.0 kg'), findsOneWidget);
        expect(find.text('5'), findsOneWidget);
        expect(find.text('9.5'), findsOneWidget);
        expect(find.text('CNS Fatigue Alert'), findsOneWidget);
        expect(find.textContaining('ON-DEVICE'), findsWidgets);
      },
    );

    testWidgets(
      '4. Tapping hybrid_scan_image_button triggers multimodal request with imageBytes and renders hybrid_vision_result_card',
      (WidgetTester tester) async {
        final FakeAtlasHybridAiService fakeService = FakeAtlasHybridAiService(
          status: OnDeviceModelStatus.available,
          simulatedLatencyMs: 22,
        );

        await tester.pumpWidget(_buildTestHarness(fakeService));
        await tester.pumpAndSettle();

        await tester.ensureVisible(find.byKey(const Key('hybrid_scan_image_button')));
        await tester.pumpAndSettle();
        await tester.tap(find.byKey(const Key('hybrid_scan_image_button')));
        await tester.pumpAndSettle();

        expect(fakeService.recordedRequests, hasLength(1));
        expect(fakeService.recordedRequests.first.imageBytes, isNotNull);
        expect(fakeService.recordedRequests.first.imageBytes, isNotEmpty);
        expect(find.byKey(const Key('hybrid_vision_result_card')), findsOneWidget);
      },
    );

    testWidgets(
      '5. Selecting onlyOnDevice when FakeAtlasHybridAiService is unavailable displays hybrid_error_banner',
      (WidgetTester tester) async {
        final FakeAtlasHybridAiService fakeService = FakeAtlasHybridAiService(
          status: OnDeviceModelStatus.unavailable,
        );

        await tester.pumpWidget(_buildTestHarness(fakeService));
        await tester.pumpAndSettle();

        await tester.tap(find.byKey(const Key('hybrid_mode_onlyOnDevice')));
        await tester.pumpAndSettle();

        expect(find.byKey(const Key('hybrid_error_banner')), findsOneWidget);

        await tester.ensureVisible(find.byKey(const Key('hybrid_analyze_set_button')));
        await tester.pumpAndSettle();
        await tester.tap(find.byKey(const Key('hybrid_analyze_set_button')));
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('hybrid_error_banner')), findsOneWidget);
      },
    );

    testWidgets(
      '6. Tapping hybrid_download_model_button downloads and warms up on-device Gemini Nano',
      (WidgetTester tester) async {
        final FakeAtlasHybridAiService fakeService = FakeAtlasHybridAiService(
          status: OnDeviceModelStatus.downloadable,
          downloadResultStatus: OnDeviceModelStatus.available,
        );

        await tester.pumpWidget(_buildTestHarness(fakeService));
        await tester.pumpAndSettle();

        expect(find.byKey(const Key('hybrid_download_model_button')), findsOneWidget);

        await tester.tap(find.byKey(const Key('hybrid_download_model_button')));
        await tester.pumpAndSettle();

        expect(fakeService.downloadCallCount, equals(1));
        expect(find.textContaining('On-Device Ready'), findsOneWidget);
      },
    );

    testWidgets(
      '7. Tapping hybrid_server_template_toggle switches Dotprompt Server Prompt Templates on and off',
      (WidgetTester tester) async {
        final FakeAtlasHybridAiService fakeService = FakeAtlasHybridAiService(
          status: OnDeviceModelStatus.available,
        );

        await tester.pumpWidget(_buildTestHarness(fakeService));
        await tester.pumpAndSettle();

        final Finder templateToggle = find.byKey(const Key('hybrid_server_template_toggle'));
        expect(templateToggle, findsOneWidget);
        expect(find.textContaining('Dotprompt · atlas-set-autoregulation-v1-0-0'), findsOneWidget);

        await tester.tap(templateToggle);
        await tester.pumpAndSettle();

        expect(find.textContaining('Remote Config Only · atlas-set-autoregulation-v1-0-0'), findsOneWidget);

        await tester.tap(templateToggle);
        await tester.pumpAndSettle();

        expect(find.textContaining('Dotprompt · atlas-set-autoregulation-v1-0-0'), findsOneWidget);
      },
    );
  });
}
