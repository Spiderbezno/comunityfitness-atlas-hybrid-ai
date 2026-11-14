// ignore_for_file: prefer_initializing_formals

// 🎯 Dart imports:
import 'dart:async';
import 'dart:convert';

// 🐦 Flutter imports:
import 'package:flutter/foundation.dart';

// 📦 Package imports:
import 'package:firebase_ai/firebase_ai.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/ai_coach_models.dart';
import 'package:comunityfitness/pigeon/atlas_hybrid_ai_api.g.dart';
import 'package:comunityfitness/services/atlas_ai_config_service.dart';
import 'package:comunityfitness/services/coach_decisions_gateway.dart';
import 'package:comunityfitness/services/web_hybrid_ai_bridge.dart';

part 'atlas_hybrid_ai_service.g.dart';

/// Application-owned execution policy for ATLAS Hybrid AI requests.
enum HybridInferenceMode {
  /// Attempt on-device Gemini Nano via AICore first; fall back to Cloud Gemini if unavailable.
  preferOnDevice,

  /// Strictly execute on-device via Gemini Nano; throw if AICore/model is unavailable.
  onlyOnDevice,

  /// Attempt Cloud Gemini first; fall back to on-device Gemini Nano or local rules when offline.
  preferInCloud,

  /// Strictly execute in Cloud Gemini; throw if offline or unreachable.
  onlyInCloud,
}

/// Application-owned availability status for the on-device Gemini Nano model.
enum OnDeviceModelStatus {
  /// Device hardware or OS does not support AICore / Gemini Nano.
  unavailable,

  /// Gemini Nano is supported and can be downloaded via AICore.
  downloadable,

  /// Gemini Nano model weights are currently downloading.
  downloading,

  /// Gemini Nano is downloaded and ready for local inference.
  available,
}

/// Application-owned telemetry source indicating where an AI response was produced.
enum HybridInferenceSource {
  /// Executed on-device on the NPU/GPU via Android AICore (`InferenceSource.ON_DEVICE`).
  onDevice,

  /// Executed in the cloud via Firebase AI Logic (`InferenceSource.IN_CLOUD`).
  inCloud,

  /// Executed locally via deterministic biomechanical rules when both NPU and cloud are unavailable.
  localOfflineFallback,
}

/// Domain request model for single-turn text or single-image multimodal hybrid inference.
class HybridAiRequest {
  const HybridAiRequest({
    required this.prompt,
    this.systemInstruction,
    this.mode = HybridInferenceMode.preferOnDevice,
    this.cloudModelName = 'gemini-3.8-flash',
    this.imageBytes,
    this.imageMimeType,
    this.responseJsonSchema,
    this.temperature,
    this.maxOutputTokens,
    this.templateId,
    this.templateInputs,
  });

  final String prompt;
  final String? systemInstruction;
  final HybridInferenceMode mode;
  final String cloudModelName;
  final Uint8List? imageBytes;
  final String? imageMimeType;
  final String? responseJsonSchema;
  final double? temperature;
  final int? maxOutputTokens;
  final String? templateId;
  final Map<String, Object?>? templateInputs;

  HybridAiRequest copyWith({
    String? prompt,
    String? systemInstruction,
    HybridInferenceMode? mode,
    String? cloudModelName,
    Uint8List? imageBytes,
    String? imageMimeType,
    String? responseJsonSchema,
    double? temperature,
    int? maxOutputTokens,
    String? templateId,
    Map<String, Object?>? templateInputs,
  }) {
    return HybridAiRequest(
      prompt: prompt ?? this.prompt,
      systemInstruction: systemInstruction ?? this.systemInstruction,
      mode: mode ?? this.mode,
      cloudModelName: cloudModelName ?? this.cloudModelName,
      imageBytes: imageBytes ?? this.imageBytes,
      imageMimeType: imageMimeType ?? this.imageMimeType,
      responseJsonSchema: responseJsonSchema ?? this.responseJsonSchema,
      temperature: temperature ?? this.temperature,
      maxOutputTokens: maxOutputTokens ?? this.maxOutputTokens,
      templateId: templateId ?? this.templateId,
      templateInputs: templateInputs ?? this.templateInputs,
    );
  }
}

/// Domain response model containing generated text and execution telemetry.
class HybridAiResponse {
  const HybridAiResponse({
    required this.text,
    required this.inferenceSource,
    required this.modelUsed,
    required this.latencyMs,
    this.usedFallback = false,
    this.fallbackReason,
  });

  final String text;
  final HybridInferenceSource inferenceSource;
  final String modelUsed;
  final int latencyMs;
  final bool usedFallback;
  final String? fallbackReason;
}

/// Structured offline-first workout set analysis with execution telemetry.
class HybridSetLogAnalysis {
  const HybridSetLogAnalysis({
    required this.exerciseName,
    this.matchedExerciseId,
    required this.weightKg,
    required this.reps,
    required this.rpe,
    required this.fatigueAlert,
    required this.nextSetRecommendation,
    required this.inferenceSource,
    required this.modelUsed,
    required this.latencyMs,
    this.usedFallback = false,
  });

  final String exerciseName;
  final String? matchedExerciseId;
  final double weightKg;
  final int reps;
  final double rpe;
  final bool fatigueAlert;
  final String nextSetRecommendation;
  final HybridInferenceSource inferenceSource;
  final String modelUsed;
  final int latencyMs;
  final bool usedFallback;

