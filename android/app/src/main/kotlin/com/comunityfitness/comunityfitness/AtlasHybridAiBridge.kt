@file:OptIn(com.google.firebase.ai.type.PublicPreviewAPI::class)

package com.comunityfitness.comunityfitness

import android.graphics.BitmapFactory
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import com.google.firebase.Firebase
import com.google.firebase.ai.InferenceMode
import com.google.firebase.ai.OnDeviceConfig
import com.google.firebase.ai.ai
import com.google.firebase.ai.ondevice.DownloadStatus
import com.google.firebase.ai.ondevice.FirebaseAIOnDevice
import com.google.firebase.ai.ondevice.OnDeviceModelStatus
import com.google.firebase.ai.type.GenerativeBackend
import com.google.firebase.ai.type.content
import com.google.firebase.ai.type.generationConfig
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Native Android implementation of [AtlasHybridAiHostApi] powered by
 * Firebase AI Logic Hybrid (`com.google.firebase:firebase-ai` + `firebase-ai-ondevice`).
 *
 * Routes single-turn text and single-image + text prompts to on-device Gemini Nano
 * (via Android AICore / ML Kit GenAI Prompt API) or cloud Gemini models according
 * to [PigeonHybridInferenceMode], and reports exact [PigeonInferenceSource] telemetry.
 */
