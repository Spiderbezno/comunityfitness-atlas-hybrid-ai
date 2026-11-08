// 🎯 Dart imports:
import 'dart:async';

// 🐦 Flutter imports:
import 'package:flutter/services.dart';

// 📦 Package imports:
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/ai_coach_models.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/services/atlas_ai_config_service.dart';
import 'package:comunityfitness/services/atlas_hybrid_ai_service.dart';

part 'atlas_hybrid_ai_viewmodel.g.dart';

/// Immutable state for the ATLAS Hybrid AI (On-Device Gemini Nano + Cloud Gemini) panel.
class AtlasHybridAiState {
  const AtlasHybridAiState({
    this.selectedMode = HybridInferenceMode.preferOnDevice,
    this.modelStatus = OnDeviceModelStatus.unavailable,
    this.isWarmedUp = false,
    this.isLoading = false,
    this.activeTemplateId = 'atlas-set-autoregulation-v1-0-0',
    this.useServerPromptTemplates = true,
    this.configSource = 'in_app_defaults',
    this.lastInferenceSource,
    this.lastModelUsed,
    this.lastLatencyMs,
    this.lastUsedFallback = false,
    this.lastSetAnalysis,
    this.lastVisionResponse,
    this.errorMessage,
  });

  final HybridInferenceMode selectedMode;
  final OnDeviceModelStatus modelStatus;
  final bool isWarmedUp;
  final bool isLoading;
  final String activeTemplateId;
  final bool useServerPromptTemplates;
  final String configSource;
  final HybridInferenceSource? lastInferenceSource;
  final String? lastModelUsed;
  final int? lastLatencyMs;
  final bool lastUsedFallback;
  final HybridSetLogAnalysis? lastSetAnalysis;
  final HybridAiResponse? lastVisionResponse;
  final String? errorMessage;