  factory HybridSetLogAnalysis.fromJson(
    Map<String, dynamic> json, {
    required HybridInferenceSource inferenceSource,
    required String modelUsed,
    required int latencyMs,
    bool usedFallback = false,
  }) {
    final double parsedRpe = (json['rpe'] is num) ? (json['rpe'] as num).toDouble().clamp(1.0, 10.0) : 8.0;
    final bool parsedFatigue = json['fatigueAlert'] is bool ? json['fatigueAlert'] as bool : parsedRpe >= 9.0;
    return HybridSetLogAnalysis(
      exerciseName: (json['exerciseName'] ?? 'Unknown Exercise').toString().trim(),
      matchedExerciseId: json['matchedExerciseId']?.toString(),
      weightKg: (json['weightKg'] is num) ? (json['weightKg'] as num).toDouble() : 0.0,
      reps: (json['reps'] is num) ? (json['reps'] as num).toInt() : 0,
      rpe: parsedRpe,
      fatigueAlert: parsedFatigue,
      nextSetRecommendation: (json['nextSetRecommendation'] ?? '').toString().trim(),
      inferenceSource: inferenceSource,
      modelUsed: modelUsed,
      latencyMs: latencyMs,
      usedFallback: usedFallback,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'exerciseName': exerciseName,
      'matchedExerciseId': matchedExerciseId,
      'weightKg': weightKg,
      'reps': reps,
      'rpe': rpe,
      'fatigueAlert': fatigueAlert,
      'nextSetRecommendation': nextSetRecommendation,
      'inferenceSource': inferenceSource.name,
      'modelUsed': modelUsed,
      'latencyMs': latencyMs,
      'usedFallback': usedFallback,
    };
  }
}

/// Application-owned contract for ATLAS Hybrid AI (On-Device Gemini Nano + Cloud Gemini).
///
/// Zero external SDK or Pigeon types leak across this boundary (`flutter-sdk-contracts`).
abstract interface class AtlasHybridAiService {
  String get defaultCloudModelName;

  /// Checks whether the on-device Gemini Nano model is available, downloadable, or unavailable.
  Future<OnDeviceModelStatus> checkOnDeviceStatus();

  /// Triggers an on-device Gemini Nano model download via AICore when supported.
  Future<OnDeviceModelStatus> downloadOnDeviceModel();

  /// Warms up the on-device Gemini Nano model into memory to reduce first-token latency.
  Future<bool> warmUpOnDeviceModel();

  /// Generates text from a text-only or single-image + text prompt using the specified [HybridInferenceMode].
  Future<HybridAiResponse> generateHybridContent(HybridAiRequest request);

  /// Parses a natural-language workout set log (and optional equipment/plate photo) into a
  /// structured [HybridSetLogAnalysis] with fatigue detection and next-set load prescription.
  Future<HybridSetLogAnalysis> analyzeSetOfflineFirst({
    required String rawSetText,
    List<ExerciseModel> catalog = const <ExerciseModel>[],
    ExerciseModel? activeExercise,
    HybridInferenceMode mode = HybridInferenceMode.preferOnDevice,
    Uint8List? imageBytes,
    String? imageMimeType,
  });
}

/// Signature for injectable Dart-side cloud generation used when the native host channel
/// is unavailable (e.g. iOS, desktop, or non-AICore fallback).
typedef CloudPromptGenerator = Future<String> Function(HybridAiRequest request);

/// Signature for injectable Firebase AI Logic Server Prompt Template execution
/// (`FirebaseAI.googleAI().templateGenerativeModel().generateContent(templateId, inputs: ...)`).
typedef ServerTemplateExecutor = Future<String> Function(String templateId, Map<String, Object?> inputs);

/// Production implementation of [AtlasHybridAiService] bridging Android AICore
/// (`com.google.firebase:firebase-ai-ondevice`), `package:firebase_ai` cloud models,
/// Firebase Remote Config OTA prompt governance, Server Prompt Templates,
/// and a deterministic offline biomechanical engine.
class AppAtlasHybridAiService implements AtlasHybridAiService {
  AppAtlasHybridAiService({
    AtlasHybridAiHostApi? hostApi,
    WebHybridAiBridge? webBridge,
    AtlasAiConfigService? configService,
    CoachDecisionsGateway? decisionsGateway,
    CloudPromptGenerator? cloudGenerator,
    ServerTemplateExecutor? serverTemplateExecutor,
    this.defaultCloudModelName = 'gemini-3.8-flash',
  }) : _hostApi = hostApi ?? AtlasHybridAiHostApi(),
       _webBridge = webBridge ?? createWebHybridAiBridge(),
       _configService = configService ?? AppAtlasAiConfigService(),
       _decisionsGateway = decisionsGateway ?? LocalFallbackCoachDecisionsGateway(),
       _cloudGenerator = cloudGenerator,
       _serverTemplateExecutor = serverTemplateExecutor;

  final AtlasHybridAiHostApi _hostApi;
  final WebHybridAiBridge _webBridge;
  final AtlasAiConfigService _configService;
  final CoachDecisionsGateway _decisionsGateway;
  final CloudPromptGenerator? _cloudGenerator;
  final ServerTemplateExecutor? _serverTemplateExecutor;

  @override
  final String defaultCloudModelName;

  static const String _onDeviceSetSchema = '''
{
  "type": "object",
  "properties": {
    "exerciseName": {"type": "string"},
    "matchedExerciseId": {"type": "string"},
    "weightKg": {"type": "number"},
    "reps": {"type": "integer"},
    "rpe": {"type": "number"},
    "fatigueAlert": {"type": "boolean"},
    "nextSetRecommendation": {"type": "string"}
  },
  "required": ["exerciseName", "weightKg", "reps", "rpe", "fatigueAlert", "nextSetRecommendation"]
}''';

  @override
  Future<OnDeviceModelStatus> checkOnDeviceStatus() async {
    if (_webBridge.isWebPlatform) {
      return _webBridge.checkOnDeviceStatus();
    }
    try {
      final PigeonOnDeviceModelStatus pigeonStatus = await _hostApi.checkOnDeviceStatus();
      return _mapFromPigeonStatus(pigeonStatus);
    } catch (_) {
      return OnDeviceModelStatus.unavailable;
    }
  }

  @override
  Future<OnDeviceModelStatus> downloadOnDeviceModel() async {
    if (_webBridge.isWebPlatform) {
      return _webBridge.downloadOnDeviceModel();
    }
    try {
      final PigeonOnDeviceModelStatus pigeonStatus = await _hostApi.downloadOnDeviceModel();
      return _mapFromPigeonStatus(pigeonStatus);
    } catch (_) {
      return OnDeviceModelStatus.unavailable;
    }
  }

  @override
  Future<bool> warmUpOnDeviceModel() async {
    if (_webBridge.isWebPlatform) {
      return _webBridge.warmUpOnDeviceModel();
    }
    try {
      return await _hostApi.warmUpOnDeviceModel();
    } catch (_) {
      return false;
    }
  }