class AtlasHybridAiBridge : AtlasHybridAiHostApi {
    companion object {
        private const val TAG = "AtlasHybridAiBridge"
        private const val DEFAULT_CLOUD_MODEL = "gemini-3.8-flash"
        private const val ON_DEVICE_MODEL_LABEL = "gemini-nano-on-device"
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val mainHandler = Handler(Looper.getMainLooper())
    @Volatile
    private var isDownloadCollectorActive = false

    override fun checkOnDeviceStatus(callback: (Result<PigeonOnDeviceModelStatus>) -> Unit) {
        scope.launch {
            val mappedStatus = try {
                mapModelStatus(FirebaseAIOnDevice.checkStatus())
            } catch (t: Throwable) {
                Log.w(TAG, "AICore / FirebaseAIOnDevice.checkStatus unavailable: ${t.message}")
                PigeonOnDeviceModelStatus.UNAVAILABLE
            }
            mainHandler.post {
                callback(Result.success(mappedStatus))
            }
        }
    }

    override fun downloadOnDeviceModel(callback: (Result<PigeonOnDeviceModelStatus>) -> Unit) {
        scope.launch {
            val initialStatus = try {
                when (FirebaseAIOnDevice.checkStatus()) {
                    OnDeviceModelStatus.AVAILABLE -> PigeonOnDeviceModelStatus.AVAILABLE
                    OnDeviceModelStatus.UNAVAILABLE -> PigeonOnDeviceModelStatus.UNAVAILABLE
                    OnDeviceModelStatus.DOWNLOADING -> {
                        ensureBackgroundDownloadCollector()
                        PigeonOnDeviceModelStatus.DOWNLOADING
                    }
                    OnDeviceModelStatus.DOWNLOADABLE -> {
                        ensureBackgroundDownloadCollector()
                        PigeonOnDeviceModelStatus.DOWNLOADING
                    }
                    else -> PigeonOnDeviceModelStatus.UNAVAILABLE
                }
            } catch (t: Throwable) {
                Log.w(TAG, "AICore / FirebaseAIOnDevice.download failed: ${t.message}")
                PigeonOnDeviceModelStatus.UNAVAILABLE
            }
            mainHandler.post {
                callback(Result.success(initialStatus))
            }
        }
    }

    private fun ensureBackgroundDownloadCollector() {
        if (isDownloadCollectorActive) {
            return
        }
        isDownloadCollectorActive = true
        scope.launch {
            try {
                FirebaseAIOnDevice.download().collect { downloadStatus ->
                    when (downloadStatus) {
                        is DownloadStatus.DownloadStarted -> {
                            Log.i(TAG, "Gemini Nano download started (${downloadStatus.bytesToDownload} bytes)")
                        }
                        is DownloadStatus.DownloadInProgress -> {
                            Log.d(TAG, "Gemini Nano download in progress: $downloadStatus")
                        }
                        is DownloadStatus.DownloadCompleted -> {
                            Log.i(TAG, "Gemini Nano on-device download completed")
                        }
                        is DownloadStatus.DownloadFailed -> {
                            Log.w(TAG, "Gemini Nano on-device download failed: $downloadStatus")
                        }
                    }
                }
            } catch (t: Throwable) {
                Log.w(TAG, "Background Gemini Nano download flow terminated: ${t.message}")
            } finally {
                isDownloadCollectorActive = false
            }
        }
    }

    override fun warmUpOnDeviceModel(callback: (Result<Boolean>) -> Unit) {
        scope.launch {
            val warmedUp = try {
                val status = FirebaseAIOnDevice.checkStatus()
                if (status != OnDeviceModelStatus.AVAILABLE) {
                    false
                } else {
                    val model = Firebase.ai(backend = GenerativeBackend.googleAI())
                        .generativeModel(
                            modelName = DEFAULT_CLOUD_MODEL,
                            onDeviceConfig = OnDeviceConfig(mode = InferenceMode.PREFER_ON_DEVICE)
                        )
                    model.onDeviceExtension?.warmUp()
                    true
                }
            } catch (t: Throwable) {
                Log.w(TAG, "On-device warmUp skipped: ${t.message}")
                false
            }
            mainHandler.post {
                callback(Result.success(warmedUp))
            }
        }
    }

    override fun generateHybridContent(
        request: PigeonHybridAiRequest,
        callback: (Result<PigeonHybridAiResponse>) -> Unit
    ) {
        scope.launch {
            val startMs = SystemClock.elapsedRealtime()
            val cloudModel = request.cloudModelName.ifBlank { DEFAULT_CLOUD_MODEL }
            val effectivePrompt = buildEffectivePrompt(request)

            val result: Result<PigeonHybridAiResponse> = try {
                val response = executeHybridRequest(
                    request = request,
                    cloudModel = cloudModel,
                    effectivePrompt = effectivePrompt,
                    startMs = startMs
                )
                Result.success(response)
            } catch (primaryError: Throwable) {
                if (request.mode == PigeonHybridInferenceMode.ONLY_ON_DEVICE) {
                    Result.failure(
                        FlutterError(
                            "ONLY_ON_DEVICE_FAILED",
                            "On-device Gemini Nano inference failed or AICore is unavailable: ${primaryError.message}",
                            null
                        )
                    )
                } else {
                    try {
                        val fallbackResponse = executePureCloudFallback(
                            request = request,
                            cloudModel = cloudModel,
                            effectivePrompt = effectivePrompt,
                            startMs = startMs,
                            reason = primaryError.message ?: primaryError.javaClass.simpleName
                        )
                        Result.success(fallbackResponse)
                    } catch (cloudError: Throwable) {
                        Result.failure(
                            FlutterError(
                                "HYBRID_INFERENCE_FAILED",
                                cloudError.message ?: primaryError.message ?: "Hybrid inference failed",
                                null
                            )
                        )
                    }
                }
            }

            mainHandler.post {
                callback(result)
            }
        }
    }

    private suspend fun executeHybridRequest(
        request: PigeonHybridAiRequest,
        cloudModel: String,
        effectivePrompt: String,
        startMs: Long
    ): PigeonHybridAiResponse {
        val inferenceMode = mapInferenceMode(request.mode)
        val genConfig = generationConfig {
            request.temperature?.let { temperature = it.toFloat() }
            request.maxOutputTokens?.let { maxOutputTokens = it.toInt() }
            if (!request.responseJsonSchema.isNullOrBlank() &&
                request.mode == PigeonHybridInferenceMode.ONLY_IN_CLOUD
            ) {
                responseMimeType = "application/json"
            }
        }
        val onDeviceConfig = OnDeviceConfig(
            mode = inferenceMode,
            temperature = request.temperature?.toFloat(),
            maxOutputTokens = request.maxOutputTokens?.toInt()
        )
        val systemInstructionContent = request.systemInstruction
            ?.takeIf { it.isNotBlank() }
            ?.let { instruction -> content { text(instruction) } }

        val model = Firebase.ai(backend = GenerativeBackend.googleAI())
            .generativeModel(
                modelName = cloudModel,
                generationConfig = genConfig,
                systemInstruction = systemInstructionContent,
                onDeviceConfig = onDeviceConfig
            )

        val rawResponse = generateWithOptionalImage(
            model = model,
            prompt = effectivePrompt,
            imageBytes = request.imageBytes
        )
        val elapsedMs = (SystemClock.elapsedRealtime() - startMs).coerceAtLeast(1L)
        val responseText = rawResponse.text?.trim().orEmpty()
        if (responseText.isEmpty()) {
            throw IllegalStateException("Empty response from hybrid generativeModel")
        }

        val isOnDevice = rawResponse.inferenceSource?.toString()?.contains("ON_DEVICE", ignoreCase = true) == true
        val source = if (isOnDevice) {
            PigeonInferenceSource.ON_DEVICE
        } else {
            PigeonInferenceSource.IN_CLOUD
        }
        val usedFallback = (request.mode == PigeonHybridInferenceMode.PREFER_ON_DEVICE && !isOnDevice) ||
            (request.mode == PigeonHybridInferenceMode.PREFER_IN_CLOUD && isOnDevice)
        val fallbackReason = when {
            request.mode == PigeonHybridInferenceMode.PREFER_ON_DEVICE && !isOnDevice ->
                "On-device Gemini Nano unavailable or unsupported request; routed to Cloud Gemini."
            request.mode == PigeonHybridInferenceMode.PREFER_IN_CLOUD && isOnDevice ->
                "Cloud Gemini unreachable; routed to on-device Gemini Nano."
            else -> null
        }

        return PigeonHybridAiResponse(
            text = responseText,
            inferenceSource = source,
            modelUsed = if (isOnDevice) ON_DEVICE_MODEL_LABEL else cloudModel,
            latencyMs = elapsedMs,
            usedFallback = usedFallback,
            fallbackReason = fallbackReason
        )
    }

    private suspend fun executePureCloudFallback(
        request: PigeonHybridAiRequest,
        cloudModel: String,
        effectivePrompt: String,
        startMs: Long,
        reason: String
    ): PigeonHybridAiResponse {
        val genConfig = generationConfig {
            request.temperature?.let { temperature = it.toFloat() }
            request.maxOutputTokens?.let { maxOutputTokens = it.toInt() }
            if (!request.responseJsonSchema.isNullOrBlank()) {
                responseMimeType = "application/json"
            }
        }
        val systemInstructionContent = request.systemInstruction
            ?.takeIf { it.isNotBlank() }
            ?.let { instruction -> content { text(instruction) } }

        val cloudModelInstance = Firebase.ai(backend = GenerativeBackend.googleAI())
            .generativeModel(
                modelName = cloudModel,
                generationConfig = genConfig,
                systemInstruction = systemInstructionContent
            )

        val rawResponse = generateWithOptionalImage(
            model = cloudModelInstance,
            prompt = effectivePrompt,
            imageBytes = request.imageBytes
        )
        val elapsedMs = (SystemClock.elapsedRealtime() - startMs).coerceAtLeast(1L)
        val responseText = rawResponse.text?.trim().orEmpty()
        if (responseText.isEmpty()) {
            throw IllegalStateException("Empty response from cloud fallback generativeModel")
        }

        return PigeonHybridAiResponse(
            text = responseText,
            inferenceSource = PigeonInferenceSource.IN_CLOUD,
            modelUsed = cloudModel,
            latencyMs = elapsedMs,
            usedFallback = request.mode != PigeonHybridInferenceMode.ONLY_IN_CLOUD,
            fallbackReason = if (request.mode != PigeonHybridInferenceMode.ONLY_IN_CLOUD) reason else null
        )
    }

    private suspend fun generateWithOptionalImage(
        model: com.google.firebase.ai.GenerativeModel,
        prompt: String,
        imageBytes: ByteArray?
    ): com.google.firebase.ai.type.GenerateContentResponse {
        if (imageBytes != null && imageBytes.isNotEmpty()) {
            val bitmap = BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size)
            if (bitmap != null) {
                val multimodalContent = content {
                    image(bitmap)
                    text(prompt)
                }
                return model.generateContent(multimodalContent)
            }
        }
        return model.generateContent(prompt)
    }

