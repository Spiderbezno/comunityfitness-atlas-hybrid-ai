import AVFoundation
import Flutter
import Speech
import UIKit
#if canImport(FoundationModels)
import FoundationModels
#endif

// MARK: - Pigeon Generated Bindings (LiveCoachAudioApi)

final class PigeonError: Error {
  let code: String
  let message: String?
  let details: Any?

  init(code: String, message: String?, details: Any?) {
    self.code = code
    self.message = message
    self.details = details
  }
}

private func wrapResult(_ result: Any?) -> [Any?] {
  return [result]
}

private func wrapError(_ error: Any) -> [Any?] {
  if let pigeonError = error as? PigeonError {
    return [
      pigeonError.code,
      pigeonError.message,
      pigeonError.details,
    ]
  }
  if let flutterError = error as? FlutterError {
    return [
      flutterError.code,
      flutterError.message,
      flutterError.details,
    ]
  }
  return [
    "\(error)",
    "\(type(of: error))",
    "Stacktrace: \(Thread.callStackSymbols)",
  ]
}

private func createConnectionError(withChannelName channelName: String) -> PigeonError {
  return PigeonError(
    code: "channel-error",
    message: "Unable to establish connection on channel: '\(channelName)'.",
    details: ""
  )
}

protocol LiveCoachAudioHostApi {
  func playPcm24k(base64Pcm: String, sampleRate: Int64) throws -> Bool
  func speak(text: String) throws -> Bool
  func stop() throws -> Bool
  func startMicCapture() throws -> Bool
  func stopMicCapture() throws -> String
  func setLanguage(languageCode: String) throws -> Bool
}

final class LiveCoachAudioHostApiSetup {
  static var codec: FlutterStandardMessageCodec {
    FlutterStandardMessageCodec.sharedInstance()
  }

  static func setUp(
    binaryMessenger: FlutterBinaryMessenger,
    api: LiveCoachAudioHostApi?,
    messageChannelSuffix: String = ""
  ) {
    let channelSuffix = messageChannelSuffix.isEmpty ? "" : ".\(messageChannelSuffix)"

    let playPcm24kChannel = FlutterBasicMessageChannel(
      name: "dev.flutter.pigeon.comunityfitness.LiveCoachAudioHostApi.playPcm24k\(channelSuffix)",
      binaryMessenger: binaryMessenger,
      codec: codec
    )
    if let api = api {
      playPcm24kChannel.setMessageHandler { message, reply in
        guard
          let args = message as? [Any?],
          args.count >= 2,
          let base64PcmArg = args[0] as? String,
          let sampleRateNum = args[1] as? NSNumber
        else {
          reply(wrapError(PigeonError(code: "invalid-args", message: "Invalid playPcm24k args", details: nil)))
          return
        }
        do {
          let result = try api.playPcm24k(base64Pcm: base64PcmArg, sampleRate: sampleRateNum.int64Value)
          reply(wrapResult(result))
        } catch {
          reply(wrapError(error))
        }
      }
    } else {
      playPcm24kChannel.setMessageHandler(nil)
    }

    let speakChannel = FlutterBasicMessageChannel(
      name: "dev.flutter.pigeon.comunityfitness.LiveCoachAudioHostApi.speak\(channelSuffix)",
      binaryMessenger: binaryMessenger,
      codec: codec
    )
    if let api = api {
      speakChannel.setMessageHandler { message, reply in
        guard
          let args = message as? [Any?],
          let textArg = args.first as? String
        else {
          reply(wrapError(PigeonError(code: "invalid-args", message: "Invalid speak args", details: nil)))
          return
        }
        do {
          let result = try api.speak(text: textArg)
          reply(wrapResult(result))
        } catch {
          reply(wrapError(error))
        }
      }
    } else {
      speakChannel.setMessageHandler(nil)
    }

    let stopChannel = FlutterBasicMessageChannel(
      name: "dev.flutter.pigeon.comunityfitness.LiveCoachAudioHostApi.stop\(channelSuffix)",
      binaryMessenger: binaryMessenger,
      codec: codec
    )
    if let api = api {
      stopChannel.setMessageHandler { _, reply in
        do {
          let result = try api.stop()
          reply(wrapResult(result))
        } catch {
          reply(wrapError(error))
        }
      }
    } else {
      stopChannel.setMessageHandler(nil)
    }

    let startMicCaptureChannel = FlutterBasicMessageChannel(
      name: "dev.flutter.pigeon.comunityfitness.LiveCoachAudioHostApi.startMicCapture\(channelSuffix)",
      binaryMessenger: binaryMessenger,
      codec: codec
    )
    if let api = api {
      startMicCaptureChannel.setMessageHandler { _, reply in
        do {
          let result = try api.startMicCapture()
          reply(wrapResult(result))
        } catch {
          reply(wrapError(error))
        }
      }
    } else {
      startMicCaptureChannel.setMessageHandler(nil)
    }

    let stopMicCaptureChannel = FlutterBasicMessageChannel(
      name: "dev.flutter.pigeon.comunityfitness.LiveCoachAudioHostApi.stopMicCapture\(channelSuffix)",
      binaryMessenger: binaryMessenger,
      codec: codec
    )
    if let api = api {
      stopMicCaptureChannel.setMessageHandler { _, reply in
        do {
          let result = try api.stopMicCapture()
          reply(wrapResult(result))
        } catch {
          reply(wrapError(error))
        }
      }
    } else {
      stopMicCaptureChannel.setMessageHandler(nil)
    }

    let setLanguageChannel = FlutterBasicMessageChannel(
      name: "dev.flutter.pigeon.comunityfitness.LiveCoachAudioHostApi.setLanguage\(channelSuffix)",
      binaryMessenger: binaryMessenger,
      codec: codec
    )
    if let api = api {
      setLanguageChannel.setMessageHandler { message, reply in
        guard
          let args = message as? [Any?],
          let languageCodeArg = args.first as? String
        else {
          reply(wrapError(PigeonError(code: "invalid-args", message: "Invalid setLanguage args", details: nil)))
          return
        }
        do {
          let result = try api.setLanguage(languageCode: languageCodeArg)
          reply(wrapResult(result))
        } catch {
          reply(wrapError(error))
        }
      }
    } else {
      setLanguageChannel.setMessageHandler(nil)
    }
  }
}