  HybridAiResponse _sanitizeHybridResponse(HybridAiResponse response, String language) {
    return HybridAiResponse(
      text: _decisionsGateway.sanitizeOutput(response.text, language: language),
      inferenceSource: response.inferenceSource,
      modelUsed: response.modelUsed,
      latencyMs: response.latencyMs,
      usedFallback: response.usedFallback,
      fallbackReason: response.fallbackReason,
    );
  }

  @override
  Future<HybridAiResponse> generateHybridContent(HybridAiRequest request) {
    return _generateHybridContentInternal(request, skipPromptGate: false);
  }

  Future<HybridAiResponse> _generateHybridContentInternal(
    HybridAiRequest request, {
    required bool skipPromptGate,
  }) async {
    final Stopwatch stopwatch = Stopwatch()..start();
    final String langCode = LocaleSettings.currentLocale.languageCode;
    final String? mediaRefusal = CoachSecuritySanitizer.validateEquipmentImage(
      imageBytes: request.imageBytes,
      imageMimeType: request.imageMimeType,
      language: langCode,
    );
    if (mediaRefusal != null) {
      stopwatch.stop();
      return HybridAiResponse(
        text: mediaRefusal,
        inferenceSource: HybridInferenceSource.localOfflineFallback,
        modelUsed: 'atlas-security-gatekeeper',
        latencyMs: stopwatch.elapsedMilliseconds.clamp(1, 600000),
        usedFallback: true,
        fallbackReason: 'Rejected media payload',
      );
    }

    if (!skipPromptGate) {
      try {
        final CoachDecisionResult decision = await _decisionsGateway.evaluatePrompt(
          request.prompt,
          language: langCode,
          maxLength: CoachSecuritySanitizer.maxHybridPromptLength,
        );
        if (!decision.allowed) {
          stopwatch.stop();
          final String safeRefusal = _decisionsGateway.sanitizeOutput(
            decision.refusalText ?? CoachSecuritySanitizer.constantRefusal(langCode),
            language: langCode,
          );
          return HybridAiResponse(
            text: safeRefusal,
            inferenceSource: HybridInferenceSource.localOfflineFallback,
            modelUsed: 'atlas-security-gatekeeper',
            latencyMs: stopwatch.elapsedMilliseconds.clamp(1, 600000),
            usedFallback: true,
            fallbackReason: decision.medicalRedFlag ? 'Medical red flag' : 'Blocked by security gatekeeper',
          );
        }
      } catch (error) {
        stopwatch.stop();
        return HybridAiResponse(
          text: _decisionsGateway.sanitizeError(error, language: langCode),
          inferenceSource: HybridInferenceSource.localOfflineFallback,
          modelUsed: 'atlas-security-gatekeeper',
          latencyMs: stopwatch.elapsedMilliseconds.clamp(1, 600000),
          usedFallback: true,
          fallbackReason: 'Security gatekeeper rejected',
        );
      }
    }

    final AtlasAiRemoteConfig otaConfig = _configService.currentConfig;
    final String configuredCloud = otaConfig.cloudModelName.trim().isNotEmpty ? otaConfig.cloudModelName.trim() : defaultCloudModelName;
    final String effectiveCloudModel = request.cloudModelName.trim().isEmpty ? configuredCloud : request.cloudModelName.trim();

    if (_webBridge.isWebPlatform) {
      return _sanitizeHybridResponse(await _generateWebHybridContent(request, effectiveCloudModel, stopwatch), langCode);
    }

    final String? requestedTemplateId = request.templateId?.trim();
    if ((request.mode == HybridInferenceMode.preferInCloud || request.mode == HybridInferenceMode.onlyInCloud) &&
        otaConfig.useServerPromptTemplates &&
        requestedTemplateId != null &&
        requestedTemplateId.isNotEmpty &&
        _serverTemplateExecutor != null) {
      try {
        final String templateText = await _executeServerPromptTemplate(
          requestedTemplateId,
          request.templateInputs ?? <String, Object?>{'prompt': request.prompt},
        );
        stopwatch.stop();
        return _sanitizeHybridResponse(
          HybridAiResponse(
            text: templateText,
            inferenceSource: HybridInferenceSource.inCloud,
            modelUsed: '$effectiveCloudModel · template:$requestedTemplateId',
            latencyMs: stopwatch.elapsedMilliseconds.clamp(1, 600000),
            usedFallback: false,
          ),
          langCode,
        );
      } catch (_) {
        // Transparent fallback to standard host/cloud route when server template is unprovisioned.
      }
    }

    try {
      final PigeonHybridAiResponse hostResponse = await _hostApi.generateHybridContent(
        PigeonHybridAiRequest(
          prompt: request.prompt,
          systemInstruction: request.systemInstruction,
          mode: _mapToPigeonMode(request.mode),
          cloudModelName: effectiveCloudModel,
          imageBytes: request.imageBytes,
          imageMimeType: request.imageMimeType,
          responseJsonSchema: request.responseJsonSchema,
          temperature: request.temperature,
          maxOutputTokens: request.maxOutputTokens,
        ),
      );
      stopwatch.stop();
      return _sanitizeHybridResponse(
        HybridAiResponse(
          text: hostResponse.text,
          inferenceSource: _mapFromPigeonSource(hostResponse.inferenceSource),
          modelUsed: hostResponse.modelUsed,
          latencyMs: hostResponse.latencyMs > 0 ? hostResponse.latencyMs : stopwatch.elapsedMilliseconds,
          usedFallback: hostResponse.usedFallback,
          fallbackReason: hostResponse.fallbackReason,
        ),
        langCode,
      );
    } catch (hostError) {
      if (request.mode == HybridInferenceMode.onlyOnDevice) {
        throw StateError('ONLY_ON_DEVICE inference failed because Gemini Nano / AICore is unavailable: $hostError');
      }

      // Attempt Server Prompt Template + Dart-side Cloud Gemini fallback if allowed by the inference mode.
      try {
        final ({String text, String modelLabel}) cloudResult = await _executeCloudWithTemplateFallback(
          request.copyWith(cloudModelName: effectiveCloudModel),
          effectiveCloudModel,
        );
        stopwatch.stop();
        final bool isFallbackFromOnDevice = request.mode == HybridInferenceMode.preferOnDevice;
        return _sanitizeHybridResponse(
          HybridAiResponse(
            text: cloudResult.text,
            inferenceSource: HybridInferenceSource.inCloud,
            modelUsed: cloudResult.modelLabel,
            latencyMs: stopwatch.elapsedMilliseconds.clamp(1, 600000),
            usedFallback: isFallbackFromOnDevice,
            fallbackReason: isFallbackFromOnDevice ? hostError.toString() : null,
          ),
          langCode,
        );
      } catch (cloudError) {
        if (request.mode == HybridInferenceMode.onlyInCloud) {
          throw StateError('ONLY_IN_CLOUD inference failed while offline or unreachable: $cloudError');
        }

        stopwatch.stop();
        final String offlineText = _buildDeterministicOfflineResponse(request);
        return _sanitizeHybridResponse(
          HybridAiResponse(
            text: offlineText,
            inferenceSource: HybridInferenceSource.localOfflineFallback,
            modelUsed: 'atlas-biomechanical-offline-engine',
            latencyMs: stopwatch.elapsedMilliseconds.clamp(1, 600000),
            usedFallback: true,
            fallbackReason: 'Host & Cloud unavailable ($hostError | $cloudError)',
          ),
          langCode,
        );
      }
    }
  }

