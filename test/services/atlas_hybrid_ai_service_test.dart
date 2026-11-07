// 🎯 Dart imports:
import 'dart:convert';

// 🐦 Flutter imports:
import 'package:flutter/services.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/pigeon/atlas_hybrid_ai_api.g.dart';
import 'package:comunityfitness/services/atlas_ai_config_service.dart';
import 'package:comunityfitness/services/atlas_hybrid_ai_service.dart';
import 'package:comunityfitness/services/web_hybrid_ai_bridge.dart';

class _TestHostApi extends AtlasHybridAiHostApi {
  PigeonOnDeviceModelStatus status = PigeonOnDeviceModelStatus.available;
  PigeonOnDeviceModelStatus downloadStatus = PigeonOnDeviceModelStatus.available;
  bool warmUpResult = true;
  bool shouldThrowOnStatus = false;
  bool shouldThrowOnGenerate = false;
  PigeonHybridAiResponse? configuredResponse;
  PigeonHybridAiRequest? lastRequest;

  @override
  Future<PigeonOnDeviceModelStatus> checkOnDeviceStatus() async {
    if (shouldThrowOnStatus) {
      throw PlatformException(code: 'AICORE_ERROR', message: 'AICore not installed');
    }
    return status;
  }

  @override
  Future<PigeonOnDeviceModelStatus> downloadOnDeviceModel() async {
    if (shouldThrowOnStatus) {
      throw PlatformException(code: 'DOWNLOAD_ERROR', message: 'AICore download failed');
    }
    status = downloadStatus;
    return status;
  }

  @override
  Future<bool> warmUpOnDeviceModel() async {
    if (shouldThrowOnStatus) {
      throw PlatformException(code: 'WARMUP_ERROR', message: 'AICore warmUp failed');
    }
    return warmUpResult;
  }