final class LiveCoachAudioFlutterApi {
  private let binaryMessenger: FlutterBinaryMessenger
  private let messageChannelSuffix: String

  init(binaryMessenger: FlutterBinaryMessenger, messageChannelSuffix: String = "") {
    self.binaryMessenger = binaryMessenger
    self.messageChannelSuffix = messageChannelSuffix.isEmpty ? "" : ".\(messageChannelSuffix)"
  }

  var codec: FlutterStandardMessageCodec {
    FlutterStandardMessageCodec.sharedInstance()
  }

  func onMicPcm16kChunk(
    base64Pcm base64PcmArg: String,
    completion: @escaping (Result<Void, PigeonError>) -> Void
  ) {
    let channelName =
      "dev.flutter.pigeon.comunityfitness.LiveCoachAudioFlutterApi.onMicPcm16kChunk\(messageChannelSuffix)"
    let channel = FlutterBasicMessageChannel(
      name: channelName,
      binaryMessenger: binaryMessenger,
      codec: codec
    )
    channel.sendMessage([base64PcmArg]) { response in
      guard let listResponse = response as? [Any?] else {
        completion(.failure(createConnectionError(withChannelName: channelName)))
        return
      }
      if listResponse.count > 1 {
        let code = listResponse[0] as? String ?? "error"
        let message = listResponse[1] as? String
        let details = listResponse[2]
        completion(.failure(PigeonError(code: code, message: message, details: details)))
      } else {
        completion(.success(()))
      }
    }
  }
}

// MARK: - Native Live Coach Audio & Multi-Language Microphone Plugin

