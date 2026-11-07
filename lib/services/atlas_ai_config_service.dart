// ignore_for_file: prefer_initializing_formals

// 🎯 Dart imports:
import 'dart:async';

// 📦 Package imports:
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/services/atlas_hybrid_ai_service.dart';

part 'atlas_ai_config_service.g.dart';

/// Immutable over-the-air (OTA) configuration for ATLAS Hybrid AI routing,
/// system instructions, and Server Prompt Templates (`templateGenerativeModel`).
///
/// Mirrors the Firebase Remote Config parameter schema defined in
/// `firebase/remote_config_defaults.json` so prompt governance works across
/// all 3 execution engines: On-Device NPU (offline cached), Gemini Live API,
/// and Cloud Gemini + Dotprompt Server Prompt Templates.
class AtlasAiRemoteConfig {
  const AtlasAiRemoteConfig({
    this.cloudModelName = 'gemini-3.8-flash',
    this.chatModelName = 'gemini-3.8-flash',
    this.liveModelName = 'gemini-3.8-live',
    this.defaultHybridMode = HybridInferenceMode.preferOnDevice,
    this.useServerPromptTemplates = true,
    this.setAutoregulationTemplateId = 'atlas-set-autoregulation-v1-0-0',
    this.equipmentVisionTemplateId = 'atlas-equipment-vision-v1-0-0',
    this.coachChatTemplateId = 'atlas-coach-chat-v1-0-0',
    this.coachSystemPrompt = defaultCoachSystemPrompt,
    this.hybridSetPromptTemplate = defaultHybridSetPromptTemplate,
    this.configSource = 'in_app_defaults',
  });

  static const String defaultCoachSystemPrompt =
      'You are ATLAS, an elite strength, hypertrophy, and biomechanics AI coach. '
      'Prioritize joint safety, eccentric control, RPE-based autoregulation, and progressive overload.';

  static const String defaultHybridSetPromptTemplate =
      'Analyze this strength training set log and return JSON matching the schema:\n'
      'Raw set log: "{{rawSetText}}"\n'
      'Active exercise context: "{{activeExerciseName}}" (id: "{{activeExerciseId}}")\n'
      'Available exercise catalog: [{{catalogContext}}]';

  final String cloudModelName;
  final String chatModelName;
  final String liveModelName;
  final HybridInferenceMode defaultHybridMode;
  final bool useServerPromptTemplates;
  final String setAutoregulationTemplateId;
  final String equipmentVisionTemplateId;
  final String coachChatTemplateId;
  final String coachSystemPrompt;
  final String hybridSetPromptTemplate;
  final String configSource;

  /// Renders the OTA hybrid set prompt by substituting template placeholders.
  String renderHybridSetPrompt({
    required String rawSetText,
    required String catalogContext,
    String? activeExerciseName,
    String? activeExerciseId,
  }) {
    return hybridSetPromptTemplate
        .replaceAll('{{rawSetText}}', rawSetText)
        .replaceAll('{{catalogContext}}', catalogContext)
        .replaceAll('{{activeExerciseName}}', activeExerciseName ?? 'none')
        .replaceAll('{{activeExerciseId}}', activeExerciseId ?? '');
  }

  AtlasAiRemoteConfig copyWith({
    String? cloudModelName,
    String? chatModelName,
    String? liveModelName,
    HybridInferenceMode? defaultHybridMode,
    bool? useServerPromptTemplates,
    String? setAutoregulationTemplateId,
    String? equipmentVisionTemplateId,
    String? coachChatTemplateId,
    String? coachSystemPrompt,
    String? hybridSetPromptTemplate,
    String? configSource,
  }) {
    return AtlasAiRemoteConfig(
      cloudModelName: cloudModelName ?? this.cloudModelName,
      chatModelName: chatModelName ?? this.chatModelName,
      liveModelName: liveModelName ?? this.liveModelName,
      defaultHybridMode: defaultHybridMode ?? this.defaultHybridMode,
      useServerPromptTemplates: useServerPromptTemplates ?? this.useServerPromptTemplates,
      setAutoregulationTemplateId: setAutoregulationTemplateId ?? this.setAutoregulationTemplateId,
      equipmentVisionTemplateId: equipmentVisionTemplateId ?? this.equipmentVisionTemplateId,
      coachChatTemplateId: coachChatTemplateId ?? this.coachChatTemplateId,
      coachSystemPrompt: coachSystemPrompt ?? this.coachSystemPrompt,
      hybridSetPromptTemplate: hybridSetPromptTemplate ?? this.hybridSetPromptTemplate,
      configSource: configSource ?? this.configSource,
    );
  }

