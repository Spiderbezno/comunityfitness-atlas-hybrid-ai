// ignore_for_file: prefer_initializing_formals

// 🎯 Dart imports:
import 'dart:async';
import 'dart:convert';
import 'dart:io';

// 🐦 Flutter imports:
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

// 📦 Package imports:
import 'package:firebase_ai/firebase_ai.dart';
import 'package:firebase_app_check/firebase_app_check.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:uuid/uuid.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/ai_coach_models.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/pigeon/live_coach_audio_api.g.dart';
import 'package:comunityfitness/services/atlas_ai_config_service.dart';

part 'ai_coach_service.g.dart';

/// Application-owned contract for the Gemini 3.8 Personal Trainer &
/// Exercise Alternative Assistant.
///
/// Zero external SDK types leak across this interface boundary.
abstract interface class AiCoachService {
  String get chatModelName;
  String get liveModelName;

  Future<List<AiExerciseRecommendation>> suggestAlternatives({
    required ExerciseModel exercise,
    required String constraint,
    required List<ExerciseModel> catalog,
  });

  Future<AiWorkoutPlan> planWorkoutByMuscles({
    required List<String> targetMuscles,
    required String equipmentConstraint,
    required String userPrompt,
    required List<ExerciseModel> catalog,
  });

  Future<AiChatMessage> sendCoachMessage({
    required String message,
    required List<AiChatMessage> history,
    required List<ExerciseModel> catalog,
    ExerciseModel? contextExercise,
  });

  Stream<AiLiveCoachEvent> get liveEvents;

  AiLiveCoachState get currentLiveState;

  bool get isMicRecording;

  Future<void> startLiveCoachSession({required List<ExerciseModel> catalog, ExerciseModel? activeExercise});

  Future<void> sendLiveVoiceOrTextTurn({required String userUtterance, required List<ExerciseModel> catalog, ExerciseModel? activeExercise});

  Future<void> sendLiveAudioChunk({String? base64Pcm16k, bool audioStreamEnd = false});

  Future<bool> startLiveMicRecording({required List<ExerciseModel> catalog, ExerciseModel? activeExercise});

  Future<String> stopLiveMicRecording({required List<ExerciseModel> catalog, ExerciseModel? activeExercise, String? fallbackUtterance});

  Future<void> stopLiveCoachSession();

  void dispose();
}

abstract interface class LiveBidiWebSocket {
  Stream<dynamic> get messages;
  void sendJson(Map<String, dynamic> payload);
  Future<void> close();
}

/// Marker interface implemented by cloud-backed Gemini Live sockets
/// ([_IoLiveBidiWebSocket] and [_FirebaseAiLiveSessionSocket]) to enable
/// automatic 1-click microphone activation on session start and speaker echo gating.
abstract interface class CloudLiveBidiWebSocket implements LiveBidiWebSocket {}

class _IoLiveBidiWebSocket implements CloudLiveBidiWebSocket {
  final WebSocket _socket;
  final Stream<dynamic> _broadcastMessages;

  _IoLiveBidiWebSocket(this._socket) : _broadcastMessages = _socket.asBroadcastStream();

  @override
  Stream<dynamic> get messages => _broadcastMessages;

  @override
  void sendJson(Map<String, dynamic> payload) {
    _socket.add(jsonEncode(payload));
  }

  @override
  Future<void> close() async {
    await _socket.close();
  }
}

/// Official `package:firebase_ai` (`LiveSession`) adapter implementing
/// [CloudLiveBidiWebSocket] so that real-time Gemini Live bidirectional streaming
/// runs through `FirebaseAI.googleAI().liveGenerativeModel(...).connect()`.
class _FirebaseAiLiveSessionSocket implements CloudLiveBidiWebSocket {
  final LiveSession _session;
  final StreamController<dynamic> _inboundController = StreamController<dynamic>.broadcast();
  late final StreamSubscription<LiveServerResponse> _subscription;
  bool _isClosed = false;

  _FirebaseAiLiveSessionSocket(this._session) {
    // Emit setupComplete immediately since LiveSession.create() has already sent
    // the setup frame over the WebSocket.
    scheduleMicrotask(() {
      if (!_inboundController.isClosed) {
        _inboundController.add(jsonEncode(<String, dynamic>{'setupComplete': <String, dynamic>{}}));
      }
    });
    _subscription = _session.receive().listen(
      (response) {
        if (_inboundController.isClosed) {
          return;
        }
        final frame = _mapServerMessageToWireMap(response.message);
        if (frame != null) {
          _inboundController.add(jsonEncode(frame));
        }
      },
      onError: (Object error, StackTrace stackTrace) {
        debugPrint('[FirebaseAI LiveSession Error] $error');
        if (!_inboundController.isClosed) {
          _inboundController.addError(error, stackTrace);
        }
      },
      onDone: () {
        if (!_inboundController.isClosed) {
          _inboundController.close();
        }
      },
    );
  }

  Map<String, dynamic>? _mapServerMessageToWireMap(LiveServerMessage msg) {
    if (msg is LiveServerContent) {
      final partsJson = <Map<String, dynamic>>[];
      final parts = msg.modelTurn?.parts ?? const <Part>[];
      for (final part in parts) {
        if (part is TextPart) {
          partsJson.add(<String, dynamic>{'text': part.text});
        } else if (part is InlineDataPart) {
          partsJson.add(<String, dynamic>{
            'inlineData': <String, dynamic>{'mimeType': part.mimeType, 'data': base64Encode(part.bytes)},
          });
        }
      }
      return <String, dynamic>{
        'serverContent': <String, dynamic>{
          if (partsJson.isNotEmpty) 'modelTurn': <String, dynamic>{'parts': partsJson},
          if (msg.turnComplete != null) 'turnComplete': msg.turnComplete,
          if (msg.interrupted != null) 'interrupted': msg.interrupted,
          if (msg.inputTranscription?.text != null)
            'inputTranscription': <String, dynamic>{
              'text': msg.inputTranscription!.text,
              if (msg.inputTranscription!.finished != null) 'finished': msg.inputTranscription!.finished,
            },
          if (msg.outputTranscription?.text != null)
            'outputTranscription': <String, dynamic>{
              'text': msg.outputTranscription!.text,
              if (msg.outputTranscription!.finished != null) 'finished': msg.outputTranscription!.finished,
            },
        },
      };
    } else if (msg is LiveServerToolCall) {
      final calls = msg.functionCalls ?? const <FunctionCall>[];
      return <String, dynamic>{
        'toolCall': <String, dynamic>{
          'functionCalls': [
            for (final call in calls) <String, dynamic>{if (call.id != null) 'id': call.id, 'name': call.name, 'args': call.args},
          ],
        },
      };
    } else if (msg is LiveServerToolCallCancellation) {
      return <String, dynamic>{
        'toolCallCancellation': <String, dynamic>{'ids': msg.functionIds ?? const <String>[]},
      };
    }
    return <String, dynamic>{'setupComplete': <String, dynamic>{}};
  }

  @override
  Stream<dynamic> get messages => _inboundController.stream;

  @override
  void sendJson(Map<String, dynamic> payload) {
    if (_isClosed) {
      return;
    }
    final realtimeInput = payload['realtimeInput'] ?? payload['realtime_input'];
    if (realtimeInput is Map) {
      final text = realtimeInput['text']?.toString();
      if (text != null && text.isNotEmpty) {
        unawaited(_session.sendTextRealtime(text));
        return;
      }
      final audio = realtimeInput['audio'];
      if (audio is Map) {
        final b64 = audio['data']?.toString();
        final mime = audio['mimeType']?.toString() ?? 'audio/pcm;rate=16000';
        if (b64 != null && b64.isNotEmpty) {
          unawaited(_session.sendAudioRealtime(InlineDataPart(mime, base64Decode(b64))));
          return;
        }
      }
      final mediaChunks = realtimeInput['mediaChunks'] ?? realtimeInput['media_chunks'];
      if (mediaChunks is List && mediaChunks.isNotEmpty) {
        final first = mediaChunks.first;
        if (first is Map) {
          final b64 = first['data']?.toString();
          final mime = first['mimeType']?.toString() ?? 'audio/pcm;rate=16000';
          if (b64 != null && b64.isNotEmpty) {
            unawaited(_session.sendAudioRealtime(InlineDataPart(mime, base64Decode(b64))));
            return;
          }
        }
      }
    }

    final clientContent = payload['clientContent'] ?? payload['client_content'];
    if (clientContent is Map) {
      final turnComplete = (clientContent['turnComplete'] ?? clientContent['turn_complete']) == true;
      final turns = clientContent['turns'];
      Content? inputContent;
      if (turns is List && turns.isNotEmpty) {
        final turn = turns.first;
        if (turn is Map) {
          final parts = turn['parts'];
          if (parts is List && parts.isNotEmpty) {
            final sdkParts = <Part>[];
            for (final p in parts) {
              if (p is Map) {
                if (p['text'] != null) {
                  sdkParts.add(TextPart(p['text'].toString()));
                } else if (p['inlineData'] is Map) {
                  final inlineData = p['inlineData'] as Map;
                  final mime = inlineData['mimeType']?.toString() ?? 'audio/wav';
                  final data = inlineData['data']?.toString() ?? '';
                  if (data.isNotEmpty) {
                    sdkParts.add(InlineDataPart(mime, base64Decode(data)));
                  }
                }
              }
            }
            if (sdkParts.isNotEmpty) {
              inputContent = Content('user', sdkParts);
            }
          }
        }
      }
      unawaited(_session.send(input: inputContent, turnComplete: turnComplete));
      return;
    }

    final toolResponse = payload['toolResponse'] ?? payload['tool_response'];
    if (toolResponse is Map) {
      final fnList = toolResponse['functionResponses'] ?? toolResponse['function_responses'];
      if (fnList is List && fnList.isNotEmpty) {
        final sdkResponses = <FunctionResponse>[];
        for (final item in fnList) {
          if (item is Map) {
            final name = item['name']?.toString() ?? '';
            final id = item['id']?.toString();
            final resp = item['response'];
            sdkResponses.add(
              FunctionResponse(
                name,
                resp is Map<String, Object?> ? resp : (resp is Map ? Map<String, Object?>.from(resp) : <String, Object?>{'result': resp}),
                id: id,
              ),
            );
          }
        }
        unawaited(_session.sendToolResponse(sdkResponses));
      }
    }
  }

  @override
  Future<void> close() async {
    if (_isClosed) {
      return;
    }
    _isClosed = true;
    await _subscription.cancel();
    await _session.close();
    if (!_inboundController.isClosed) {
      await _inboundController.close();
    }
  }
}

typedef LiveWebSocketConnector = Future<LiveBidiWebSocket> Function(Uri uri, Map<String, String> headers);

typedef AiHttpTransport = Future<({int statusCode, String body})> Function(Uri uri, Map<String, String> headers, String body);

/// Lightweight Firebase AI Logic (`FirebaseAI.googleAI`) client wrapper
/// for Gemini Developer API (`gemini-3.8-flash` & `gemini-3.8-live`)
/// with strict fail-closed Firebase App Check and Firebase Auth enforcement.
class FirebaseAiGoogleClient {
  final FirebaseAuth? _auth;
  final FirebaseAppCheck? _appCheck;
  final Future<String?> Function()? _appCheckTokenProvider;
  final Future<String?> Function()? _authTokenProvider;
  final String? _apiKeyOverride;
  final String? _projectIdOverride;
  final Uri? _endpointOverride;
  final Uri? _liveEndpointOverride;
  final AiHttpTransport? _httpTransport;
  final LiveWebSocketConnector? _liveWebSocketConnector;

  const FirebaseAiGoogleClient({
    FirebaseAuth? auth,
    FirebaseAppCheck? appCheck,
    Future<String?> Function()? appCheckTokenProvider,
    Future<String?> Function()? authTokenProvider,
    String? apiKeyOverride,
    String? projectIdOverride,
    Uri? endpointOverride,
    Uri? liveEndpointOverride,
    AiHttpTransport? httpTransport,
    LiveWebSocketConnector? liveWebSocketConnector,
  }) : _auth = auth,
       _appCheck = appCheck,
       _appCheckTokenProvider = appCheckTokenProvider,
       _authTokenProvider = authTokenProvider,
       _apiKeyOverride = apiKeyOverride,
       _projectIdOverride = projectIdOverride,
       _endpointOverride = endpointOverride,
       _liveEndpointOverride = liveEndpointOverride,
       _httpTransport = httpTransport,
       _liveWebSocketConnector = liveWebSocketConnector;

  Future<String?> _resolveAppCheckToken() async {
    if (_appCheckTokenProvider != null) {
      return _appCheckTokenProvider();
    }
    try {
      final appCheck = _appCheck ?? FirebaseAppCheck.instance;
      return await appCheck.getToken().timeout(const Duration(seconds: 3));
    } catch (_) {
      return null;
    }
  }

  Future<String?> _resolveAuthToken() async {
    if (_authTokenProvider != null) {
      return _authTokenProvider();
    }
    try {
      final auth = _auth ?? FirebaseAuth.instance;
      if (auth.currentUser == null) {
        await auth.signInAnonymously().timeout(const Duration(seconds: 3));
      }
      return await auth.currentUser?.getIdToken().timeout(const Duration(seconds: 3));
    } catch (_) {
      return null;
    }
  }

  Map<String, String> _buildSecurityHeaders({required String? appCheckToken, required String? authToken, String? appId, String? iosBundleId}) {
    final headers = <String, String>{'x-goog-api-client': 'gl-dart/3.8.0 fire/5.1.0'};
    if (appCheckToken != null && appCheckToken.trim().isNotEmpty) {
      headers['X-Firebase-AppCheck'] = appCheckToken.trim();
    }
    if (authToken != null && authToken.trim().isNotEmpty) {
      headers['Authorization'] = 'Firebase ${authToken.trim()}';
      headers['X-Firebase-Auth'] = authToken.trim();
    }
    if (appId != null && appId.isNotEmpty) {
      headers['X-Firebase-AppId'] = appId;
    }
    if (iosBundleId != null && iosBundleId.isNotEmpty) {
      headers['x-ios-bundle-identifier'] = iosBundleId;
    }
    return headers;
  }

