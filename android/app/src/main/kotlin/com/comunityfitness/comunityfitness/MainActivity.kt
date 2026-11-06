package com.comunityfitness.comunityfitness

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.media.audiofx.AcousticEchoCanceler
import android.media.audiofx.NoiseSuppressor
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.util.Base64
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import java.util.Locale
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

class MainActivity : FlutterActivity(), LiveCoachAudioHostApi, TextToSpeech.OnInitListener {
    companion object {
        private const val REQUEST_RECORD_AUDIO = 3801
        private const val OUTPUT_SAMPLE_RATE = 24000
        private const val INPUT_SAMPLE_RATE = 16000

        fun resolveSupportedBcp47(rawCode: String): String {
            val lower = rawCode.trim().lowercase(Locale.ROOT)
            if (lower.startsWith("es")) return "es-ES"
            if (lower.startsWith("ca")) return "ca-ES"
            if (lower.startsWith("fr")) return "fr-FR"
            if (lower.startsWith("pt")) return "pt-PT"
            if (lower.startsWith("en")) return "en-US"
            return "es-ES"
        }
    }

    private var flutterApi: LiveCoachAudioFlutterApi? = null
    private var atlasHybridAiBridge: AtlasHybridAiBridge? = null
    private var tts: TextToSpeech? = null
    private var isTtsReady = false
    private var currentLocaleIdentifier: String =
        resolveSupportedBcp47(Locale.getDefault().toLanguageTag())

    private var audioTrack: AudioTrack? = null
    private val pcmPlaybackQueue = LinkedBlockingQueue<ByteArray>()
    private var pcmPlaybackThread: Thread? = null
    private val isPlaybackLoopRunning = AtomicBoolean(false)
    private val playbackGeneration = AtomicInteger(0)

    private var audioRecord: AudioRecord? = null
    private var echoCanceler: AcousticEchoCanceler? = null
    private var noiseSuppressor: NoiseSuppressor? = null
    private var micThread: Thread? = null
    private val isMicRecording = AtomicBoolean(false)

    private var speechRecognizer: SpeechRecognizer? = null
    @Volatile
    private var recognizedTranscript: String = ""
    private val mainHandler = Handler(Looper.getMainLooper())

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        tts = TextToSpeech(this, this)

        val messenger = flutterEngine.dartExecutor.binaryMessenger
        LiveCoachAudioHostApi.setUp(messenger, this)
        flutterApi = LiveCoachAudioFlutterApi(messenger)

