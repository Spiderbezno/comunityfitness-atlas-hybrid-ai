// 🎯 Dart imports:
import 'dart:async';
import 'dart:convert';

// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/ai_coach_models.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/pigeon/live_coach_audio_api.g.dart';
import 'package:comunityfitness/services/ai_coach_service.dart';

class FakeLiveCoachAudioHostApi implements LiveCoachAudioHostApi {
  final List<String> playedPcmChunks = <String>[];
  final List<String> spokenTexts = <String>[];
  final List<String> configuredLanguages = <String>[];
  int stopCount = 0;
  int startMicCaptureCount = 0;
  int stopMicCaptureCount = 0;
  String nextRecognizedTranscript = '';

  @override
  Future<bool> playPcm24k(String base64Pcm, int sampleRate) async {
    playedPcmChunks.add('$sampleRate:$base64Pcm');
    return true;
  }

  @override
  Future<bool> speak(String text) async {
    spokenTexts.add(text);
    return false;
  }

  @override
  Future<bool> stop() async {
    stopCount++;
    return true;
  }

  @override
  Future<bool> startMicCapture() async {
    startMicCaptureCount++;
    return true;
  }

  @override
  Future<String> stopMicCapture() async {
    stopMicCaptureCount++;
    return nextRecognizedTranscript;
  }

  @override
  Future<bool> setLanguage(String languageCode) async {
    configuredLanguages.add(languageCode);
    return true;
  }
}

class FakeLiveBidiWebSocket implements LiveBidiWebSocket {
  final StreamController<dynamic> serverToClientController = StreamController<dynamic>.broadcast();
  final List<Map<String, dynamic>> sentPayloads = <Map<String, dynamic>>[];
  bool isClosed = false;

  @override
  Stream<dynamic> get messages => serverToClientController.stream;

  @override
  void sendJson(Map<String, dynamic> payload) {
    sentPayloads.add(payload);
  }

  void pushServerFrame(Map<String, dynamic> frame) {
    serverToClientController.add(jsonEncode(frame));
  }

  @override
  Future<void> close() async {
    isClosed = true;
    await serverToClientController.close();
  }
}

class FakeCloudLiveBidiWebSocket extends FakeLiveBidiWebSocket implements CloudLiveBidiWebSocket {}