  /// Invokes Firebase AI Logic `generateContent` with structured JSON or
  /// conversational text output.
  ///
  /// Enforces fail-closed attestation when custom token providers are configured.
  Future<String?> generateStructuredText({
    required String model,
    required String systemInstruction,
    required String prompt,
    String responseMimeType = 'application/json',
    Duration timeout = const Duration(seconds: 8),
  }) async {
    try {
      if (_appCheckTokenProvider == null &&
          _authTokenProvider == null &&
          (_apiKeyOverride == null || _apiKeyOverride.isEmpty) &&
          Firebase.apps.isEmpty) {
        return null;
      }

      final appCheckToken = await _resolveAppCheckToken();
      if (appCheckToken == null || appCheckToken.trim().isEmpty) {
        return null;
      }

      final authToken = await _resolveAuthToken();
      if (authToken == null || authToken.trim().isEmpty) {
        return null;
      }

      String apiKey = _apiKeyOverride ?? '';
      String projectId = _projectIdOverride ?? '';
      String? appId;
      String? iosBundleId;
      if (apiKey.isEmpty || projectId.isEmpty) {
        if (Firebase.apps.isEmpty) {
          return null;
        }
        final app = Firebase.app();
        apiKey = app.options.apiKey;
        projectId = app.options.projectId;
        appId = app.options.appId;
        iosBundleId = app.options.iosBundleId;
      }
      if (apiKey.isEmpty || projectId.isEmpty) {
        return null;
      }

      final headers = <String, String>{
        HttpHeaders.contentTypeHeader: 'application/json',
        'x-goog-api-key': apiKey,
        ..._buildSecurityHeaders(appCheckToken: appCheckToken, authToken: authToken, appId: appId, iosBundleId: iosBundleId),
      };

      Map<String, dynamic> buildPayload(String modelName) => <String, dynamic>{
        'model': 'models/$modelName',
        'systemInstruction': {
          'role': 'system',
          'parts': [
            {'text': systemInstruction},
          ],
        },
        'contents': [
          {
            'role': 'user',
            'parts': [
              {'text': prompt},
            ],
          },
        ],
        'generationConfig': {
          'temperature': 0.4,
          if (responseMimeType.isNotEmpty && responseMimeType != 'text/plain') 'responseMimeType': responseMimeType,
        },
      };

      if (_httpTransport != null) {
        final uri =
            _endpointOverride ?? Uri.parse('https://firebasevertexai.googleapis.com/v1beta/projects/$projectId/models/$model:generateContent');
        final result = await _httpTransport(uri, headers, jsonEncode(buildPayload(model))).timeout(timeout);
        if (result.statusCode < 200 || result.statusCode >= 300) {
          return null;
        }
        return _extractCandidateText(result.body);
      }

      final candidateModels = <String>[model, if (model != 'gemini-3.5-flash-lite') 'gemini-3.5-flash-lite'];

      // 1. Primary path: Official `package:firebase_ai` SDK (`FirebaseAI.googleAI().generativeModel(...)`)
      if (_endpointOverride == null && Firebase.apps.isNotEmpty) {
        final fbAi = FirebaseAI.googleAI(app: Firebase.app());
        for (final candidateModel in candidateModels) {
          try {
            final genModel = fbAi.generativeModel(
              model: candidateModel,
              systemInstruction: Content.system(systemInstruction),
              generationConfig: GenerationConfig(
                temperature: 0.4,
                responseMimeType: (responseMimeType.isNotEmpty && responseMimeType != 'text/plain') ? responseMimeType : null,
              ),
            );
            final sdkResponse = await genModel.generateContent([Content.text(prompt)]).timeout(const Duration(seconds: 12));
            final sdkText = sdkResponse.text?.trim();
            if (sdkText != null && sdkText.isNotEmpty) {
              debugPrint('[FirebaseAI SDK Chat OK] ($candidateModel) ${sdkText.length} chars');
              return sdkText;
            }
          } catch (e) {
            debugPrint('[FirebaseAI SDK Chat Error] ($candidateModel) $e');
          }
        }
      }

      for (final candidateModel in candidateModels) {
        final encodedPayload = jsonEncode(buildPayload(candidateModel));
        final endpointOverride = _endpointOverride;
        final candidateUris = <Uri>[
          if (endpointOverride != null)
            endpointOverride
          else
            Uri.parse('https://firebasevertexai.googleapis.com/v1beta/projects/$projectId/models/$candidateModel:generateContent'),
        ];

        for (final uri in candidateUris) {
          final client = HttpClient()..connectionTimeout = const Duration(seconds: 6);
          try {
            final request = await client.postUrl(uri).timeout(const Duration(seconds: 6));
            headers.forEach(request.headers.set);
            request.add(utf8.encode(encodedPayload));
            final response = await request.close().timeout(const Duration(seconds: 12));
            final statusCode = response.statusCode;
            final responseBody = await response.transform(utf8.decoder).join();
            if (statusCode >= 200 && statusCode < 300) {
              final text = _extractCandidateText(responseBody);
              if (text != null) {
                debugPrint('[FirebaseAI Chat OK] ($candidateModel) ${text.length} chars');
                return text;
              }
            } else {
              debugPrint('[FirebaseAI HTTP $statusCode] ($candidateModel) $responseBody');
            }
          } catch (e) {
            debugPrint('[FirebaseAI HTTP Error] ($candidateModel) $e');
          } finally {
            client.close(force: true);
          }
        }
      }
    } catch (_) {
      // Automatically fall back to the local biomechanical catalog engine.
    }
    return null;
  }

  String? _extractCandidateText(String responseBody) {
    final decoded = jsonDecode(responseBody);
    if (decoded is Map<String, dynamic>) {
      final candidates = decoded['candidates'];
      if (candidates is List && candidates.isNotEmpty) {
        final content = candidates.first['content'];
        final parts = content is Map ? content['parts'] : null;
        if (parts is List && parts.isNotEmpty) {
          final text = parts.first['text']?.toString();
          if (text != null && text.trim().isNotEmpty) {
            return text.trim();
          }
        }
      }
    }
    return null;
  }

  /// Opens a bidirectional `BidiGenerateContent` WebSocket session to
  /// Gemini Live via Firebase AI Logic with App Check + Auth headers and sends
  /// the initial `setup` frame.
  Future<LiveBidiWebSocket?> connectLiveBidiSession({
    required String model,
    required String systemInstruction,
    Duration timeout = const Duration(seconds: 8),
  }) async {
    try {
      if (_appCheckTokenProvider == null &&
          _authTokenProvider == null &&
          (_apiKeyOverride == null || _apiKeyOverride.isEmpty) &&
          Firebase.apps.isEmpty) {
        return null;
      }

      final appCheckToken = await _resolveAppCheckToken();
      if (appCheckToken == null || appCheckToken.trim().isEmpty) {
        return null;
      }

      final authToken = await _resolveAuthToken();
      if (authToken == null || authToken.trim().isEmpty) {
        return null;
      }

      String apiKey = _apiKeyOverride ?? '';
      String projectId = _projectIdOverride ?? '';
      String? appId;
      String? iosBundleId;
      if (apiKey.isEmpty || projectId.isEmpty) {
        if (Firebase.apps.isEmpty) {
          return null;
        }
        final app = Firebase.app();
        apiKey = app.options.apiKey;
        projectId = app.options.projectId;
        appId = app.options.appId;
        iosBundleId = app.options.iosBundleId;
      }
      if (apiKey.isEmpty || projectId.isEmpty) {
        return null;
      }

      final headers = <String, String>{
        'x-goog-api-key': apiKey,
        ..._buildSecurityHeaders(appCheckToken: appCheckToken, authToken: authToken, appId: appId, iosBundleId: iosBundleId),
      };

      if (_liveWebSocketConnector != null) {
        final uri =
            _liveEndpointOverride ??
            Uri.parse('wss://firebasevertexai.googleapis.com/ws/google.firebase.vertexai.v1beta.LlmBidiService/BidiGenerateContent');
        final socket = await _liveWebSocketConnector(uri, headers).timeout(timeout);
        socket.sendJson(
          _buildLiveSetupPayload(
            modelResourceName: 'projects/$projectId/locations/us-central1/publishers/google/models/$model',
            systemInstruction: systemInstruction,
          ),
        );
        return socket;
      }

      // 1. Primary path: Official `package:firebase_ai` SDK (`FirebaseAI.googleAI().liveGenerativeModel(...)`)
      if (_liveEndpointOverride == null && Firebase.apps.isNotEmpty) {
        final fbAi = FirebaseAI.googleAI(app: Firebase.app());
        final sdkLiveTools = <Tool>[
          Tool.functionDeclarations([
            FunctionDeclaration(
              'suggest_exercise_alternatives',
              'Returns biomechanically equivalent alternatives from the CommunityFitness catalog for home or limited equipment.',
              parameters: <String, Schema>{'exerciseName': Schema.string(), 'constraint': Schema.string()},
            ),
            FunctionDeclaration(
              'plan_workout_by_muscles',
              'Builds a workout plan for target muscle groups using exercises from the CommunityFitness catalog.',
              parameters: <String, Schema>{
                'targetMuscles': Schema.array(items: Schema.string()),
                'equipmentConstraint': Schema.string(nullable: true),
              },
              optionalParameters: const <String>['equipmentConstraint'],
            ),
            FunctionDeclaration(
              'get_exercise_coaching_details',
              'Returns detailed biomechanics, primary muscles, equipment, and step-by-step form tracking cues for a specific exercise in the CommunityFitness catalog.',
              parameters: <String, Schema>{'exerciseName': Schema.string()},
            ),
          ]),
        ];

        const sdkLiveModels = <String>['gemini-3.1-flash-live-preview', 'gemini-2.5-flash-native-audio-preview-12-2025'];
        for (final liveModelName in sdkLiveModels) {
          try {
            final liveModel = fbAi.liveGenerativeModel(
              model: liveModelName,
              systemInstruction: Content.system(systemInstruction),
              tools: sdkLiveTools,
              liveGenerationConfig: LiveGenerationConfig(
                responseModalities: const <ResponseModalities>[ResponseModalities.audio],
                speechConfig: SpeechConfig(voiceName: 'Puck'),
                inputAudioTranscription: AudioTranscriptionConfig(),
                outputAudioTranscription: AudioTranscriptionConfig(),
              ),
            );
            final liveSession = await liveModel.connect().timeout(const Duration(seconds: 5));
            debugPrint('[FirebaseAI SDK Live OK] ($liveModelName)');
            return _FirebaseAiLiveSessionSocket(liveSession);
          } catch (e) {
            debugPrint('[FirebaseAI SDK Live Error] ($liveModelName) $e');
          }
        }
      }

      // 2. Fallback WebSocket transport if custom override or SDK model preview requires custom wire framing
      final liveOverride = _liveEndpointOverride;
      final googleAiLiveUri = Uri.parse(
        'wss://firebasevertexai.googleapis.com/ws/google.firebase.vertexai.v1beta.GenerativeService/BidiGenerateContent',
      );
      final endpoints = <({Uri uri, String modelResource, bool nonBlockingTools})>[
        if (liveOverride != null)
          (uri: liveOverride, modelResource: 'projects/$projectId/models/$model', nonBlockingTools: true)
        else ...[
          (uri: googleAiLiveUri, modelResource: 'projects/$projectId/models/gemini-3.1-flash-live-preview', nonBlockingTools: false),
          (uri: googleAiLiveUri, modelResource: 'projects/$projectId/models/gemini-2.5-flash-native-audio-preview-12-2025', nonBlockingTools: false),
          (uri: googleAiLiveUri, modelResource: 'projects/$projectId/models/$model', nonBlockingTools: true),
        ],
      ];

      for (final target in endpoints) {
        WebSocket? rawSocket;
        try {
          rawSocket = await WebSocket.connect(target.uri.toString(), headers: headers).timeout(const Duration(seconds: 4));
          final socket = _IoLiveBidiWebSocket(rawSocket);
          final setupCompleter = Completer<bool>();
          late final StreamSubscription<dynamic> sub;
          sub = socket.messages.listen(
            (frame) {
              try {
                final text = frame is String ? frame : utf8.decode(frame as List<int>);
                final decoded = jsonDecode(text);
                if (decoded is Map &&
                    (decoded.containsKey('setupComplete') ||
                        decoded.containsKey('setup_complete') ||
                        decoded.containsKey('serverContent') ||
                        decoded.containsKey('server_content'))) {
                  if (!setupCompleter.isCompleted) {
                    setupCompleter.complete(true);
                  }
                }
              } catch (_) {}
            },
            onError: (Object e) {
              debugPrint('[FirebaseAI Live WS Error] (${target.modelResource}) $e');
              if (!setupCompleter.isCompleted) {
                setupCompleter.complete(false);
              }
            },
            onDone: () {
              debugPrint('[FirebaseAI Live WS Closed] (${target.modelResource}) code=${rawSocket?.closeCode} reason=${rawSocket?.closeReason}');
              if (!setupCompleter.isCompleted) {
                setupCompleter.complete(false);
              }
            },
          );

          socket.sendJson(
            _buildLiveSetupPayload(
              modelResourceName: target.modelResource,
              systemInstruction: systemInstruction,
              includeNonBlockingBehavior: target.nonBlockingTools,
            ),
          );

          final setupOk = await setupCompleter.future.timeout(const Duration(seconds: 4), onTimeout: () => false);
          await sub.cancel();

          if (setupOk) {
            return socket;
          }
          await rawSocket.close();
        } catch (_) {
          try {
            await rawSocket?.close();
          } catch (_) {}
          // Try next endpoint.
        }
      }
    } catch (_) {
      return null;
    }
    return null;
  }

  Map<String, dynamic> _buildLiveSetupPayload({
    required String modelResourceName,
    required String systemInstruction,
    bool includeNonBlockingBehavior = true,
  }) {
    return <String, dynamic>{
      'setup': {
        'model': modelResourceName,
        'generationConfig': {
          'responseModalities': ['AUDIO'],
          'speechConfig': {
            'voiceConfig': {
              'prebuiltVoiceConfig': {'voiceName': 'Puck'},
            },
          },
        },
        'systemInstruction': {
          'parts': [
            {'text': systemInstruction},
          ],
        },
        'outputAudioTranscription': <String, dynamic>{},
        'inputAudioTranscription': <String, dynamic>{},
        'tools': [
          {
            'functionDeclarations': [
              {
                'name': 'suggest_exercise_alternatives',
                'description': 'Returns biomechanically equivalent alternatives from the CommunityFitness catalog for home or limited equipment.',
                if (includeNonBlockingBehavior) 'behavior': 'NON_BLOCKING',
                'parameters': {
                  'type': 'OBJECT',
                  'properties': {
                    'exerciseName': {'type': 'STRING'},
                    'constraint': {'type': 'STRING'},
                  },
                  'required': ['exerciseName', 'constraint'],
                },
              },
              {
                'name': 'plan_workout_by_muscles',
                'description': 'Builds a workout plan for target muscle groups using exercises from the CommunityFitness catalog.',
                if (includeNonBlockingBehavior) 'behavior': 'NON_BLOCKING',
                'parameters': {
                  'type': 'OBJECT',
                  'properties': {
                    'targetMuscles': {
                      'type': 'ARRAY',
                      'items': {'type': 'STRING'},
                    },
                    'equipmentConstraint': {'type': 'STRING'},
                  },
                  'required': ['targetMuscles'],
                },
              },
              {
                'name': 'get_exercise_coaching_details',
                'description': 'Returns detailed biomechanics, primary muscles, equipment, and step-by-step form tracking cues for a specific exercise in the CommunityFitness catalog.',
                if (includeNonBlockingBehavior) 'behavior': 'NON_BLOCKING',
                'parameters': {
                  'type': 'OBJECT',
                  'properties': {
                    'exerciseName': {'type': 'STRING'},
                  },
                  'required': ['exerciseName'],
                },
              },
            ],
          },
        ],
      },
    };
  }
}