  Future<HybridAiResponse> _generateWebHybridContent(HybridAiRequest request, String effectiveCloudModel, Stopwatch stopwatch) async {
    final bool hasImage = request.imageBytes != null && request.imageBytes!.isNotEmpty;

    if (request.mode == HybridInferenceMode.preferOnDevice || request.mode == HybridInferenceMode.onlyOnDevice) {
      try {
        if (hasImage) {
          throw UnsupportedError('Chrome Prompt API text session does not accept image bytes.');
        }
        final String onDeviceText = await _webBridge.generateOnDeviceText(
          prompt: request.prompt,
          systemInstruction: request.systemInstruction,
          responseJsonSchema: request.responseJsonSchema,
          temperature: request.temperature,
        );
        stopwatch.stop();
        return HybridAiResponse(
          text: onDeviceText,
          inferenceSource: HybridInferenceSource.onDevice,
          modelUsed: 'chrome-prompt-api-gemini-nano',
          latencyMs: stopwatch.elapsedMilliseconds.clamp(1, 600000),
          usedFallback: false,
        );
      } catch (webError) {
        if (request.mode == HybridInferenceMode.onlyOnDevice) {
          throw StateError('ONLY_ON_DEVICE inference failed on Web Chrome Prompt API: $webError');
        }
        try {
          final ({String text, String modelLabel}) cloudResult = await _executeCloudWithTemplateFallback(
            request.copyWith(cloudModelName: effectiveCloudModel),
            effectiveCloudModel,
          );
          stopwatch.stop();
          return HybridAiResponse(
            text: cloudResult.text,
            inferenceSource: HybridInferenceSource.inCloud,
            modelUsed: cloudResult.modelLabel,
            latencyMs: stopwatch.elapsedMilliseconds.clamp(1, 600000),
            usedFallback: true,
            fallbackReason: webError.toString(),
          );
        } catch (cloudError) {
          stopwatch.stop();
          return HybridAiResponse(
            text: _buildDeterministicOfflineResponse(request),
            inferenceSource: HybridInferenceSource.localOfflineFallback,
            modelUsed: 'atlas-biomechanical-offline-engine',
            latencyMs: stopwatch.elapsedMilliseconds.clamp(1, 600000),
            usedFallback: true,
            fallbackReason: 'Web Prompt API & Cloud unavailable ($webError | $cloudError)',
          );
        }
      }
    }

    try {
      final ({String text, String modelLabel}) cloudResult = await _executeCloudWithTemplateFallback(
        request.copyWith(cloudModelName: effectiveCloudModel),
        effectiveCloudModel,
      );
      stopwatch.stop();
      return HybridAiResponse(
        text: cloudResult.text,
        inferenceSource: HybridInferenceSource.inCloud,
        modelUsed: cloudResult.modelLabel,
        latencyMs: stopwatch.elapsedMilliseconds.clamp(1, 600000),
        usedFallback: false,
      );
    } catch (cloudError) {
      if (request.mode == HybridInferenceMode.onlyInCloud) {
        throw StateError('ONLY_IN_CLOUD inference failed while offline or unreachable: $cloudError');
      }
      if (!hasImage) {
        try {
          final String onDeviceText = await _webBridge.generateOnDeviceText(
            prompt: request.prompt,
            systemInstruction: request.systemInstruction,
            responseJsonSchema: request.responseJsonSchema,
            temperature: request.temperature,
          );
          stopwatch.stop();
          return HybridAiResponse(
            text: onDeviceText,
            inferenceSource: HybridInferenceSource.onDevice,
            modelUsed: 'chrome-prompt-api-gemini-nano',
            latencyMs: stopwatch.elapsedMilliseconds.clamp(1, 600000),
            usedFallback: true,
            fallbackReason: cloudError.toString(),
          );
        } catch (_) {}
      }
      stopwatch.stop();
      return HybridAiResponse(
        text: _buildDeterministicOfflineResponse(request),
        inferenceSource: HybridInferenceSource.localOfflineFallback,
        modelUsed: 'atlas-biomechanical-offline-engine',
        latencyMs: stopwatch.elapsedMilliseconds.clamp(1, 600000),
        usedFallback: true,
        fallbackReason: cloudError.toString(),
      );
    }
  }

