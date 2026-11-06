// 🌎 Project imports:
import 'package:comunityfitness/services/atlas_hybrid_ai_service.dart';
import 'package:comunityfitness/services/web_hybrid_ai_bridge.dart';

class _StubWebHybridAiBridge implements WebHybridAiBridge {
  const _StubWebHybridAiBridge();

  @override
  bool get isWebPlatform => false;

  @override
  Future<OnDeviceModelStatus> checkOnDeviceStatus() async => OnDeviceModelStatus.unavailable;

  @override
  Future<OnDeviceModelStatus> downloadOnDeviceModel() async => OnDeviceModelStatus.unavailable;

  @override
  Future<bool> warmUpOnDeviceModel() async => false;

  @override
  Future<String> generateOnDeviceText({
    required String prompt,
    String? systemInstruction,
    String? responseJsonSchema,
    double? temperature,
  }) {
    throw UnsupportedError('Chrome Prompt API is only available on Web.');
  }
}

WebHybridAiBridge createPlatformWebHybridAiBridge() => const _StubWebHybridAiBridge();