  factory AtlasAiRemoteConfig.fromMap(Map<String, dynamic> map, {String source = 'ota_remote_config'}) {
    final String rawMode = (map['atlas_default_hybrid_mode'] ?? 'preferOnDevice').toString().trim();
    final HybridInferenceMode parsedMode = switch (rawMode) {
      'onlyOnDevice' || 'ONLY_ON_DEVICE' => HybridInferenceMode.onlyOnDevice,
      'preferInCloud' || 'PREFER_IN_CLOUD' => HybridInferenceMode.preferInCloud,
      'onlyInCloud' || 'ONLY_IN_CLOUD' => HybridInferenceMode.onlyInCloud,
      _ => HybridInferenceMode.preferOnDevice,
    };

    return AtlasAiRemoteConfig(
      cloudModelName: (map['atlas_cloud_model_name'] ?? 'gemini-3.8-flash').toString().trim(),
      chatModelName: (map['atlas_chat_model_name'] ?? 'gemini-3.8-flash').toString().trim(),
      liveModelName: (map['atlas_live_model_name'] ?? 'gemini-3.8-live').toString().trim(),
      defaultHybridMode: parsedMode,
      useServerPromptTemplates: map['atlas_use_server_templates'] is! bool || (map['atlas_use_server_templates'] as bool),
      setAutoregulationTemplateId: (map['atlas_set_autoregulation_template_id'] ?? 'atlas-set-autoregulation-v1-0-0').toString().trim(),
      equipmentVisionTemplateId: (map['atlas_equipment_vision_template_id'] ?? 'atlas-equipment-vision-v1-0-0').toString().trim(),
      coachChatTemplateId: (map['atlas_coach_chat_template_id'] ?? 'atlas-coach-chat-v1-0-0').toString().trim(),
      coachSystemPrompt: (map['atlas_coach_system_prompt'] ?? defaultCoachSystemPrompt).toString().trim(),
      hybridSetPromptTemplate: (map['atlas_hybrid_set_prompt_template'] ?? defaultHybridSetPromptTemplate).toString().trim(),
      configSource: source,
    );
  }
}

/// Application-owned contract for dynamic AI model routing and OTA prompt governance
/// (`flutter-sdk-contracts`).
abstract interface class AtlasAiConfigService {
  /// Synchronously returns the active cached [AtlasAiRemoteConfig].
  AtlasAiRemoteConfig get currentConfig;

  /// Returns the current [AtlasAiRemoteConfig], fetching from remote if not yet loaded.
  Future<AtlasAiRemoteConfig> getConfig();

  /// Refreshes the configuration from Firebase OTA storage with offline-safe fallback.
  Future<AtlasAiRemoteConfig> refreshConfig();

  /// Enables or disables Firebase AI Logic Server Prompt Templates (`templateGenerativeModel`).
  void setUseServerPromptTemplates(bool enabled);

  /// Applies an over-the-air config override (used for live judge demos and unit testing).
  void updateOtaConfigOverride(AtlasAiRemoteConfig override);
}

/// Signature for an injectable remote config fetcher returning parameter key-value pairs.
typedef RemoteConfigMapFetcher = Future<Map<String, dynamic>?> Function();

/// Production implementation of [AtlasAiConfigService] backed by in-app defaults and
/// Firebase OTA parameter sync (`remote_config/atlas_ai_logic`).
class AppAtlasAiConfigService implements AtlasAiConfigService {
  AppAtlasAiConfigService({
    AtlasAiRemoteConfig? initialConfig,
    RemoteConfigMapFetcher? remoteFetcher,
  }) : _config = initialConfig ?? const AtlasAiRemoteConfig(),
       _remoteFetcher = remoteFetcher;

  AtlasAiRemoteConfig _config;
  final RemoteConfigMapFetcher? _remoteFetcher;

  @override
  AtlasAiRemoteConfig get currentConfig => _config;

  @override
  Future<AtlasAiRemoteConfig> getConfig() async => _config;

  @override
  Future<AtlasAiRemoteConfig> refreshConfig() async {
    try {
      final Map<String, dynamic>? remoteMap = _remoteFetcher != null ? await _remoteFetcher() : await _fetchFromFirestoreRemoteConfigDoc();
      if (remoteMap != null && remoteMap.isNotEmpty) {
        _config = AtlasAiRemoteConfig.fromMap(remoteMap, source: 'ota_remote_config');
      }
    } catch (_) {
      // Offline or unauthenticated: preserve cached/in-app default configuration.
    }
    return _config;
  }

  Future<Map<String, dynamic>?> _fetchFromFirestoreRemoteConfigDoc() async {
    if (Firebase.apps.isEmpty) {
      return null;
    }
    final DocumentSnapshot<Map<String, dynamic>> snapshot = await FirebaseFirestore.instance
        .collection('app_config')
        .doc('atlas_ai_remote_config')
        .get()
        .timeout(const Duration(seconds: 2));
    return snapshot.data();
  }

  @override
  void setUseServerPromptTemplates(bool enabled) {
    _config = _config.copyWith(useServerPromptTemplates: enabled);
  }

  @override
  void updateOtaConfigOverride(AtlasAiRemoteConfig override) {
    _config = override;
  }
}

/// Deterministic fake implementation of [AtlasAiConfigService] for unit and widget tests.
class FakeAtlasAiConfigService implements AtlasAiConfigService {
  FakeAtlasAiConfigService({
    AtlasAiRemoteConfig? initialConfig,
  }) : _config = initialConfig ?? const AtlasAiRemoteConfig();

  AtlasAiRemoteConfig _config;
  int refreshCallCount = 0;

  @override
  AtlasAiRemoteConfig get currentConfig => _config;

  @override
  Future<AtlasAiRemoteConfig> getConfig() async => _config;

  @override
  Future<AtlasAiRemoteConfig> refreshConfig() async {
    refreshCallCount += 1;
    return _config;
  }

  @override
  void setUseServerPromptTemplates(bool enabled) {
    _config = _config.copyWith(useServerPromptTemplates: enabled);
  }

  @override
  void updateOtaConfigOverride(AtlasAiRemoteConfig override) {
    _config = override;
  }
}

@Riverpod(keepAlive: true)
AtlasAiConfigService atlasAiConfigService(Ref ref) {
  return AppAtlasAiConfigService();
}