final class LiveCoachTtsPlugin: NSObject, FlutterPlugin, LiveCoachAudioHostApi, AVSpeechSynthesizerDelegate {
  private let synthesizer = AVSpeechSynthesizer()
  private let audioEngine = AVAudioEngine()
  private let playerNode = AVAudioPlayerNode()
  private let micEngine = AVAudioEngine()
  private let pcm24kFormat = AVAudioFormat(
    commonFormat: .pcmFormatFloat32,
    sampleRate: 24000.0,
    channels: 1,
    interleaved: false
  )
  private var isAudioSessionConfigured = false
  private var isAudioEngineConfigured = false
  private var isMicRecording = false
  private var isMicTapInstalled = false
  private var flutterApi: LiveCoachAudioFlutterApi?
  private var currentLocaleIdentifier: String = LiveCoachTtsPlugin.resolveSupportedBcp47(
    Locale.preferredLanguages.first ?? "es-ES"
  )
  private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
  private var recognitionTask: SFSpeechRecognitionTask?
  private var recognizedTranscript: String = ""

  override init() {
    super.init()
    synthesizer.delegate = self
  }

  static func resolveSupportedBcp47(_ rawCode: String) -> String {
    let lower = rawCode.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    if lower.hasPrefix("es") { return "es-ES" }
    if lower.hasPrefix("ca") { return "ca-ES" }
    if lower.hasPrefix("fr") { return "fr-FR" }
    if lower.hasPrefix("pt") { return "pt-PT" }
    if lower.hasPrefix("en") { return "en-US" }
    return "es-ES"
  }

  static func register(with registrar: FlutterPluginRegistrar) {
    let instance = LiveCoachTtsPlugin()
    let messenger = registrar.messenger()
    instance.flutterApi = LiveCoachAudioFlutterApi(binaryMessenger: messenger)
    LiveCoachAudioHostApiSetup.setUp(binaryMessenger: messenger, api: instance)
  }

  private func configureAudioSession(force: Bool = false) {
    if isAudioSessionConfigured && !force {
      return
    }
    let audioSession = AVAudioSession.sharedInstance()
    do {
      try audioSession.setCategory(
        .playAndRecord,
        mode: .default,
        options: [.defaultToSpeaker, .allowBluetooth, .allowBluetoothA2DP, .duckOthers]
      )
      try audioSession.setActive(true)
      isAudioSessionConfigured = true
    } catch {
      try? audioSession.setCategory(
        .playback,
        mode: .spokenAudio,
        options: [.duckOthers]
      )
      try? audioSession.setActive(true)
      isAudioSessionConfigured = true
    }
  }

  private func configurePlayAndRecordSession() {
    configureAudioSession()
  }

  private func ensurePcmPlayerReady() -> Bool {
    guard let format = pcm24kFormat else {
      return false
    }
    configureAudioSession()

    if !isAudioEngineConfigured {
      audioEngine.attach(playerNode)
      audioEngine.connect(playerNode, to: audioEngine.mainMixerNode, format: format)
      isAudioEngineConfigured = true
    }

    if !audioEngine.isRunning {
      do {
        try audioEngine.start()
      } catch {
        return false
      }
    }

    if !playerNode.isPlaying {
      playerNode.play()
    }
    return true
  }

  private func startMicrophoneTap() {
    if isMicRecording && isMicTapInstalled && micEngine.isRunning {
      return
    }
    _ = stopMicrophoneTap()
    recognizedTranscript = ""

    configurePlayAndRecordSession()
    isMicRecording = true

    let inputNode = micEngine.inputNode
    let inputFormat = inputNode.outputFormat(forBus: 0)
    guard inputFormat.sampleRate > 0 && inputFormat.channelCount > 0 else {
      // Simulator without audio input hardware attached: stay in recording mode gracefully
      return
    }

    let sourceSampleRate = inputFormat.sampleRate
    let targetSampleRate = 16000.0
    let ratio = max(1.0, sourceSampleRate / targetSampleRate)

    inputNode.installTap(onBus: 0, bufferSize: 2048, format: inputFormat) { [weak self] buffer, _ in
      guard let self = self, self.isMicRecording else { return }

      guard let channelData = buffer.floatChannelData?[0] else { return }
      let frameLength = Int(buffer.frameLength)
      guard frameLength > 0 else { return }

      let outCount = max(1, Int(Double(frameLength) / ratio))
      var pcm16Samples = [Int16](repeating: 0, count: outCount)
      for i in 0..<outCount {
        let srcIndex = min(frameLength - 1, Int(Double(i) * ratio))
        let clamped = max(-1.0, min(1.0, channelData[srcIndex]))
        let scaled = Int16(clamped * 32767.0)
        pcm16Samples[i] = scaled.littleEndian
      }

      let pcmData = pcm16Samples.withUnsafeBufferPointer { Data(buffer: $0) }
      let base64Chunk = pcmData.base64EncodedString()
      DispatchQueue.main.async {
        self.flutterApi?.onMicPcm16kChunk(base64Pcm: base64Chunk) { _ in }
      }
    }
    isMicTapInstalled = true

    do {
      micEngine.prepare()
      try micEngine.start()
    } catch {
      // Simulator fallback: keep isMicRecording = true even if hardware start fails
    }
  }