  @override
  Future<HybridSetLogAnalysis> analyzeSetOfflineFirst({
    required String rawSetText,
    List<ExerciseModel> catalog = const <ExerciseModel>[],
    ExerciseModel? activeExercise,
    HybridInferenceMode mode = HybridInferenceMode.preferOnDevice,
    Uint8List? imageBytes,
    String? imageMimeType,
  }) async {
    final HybridSetLogAnalysis deterministicBaseline = parseSetDeterministically(
      rawSetText: rawSetText,
      catalog: catalog,
      activeExercise: activeExercise,
    );

    final String langCode = LocaleSettings.currentLocale.languageCode;
    final String? imageRefusal = CoachSecuritySanitizer.validateEquipmentImage(
      imageBytes: imageBytes,
      imageMimeType: imageMimeType,
      language: langCode,
    );
    if (imageRefusal != null) {
      return HybridSetLogAnalysis(
        exerciseName: deterministicBaseline.exerciseName,
        matchedExerciseId: deterministicBaseline.matchedExerciseId,
        weightKg: 0,
        reps: 0,
        rpe: deterministicBaseline.rpe,
        fatigueAlert: false,
        nextSetRecommendation: imageRefusal,
        inferenceSource: HybridInferenceSource.localOfflineFallback,
        modelUsed: 'atlas-security-gatekeeper',
        latencyMs: 1,
        usedFallback: true,
      );
    }

    if (rawSetText.trim().isNotEmpty) {
      try {
        final CoachDecisionResult decision = await _decisionsGateway.evaluatePrompt(rawSetText, language: langCode);
        if (!decision.allowed) {
          final String safeRefusal = _decisionsGateway.sanitizeOutput(
            decision.refusalText ?? CoachSecuritySanitizer.constantRefusal(langCode),
            language: langCode,
          );
          return HybridSetLogAnalysis(
            exerciseName: decision.medicalRedFlag ? 'ATLAS Safety Alert' : deterministicBaseline.exerciseName,
            matchedExerciseId: deterministicBaseline.matchedExerciseId,
            weightKg: 0,
            reps: 0,
            rpe: deterministicBaseline.rpe,
            fatigueAlert: decision.medicalRedFlag,
            nextSetRecommendation: safeRefusal,
            inferenceSource: HybridInferenceSource.localOfflineFallback,
            modelUsed: 'atlas-security-gatekeeper',
            latencyMs: 1,
            usedFallback: true,
          );
        }
      } catch (error) {
        return HybridSetLogAnalysis(
          exerciseName: deterministicBaseline.exerciseName,
          matchedExerciseId: deterministicBaseline.matchedExerciseId,
          weightKg: 0,
          reps: 0,
          rpe: deterministicBaseline.rpe,
          fatigueAlert: false,
          nextSetRecommendation: _decisionsGateway.sanitizeError(error, language: langCode),
          inferenceSource: HybridInferenceSource.localOfflineFallback,
          modelUsed: 'atlas-security-gatekeeper',
          latencyMs: 1,
          usedFallback: true,
        );
      }
    }

    final String catalogSummary = catalog.take(25).map((ExerciseModel e) => '${e.id}:${e.name} (${e.primaryMuscleGroup})').join(', ');

    final AtlasAiRemoteConfig otaConfig = _configService.currentConfig;
    final String prompt = otaConfig.renderHybridSetPrompt(
      rawSetText: rawSetText,
      catalogContext: catalogSummary,
      activeExerciseName: activeExercise?.name,
      activeExerciseId: activeExercise?.id,
    );

    final String languageName = switch (LocaleSettings.currentLocale) {
      AppLocale.es => 'Spanish (Español)',
      AppLocale.ca => 'Catalan (Català)',
      AppLocale.fr => 'French (Français)',
      AppLocale.pt => 'Portuguese (Português)',
      AppLocale.en => 'English',
    };
    final String localizedPrompt =
        '$prompt\n'
        'IMPORTANT: Write exerciseName and nextSetRecommendation strictly in $languageName (locale: $langCode).';
    final HybridAiResponse response = await _generateHybridContentInternal(
      HybridAiRequest(
        prompt: localizedPrompt,
        systemInstruction:
            '${otaConfig.coachSystemPrompt} '
            'Parse the set log into JSON and prescribe the next set load/rest based on RPE and fatigue. '
            'Always write exerciseName and nextSetRecommendation in $languageName ($langCode).',
        mode: mode,
        cloudModelName: otaConfig.cloudModelName.isNotEmpty ? otaConfig.cloudModelName : defaultCloudModelName,
        imageBytes: imageBytes,
        imageMimeType: imageMimeType,
        responseJsonSchema: _onDeviceSetSchema,
        temperature: 0.1,
        maxOutputTokens: 256,
        templateId: otaConfig.useServerPromptTemplates ? otaConfig.setAutoregulationTemplateId : null,
        templateInputs: <String, Object?>{
          'rawSetText': rawSetText,
          'activeExerciseName': activeExercise?.name ?? 'none',
          'activeExerciseId': activeExercise?.id ?? '',
          'catalogContext': catalogSummary,
        },
      ),
      skipPromptGate: true,
    );

    if (response.inferenceSource != HybridInferenceSource.localOfflineFallback) {
      final Map<String, dynamic>? decoded = _tryDecodeJsonMap(response.text);
      if (decoded != null) {
        final HybridSetLogAnalysis parsed = HybridSetLogAnalysis.fromJson(
          decoded,
          inferenceSource: response.inferenceSource,
          modelUsed: response.modelUsed,
          latencyMs: response.latencyMs,
          usedFallback: response.usedFallback,
        );
        final String resolvedRecommendation = _decisionsGateway.sanitizeOutput(
          parsed.nextSetRecommendation.isEmpty ? deterministicBaseline.nextSetRecommendation : parsed.nextSetRecommendation,
          language: langCode,
        );
        return HybridSetLogAnalysis(
          exerciseName: parsed.exerciseName.isEmpty || parsed.exerciseName == 'Unknown Exercise'
              ? deterministicBaseline.exerciseName
              : _decisionsGateway.sanitizeOutput(parsed.exerciseName, language: langCode),
          matchedExerciseId: (parsed.matchedExerciseId == null || parsed.matchedExerciseId!.isEmpty)
              ? deterministicBaseline.matchedExerciseId
              : parsed.matchedExerciseId,
          weightKg: parsed.weightKg > 0 ? parsed.weightKg : deterministicBaseline.weightKg,
          reps: parsed.reps > 0 ? parsed.reps : deterministicBaseline.reps,
          rpe: parsed.rpe,
          fatigueAlert: parsed.fatigueAlert,
          nextSetRecommendation: resolvedRecommendation,
          inferenceSource: response.inferenceSource,
          modelUsed: response.modelUsed,
          latencyMs: response.latencyMs,
          usedFallback: response.usedFallback,
        );
      }
    }

    return HybridSetLogAnalysis(
      exerciseName: deterministicBaseline.exerciseName,
      matchedExerciseId: deterministicBaseline.matchedExerciseId,
      weightKg: deterministicBaseline.weightKg,
      reps: deterministicBaseline.reps,
      rpe: deterministicBaseline.rpe,
      fatigueAlert: deterministicBaseline.fatigueAlert,
      nextSetRecommendation: _decisionsGateway.sanitizeOutput(
        deterministicBaseline.nextSetRecommendation,
        language: langCode,
      ),
      inferenceSource: response.inferenceSource,
      modelUsed: response.modelUsed,
      latencyMs: response.latencyMs,
      usedFallback: true,
    );
  }

