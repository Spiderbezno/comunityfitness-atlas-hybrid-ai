// Pigeon schema definition for strongly-typed ATLAS Hybrid AI (On-Device Gemini Nano + Cloud Gemini).
// Run `dart run pigeon --input pigeons/atlas_hybrid_ai_api.dart` to regenerate bindings.

// 🎯 Dart imports:
import 'dart:typed_data';

/// Hybrid inference execution policy mirrored to Firebase AI Logic `InferenceMode`.
enum PigeonHybridInferenceMode {
  /// Attempt on-device Gemini Nano first; fall back to cloud Gemini if unavailable.
  preferOnDevice,

  /// Strictly execute on-device via AICore / ML Kit GenAI Prompt API; throw if unavailable.
  onlyOnDevice,

  /// Attempt cloud Gemini first; fall back to on-device Gemini Nano when offline.
  preferInCloud,

  /// Strictly execute in cloud via Gemini Developer API; throw if offline.
  onlyInCloud,
}

/// Availability state of the on-device Gemini Nano model managed by Android AICore.
enum PigeonOnDeviceModelStatus {
  /// Hardware or OS does not support AICore / Gemini Nano on-device inference.
  unavailable,

  /// Device supports Gemini Nano, and weights can be downloaded via AICore.
  downloadable,

  /// Model weights are currently downloading in the background via AICore.
  downloading,

  /// Model weights are downloaded and ready for zero-latency local inference.
  available,
}

/// Telemetry source indicating where the inference actually executed.
enum PigeonInferenceSource {
  /// Executed locally on the device NPU/GPU via Gemini Nano (`InferenceSource.ON_DEVICE`).
  onDevice,

  /// Executed in the cloud via Firebase AI Logic (`InferenceSource.IN_CLOUD`).
  inCloud,

  /// Executed via deterministic local domain rules when both NPU and network are unavailable.
  localOfflineFallback,
}

/// Request payload for hybrid text or single-image multimodal generation.
class PigeonHybridAiRequest {
  const PigeonHybridAiRequest({
    required this.prompt,
    this.systemInstruction,
    required this.mode,
    required this.cloudModelName,
    this.imageBytes,
    this.imageMimeType,
    this.responseJsonSchema,
    this.temperature,
    this.maxOutputTokens,
  });

  final String prompt;
  final String? systemInstruction;
  final PigeonHybridInferenceMode mode;
  final String cloudModelName;
  final Uint8List? imageBytes;
  final String? imageMimeType;
  final String? responseJsonSchema;
  final double? temperature;
  final int? maxOutputTokens;
}

/// Strongly-typed response from hybrid inference including execution telemetry.
class PigeonHybridAiResponse {
  const PigeonHybridAiResponse({
    required this.text,
    required this.inferenceSource,
    required this.modelUsed,
    required this.latencyMs,
    required this.usedFallback,
    this.fallbackReason,
  });

  final String text;
  final PigeonInferenceSource inferenceSource;
  final String modelUsed;
  final int latencyMs;
  final bool usedFallback;
  final String? fallbackReason;
}

/// Host API implemented by Android (`com.google.firebase:firebase-ai` + `firebase-ai-ondevice`)
/// and iOS safe fallback handler.
abstract class AtlasHybridAiHostApi {
  /// Queries `FirebaseAIOnDevice.checkStatus()` to inspect local Gemini Nano availability.
  Future<PigeonOnDeviceModelStatus> checkOnDeviceStatus();

  /// Triggers `FirebaseAIOnDevice.download()` and returns the resulting model status.
  Future<PigeonOnDeviceModelStatus> downloadOnDeviceModel();

  /// Warms up the on-device Gemini Nano model into memory for low-latency first token.
  Future<bool> warmUpOnDeviceModel();

  /// Executes single-turn text or single-image + text generation using the requested [PigeonHybridInferenceMode].
  Future<PigeonHybridAiResponse> generateHybridContent(
    PigeonHybridAiRequest request,
  );
}