    private fun buildEffectivePrompt(request: PigeonHybridAiRequest): String {
        val basePrompt = if (!request.systemInstruction.isNullOrBlank() &&
            request.mode != PigeonHybridInferenceMode.ONLY_IN_CLOUD
        ) {
            "${request.systemInstruction.trim()}\n\n${request.prompt.trim()}"
        } else {
            request.prompt.trim()
        }
        val schema = request.responseJsonSchema?.trim()
        if (schema.isNullOrEmpty()) {
            return basePrompt
        }
        return "$basePrompt\n\nRespond strictly with valid JSON matching this schema:\n$schema"
    }

    private fun mapInferenceMode(mode: PigeonHybridInferenceMode): InferenceMode {
        return when (mode) {
            PigeonHybridInferenceMode.PREFER_ON_DEVICE -> InferenceMode.PREFER_ON_DEVICE
            PigeonHybridInferenceMode.ONLY_ON_DEVICE -> InferenceMode.ONLY_ON_DEVICE
            PigeonHybridInferenceMode.PREFER_IN_CLOUD -> InferenceMode.PREFER_IN_CLOUD
            PigeonHybridInferenceMode.ONLY_IN_CLOUD -> InferenceMode.ONLY_IN_CLOUD
        }
    }

    private fun mapModelStatus(status: OnDeviceModelStatus): PigeonOnDeviceModelStatus {
        return when (status) {
            OnDeviceModelStatus.UNAVAILABLE -> PigeonOnDeviceModelStatus.UNAVAILABLE
            OnDeviceModelStatus.DOWNLOADABLE -> PigeonOnDeviceModelStatus.DOWNLOADABLE
            OnDeviceModelStatus.DOWNLOADING -> PigeonOnDeviceModelStatus.DOWNLOADING
            OnDeviceModelStatus.AVAILABLE -> PigeonOnDeviceModelStatus.AVAILABLE
            else -> PigeonOnDeviceModelStatus.UNAVAILABLE
        }
    }

    fun dispose() {
        scope.cancel()
    }
}