  /// Pure, deterministic biomechanical parser for workout set logs when both NPU and Cloud are unavailable.
  @visibleForTesting
  static HybridSetLogAnalysis parseSetDeterministically({
    required String rawSetText,
    List<ExerciseModel> catalog = const <ExerciseModel>[],
    ExerciseModel? activeExercise,
    HybridInferenceSource inferenceSource = HybridInferenceSource.localOfflineFallback,
    String modelUsed = 'atlas-biomechanical-offline-engine',
    int latencyMs = 1,
    bool usedFallback = true,
  }) {
    final String normalized = rawSetText.trim();
    final String lower = normalized.toLowerCase();

    // 1. Extract weight (kg or lbs converted to kg).
    double weightKg = 0.0;
    final RegExp weightRegex = RegExp(r'(\d+(?:[.,]\d+)?)\s*(kg|kgs|kilos|lb|lbs)\b', caseSensitive: false);
    final RegExpMatch? weightMatch = weightRegex.firstMatch(lower);
    if (weightMatch != null) {
      final double rawVal = double.tryParse(weightMatch.group(1)!.replaceAll(',', '.')) ?? 0.0;
      final String unit = weightMatch.group(2)!.toLowerCase();
      weightKg = unit.startsWith('lb') ? double.parse((rawVal * 0.45359237).toStringAsFixed(1)) : rawVal;
    } else {
      final RegExp xPattern = RegExp(r'(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+)');
      final RegExpMatch? xMatch = xPattern.firstMatch(lower);
      if (xMatch != null) {
        weightKg = double.tryParse(xMatch.group(1)!.replaceAll(',', '.')) ?? 0.0;
      }
    }

    // 2. Extract repetitions.
    int reps = 0;
    final RegExp repsExplicit = RegExp(r'(?:[x×]\s*(\d+))|(?:(\d+)\s*(?:reps|rep|repeticiones|r)\b)', caseSensitive: false);
    final RegExpMatch? repsMatch = repsExplicit.firstMatch(lower);
    if (repsMatch != null) {
      final String? group1 = repsMatch.group(1);
      final String? group2 = repsMatch.group(2);
      reps = int.tryParse(group1 ?? group2 ?? '0') ?? 0;
    }
    if (reps <= 0) {
      reps = 8;
    }

    // 3. Extract RPE (Rate of Perceived Exertion, 1-10).
    double rpe = 8.0;
    final RegExp rpeRegex = RegExp(r'(?:@\s*rpe|rpe|@)\s*(\d+(?:[.,]\d+)?)', caseSensitive: false);
    final RegExpMatch? rpeMatch = rpeRegex.firstMatch(lower);
    if (rpeMatch != null) {
      final double parsed = double.tryParse(rpeMatch.group(1)!.replaceAll(',', '.')) ?? 8.0;
      rpe = parsed.clamp(1.0, 10.0);
    }

    // 4. Match exercise from activeExercise or catalog.
    ExerciseModel? matched = activeExercise;
    if (matched == null && catalog.isNotEmpty) {
      for (final ExerciseModel candidate in catalog) {
        if (lower.contains(candidate.name.toLowerCase()) || lower.contains(candidate.id.toLowerCase())) {
          matched = candidate;
          break;
        }
      }
    }

    String resolvedName = matched?.name ?? '';
    if (resolvedName.isEmpty) {
      final String stripped = normalized
          .replaceAll(RegExp(r'(\d+(?:[.,]\d+)?)\s*(?:kg|kgs|kilos|lb|lbs)\b', caseSensitive: false), '')
          .replaceAll(RegExp(r'[x×]\s*\d+', caseSensitive: false), '')
          .replaceAll(RegExp(r'\d+\s*(?:reps|rep|repeticiones)\b', caseSensitive: false), '')
          .replaceAll(RegExp(r'(?:@\s*rpe|rpe|@)\s*\d+(?:[.,]\d+)?', caseSensitive: false), '')
          .replaceAll('@', '')
          .replaceAll(RegExp(r'\s+'), ' ')
          .trim();
      resolvedName = stripped.isNotEmpty ? stripped : 'Strength Set';
    }

    final bool fatigueAlert = rpe >= 9.0;
    final String nextSetRecommendation;
    if (rpe >= 9.5) {
      final double reducedWeight = weightKg > 0 ? double.parse((weightKg * 0.95).toStringAsFixed(1)) : 0.0;
      nextSetRecommendation = reducedWeight > 0
          ? t.hybridAi.recHighFatigueWithWeight(rpe: rpe, weight: reducedWeight)
          : t.hybridAi.recHighFatigueNoWeight(rpe: rpe);
    } else if (rpe >= 9.0) {
      nextSetRecommendation = weightKg > 0
          ? t.hybridAi.recNearFailureWithWeight(rpe: rpe, weight: weightKg)
          : t.hybridAi.recNearFailureNoWeight(rpe: rpe);
    } else if (rpe <= 7.5 && weightKg > 0) {
      final double nextWeight = double.parse((weightKg + 2.5).toStringAsFixed(1));
      nextSetRecommendation = t.hybridAi.recProgressiveOverload(rpe: rpe, weight: nextWeight, reps: reps);
    } else {
      nextSetRecommendation = weightKg > 0
          ? t.hybridAi.recOptimalWithWeight(rpe: rpe, weight: weightKg, reps: reps)
          : t.hybridAi.recOptimalNoWeight(rpe: rpe, reps: reps);
    }

    return HybridSetLogAnalysis(
      exerciseName: resolvedName,
      matchedExerciseId: matched?.id,
      weightKg: weightKg,
      reps: reps,
      rpe: rpe,
      fatigueAlert: fatigueAlert,
      nextSetRecommendation: nextSetRecommendation,
      inferenceSource: inferenceSource,
      modelUsed: modelUsed,
      latencyMs: latencyMs,
      usedFallback: usedFallback,
    );
  }

