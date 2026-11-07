// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/services/atlas_hybrid_ai_service.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/viewmodels/atlas_hybrid_ai_viewmodel.dart';

/// Interactive panel for ATLAS Hybrid AI (On-Device Gemini Nano via Android AICore +
/// Cloud Gemini fallback + deterministic basement-gym biomechanical engine).
class AtlasHybridAiPanel extends ConsumerStatefulWidget {
  const AtlasHybridAiPanel({
    super.key,
    this.activeExercise,
  });

  final Exercise? activeExercise;

  @override
  ConsumerState<AtlasHybridAiPanel> createState() => _AtlasHybridAiPanelState();
}

class _AtlasHybridAiPanelState extends ConsumerState<AtlasHybridAiPanel> {
  static const String _heavyBenchPreset = 'Barbell Bench Press 100kg x 6 @ RPE 9.5';
  static const String _fastSquatPreset = 'Barbell Back Squat 120kg x 8 @ RPE 7.0';

  late final TextEditingController _setController;

  @override
  void initState() {
    super.initState();
    _setController = TextEditingController(text: _heavyBenchPreset);
  }

  @override
  void dispose() {
    _setController.dispose();
    super.dispose();
  }

  void _applyPreset(String presetText, AtlasHybridAiViewModel vm) {
    _setController.text = presetText;
    setState(() {});
    vm.analyzeSetLog(presetText, activeExercise: widget.activeExercise);
  }

