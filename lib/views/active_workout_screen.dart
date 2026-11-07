// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:rive/rive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/services/atlas_hybrid_ai_service.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/utils/rest_progress.dart';
import 'package:comunityfitness/viewmodels/active_workout_viewmodel.dart';
import 'package:comunityfitness/views/exercise_catalog_screen.dart';
import 'package:comunityfitness/views/widgets/app_back_button.dart';
import 'package:comunityfitness/views/widgets/rest_timer_ring.dart';
import 'package:comunityfitness/views/widgets/workout_anatomical_summary_sheet.dart';

class ActiveWorkoutScreen extends ConsumerWidget {
  const ActiveWorkoutScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tr = TranslationProvider.of(context).translations;
    final state = ref.watch(activeWorkoutViewModelProvider);
    final vm = ref.read(activeWorkoutViewModelProvider.notifier);

    final hours = state.elapsedSeconds ~/ 3600;
    final minutes = (state.elapsedSeconds % 3600) ~/ 60;
    final seconds = state.elapsedSeconds % 60;
    final timeFormatted = '${hours.toString().padLeft(2, '0')}:${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        automaticallyImplyLeading: false,
        leading: AppBackButton.maybeLeading(context),
        backgroundColor: AppColors.surface,
        elevation: 0,
        scrolledUnderElevation: 0,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              state.routineTitle,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: AppDimensions.fontL, fontWeight: FontWeight.w900, letterSpacing: 0.3, color: AppColors.textPrimary),
            ),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const FaIcon(FontAwesomeIcons.stopwatch, size: AppDimensions.iconXS, color: AppColors.primary),
                const SizedBox(width: AppDimensions.paddingXS),
                Flexible(
                  child: Text(
                    timeFormatted,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: AppDimensions.fontS, color: AppColors.primary, fontWeight: FontWeight.bold),
                  ),
                ),
                if (state.isPaused) ...[
                  const SizedBox(width: AppDimensions.paddingXS),
                  Flexible(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingXS, vertical: AppDimensions.paddingXXS),
                      decoration: BoxDecoration(
                        color: AppColors.warning.withValues(alpha: AppColors.opacityLow),
                        borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                        border: Border.all(
                          color: AppColors.warning.withValues(alpha: AppColors.opacityMedium),
                          width: AppDimensions.borderThin,
                        ),
                      ),
                      child: const Text(
                        'PAUSED',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: AppDimensions.fontXXS, color: AppColors.warning, fontWeight: FontWeight.w900, letterSpacing: 0.5),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: FaIcon(state.isPaused ? FontAwesomeIcons.play : FontAwesomeIcons.pause, size: AppDimensions.iconM, color: AppColors.textSecondary),
            tooltip: state.isPaused ? 'Resume' : 'Pause',
            onPressed: vm.togglePause,
          ),
          Padding(
            padding: const EdgeInsets.only(right: AppDimensions.paddingM),
            child: ElevatedButton.icon(
              key: const Key('active_workout_finish_button'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: AppColors.background,
                elevation: 0,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
              ),
              icon: const FaIcon(FontAwesomeIcons.flagCheckered, size: AppDimensions.iconS),
              label: Text(tr.workout.finishButton, style: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5)),
              onPressed: () async {
                final snapshot = state;
                final session = await vm.finishWorkout();
                if (!context.mounted) {
                  return;
                }
                if (session.steps.isEmpty) {
                  if (Navigator.canPop(context)) {
                    Navigator.of(context).pop();
                  }
                  return;
                }
                await showModalBottomSheet<void>(
                  context: context,
                  isScrollControlled: true,
                  backgroundColor: AppColors.background,
                  builder: (_) => WorkoutAnatomicalSummarySheet.fromActiveState(state: snapshot),
                );
                if (context.mounted && Navigator.canPop(context)) {
                  Navigator.of(context).pop();
                }
              },
            ),
          ),
        ],
      ),
      body: Stack(
        children: [
          Column(
            children: [
              if (state.ghostTitle != null) _buildGhostPartnerBanner(state, tr),
              if (state.lastHybridAnalysis != null) _buildHybridTelemetryBanner(state.lastHybridAnalysis!, tr),
              Expanded(
                child: state.steps.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const FaIcon(FontAwesomeIcons.dumbbell, size: AppDimensions.iconHuge, color: AppColors.border),
                            const SizedBox(height: AppDimensions.paddingM),
                            const Text(
                              'No exercises in session',
                              style: TextStyle(fontSize: AppDimensions.fontL, fontWeight: FontWeight.bold, color: AppColors.textSecondary),
                            ),
                            const SizedBox(height: AppDimensions.paddingM),
                            ElevatedButton.icon(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppColors.primary,
                                foregroundColor: AppColors.background,
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
                              ),
                              icon: const FaIcon(FontAwesomeIcons.plus, size: AppDimensions.iconS),
                              label: Text(tr.workout.addExerciseButton),
                              onPressed: () => _openExerciseSelector(context, vm),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.only(
                          left: AppDimensions.paddingM,
                          right: AppDimensions.paddingM,
                          top: AppDimensions.paddingM,
                          bottom: AppDimensions.activeHudBottomPadding,
                        ),
                        itemCount: state.steps.length + 1,
                        itemBuilder: (context, index) {
                          if (index == state.steps.length) {
                            return Padding(
                              padding: const EdgeInsets.only(top: AppDimensions.paddingXS),
                              child: OutlinedButton.icon(
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: AppColors.primary,
                                  side: const BorderSide(color: AppColors.primary, width: AppDimensions.borderThick),
                                  padding: const EdgeInsets.symmetric(vertical: AppDimensions.paddingM),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
                                ),
                                icon: const FaIcon(FontAwesomeIcons.plus, size: AppDimensions.iconS),
                                label: Text(tr.workout.addExerciseButton, style: const TextStyle(fontWeight: FontWeight.w900)),
                                onPressed: () => _openExerciseSelector(context, vm),
                              ),
                            );
                          }

                          final step = state.steps[index];
                          final isSuperset = step.supersetGroupId != null;

                          return Container(
                            margin: const EdgeInsets.only(bottom: AppDimensions.paddingM),
                            decoration: BoxDecoration(
                              color: AppColors.surfaceElevated,
                              borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                              border: Border.all(
                                color: isSuperset ? AppColors.secondary : (step.isCompleted ? AppColors.primary : AppColors.border),
                                width: (isSuperset || step.isCompleted) ? AppDimensions.borderThick : AppDimensions.borderDefault,
                              ),
                            ),
                            child: Padding(
                              padding: const EdgeInsets.all(AppDimensions.paddingM),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            if (isSuperset) ...[
                                              Container(
                                                margin: const EdgeInsets.only(bottom: AppDimensions.paddingXS),
                                                padding: const EdgeInsets.symmetric(
                                                  horizontal: AppDimensions.paddingS,
                                                  vertical: AppDimensions.paddingXXS,
                                                ),
                                                decoration: BoxDecoration(
                                                  color: AppColors.secondary.withValues(alpha: AppColors.opacityLow),
                                                  borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                                                  border: Border.all(
                                                    color: AppColors.secondary.withValues(alpha: AppColors.opacityMedium),
                                                    width: AppDimensions.borderThin,
                                                  ),
                                                ),
                                                child: const Row(
                                                  mainAxisSize: MainAxisSize.min,
                                                  children: [
                                                    FaIcon(FontAwesomeIcons.link, size: AppDimensions.iconXS, color: AppColors.secondary),
                                                    SizedBox(width: AppDimensions.paddingXS),
                                                    Text(
                                                      'SUPERSET',
                                                      style: TextStyle(
                                                        fontSize: AppDimensions.fontXXS,
                                                        fontWeight: FontWeight.w900,
                                                        color: AppColors.secondary,
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ),
                                            ],
                                            Text(
                                              step.exerciseName,
                                              style: const TextStyle(
                                                fontSize: AppDimensions.fontL,
                                                fontWeight: FontWeight.w900,
                                                color: AppColors.textPrimary,
                                              ),
                                            ),
                                            const SizedBox(height: AppDimensions.paddingXXS),
                                            Row(
                                              children: [
                                                Expanded(
                                                  child: Text(
                                                    step.equipment.isNotEmpty
                                                        ? '${tr.translateMuscle(step.primaryMuscleGroup)} · ${tr.translateEquipment(step.equipment)}'
                                                        : tr.translateMuscle(step.primaryMuscleGroup),
                                                    maxLines: 1,
                                                    overflow: TextOverflow.ellipsis,
                                                    style: const TextStyle(fontSize: AppDimensions.fontS, color: AppColors.textSecondary),
                                                  ),
                                                ),
                                                const SizedBox(width: AppDimensions.paddingXS),
                                                Flexible(
                                                  child: InkWell(
                                                    key: Key('busy_machine_swap_button_$index'),
                                                    borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                                                    onTap: () {
                                                      vm.swapExerciseForBusyEquipment(index);
                                                    },
                                                    child: Container(
                                                      padding: const EdgeInsets.symmetric(
                                                        horizontal: AppDimensions.paddingS,
                                                        vertical: AppDimensions.paddingXXS,
                                                      ),
                                                      decoration: BoxDecoration(
                                                        color: AppColors.surface,
                                                        borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                                                        border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
                                                      ),
                                                      child: Row(
                                                        mainAxisSize: MainAxisSize.min,
                                                        children: [
                                                          const FaIcon(
                                                            FontAwesomeIcons.arrowsRotate,
                                                            size: AppDimensions.iconXS,
                                                            color: AppColors.primary,
                                                          ),
                                                          const SizedBox(width: AppDimensions.paddingXS),
                                                          Flexible(
                                                            child: Text(
                                                              tr.workout.machineBusySwapPill,
                                                              maxLines: 1,
                                                              overflow: TextOverflow.ellipsis,
                                                              style: const TextStyle(
                                                                fontSize: AppDimensions.fontXXS,
                                                                fontWeight: FontWeight.w700,
                                                                color: AppColors.textPrimary,
                                                              ),
                                                            ),
                                                          ),
                                                        ],
                                                      ),
                                                    ),
                                                  ),
                                                ),
                                              ],
                                            ),
                                            if ((step.autopilotBadge != null && step.autopilotBadge!.isNotEmpty) ||
                                                (step.swapReason != null && step.swapReason!.isNotEmpty)) ...[
                                              const SizedBox(height: AppDimensions.paddingS),
                                              Wrap(
                                                spacing: AppDimensions.paddingS,
                                                runSpacing: AppDimensions.paddingXS,
                                                children: [
                                                  if (step.autopilotBadge != null && step.autopilotBadge!.isNotEmpty)
                                                    Container(
                                                      key: Key('autopilot_badge_$index'),
                                                      padding: const EdgeInsets.symmetric(
                                                        horizontal: AppDimensions.paddingS,
                                                        vertical: AppDimensions.paddingXXS,
                                                      ),
                                                      decoration: BoxDecoration(
                                                        color: AppColors.secondary.withValues(alpha: AppColors.opacityLow),
                                                        borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                                                        border: Border.all(
                                                          color: AppColors.secondary.withValues(alpha: AppColors.opacityMedium),
                                                          width: AppDimensions.borderThin,
                                                        ),
                                                      ),
                                                      child: Row(
                                                        mainAxisSize: MainAxisSize.min,
                                                        children: [
                                                          const FaIcon(
                                                            FontAwesomeIcons.boltLightning,
                                                            size: AppDimensions.iconS,
                                                            color: AppColors.secondary,
                                                          ),
                                                          const SizedBox(width: AppDimensions.paddingXS),
                                                          Flexible(
                                                            child: Text(
                                                              step.autopilotBadge!,
                                                              maxLines: 1,
                                                              overflow: TextOverflow.ellipsis,
                                                              style: const TextStyle(
                                                                fontSize: AppDimensions.fontXXS,
                                                                fontWeight: FontWeight.w800,
                                                                color: AppColors.secondary,
                                                              ),
                                                            ),
                                                          ),
                                                        ],
                                                      ),
                                                    ),
                                                  if (step.swapReason != null && step.swapReason!.isNotEmpty)
                                                    Container(
                                                      key: Key('swap_reason_badge_$index'),
                                                      padding: const EdgeInsets.symmetric(
                                                        horizontal: AppDimensions.paddingS,
                                                        vertical: AppDimensions.paddingXXS,
                                                      ),
                                                      decoration: BoxDecoration(
                                                        color: AppColors.primary.withValues(alpha: AppColors.opacityLow),
                                                        borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                                                        border: Border.all(
                                                          color: AppColors.primary.withValues(alpha: AppColors.opacityMedium),
                                                          width: AppDimensions.borderThin,
                                                        ),
                                                      ),
                                                      child: Row(
                                                        mainAxisSize: MainAxisSize.min,
                                                        children: [
                                                          const FaIcon(
                                                            FontAwesomeIcons.arrowsRotate,
                                                            size: AppDimensions.iconS,
                                                            color: AppColors.primary,
                                                          ),
                                                          const SizedBox(width: AppDimensions.paddingXS),
                                                          Flexible(
                                                            child: Text(
                                                              step.swapReason!,
                                                              maxLines: 1,
                                                              overflow: TextOverflow.ellipsis,
                                                              style: const TextStyle(
                                                                fontSize: AppDimensions.fontXXS,
                                                                fontWeight: FontWeight.w700,
                                                                color: AppColors.primary,
                                                              ),
                                                            ),
                                                          ),
                                                        ],
                                                      ),
                                                    ),
                                                ],
                                              ),
                                            ],
                                          ],
                                        ),
                                      ),
                                      IconButton(
                                        icon: const FaIcon(
                                          FontAwesomeIcons.ellipsisVertical,
                                          size: AppDimensions.iconM,
                                          color: AppColors.textSecondary,
                                        ),
                                        onPressed: () {
                                          _showStepOptionsModal(context, ref, index, step);
                                        },
                                      ),
                                    ],
                                  ),
                                  const Divider(color: AppColors.border, height: AppDimensions.paddingL),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                                    children: [
                                      Flexible(
                                        child: _MetricColumn(
                                          label: 'WEIGHT',
                                          value: '${step.weight} kg',
                                          onTap: () => _editWeight(context, vm, index, step.weight),
                                        ),
                                      ),
                                      Flexible(
                                        child: _MetricColumn(
                                          label: 'REPS',
                                          value: '${step.reps}',
                                          onTap: () => _editReps(context, vm, index, step.reps),
                                        ),
                                      ),
                                      Flexible(
                                        child: _MetricColumn(
                                          label: 'SETS',
                                          value: '${step.completedSets} / ${step.sets}',
                                          highlight: step.isCompleted,
                                        ),
                                      ),
                                      GestureDetector(
                                        onTap: () => vm.toggleSetCompleted(index),
                                        child: Container(
                                          width: AppDimensions.setCheckSize,
                                          height: AppDimensions.setCheckSize,
                                          decoration: step.isCompleted
                                              ? null
                                              : BoxDecoration(
                                                  shape: BoxShape.circle,
                                                  color: step.completedSets > 0
                                                      ? AppColors.primary.withValues(alpha: AppColors.opacityLow)
                                                      : AppColors.surface,
                                                  border: Border.all(
                                                    color: step.completedSets > 0 ? AppColors.primary : AppColors.border,
                                                    width: AppDimensions.borderThick,
                                                  ),
                                                ),
                                          child: Center(
                                            child: step.isCompleted
                                                ? const _CompletedSetRiveBadge()
                                                : FaIcon(
                                                    FontAwesomeIcons.check,
                                                    size: AppDimensions.iconM,
                                                    color: step.completedSets > 0 ? AppColors.primary : AppColors.textMuted,
                                                  ),
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: AppDimensions.paddingS),
                                  _buildHybridAutoregulationRow(vm, index, state.isHybridAnalyzing, tr),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
              ),
            ],
          ),

          // High-Contrast Floating Rest Timer HUD
          if (state.isRestTimerActive)
            Positioned(
              left: AppDimensions.paddingM,
              right: AppDimensions.paddingM,
              bottom: AppDimensions.paddingM,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingL, vertical: AppDimensions.paddingM),
                decoration: BoxDecoration(
                  color: AppColors.surfaceElevated,
                  borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                  border: Border.all(color: AppColors.primary, width: AppDimensions.borderThick),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primary.withValues(alpha: AppColors.opacityLow),
                      blurRadius: AppDimensions.shadowBlurL,
                      offset: AppDimensions.shadowOffsetL,
                    ),
                  ],
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        RestTimerRing(progress: restProgress(state.restTimerSecondsRemaining, state.restTimerTotalSeconds)),
                        const SizedBox(width: AppDimensions.paddingM),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Text(
                              'REST TIMER',
                              style: TextStyle(
                                fontSize: AppDimensions.fontXXS,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 1.0,
                                color: AppColors.textMuted,
                              ),
                            ),
                            Text(
                              '${state.restTimerSecondsRemaining}s',
                              style: const TextStyle(fontSize: AppDimensions.fontXXL, fontWeight: FontWeight.w900, color: AppColors.primary),
                            ),
                          ],
                        ),
                      ],
                    ),
                    Row(
                      children: [
                        OutlinedButton(
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
                          ),
                          onPressed: () => vm.addRestTime(30),
                          child: const Text(
                            '+30s',
                            style: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.bold),
                          ),
                        ),
                        const SizedBox(width: AppDimensions.paddingS),
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.primary,
                            foregroundColor: AppColors.background,
                            elevation: 0,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
                          ),
                          onPressed: vm.skipRestTimer,
                          child: const Text('Skip', style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5)),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildGhostPartnerBanner(ActiveWorkoutState state, Translations tr) {
    final delta = state.ghostDeltaVolume;
    final String badgeLabel;
    final Color badgeColor;
    if (delta > 0) {
      badgeLabel = tr.workout.ghostAheadBadge(delta: delta.toStringAsFixed(0));
      badgeColor = AppColors.success;
    } else if (delta < 0) {
      badgeLabel = tr.workout.ghostBehindBadge(delta: delta.toStringAsFixed(0));
      badgeColor = AppColors.warning;
    } else {
      badgeLabel = tr.workout.ghostOnPaceBadge;
      badgeColor = AppColors.secondary;
    }

    return Container(
      key: const Key('ghost_partner_hud_banner'),
      margin: const EdgeInsets.only(left: AppDimensions.paddingM, right: AppDimensions.paddingM, top: AppDimensions.paddingM),
      padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM, vertical: AppDimensions.paddingS),
      decoration: BoxDecoration(
        color: AppColors.surfaceElevated,
        borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
        border: Border.all(
          color: AppColors.secondary.withValues(alpha: AppColors.opacityMedium),
          width: AppDimensions.borderDefault,
        ),
      ),
      child: Row(
        children: [
          const FaIcon(FontAwesomeIcons.ghost, size: AppDimensions.iconM, color: AppColors.secondary),
          const SizedBox(width: AppDimensions.paddingS),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  state.ghostTitle!,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: AppDimensions.fontS, fontWeight: FontWeight.w800, color: AppColors.textPrimary),
                ),
                const SizedBox(height: AppDimensions.paddingXXS),
                Text(
                  tr.workout.ghostPaceCompare(live: state.liveVolume.toStringAsFixed(0), target: state.ghostTargetVolumeNow.toStringAsFixed(0)),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: AppDimensions.fontXXS, color: AppColors.textSecondary),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppDimensions.paddingS),
          Flexible(
            child: Container(
              key: const Key('ghost_partner_delta_badge'),
              padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXXS),
              decoration: BoxDecoration(
                color: badgeColor.withValues(alpha: AppColors.opacityLow),
                borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                border: Border.all(
                  color: badgeColor.withValues(alpha: AppColors.opacityMedium),
                  width: AppDimensions.borderThin,
                ),
              ),
              child: Text(
                badgeLabel,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w900, color: badgeColor),
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatOnDeviceSourceLabel(Translations tr, String modelUsed) {
    final String normalized = modelUsed.toLowerCase();
    if (normalized.contains('apple-foundation-models')) {
      return tr.hybridAi.sourceOnDeviceApple;
    }
    if (normalized.contains('chrome-prompt-api')) {
      return tr.hybridAi.sourceOnDeviceChrome;
    }
    return tr.hybridAi.sourceOnDeviceNano;
  }

  Widget _buildHybridTelemetryBanner(HybridSetLogAnalysis analysis, Translations tr) {
    final (String sourceLabel, Color sourceColor, FaIconData sourceIcon) = switch (analysis.inferenceSource) {
      HybridInferenceSource.onDevice => (_formatOnDeviceSourceLabel(tr, analysis.modelUsed), AppColors.success, FontAwesomeIcons.microchip),
      HybridInferenceSource.inCloud => (tr.hybridAi.sourceInCloud(model: analysis.modelUsed), AppColors.secondary, FontAwesomeIcons.cloudBolt),
      HybridInferenceSource.localOfflineFallback => (tr.hybridAi.sourceOfflineEngine, AppColors.warning, FontAwesomeIcons.shieldHalved),
    };

    return Container(
      key: const Key('active_workout_hybrid_telemetry_banner'),
      margin: const EdgeInsets.only(left: AppDimensions.paddingM, right: AppDimensions.paddingM, top: AppDimensions.paddingM),
      padding: const EdgeInsets.all(AppDimensions.paddingM),
      decoration: BoxDecoration(
        color: AppColors.surfaceElevated,
        borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
        border: Border.all(
          color: sourceColor.withValues(alpha: AppColors.opacityMedium),
          width: AppDimensions.borderDefault,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: AppDimensions.paddingS,
            runSpacing: AppDimensions.paddingXS,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXXS),
                decoration: BoxDecoration(
                  color: sourceColor.withValues(alpha: AppColors.opacityLow),
                  borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                  border: Border.all(
                    color: sourceColor.withValues(alpha: AppColors.opacityMedium),
                    width: AppDimensions.borderThin,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    FaIcon(sourceIcon, size: AppDimensions.iconXS, color: sourceColor),
                    const SizedBox(width: AppDimensions.paddingXS),
                    Text(
                      sourceLabel,
                      style: TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w900, color: sourceColor),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXXS),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                  border: Border.all(color: AppColors.border, width: AppDimensions.borderThin),
                ),
                child: Text(
                  '${analysis.latencyMs}ms',
                  style: const TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w800, color: AppColors.textPrimary),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXXS),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: AppColors.opacityLow),
                  borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                ),
                child: Text(
                  '${tr.hybridAi.rpeLabel} ${analysis.rpe.toStringAsFixed(1)}',
                  style: const TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w800, color: AppColors.primary),
                ),
              ),
              if (analysis.fatigueAlert)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXXS),
                  decoration: BoxDecoration(
                    color: AppColors.error.withValues(alpha: AppColors.opacityLow),
                    borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                    border: Border.all(
                      color: AppColors.error.withValues(alpha: AppColors.opacityMedium),
                      width: AppDimensions.borderThin,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const FaIcon(FontAwesomeIcons.triangleExclamation, size: AppDimensions.iconXS, color: AppColors.error),
                      const SizedBox(width: AppDimensions.paddingXS),
                      Text(
                        tr.hybridAi.fatigueAlertBannerBadge,
                        style: const TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w900, color: AppColors.error),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingXS),
          Text(
            '${analysis.exerciseName} · ${analysis.nextSetRecommendation}',
            style: const TextStyle(fontSize: AppDimensions.fontS, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
          ),
        ],
      ),
    );
  }

  Widget _buildHybridAutoregulationRow(ActiveWorkoutViewModel vm, int index, bool isBusy, Translations tr) {
    return Container(
      key: Key('active_step_hybrid_row_$index'),
      padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXS),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppDimensions.radiusM),
        border: Border.all(color: AppColors.border, width: AppDimensions.borderThin),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const FaIcon(FontAwesomeIcons.microchip, size: AppDimensions.iconXS, color: AppColors.secondary),
              const SizedBox(width: AppDimensions.paddingXS),
              Expanded(
                child: Text(
                  tr.hybridAi.activeWorkoutSectionTitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: AppDimensions.fontXXS,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0.5,
                    color: AppColors.secondary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingXS),
          Wrap(
            spacing: AppDimensions.paddingXS,
            runSpacing: AppDimensions.paddingXXS,
            children: [
              _buildRpeActionChip(
                key: Key('active_step_hybrid_rpe_7_$index'),
                label: tr.hybridAi.rpe7Chip,
                accentColor: AppColors.success,
                isBusy: isBusy,
                onTap: () => vm.autoregulateStepWithHybridAi(index, rpe: 7.0),
              ),
              _buildRpeActionChip(
                key: Key('active_step_hybrid_rpe_85_$index'),
                label: tr.hybridAi.rpe85Chip,
                accentColor: AppColors.secondary,
                isBusy: isBusy,
                onTap: () => vm.autoregulateStepWithHybridAi(index, rpe: 8.5),
              ),
              _buildRpeActionChip(
                key: Key('active_step_hybrid_rpe_95_$index'),
                label: tr.hybridAi.rpe95Chip,
                accentColor: AppColors.warning,
                isBusy: isBusy,
                onTap: () => vm.autoregulateStepWithHybridAi(index, rpe: 9.5),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildRpeActionChip({
    required Key key,
    required String label,
    required Color accentColor,
    required bool isBusy,
    required VoidCallback onTap,
  }) {
    return ActionChip(
      key: key,
      onPressed: isBusy ? null : onTap,
      backgroundColor: accentColor.withValues(alpha: AppColors.opacityLow),
      side: BorderSide(
        color: accentColor.withValues(alpha: AppColors.opacityMedium),
        width: AppDimensions.borderThin,
      ),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusPill)),
      visualDensity: VisualDensity.compact,
      label: Text(
        label,
        style: TextStyle(
          fontSize: AppDimensions.fontXXS,
          fontWeight: FontWeight.w800,
          color: accentColor,
        ),
      ),
    );
  }

  Future<void> _openExerciseSelector(BuildContext context, ActiveWorkoutViewModel vm) async {
    final Exercise? chosen = await Navigator.push<Exercise>(
      context,
      MaterialPageRoute(builder: (context) => const ExerciseCatalogScreen(isSelectionMode: true)),
    );
    if (chosen != null) {
      vm.addExercise(chosen);
    }
  }

  void _showStepOptionsModal(BuildContext context, WidgetRef ref, int index, ActiveStepItem step) {
    final tr = TranslationProvider.of(context).translations;
    final vm = ref.read(activeWorkoutViewModelProvider.notifier);
    final state = ref.read(activeWorkoutViewModelProvider);

    showModalBottomSheet<void>(
      context: context,
      backgroundColor: AppColors.surfaceElevated,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(AppDimensions.radiusBottomSheet))),
      builder: (context) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(AppDimensions.paddingM),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ListTile(
                  leading: const FaIcon(FontAwesomeIcons.arrowsRotate, color: AppColors.primary),
                  title: Text(
                    tr.workout.machineBusyModalTitle,
                    style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600),
                  ),
                  onTap: () {
                    vm.swapExerciseForBusyEquipment(index);
                    Navigator.pop(context);
                  },
                ),
                ListTile(
                  leading: const FaIcon(FontAwesomeIcons.fire, color: AppColors.warning),
                  title: Text(
                    step.isWarmup ? 'Unmark Warm-up' : 'Mark as Warm-up set',
                    style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600),
                  ),
                  onTap: () {
                    vm.updateStepValues(index, isWarmup: !step.isWarmup);
                    Navigator.pop(context);
                  },
                ),
                if (step.supersetGroupId != null)
                  ListTile(
                    leading: const FaIcon(FontAwesomeIcons.linkSlash, color: AppColors.secondary),
                    title: const Text(
                      'Unpair Superset',
                      style: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600),
                    ),
                    onTap: () {
                      vm.unpairSuperset(index);
                      Navigator.pop(context);
                    },
                  )
                else if (index + 1 < state.steps.length)
                  ListTile(
                    leading: const FaIcon(FontAwesomeIcons.link, color: AppColors.secondary),
                    title: const Text(
                      'Pair Superset with Next',
                      style: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600),
                    ),
                    onTap: () {
                      vm.pairAsSuperset(index, index + 1);
                      Navigator.pop(context);
                    },
                  ),
                ListTile(
                  leading: const FaIcon(FontAwesomeIcons.trash, color: AppColors.error),
                  title: const Text(
                    'Remove from Workout',
                    style: TextStyle(color: AppColors.error, fontWeight: FontWeight.w600),
                  ),
                  onTap: () {
                    vm.removeStep(index);
                    Navigator.pop(context);
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _editWeight(BuildContext context, ActiveWorkoutViewModel vm, int index, double current) async {
    final controller = TextEditingController(text: current.toString());
    try {
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          backgroundColor: AppColors.surfaceElevated,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
            side: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
          ),
          title: const Text(
            'Edit Weight (kg)',
            style: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.bold),
          ),
          content: TextField(
            controller: controller,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            autofocus: true,
            style: const TextStyle(color: AppColors.textPrimary),
          ),
          actions: [
            TextButton(
              child: const Text('Cancel', style: TextStyle(color: AppColors.textSecondary)),
              onPressed: () => Navigator.pop(context),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: AppColors.background,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
              ),
              child: const Text('Save', style: TextStyle(fontWeight: FontWeight.bold)),
              onPressed: () {
                final val = double.tryParse(controller.text);
                if (val != null) {
                  vm.updateStepValues(index, weight: val);
                }
                Navigator.pop(context);
              },
            ),
          ],
        ),
      );
    } finally {
      controller.dispose();
    }
  }

  Future<void> _editReps(BuildContext context, ActiveWorkoutViewModel vm, int index, int current) async {
    final controller = TextEditingController(text: current.toString());
    try {
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          backgroundColor: AppColors.surfaceElevated,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
            side: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
          ),
          title: const Text(
            'Edit Target Reps',
            style: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.bold),
          ),
          content: TextField(
            controller: controller,
            keyboardType: TextInputType.number,
            autofocus: true,
            style: const TextStyle(color: AppColors.textPrimary),
          ),
          actions: [
            TextButton(
              child: const Text('Cancel', style: TextStyle(color: AppColors.textSecondary)),
              onPressed: () => Navigator.pop(context),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: AppColors.background,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
              ),
              child: const Text('Save', style: TextStyle(fontWeight: FontWeight.bold)),
              onPressed: () {
                final val = int.tryParse(controller.text);
                if (val != null) {
                  vm.updateStepValues(index, reps: val);
                }
                Navigator.pop(context);
              },
            ),
          ],
        ),
      );
    } finally {
      controller.dispose();
    }
  }
}