  Future<({String text, String modelLabel})> _executeCloudWithTemplateFallback(HybridAiRequest request, String effectiveCloudModel) async {
    final AtlasAiRemoteConfig otaConfig = _configService.currentConfig;
    final String? templateId = request.templateId?.trim();
    if (otaConfig.useServerPromptTemplates && templateId != null && templateId.isNotEmpty) {
      try {
        final String templateText = await _executeServerPromptTemplate(
          templateId,
          request.templateInputs ?? <String, Object?>{'prompt': request.prompt},
        );
        return (text: templateText, modelLabel: '$effectiveCloudModel · template:$templateId');
      } catch (_) {
        // Transparent fallback to standard cloud prompt when server template is not yet provisioned.
      }
    }

    final String cloudText = await _executeDartCloudGeneration(request);
    return (text: cloudText, modelLabel: effectiveCloudModel);
  }

  Future<String> _executeServerPromptTemplate(String templateId, Map<String, Object?> inputs) async {
    if (_serverTemplateExecutor != null) {
      return _serverTemplateExecutor(templateId, inputs);
    }
    if (Firebase.apps.isEmpty) {
      throw StateError('Firebase is not initialized for templateGenerativeModel.');
    }
    if (FirebaseAuth.instance.currentUser == null) {
      try {
        await FirebaseAuth.instance.signInAnonymously();
      } catch (_) {}
    }
    final dynamic aiInstance = FirebaseAI.googleAI(app: Firebase.app());
    final dynamic templateModel = aiInstance.templateGenerativeModel();
    final dynamic response = await templateModel.generateContent(templateId, inputs: inputs);
    final String text = (response?.text ?? '').toString().trim();
    if (text.isEmpty) {
      throw StateError('Empty response from FirebaseAI templateGenerativeModel ($templateId).');
    }
    return text;
  }

  Future<String> _executeDartCloudGeneration(HybridAiRequest request) async {
    final String untrustedPrompt =
        CoachSecuritySanitizer.wrapUntrustedPrompt(request.prompt);
    if (_cloudGenerator != null) {
      return _cloudGenerator(request.copyWith(prompt: untrustedPrompt));
    }
    if (Firebase.apps.isEmpty) {
      throw StateError('Firebase is not initialized for cloud inference.');
    }

    final GenerationConfig generationConfig = GenerationConfig(
      temperature: request.temperature,
      maxOutputTokens: request.maxOutputTokens,
      responseMimeType: request.responseJsonSchema != null ? 'application/json' : null,
    );

    if (FirebaseAuth.instance.currentUser == null) {
      try {
        await FirebaseAuth.instance.signInAnonymously();
      } catch (_) {}
    }

    final String effectivePrompt = request.responseJsonSchema != null
        ? '$untrustedPrompt\n\nRespond strictly with valid JSON matching this schema:\n${request.responseJsonSchema}'
        : untrustedPrompt;

    final List<Content> contents;
    if (request.imageBytes != null && request.imageBytes!.isNotEmpty) {
      contents = <Content>[
        Content.multi(<Part>[InlineDataPart(request.imageMimeType ?? 'image/jpeg', request.imageBytes!), TextPart(effectivePrompt)]),
      ];
    } else {
      contents = <Content>[Content.text(effectivePrompt)];
    }

    final List<String> candidateModels = <String>[
      request.cloudModelName,
      if (request.cloudModelName != 'gemini-3.8-flash') 'gemini-3.8-flash',
    ];

    Object? lastError;
    for (final String candidateModel in candidateModels) {
      try {
        final GenerativeModel model = FirebaseAI.googleAI(app: Firebase.app()).generativeModel(
          model: candidateModel,
          generationConfig: generationConfig,
          systemInstruction: (request.systemInstruction != null && request.systemInstruction!.trim().isNotEmpty)
              ? Content.system(request.systemInstruction!.trim())
              : null,
        );
        final GenerateContentResponse response = await model.generateContent(contents);
        final String text = response.text?.trim() ?? '';
        if (text.isNotEmpty) {
          return text;
        }
      } catch (e) {
        lastError = e;
        debugPrint('[AtlasHybridAiService Cloud Error] ($candidateModel) $e');
      }
    }
    throw StateError('FirebaseAI cloud models failed ($lastError).');
  }

  String _buildDeterministicOfflineResponse(HybridAiRequest request) {
    final HybridSetLogAnalysis analysis = parseSetDeterministically(rawSetText: request.prompt);
    if (request.responseJsonSchema != null) {
      return jsonEncode(<String, dynamic>{
        'exerciseName': analysis.exerciseName,
        'matchedExerciseId': analysis.matchedExerciseId,
        'weightKg': analysis.weightKg,
        'reps': analysis.reps,
        'rpe': analysis.rpe,
        'fatigueAlert': analysis.fatigueAlert,
        'nextSetRecommendation': analysis.nextSetRecommendation,
      });
    }
    return analysis.nextSetRecommendation;
  }

  static Map<String, dynamic>? _tryDecodeJsonMap(String rawText) {
    String cleaned = rawText.trim();
    if (cleaned.startsWith('```')) {
      cleaned = cleaned.replaceFirst(RegExp(r'^```(?:json)?\s*'), '').replaceFirst(RegExp(r'\s*```$'), '').trim();
    }
    final int startBrace = cleaned.indexOf('{');
    final int endBrace = cleaned.lastIndexOf('}');
    if (startBrace >= 0 && endBrace > startBrace) {
      cleaned = cleaned.substring(startBrace, endBrace + 1);
    }
    try {
      final Object? decoded = jsonDecode(cleaned);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
      if (decoded is Map) {
        return decoded.map((Object? k, Object? v) => MapEntry(k.toString(), v));
      }
    } catch (_) {}
    return null;
  }