  private func stopMicrophoneTap() -> String {
    isMicRecording = false
    if isMicTapInstalled {
      micEngine.inputNode.removeTap(onBus: 0)
      isMicTapInstalled = false
    }
    if micEngine.isRunning {
      micEngine.stop()
    }
    recognitionRequest?.endAudio()
    recognitionTask?.cancel()
    recognitionRequest = nil
    recognitionTask = nil

    return recognizedTranscript.trimmingCharacters(in: .whitespacesAndNewlines)
  }

  // MARK: - LiveCoachAudioHostApi

  func playPcm24k(base64Pcm: String, sampleRate: Int64) throws -> Bool {
    guard
      let pcmData = Data(base64Encoded: base64Pcm),
      pcmData.count >= 2,
      let format = pcm24kFormat
    else {
      return false
    }

    let frameCount = AVAudioFrameCount(pcmData.count / 2)
    guard
      frameCount > 0,
      let pcmBuffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frameCount),
      let floatChannel = pcmBuffer.floatChannelData?[0]
    else {
      return false
    }

    pcmBuffer.frameLength = frameCount
    pcmData.withUnsafeBytes { rawBytes in
      let int16Buffer = rawBytes.bindMemory(to: Int16.self)
      for idx in 0..<Int(frameCount) {
        let sample = Int16(littleEndian: int16Buffer[idx])
        floatChannel[idx] = Float(sample) / 32768.0
      }
    }

    guard ensurePcmPlayerReady() else {
      return false
    }

    if synthesizer.isSpeaking {
      synthesizer.stopSpeaking(at: .immediate)
    }

    playerNode.scheduleBuffer(pcmBuffer, completionHandler: nil)
    return true
  }

  func speak(text rawText: String) throws -> Bool {
    let text = rawText.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !text.isEmpty else {
      return false
    }

    configureAudioSession()

    if synthesizer.isSpeaking {
      synthesizer.stopSpeaking(at: .immediate)
    }

    let utterance = AVSpeechUtterance(string: text)
    utterance.voice =
      AVSpeechSynthesisVoice(language: currentLocaleIdentifier)
      ?? AVSpeechSynthesisVoice(language: AVSpeechSynthesisVoice.currentLanguageCode())
    utterance.rate = AVSpeechUtteranceDefaultSpeechRate
    utterance.pitchMultiplier = 1.0
    utterance.volume = 1.0
    synthesizer.speak(utterance)
    return true
  }

  func stop() throws -> Bool {
    if isAudioEngineConfigured && playerNode.isPlaying {
      playerNode.stop()
    }
    if synthesizer.isSpeaking {
      synthesizer.stopSpeaking(at: .immediate)
    }
    return true
  }

  func startMicCapture() throws -> Bool {
    startMicrophoneTap()
    return true
  }

  func stopMicCapture() throws -> String {
    return stopMicrophoneTap()
  }

  func setLanguage(languageCode: String) throws -> Bool {
    currentLocaleIdentifier = LiveCoachTtsPlugin.resolveSupportedBcp47(languageCode)
    return true
  }
}

// MARK: - Apple Intelligence / FoundationModels Hybrid AI Bridge (iOS)

private enum IosHybridInferenceMode: Int {
  case preferOnDevice = 0
  case onlyOnDevice = 1
  case preferInCloud = 2
  case onlyInCloud = 3
}

