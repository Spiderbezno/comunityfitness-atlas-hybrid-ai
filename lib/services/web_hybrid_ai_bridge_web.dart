// 🎯 Dart imports:
import 'dart:convert';
import 'dart:js_interop';
import 'dart:js_interop_unsafe';

// 🌎 Project imports:
import 'package:comunityfitness/services/atlas_hybrid_ai_service.dart';
import 'package:comunityfitness/services/web_hybrid_ai_bridge.dart';

class _BrowserWebHybridAiBridge implements WebHybridAiBridge {
  _BrowserWebHybridAiBridge();

  JSObject? _cachedSession;

  @override
  bool get isWebPlatform => true;

  JSObject? _resolveLanguageModelFactory() {
    final JSAny? topLevel = globalContext['LanguageModel'];
    if (topLevel != null && !topLevel.isUndefinedOrNull && topLevel.isA<JSObject>()) {
      return topLevel as JSObject;
    }
    final JSAny? aiNamespace = globalContext['ai'];
    if (aiNamespace != null && !aiNamespace.isUndefinedOrNull && aiNamespace.isA<JSObject>()) {
      final JSAny? legacyLm = (aiNamespace as JSObject)['languageModel'];
      if (legacyLm != null && !legacyLm.isUndefinedOrNull && legacyLm.isA<JSObject>()) {
        return legacyLm as JSObject;
      }
    }
    return null;
  }

  OnDeviceModelStatus _mapAvailabilityString(String raw) {
    final String normalized = raw.trim().toLowerCase();
    return switch (normalized) {
      'available' || 'readily' => OnDeviceModelStatus.available,
      'downloadable' || 'after-download' => OnDeviceModelStatus.downloadable,
      'downloading' => OnDeviceModelStatus.downloading,
      _ => OnDeviceModelStatus.unavailable,
    };
  }

  @override
  Future<OnDeviceModelStatus> checkOnDeviceStatus() async {
    try {
      final JSObject? factory = _resolveLanguageModelFactory();
      if (factory == null) {
        return OnDeviceModelStatus.unavailable;
      }

      if (factory.has('availability')) {
        final JSPromise<JSAny?> promise = factory.callMethod<JSPromise<JSAny?>>('availability'.toJS);
        final JSAny? result = await promise.toDart;
        if (result != null && result.isA<JSString>()) {
          return _mapAvailabilityString((result as JSString).toDart);
        }
      }

      if (factory.has('capabilities')) {
        final JSPromise<JSAny?> promise = factory.callMethod<JSPromise<JSAny?>>('capabilities'.toJS);
        final JSAny? caps = await promise.toDart;
        if (caps != null && !caps.isUndefinedOrNull && caps.isA<JSObject>()) {
          final JSAny? availableProp = (caps as JSObject)['available'];
          if (availableProp != null && availableProp.isA<JSString>()) {
            return _mapAvailabilityString((availableProp as JSString).toDart);
          }
        }
      }
      return OnDeviceModelStatus.unavailable;
    } catch (_) {
      return OnDeviceModelStatus.unavailable;
    }
  }

  Future<JSObject?> _createSession({String? systemInstruction, double? temperature}) async {
    final JSObject? factory = _resolveLanguageModelFactory();
    if (factory == null || !factory.has('create')) {
      return null;
    }

    final Map<String, Object?> createOptions = <String, Object?>{};
    if (systemInstruction != null && systemInstruction.trim().isNotEmpty) {
      createOptions['systemPrompt'] = systemInstruction.trim();
      createOptions['initialPrompts'] = <Map<String, String>>[
        <String, String>{'role': 'system', 'content': systemInstruction.trim()},
      ];
    }
    if (temperature != null) {
      createOptions['temperature'] = temperature;
      createOptions['topK'] = 3;
    }

    final JSAny? jsOptions = createOptions.isEmpty ? null : createOptions.jsify();
    final JSPromise<JSAny?> promise = jsOptions != null
        ? factory.callMethod<JSPromise<JSAny?>>('create'.toJS, jsOptions)
        : factory.callMethod<JSPromise<JSAny?>>('create'.toJS);
    final JSAny? session = await promise.toDart;
    if (session != null && !session.isUndefinedOrNull && session.isA<JSObject>()) {
      return session as JSObject;
    }
    return null;
  }

  @override
  Future<OnDeviceModelStatus> downloadOnDeviceModel() async {
    try {
      final JSObject? session = await _createSession();
      if (session != null) {
        _cachedSession = session;
        return OnDeviceModelStatus.available;
      }
      return await checkOnDeviceStatus();
    } catch (_) {
      return OnDeviceModelStatus.unavailable;
    }
  }

  @override
  Future<bool> warmUpOnDeviceModel() async {
    try {
      _cachedSession ??= await _createSession();
      return _cachedSession != null;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<String> generateOnDeviceText({
    required String prompt,
    String? systemInstruction,
    String? responseJsonSchema,
    double? temperature,
  }) async {
    final JSObject? session = (systemInstruction == null && temperature == null && _cachedSession != null)
        ? _cachedSession
        : await _createSession(systemInstruction: systemInstruction, temperature: temperature);
    if (session == null) {
      throw StateError('Chrome Prompt API LanguageModel session could not be created.');
    }

    final Map<String, Object?> promptOptions = <String, Object?>{};
    String effectivePrompt = prompt;
    if (responseJsonSchema != null && responseJsonSchema.trim().isNotEmpty) {
      try {
        final Object? decodedSchema = jsonDecode(responseJsonSchema);
        if (decodedSchema != null) {
          promptOptions['responseConstraint'] = decodedSchema;
        }
      } catch (_) {
        effectivePrompt = '$prompt\n\nRespond ONLY with valid JSON matching this schema:\n$responseJsonSchema';
      }
    }

    final JSPromise<JSAny?> responsePromise = promptOptions.isNotEmpty
        ? session.callMethod<JSPromise<JSAny?>>('prompt'.toJS, effectivePrompt.toJS, promptOptions.jsify())
        : session.callMethod<JSPromise<JSAny?>>('prompt'.toJS, effectivePrompt.toJS);

    final JSAny? rawResult = await responsePromise.toDart;
    if (rawResult != null && rawResult.isA<JSString>()) {
      return (rawResult as JSString).toDart.trim();
    }
    throw StateError('Chrome Prompt API returned an empty or non-string response.');
  }
}

WebHybridAiBridge createPlatformWebHybridAiBridge() => _BrowserWebHybridAiBridge();