  @override
  Widget build(BuildContext context) {
    final AtlasHybridAiState state = ref.watch(atlasHybridAiViewModelProvider);
    final AtlasHybridAiViewModel vm = ref.read(atlasHybridAiViewModelProvider.notifier);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _TelemetryStatusHeader(
          state: state,
          onDownloadModel: vm.triggerModelDownload,
          onToggleServerTemplates: vm.toggleServerPromptTemplates,
        ),
        const SizedBox(height: AppDimensions.paddingM),
        _InferenceModeSelectorCard(
          selectedMode: state.selectedMode,
          onSelectMode: vm.setInferenceMode,
        ),
        const SizedBox(height: AppDimensions.paddingM),
        if (state.errorMessage != null) ...[
          Container(
            key: const Key('hybrid_error_banner'),
            padding: const EdgeInsets.all(AppDimensions.paddingM),
            decoration: BoxDecoration(
              color: AppColors.error.withValues(alpha: AppColors.opacityLow),
              borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
              border: Border.all(
                color: AppColors.error,
                width: AppDimensions.borderDefault,
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const FaIcon(
                  FontAwesomeIcons.triangleExclamation,
                  size: AppDimensions.iconM,
                  color: AppColors.error,
                ),
                const SizedBox(width: AppDimensions.paddingS),
                Expanded(
                  child: Text(
                    state.errorMessage!,
                    style: const TextStyle(
                      fontSize: AppDimensions.fontS,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppDimensions.paddingM),
        ],
        _BasementGymLoggerCard(
          controller: _setController,
          isLoading: state.isLoading,
          onSelectHeavyBench: () => _applyPreset(_heavyBenchPreset, vm),
          onSelectFastSquat: () => _applyPreset(_fastSquatPreset, vm),
          onAnalyzeSet: () {
            vm.analyzeSetLog(
              _setController.text,
              activeExercise: widget.activeExercise,
            );
          },
          onScanEquipment: () {
            vm.scanEquipmentSample(
              customPrompt: _setController.text.trim().isNotEmpty ? _setController.text.trim() : null,
            );
          },
        ),
        if (state.lastSetAnalysis != null) ...[
          const SizedBox(height: AppDimensions.paddingM),
          _SetAnalysisResultCard(analysis: state.lastSetAnalysis!),
        ],
        if (state.lastVisionResponse != null) ...[
          const SizedBox(height: AppDimensions.paddingM),
          _VisionScanResultCard(response: state.lastVisionResponse!),
        ],
      ],
    );
  }
}

class _TelemetryStatusHeader extends StatelessWidget {
  const _TelemetryStatusHeader({
    required this.state,
    required this.onDownloadModel,
    required this.onToggleServerTemplates,
  });

  final AtlasHybridAiState state;
  final VoidCallback onDownloadModel;
  final VoidCallback onToggleServerTemplates;

  String _npuStatusLabel(Translations tr, OnDeviceModelStatus status) {
    return switch (status) {
      OnDeviceModelStatus.available => tr.hybridAi.statusOnDeviceReady,
      OnDeviceModelStatus.downloadable => tr.hybridAi.statusDownloadable,
      OnDeviceModelStatus.downloading => tr.hybridAi.statusDownloading,
      OnDeviceModelStatus.unavailable => tr.hybridAi.statusCloudFallback,
    };
  }

  Color _npuStatusColor(OnDeviceModelStatus status) {
    return switch (status) {
      OnDeviceModelStatus.available => AppColors.success,
      OnDeviceModelStatus.downloadable => AppColors.secondary,
      OnDeviceModelStatus.downloading => AppColors.warning,
      OnDeviceModelStatus.unavailable => AppColors.textSecondary,
    };
  }

  String _formatOnDeviceBadgeLabel(Translations tr, String? modelUsed) {
    final String normalized = (modelUsed ?? '').toLowerCase();
    if (normalized.contains('apple-foundation-models')) {
      return tr.hybridAi.sourceOnDeviceApple;
    }
    if (normalized.contains('chrome-prompt-api')) {
      return tr.hybridAi.sourceOnDeviceChrome;
    }
    return tr.hybridAi.sourceOnDeviceNano;
  }

  String _executionSourceLabel(Translations tr, AtlasHybridAiState current) {
    final HybridInferenceSource? source = current.lastInferenceSource;
    if (source == null) {
      return current.modelStatus == OnDeviceModelStatus.available
          ? _formatOnDeviceBadgeLabel(tr, current.lastModelUsed)
          : tr.hybridAi.sourceInCloud(model: 'gemini-3.8-flash');
    }
    return switch (source) {
      HybridInferenceSource.onDevice => _formatOnDeviceBadgeLabel(tr, current.lastModelUsed),
      HybridInferenceSource.inCloud => tr.hybridAi.sourceInCloud(model: current.lastModelUsed ?? 'gemini-3.8-flash'),
      HybridInferenceSource.localOfflineFallback => tr.hybridAi.sourceOfflineEngine,
    };
  }

  Color _executionSourceColor(HybridInferenceSource? source, OnDeviceModelStatus status) {
    if (source == null) {
      return status == OnDeviceModelStatus.available ? AppColors.success : AppColors.secondary;
    }
    return switch (source) {
      HybridInferenceSource.onDevice => AppColors.success,
      HybridInferenceSource.inCloud => AppColors.secondary,
      HybridInferenceSource.localOfflineFallback => AppColors.warning,
    };
  }

  @override
  Widget build(BuildContext context) {
    final Translations tr = TranslationProvider.of(context).translations;
    final Color statusColor = _npuStatusColor(state.modelStatus);
    final Color sourceColor = _executionSourceColor(state.lastInferenceSource, state.modelStatus);

    return Container(
      key: const Key('hybrid_telemetry_badge'),
      padding: const EdgeInsets.all(AppDimensions.paddingM),
      decoration: BoxDecoration(
        color: AppColors.surfaceElevated,
        borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
        border: Border.all(
          color: statusColor.withValues(alpha: AppColors.opacityMedium),
          width: AppDimensions.borderDefault,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(AppDimensions.paddingS),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: AppColors.opacityLow),
                  borderRadius: BorderRadius.circular(AppDimensions.radiusS),
                ),
                child: FaIcon(
                  FontAwesomeIcons.microchip,
                  size: AppDimensions.iconM,
                  color: statusColor,
                ),
              ),
              const SizedBox(width: AppDimensions.paddingS),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      tr.hybridAi.routerTitle,
                      style: const TextStyle(
                        fontSize: AppDimensions.fontM,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: AppDimensions.paddingXXS),
                    Text(
                      tr.hybridAi.npuStatusPrefix(status: _npuStatusLabel(tr, state.modelStatus)),
                      style: TextStyle(
                        fontSize: AppDimensions.fontS,
                        fontWeight: FontWeight.w600,
                        color: statusColor,
                      ),
                    ),
                  ],
                ),
              ),
              if (state.lastLatencyMs != null)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppDimensions.paddingS,
                    vertical: AppDimensions.paddingXS,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                    border: Border.all(
                      color: AppColors.border,
                      width: AppDimensions.borderDefault,
                    ),
                  ),
                  child: Text(
                    '${state.lastLatencyMs} ms',
                    style: const TextStyle(
                      fontSize: AppDimensions.fontXS,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingS),
          Wrap(
            spacing: AppDimensions.paddingS,
            runSpacing: AppDimensions.paddingXS,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppDimensions.paddingS,
                  vertical: AppDimensions.paddingXS,
                ),
                decoration: BoxDecoration(
                  color: sourceColor.withValues(alpha: AppColors.opacityLow),
                  borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                  border: Border.all(
                    color: sourceColor.withValues(alpha: AppColors.opacityMedium),
                    width: AppDimensions.borderDefault,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    FaIcon(
                      state.lastInferenceSource == HybridInferenceSource.inCloud
                          ? FontAwesomeIcons.cloudBolt
                          : FontAwesomeIcons.bolt,
                      size: AppDimensions.iconXS,
                      color: sourceColor,
                    ),
                    const SizedBox(width: AppDimensions.paddingXS),
                    Text(
                      _executionSourceLabel(tr, state),
                      style: TextStyle(
                        fontSize: AppDimensions.fontXS,
                        fontWeight: FontWeight.w800,
                        color: sourceColor,
                      ),
                    ),
                  ],
                ),
              ),
              if (state.isWarmedUp)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppDimensions.paddingS,
                    vertical: AppDimensions.paddingXS,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                    border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
                  ),
                  child: Text(
                    tr.hybridAi.ramWarmedUp,
                    style: const TextStyle(
                      fontSize: AppDimensions.fontXS,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
              if (state.modelStatus == OnDeviceModelStatus.downloadable)
                OutlinedButton.icon(
                  key: const Key('hybrid_download_model_button'),
                  onPressed: state.isLoading ? null : onDownloadModel,
                  icon: const FaIcon(
                    FontAwesomeIcons.download,
                    size: AppDimensions.iconS,
                    color: AppColors.secondary,
                  ),
                  label: Text(tr.hybridAi.downloadModelButton),
                ),
              FilterChip(
                key: const Key('hybrid_server_template_toggle'),
                selected: state.useServerPromptTemplates,
                onSelected: (_) => onToggleServerTemplates(),
                avatar: FaIcon(
                  FontAwesomeIcons.fileCode,
                  size: AppDimensions.iconXS,
                  color: state.useServerPromptTemplates ? AppColors.secondary : AppColors.textSecondary,
                ),
                label: Text(
                  state.useServerPromptTemplates
                      ? tr.hybridAi.dotpromptBadge(templateId: state.activeTemplateId)
                      : tr.hybridAi.remoteConfigOnlyBadge(templateId: state.activeTemplateId),
                  style: TextStyle(
                    fontSize: AppDimensions.fontXS,
                    fontWeight: FontWeight.w700,
                    color: state.useServerPromptTemplates ? AppColors.secondary : AppColors.textSecondary,
                  ),
                ),
                selectedColor: AppColors.secondary.withValues(alpha: AppColors.opacityLow),
                backgroundColor: AppColors.surface,
                side: BorderSide(
                  color: state.useServerPromptTemplates
                      ? AppColors.secondary.withValues(alpha: AppColors.opacityMedium)
                      : AppColors.border,
                  width: AppDimensions.borderDefault,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _InferenceModeSelectorCard extends StatelessWidget {
  const _InferenceModeSelectorCard({
    required this.selectedMode,
    required this.onSelectMode,
  });

  final HybridInferenceMode selectedMode;
  final ValueChanged<HybridInferenceMode> onSelectMode;

  List<(HybridInferenceMode, String, String, FaIconData)> _localizedModes(Translations tr) =>
      <(HybridInferenceMode, String, String, FaIconData)>[
        (
          HybridInferenceMode.preferOnDevice,
          'hybrid_mode_preferOnDevice',
          tr.hybridAi.modePreferOnDevice,
          FontAwesomeIcons.microchip,
        ),
        (
          HybridInferenceMode.onlyOnDevice,
          'hybrid_mode_onlyOnDevice',
          tr.hybridAi.modeOnlyOnDevice,
          FontAwesomeIcons.shieldHalved,
        ),
        (
          HybridInferenceMode.preferInCloud,
          'hybrid_mode_preferInCloud',
          tr.hybridAi.modePreferInCloud,
          FontAwesomeIcons.cloudArrowUp,
        ),
        (
          HybridInferenceMode.onlyInCloud,
          'hybrid_mode_onlyInCloud',
          tr.hybridAi.modeOnlyInCloud,
          FontAwesomeIcons.cloud,
        ),
      ];

  @override
  Widget build(BuildContext context) {
    final Translations tr = TranslationProvider.of(context).translations;
    return Container(
      padding: const EdgeInsets.all(AppDimensions.paddingM),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
        border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            tr.hybridAi.modeSectionTitle,
            style: const TextStyle(
              fontSize: AppDimensions.fontS,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: AppDimensions.paddingXS),
          Text(
            tr.hybridAi.modeSectionSubtitle,
            style: const TextStyle(
              fontSize: AppDimensions.fontXS,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppDimensions.paddingS),
          Wrap(
            spacing: AppDimensions.paddingS,
            runSpacing: AppDimensions.paddingS,
            children: _localizedModes(tr).map(((HybridInferenceMode, String, String, FaIconData) item) {
              final (HybridInferenceMode mode, String keyName, String label, FaIconData icon) = item;
              final bool isSelected = selectedMode == mode;
              return ChoiceChip(
                key: Key(keyName),
                selected: isSelected,
                onSelected: (_) => onSelectMode(mode),
                avatar: FaIcon(
                  icon,
                  size: AppDimensions.iconXS,
                  color: isSelected ? AppColors.primary : AppColors.textSecondary,
                ),
                label: Text(
                  label,
                  style: TextStyle(
                    fontSize: AppDimensions.fontXS,
                    fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                    color: isSelected ? AppColors.textPrimary : AppColors.textSecondary,
                  ),
                ),
                selectedColor: AppColors.primary.withValues(alpha: AppColors.opacityLow),
                backgroundColor: AppColors.surfaceElevated,
                side: BorderSide(
                  color: isSelected ? AppColors.primary : AppColors.border,
                  width: isSelected ? AppDimensions.borderThick : AppDimensions.borderDefault,
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}

class _BasementGymLoggerCard extends StatelessWidget {
  const _BasementGymLoggerCard({
    required this.controller,
    required this.isLoading,
    required this.onSelectHeavyBench,
    required this.onSelectFastSquat,
    required this.onAnalyzeSet,
    required this.onScanEquipment,
  });

  final TextEditingController controller;
  final bool isLoading;
  final VoidCallback onSelectHeavyBench;
  final VoidCallback onSelectFastSquat;
  final VoidCallback onAnalyzeSet;
  final VoidCallback onScanEquipment;

  @override
  Widget build(BuildContext context) {
    final Translations tr = TranslationProvider.of(context).translations;
    return Container(
      padding: const EdgeInsets.all(AppDimensions.paddingM),
      decoration: BoxDecoration(
        color: AppColors.surfaceElevated,
        borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
        border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const FaIcon(
                FontAwesomeIcons.dumbbell,
                size: AppDimensions.iconM,
                color: AppColors.primary,
              ),
              const SizedBox(width: AppDimensions.paddingS),
              Expanded(
                child: Text(
                  tr.hybridAi.loggerTitle,
                  style: const TextStyle(
                    fontSize: AppDimensions.fontM,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingXS),
          Text(
            tr.hybridAi.loggerSubtitle,
            style: const TextStyle(
              fontSize: AppDimensions.fontXS,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppDimensions.paddingS),
          Wrap(
            spacing: AppDimensions.paddingS,
            runSpacing: AppDimensions.paddingXS,
            children: [
              ActionChip(
                key: const Key('hybrid_preset_heavy_bench'),
                onPressed: isLoading ? null : onSelectHeavyBench,
                avatar: const FaIcon(
                  FontAwesomeIcons.fireFlameCurved,
                  size: AppDimensions.iconXS,
                  color: AppColors.warning,
                ),
                label: Text(
                  tr.hybridAi.presetHeavyBenchChip,
                  style: const TextStyle(fontSize: AppDimensions.fontXS),
                ),
              ),
              ActionChip(
                key: const Key('hybrid_preset_fast_squat'),
                onPressed: isLoading ? null : onSelectFastSquat,
                avatar: const FaIcon(
                  FontAwesomeIcons.bolt,
                  size: AppDimensions.iconXS,
                  color: AppColors.success,
                ),
                label: Text(
                  tr.hybridAi.presetFastSquatChip,
                  style: const TextStyle(fontSize: AppDimensions.fontXS),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingS),
          TextField(
            key: const Key('hybrid_set_input_field'),
            controller: controller,
            style: const TextStyle(
              fontSize: AppDimensions.fontM,
              color: AppColors.textPrimary,
            ),
            decoration: InputDecoration(
              hintText: tr.hybridAi.inputHint,
              fillColor: AppColors.surface,
            ),
          ),
          const SizedBox(height: AppDimensions.paddingM),
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  key: const Key('hybrid_analyze_set_button'),
                  onPressed: isLoading ? null : onAnalyzeSet,
                  icon: const FaIcon(
                    FontAwesomeIcons.wandMagicSparkles,
                    size: AppDimensions.iconS,
                    color: AppColors.background,
                  ),
                  label: Text(tr.hybridAi.analyzeSetButton),
                ),
              ),
              const SizedBox(width: AppDimensions.paddingS),
              Expanded(
                child: OutlinedButton.icon(
                  key: const Key('hybrid_scan_image_button'),
                  onPressed: isLoading ? null : onScanEquipment,
                  icon: const FaIcon(
                    FontAwesomeIcons.camera,
                    size: AppDimensions.iconS,
                    color: AppColors.secondary,
                  ),
                  label: Text(tr.hybridAi.scanEquipmentButton),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SetAnalysisResultCard extends StatelessWidget {
  const _SetAnalysisResultCard({required this.analysis});

  final HybridSetLogAnalysis analysis;

  String _sourceBadgeText(Translations tr, HybridInferenceSource source) {
    return switch (source) {
      HybridInferenceSource.onDevice => tr.hybridAi.sourceOnDeviceShort,
      HybridInferenceSource.inCloud => tr.hybridAi.sourceInCloudShort,
      HybridInferenceSource.localOfflineFallback => tr.hybridAi.sourceOfflineEngine,
    };
  }

  @override
  Widget build(BuildContext context) {
    final Translations tr = TranslationProvider.of(context).translations;
    final Color fatigueColor = analysis.fatigueAlert ? AppColors.warning : AppColors.success;

    return Container(
      key: const Key('hybrid_analysis_result_card'),
      padding: const EdgeInsets.all(AppDimensions.paddingM),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
        border: Border.all(
          color: fatigueColor.withValues(alpha: AppColors.opacityMedium),
          width: AppDimensions.borderDefault,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  analysis.exerciseName,
                  style: const TextStyle(
                    fontSize: AppDimensions.fontL,
                    fontWeight: FontWeight.w900,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppDimensions.paddingS,
                  vertical: AppDimensions.paddingXS,
                ),
                decoration: BoxDecoration(
                  color: AppColors.secondary.withValues(alpha: AppColors.opacityLow),
                  borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                ),
                child: Text(
                  '${_sourceBadgeText(tr, analysis.inferenceSource)} · ${analysis.latencyMs}ms',
                  style: const TextStyle(
                    fontSize: AppDimensions.fontXS,
                    fontWeight: FontWeight.w800,
                    color: AppColors.secondary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingS),
          Wrap(
            spacing: AppDimensions.paddingM,
            runSpacing: AppDimensions.paddingS,
            children: [
              _MetricPill(label: tr.hybridAi.loadLabel, value: '${analysis.weightKg} kg'),
              _MetricPill(label: tr.hybridAi.repsLabel, value: '${analysis.reps}'),
              _MetricPill(label: tr.hybridAi.rpeLabel, value: '${analysis.rpe}'),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppDimensions.paddingS,
                  vertical: AppDimensions.paddingXS,
                ),
                decoration: BoxDecoration(
                  color: fatigueColor.withValues(alpha: AppColors.opacityLow),
                  borderRadius: BorderRadius.circular(AppDimensions.radiusS),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    FaIcon(
                      analysis.fatigueAlert
                          ? FontAwesomeIcons.triangleExclamation
                          : FontAwesomeIcons.circleCheck,
                      size: AppDimensions.iconXS,
                      color: fatigueColor,
                    ),
                    const SizedBox(width: AppDimensions.paddingXS),
                    Text(
                      analysis.fatigueAlert ? tr.hybridAi.fatigueAlertBadge : tr.hybridAi.optimalVelocityBadge,
                      style: TextStyle(
                        fontSize: AppDimensions.fontXS,
                        fontWeight: FontWeight.w800,
                        color: fatigueColor,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingS),
          Text(
            analysis.nextSetRecommendation,
            style: const TextStyle(
              fontSize: AppDimensions.fontS,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}

class _MetricPill extends StatelessWidget {
  const _MetricPill({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppDimensions.paddingS,
        vertical: AppDimensions.paddingXS,
      ),
      decoration: BoxDecoration(
        color: AppColors.surfaceElevated,
        borderRadius: BorderRadius.circular(AppDimensions.radiusS),
        border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$label: ',
            style: const TextStyle(
              fontSize: AppDimensions.fontXS,
              fontWeight: FontWeight.w700,
              color: AppColors.textSecondary,
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              fontSize: AppDimensions.fontS,
              fontWeight: FontWeight.w900,
              color: AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}

class _VisionScanResultCard extends StatelessWidget {
  const _VisionScanResultCard({required this.response});

  final HybridAiResponse response;

  @override
  Widget build(BuildContext context) {
    final Translations tr = TranslationProvider.of(context).translations;
    return Container(
      key: const Key('hybrid_vision_result_card'),
      padding: const EdgeInsets.all(AppDimensions.paddingM),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
        border: Border.all(
          color: AppColors.secondary.withValues(alpha: AppColors.opacityMedium),
          width: AppDimensions.borderDefault,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const FaIcon(
                FontAwesomeIcons.eye,
                size: AppDimensions.iconS,
                color: AppColors.secondary,
              ),
              const SizedBox(width: AppDimensions.paddingS),
              Expanded(
                child: Text(
                  tr.hybridAi.visionCardTitle,
                  style: const TextStyle(
                    fontSize: AppDimensions.fontS,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              Text(
                '${response.modelUsed} · ${response.latencyMs}ms',
                style: const TextStyle(
                  fontSize: AppDimensions.fontXS,
                  fontWeight: FontWeight.w700,
                  color: AppColors.secondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingS),
          Text(
            response.text,
            style: const TextStyle(
              fontSize: AppDimensions.fontS,
              color: AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}