private enum IosOnDeviceModelStatus: Int {
  case unavailable = 0
  case downloadable = 1
  case downloading = 2
  case available = 3
}

private enum IosInferenceSource: Int {
  case onDevice = 0
  case inCloud = 1
  case localOfflineFallback = 2
}

private struct IosHybridAiRequest {
  let prompt: String
  let systemInstruction: String?
  let mode: IosHybridInferenceMode
  let cloudModelName: String
  let imageBytes: FlutterStandardTypedData?
  let imageMimeType: String?
  let responseJsonSchema: String?
  let temperature: Double?
  let maxOutputTokens: Int64?

  static func fromList(_ list: [Any?]) -> IosHybridAiRequest? {
    guard
      list.count >= 9,
      let prompt = list[0] as? String,
      let cloudModelName = list[3] as? String
    else {
      return nil
    }
    let systemInstruction = list[1] as? String
    let modeRaw = (list[2] as? NSNumber)?.intValue ?? 0
    let mode = IosHybridInferenceMode(rawValue: modeRaw) ?? .preferOnDevice
    let imageBytes = list[4] as? FlutterStandardTypedData
    let imageMimeType = list[5] as? String
    let responseJsonSchema = list[6] as? String
    let temperature = (list[7] as? NSNumber)?.doubleValue
    let maxOutputTokens = (list[8] as? NSNumber)?.int64Value
    return IosHybridAiRequest(
      prompt: prompt,
      systemInstruction: systemInstruction,
      mode: mode,
      cloudModelName: cloudModelName,
      imageBytes: imageBytes,
      imageMimeType: imageMimeType,
      responseJsonSchema: responseJsonSchema,
      temperature: temperature,
      maxOutputTokens: maxOutputTokens
    )
  }
}

private struct IosHybridAiResponse {
  let text: String
  let inferenceSource: IosInferenceSource
  let modelUsed: String
  let latencyMs: Int64
  let usedFallback: Bool
  let fallbackReason: String?

  func toList() -> [Any?] {
    return [
      text,
      inferenceSource.rawValue,
      modelUsed,
      latencyMs,
      usedFallback,
      fallbackReason,
    ]
  }
}

final class AtlasHybridAiIosBridge {
  static let onDeviceModelName = "apple-foundation-models-system-language-model"