void main() {
  const sampleCatalog = <Exercise>[
    Exercise(
      id: 'bench_press',
      name: 'Bench Press',
      primaryMuscleGroup: 'Chest',
      equipment: 'Barbell',
      animationType: 'rive',
      animationPath: 'assets/animations/bench_press.riv',
      description: 'Barbell chest press.',
    ),
    Exercise(
      id: 'push_up',
      name: 'Push Up',
      primaryMuscleGroup: 'Chest',
      equipment: 'Bodyweight',
      animationType: 'rive',
      animationPath: 'assets/animations/push_up.riv',
      description: 'Bodyweight chest press.',
    ),
    Exercise(
      id: 'pull_up',
      name: 'Pull Up',
      primaryMuscleGroup: 'Back',
      equipment: 'Bodyweight',
      animationType: 'movekit',
      animationPath: 'assets/animations/pull_up.movekit',
      description: 'Bodyweight vertical back pull.',
    ),
  ];

  group('FirebaseAiGoogleClient Fail-Closed App Check & Auth Enforcement', () {
    test('returns null immediately without making any HTTP request when appCheckTokenProvider returns null or empty', () async {
      var httpRequestsSent = 0;

      for (final invalidAppCheck in <String?>[null, '', '  ']) {
        final client = FirebaseAiGoogleClient(
          appCheckTokenProvider: () async => invalidAppCheck,
          authTokenProvider: () async => 'valid-auth-jwt',
          apiKeyOverride: 'fake-api-key',
          projectIdOverride: 'comunityfitness',
          httpTransport: (uri, headers, body) async {
            httpRequestsSent++;
            return (statusCode: 200, body: '{}');
          },
        );

        final output = await client.generateStructuredText(model: 'gemini-3.8-flash', systemInstruction: 'system', prompt: 'user prompt');

        expect(output, isNull);
        expect(httpRequestsSent, 0);
      }
    });

    test('returns null immediately without making any HTTP request when authTokenProvider returns null or empty', () async {
      var httpRequestsSent = 0;

      for (final invalidAuth in <String?>[null, '', '   ']) {
        final client = FirebaseAiGoogleClient(
          appCheckTokenProvider: () async => 'valid-app-check-jwt',
          authTokenProvider: () async => invalidAuth,
          apiKeyOverride: 'fake-api-key',
          projectIdOverride: 'comunityfitness',
          httpTransport: (uri, headers, body) async {
            httpRequestsSent++;
            return (statusCode: 200, body: '{}');
          },
        );

        final output = await client.generateStructuredText(model: 'gemini-3.8-flash', systemInstruction: 'system', prompt: 'user prompt');

        expect(output, isNull);
        expect(httpRequestsSent, 0);
      }
    });

    test('attaches both X-Firebase-AppCheck and X-Firebase-Auth headers when both tokens are non-empty', () async {
      var httpRequestsSent = 0;
      Map<String, String>? sentHeaders;

      final client = FirebaseAiGoogleClient(
        appCheckTokenProvider: () async => 'attested-app-check-token',
        authTokenProvider: () async => 'authenticated-user-id-token',
        apiKeyOverride: 'fake-api-key',
        projectIdOverride: 'comunityfitness',
        httpTransport: (uri, headers, body) async {
          httpRequestsSent++;
          sentHeaders = headers;
          return (statusCode: 200, body: '{"candidates":[{"content":{"parts":[{"text":"{\\"ok\\":true}"}]}}]}');
        },
      );

      final output = await client.generateStructuredText(model: 'gemini-3.8-flash', systemInstruction: 'system', prompt: 'user prompt');

      expect(output, '{"ok":true}');
      expect(httpRequestsSent, 1);
      expect(sentHeaders, isNotNull);
      expect(sentHeaders!['X-Firebase-AppCheck'], 'attested-app-check-token');
      expect(sentHeaders!['X-Firebase-Auth'], 'authenticated-user-id-token');
    });
  });

  group('Gemini 3.8 Live BidiGenerateContent WebSocket Protocol', () {
    test('connectLiveBidiSession enforces fail-closed App Check + Auth before connecting WebSocket', () async {
      var wsConnectAttempts = 0;

      final missingAppCheckClient = FirebaseAiGoogleClient(
        appCheckTokenProvider: () async => null,
        authTokenProvider: () async => 'valid-auth-token',
        apiKeyOverride: 'fake-api-key',
        projectIdOverride: 'comunityfitness',
        liveWebSocketConnector: (uri, headers) async {
          wsConnectAttempts++;
          return FakeLiveBidiWebSocket();
        },
      );

      final s1 = await missingAppCheckClient.connectLiveBidiSession(model: 'gemini-3.8-live', systemInstruction: 'Coach');
      expect(s1, isNull);
      expect(wsConnectAttempts, 0);

      final missingAuthClient = FirebaseAiGoogleClient(
        appCheckTokenProvider: () async => 'valid-app-check-token',
        authTokenProvider: () async => '',
        apiKeyOverride: 'fake-api-key',
        projectIdOverride: 'comunityfitness',
        liveWebSocketConnector: (uri, headers) async {
          wsConnectAttempts++;
          return FakeLiveBidiWebSocket();
        },
      );

      final s2 = await missingAuthClient.connectLiveBidiSession(model: 'gemini-3.8-live', systemInstruction: 'Coach');
      expect(s2, isNull);
      expect(wsConnectAttempts, 0);
    });

    test('sends setup frame with models/gemini-3.8-live, AUDIO modality, Puck voice, and NON_BLOCKING tools, then streams 24kHz PCM & executes async toolCall', () async {
      late FakeLiveBidiWebSocket fakeSocket;
      Uri? connectedUri;
      Map<String, String>? connectedHeaders;
      final playedPcmChunks = <String>[];
      var stopCalledCount = 0;

      final client = FirebaseAiGoogleClient(
        appCheckTokenProvider: () async => 'live-app-check-token',
        authTokenProvider: () async => 'live-auth-id-token',
        apiKeyOverride: 'fake-api-key',
        projectIdOverride: 'comunityfitness',
        liveWebSocketConnector: (uri, headers) async {
          connectedUri = uri;
          connectedHeaders = headers;
          fakeSocket = FakeLiveBidiWebSocket();
          return fakeSocket;
        },
      );

      final service = FirebaseAiCoachService(
        googleAiClient: client,
        enablePlatformCues: false,
        onPlayPcm24k: (base64Pcm, sampleRate) async {
          expect(sampleRate, 24000);
          playedPcmChunks.add(base64Pcm);
        },
        onStopAudio: () async {
          stopCalledCount++;
        },
      );

      final events = <AiLiveCoachEvent>[];
      final sub = service.liveEvents.listen(events.add);

      // 1. Start session -> connects & sends setup frame
      await service.startLiveCoachSession(catalog: sampleCatalog, activeExercise: sampleCatalog.first);

      expect(connectedUri.toString(), contains('BidiGenerateContent'));
      expect(connectedUri.toString(), isNot(contains('key=')));
      expect(connectedHeaders!['x-goog-api-key'], 'fake-api-key');
      expect(connectedHeaders!['X-Firebase-AppCheck'], 'live-app-check-token');
      expect(connectedHeaders!['X-Firebase-Auth'], 'live-auth-id-token');
      expect(fakeSocket.sentPayloads, isNotEmpty);

      final setupMsg = fakeSocket.sentPayloads.first['setup'] as Map<String, dynamic>;
      expect(setupMsg['model'], 'projects/comunityfitness/locations/us-central1/publishers/google/models/gemini-3.8-live');
      final genConfig = setupMsg['generationConfig'] as Map<String, dynamic>;
      expect(genConfig['responseModalities'], ['AUDIO']);
      final voiceConfig = ((genConfig['speechConfig'] as Map)['voiceConfig'] as Map)['prebuiltVoiceConfig'] as Map;
      expect(voiceConfig['voiceName'], 'Puck');

      final fnDecls = ((setupMsg['tools'] as List).first as Map)['functionDeclarations'] as List;
      expect(fnDecls.every((fn) => (fn as Map)['behavior'] == 'NON_BLOCKING'), isTrue);

      // 2. Send user turn via realtimeInput
      await service.sendLiveVoiceOrTextTurn(
        userUtterance: 'Give me a home no-weights alternative for Bench Press',
        catalog: sampleCatalog,
        activeExercise: sampleCatalog.first,
      );

      expect(fakeSocket.sentPayloads.last, {
        'realtimeInput': {'text': 'Give me a home no-weights alternative for Bench Press'},
      });

      // Also test 16kHz PCM audio chunk + Hybrid VAD audioStreamEnd
      await service.sendLiveAudioChunk(base64Pcm16k: 'AAAA', audioStreamEnd: true);
      expect(fakeSocket.sentPayloads.any((p) => p['realtimeInput'] is Map && (p['realtimeInput'] as Map)['audioStreamEnd'] == true), isTrue);

      // 3. Simulate server streaming conversational filler audio (24kHz PCM) + IN_PROGRESS + toolCall
      fakeSocket.pushServerFrame({
        'interactionStatus': 'IN_PROGRESS',
        'serverContent': {
          'modelTurn': {
            'parts': [
              {
                'inlineData': {'mimeType': 'audio/pcm;rate=24000', 'data': 'UENNMTZDSFVOSzE='},
              },
            ],
          },
          'outputTranscription': {'text': 'Checking your catalog for bodyweight chest swaps... '},
        },
        'toolCall': {
          'functionCalls': [
            {
              'id': 'call-101',
              'name': 'suggest_exercise_alternatives',
              'args': {'exerciseName': 'Bench Press', 'constraint': 'At Home / No Weights'},
            },
          ],
        },
      });

      await Future<void>.delayed(const Duration(milliseconds: 20));

      // Verify 24kHz PCM chunk was played and toolResponse was sent back
      expect(playedPcmChunks, ['UENNMTZDSFVOSzE=']);
      final toolResponseFrame = fakeSocket.sentPayloads.last;
      expect(toolResponseFrame.containsKey('toolResponse'), isTrue);
      final fnResponses = (toolResponseFrame['toolResponse'] as Map)['functionResponses'] as List;
      expect((fnResponses.first as Map)['id'], 'call-101');
      expect((fnResponses.first as Map)['name'], 'suggest_exercise_alternatives');

      // 4. Simulate final audio + turnComplete while interactionStatus transitions to IDLE
      fakeSocket.pushServerFrame({
        'interactionStatus': 'IDLE',
        'serverContent': {
          'modelTurn': {
            'parts': [
              {
                'inlineData': {'mimeType': 'audio/pcm;rate=24000', 'data': 'UENNMTZDSFVOSzI='},
              },
            ],
          },
          'outputTranscription': {'text': 'Switch to Push Up for 3 sets of 15 reps!'},
          'turnComplete': true,
        },
      });

      await Future<void>.delayed(const Duration(milliseconds: 20));

      expect(playedPcmChunks.length, 2);
      expect(service.currentLiveState, AiLiveCoachState.listening);
      expect(events.last.transcript, contains('Switch to Push Up for 3 sets of 15 reps!'));
      expect(events.last.alternatives, isNotEmpty);

      // 5. Simulate barge-in interruption (interrupted: true)
      fakeSocket.pushServerFrame({
        'serverContent': {'interrupted': true},
      });
      await Future<void>.delayed(const Duration(milliseconds: 20));
      expect(stopCalledCount, greaterThanOrEqualTo(1));

      await service.stopLiveCoachSession();
      expect(fakeSocket.isClosed, isTrue);
      await sub.cancel();
    });

    test('prefixes transcript with explicit Offline Fallback notice when BidiGenerateContent WebSocket is unavailable', () async {
      final offlineClient = FirebaseAiGoogleClient(appCheckTokenProvider: () async => null, authTokenProvider: () async => null);
      final service = FirebaseAiCoachService(googleAiClient: offlineClient, enablePlatformCues: false);

      final events = <AiLiveCoachEvent>[];
      final sub = service.liveEvents.listen(events.add);

      await service.startLiveCoachSession(catalog: sampleCatalog);
      await Future<void>.delayed(Duration.zero);

      expect(events.last.transcript, startsWith(FirebaseAiCoachService.offlineFallbackPrefix));

      await sub.cancel();
    });

    test(
      'startLiveMicRecording and stopLiveMicRecording invoke Pigeon LiveCoachAudioHostApi and stream 16kHz PCM via LiveCoachAudioFlutterApi',
      () async {
        late FakeLiveBidiWebSocket fakeSocket;
        final fakeAudioHostApi = FakeLiveCoachAudioHostApi()..nextRecognizedTranscript = 'Give me a home chest alternative';

        final client = FirebaseAiGoogleClient(
          appCheckTokenProvider: () async => 'live-app-check-token',
          authTokenProvider: () async => 'live-auth-id-token',
          apiKeyOverride: 'fake-api-key',
          projectIdOverride: 'comunityfitness',
          liveWebSocketConnector: (uri, headers) async {
            fakeSocket = FakeLiveBidiWebSocket();
            return fakeSocket;
          },
        );

        final service = FirebaseAiCoachService(googleAiClient: client, audioHostApi: fakeAudioHostApi, enablePlatformCues: true);

        final events = <AiLiveCoachEvent>[];
        final sub = service.liveEvents.listen(events.add);

        final started = await service.startLiveMicRecording(catalog: sampleCatalog, activeExercise: sampleCatalog.first);
        expect(started, isTrue);
        expect(service.isMicRecording, isTrue);
        expect(fakeAudioHostApi.startMicCaptureCount, 1);

        // Simulate Pigeon LiveCoachAudioFlutterApi callback delivering 16kHz PCM chunk
        service.onMicPcm16kChunk('UENNMTZL');
        await Future<void>.delayed(Duration.zero);

        expect(
          fakeSocket.sentPayloads.any((p) => p['realtimeInput'] is Map && ((p['realtimeInput'] as Map)['audio'] as Map?)?['data'] == 'UENNMTZL'),
          isTrue,
        );

        final transcript = await service.stopLiveMicRecording(catalog: sampleCatalog, activeExercise: sampleCatalog.first);
        expect(service.isMicRecording, isFalse);
        expect(fakeAudioHostApi.stopMicCaptureCount, 1);
        expect(transcript, 'Give me a home chest alternative');

        await service.stopLiveCoachSession();
        await sub.cancel();
      },
    );

    test('supports multi-language (es, ca, fr, pt, en) in microphone speech recognition and AI Coach responses', () async {
      LocaleSettings.setLocale(AppLocale.es);
      addTearDown(() => LocaleSettings.setLocale(AppLocale.en));

      final fakeAudioHostApi = FakeLiveCoachAudioHostApi()..nextRecognizedTranscript = 'Dame una rutina de pecho y espalda en casa sin pesas';
      final offlineClient = FirebaseAiGoogleClient(appCheckTokenProvider: () async => null, authTokenProvider: () async => null);
      final service = FirebaseAiCoachService(googleAiClient: offlineClient, audioHostApi: fakeAudioHostApi, enablePlatformCues: true);

      await service.startLiveMicRecording(catalog: sampleCatalog);
      expect(fakeAudioHostApi.configuredLanguages, contains('es-ES'));

      final transcript = await service.stopLiveMicRecording(catalog: sampleCatalog);
      expect(transcript, 'Dame una rutina de pecho y espalda en casa sin pesas');

      final reply = await service.sendCoachMessage(
        message: 'Dame una alternativa en casa sin pesas para Bench Press',
        history: const [],
        catalog: sampleCatalog,
        contextExercise: sampleCatalog.first,
      );
      expect(reply.text, contains('Aquí tienes las mejores alternativas'));
      expect(reply.alternatives, isNotEmpty);

      // Verify Catalan, French, and Portuguese muscle & constraint extraction
      expect(FirebaseAiCoachService.extractTargetMusclesFromText('Vull entrenar pit i esquena a casa'), containsAll(['Chest', 'Back']));
      expect(
        FirebaseAiCoachService.extractTargetMusclesFromText('Entraînement pectoraux et dos à la maison sans poids'),
        containsAll(['Chest', 'Back']),
      );
      expect(FirebaseAiCoachService.extractTargetMusclesFromText('Treino de peito e costas em casa sem peso'), containsAll(['Chest', 'Back']));
    });

    test('CloudLiveBidiWebSocket auto-starts mic on session connect (1-click active listening), suppresses speaker echo during playback, and supports manual barge-in', () async {
      late FakeCloudLiveBidiWebSocket cloudSocket;
      final fakeAudioHostApi = FakeLiveCoachAudioHostApi();

      final client = FirebaseAiGoogleClient(
        appCheckTokenProvider: () async => 'live-app-check-token',
        authTokenProvider: () async => 'live-auth-id-token',
        apiKeyOverride: 'fake-api-key',
        projectIdOverride: 'comunityfitness',
        liveWebSocketConnector: (uri, headers) async {
          cloudSocket = FakeCloudLiveBidiWebSocket();
          return cloudSocket;
        },
      );

      final service = FirebaseAiCoachService(googleAiClient: client, audioHostApi: fakeAudioHostApi, enablePlatformCues: true);

      final events = <AiLiveCoachEvent>[];
      final sub = service.liveEvents.listen(events.add);

      // 1. Toggling Live Mode on immediately starts microphone capture without a second tap
      await service.startLiveCoachSession(catalog: sampleCatalog, activeExercise: sampleCatalog.first);
      await Future<void>.delayed(Duration.zero);
      expect(service.isMicRecording, isTrue);
      expect(fakeAudioHostApi.startMicCaptureCount, 1);
      expect(events.last.isMicRecording, isTrue);

      // 2. Simulate Coach speaking 24kHz audio chunk
      final largePcmChunk = base64Encode(List<int>.filled(24000, 1));
      cloudSocket.pushServerFrame({
        'interactionStatus': 'IN_PROGRESS',
        'serverContent': {
          'modelTurn': {
            'parts': [
              {
                'inlineData': {'mimeType': 'audio/pcm;rate=24000', 'data': largePcmChunk},
              },
            ],
          },
          'outputTranscription': {'text': 'Hola, ¿qué grupo muscular entrenamos hoy?'},
        },
      });
      await Future<void>.delayed(const Duration(milliseconds: 20));
      expect(service.currentLiveState, AiLiveCoachState.speaking);

      // 3. Mic chunks arriving while Coach is speaking are suppressed (speaker echo protection)
      final sentBeforeEcho = cloudSocket.sentPayloads.length;
      service.onMicPcm16kChunk('RUNIT19DSFVOSw==');
      await Future<void>.delayed(Duration.zero);
      expect(cloudSocket.sentPayloads.length, sentBeforeEcho);

      // 4. Spurious server interrupted flag during active speaker playback is ignored
      final stopCountBeforeSpurious = fakeAudioHostApi.stopCount;
      cloudSocket.pushServerFrame({
        'serverContent': {'interrupted': true},
      });
      await Future<void>.delayed(const Duration(milliseconds: 20));
      expect(fakeAudioHostApi.stopCount, stopCountBeforeSpurious);
      expect(service.currentLiveState, AiLiveCoachState.speaking);

      // 5. Explicit user barge-in via stopLiveMicRecording stops Coach speech and keeps mic listening
      await service.stopLiveMicRecording(catalog: sampleCatalog, activeExercise: sampleCatalog.first);
      expect(service.isMicRecording, isTrue);
      expect(service.currentLiveState, AiLiveCoachState.listening);

      // 6. Now user mic audio chunks are forwarded to Gemini Live
      service.onMicPcm16kChunk('VVNFUl9WT0lDRQ==');
      await Future<void>.delayed(Duration.zero);
      expect(
        cloudSocket.sentPayloads.any(
          (p) => p['realtimeInput'] is Map && ((p['realtimeInput'] as Map)['audio'] as Map?)?['data'] == 'VVNFUl9WT0lDRQ==',
        ),
        isTrue,
      );

      await service.stopLiveCoachSession();
      await sub.cancel();
    });
  });
}
