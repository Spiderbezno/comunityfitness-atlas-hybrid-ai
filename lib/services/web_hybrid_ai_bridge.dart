// 🌎 Project imports:
import 'package:comunityfitness/services/atlas_hybrid_ai_service.dart';

import 'package:comunityfitness/services/web_hybrid_ai_bridge_stub.dart'
    if (dart.library.js_interop) 'package:comunityfitness/services/web_hybrid_ai_bridge_web.dart' as impl;

/// Application-owned contract for Web on-device inference via the Chrome Built-in AI Prompt API
/// (`LanguageModel` / `window.ai.languageModel` backing Firebase AI Logic Hybrid on Web).
abstract interface class WebHybridAiBridge {
  /// Whether the current runtime is a Web platform supporting JS interop.
  bool get isWebPlatform;

  /// Checks Chrome's Built-in AI (`LanguageModel.availability()`) on-device status.
  Future<OnDeviceModelStatus> checkOnDeviceStatus();

  /// Triggers on-device Gemini Nano model download in Chrome via `LanguageModel.create()`.
  Future<OnDeviceModelStatus> downloadOnDeviceModel();

  /// Warms up a Chrome `LanguageModel` session in memory.
  Future<bool> warmUpOnDeviceModel();

  /// Executes a single-turn prompt on Chrome's built-in Gemini Nano model.
  Future<String> generateOnDeviceText({
    required String prompt,
    String? systemInstruction,
    String? responseJsonSchema,
    double? temperature,
  });
}

/// Creates the platform-appropriate [WebHybridAiBridge] implementation.
WebHybridAiBridge createWebHybridAiBridge() => impl.createPlatformWebHybridAiBridge();

/// Deterministic fake implementation of [WebHybridAiBridge] for unit tests.
class FakeWebHybridAiBridge implements WebHybridAiBridge {
  FakeWebHybridAiBridge({
    this.isWebPlatform = false,
    this.status = OnDeviceModelStatus.available,
    this.shouldThrowOnGenerate = false,
    this.customResponseText,
  });

  @override
  final bool isWebPlatform;

  OnDeviceModelStatus status;
  bool shouldThrowOnGenerate;
  String? customResponseText;
  int generateCallCount = 0;

  @override
  Future<OnDeviceModelStatus> checkOnDeviceStatus() async => status;

  @override
  Future<OnDeviceModelStatus> downloadOnDeviceModel() async {
    status = OnDeviceModelStatus.available;
    return status;
  }

  @override
  Future<bool> warmUpOnDeviceModel() async => status == OnDeviceModelStatus.available;

  @override
  Future<String> generateOnDeviceText({
    required String prompt,
    String? systemInstruction,
    String? responseJsonSchema,
    double? temperature,
  }) async {
    generateCallCount += 1;
    if (shouldThrowOnGenerate || status != OnDeviceModelStatus.available) {
      throw StateError('Chrome Prompt API LanguageModel is unavailable or failed.');
    }
    return customResponseText ?? 'Chrome Gemini Nano on-device response for: $prompt';
  }
}