  static func resolveOnDeviceStatus() -> Int {
    #if canImport(FoundationModels)
    if #available(iOS 26.0, *) {
      switch SystemLanguageModel.default.availability {
      case .available:
        return IosOnDeviceModelStatus.available.rawValue
      case .unavailable(.appleIntelligenceNotEnabled):
        return IosOnDeviceModelStatus.downloadable.rawValue
      case .unavailable(.modelNotReady):
        return IosOnDeviceModelStatus.downloading.rawValue
      default:
        return IosOnDeviceModelStatus.unavailable.rawValue
      }
    }
    #endif
    return IosOnDeviceModelStatus.unavailable.rawValue
  }

  static func register(binaryMessenger: FlutterBinaryMessenger) {
    let codec = FlutterStandardMessageCodec.sharedInstance()

    let checkStatusChannel = FlutterBasicMessageChannel(
      name: "dev.flutter.pigeon.comunityfitness.AtlasHybridAiHostApi.checkOnDeviceStatus",
      binaryMessenger: binaryMessenger,
      codec: codec
    )
    checkStatusChannel.setMessageHandler { _, reply in
      reply(wrapResult(resolveOnDeviceStatus()))
    }

    let downloadChannel = FlutterBasicMessageChannel(
      name: "dev.flutter.pigeon.comunityfitness.AtlasHybridAiHostApi.downloadOnDeviceModel",
      binaryMessenger: binaryMessenger,
      codec: codec
    )
    downloadChannel.setMessageHandler { _, reply in
      reply(wrapResult(resolveOnDeviceStatus()))
    }

    let warmUpChannel = FlutterBasicMessageChannel(
      name: "dev.flutter.pigeon.comunityfitness.AtlasHybridAiHostApi.warmUpOnDeviceModel",
      binaryMessenger: binaryMessenger,
      codec: codec
    )
    warmUpChannel.setMessageHandler { _, reply in
      #if canImport(FoundationModels)
      if #available(iOS 26.0, *), SystemLanguageModel.default.isAvailable {
        let session = LanguageModelSession()
        session.prewarm()
        reply(wrapResult(true))
        return
      }
      #endif
      reply(wrapResult(false))
    }

    let generateChannel = FlutterBasicMessageChannel(
      name: "dev.flutter.pigeon.comunityfitness.AtlasHybridAiHostApi.generateHybridContent",
      binaryMessenger: binaryMessenger,
      codec: codec
    )
    generateChannel.setMessageHandler { message, reply in
      guard
        let args = message as? [Any?],
        let rawRequest = args.first as? [Any?],
        let request = IosHybridAiRequest.fromList(rawRequest)
      else {
        reply(
          wrapError(
            PigeonError(
              code: "INVALID_ARGS",
              message: "Invalid PigeonHybridAiRequest payload on iOS.",
              details: nil
            )
          )
        )
        return
      }

      let hasImage = request.imageBytes != nil && !request.imageBytes!.data.isEmpty
      if request.mode == .preferInCloud || request.mode == .onlyInCloud {
        reply(
          wrapError(
            PigeonError(
              code: "IOS_DELEGATE_TO_DART_CLOUD",
              message: "Cloud mode requested on iOS; delegating to Dart FirebaseAI cloud model.",
              details: nil
            )
          )
        )
        return
      }

      if hasImage {
        reply(
          wrapError(
            PigeonError(
              code: "IOS_DELEGATE_TO_DART_CLOUD",
              message: "Apple FoundationModels on-device model supports text-only input; delegating multimodal request to Cloud.",
              details: nil
            )
          )
        )
        return
      }

      #if canImport(FoundationModels)
      if #available(iOS 26.0, *), SystemLanguageModel.default.isAvailable {
        let startTime = DispatchTime.now()
        Task {
          do {
            let instructions = request.systemInstruction?.trimmingCharacters(in: .whitespacesAndNewlines)
            let session: LanguageModelSession
            if let instructions = instructions, !instructions.isEmpty {
              session = LanguageModelSession(instructions: instructions)
            } else {
              session = LanguageModelSession()
            }

            let effectivePrompt: String
            if let schema = request.responseJsonSchema?.trimmingCharacters(in: .whitespacesAndNewlines),
               !schema.isEmpty {
              effectivePrompt = "\(request.prompt)\n\nRespond ONLY with valid JSON matching this schema:\n\(schema)"
            } else {
              effectivePrompt = request.prompt
            }

            let response = try await session.respond(to: effectivePrompt)
            let elapsedNanos = DispatchTime.now().uptimeNanoseconds - startTime.uptimeNanoseconds
            let elapsedMs = max(1, Int64(elapsedNanos / 1_000_000))
            let payload = IosHybridAiResponse(
              text: response.content.trimmingCharacters(in: .whitespacesAndNewlines),
              inferenceSource: .onDevice,
              modelUsed: onDeviceModelName,
              latencyMs: elapsedMs,
              usedFallback: false,
              fallbackReason: nil
            )
            DispatchQueue.main.async {
              reply(wrapResult(payload.toList()))
            }
          } catch {
            DispatchQueue.main.async {
              reply(
                wrapError(
                  PigeonError(
                    code: "IOS_DELEGATE_TO_DART_CLOUD",
                    message: "Apple FoundationModels on-device generation failed: \(error.localizedDescription)",
                    details: nil
                  )
                )
              )
            }
          }
        }
        return
      }
      #endif

      reply(
        wrapError(
          PigeonError(
            code: "IOS_DELEGATE_TO_DART_CLOUD",
            message: "Apple Intelligence (FoundationModels) is unavailable on this iOS device; delegating to Dart FirebaseAI cloud.",
            details: nil
          )
        )
      )
    }
  }
}

typealias AtlasHybridAiIosSafeHandler = AtlasHybridAiIosBridge

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    if let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "LiveCoachTtsPlugin") {
      LiveCoachTtsPlugin.register(with: registrar)
      AtlasHybridAiIosBridge.register(binaryMessenger: registrar.messenger())
    }
  }
}
