// Pigeon schema definition for strongly-typed Live Coach audio & microphone streaming.
// Run `dart run pigeon --input pigeons/live_coach_audio_api.dart` to regenerate bindings.

/// Host API implemented by iOS (`AVAudioEngine` / `AVSpeechSynthesizer` / `SFSpeechRecognizer`)
/// and Android (`AudioTrack` / `AudioRecord` / `TextToSpeech` / `SpeechRecognizer`).
abstract class LiveCoachAudioHostApi {
  /// Plays a base64-encoded 24kHz 16-bit mono PCM audio chunk streamed from `gemini-3.8-live`.
  bool playPcm24k(String base64Pcm, int sampleRate);

  /// Speaks the given coaching cue via native platform TTS when running in offline fallback mode.
  bool speak(String text);

  /// Immediately stops any active 24kHz PCM playback, TTS utterance, or microphone capture (barge-in).
  bool stop();

  /// Starts 16kHz 16-bit mono PCM microphone capture and streams chunks back via [LiveCoachAudioFlutterApi.onMicPcm16kChunk].
  bool startMicCapture();

  /// Stops 16kHz microphone capture and returns any native speech-to-text transcript recognized during the turn.
  String stopMicCapture();

  /// Updates the active BCP-47 speech recognition & TTS language (e.g. `es-ES`, `en-US`, `ca-ES`, `fr-FR`, `pt-PT`).
  bool setLanguage(String languageCode);
}

/// Flutter API invoked from native iOS/Android as 16kHz PCM microphone chunks are captured.
abstract class LiveCoachAudioFlutterApi {
  /// Delivers a base64-encoded 16kHz 16-bit little-endian mono PCM audio chunk to Dart.
  void onMicPcm16kChunk(String base64Pcm);
}