@Riverpod(keepAlive: true)
AiCoachService aiCoachService(Ref ref) {
  final configService = ref.watch(atlasAiConfigServiceProvider);
  final service = FirebaseAiCoachService(configService: configService);
  ref.onDispose(service.dispose);
  return service;
}

/// Concrete implementation of [AiCoachService] powered by Firebase AI Logic
/// (`gemini-3.8-flash` and `gemini-3.8-live`) with an offline/simulator-safe
/// biomechanical catalog fallback grounded in `assets/data/exercises.json`.
class FirebaseAiCoachService implements AiCoachService, LiveCoachAudioFlutterApi {
  static const String defaultChatModel = 'gemini-3.8-flash';
  static const String defaultLiveModel = 'gemini-3.8-live';
  static const String offlineFallbackPrefix = '[ATLAS Offline Mode]';
  static const String regionalLanguageStandards =
      'LANGUAGE & ACCENT STANDARDS (apply strictly in both text and spoken audio): '
      '1) Spanish MUST be Peninsular Spanish from Spain (es-ES, Español de España — use "tú", Spain fitness terminology like mancuernas, flexiones, sentadillas, zancadas, dominadas, and Castilian Spain accent/pronunciation). '
      '2) English MUST be United States American English (en-US vocabulary and American pronunciation). '
      '3) Catalan MUST be neutral standard Andorran Catalan (ca-AD / neutral standard Català d\'Andorra, clear and neutral without heavy localisms). '
      '4) French: standard fr-FR. 5) Portuguese: standard pt-PT.';
  static const Uuid _uuid = Uuid();

  final FirebaseAiGoogleClient _googleAiClient;
  final LiveCoachAudioHostApi _audioHostApi;
  final AtlasAiConfigService _configService;
  final bool _enablePlatformCues;
  final Future<void> Function(String base64Pcm, int sampleRate)? _onPlayPcm24k;
  final Future<void> Function()? _onStopAudio;
  final StreamController<AiLiveCoachEvent> _liveController = StreamController<AiLiveCoachEvent>.broadcast();

  final List<String> receivedPcm24kChunks = <String>[];
  int _sentMicPcm16kChunksCount = 0;
  bool _isMicRecording = false;
  DateTime _coachAudioPlayingUntil = DateTime.fromMillisecondsSinceEpoch(0);
  Timer? _postSpeechListeningTimer;

  AiLiveCoachState _liveState = AiLiveCoachState.disconnected;
  LiveBidiWebSocket? _liveSocket;
  StreamSubscription<dynamic>? _liveSocketSubscription;
  Future<void> _liveFrameProcessingChain = Future<void>.value();
  List<ExerciseModel> _activeCatalog = const [];
  ExerciseModel? _activeContextExercise;
  final StringBuffer _liveOutputTranscriptBuffer = StringBuffer();
  final StringBuffer _liveInputTranscriptBuffer = StringBuffer();
  String _currentInteractionStatus = 'IDLE';
  bool _pendingTurnComplete = false;
  AiWorkoutPlan? _pendingLiveWorkoutPlan;
  List<AiExerciseRecommendation>? _pendingLiveAlternatives;

  FirebaseAiCoachService({
    FirebaseAiGoogleClient? googleAiClient,
    LiveCoachAudioHostApi? audioHostApi,
    AtlasAiConfigService? configService,
    this._enablePlatformCues = true,
    this._onPlayPcm24k,
    this._onStopAudio,
  }) : _googleAiClient = googleAiClient ?? const FirebaseAiGoogleClient(),
       _audioHostApi = audioHostApi ?? LiveCoachAudioHostApi(),
       _configService = configService ?? AppAtlasAiConfigService() {
    if (_enablePlatformCues) {
      try {
        LiveCoachAudioFlutterApi.setUp(this);
      } catch (_) {
        // Safe no-op in pure Dart unit tests without binary messenger binding.
      }
    }
  }

  String _buildCoachSystemInstruction(String baseInstruction) {
    final String otaDirective = _configService.currentConfig.coachSystemPrompt.trim();
    if (otaDirective.isEmpty) {
      return baseInstruction;
    }
    return '$baseInstruction $otaDirective';
  }

  bool _isCloudLiveSocket([LiveBidiWebSocket? socket]) {
    final target = socket ?? _liveSocket;
    return target is CloudLiveBidiWebSocket;
  }

  @override
  void onMicPcm16kChunk(String base64Pcm) {
    if (base64Pcm.isNotEmpty) {
      _sentMicPcm16kChunksCount++;
      // Suppress forwarding speaker echo strictly while the coach's 24kHz audio is actively
      // playing on the hardware speaker + a 350ms acoustic tail window. Never gate solely on
      // `_liveState == AiLiveCoachState.speaking` without checking the clock so the microphone
      // can never remain muted after speaker playback finishes.
      if (_isCloudLiveSocket() && DateTime.now().isBefore(_coachAudioPlayingUntil.add(const Duration(milliseconds: 350)))) {
        return;
      }
      unawaited(sendLiveAudioChunk(base64Pcm16k: base64Pcm));
    }
  }

  @override
  String get chatModelName => defaultChatModel;

  @override
  String get liveModelName => defaultLiveModel;

  @override
  Stream<AiLiveCoachEvent> get liveEvents => _liveController.stream;

  @override
  AiLiveCoachState get currentLiveState => _liveState;

  @override
  bool get isMicRecording => _isMicRecording;

  @override
  Future<List<AiExerciseRecommendation>> suggestAlternatives({
    required ExerciseModel exercise,
    required String constraint,
    required List<ExerciseModel> catalog,
  }) async {
    final candidates = selectAlternativeCandidates(target: exercise, constraint: constraint, catalog: catalog);

    final catalogDigest = candidates
        .take(25)
        .map((e) => jsonEncode({'id': e.id, 'name': e.name, 'muscle': e.primaryMuscleGroup, 'equipment': e.equipment}))
        .join(', ');

    final langName = LocaleSettings.currentLocale.nativeName;
    final systemInstruction =
        'Your name is ATLAS, the CommunityFitness Biomechanical AI Personal Trainer. Never refer to yourself as Gemini or mention model version numbers. '
        '$regionalLanguageStandards '
        'Only recommend exercises that exist in the provided catalog JSON. '
        'Write all "matchReason", "homeAdaptationTip", and "keyBiomechanicalCues" fields in $langName (${LocaleSettings.currentLocale.bcp47Code}). '
        'Return a JSON object with an "alternatives" array of 3 items matching schema: '
        '{"alternatives":[{"exerciseId":"string","exerciseName":"string","matchReason":"string",'
        '"homeAdaptationTip":"string","sets":3,"reps":12,"restSeconds":60,'
        '"keyBiomechanicalCues":["string","string"]}]}';

    final prompt =
        'Target exercise to replace: ${exercise.name} (id: ${exercise.id}, muscle: ${exercise.primaryMuscleGroup}, equipment: ${exercise.equipment}). '
        'User constraint: "$constraint". '
        'Available catalog candidates: [$catalogDigest]';

    final remoteJson = await _googleAiClient.generateStructuredText(model: chatModelName, systemInstruction: systemInstruction, prompt: prompt);

    if (remoteJson != null) {
      final parsed = _tryParseAlternatives(remoteJson, catalog);
      if (parsed.isNotEmpty) {
        return parsed;
      }
    }

    return buildCatalogAlternatives(target: exercise, constraint: constraint, catalog: catalog);
  }

  @override
  Future<AiWorkoutPlan> planWorkoutByMuscles({
    required List<String> targetMuscles,
    required String equipmentConstraint,
    required String userPrompt,
    required List<ExerciseModel> catalog,
  }) async {
    final normalizedMuscles = targetMuscles.isEmpty ? const <String>['Full Body'] : targetMuscles;
    final matchingPool = filterCatalogByMusclesAndEquipment(
      targetMuscles: normalizedMuscles,
      equipmentConstraint: equipmentConstraint,
      catalog: catalog,
    );

    final catalogDigest = matchingPool
        .take(30)
        .map((e) => jsonEncode({'id': e.id, 'name': e.name, 'muscle': e.primaryMuscleGroup, 'equipment': e.equipment}))
        .join(', ');

    final langName = LocaleSettings.currentLocale.nativeName;
    final systemInstruction =
        'Your name is ATLAS, the CommunityFitness Biomechanical AI Personal Trainer. Never refer to yourself as Gemini or mention model version numbers. '
        '$regionalLanguageStandards '
        'Design a biomechanically balanced workout using ONLY exercises from the provided catalog JSON. '
        'Write "title", "coachSummary", "matchReason", "homeAdaptationTip", and "keyBiomechanicalCues" in $langName (${LocaleSettings.currentLocale.bcp47Code}). '
        'Return JSON matching schema: '
        '{"title":"string","targetMuscles":["string"],"coachSummary":"string",'
        '"exercises":[{"exerciseId":"string","exerciseName":"string","matchReason":"string",'
        '"homeAdaptationTip":"string","sets":3,"reps":12,"restSeconds":60,'
        '"keyBiomechanicalCues":["string","string"]}]}';

    final prompt =
        'Target muscles: ${normalizedMuscles.join(", ")}. '
        'Equipment constraint: "$equipmentConstraint". '
        'User goal/note: "$userPrompt". '
        'Available catalog exercises: [$catalogDigest]';

    final remoteJson = await _googleAiClient.generateStructuredText(model: chatModelName, systemInstruction: systemInstruction, prompt: prompt);

    if (remoteJson != null) {
      final parsed = _tryParseWorkoutPlan(remoteJson, catalog);
      if (parsed != null && parsed.exercises.isNotEmpty) {
        return parsed;
      }
    }

    return buildCatalogWorkoutPlan(
      targetMuscles: normalizedMuscles,
      equipmentConstraint: equipmentConstraint,
      userPrompt: userPrompt,
      catalog: catalog,
    );
  }

  @override
  Future<AiChatMessage> sendCoachMessage({
    required String message,
    required List<AiChatMessage> history,
    required List<ExerciseModel> catalog,
    ExerciseModel? contextExercise,
  }) async {
    final trimmed = message.trim();
    final lower = trimmed.toLowerCase();

    // Detect if user is asking for an alternative to a specific exercise (ES, EN, CA, FR, PT)
    final matchedExercise = contextExercise ?? findReferencedExercise(trimmed, catalog);
    final asksForAlternative =
        lower.contains('alternative') ||
        lower.contains('alternativa') ||
        lower.contains('replace') ||
        lower.contains('reemplaz') ||
        lower.contains('remplac') ||
        lower.contains('substitu') ||
        lower.contains('sustitu') ||
        lower.contains('instead of') ||
        lower.contains('en vez de') ||
        lower.contains('en lloc de') ||
        lower.contains('au lieu de') ||
        lower.contains('em vez de') ||
        lower.contains('at home') ||
        lower.contains('en casa') ||
        lower.contains('a casa') ||
        lower.contains('à la maison') ||
        lower.contains('em casa') ||
        lower.contains('no weight') ||
        lower.contains('sin pesa') ||
        lower.contains('sense pes') ||
        lower.contains('sans poids') ||
        lower.contains('sem peso') ||
        lower.contains('bodyweight') ||
        lower.contains('peso corporal') ||
        lower.contains('pes corporal') ||
        lower.contains('poids du corps') ||
        lower.contains('no bench') ||
        lower.contains('sin banco') ||
        lower.contains('sense banc') ||
        lower.contains('sans banc') ||
        lower.contains('sem banco') ||
        lower.contains('without equipment') ||
        lower.contains('sin equipo') ||
        lower.contains('sense material') ||
        lower.contains('sans matériel') ||
        lower.contains('sem equipamento');

    if (matchedExercise != null && asksForAlternative) {
      final constraint = inferConstraintFromMessage(trimmed);
      final alternatives = await suggestAlternatives(exercise: matchedExercise, constraint: constraint, catalog: catalog);
      final topNames = alternatives.map((a) => a.exerciseName).join(', ');
      final coachReply = await _googleAiClient.generateStructuredText(
        model: chatModelName,
        responseMimeType: 'text/plain',
        systemInstruction:
            'Your name is ATLAS, the CommunityFitness Specialist Personal Trainer. Never refer to yourself as Gemini or mention model version numbers. '
            '$regionalLanguageStandards '
            'Reply in the same language as the user message (or ${LocaleSettings.currentLocale.nativeName} if ambiguous). Be concise (2-3 sentences), explain why these catalog alternatives ($topNames) fit the constraint ($constraint) for ${matchedExercise.name}, and give a key biomechanical cue.',
        prompt: trimmed,
      );
      return AiChatMessage(
        id: _uuid.v4(),
        role: AiChatRole.coach,
        text: coachReply ?? _localizedAlternativesChatFallback(matchedExercise.name, constraint, topNames),
        timestamp: DateTime.now(),
        alternatives: alternatives,
      );
    }

    // Detect if user is asking for a workout plan or muscle-group routine (ES, EN, CA, FR, PT)
    final detectedMuscles = extractTargetMusclesFromText(trimmed);
    final equipmentConstraint = inferConstraintFromMessage(trimmed);
    final asksForPlan =
        lower.contains('workout') ||
        lower.contains('routine') ||
        lower.contains('rutina') ||
        lower.contains('rotina') ||
        lower.contains('entrenamiento') ||
        lower.contains('entrenament') ||
        lower.contains('entraînement') ||
        lower.contains('entrainement') ||
        lower.contains('treino') ||
        lower.contains('plan') ||
        lower.contains('pla ') ||
        lower.contains('plano') ||
        lower.contains('session') ||
        lower.contains('sesión') ||
        lower.contains('sessió') ||
        lower.contains('séance') ||
        lower.contains('sessão');

    if (asksForPlan || (detectedMuscles.isNotEmpty && matchedExercise == null)) {
      final musclesToPlan = detectedMuscles.isNotEmpty ? detectedMuscles : const ['Chest', 'Back', 'Legs'];
      final plan = await planWorkoutByMuscles(
        targetMuscles: musclesToPlan,
        equipmentConstraint: equipmentConstraint,
        userPrompt: trimmed,
        catalog: catalog,
      );
      return AiChatMessage(id: _uuid.v4(), role: AiChatRole.coach, text: plan.coachSummary, timestamp: DateTime.now(), workoutPlan: plan);
    }

    // Interactive Specialist Personal Trainer Q&A (form doubts, exercise tracking, tempo, sets/reps, injuries)
    final historyContext = history.reversed.take(6).toList().reversed.map((m) => '${m.role.name.toUpperCase()}: ${m.text}').join('\n');
    final activeExInfo = matchedExercise != null
        ? 'Active exercise context: ${matchedExercise.name} (primary muscle: ${matchedExercise.primaryMuscleGroup}, equipment: ${matchedExercise.equipment}, description: ${matchedExercise.description}, cues: ${_buildBiomechanicalCues(matchedExercise).join(" | ")}).'
        : 'No single exercise locked; full CommunityFitness catalog (${catalog.length} exercises) available.';

    final specialistReply = await _googleAiClient.generateStructuredText(
      model: chatModelName,
      responseMimeType: 'text/plain',
      systemInstruction: _buildCoachSystemInstruction(
        'Your name is ATLAS, the CommunityFitness Interactive Personal Trainer & Biomechanics Specialist. Never refer to yourself as Gemini or mention model version numbers. '
        '$regionalLanguageStandards '
        'Always reply in the exact language the user writes in (or ${LocaleSettings.currentLocale.nativeName} [${LocaleSettings.currentLocale.bcp47Code}] if ambiguous). '
        'Help the athlete track their sets/reps/RPE, resolve exercise technique and posture doubts, prevent joint pain, and structure progressive overload. '
        '$activeExInfo',
      ),
      prompt: historyContext.isNotEmpty ? 'Conversation history:\n$historyContext\n\nAthlete question: $trimmed' : trimmed,
    );

    if (specialistReply != null && specialistReply.isNotEmpty) {
      return AiChatMessage(id: _uuid.v4(), role: AiChatRole.coach, text: specialistReply, timestamp: DateTime.now());
    }

    // If offline and asking about a specific exercise's form/tracking
    if (matchedExercise != null) {
      final cues = _buildBiomechanicalCues(matchedExercise);
      final tip = _buildHomeAdaptationTip(matchedExercise, equipmentConstraint);
      return AiChatMessage(
        id: _uuid.v4(),
        role: AiChatRole.coach,
        text: _localizedExerciseCoachingFallback(matchedExercise, cues, tip),
        timestamp: DateTime.now(),
      );
    }

    // Conversational fallback (never attach an unsolicited workoutPlan when the user just greets or asks a question)
    return AiChatMessage(id: _uuid.v4(), role: AiChatRole.coach, text: _localizedGeneralCoachFallback(chatModelName), timestamp: DateTime.now());
  }