  @override
  Future<PigeonHybridAiResponse> generateHybridContent(PigeonHybridAiRequest request) async {
    lastRequest = request;
    if (shouldThrowOnGenerate) {
      throw PlatformException(
        code: 'HOST_UNAVAILABLE',
        message: 'Native AICore / Firebase AI host channel failed',
      );
    }
    if (configuredResponse != null) {
      return configuredResponse!;
    }
    final bool isOnDevice = request.mode == PigeonHybridInferenceMode.preferOnDevice ||
        request.mode == PigeonHybridInferenceMode.onlyOnDevice;
    return PigeonHybridAiResponse(
      text: 'Native hybrid output for: ${request.prompt}',
      inferenceSource: isOnDevice ? PigeonInferenceSource.onDevice : PigeonInferenceSource.inCloud,
      modelUsed: isOnDevice ? 'gemini-nano-on-device' : request.cloudModelName,
      latencyMs: 24,
      usedFallback: false,
    );
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const List<Exercise> sampleCatalog = <Exercise>[
    Exercise(
      id: 'barbell_bench_press',
      name: 'Barbell Bench Press',
      primaryMuscleGroup: 'chest',
      equipment: 'barbell',
      animationType: 'rive',
      animationPath: 'assets/animations/bench.riv',
      description: 'Compound horizontal press.',
    ),
    Exercise(
      id: 'barbell_back_squat',
      name: 'Barbell Back Squat',
      primaryMuscleGroup: 'quadriceps',
      equipment: 'barbell',
      animationType: 'rive',
      animationPath: 'assets/animations/squat.riv',
      description: 'Compound lower-body squat.',
    ),
  ];

  group('AtlasHybridAiService - Model Lifecycle (checkStatus, download, warmUp)', () {
    late _TestHostApi hostApi;
    late AppAtlasHybridAiService service;

    setUp(() {
      hostApi = _TestHostApi();
      service = AppAtlasHybridAiService(hostApi: hostApi);
    });

    test('maps all 4 on-device model statuses accurately', () async {
      hostApi.status = PigeonOnDeviceModelStatus.unavailable;
      expect(await service.checkOnDeviceStatus(), equals(OnDeviceModelStatus.unavailable));

      hostApi.status = PigeonOnDeviceModelStatus.downloadable;
      expect(await service.checkOnDeviceStatus(), equals(OnDeviceModelStatus.downloadable));

      hostApi.status = PigeonOnDeviceModelStatus.downloading;
      expect(await service.checkOnDeviceStatus(), equals(OnDeviceModelStatus.downloading));

      hostApi.status = PigeonOnDeviceModelStatus.available;
      expect(await service.checkOnDeviceStatus(), equals(OnDeviceModelStatus.available));
    });

    test('gracefully returns unavailable/false when host channel throws', () async {
      hostApi.shouldThrowOnStatus = true;
      expect(await service.checkOnDeviceStatus(), equals(OnDeviceModelStatus.unavailable));
      expect(await service.downloadOnDeviceModel(), equals(OnDeviceModelStatus.unavailable));
      expect(await service.warmUpOnDeviceModel(), isFalse);
    });

    test('downloads and warms up on-device model when AICore is supported', () async {
      hostApi.status = PigeonOnDeviceModelStatus.downloadable;
      hostApi.downloadStatus = PigeonOnDeviceModelStatus.available;
      hostApi.warmUpResult = true;

      final OnDeviceModelStatus downloaded = await service.downloadOnDeviceModel();
      final bool warmedUp = await service.warmUpOnDeviceModel();

      expect(downloaded, equals(OnDeviceModelStatus.available));
      expect(warmedUp, isTrue);
    });
  });

  group('AtlasHybridAiService - 4 Inference Modes & Telemetry', () {
    late _TestHostApi hostApi;

    setUp(() {
      hostApi = _TestHostApi();
    });

    test('PREFER_ON_DEVICE executes on-device when Gemini Nano is available', () async {
      final AppAtlasHybridAiService service = AppAtlasHybridAiService(hostApi: hostApi);

      final HybridAiResponse response = await service.generateHybridContent(
        const HybridAiRequest(
          prompt: 'Give 1 cue for Barbell Back Squat',
          mode: HybridInferenceMode.preferOnDevice,
        ),
      );

      expect(hostApi.lastRequest?.mode, equals(PigeonHybridInferenceMode.preferOnDevice));
      expect(response.inferenceSource, equals(HybridInferenceSource.onDevice));
      expect(response.modelUsed, equals('gemini-nano-on-device'));
      expect(response.usedFallback, isFalse);
    });

    test('PREFER_ON_DEVICE falls back to Dart cloud generator when host fails', () async {
      hostApi.shouldThrowOnGenerate = true;
      final AppAtlasHybridAiService service = AppAtlasHybridAiService(
        hostApi: hostApi,
        cloudGenerator: (HybridAiRequest req) async => 'Cloud Gemini fallback cue for: ${req.prompt}',
      );

      final HybridAiResponse response = await service.generateHybridContent(
        const HybridAiRequest(
          prompt: 'Cue for deadlift lockout',
          mode: HybridInferenceMode.preferOnDevice,
          cloudModelName: 'gemini-3.8-flash',
        ),
      );

      expect(response.inferenceSource, equals(HybridInferenceSource.inCloud));
      expect(response.modelUsed, equals('gemini-3.8-flash'));
      expect(response.usedFallback, isTrue);
      expect(response.text, contains('Cloud Gemini fallback cue'));
    });

    test('PREFER_ON_DEVICE falls back to localOfflineFallback when both NPU and Cloud fail', () async {
      hostApi.shouldThrowOnGenerate = true;
      final AppAtlasHybridAiService service = AppAtlasHybridAiService(
        hostApi: hostApi,
        cloudGenerator: (HybridAiRequest _) async => throw Exception('Airplane mode / No network'),
      );

      final HybridAiResponse response = await service.generateHybridContent(
        const HybridAiRequest(
          prompt: 'Barbell Bench Press 100kg x 8 @ RPE 9.5',
          mode: HybridInferenceMode.preferOnDevice,
        ),
      );

      expect(response.inferenceSource, equals(HybridInferenceSource.localOfflineFallback));
      expect(response.modelUsed, equals('atlas-biomechanical-offline-engine'));
      expect(response.usedFallback, isTrue);
      expect(response.text, contains('RPE 9.5'));
    });

    test('ONLY_ON_DEVICE throws StateError when on-device Gemini Nano is unavailable', () async {
      hostApi.shouldThrowOnGenerate = true;
      final AppAtlasHybridAiService service = AppAtlasHybridAiService(
        hostApi: hostApi,
        cloudGenerator: (HybridAiRequest _) async => 'Should not be called',
      );

      await expectLater(
        () => service.generateHybridContent(
          const HybridAiRequest(
            prompt: 'Private local health note',
            mode: HybridInferenceMode.onlyOnDevice,
          ),
        ),
        throwsA(isA<StateError>()),
      );
    });

    test('PREFER_IN_CLOUD routes to Cloud Gemini and falls back to on-device/offline when offline', () async {
      hostApi.configuredResponse = PigeonHybridAiResponse(
        text: 'On-device fallback because cloud was offline',
        inferenceSource: PigeonInferenceSource.onDevice,
        modelUsed: 'gemini-nano-on-device',
        latencyMs: 31,
        usedFallback: true,
        fallbackReason: 'Cloud unreachable; executed on Gemini Nano',
      );
      final AppAtlasHybridAiService service = AppAtlasHybridAiService(hostApi: hostApi);

      final HybridAiResponse response = await service.generateHybridContent(
        const HybridAiRequest(
          prompt: 'Periodization block summary',
          mode: HybridInferenceMode.preferInCloud,
        ),
      );

      expect(hostApi.lastRequest?.mode, equals(PigeonHybridInferenceMode.preferInCloud));
      expect(response.inferenceSource, equals(HybridInferenceSource.onDevice));
      expect(response.usedFallback, isTrue);
    });

    test('ONLY_IN_CLOUD throws StateError when both host cloud and Dart cloud fail', () async {
      hostApi.shouldThrowOnGenerate = true;
      final AppAtlasHybridAiService service = AppAtlasHybridAiService(
        hostApi: hostApi,
        cloudGenerator: (HybridAiRequest _) async => throw Exception('Offline'),
      );

      await expectLater(
        () => service.generateHybridContent(
          const HybridAiRequest(
            prompt: 'Generate 12-week macrocycle',
            mode: HybridInferenceMode.onlyInCloud,
          ),
        ),
        throwsA(isA<StateError>()),
      );
    });

    test('forwards single-image multimodal bytes and MIME type to host API', () async {
      final AppAtlasHybridAiService service = AppAtlasHybridAiService(hostApi: hostApi);
      final Uint8List fakeJpegBytes = Uint8List.fromList(<int>[0xFF, 0xD8, 0xFF, 0xE0, 1, 2, 3, 4]);

      final HybridAiResponse response = await service.generateHybridContent(
        HybridAiRequest(
          prompt: 'Identify this gym machine and suggest 3 sets',
          mode: HybridInferenceMode.preferOnDevice,
          imageBytes: fakeJpegBytes,
          imageMimeType: 'image/jpeg',
        ),
      );

      expect(hostApi.lastRequest?.imageBytes, equals(fakeJpegBytes));
      expect(hostApi.lastRequest?.imageMimeType, equals('image/jpeg'));
      expect(response.inferenceSource, equals(HybridInferenceSource.onDevice));
    });
  });

  group('AtlasHybridAiService - analyzeSetOfflineFirst Structured JSON & Offline Parser', () {
    late _TestHostApi hostApi;

    setUp(() {
      hostApi = _TestHostApi();
    });

    test('parses structured JSON returned by on-device Gemini Nano', () async {
      hostApi.configuredResponse = PigeonHybridAiResponse(
        text: jsonEncode(<String, dynamic>{
          'exerciseName': 'Barbell Bench Press',
          'matchedExerciseId': 'barbell_bench_press',
          'weightKg': 105.0,
          'reps': 6,
          'rpe': 9.0,
          'fatigueAlert': true,
          'nextSetRecommendation': 'Maintain 105.0kg and rest 180s.',
        }),
        inferenceSource: PigeonInferenceSource.onDevice,
        modelUsed: 'gemini-nano-on-device',
        latencyMs: 19,
        usedFallback: false,
      );

      final AppAtlasHybridAiService service = AppAtlasHybridAiService(hostApi: hostApi);
      final HybridSetLogAnalysis analysis = await service.analyzeSetOfflineFirst(
        rawSetText: 'Bench press 105kg x 6 @ RPE 9',
        catalog: sampleCatalog,
      );

      expect(analysis.exerciseName, equals('Barbell Bench Press'));
      expect(analysis.matchedExerciseId, equals('barbell_bench_press'));
      expect(analysis.weightKg, equals(105.0));
      expect(analysis.reps, equals(6));
      expect(analysis.rpe, equals(9.0));
      expect(analysis.fatigueAlert, isTrue);
      expect(analysis.inferenceSource, equals(HybridInferenceSource.onDevice));
      expect(analysis.modelUsed, equals('gemini-nano-on-device'));
      expect(analysis.usedFallback, isFalse);
    });

    test('falls back to deterministic biomechanical parser when completely offline without NPU', () async {
      hostApi.shouldThrowOnGenerate = true;
      final AppAtlasHybridAiService service = AppAtlasHybridAiService(
        hostApi: hostApi,
        cloudGenerator: (HybridAiRequest _) async => throw Exception('Basement gym - zero signal'),
      );

      final HybridSetLogAnalysis analysis = await service.analyzeSetOfflineFirst(
        rawSetText: 'Barbell Back Squat 140kg x 5 @ RPE 9.5',
        catalog: sampleCatalog,
      );

      expect(analysis.exerciseName, equals('Barbell Back Squat'));
      expect(analysis.matchedExerciseId, equals('barbell_back_squat'));
      expect(analysis.weightKg, equals(140.0));
      expect(analysis.reps, equals(5));
      expect(analysis.rpe, equals(9.5));
      expect(analysis.fatigueAlert, isTrue);
      expect(analysis.nextSetRecommendation, contains('133.0kg'));
      expect(analysis.inferenceSource, equals(HybridInferenceSource.localOfflineFallback));
      expect(analysis.usedFallback, isTrue);
    });

    test('converts lbs to kg and prescribes progressive overload on low RPE', () {
      final HybridSetLogAnalysis analysis = AppAtlasHybridAiService.parseSetDeterministically(
        rawSetText: 'Barbell Bench Press 225 lbs x 8 @ RPE 7',
        catalog: sampleCatalog,
      );

      expect(analysis.matchedExerciseId, equals('barbell_bench_press'));
      expect(analysis.weightKg, closeTo(102.1, 0.1));
      expect(analysis.reps, equals(8));
      expect(analysis.rpe, equals(7.0));
      expect(analysis.fatigueAlert, isFalse);
      expect(analysis.nextSetRecommendation, contains('progressive overload'));
    });

    test('localizes deterministic biomechanical recommendations when locale is es', () {
      LocaleSettings.setLocale(AppLocale.es);
      addTearDown(() => LocaleSettings.setLocale(AppLocale.en));

      final HybridSetLogAnalysis analysis = AppAtlasHybridAiService.parseSetDeterministically(
        rawSetText: 'Barbell Back Squat 140kg x 5 @ RPE 9.5',
        catalog: sampleCatalog,
      );

      expect(analysis.fatigueAlert, isTrue);
      expect(analysis.nextSetRecommendation, contains('Alta fatiga del SNC detectada'));
      expect(analysis.nextSetRecommendation, contains('133.0kg'));
    });
  });

  group('FakeAtlasHybridAiService & Riverpod Provider Override', () {
    test('overrides atlasHybridAiServiceProvider cleanly for widget/unit tests', () async {
      final FakeAtlasHybridAiService fake = FakeAtlasHybridAiService(
        status: OnDeviceModelStatus.available,
        simulatedLatencyMs: 12,
      );
      final ProviderContainer container = ProviderContainer(
        overrides: [atlasHybridAiServiceProvider.overrideWithValue(fake)],
      );
      addTearDown(container.dispose);

      final AtlasHybridAiService service = container.read(atlasHybridAiServiceProvider);
      expect(await service.checkOnDeviceStatus(), equals(OnDeviceModelStatus.available));

      final HybridAiResponse res = await service.generateHybridContent(
        const HybridAiRequest(prompt: 'Test prompt'),
      );
      expect(res.inferenceSource, equals(HybridInferenceSource.onDevice));
      expect(fake.recordedRequests, hasLength(1));
    });

    test('PigeonHybridAiRequest and PigeonHybridAiResponse encode/decode round-trip', () {
      final Uint8List bytes = Uint8List.fromList(<int>[10, 20, 30]);
      final PigeonHybridAiRequest req = PigeonHybridAiRequest(
        prompt: 'Analyze form',
        systemInstruction: 'Be concise',
        mode: PigeonHybridInferenceMode.preferInCloud,
        cloudModelName: 'gemini-3.8-flash',
        imageBytes: bytes,
        imageMimeType: 'image/png',
        responseJsonSchema: '{"type":"object"}',
        temperature: 0.2,
        maxOutputTokens: 128,
      );

      final PigeonHybridAiRequest decodedReq = PigeonHybridAiRequest.decode(req.encode());
      expect(decodedReq.prompt, equals('Analyze form'));
      expect(decodedReq.mode, equals(PigeonHybridInferenceMode.preferInCloud));
      expect(decodedReq.imageBytes, equals(bytes));
      expect(decodedReq.maxOutputTokens, equals(128));

      final PigeonHybridAiResponse resp = PigeonHybridAiResponse(
        text: '{"ok":true}',
        inferenceSource: PigeonInferenceSource.onDevice,
        modelUsed: 'gemini-nano-on-device',
        latencyMs: 15,
        usedFallback: false,
      );
      final PigeonHybridAiResponse decodedResp = PigeonHybridAiResponse.decode(resp.encode());
      expect(decodedResp.text, equals('{"ok":true}'));
      expect(decodedResp.inferenceSource, equals(PigeonInferenceSource.onDevice));
      expect(decodedResp.latencyMs, equals(15));
    });
  });

  group('AtlasHybridAiService - Web Chrome Prompt API & iOS Apple Intelligence Bridges', () {
    test('WebHybridAiBridge executes PREFER_ON_DEVICE via Chrome Prompt API and falls back to Cloud when unavailable', () async {
      final _TestHostApi hostApi = _TestHostApi();
      final FakeWebHybridAiBridge webBridge = FakeWebHybridAiBridge(
        isWebPlatform: true,
        status: OnDeviceModelStatus.available,
        customResponseText:
            '{"exerciseName":"Bench Press","weightKg":100.0,"reps":8,"rpe":8.0,'
            '"fatigueAlert":false,"nextSetRecommendation":"Keep 100kg"}',
      );
      final AppAtlasHybridAiService service = AppAtlasHybridAiService(
        hostApi: hostApi,
        webBridge: webBridge,
        cloudGenerator: (HybridAiRequest req) async => 'Cloud fallback via ${req.cloudModelName}',
      );

      expect(await service.checkOnDeviceStatus(), equals(OnDeviceModelStatus.available));
      expect(await service.warmUpOnDeviceModel(), isTrue);

      final HybridAiResponse onDeviceRes = await service.generateHybridContent(
        const HybridAiRequest(
          prompt: 'Bench 100kg x 8',
          mode: HybridInferenceMode.preferOnDevice,
        ),
      );
      expect(onDeviceRes.inferenceSource, equals(HybridInferenceSource.onDevice));
      expect(onDeviceRes.modelUsed, equals('chrome-prompt-api-gemini-nano'));
      expect(onDeviceRes.usedFallback, isFalse);
      expect(webBridge.generateCallCount, equals(1));

      webBridge.shouldThrowOnGenerate = true;
      final HybridAiResponse fallbackRes = await service.generateHybridContent(
        const HybridAiRequest(
          prompt: 'Bench 100kg x 8',
          mode: HybridInferenceMode.preferOnDevice,
        ),
      );
      expect(fallbackRes.inferenceSource, equals(HybridInferenceSource.inCloud));
      expect(fallbackRes.modelUsed, equals('gemini-3.8-flash'));
      expect(fallbackRes.usedFallback, isTrue);
    });

    test('propagates iOS Apple Intelligence FoundationModels telemetry when returned by host bridge', () async {
      final _TestHostApi hostApi = _TestHostApi()
        ..configuredResponse = PigeonHybridAiResponse(
          text: 'Keep torso braced and rest 120s.',
          inferenceSource: PigeonInferenceSource.onDevice,
          modelUsed: 'apple-foundation-models-system-language-model',
          latencyMs: 21,
          usedFallback: false,
        );
      final AppAtlasHybridAiService service = AppAtlasHybridAiService(hostApi: hostApi);

      final HybridAiResponse res = await service.generateHybridContent(
        const HybridAiRequest(
          prompt: 'Analyze squat depth and bracing',
          mode: HybridInferenceMode.preferOnDevice,
        ),
      );
      expect(res.inferenceSource, equals(HybridInferenceSource.onDevice));
      expect(res.modelUsed, equals('apple-foundation-models-system-language-model'));
      expect(res.latencyMs, equals(21));
      expect(res.usedFallback, isFalse);
    });
  });

  group('AtlasHybridAiService - Remote Config OTA & Server Prompt Templates (templateGenerativeModel)', () {
    test('applies OTA hybridSetPromptTemplate and coachSystemPrompt from AtlasAiConfigService to on-device NPU requests', () async {
      final _TestHostApi hostApi = _TestHostApi();
      final FakeAtlasAiConfigService configService = FakeAtlasAiConfigService(
        initialConfig: const AtlasAiRemoteConfig(
          coachSystemPrompt: 'OTA-COACH-DIRECTIVE-V2',
          hybridSetPromptTemplate: 'OTA_SET_TEMPLATE: {{rawSetText}} | catalog={{catalogContext}}',
          configSource: 'ota_remote_config',
        ),
      );
      final AppAtlasHybridAiService service = AppAtlasHybridAiService(
        hostApi: hostApi,
        configService: configService,
      );

      await service.analyzeSetOfflineFirst(
        rawSetText: 'Barbell Bench Press 100kg x 8 @ RPE 8',
        catalog: sampleCatalog,
      );

      expect(hostApi.lastRequest, isNotNull);
      expect(hostApi.lastRequest!.prompt, contains('OTA_SET_TEMPLATE: Barbell Bench Press 100kg x 8 @ RPE 8'));
      expect(hostApi.lastRequest!.systemInstruction, contains('OTA-COACH-DIRECTIVE-V2'));
    });

    test('executes Dotprompt Server Prompt Template via ServerTemplateExecutor and falls back to Cloud when template throws', () async {
      final _TestHostApi hostApi = _TestHostApi()..shouldThrowOnGenerate = true;
      final FakeAtlasAiConfigService configService = FakeAtlasAiConfigService();
      String? recordedTemplateId;
      Map<String, Object?>? recordedInputs;
      bool shouldFailTemplate = false;

      final AppAtlasHybridAiService service = AppAtlasHybridAiService(
        hostApi: hostApi,
        configService: configService,
        serverTemplateExecutor: (String templateId, Map<String, Object?> inputs) async {
          recordedTemplateId = templateId;
          recordedInputs = inputs;
          if (shouldFailTemplate) {
            throw StateError('Template not provisioned in Firebase Console');
          }
          return jsonEncode(<String, dynamic>{
            'exerciseName': 'Barbell Back Squat',
            'matchedExerciseId': 'barbell_back_squat',
            'weightKg': 140.0,
            'reps': 5,
            'rpe': 9.5,
            'fatigueAlert': true,
            'nextSetRecommendation': 'Server template prescription: drop to 133kg and rest 180s.',
          });
        },
        cloudGenerator: (HybridAiRequest _) async => jsonEncode(<String, dynamic>{
          'exerciseName': 'Barbell Back Squat',
          'matchedExerciseId': 'barbell_back_squat',
          'weightKg': 140.0,
          'reps': 5,
          'rpe': 9.5,
          'fatigueAlert': true,
          'nextSetRecommendation': 'Standard cloud fallback prescription.',
        }),
      );

      final HybridSetLogAnalysis templateAnalysis = await service.analyzeSetOfflineFirst(
        rawSetText: 'Barbell Back Squat 140kg x 5 @ RPE 9.5',
        catalog: sampleCatalog,
        mode: HybridInferenceMode.preferInCloud,
      );

      expect(recordedTemplateId, equals('atlas-set-autoregulation-v1-0-0'));
      expect(recordedInputs?['rawSetText'], equals('Barbell Back Squat 140kg x 5 @ RPE 9.5'));
      expect(templateAnalysis.inferenceSource, equals(HybridInferenceSource.inCloud));
      expect(templateAnalysis.modelUsed, equals('gemini-3.8-flash · template:atlas-set-autoregulation-v1-0-0'));
      expect(templateAnalysis.nextSetRecommendation, contains('Server template prescription'));

      shouldFailTemplate = true;
      final HybridSetLogAnalysis fallbackAnalysis = await service.analyzeSetOfflineFirst(
        rawSetText: 'Barbell Back Squat 140kg x 5 @ RPE 9.5',
        catalog: sampleCatalog,
        mode: HybridInferenceMode.preferInCloud,
      );

      expect(fallbackAnalysis.inferenceSource, equals(HybridInferenceSource.inCloud));
      expect(fallbackAnalysis.modelUsed, equals('gemini-3.8-flash'));
      expect(fallbackAnalysis.nextSetRecommendation, contains('Standard cloud fallback prescription'));
    });
  });
}