class _CompletedSetRiveBadge extends StatefulWidget {
  const _CompletedSetRiveBadge();

  @override
  State<_CompletedSetRiveBadge> createState() => _CompletedSetRiveBadgeState();
}

class _CompletedSetRiveBadgeState extends State<_CompletedSetRiveBadge> {
  late final FileLoader _fileLoader;

  @override
  void initState() {
    super.initState();
    _fileLoader = FileLoader.fromAsset('assets/animations/set_check_button.riv', riveFactory: Factory.flutter);
  }

  @override
  void dispose() {
    _fileLoader.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return OverflowBox(
      maxWidth: AppDimensions.setCheckAnimSize,
      maxHeight: AppDimensions.setCheckAnimSize,
      child: SizedBox(
        width: AppDimensions.setCheckAnimSize,
        height: AppDimensions.setCheckAnimSize,
        child: RiveWidgetBuilder(
          fileLoader: _fileLoader,
          builder: (context, rState) {
            return switch (rState) {
              RiveLoaded() => RiveWidget(controller: rState.controller, fit: Fit.contain),
              _ => const FaIcon(FontAwesomeIcons.check, size: AppDimensions.iconM, color: AppColors.primary),
            };
          },
        ),
      ),
    );
  }
}

class _MetricColumn extends StatelessWidget {
  final String label;
  final String value;
  final bool highlight;
  final VoidCallback? onTap;

  const _MetricColumn({required this.label, required this.value, this.highlight = false, this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w700, letterSpacing: 0.8, color: AppColors.textMuted),
          ),
          const SizedBox(height: AppDimensions.paddingXS),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: AppDimensions.fontXL,
              fontWeight: FontWeight.w900,
              color: highlight ? AppColors.primary : AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}