  @override
  Future<void> startLiveCoachSession({required List<ExerciseModel> catalog, ExerciseModel? activeExercise}) async {
    await _closeLiveSocket();
    receivedPcm24kChunks.clear();
    _activeCatalog = catalog;
    _activeContextExercise = activeExercise;
    _liveOutputTranscriptBuffer.clear();
    _liveInputTranscriptBuffer.clear();
    _currentInteractionStatus = 'IN_PROGRESS';
    _pendingTurnComplete = false;
    _pendingLiveWorkoutPlan = null;
    _pendingLiveAlternatives = null;

    _emitLiveEvent(state: AiLiveCoachState.connecting, interactionStatus: 'IN_PROGRESS', transcript: t.aiCoach.liveBanner.connecting);

    await _triggerFeedbackCue();

    final catalogSummary = catalog.take(35).map((e) => '${e.name} (${e.primaryMuscleGroup}, ${e.equipment})').join('; ');
    final activeContextPrompt = activeExercise != null
        ? 'Current exercise being tracked: ${activeExercise.name} (${activeExercise.primaryMuscleGroup}, ${activeExercise.equipment}) — ${activeExercise.description}. Key biomechanical cues: ${_buildBiomechanicalCues(activeExercise).join(" ")}. '
        : '';

    final langName = LocaleSettings.currentLocale.nativeName;
    final bcp47 = LocaleSettings.currentLocale.bcp47Code;
    final systemInstruction = _buildCoachSystemInstruction(
      'Your name is ATLAS, the CommunityFitness Interactive Live Personal Trainer and Biomechanics Specialist. Never refer to yourself as Gemini or mention model version numbers. '
      '$regionalLanguageStandards '
      'CRITICAL MULTILINGUAL RULE: The athlete may speak in ANY language (Español de España [es-ES], American English [en-US], Neutral Andorran Català [ca-AD], Français [fr-FR], Português [pt-PT]), even if the app UI is set to $langName ($bcp47). '
      'Always detect the language the athlete speaks in their voice/audio or text turn and reply in that EXACT same language and regional accent! '
      'Keep your spoken answers concise, conversational, and natural (1-3 sentences) so the athlete can have a fluid back-and-forth voice dialogue with you. '
      'Act as a real-time interactive specialist: track sets, reps, rest times, and eccentric/concentric tempo; answer posture, biomechanics, and joint-safety questions; and help plan or adapt workouts. '
      '$activeContextPrompt'
      'Available CommunityFitness catalog exercises: [$catalogSummary]. '
      'Use tools suggest_exercise_alternatives, plan_workout_by_muscles, and get_exercise_coaching_details whenever the athlete asks for exercise swaps, workout planning, or specific movement details.',
    );

    final socket = await _googleAiClient.connectLiveBidiSession(model: liveModelName, systemInstruction: systemInstruction);

    if (socket != null) {
      _liveSocket = socket;
      _currentInteractionStatus = 'IDLE';
      _liveFrameProcessingChain = Future<void>.value();
      _liveSocketSubscription = socket.messages.listen(
        (dynamic rawFrame) {
          _liveFrameProcessingChain = _liveFrameProcessingChain.then((_) => _handleLiveServerFrame(rawFrame));
        },
        onError: (_) {},
        onDone: () {
          _liveSocket = null;
          if (_liveState != AiLiveCoachState.disconnected) {
            _emitLiveEvent(state: AiLiveCoachState.listening, interactionStatus: 'IDLE', isMicRecording: _isMicRecording);
          }
        },
      );

      if (_isCloudLiveSocket(socket)) {
        _isMicRecording = true;
        _sentMicPcm16kChunksCount = 0;
        // Gate mic chunks briefly while the initial greeting turn is requested
        _coachAudioPlayingUntil = DateTime.now().add(const Duration(milliseconds: 1800));
        if (_enablePlatformCues) {
          try {
            await _audioHostApi.setLanguage(bcp47);
            await _audioHostApi.startMicCapture();
          } catch (_) {}
        }
      }

      final connectedMsg = _localizedLiveConnectedMsg(activeExercise);

      _emitLiveEvent(
        state: AiLiveCoachState.listening,
        interactionStatus: 'IDLE',
        isMicRecording: _isMicRecording,
        transcript: connectedMsg,
        spokenCue: connectedMsg,
      );

      if (_isCloudLiveSocket(socket)) {
        socket.sendJson({
          'client_content': {
            'turns': [
              {
                'role': 'user',
                'parts': [
                  {
                    'text':
                        'Greet the athlete in $langName ($bcp47) in 1 short, energetic sentence as ATLAS, their Live Personal Trainer, and ask what exercise, technique doubt, or muscle group they want to work on right now. Never mention Gemini or version numbers.',
                  },
                ],
              },
            ],
            'turn_complete': true,
          },
        });
      }
      return;
    }

    // Graceful Offline Fallback when BidiGenerateContent WebSocket is unreachable.
    // NOTE: Never invoke local phone TTS (_speakLiveCue) in Live Mode — audio in Live Mode
    // is strictly reserved for Gemini Live 24kHz PCM streaming.
    final rawWelcome = _localizedLiveOfflineWelcome(activeExercise);
    final fallbackTranscript = '$offlineFallbackPrefix $rawWelcome';

    _emitLiveEvent(state: AiLiveCoachState.listening, interactionStatus: 'IDLE', transcript: fallbackTranscript, spokenCue: rawWelcome);
  }

  @override
  Future<void> sendLiveVoiceOrTextTurn({required String userUtterance, required List<ExerciseModel> catalog, ExerciseModel? activeExercise}) async {
    _activeCatalog = catalog.isNotEmpty ? catalog : _activeCatalog;
    _activeContextExercise = activeExercise ?? _activeContextExercise;

    if (_liveState == AiLiveCoachState.disconnected) {
      await startLiveCoachSession(catalog: _activeCatalog, activeExercise: _activeContextExercise);
    }

    // Stop any previous turn's audio immediately so old responses never overlap with a new turn.
    await _stopLiveSpeech();

    _liveOutputTranscriptBuffer.clear();
    _liveInputTranscriptBuffer.clear();
    _pendingTurnComplete = false;
    _pendingLiveWorkoutPlan = null;
    _pendingLiveAlternatives = null;
    _currentInteractionStatus = 'IN_PROGRESS';

    _emitLiveEvent(state: AiLiveCoachState.thinking, interactionStatus: 'IN_PROGRESS', transcript: 'Analyzing biomechanics & catalog movements...');

    await _triggerFeedbackCue();

    // If connected to the real BidiGenerateContent WebSocket, send turn
    if (_liveSocket != null) {
      if (_isCloudLiveSocket(_liveSocket)) {
        _liveSocket!.sendJson({
          'client_content': {
            'turns': [
              {
                'role': 'user',
                'parts': [
                  {'text': userUtterance},
                ],
              },
            ],
            'turn_complete': true,
          },
        });
      } else {
        _liveSocket!.sendJson({
          'realtimeInput': {'text': userUtterance},
        });
      }
      return;
    }

    // Offline Fallback when BidiGenerateContent WebSocket is unavailable
    // (No local phone TTS — updates transcript and interactive cards only)
    final responseMessage = await sendCoachMessage(
      message: userUtterance,
      history: const [],
      catalog: _activeCatalog,
      contextExercise: _activeContextExercise,
    );

    final spokenText = _buildSpokenCoachScript(responseMessage);
    final fallbackTranscript = '$offlineFallbackPrefix ${responseMessage.text}';

    _emitLiveEvent(
      state: AiLiveCoachState.listening,
      interactionStatus: 'IDLE',
      transcript: fallbackTranscript,
      spokenCue: spokenText,
      workoutPlan: responseMessage.workoutPlan,
      alternatives: responseMessage.alternatives,
    );
  }

  @override
  Future<void> sendLiveAudioChunk({String? base64Pcm16k, bool audioStreamEnd = false}) async {
    if (_liveSocket == null) {
      return;
    }
    if (_liveSocket is _IoLiveBidiWebSocket) {
      if (base64Pcm16k != null && base64Pcm16k.isNotEmpty) {
        _liveSocket!.sendJson({
          'realtime_input': {
            'audio': {'data': base64Pcm16k, 'mimeType': 'audio/pcm;rate=16000'},
          },
        });
      }
      if (audioStreamEnd) {
        _liveSocket!.sendJson({
          'realtime_input': {'audio_stream_end': true},
        });
      }
      return;
    }
    if (base64Pcm16k != null && base64Pcm16k.isNotEmpty) {
      _liveSocket!.sendJson({
        'realtimeInput': {
          'audio': {'data': base64Pcm16k, 'mimeType': 'audio/pcm;rate=16000'},
        },
      });
    }
    if (audioStreamEnd) {
      _liveSocket!.sendJson({
        'realtimeInput': {'audioStreamEnd': true},
      });
    }
  }

  @override
  Future<bool> startLiveMicRecording({required List<ExerciseModel> catalog, ExerciseModel? activeExercise}) async {
    _activeCatalog = catalog.isNotEmpty ? catalog : _activeCatalog;
    _activeContextExercise = activeExercise ?? _activeContextExercise;
    _sentMicPcm16kChunksCount = 0;

    if (_liveState == AiLiveCoachState.disconnected) {
      await startLiveCoachSession(catalog: _activeCatalog, activeExercise: _activeContextExercise);
    }

    await _stopLiveSpeech();
    await _triggerFeedbackCue();
    _isMicRecording = true;

    if (_enablePlatformCues) {
      try {
        await _audioHostApi.setLanguage(LocaleSettings.currentLocale.bcp47Code);
        await _audioHostApi.startMicCapture();
      } catch (_) {}
    }

    final micListeningPrompt = _localizedMicListeningPrompt();
    _emitLiveEvent(
      state: AiLiveCoachState.listening,
      interactionStatus: 'IN_PROGRESS',
      isMicRecording: true,
      transcript: micListeningPrompt,
      spokenCue: micListeningPrompt,
    );

    return true;
  }