  static PigeonHybridInferenceMode _mapToPigeonMode(HybridInferenceMode mode) {
    return switch (mode) {
      HybridInferenceMode.preferOnDevice => PigeonHybridInferenceMode.preferOnDevice,
      HybridInferenceMode.onlyOnDevice => PigeonHybridInferenceMode.onlyOnDevice,
      HybridInferenceMode.preferInCloud => PigeonHybridInferenceMode.preferInCloud,
      HybridInferenceMode.onlyInCloud => PigeonHybridInferenceMode.onlyInCloud,
    };
  }

  static OnDeviceModelStatus _mapFromPigeonStatus(PigeonOnDeviceModelStatus status) {
    return switch (status) {
      PigeonOnDeviceModelStatus.unavailable => OnDeviceModelStatus.unavailable,
      PigeonOnDeviceModelStatus.downloadable => OnDeviceModelStatus.downloadable,
      PigeonOnDeviceModelStatus.downloading => OnDeviceModelStatus.downloading,
      PigeonOnDeviceModelStatus.available => OnDeviceModelStatus.available,
    };
  }

  static HybridInferenceSource _mapFromPigeonSource(PigeonInferenceSource source) {
    return switch (source) {
      PigeonInferenceSource.onDevice => HybridInferenceSource.onDevice,
      PigeonInferenceSource.inCloud => HybridInferenceSource.inCloud,
      PigeonInferenceSource.localOfflineFallback => HybridInferenceSource.localOfflineFallback,
    };
  }
}

/// In-memory test double for [AtlasHybridAiService] enabling deterministic unit and widget tests
/// without native platform channels (`flutter-sdk-contracts`).
class FakeAtlasHybridAiService implements AtlasHybridAiService {
  FakeAtlasHybridAiService({
    this.status = OnDeviceModelStatus.available,
    this.downloadResultStatus = OnDeviceModelStatus.available,
    this.warmUpResult = true,
    this.defaultCloudModelName = 'gemini-3.8-flash',
    this.simulatedLatencyMs = 18,
  });

  OnDeviceModelStatus status;
  OnDeviceModelStatus downloadResultStatus;
  bool warmUpResult;

  @override
  final String defaultCloudModelName;

  int simulatedLatencyMs;
  HybridAiResponse? nextResponse;
  final List<HybridAiRequest> recordedRequests = <HybridAiRequest>[];
  int checkStatusCallCount = 0;
  int downloadCallCount = 0;
  int warmUpCallCount = 0;

  @override
  Future<OnDeviceModelStatus> checkOnDeviceStatus() async {
    checkStatusCallCount += 1;
    return status;
  }

  @override
  Future<OnDeviceModelStatus> downloadOnDeviceModel() async {
    downloadCallCount += 1;
    status = downloadResultStatus;
    return status;
  }

  @override
  Future<bool> warmUpOnDeviceModel() async {
    warmUpCallCount += 1;
    return warmUpResult && status == OnDeviceModelStatus.available;
  }

  @override
  Future<HybridAiResponse> generateHybridContent(HybridAiRequest request) async {
    recordedRequests.add(request);
    if (nextResponse != null) {
      return nextResponse!;
    }

    if (request.mode == HybridInferenceMode.onlyOnDevice && status != OnDeviceModelStatus.available) {
      throw StateError('FakeAtlasHybridAiService: On-device Gemini Nano is not available ($status).');
    }

    final bool runOnDevice = switch (request.mode) {
      HybridInferenceMode.preferOnDevice => status == OnDeviceModelStatus.available,
      HybridInferenceMode.onlyOnDevice => true,
      HybridInferenceMode.preferInCloud => false,
      HybridInferenceMode.onlyInCloud => false,
    };

    return HybridAiResponse(
      text: 'Simulated hybrid response for: ${request.prompt}',
      inferenceSource: runOnDevice ? HybridInferenceSource.onDevice : HybridInferenceSource.inCloud,
      modelUsed: runOnDevice ? 'gemini-nano-on-device' : request.cloudModelName,
      latencyMs: simulatedLatencyMs,
      usedFallback: request.mode == HybridInferenceMode.preferOnDevice && !runOnDevice,
    );
  }

  @override
  Future<HybridSetLogAnalysis> analyzeSetOfflineFirst({
    required String rawSetText,
    List<ExerciseModel> catalog = const <ExerciseModel>[],
    ExerciseModel? activeExercise,
    HybridInferenceMode mode = HybridInferenceMode.preferOnDevice,
    Uint8List? imageBytes,
    String? imageMimeType,
  }) async {
    if (mode == HybridInferenceMode.onlyOnDevice && status != OnDeviceModelStatus.available) {
      throw StateError('FakeAtlasHybridAiService: On-device Gemini Nano is not available ($status).');
    }
    final bool runOnDevice =
        mode == HybridInferenceMode.onlyOnDevice || (mode == HybridInferenceMode.preferOnDevice && status == OnDeviceModelStatus.available);
    return AppAtlasHybridAiService.parseSetDeterministically(
      rawSetText: rawSetText,
      catalog: catalog,
      activeExercise: activeExercise,
      inferenceSource: runOnDevice ? HybridInferenceSource.onDevice : HybridInferenceSource.inCloud,
      modelUsed: runOnDevice ? 'gemini-nano-on-device' : defaultCloudModelName,
      latencyMs: simulatedLatencyMs,
      usedFallback: mode == HybridInferenceMode.preferOnDevice && !runOnDevice,
    );
  }
}

@Riverpod(keepAlive: true)
AtlasHybridAiService atlasHybridAiService(Ref ref) {
  final AtlasAiConfigService configService = ref.watch(atlasAiConfigServiceProvider);
  return AppAtlasHybridAiService(configService: configService);
}