  AtlasHybridAiState copyWith({
    HybridInferenceMode? selectedMode,
    OnDeviceModelStatus? modelStatus,
    bool? isWarmedUp,
    bool? isLoading,
    String? activeTemplateId,
    bool? useServerPromptTemplates,
    String? configSource,
    HybridInferenceSource? lastInferenceSource,
    String? lastModelUsed,
    int? lastLatencyMs,
    bool? lastUsedFallback,
    HybridSetLogAnalysis? lastSetAnalysis,
    HybridAiResponse? lastVisionResponse,
    String? errorMessage,
    bool clearError = false,
  }) {
    return AtlasHybridAiState(
      selectedMode: selectedMode ?? this.selectedMode,
      modelStatus: modelStatus ?? this.modelStatus,
      isWarmedUp: isWarmedUp ?? this.isWarmedUp,
      isLoading: isLoading ?? this.isLoading,
      activeTemplateId: activeTemplateId ?? this.activeTemplateId,
      useServerPromptTemplates: useServerPromptTemplates ?? this.useServerPromptTemplates,
      configSource: configSource ?? this.configSource,
      lastInferenceSource: lastInferenceSource ?? this.lastInferenceSource,
      lastModelUsed: lastModelUsed ?? this.lastModelUsed,
      lastLatencyMs: lastLatencyMs ?? this.lastLatencyMs,
      lastUsedFallback: lastUsedFallback ?? this.lastUsedFallback,
      lastSetAnalysis: lastSetAnalysis ?? this.lastSetAnalysis,
      lastVisionResponse: lastVisionResponse ?? this.lastVisionResponse,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}

@riverpod
class AtlasHybridAiViewModel extends _$AtlasHybridAiViewModel {
  static const MethodChannel _cameraChannel = MethodChannel('com.comunityfitness.hybrid_ai/camera');

  /// Valid 1x1 PNG sample image bytes for 1-tap multimodal (`Bitmap + prompt`) verification
  /// on emulators or physical devices.
  static final Uint8List defaultSampleEquipmentPng = Uint8List.fromList(const <int>[
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, // PNG signature
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52, // IHDR chunk
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
    0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41, // IDAT chunk
    0x54, 0x78, 0x9C, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
    0x00, 0x03, 0x01, 0x01, 0x00, 0x18, 0xDD, 0x8D,
    0xB0, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, // IEND chunk
    0x44, 0xAE, 0x42, 0x60, 0x82,
  ]);

  late AtlasHybridAiService _service;
  late AtlasAiConfigService _configService;

  @override
  AtlasHybridAiState build() {
    _service = ref.watch(atlasHybridAiServiceProvider);
    _configService = ref.watch(atlasAiConfigServiceProvider);
    final AtlasAiRemoteConfig cfg = _configService.currentConfig;
    Future<void>.microtask(initialize);
    return AtlasHybridAiState(
      selectedMode: cfg.defaultHybridMode,
      activeTemplateId: cfg.setAutoregulationTemplateId,
      useServerPromptTemplates: cfg.useServerPromptTemplates,
      configSource: cfg.configSource,
    );
  }

  /// Toggles Firebase AI Logic Server Prompt Templates (`templateGenerativeModel`) on or off.
  void toggleServerPromptTemplates() {
    setUseServerPromptTemplates(!state.useServerPromptTemplates);
  }

  /// Sets whether Firebase AI Logic Server Prompt Templates (`templateGenerativeModel`) are enabled.
  void setUseServerPromptTemplates(bool enabled) {
    _configService.setUseServerPromptTemplates(enabled);
    state = state.copyWith(
      useServerPromptTemplates: enabled,
      activeTemplateId: _configService.currentConfig.setAutoregulationTemplateId,
      configSource: _configService.currentConfig.configSource,
    );
  }

  /// Queries Android AICore for Gemini Nano availability and warms up the model into RAM if ready.
  Future<void> initialize() async {
    final OnDeviceModelStatus status = await _service.checkOnDeviceStatus();
    if (!ref.mounted) {
      return;
    }
    bool warmed = false;
    if (status == OnDeviceModelStatus.available) {
      warmed = await _service.warmUpOnDeviceModel();
      if (!ref.mounted) {
        return;
      }
    }
    state = state.copyWith(modelStatus: status, isWarmedUp: warmed);
  }

  /// Triggers an on-device Gemini Nano download via AICore and warms up the model once available.
  Future<void> triggerModelDownload() async {
    state = state.copyWith(isLoading: true, modelStatus: OnDeviceModelStatus.downloading, clearError: true);
    final OnDeviceModelStatus updatedStatus = await _service.downloadOnDeviceModel();
    if (!ref.mounted) {
      return;
    }
    bool warmed = state.isWarmedUp;
    if (updatedStatus == OnDeviceModelStatus.available) {
      warmed = await _service.warmUpOnDeviceModel();
      if (!ref.mounted) {
        return;
      }
    }
    state = state.copyWith(isLoading: false, modelStatus: updatedStatus, isWarmedUp: warmed);
  }

  /// Switches the active [HybridInferenceMode] (`PREFER_ON_DEVICE`, `ONLY_ON_DEVICE`, `PREFER_IN_CLOUD`, `ONLY_IN_CLOUD`).
  void setInferenceMode(HybridInferenceMode mode) {
    final bool isUnavailableOnlyOnDevice = mode == HybridInferenceMode.onlyOnDevice && state.modelStatus != OnDeviceModelStatus.available;
    state = state.copyWith(
      selectedMode: mode,
      errorMessage: isUnavailableOnlyOnDevice ? t.hybridAi.errorOnlyOnDeviceUnavailable(status: state.modelStatus.name) : null,
      clearError: !isUnavailableOnlyOnDevice,
    );
  }

  /// Parses a natural-language workout set log and prescribes the next set load/rest.
  Future<void> analyzeSetLog(String rawSetText, {List<ExerciseModel> catalog = const <ExerciseModel>[], ExerciseModel? activeExercise}) async {
    final String trimmed = rawSetText.trim();
    if (trimmed.isEmpty) {
      return;
    }

    final List<ExerciseModel> resolvedCatalog = catalog.isNotEmpty ? catalog : _resolveStoredCatalogSafely();
    state = state.copyWith(isLoading: true, clearError: true);

    try {
      if (state.modelStatus == OnDeviceModelStatus.downloading || state.modelStatus == OnDeviceModelStatus.downloadable) {
        final OnDeviceModelStatus refreshedStatus = await _service.checkOnDeviceStatus();
        if (!ref.mounted) {
          return;
        }
        if (refreshedStatus != state.modelStatus) {
          state = state.copyWith(modelStatus: refreshedStatus);
        }
      }
      final HybridSetLogAnalysis analysis = await _service.analyzeSetOfflineFirst(
        rawSetText: trimmed,
        catalog: resolvedCatalog,
        activeExercise: activeExercise,
        mode: state.selectedMode,
      );
      if (!ref.mounted) {
        return;
      }
      state = state.copyWith(
        isLoading: false,
        lastSetAnalysis: analysis,
        lastInferenceSource: analysis.inferenceSource,
        lastModelUsed: analysis.modelUsed,
        lastLatencyMs: analysis.latencyMs,
        lastUsedFallback: analysis.usedFallback,
        clearError: true,
      );
    } catch (error) {
      if (!ref.mounted) {
        return;
      }
      state = state.copyWith(isLoading: false, errorMessage: error.toString());
    }
  }

  /// Executes a single-image + text multimodal request through the hybrid pipeline.
  Future<void> scanEquipmentSample({String? customPrompt, Uint8List? imageBytes, bool openCamera = false}) async {
    state = state.copyWith(isLoading: true, clearError: true);

    Uint8List? resolvedBytes = imageBytes;
    if (openCamera && (resolvedBytes == null || resolvedBytes.isEmpty) && _service is! FakeAtlasHybridAiService) {
      try {
        final Uint8List? captured = await _cameraChannel.invokeMethod<Uint8List>('captureEquipmentPhoto');
        if (!ref.mounted) {
          return;
        }
        if (captured != null) {
          if (captured.isEmpty) {
            state = state.copyWith(isLoading: false);
            return;
          }
          resolvedBytes = captured;
        }
      } on MissingPluginException {
        resolvedBytes = defaultSampleEquipmentPng;
      } on PlatformException {
        resolvedBytes = defaultSampleEquipmentPng;
      }
    }

    final String langCode = LocaleSettings.currentLocale.languageCode;
    final String languageName = switch (LocaleSettings.currentLocale) {
      AppLocale.es => 'Spanish (Español)',
      AppLocale.ca => 'Catalan (Català)',
      AppLocale.fr => 'French (Français)',
      AppLocale.pt => 'Portuguese (Português)',
      AppLocale.en => 'English',
    };
    final String basePrompt = (customPrompt != null && customPrompt.trim().isNotEmpty)
        ? customPrompt.trim()
        : 'Identify the gym equipment in this frame, list primary muscles worked, and prescribe 3 hypertrophy sets.';
    final String effectivePrompt =
        '$basePrompt\n'
        'IMPORTANT: Respond strictly in $languageName (locale: $langCode).';
    final Uint8List effectiveImage = (resolvedBytes != null && resolvedBytes.isNotEmpty) ? resolvedBytes : defaultSampleEquipmentPng;

    try {
      if (state.modelStatus == OnDeviceModelStatus.downloading || state.modelStatus == OnDeviceModelStatus.downloadable) {
        final OnDeviceModelStatus refreshedStatus = await _service.checkOnDeviceStatus();
        if (!ref.mounted) {
          return;
        }
        if (refreshedStatus != state.modelStatus) {
          state = state.copyWith(modelStatus: refreshedStatus);
        }
      }
      final HybridAiResponse response = await _service.generateHybridContent(
        HybridAiRequest(
          prompt: effectivePrompt,
          systemInstruction:
              'You are ATLAS, an elite strength & biomechanics coach. '
              'Provide a concise, actionable 3-set prescription for the pictured equipment in $languageName ($langCode).',
          mode: state.selectedMode,
          cloudModelName: _service.defaultCloudModelName,
          imageBytes: effectiveImage,
          imageMimeType: 'image/png',
          temperature: 0.2,
          maxOutputTokens: 220,
        ),
      );
      if (!ref.mounted) {
        return;
      }
      state = state.copyWith(
        isLoading: false,
        lastVisionResponse: response,
        lastInferenceSource: response.inferenceSource,
        lastModelUsed: response.modelUsed,
        lastLatencyMs: response.latencyMs,
        lastUsedFallback: response.usedFallback,
        clearError: true,
      );
    } catch (error) {
      if (!ref.mounted) {
        return;
      }
      state = state.copyWith(isLoading: false, errorMessage: error.toString());
    }
  }

  List<ExerciseModel> _resolveStoredCatalogSafely() {
    try {
      return ref.read(exerciseRepositoryProvider).getExercises();
    } catch (_) {
      return const <ExerciseModel>[];
    }
  }
}