        atlasHybridAiBridge?.dispose()
        val hybridBridge = AtlasHybridAiBridge()
        atlasHybridAiBridge = hybridBridge
        AtlasHybridAiHostApi.setUp(messenger, hybridBridge)
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.language = Locale.forLanguageTag(currentLocaleIdentifier)
            isTtsReady = true
        }
    }

    override fun setLanguage(languageCode: String): Boolean {
        currentLocaleIdentifier = resolveSupportedBcp47(languageCode)
        if (isTtsReady) {
            tts?.language = Locale.forLanguageTag(currentLocaleIdentifier)
        }
        return true
    }

    override fun playPcm24k(base64Pcm: String, sampleRate: Long): Boolean {
        if (base64Pcm.isBlank()) {
            return false
        }
        return try {
            val pcmBytes = Base64.decode(base64Pcm, Base64.DEFAULT)
            if (pcmBytes.size < 2) {
                return false
            }
            if (tts?.isSpeaking == true) {
                tts?.stop()
            }
            ensurePcmPlaybackWorkerRunning()
            pcmPlaybackQueue.offer(pcmBytes)
            true
        } catch (_: Throwable) {
            false
        }
    }

    override fun speak(text: String): Boolean {
        val rawText = text.trim()
        if (rawText.isEmpty() || !isTtsReady) {
            return false
        }
        stopPcmTrack()
        tts?.language = Locale.forLanguageTag(currentLocaleIdentifier)
        tts?.speak(rawText, TextToSpeech.QUEUE_FLUSH, null, "live_coach_utterance")
        return true
    }

    override fun stop(): Boolean {
        stopPcmTrack()
        tts?.stop()
        return true
    }

    override fun startMicCapture(): Boolean {
        return startMicrophoneCapture16k()
    }

    override fun stopMicCapture(): String {
        return stopMicrophoneCapture16k()
    }

    private fun ensureAudioTrack24k(): AudioTrack {
        val existing = audioTrack
        if (existing != null && existing.state == AudioTrack.STATE_INITIALIZED) {
            return existing
        }
        // Use a small, low-latency hardware buffer (~100ms = 4800 bytes at 24kHz 16-bit mono)
        // so Android's AudioFlinger starts playing on the very first chunk without waiting
        // for a multi-second start threshold, while pcmPlaybackQueue buffers bursts in RAM.
        val minBufSize = (AudioTrack.getMinBufferSize(
            OUTPUT_SAMPLE_RATE,
            AudioFormat.CHANNEL_OUT_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        ) * 2).coerceAtLeast(4800)

        val track = AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()
            )
            .setAudioFormat(
                AudioFormat.Builder()
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setSampleRate(OUTPUT_SAMPLE_RATE)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .build()
            )
            .setBufferSizeInBytes(minBufSize)
            .setTransferMode(AudioTrack.MODE_STREAM)
            .build()

        audioTrack = track
        return track
    }

    private fun ensurePcmPlaybackWorkerRunning() {
        if (isPlaybackLoopRunning.get() && pcmPlaybackThread?.isAlive == true) {
            return
        }
        isPlaybackLoopRunning.set(true)
        pcmPlaybackThread = Thread {
            while (isPlaybackLoopRunning.get()) {
                try {
                    val chunk = pcmPlaybackQueue.poll(120, TimeUnit.MILLISECONDS)
                    val track = ensureAudioTrack24k()
                    if (chunk != null) {
                        val genBeforeWrite = playbackGeneration.get()
                        if (track.playState != AudioTrack.PLAYSTATE_PLAYING) {
                            track.play()
                        }
                        if (playbackGeneration.get() == genBeforeWrite) {
                            track.write(chunk, 0, chunk.size, AudioTrack.WRITE_BLOCKING)
                        }
                    } else {
                        // Queue has been idle for 120ms: pause cleanly so AudioTrack never enters
                        // an underrun-disabled state between sentences.
                        if (track.state == AudioTrack.STATE_INITIALIZED &&
                            track.playState == AudioTrack.PLAYSTATE_PLAYING
                        ) {
                            track.pause()
                            track.flush()
                        }
                    }
                } catch (_: InterruptedException) {
                    // Normal wake-up on stopPcmTrack / shutdown
                } catch (_: Throwable) {
                }
            }
        }.apply {
            name = "AtlasLivePcm24kPlayThread"
            priority = Thread.MAX_PRIORITY
            start()
        }
    }

    private fun stopPcmTrack() {
        playbackGeneration.incrementAndGet()
        pcmPlaybackQueue.clear()
        try {
            audioTrack?.let { track ->
                if (track.state == AudioTrack.STATE_INITIALIZED) {
                    track.pause()
                    track.flush()
                }
            }
        } catch (_: Throwable) {
        }
    }

    private fun startMicrophoneCapture16k(): Boolean {
        if (isMicRecording.get() &&
            audioRecord?.recordingState == AudioRecord.RECORDSTATE_RECORDING &&
            micThread?.isAlive == true
        ) {
            return true
        }
        stopMicrophoneCapture16k()
        recognizedTranscript = ""

        val hasPermission = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED

        if (!hasPermission) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.RECORD_AUDIO),
                REQUEST_RECORD_AUDIO
            )
            return true
        }

        return startAudioRecordLoop()
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_RECORD_AUDIO &&
            grantResults.isNotEmpty() &&
            grantResults[0] == PackageManager.PERMISSION_GRANTED
        ) {
            startAudioRecordLoop()
        }
    }

    private fun startAudioRecordLoop(): Boolean {

        try {
            val minBuf = AudioRecord.getMinBufferSize(
                INPUT_SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT
            ).coerceAtLeast(4096)

            val recorder = AudioRecord(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                INPUT_SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                minBuf
            )

            if (recorder.state == AudioRecord.STATE_INITIALIZED) {
                audioRecord = recorder
                try {
                    if (AcousticEchoCanceler.isAvailable()) {
                        echoCanceler = AcousticEchoCanceler.create(recorder.audioSessionId)?.apply {
                            enabled = true
                        }
                    }
                    if (NoiseSuppressor.isAvailable()) {
                        noiseSuppressor = NoiseSuppressor.create(recorder.audioSessionId)?.apply {
                            enabled = true
                        }
                    }
                } catch (_: Throwable) {
                }
                isMicRecording.set(true)
                recorder.startRecording()

                micThread = Thread {
                    val buffer = ByteArray(3200) // 100ms of 16kHz 16-bit mono PCM
                    while (isMicRecording.get()) {
                        val readBytes = recorder.read(buffer, 0, buffer.size)
                        if (readBytes > 0) {
                            val chunkBytes = buffer.copyOf(readBytes)
                            val base64Chunk = Base64.encodeToString(chunkBytes, Base64.NO_WRAP)
                            mainHandler.post {
                                flutterApi?.onMicPcm16kChunk(base64Chunk) {}
                            }
                        }
                    }
                }.apply {
                    name = "GeminiLiveMic16kThread"
                    start()
                }
            }
        } catch (_: Throwable) {
        }

        return true
    }

    private fun startAndroidSpeechRecognizer() {
        mainHandler.post {
            try {
                if (!SpeechRecognizer.isRecognitionAvailable(this)) return@post
                val recognizer = SpeechRecognizer.createSpeechRecognizer(this)
                speechRecognizer = recognizer
                recognizer.setRecognitionListener(object : RecognitionListener {
                    override fun onReadyForSpeech(params: Bundle?) {}
                    override fun onBeginningOfSpeech() {}
                    override fun onRmsChanged(rmsdB: Float) {}
                    override fun onBufferReceived(buffer: ByteArray?) {}
                    override fun onEndOfSpeech() {}
                    override fun onError(error: Int) {}
                    override fun onEvent(eventType: Int, params: Bundle?) {}

                    override fun onPartialResults(partialResults: Bundle?) {
                        val matches = partialResults
                            ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        if (!matches.isNullOrEmpty() && matches[0].isNotBlank()) {
                            recognizedTranscript = matches[0]
                        }
                    }

                    override fun onResults(results: Bundle?) {
                        val matches = results
                            ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        if (!matches.isNullOrEmpty() && matches[0].isNotBlank()) {
                            recognizedTranscript = matches[0]
                        }
                    }
                })

                val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(
                        RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                        RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
                    )
                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, currentLocaleIdentifier)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, currentLocaleIdentifier)
                }
                recognizer.startListening(intent)
            } catch (_: Throwable) {
            }
        }
    }

    private fun stopMicrophoneCapture16k(): String {
        isMicRecording.set(false)
        try {
            micThread?.join(250)
        } catch (_: Throwable) {
        }
        micThread = null

        try {
            echoCanceler?.release()
        } catch (_: Throwable) {
        }
        echoCanceler = null

        try {
            noiseSuppressor?.release()
        } catch (_: Throwable) {
        }
        noiseSuppressor = null

        try {
            audioRecord?.let { rec ->
                if (rec.recordingState == AudioRecord.RECORDSTATE_RECORDING) {
                    rec.stop()
                }
                rec.release()
            }
        } catch (_: Throwable) {
        }
        audioRecord = null

        mainHandler.post {
            try {
                speechRecognizer?.stopListening()
                speechRecognizer?.destroy()
            } catch (_: Throwable) {
            }
            speechRecognizer = null
        }

        val finalTranscript = recognizedTranscript.trim()
        recognizedTranscript = ""
        return finalTranscript
    }

    override fun onDestroy() {
        stopMicrophoneCapture16k()
        isPlaybackLoopRunning.set(false)
        stopPcmTrack()
        try {
            pcmPlaybackThread?.interrupt()
            pcmPlaybackThread?.join(200)
        } catch (_: Throwable) {
        }
        pcmPlaybackThread = null
        try {
            audioTrack?.release()
        } catch (_: Throwable) {
        }
        audioTrack = null
        tts?.stop()
        tts?.shutdown()
        atlasHybridAiBridge?.dispose()
        atlasHybridAiBridge = null
        super.onDestroy()
    }
}