  @override
  Future<String> stopLiveMicRecording({required List<ExerciseModel> catalog, ExerciseModel? activeExercise, String? fallbackUtterance}) async {
    _activeCatalog = catalog.isNotEmpty ? catalog : _activeCatalog;
    _activeContextExercise = activeExercise ?? _activeContextExercise;

    // If coach is currently speaking on a real Live WebSocket, tapping the mic/orb button
    // interrupts the coach (barge-in) and keeps the microphone actively listening!
    if (_isCloudLiveSocket() && (_liveState == AiLiveCoachState.speaking || DateTime.now().isBefore(_coachAudioPlayingUntil))) {
      await _stopLiveSpeech();
      await _triggerFeedbackCue();
      _isMicRecording = true;
      if (_enablePlatformCues) {
        try {
          await _audioHostApi.startMicCapture();
        } catch (_) {}
      }
      final micListeningPrompt = _localizedMicListeningPrompt();
      _emitLiveEvent(state: AiLiveCoachState.listening, interactionStatus: 'IDLE', isMicRecording: true, transcript: micListeningPrompt);
      return '';
    }

    _isMicRecording = false;
    await _triggerFeedbackCue();

    String nativeTranscript = '';
    if (_enablePlatformCues) {
      try {
        nativeTranscript = (await _audioHostApi.stopMicCapture()).trim();
      } catch (_) {}
    }

    // On a real Cloud Gemini Live WebSocket (CloudLiveBidiWebSocket), NEVER inject a fake
    // fallbackUtterance ("Build Chest & Back Plan"): flush the audio stream and let Gemini Live respond!
    if (_isCloudLiveSocket()) {
      await sendLiveAudioChunk(audioStreamEnd: true);
      final spokenSoFar = _liveInputTranscriptBuffer.toString().trim();
      _emitLiveEvent(
        state: AiLiveCoachState.listening,
        interactionStatus: 'IDLE',
        isMicRecording: false,
        transcript: spokenSoFar.isNotEmpty ? '🎙️ "$spokenSoFar"' : 'Mic muted — tap the mic button to speak again.',
      );
      return '';
    }

    final resolvedFallback = (fallbackUtterance != null && fallbackUtterance.trim().isNotEmpty)
        ? fallbackUtterance.trim()
        : (_activeContextExercise != null
              ? 'Give me a home no-weights alternative for ${_activeContextExercise!.name}'
              : 'Build a home bodyweight workout for Chest and Back');

    final effectiveUtterance = nativeTranscript.isNotEmpty ? nativeTranscript : resolvedFallback;

    if (_liveSocket != null) {
      await sendLiveAudioChunk(audioStreamEnd: true);
      if (_sentMicPcm16kChunksCount == 0 || nativeTranscript.isNotEmpty) {
        await sendLiveVoiceOrTextTurn(userUtterance: effectiveUtterance, catalog: _activeCatalog, activeExercise: _activeContextExercise);
      } else {
        _emitLiveEvent(
          state: AiLiveCoachState.thinking,
          interactionStatus: 'IN_PROGRESS',
          isMicRecording: false,
          transcript: 'Processing your live voice audio with $liveModelName...',
        );
      }
      return effectiveUtterance;
    }

    await sendLiveVoiceOrTextTurn(userUtterance: effectiveUtterance, catalog: _activeCatalog, activeExercise: _activeContextExercise);
    return effectiveUtterance;
  }

  Future<void> _handleLiveServerFrame(dynamic rawFrame) async {
    try {
      final String jsonStr;
      if (rawFrame is String) {
        jsonStr = rawFrame;
      } else if (rawFrame is List<int>) {
        jsonStr = utf8.decode(rawFrame);
      } else {
        return;
      }

      final decoded = jsonDecode(jsonStr);
      if (decoded is! Map<String, dynamic>) {
        return;
      }

      // Track top-level or serverContent interactionStatus
      final serverContent = decoded['serverContent'] ?? decoded['server_content'];
      final rawStatus =
          decoded['interactionStatus'] ??
          decoded['interaction_status'] ??
          (serverContent is Map ? (serverContent['interactionStatus'] ?? serverContent['interaction_status']) : null);
      if (rawStatus != null) {
        _currentInteractionStatus = rawStatus.toString();
      }

      if (decoded.containsKey('setupComplete') || decoded.containsKey('setup_complete')) {
        _currentInteractionStatus = 'IDLE';
        _emitLiveEvent(
          state: AiLiveCoachState.listening,
          interactionStatus: 'IDLE',
          isMicRecording: _isMicRecording,
          transcript: _localizedLiveConnectedMsg(_activeContextExercise),
        );
      }

      // 1. Handle non-blocking toolCall requests from gemini-3.8-live
      final toolCall = decoded['toolCall'] ?? decoded['tool_call'];
      if (toolCall is Map) {
        final rawCalls = toolCall['functionCalls'] ?? toolCall['function_calls'];
        if (rawCalls is List) {
          for (final call in rawCalls.whereType<Map<dynamic, dynamic>>()) {
            await _executeLiveToolCall(call.cast<String, dynamic>());
          }
        }
      }

      // 2. Process all parts in serverContent
      if (serverContent is Map) {
        final interrupted = serverContent['interrupted'] == true;
        if (interrupted) {
          // On a cloud live socket, while speaker playback is active and mic echo gating is on,
          // ignore spurious server-side VAD interruptions from trailing pre-speech packets so
          // the Coach never cuts itself off mid-sentence.
          if (_isCloudLiveSocket() && DateTime.now().isBefore(_coachAudioPlayingUntil)) {
            return;
          }
          _postSpeechListeningTimer?.cancel();
          _liveOutputTranscriptBuffer.clear();
          _pendingTurnComplete = false;
          _currentInteractionStatus = 'IDLE';
          await _stopLiveSpeech();
          _emitLiveEvent(
            state: AiLiveCoachState.listening,
            interactionStatus: 'IDLE',
            isMicRecording: _isMicRecording,
            transcript: 'Interrupted — listening for your voice...',
          );
          return;
        }

        // Input audio transcription (multilingual speech from the athlete)
        final inputTrans = serverContent['inputTranscription'] ?? serverContent['input_transcription'];
        if (inputTrans is Map) {
          final inText = inputTrans['text']?.toString() ?? '';
          if (inText.isNotEmpty) {
            _liveInputTranscriptBuffer.write(inText);
            final currentInput = _liveInputTranscriptBuffer.toString().trim();
            if (currentInput.isNotEmpty) {
              debugPrint('[FirebaseAI Live User Speech]: $currentInput');
              _emitLiveEvent(
                state: AiLiveCoachState.listening,
                interactionStatus: 'IN_PROGRESS',
                isMicRecording: _isMicRecording,
                transcript: '🎙️ "$currentInput"',
              );
            }
          }
        }

        String? finalizedUserTranscript;
        void consumeUserInputIfComplete() {
          if (_liveInputTranscriptBuffer.isNotEmpty) {
            finalizedUserTranscript = _liveInputTranscriptBuffer.toString().trim();
            _liveInputTranscriptBuffer.clear();
          }
        }

        // Process ALL parts in modelTurn (24kHz PCM audio chunks + text parts)
        final modelTurn = serverContent['modelTurn'] ?? serverContent['model_turn'];
        if (modelTurn is Map) {
          final parts = modelTurn['parts'];
          if (parts is List) {
            for (final part in parts.whereType<Map<dynamic, dynamic>>()) {
              final inlineData = part['inlineData'] ?? part['inline_data'];
              if (inlineData is Map) {
                final mimeType = (inlineData['mimeType'] ?? inlineData['mime_type'] ?? '').toString();
                final base64Data = (inlineData['data'] ?? '').toString();
                if (mimeType.startsWith('audio/pcm') && base64Data.isNotEmpty) {
                  consumeUserInputIfComplete();
                  _postSpeechListeningTimer?.cancel();
                  if (receivedPcm24kChunks.length >= 200) {
                    receivedPcm24kChunks.removeAt(0);
                  }
                  receivedPcm24kChunks.add(base64Data);
                  await _playPcm24kChunk(base64Data, sampleRate: 24000);
                  if (_liveState != AiLiveCoachState.speaking || finalizedUserTranscript != null) {
                    _emitLiveEvent(
                      state: AiLiveCoachState.speaking,
                      interactionStatus: _currentInteractionStatus,
                      isMicRecording: _isMicRecording,
                      userTranscript: finalizedUserTranscript,
                      transcript: _liveOutputTranscriptBuffer.isEmpty ? null : _liveOutputTranscriptBuffer.toString().trim(),
                      spokenCue: _liveOutputTranscriptBuffer.isEmpty ? null : _liveOutputTranscriptBuffer.toString().trim(),
                      workoutPlan: _pendingLiveWorkoutPlan,
                      alternatives: _pendingLiveAlternatives,
                    );
                    finalizedUserTranscript = null;
                  }
                }
              }

              final partText = part['text']?.toString();
              if (partText != null && partText.isNotEmpty) {
                _liveOutputTranscriptBuffer.write(partText);
              }
            }
          }
        }

        // Output audio transcription
        final outputTrans = serverContent['outputTranscription'] ?? serverContent['output_transcription'];
        if (outputTrans is Map) {
          final outText = outputTrans['text']?.toString() ?? '';
          if (outText.isNotEmpty) {
            consumeUserInputIfComplete();
            _liveOutputTranscriptBuffer.write(outText);
            final currentText = _liveOutputTranscriptBuffer.toString().trim();
            debugPrint('[FirebaseAI Live Coach Speech]: $currentText');
            _emitLiveEvent(
              state: AiLiveCoachState.speaking,
              interactionStatus: _currentInteractionStatus,
              isMicRecording: _isMicRecording,
              userTranscript: finalizedUserTranscript,
              transcript: currentText,
              spokenCue: currentText,
              workoutPlan: _pendingLiveWorkoutPlan,
              alternatives: _pendingLiveAlternatives,
            );
            finalizedUserTranscript = null;
          }
        }

        final turnComplete = serverContent['turnComplete'] == true || serverContent['turn_complete'] == true;
        if (turnComplete) {
          _pendingTurnComplete = true;
          if (rawStatus == null) {
            _currentInteractionStatus = 'IDLE';
          }
        }
      }

      // Transition from speaking to listening ONLY when interactionStatus != IN_PROGRESS
      // and turnComplete has been signaled (or interactionStatus transitions to IDLE after turnComplete).
      if (_pendingTurnComplete && _currentInteractionStatus != 'IN_PROGRESS') {
        _pendingTurnComplete = false;
        final finalTranscript = _liveOutputTranscriptBuffer.toString().trim();
        _liveOutputTranscriptBuffer.clear();
        final completedPlan = _pendingLiveWorkoutPlan;
        final completedAlts = _pendingLiveAlternatives;
        _pendingLiveWorkoutPlan = null;
        _pendingLiveAlternatives = null;

        final remainingAudioMs = _isCloudLiveSocket() && _enablePlatformCues ? _coachAudioPlayingUntil.difference(DateTime.now()).inMilliseconds : 0;

        if (remainingAudioMs > 80) {
          _postSpeechListeningTimer?.cancel();
          _postSpeechListeningTimer = Timer(Duration(milliseconds: remainingAudioMs + 150), () {
            if (_liveState != AiLiveCoachState.disconnected) {
              if (_isMicRecording && _enablePlatformCues) {
                unawaited(_audioHostApi.startMicCapture().catchError((_) => false));
              }
              _emitLiveEvent(
                state: AiLiveCoachState.listening,
                interactionStatus: 'IDLE',
                isMicRecording: _isMicRecording,
                transcript: finalTranscript.isNotEmpty ? finalTranscript : null,
                spokenCue: finalTranscript.isNotEmpty ? finalTranscript : null,
                workoutPlan: completedPlan,
                alternatives: completedAlts,
              );
            }
          });
        } else {
          if (_isMicRecording && _enablePlatformCues) {
            unawaited(_audioHostApi.startMicCapture().catchError((_) => false));
          }
          _emitLiveEvent(
            state: AiLiveCoachState.listening,
            interactionStatus: 'IDLE',
            isMicRecording: _isMicRecording,
            transcript: finalTranscript.isNotEmpty ? finalTranscript : null,
            spokenCue: finalTranscript.isNotEmpty ? finalTranscript : null,
            workoutPlan: completedPlan,
            alternatives: completedAlts,
          );
        }
      }
    } catch (_) {
      // Ignore malformed frame and keep session alive.
    }
  }

  Future<void> _executeLiveToolCall(Map<String, dynamic> call) async {
    final callId = (call['id'] ?? _uuid.v4()).toString();
    final fnName = (call['name'] ?? '').toString();
    final rawArgs = call['args'] ?? call['arguments'];
    final args = rawArgs is Map ? rawArgs.cast<String, dynamic>() : const <String, dynamic>{};

    if (fnName == 'suggest_exercise_alternatives') {
      final exName = (args['exerciseName'] ?? '').toString();
      final constraint = (args['constraint'] ?? 'At Home / No Weights').toString();

      final targetExercise =
          findReferencedExercise(exName, _activeCatalog) ??
          _activeContextExercise ??
          (_activeCatalog.isNotEmpty
              ? _activeCatalog.first
              : const Exercise(
                  id: 'bench_press',
                  name: 'Bench Press',
                  primaryMuscleGroup: 'Chest',
                  equipment: 'Barbell',
                  animationType: 'rive',
                  animationPath: 'assets/animations/bench_press.riv',
                  description: 'Compound chest exercise.',
                ));

      final alts = buildCatalogAlternatives(target: targetExercise, constraint: constraint, catalog: _activeCatalog);
      _pendingLiveAlternatives = alts;

      _emitLiveEvent(
        state: _liveState,
        interactionStatus: _currentInteractionStatus,
        transcript: _liveOutputTranscriptBuffer.isNotEmpty
            ? _liveOutputTranscriptBuffer.toString().trim()
            : 'Found ${alts.length} $constraint alternatives for ${targetExercise.name}.',
        alternatives: alts,
      );

      _liveSocket?.sendJson({
        'toolResponse': {
          'functionResponses': [
            {
              'id': callId,
              'name': fnName,
              'response': {
                'output': {'alternatives': alts.map((a) => a.toJson()).toList()},
              },
            },
          ],
        },
      });
    } else if (fnName == 'plan_workout_by_muscles') {
      final rawMuscles = args['targetMuscles'];
      final muscles = rawMuscles is List ? rawMuscles.map((e) => e.toString()).toList() : const <String>['Chest', 'Back'];
      final eqConstraint = (args['equipmentConstraint'] ?? 'Home / Bodyweight').toString();

      final plan = buildCatalogWorkoutPlan(targetMuscles: muscles, equipmentConstraint: eqConstraint, userPrompt: '', catalog: _activeCatalog);
      _pendingLiveWorkoutPlan = plan;

      _emitLiveEvent(
        state: _liveState,
        interactionStatus: _currentInteractionStatus,
        transcript: _liveOutputTranscriptBuffer.isNotEmpty ? _liveOutputTranscriptBuffer.toString().trim() : plan.coachSummary,
        workoutPlan: plan,
      );

      _liveSocket?.sendJson({
        'toolResponse': {
          'functionResponses': [
            {
              'id': callId,
              'name': fnName,
              'response': {'output': plan.toJson()},
            },
          ],
        },
      });
    } else if (fnName == 'get_exercise_coaching_details') {
      final exName = (args['exerciseName'] ?? '').toString();
      final matched = findReferencedExercise(exName, _activeCatalog) ?? _activeContextExercise;
      final output = matched != null
          ? <String, dynamic>{
              'id': matched.id,
              'name': matched.name,
              'primaryMuscleGroup': matched.primaryMuscleGroup,
              'equipment': matched.equipment,
              'description': matched.description,
              'keyBiomechanicalCues': _buildBiomechanicalCues(matched),
              'homeAdaptationTip': _buildHomeAdaptationTip(matched, 'At Home / No Weights'),
            }
          : <String, dynamic>{'error': 'Exercise not found in catalog'};

      _liveSocket?.sendJson({
        'toolResponse': {
          'functionResponses': [
            {
              'id': callId,
              'name': fnName,
              'response': {'output': output},
            },
          ],
        },
      });
    }
  }

  Future<void> _closeLiveSocket() async {
    await _liveSocketSubscription?.cancel();
    _liveSocketSubscription = null;
    final socket = _liveSocket;
    _liveSocket = null;
    if (socket != null) {
      try {
        await socket.close();
      } catch (_) {}
    }
  }

  @override
  Future<void> stopLiveCoachSession() async {
    _postSpeechListeningTimer?.cancel();
    _coachAudioPlayingUntil = DateTime.fromMillisecondsSinceEpoch(0);
    _isMicRecording = false;
    if (_enablePlatformCues) {
      try {
        await _audioHostApi.stopMicCapture();
      } catch (_) {}
    }
    await _closeLiveSocket();
    await _stopLiveSpeech();
    await _triggerFeedbackCue();
    _emitLiveEvent(
      state: AiLiveCoachState.disconnected,
      interactionStatus: 'IDLE',
      isMicRecording: false,
      transcript: 'Live Personal Trainer session ended.',
    );
  }

  @override
  void dispose() {
    _postSpeechListeningTimer?.cancel();
    unawaited(_closeLiveSocket());
    if (!_liveController.isClosed) {
      unawaited(_liveController.close());
    }
  }

  void _emitLiveEvent({
    required AiLiveCoachState state,
    String? transcript,
    String? userTranscript,
    String? spokenCue,
    String? interactionStatus,
    bool? isMicRecording,
    AiWorkoutPlan? workoutPlan,
    List<AiExerciseRecommendation>? alternatives,
  }) {
    _liveState = state;
    if (!_liveController.isClosed) {
      _liveController.add(
        AiLiveCoachEvent(
          state: state,
          timestamp: DateTime.now(),
          transcript: transcript,
          userTranscript: userTranscript,
          spokenCue: spokenCue,
          interactionStatus: interactionStatus,
          isMicRecording: isMicRecording,
          workoutPlan: workoutPlan,
          alternatives: alternatives,
        ),
      );
    }
  }

  Future<void> _playPcm24kChunk(String base64Pcm, {int sampleRate = 24000}) async {
    if (base64Pcm.isNotEmpty) {
      final now = DateTime.now();
      final baseTime = _coachAudioPlayingUntil.isAfter(now) ? _coachAudioPlayingUntil : now;
      final pcmBytesCount = (base64Pcm.length * 3) ~/ 4;
      final chunkMs = ((pcmBytesCount ~/ 2) * 1000) ~/ sampleRate;
      _coachAudioPlayingUntil = baseTime.add(Duration(milliseconds: chunkMs));
    }
    if (_onPlayPcm24k != null) {
      await _onPlayPcm24k(base64Pcm, sampleRate);
    }
    if (!_enablePlatformCues || base64Pcm.isEmpty) {
      return;
    }
    try {
      await _audioHostApi.playPcm24k(base64Pcm, sampleRate);
    } catch (_) {
      // Safe no-op in headless widget tests or when channel is not registered.
    }
  }

  Future<void> _stopLiveSpeech() async {
    _postSpeechListeningTimer?.cancel();
    _coachAudioPlayingUntil = DateTime.fromMillisecondsSinceEpoch(0);
    if (_onStopAudio != null) {
      await _onStopAudio();
    }
    if (!_enablePlatformCues) {
      return;
    }
    try {
      await _audioHostApi.stop();
    } catch (_) {
      // Safe no-op in headless widget tests.
    }
  }

  Future<void> _triggerFeedbackCue() async {
    if (!_enablePlatformCues) {
      return;
    }
    try {
      await HapticFeedback.selectionClick();
      await SystemSound.play(SystemSoundType.click);
    } catch (_) {
      // Safe no-op in headless widget tests.
    }
  }

  String _buildSpokenCoachScript(AiChatMessage message) {
    if (message.alternatives != null && message.alternatives!.isNotEmpty) {
      final first = message.alternatives!.first;
      final cue = first.keyBiomechanicalCues.isNotEmpty ? first.keyBiomechanicalCues.first : first.homeAdaptationTip;
      return '${message.text} Top pick: ${first.exerciseName} for ${first.sets} sets of ${first.reps} reps. Form cue: $cue';
    }
    if (message.workoutPlan != null && message.workoutPlan!.exercises.isNotEmpty) {
      final plan = message.workoutPlan!;
      final first = plan.exercises.first;
      return '${plan.title}. ${plan.coachSummary} Starting with ${first.exerciseName} for ${first.sets} sets of ${first.reps} reps.';
    }
    return message.text;
  }

  static String _stripJsonFences(String raw) {
    var cleaned = raw.trim();
    if (cleaned.startsWith('```')) {
      final firstNewline = cleaned.indexOf('\n');
      if (firstNewline != -1) {
        cleaned = cleaned.substring(firstNewline + 1);
      }
      if (cleaned.endsWith('```')) {
        cleaned = cleaned.substring(0, cleaned.length - 3);
      }
    }
    return cleaned.trim();
  }

  List<AiExerciseRecommendation> _tryParseAlternatives(String rawJson, List<ExerciseModel> catalog) {
    try {
      final decoded = jsonDecode(_stripJsonFences(rawJson));
      final list = decoded is Map<String, dynamic> ? decoded['alternatives'] : (decoded is List ? decoded : null);
      if (list is! List) {
        return const [];
      }
      final byId = {for (final e in catalog) e.id: e};
      final byName = {for (final e in catalog) e.name.toLowerCase(): e};

      final results = <AiExerciseRecommendation>[];
      for (final item in list.whereType<Map<String, dynamic>>()) {
        final rec = AiExerciseRecommendation.fromJson(item);
        final match =
            byId[rec.exerciseId] ??
            byName[rec.exerciseName.toLowerCase()] ??
            findReferencedExercise('${rec.exerciseId} ${rec.exerciseName}', catalog);
        if (match != null) {
          results.add(rec.copyWith(exerciseId: match.id, exerciseName: match.name, catalogExercise: match));
        }
      }
      return results;
    } catch (_) {
      return const [];
    }
  }

  AiWorkoutPlan? _tryParseWorkoutPlan(String rawJson, List<ExerciseModel> catalog) {
    try {
      final decoded = jsonDecode(_stripJsonFences(rawJson));
      if (decoded is! Map<String, dynamic>) {
        return null;
      }
      final rawPlan = AiWorkoutPlan.fromJson(decoded);
      final byId = {for (final e in catalog) e.id: e};
      final byName = {for (final e in catalog) e.name.toLowerCase(): e};

      final hydrated = <AiExerciseRecommendation>[];
      for (final rec in rawPlan.exercises) {
        final match =
            byId[rec.exerciseId] ??
            byName[rec.exerciseName.toLowerCase()] ??
            findReferencedExercise('${rec.exerciseId} ${rec.exerciseName}', catalog);
        if (match != null) {
          hydrated.add(rec.copyWith(exerciseId: match.id, exerciseName: match.name, catalogExercise: match));
        }
      }
      if (hydrated.isEmpty) {
        return null;
      }
      return rawPlan.copyWith(exercises: hydrated);
    } catch (_) {
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // Pure Biomechanical Catalog Engines (Deterministic & Offline/Simulator Safe)
  // ---------------------------------------------------------------------------

  static List<ExerciseModel> selectAlternativeCandidates({
    required ExerciseModel target,
    required String constraint,
    required List<ExerciseModel> catalog,
  }) {
    final lowerConstraint = constraint.toLowerCase();
    final wantsBodyweight =
        lowerConstraint.contains('home') ||
        lowerConstraint.contains('no weight') ||
        lowerConstraint.contains('bodyweight') ||
        lowerConstraint.contains('no equipment');
    final wantsDumbbell = lowerConstraint.contains('dumbbell');
    final wantsNoBench = lowerConstraint.contains('no bench') || lowerConstraint.contains('floor');
    final wantsJointFriendly = lowerConstraint.contains('joint') || lowerConstraint.contains('low impact') || lowerConstraint.contains('friendly');

    final sameMuscle = catalog.where((e) {
      if (e.id == target.id) {
        return false;
      }
      return matchesTargetMuscle(e, target.primaryMuscleGroup);
    }).toList();

    Iterable<ExerciseModel> filtered = sameMuscle;

    if (wantsBodyweight) {
      final bw = filtered.where((e) => e.equipment.toLowerCase() == 'bodyweight').toList();
      if (bw.isNotEmpty) {
        filtered = bw;
      }
    } else if (wantsDumbbell) {
      final db = filtered.where((e) {
        final eq = e.equipment.toLowerCase();
        return eq == 'dumbbell' || eq == 'bodyweight';
      }).toList();
      if (db.isNotEmpty) {
        filtered = db;
      }
    }

    if (wantsNoBench) {
      final noBench = filtered.where((e) => !e.name.toLowerCase().contains('bench')).toList();
      if (noBench.isNotEmpty) {
        filtered = noBench;
      }
    }

    final sorted = filtered.toList()
      ..sort((a, b) {
        final scoreA = _scoreCandidate(a, wantsBodyweight: wantsBodyweight, wantsDumbbell: wantsDumbbell, wantsJointFriendly: wantsJointFriendly);
        final scoreB = _scoreCandidate(b, wantsBodyweight: wantsBodyweight, wantsDumbbell: wantsDumbbell, wantsJointFriendly: wantsJointFriendly);
        return scoreB.compareTo(scoreA);
      });

    if (sorted.isNotEmpty) {
      return sorted;
    }

    // Fallback to any bodyweight/matching exercise in the catalog
    return catalog.where((e) => e.id != target.id).toList();
  }

  static int _scoreCandidate(
    ExerciseModel candidate, {
    required bool wantsBodyweight,
    required bool wantsDumbbell,
    required bool wantsJointFriendly,
  }) {
    var score = 0;
    final isHd = candidate.animationType == 'rive' || candidate.animationType == 'movekit';
    if (isHd) {
      score += 50;
    }

    final eq = candidate.equipment.toLowerCase();
    if (wantsBodyweight && eq == 'bodyweight') {
      score += 40;
    }
    if (wantsDumbbell && eq == 'dumbbell') {
      score += 35;
    }
    if (wantsJointFriendly && (eq == 'bodyweight' || eq == 'cable' || eq == 'machine' || eq == 'dumbbell')) {
      score += 25;
    }
    return score;
  }

  static List<AiExerciseRecommendation> buildCatalogAlternatives({
    required ExerciseModel target,
    required String constraint,
    required List<ExerciseModel> catalog,
  }) {
    final candidates = selectAlternativeCandidates(target: target, constraint: constraint, catalog: catalog);

    final selected = candidates.take(3).toList();
    return selected.map((candidate) {
      return _buildRecommendationForExercise(candidate, replacedExercise: target, constraint: constraint);
    }).toList();
  }

  static List<ExerciseModel> filterCatalogByMusclesAndEquipment({
    required List<String> targetMuscles,
    required String equipmentConstraint,
    required List<ExerciseModel> catalog,
  }) {
    final lowerEq = equipmentConstraint.toLowerCase();
    final onlyBodyweight = lowerEq.contains('home') || lowerEq.contains('bodyweight') || lowerEq.contains('no weight');
    final onlyDumbbell = lowerEq.contains('dumbbell');

    final matched = catalog.where((exercise) {
      final muscleMatch = targetMuscles.any((m) => matchesTargetMuscle(exercise, m));
      if (!muscleMatch) {
        return false;
      }

      final eq = exercise.equipment.toLowerCase();
      if (onlyBodyweight) {
        return eq == 'bodyweight';
      }
      if (onlyDumbbell) {
        return eq == 'dumbbell' || eq == 'bodyweight';
      }
      return true;
    }).toList();

    matched.sort((a, b) {
      final aRive = a.animationType == 'rive';
      final bRive = b.animationType == 'rive';
      if (aRive != bRive) {
        return aRive ? -1 : 1;
      }
      final aHd = a.animationType == 'movekit';
      final bHd = b.animationType == 'movekit';
      if (aHd != bHd) {
        return aHd ? -1 : 1;
      }
      return a.name.compareTo(b.name);
    });

    return matched.isNotEmpty ? matched : catalog;
  }

  static AiWorkoutPlan buildCatalogWorkoutPlan({
    required List<String> targetMuscles,
    required String equipmentConstraint,
    required String userPrompt,
    required List<ExerciseModel> catalog,
  }) {
    final normalizedMuscles = targetMuscles.isEmpty ? const <String>['Full Body'] : targetMuscles;
    final picked = <ExerciseModel>[];
    final seenIds = <String>{};

    // Pick top exercises per requested muscle group so every chosen muscle is covered
    for (final muscle in normalizedMuscles) {
      final pool = filterCatalogByMusclesAndEquipment(targetMuscles: [muscle], equipmentConstraint: equipmentConstraint, catalog: catalog);
      final perMuscleLimit = normalizedMuscles.length == 1 ? 4 : 2;
      var count = 0;
      for (final ex in pool) {
        if (seenIds.add(ex.id)) {
          picked.add(ex);
          count++;
          if (count >= perMuscleLimit || picked.length >= 6) {
            break;
          }
        }
      }
      if (picked.length >= 6) {
        break;
      }
    }

    if (picked.isEmpty && catalog.isNotEmpty) {
      picked.addAll(catalog.take(4));
    }

    final recommendations = picked.map((e) => _buildRecommendationForExercise(e, constraint: equipmentConstraint)).toList();

    final localizedMuscles = normalizedMuscles.map((m) => t.translateMuscle(m)).toList();
    final muscleTitle = localizedMuscles.join(' & ');
    final modeSuffix = _localizedPlanModeSuffix(equipmentConstraint);
    final localizedEq = t.translateEquipment(equipmentConstraint);

    return AiWorkoutPlan(
      title: '$muscleTitle • $modeSuffix',
      targetMuscles: normalizedMuscles,
      coachSummary: _localizedWorkoutPlanSummary(recommendations.length, muscleTitle, localizedEq),
      exercises: recommendations,
    );
  }

  static bool matchesTargetMuscle(ExerciseModel exercise, String requestedMuscle) {
    final req = requestedMuscle.trim().toLowerCase();
    final primary = exercise.primaryMuscleGroup.toLowerCase();
    final name = exercise.name.toLowerCase();
    final desc = exercise.description.toLowerCase();

    if (primary == req) {
      return true;
    }

    switch (req) {
      case 'chest':
      case 'pectorals':
        return primary == 'chest' || name.contains('push up') || name.contains('bench') || name.contains('chest');
      case 'back':
      case 'lats':
        return primary == 'back' ||
            name.contains('row') ||
            name.contains('pull up') ||
            name.contains('chin up') ||
            name.contains('pulldown') ||
            name.contains('deadlift');
      case 'shoulders':
      case 'delts':
        return primary == 'shoulders' ||
            name.contains('shoulder') ||
            name.contains('delt') ||
            name.contains('overhead press') ||
            name.contains('lateral raise') ||
            name.contains('arnold press');
      case 'biceps':
        return (primary == 'arms' || primary == 'upper arms' || primary == 'back') &&
            (name.contains('curl') || name.contains('bicep') || name.contains('chin up') || desc.contains('bicep'));
      case 'triceps':
        return (primary == 'arms' || primary == 'upper arms' || primary == 'chest') &&
            (name.contains('tricep') ||
                name.contains('pushdown') ||
                name.contains('skull crusher') ||
                name.contains('dip') ||
                name.contains('diamond') ||
                desc.contains('tricep'));
      case 'arms':
        return primary == 'arms' || primary == 'upper arms' || primary == 'lower arms';
      case 'quadriceps':
      case 'quads':
        return (primary == 'legs' || primary == 'upper legs') &&
            (name.contains('squat') ||
                name.contains('lunge') ||
                name.contains('leg press') ||
                name.contains('leg extension') ||
                desc.contains('quad'));
      case 'hamstrings':
        return (primary == 'legs' || primary == 'upper legs' || primary == 'back') &&
            (name.contains('romanian') ||
                name.contains('leg curl') ||
                name.contains('hamstring') ||
                name.contains('deadlift') ||
                desc.contains('hamstring'));
      case 'glutes':
        return (primary == 'legs' || primary == 'upper legs' || primary == 'full body') &&
            (name.contains('glute') ||
                name.contains('split squat') ||
                name.contains('lunge') ||
                name.contains('squat') ||
                name.contains('romanian') ||
                name.contains('swing') ||
                desc.contains('glute'));
      case 'calves':
        return (primary == 'legs' || primary == 'lower legs') && (name.contains('calf') || desc.contains('calf') || desc.contains('gastrocnemius'));
      case 'legs':
        return primary == 'legs' || primary == 'upper legs' || primary == 'lower legs';
      case 'abs / core':
      case 'abs':
      case 'core':
      case 'waist':
        return primary == 'core' ||
            primary == 'waist' ||
            name.contains('plank') ||
            name.contains('crunch') ||
            name.contains('leg raise') ||
            name.contains('twist') ||
            name.contains('rollout') ||
            name.contains('climber');
      case 'full body':
      case 'cardio':
        return primary == 'full body' || primary == 'cardio' || name.contains('burpee') || name.contains('thruster') || name.contains('swing');
      default:
        return primary.contains(req) || name.contains(req) || desc.contains(req);
    }
  }

  static AiExerciseRecommendation _buildRecommendationForExercise(
    ExerciseModel exercise, {
    ExerciseModel? replacedExercise,
    required String constraint,
  }) {
    final isBodyweight = exercise.equipment.toLowerCase() == 'bodyweight';
    const sets = 3;
    final reps = isBodyweight ? 15 : 10;
    final restSeconds = isBodyweight ? 45 : 75;

    final matchReason = _localizedMatchReason(exercise, replacedExercise: replacedExercise, constraint: constraint);

    final homeTip = _buildHomeAdaptationTip(exercise, constraint);
    final cues = _buildBiomechanicalCues(exercise);

    return AiExerciseRecommendation(
      exerciseId: exercise.id,
      exerciseName: exercise.name,
      matchReason: matchReason,
      homeAdaptationTip: homeTip,
      sets: sets,
      reps: reps,
      restSeconds: restSeconds,
      keyBiomechanicalCues: cues,
      catalogExercise: exercise,
    );
  }

  static String _localizedAlternativesChatFallback(String exerciseName, String constraint, String topNames) {
    final locConstraint = t.translateConstraint(constraint);
    switch (LocaleSettings.currentLocale) {
      case AppLocale.es:
        return 'Aquí tienes las mejores alternativas ($locConstraint) para $exerciseName de tu catálogo CommunityFitness: $topNames. Toca cualquier tarjeta para ver su demostración 3D Rive.';
      case AppLocale.ca:
        return 'Aquí tens les millors alternatives ($locConstraint) per a $exerciseName del teu catàleg CommunityFitness: $topNames. Toca qualsevol targeta per veure la seva demostració 3D Rive.';
      case AppLocale.fr:
        return 'Voici les meilleures alternatives ($locConstraint) pour $exerciseName de votre catalogue CommunityFitness : $topNames. Appuyez sur une carte pour voir la démonstration 3D Rive.';
      case AppLocale.pt:
        return 'Aqui estão as melhores alternativas ($locConstraint) para $exerciseName do seu catálogo CommunityFitness: $topNames. Toque em qualquer cartão para ver a demonstração 3D Rive.';
      case AppLocale.en:
        return 'Here are the best $constraint alternatives for $exerciseName from your CommunityFitness catalog: $topNames. Tap any card below to inspect its 3D Rive form demonstration.';
    }
  }

  static String _localizedExerciseCoachingFallback(ExerciseModel exercise, List<String> cues, String tip) {
    final locMuscle = t.translateMuscle(exercise.primaryMuscleGroup);
    switch (LocaleSettings.currentLocale) {
      case AppLocale.es:
        return '${exercise.name} ($locMuscle • ${exercise.equipment}): ${exercise.description} Claves biomecánicas: ${cues.join(" ")} Adaptación en casa: $tip';
      case AppLocale.ca:
        return '${exercise.name} ($locMuscle • ${exercise.equipment}): ${exercise.description} Claus biomecàniques: ${cues.join(" ")} Adaptació a casa: $tip';
      case AppLocale.fr:
        return '${exercise.name} ($locMuscle • ${exercise.equipment}) : ${exercise.description} Clés biomécaniques : ${cues.join(" ")} Adaptation maison : $tip';
      case AppLocale.pt:
        return '${exercise.name} ($locMuscle • ${exercise.equipment}): ${exercise.description} Dicas biomecânicas: ${cues.join(" ")} Adaptação em casa: $tip';
      case AppLocale.en:
        return '${exercise.name} (${exercise.primaryMuscleGroup} • ${exercise.equipment}): ${exercise.description} Key cues: ${cues.join(" ")} Adaptation tip: $tip';
    }
  }

  static String _localizedGeneralCoachFallback(String modelName) {
    switch (LocaleSettings.currentLocale) {
      case AppLocale.es:
        return 'ATLAS: Concéntrate en un tempo excéntrico controlado (2-3 segundos al bajar) y rango completo de movimiento.';
      case AppLocale.ca:
        return 'ATLAS: Concentra\'t en un tempo excèntric controlat (2-3 segons en baixar) i rang complet de moviment.';
      case AppLocale.fr:
        return 'ATLAS : Concentrez-vous sur un tempo excentrique contrôlé (2-3 secondes à la descente) et une amplitude complète.';
      case AppLocale.pt:
        return 'ATLAS: Concentre-se num tempo excêntrico controlado (2-3 segundos a descer) e amplitude total de movimento.';
      case AppLocale.en:
        return 'ATLAS: Focus on controlled eccentric tempo (2-3 seconds down) and full range of motion.';
    }
  }

  static String _localizedLiveConnectedMsg(ExerciseModel? activeExercise) {
    switch (LocaleSettings.currentLocale) {
      case AppLocale.es:
        return activeExercise != null
            ? 'ATLAS en vivo listo para ${activeExercise.name}. ¡Ya te escucho, habla cuando quieras!'
            : 'ATLAS en vivo listo. ¡Ya te escucho, habla o envía tu consulta!';
      case AppLocale.ca:
        return activeExercise != null
            ? 'ATLAS en viu llest per a ${activeExercise.name}. Ja t\'escolto, parla quan vulguis!'
            : 'ATLAS en viu llest. Ja t\'escolto, parla o envia la teva consulta!';
      case AppLocale.fr:
        return activeExercise != null
            ? 'ATLAS en direct prêt pour ${activeExercise.name}. Je vous écoute, parlez quand vous voulez !'
            : 'ATLAS en direct prêt. Je vous écoute, parlez ou envoyez votre demande !';
      case AppLocale.pt:
        return activeExercise != null
            ? 'ATLAS ao vivo pronto para ${activeExercise.name}. Já estou a ouvir, fale quando quiser!'
            : 'ATLAS ao vivo pronto. Já estou a ouvir, fale ou envie a sua pergunta!';
      case AppLocale.en:
        return activeExercise != null
            ? 'ATLAS Live ready for ${activeExercise.name}. Listening now—speak whenever you are ready!'
            : 'ATLAS Live ready. Listening now—speak or send your question!';
    }
  }

  static String _localizedLiveOfflineWelcome(ExerciseModel? activeExercise) {
    switch (LocaleSettings.currentLocale) {
      case AppLocale.es:
        return activeExercise != null
            ? 'Listo para guiarte en ${activeExercise.name} o cambiarlo por una variante en casa con peso corporal. Dime con qué material cuentas o qué músculos quieres entrenar.'
            : 'Dime qué músculos quieres entrenar hoy o pide una alternativa en casa sin pesas para cualquier ejercicio del catálogo.';
      case AppLocale.ca:
        return activeExercise != null
            ? 'Llest per guiar-te en ${activeExercise.name} o canviar-lo per una variant a casa amb pes corporal. Digues-me quin material tens o quins músculs vols entrenar.'
            : 'Digues-me quins músculs vols entrenar avui o demana una alternativa a casa sense peses per a qualsevol exercici del catàleg.';
      case AppLocale.fr:
        return activeExercise != null
            ? 'Prêt à vous guider sur ${activeExercise.name} ou à le remplacer par une variante au poids du corps à la maison. Dites-moi quel matériel vous avez ou quels muscles cibler.'
            : 'Dites-moi quels muscles vous voulez entraîner aujourd\'hui ou demandez une alternative maison sans poids pour tout exercice du catalogue.';
      case AppLocale.pt:
        return activeExercise != null
            ? 'Pronto para orientar em ${activeExercise.name} ou trocá-lo por uma variação em casa com peso corporal. Diga-me que equipamento tem ou que músculos quer treinar.'
            : 'Diga-me que músculos quer treinar hoje ou peça uma alternativa em casa sem pesos para qualquer exercício do catálogo.';
      case AppLocale.en:
        return activeExercise != null
            ? 'Ready to coach your ${activeExercise.name} or swap it for a home bodyweight variation. Tell me what equipment you have or which muscles you want to hit.'
            : 'Tell me which muscles you want to train today, or ask for a no-weights home alternative for any exercise in the catalog.';
    }
  }

  static String _localizedMicListeningPrompt() {
    switch (LocaleSettings.currentLocale) {
      case AppLocale.es:
        return 'Escuchando tu micrófono... Habla con ATLAS.';
      case AppLocale.ca:
        return 'Escoltant el teu micròfon... Parla amb ATLAS.';
      case AppLocale.fr:
        return 'Écoute de votre microphone... Parlez à ATLAS.';
      case AppLocale.pt:
        return 'A ouvir o seu microfone... Fale com o ATLAS.';
      case AppLocale.en:
        return 'Listening to your microphone... Speak to ATLAS.';
    }
  }

  static String _localizedPlanModeSuffix(String equipmentConstraint) {
    final lower = equipmentConstraint.toLowerCase();
    final isHome =
        lower.contains('home') ||
        lower.contains('casa') ||
        lower.contains('maison') ||
        lower.contains('bodyweight') ||
        lower.contains('peso corporal') ||
        lower.contains('pes corporal') ||
        lower.contains('poids du corps');
    final isDumbbell =
        lower.contains('dumbbell') ||
        lower.contains('mancuerna') ||
        lower.contains('manuell') ||
        lower.contains('haltère') ||
        lower.contains('haltere');

    switch (LocaleSettings.currentLocale) {
      case AppLocale.es:
        return isHome ? 'Sesión en Casa Peso Corporal' : (isDumbbell ? 'Sesión con Mancuernas' : 'Plan de Hipertrofia y Fuerza');
      case AppLocale.ca:
        return isHome ? 'Sessió a Casa Pes Corporal' : (isDumbbell ? 'Sessió amb Manuelles' : 'Pla d\'Hipertròfia i Força');
      case AppLocale.fr:
        return isHome ? 'Séance Maison Poids du Corps' : (isDumbbell ? 'Séance Haltères' : 'Programme Hypertrophie & Force');
      case AppLocale.pt:
        return isHome ? 'Sessão em Casa Peso Corporal' : (isDumbbell ? 'Sessão com Halteres' : 'Plano de Hipertrofia e Força');
      case AppLocale.en:
        return isHome ? 'Home Bodyweight Session' : (isDumbbell ? 'Dumbbell Sculpt Session' : 'Hypertrophy & Strength Plan');
    }
  }

  static String _localizedWorkoutPlanSummary(int count, String muscleTitle, String equipmentConstraint) {
    switch (LocaleSettings.currentLocale) {
      case AppLocale.es:
        return 'Diseñado por ATLAS usando $count ejercicios de tu catálogo CommunityFitness para $muscleTitle ($equipmentConstraint). Toca cualquier ejercicio para abrir su demostración animada.';
      case AppLocale.ca:
        return 'Dissenyat per ATLAS utilitzant $count exercicis del teu catàleg CommunityFitness per a $muscleTitle ($equipmentConstraint). Toca qualsevol exercici per obrir la seva demostració animada.';
      case AppLocale.fr:
        return 'Conçu par ATLAS à partir de $count exercices de votre catalogue CommunityFitness ciblant $muscleTitle ($equipmentConstraint). Appuyez sur un mouvement pour lancer sa démonstration animée.';
      case AppLocale.pt:
        return 'Criado pelo ATLAS usando $count exercícios do seu catálogo CommunityFitness para $muscleTitle ($equipmentConstraint). Toque em qualquer movimento para abrir a demonstração animada.';
      case AppLocale.en:
        return 'Built by ATLAS using $count exercises from your CommunityFitness catalog targeting $muscleTitle ($equipmentConstraint). Tap any movement to launch its animated demonstration.';
    }
  }

  static String _localizedMatchReason(ExerciseModel exercise, {ExerciseModel? replacedExercise, required String constraint}) {
    final locMuscle = t.translateMuscle(exercise.primaryMuscleGroup);
    final locConstraint = t.translateConstraint(constraint);
    switch (LocaleSettings.currentLocale) {
      case AppLocale.es:
        return replacedExercise != null
            ? 'Reemplaza a ${replacedExercise.name} para activar $locMuscle usando ${exercise.equipment.toLowerCase()} ($locConstraint).'
            : 'Trabaja $locMuscle con mecánica de ${exercise.equipment} (${exercise.description})';
      case AppLocale.ca:
        return replacedExercise != null
            ? 'Substitueix ${replacedExercise.name} per activar $locMuscle utilitzant ${exercise.equipment.toLowerCase()} ($locConstraint).'
            : 'Treballa $locMuscle amb mecànica de ${exercise.equipment} (${exercise.description})';
      case AppLocale.fr:
        return replacedExercise != null
            ? 'Remplace ${replacedExercise.name} pour activer $locMuscle avec ${exercise.equipment.toLowerCase()} ($locConstraint).'
            : 'Cible $locMuscle avec une mécanique ${exercise.equipment} (${exercise.description})';
      case AppLocale.pt:
        return replacedExercise != null
            ? 'Substitui ${replacedExercise.name} para ativar $locMuscle usando ${exercise.equipment.toLowerCase()} ($locConstraint).'
            : 'Trabalha $locMuscle com mecânica de ${exercise.equipment} (${exercise.description})';
      case AppLocale.en:
        return replacedExercise != null
            ? 'Replaces ${replacedExercise.name} for ${exercise.primaryMuscleGroup} activation using ${exercise.equipment.toLowerCase()} ($constraint).'
            : 'Targets ${exercise.primaryMuscleGroup} with ${exercise.equipment} mechanics (${exercise.description})';
    }
  }

  static String _buildHomeAdaptationTip(ExerciseModel exercise, String constraint) {
    final id = exercise.id.toLowerCase();
    final eq = exercise.equipment.toLowerCase();
    final locConstraint = t.translateConstraint(constraint);

    switch (LocaleSettings.currentLocale) {
      case AppLocale.es:
        if (id.contains('push_up')) {
          return 'En casa sin pesas: eleva los pies en un sofá para enfatizar el pecho superior o usa una mochila con peso y baja en 3 segundos.';
        }
        if (id.contains('dips')) {
          return 'En casa: usa dos sillas firmes o el borde de un sofá estable, manteniendo los hombros lejos de las orejas.';
        }
        if (id.contains('pull_up') || id.contains('chin_up')) {
          return 'En casa: usa una barra de puerta o haz remo invertido debajo de una mesa resistente sujetando el borde.';
        }
        if (id.contains('calf_raise')) {
          return 'En casa: apóyate en el borde de un escalón para un estiramiento profundo del talón y pausa 2 segundos arriba.';
        }
        if (id.contains('squat') || id.contains('lunge')) {
          return 'En casa sin barras pesadas: usa un tempo 3-1-1 o haz sentadilla búlgara a una pierna apoyando el pie trasero en el sofá.';
        }
        if (eq == 'bodyweight') {
          return 'Sin pesas: aumenta la intensidad bajando en 3 segundos (fase excéntrica) y reduciendo el descanso a 45 segundos.';
        }
        if (eq == 'dumbbell') {
          return 'Consejo con mancuernas en casa: añade una pausa isométrica de 1 segundo en máxima contracción en cada repetición.';
        }
        return 'Adaptación ($locConstraint): prioriza el control escapular estricto y el volumen progresivo de repeticiones en casa.';

      case AppLocale.ca:
        if (id.contains('push_up')) {
          return 'A casa sense peses: eleva els peus al sofà per treballar el pit superior o utilitza una motxilla amb pes i baixa en 3 segons.';
        }
        if (id.contains('dips')) {
          return 'A casa: utilitza dues cadires fermes o la vora del sofà mantenint les espatlles allunyades de les orelles.';
        }
        if (id.contains('pull_up') || id.contains('chin_up')) {
          return 'A casa: utilitza una barra de porta o fes rem invertit sota una taula resistent.';
        }
        if (eq == 'bodyweight') {
          return 'Sense peses: augmenta la intensitat amb una fase excèntrica de 3 segons i descansos de 45 segons.';
        }
        return 'Adaptació ($locConstraint): prioritza el control escapular estricte i el volum progressiu a casa.';

      case AppLocale.fr:
        if (id.contains('push_up')) {
          return 'À la maison sans poids : surélevez les pieds sur un canapé pour le haut des pectoraux ou portez un sac à dos lesté avec 3 secondes de descente.';
        }
        if (id.contains('dips')) {
          return 'À la maison : utilisez deux chaises solides ou le bord d\'un canapé stable en gardant les épaules basses.';
        }
        if (id.contains('pull_up') || id.contains('chin_up')) {
          return 'À la maison : utilisez une barre de traction de porte ou faites du rowing inversé sous une table robuste.';
        }
        if (eq == 'bodyweight') {
          return 'Sans poids requis : augmentez l\'intensité en ralentissant la phase excentrique à 3 secondes avec 45 secondes de repos.';
        }
        return 'Adaptation ($locConstraint) : privilégiez un contrôle scapulaire strict et un volume progressif à domicile.';

      case AppLocale.pt:
        if (id.contains('push_up')) {
          return 'Em casa sem pesos: eleve os pés no sofá para focar o peito superior ou use uma mochila com peso e desça em 3 segundos.';
        }
        if (id.contains('dips')) {
          return 'Em casa: use duas cadeiras firmes ou a borda de um sofá estável, mantendo os ombros longe das orelhas.';
        }
        if (id.contains('pull_up') || id.contains('chin_up')) {
          return 'Em casa: use uma barra de porta ou faça remada invertida debaixo de uma mesa resistente.';
        }
        if (eq == 'bodyweight') {
          return 'Sem pesos: aumente a intensidade descendo em 3 segundos na fase excêntrica e descansando 45 segundos.';
        }
        return 'Adaptação ($locConstraint): foque no controlo escapular estrito e volume progressivo em casa.';

      case AppLocale.en:
        if (id.contains('push_up')) {
          return 'At home without weights: elevate feet on a sofa for upper-chest bias, or wear a loaded backpack and use a 3-second lowering tempo.';
        }
        if (id.contains('dips')) {
          return 'At home: use two sturdy dining chairs or the edge of a stable couch, keeping shoulders depressed away from your ears.';
        }
        if (id.contains('pull_up') || id.contains('chin_up')) {
          return 'At home: use a doorway pull-up bar, or perform inverted rows under a sturdy dining table gripping the edge.';
        }
        if (id.contains('calf_raise')) {
          return 'At home: stand on the edge of a stair step for a deep heel stretch and pause 2 seconds at peak contraction.';
        }
        if (id.contains('squat') || id.contains('lunge')) {
          return 'At home without heavy bars: switch to a 3-1-1 tempo or single-leg Bulgarian split squats with rear foot on a couch.';
        }
        if (eq == 'bodyweight') {
          return 'No weights required: increase intensity by slowing the eccentric phase to 3 seconds and minimizing rest to 45 seconds.';
        }
        if (eq == 'dumbbell') {
          return 'Home dumbbell tip: if using lighter dumbbells at home, add a 1-second isometric squeeze at peak contraction on every rep.';
        }
        return 'Constraint ($constraint): focus on strict scapular control and progressive rep volume if training with minimal home gear.';
    }
  }

  static List<String> _buildBiomechanicalCues(ExerciseModel exercise) {
    final muscle = exercise.primaryMuscleGroup.toLowerCase();
    switch (LocaleSettings.currentLocale) {
      case AppLocale.es:
        switch (muscle) {
          case 'chest':
            return const [
              'Retrae y deprime las escápulas antes de iniciar el empuje.',
              'Controla el descenso excéntrico en 3 segundos y empuja con la base de la palma.',
            ];
          case 'back':
            return const [
              'Inicia el tirón llevando los codos hacia la cadera sin flexionar las muñecas.',
              'Mantén la retracción escapular máxima durante 1 segundo completo en cada repetición.',
            ];
          case 'legs':
          case 'upper legs':
          case 'lower legs':
            return const [
              'Activa el core 360 grados y alinea las rodillas con el segundo dedo del pie.',
              'Empuja desde el mediopié y el talón manteniendo la columna neutra.',
            ];
          case 'shoulders':
            return const [
              'Mantén las costillas alineadas sobre la pelvis evitando arquear la zona lumbar.',
              'Guía el movimiento con los codos en el plano escapular (30 grados hacia delante).',
            ];
          case 'arms':
          case 'upper arms':
            return const [
              'Fija los brazos al torso para que toda la tensión recaiga en bíceps o tríceps.',
              'Estira el músculo por completo abajo antes de contraer un segundo arriba.',
            ];
          default:
            return const [
              'Mantén retroversión pélvica activa y exhala con fuerza en el punto de máximo esfuerzo.',
              'Prioriza un tempo fluido y controlado sin usar impulso.',
            ];
        }
      case AppLocale.ca:
        return const [
          'Mantén el control escapular i un tempo excèntric de 3 segons.',
          'Prioritza el rang complet de moviment sense utilitzar impuls.',
        ];
      case AppLocale.fr:
        return const [
          'Engagez vos omoplates et contrôlez la phase excentrique sur 3 secondes.',
          'Privilégiez une amplitude complète et un tempo fluide sans élan.',
        ];
      case AppLocale.pt:
        return const [
          'Mantenha a retração escapular e controle a descida excêntrica durante 3 segundos.',
          'Priorize a amplitude total de movimento sem usar impulso.',
        ];
      case AppLocale.en:
        switch (muscle) {
          case 'chest':
            return const [
              'Retract and depress your shoulder blades before initiating the press.',
              'Control the 3-second eccentric stretch and drive through the mid-palm.',
            ];
          case 'back':
            return const [
              'Initiate the pull by driving elbows toward your hips rather than curling with the wrists.',
              'Hold peak scapular retraction for 1 full second at the top of each rep.',
            ];
          case 'legs':
          case 'upper legs':
          case 'lower legs':
            return const [
              'Brace your core 360 degrees and track knees in line with your second toe.',
              'Drive through your mid-foot and heel while maintaining a neutral spine.',
            ];
          case 'shoulders':
            return const [
              'Keep ribs stacked over your pelvis to avoid lower-back hyperextension.',
              'Lead with the elbows in the scapular plane (30 degrees forward of the torso).',
            ];
          case 'arms':
          case 'upper arms':
            return const [
              'Pin your upper arms to your sides so all torque stays on the elbow flexors/extensors.',
              'Fully lengthen the muscle at the bottom before squeezing the concentric peak.',
            ];
          default:
            return const [
              'Maintain posterior pelvic tilt and exhale forcefully during peak exertion.',
              'Prioritize smooth, controlled tempo over momentum on every repetition.',
            ];
        }
    }
  }

  static ExerciseModel? findReferencedExercise(String text, List<ExerciseModel> catalog) {
    final lower = text.toLowerCase();
    // Sort by longest name first so "Incline Dumbbell Press" matches before "Press"
    final sorted = List<ExerciseModel>.from(catalog)..sort((a, b) => b.name.length.compareTo(a.name.length));

    for (final exercise in sorted) {
      if (lower.contains(exercise.name.toLowerCase()) || lower.contains(exercise.id.replaceAll('_', ' ').toLowerCase())) {
        return exercise;
      }
    }
    return null;
  }

  static List<String> extractTargetMusclesFromText(String text) {
    final lower = text.toLowerCase();
    final found = <String>[];

    final mapping = <String, List<String>>{
      'Chest': ['chest', 'pec', 'push', 'pecho', 'pectoral', 'pit', 'poitrine', 'pectoraux', 'peito'],
      'Back': ['back', 'lat', 'pull', 'espalda', 'dorsal', 'esquena', 'dos', 'costas'],
      'Shoulders': ['shoulder', 'delt', 'hombro', 'deltoide', 'espatll', 'épaule', 'epaule', 'ombro'],
      'Biceps': ['bicep', 'curl', 'bíceps'],
      'Triceps': ['tricep', 'dip', 'tríceps', 'fondos', 'fons'],
      'Quadriceps': [
        'quad',
        'squat',
        'leg',
        'pierna',
        'cuádriceps',
        'cuadriceps',
        'sentadilla',
        'cama',
        'cames',
        'esquat',
        'jambe',
        'cuisse',
        'perna',
        'agachamento',
      ],
      'Hamstrings': ['hamstring', 'posterior', 'hinge', 'isquio', 'femoral', 'ischio'],
      'Glutes': ['glute', 'hip', 'glúteo', 'gluteo', 'cadera', 'gluti', 'fessier', 'hanche'],
      'Calves': ['calf', 'calves', 'gemelo', 'pantorrilla', 'bessó', 'bessons', 'mollet', 'gémeo', 'gemeo', 'panturrilha'],
      'Abs / Core': ['abs', 'core', 'plank', 'ab ', 'stomach', 'six pack', 'abdomen', 'abdominal', 'abdos', 'gainage', 'abdómen'],
    };

    mapping.forEach((canonical, keywords) {
      if (keywords.any((k) => lower.contains(k))) {
        found.add(canonical);
      }
    });

    return found;
  }

  static String inferConstraintFromMessage(String text) {
    final lower = text.toLowerCase();
    if (lower.contains('home') ||
        lower.contains('en casa') ||
        lower.contains('a casa') ||
        lower.contains('à la maison') ||
        lower.contains('a la maison') ||
        lower.contains('em casa') ||
        lower.contains('no weight') ||
        lower.contains('sin pesa') ||
        lower.contains('sense pes') ||
        lower.contains('sans poids') ||
        lower.contains('sem peso') ||
        lower.contains('bodyweight') ||
        lower.contains('peso corporal') ||
        lower.contains('pes corporal') ||
        lower.contains('poids du corps') ||
        lower.contains('without weight') ||
        lower.contains('no equipment') ||
        lower.contains('sin equipo') ||
        lower.contains('sense material') ||
        lower.contains('sans matériel') ||
        lower.contains('sem equipamento')) {
      return 'At Home / No Weights';
    }
    if (lower.contains('dumbbell') ||
        lower.contains('mancuerna') ||
        lower.contains('manuell') ||
        lower.contains('haltère') ||
        lower.contains('haltere')) {
      return 'Dumbbells Only';
    }
    if (lower.contains('no bench') ||
        lower.contains('sin banco') ||
        lower.contains('sense banc') ||
        lower.contains('sans banc') ||
        lower.contains('sem banco')) {
      return 'No Bench';
    }
    if (lower.contains('joint') ||
        lower.contains('pain') ||
        lower.contains('dolor') ||
        lower.contains('injury') ||
        lower.contains('lesión') ||
        lower.contains('lesion') ||
        lower.contains('lesió') ||
        lower.contains('douleur') ||
        lower.contains('articulation') ||
        lower.contains('dor ') ||
        lower.contains('articular')) {
      return 'Joint Friendly';
    }
    return 'All Equipment';
  }
}
