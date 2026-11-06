// 🐦 Flutter imports:
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

// 📦 Package imports:
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/viewmodels/active_workout_viewmodel.dart';
import 'package:comunityfitness/viewmodels/muscle_analytics_viewmodel.dart';

class WorkoutAnatomicalSummarySheet extends StatelessWidget {
  final String routineTitle;
  final int durationSeconds;
  final double totalVolume;
  final int totalSets;
  final Map<String, int> muscleSets;
  final String? ghostTitle;
  final double? ghostDeltaVolume;

  const WorkoutAnatomicalSummarySheet({
    super.key,
    required this.routineTitle,
    required this.durationSeconds,
    required this.totalVolume,
    required this.totalSets,
    required this.muscleSets,
    this.ghostTitle,
    this.ghostDeltaVolume,
  });

  factory WorkoutAnatomicalSummarySheet.fromActiveState({Key? key, required ActiveWorkoutState state}) {
    final Map<String, int> activatedMuscles = {};
    int completedSetsTotal = 0;
    double volumeTotal = 0.0;

    final nonWarmupSteps = state.steps.where((s) => !s.isWarmup).toList();
    final hasAnyCompleted = nonWarmupSteps.any((s) => s.completedSets > 0);

    for (final item in nonWarmupSteps) {
      final setsCount = hasAnyCompleted ? item.completedSets : item.sets;
      if (setsCount <= 0) {
        continue;
      }
      completedSetsTotal += setsCount;
      final unitWeight = item.weight > 0 ? item.weight : 1.0;
      volumeTotal += unitWeight * item.reps * setsCount;

      final targetMuscles = MuscleAnalyticsViewModel.resolveTargetMuscles(item.exercise);
      for (final muscle in targetMuscles) {
        activatedMuscles[muscle] = (activatedMuscles[muscle] ?? 0) + setsCount;
      }
    }

    return WorkoutAnatomicalSummarySheet(
      key: key,
      routineTitle: state.routineTitle,
      durationSeconds: state.elapsedSeconds,
      totalVolume: state.liveVolume > 0 ? state.liveVolume : volumeTotal,
      totalSets: completedSetsTotal,
      muscleSets: activatedMuscles,
      ghostTitle: state.ghostTitle,
      ghostDeltaVolume: state.ghostDeltaVolume,
    );
  }

  factory WorkoutAnatomicalSummarySheet.fromSession({Key? key, required WorkoutSession session, required Map<String, Exercise> exercisesById}) {
    final Map<String, int> activatedMuscles = {};
    int totalSets = 0;
    double totalVolume = 0.0;

    for (final step in session.steps.where((s) => !s.isWarmup)) {
      if (step.sets <= 0) {
        continue;
      }
      totalSets += step.sets;
      final unitWeight = step.weight > 0 ? step.weight : 1.0;
      totalVolume += unitWeight * step.reps * step.sets;

      final exercise = exercisesById[step.exerciseId];
      if (exercise != null) {
        final targetMuscles = MuscleAnalyticsViewModel.resolveTargetMuscles(exercise);
        for (final muscle in targetMuscles) {
          activatedMuscles[muscle] = (activatedMuscles[muscle] ?? 0) + step.sets;
        }
      }
    }

    final durationSeconds = session.completedAt != null ? session.completedAt!.difference(session.startedAt).inSeconds : 0;

    return WorkoutAnatomicalSummarySheet(
      key: key,
      routineTitle: session.routineTitle ?? 'Workout Session',
      durationSeconds: durationSeconds > 0 ? durationSeconds : 0,
      totalVolume: totalVolume,
      totalSets: totalSets,
      muscleSets: activatedMuscles,
    );
  }

  String _buildGhostVerdictLabel(Translations tr) {
    final delta = ghostDeltaVolume;
    if (delta == null) {
      return tr.workout.ghostVerdictCompleted;
    }
    if (delta > 0) {
      return tr.workout.ghostVerdictAhead(delta: delta.toStringAsFixed(0));
    }
    if (delta < 0) {
      return tr.workout.ghostVerdictBehind(delta: delta.toStringAsFixed(0));
    }
    return tr.workout.ghostVerdictOnPace;
  }

  Color _buildGhostVerdictColor() {
    final delta = ghostDeltaVolume;
    if (delta == null) {
      return AppColors.secondary;
    }
    if (delta > 0) {
      return AppColors.success;
    }
    if (delta < 0) {
      return AppColors.warning;
    }
    return AppColors.secondary;
  }

  @override
  Widget build(BuildContext context) {
    final tr = TranslationProvider.of(context).translations;
    final durationMinutes = durationSeconds ~/ 60;
    final verdictColor = _buildGhostVerdictColor();
    final sortedEntries = muscleSets.entries.toList()..sort((a, b) => b.value.compareTo(a.value));

    return SafeArea(
      child: Container(
        key: const Key('workout_anatomical_summary_sheet'),
        padding: const EdgeInsets.all(AppDimensions.paddingL),
        decoration: const BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.vertical(top: Radius.circular(AppDimensions.radiusBottomSheet)),
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: AppDimensions.dragHandleWidth,
                  height: AppDimensions.dragHandleHeight,
                  decoration: BoxDecoration(color: AppColors.border, borderRadius: BorderRadius.circular(AppDimensions.radiusPill)),
                ),
              ),
              const SizedBox(height: AppDimensions.paddingM),
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(AppDimensions.paddingS),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withValues(alpha: AppColors.opacityLow),
                      borderRadius: BorderRadius.circular(AppDimensions.radiusS),
                      border: Border.all(
                        color: AppColors.primary.withValues(alpha: AppColors.opacityMedium),
                        width: AppDimensions.borderThin,
                      ),
                    ),
                    child: const FaIcon(FontAwesomeIcons.trophy, size: AppDimensions.iconM, color: AppColors.primary),
                  ),
                  const SizedBox(width: AppDimensions.paddingS),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          tr.workout.anatomicalCardHeader,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: AppDimensions.fontXXS,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 1.0,
                            color: AppColors.primary,
                          ),
                        ),
                        Text(
                          routineTitle,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: AppDimensions.fontXL, fontWeight: FontWeight.w900, color: AppColors.textPrimary),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppDimensions.paddingM),
              Container(
                key: const Key('summary_ghost_outcome_badge'),
                padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM, vertical: AppDimensions.paddingXS),
                decoration: BoxDecoration(
                  color: verdictColor.withValues(alpha: AppColors.opacityLow),
                  borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                  border: Border.all(
                    color: verdictColor.withValues(alpha: AppColors.opacityMedium),
                    width: AppDimensions.borderThin,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    FaIcon(FontAwesomeIcons.ghost, size: AppDimensions.iconS, color: verdictColor),
                    const SizedBox(width: AppDimensions.paddingXS),
                    Flexible(
                      child: Text(
                        _buildGhostVerdictLabel(tr),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: AppDimensions.fontS, fontWeight: FontWeight.w800, color: verdictColor),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppDimensions.paddingM),
              Container(
                padding: const EdgeInsets.all(AppDimensions.paddingM),
                decoration: BoxDecoration(
                  color: AppColors.surfaceElevated,
                  borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                  border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    Flexible(
                      child: _SummaryMetricCell(label: tr.analytics.volumeTitle, value: '${totalVolume.toStringAsFixed(0)} kg'),
                    ),
                    Container(height: AppDimensions.paddingL, width: AppDimensions.borderDefault, color: AppColors.border),
                    Flexible(
                      child: _SummaryMetricCell(label: tr.workout.completedSetsLabel, value: '$totalSets'),
                    ),
                    Container(height: AppDimensions.paddingL, width: AppDimensions.borderDefault, color: AppColors.border),
                    Flexible(
                      child: _SummaryMetricCell(label: tr.workout.durationLabel, value: '${durationMinutes}m'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppDimensions.paddingM),
              Container(
                padding: const EdgeInsets.all(AppDimensions.paddingM),
                decoration: BoxDecoration(
                  color: AppColors.surfaceElevated,
                  borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                  border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      tr.workout.muscleActivationSectionTitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: AppDimensions.fontXXS,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.8,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: AppDimensions.paddingXS),
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            tr.analytics.frontViewTab,
                            textAlign: TextAlign.center,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: AppDimensions.fontXXS,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.8,
                              color: AppColors.textMuted,
                            ),
                          ),
                        ),
                        Expanded(
                          child: Text(
                            tr.analytics.backViewTab,
                            textAlign: TextAlign.center,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: AppDimensions.fontXXS,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.8,
                              color: AppColors.textMuted,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppDimensions.paddingS),
                    SizedBox(
                      height: AppDimensions.appBarExpandedHeight,
                      width: double.infinity,
                      child: CustomPaint(painter: _MiniAnatomicalSilhouettePainter(muscleSets: muscleSets)),
                    ),
                    const SizedBox(height: AppDimensions.paddingM),
                    if (sortedEntries.isEmpty)
                      Text(
                        tr.dashboard.noWorkoutsYet,
                        style: const TextStyle(fontSize: AppDimensions.fontS, color: AppColors.textSecondary),
                      )
                    else
                      Wrap(
                        spacing: AppDimensions.paddingS,
                        runSpacing: AppDimensions.paddingXS,
                        children: sortedEntries.map((entry) {
                          return Container(
                            key: Key('summary_muscle_chip_${entry.key}'),
                            padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM, vertical: AppDimensions.paddingXS),
                            decoration: BoxDecoration(
                              color: AppColors.primary.withValues(alpha: AppColors.opacityLow),
                              borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                              border: Border.all(
                                color: AppColors.primary.withValues(alpha: AppColors.opacityMedium),
                                width: AppDimensions.borderThin,
                              ),
                            ),
                            child: Text(
                              '${tr.translateMuscle(entry.key)} · ${entry.value}s',
                              style: const TextStyle(fontSize: AppDimensions.fontS, fontWeight: FontWeight.w800, color: AppColors.textPrimary),
                            ),
                          );
                        }).toList(),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: AppDimensions.paddingL),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      key: const Key('share_anatomical_card_button'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.textPrimary,
                        side: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
                        padding: const EdgeInsets.symmetric(vertical: AppDimensions.paddingM),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
                      ),
                      icon: const FaIcon(FontAwesomeIcons.shareNodes, size: AppDimensions.iconS, color: AppColors.secondary),
                      label: Text(
                        tr.workout.copyShareCardButton,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                      onPressed: () async {
                        final musclesLine = sortedEntries.isEmpty
                            ? tr.translateMuscle('Full Body')
                            : sortedEntries.map((e) => '${tr.translateMuscle(e.key)} (${e.value}s)').join(', ');
                        final shareText =
                            'CommunityFitness · $routineTitle\n${tr.analytics.volumeTitle}: ${totalVolume.toStringAsFixed(0)} kg ($totalSets)\n$musclesLine';
                        await Clipboard.setData(ClipboardData(text: shareText));
                        if (context.mounted) {
                          ScaffoldMessenger.of(context)
                              .showSnackBar(SnackBar(content: Text(tr.workout.cardCopiedSnackbar), backgroundColor: AppColors.surfaceElevated));
                        }
                      },
                    ),
                  ),
                  const SizedBox(width: AppDimensions.paddingM),
                  Expanded(
                    child: ElevatedButton.icon(
                      key: const Key('close_anatomical_summary_button'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: AppColors.background,
                        padding: const EdgeInsets.symmetric(vertical: AppDimensions.paddingM),
                        elevation: 0,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
                      ),
                      icon: const FaIcon(FontAwesomeIcons.check, size: AppDimensions.iconS),
                      label: Text(
                        tr.workout.doneButton,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w900),
                      ),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SummaryMetricCell extends StatelessWidget {
  final String label;
  final String value;

  const _SummaryMetricCell({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: AppDimensions.fontL, fontWeight: FontWeight.w900, color: AppColors.textPrimary),
        ),
        const SizedBox(height: AppDimensions.paddingXXS),
        Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w700, letterSpacing: 0.6, color: AppColors.textMuted),
        ),
      ],
    );
  }
}

class _MiniAnatomicalSilhouettePainter extends CustomPainter {
  final Map<String, int> muscleSets;

  const _MiniAnatomicalSilhouettePainter({required this.muscleSets});

  Paint _paintFor(String muscle) {
    final sets = muscleSets[muscle] ?? 0;
    if (sets <= 0) {
      return Paint()
        ..color = AppColors.surface
        ..style = PaintingStyle.fill;
    }
    return Paint()
      ..color = sets >= 3 ? AppColors.primary : AppColors.secondary
      ..style = PaintingStyle.fill;
  }

  @override
  void paint(Canvas canvas, Size size) {
    final outlinePaint = Paint()
      ..color = AppColors.border
      ..style = PaintingStyle.stroke
      ..strokeWidth = AppDimensions.borderDefault;

    final headPaint = Paint()
      ..color = AppColors.surface
      ..style = PaintingStyle.fill;

    // Anterior figure centered at 25% width
    final ax = size.width * 0.25;
    // Posterior figure centered at 75% width
    final px = size.width * 0.75;
    final h = size.height;

    // Heads
    canvas.drawCircle(Offset(ax, h * 0.12), h * 0.07, headPaint);
    canvas.drawCircle(Offset(ax, h * 0.12), h * 0.07, outlinePaint);
    canvas.drawCircle(Offset(px, h * 0.12), h * 0.07, headPaint);
    canvas.drawCircle(Offset(px, h * 0.12), h * 0.07, outlinePaint);

    // Anterior regions: Shoulders, Chest, Core, Biceps, Quads, Calves
    _drawRectRegion(canvas, Offset(ax - h * 0.18, h * 0.22), Size(h * 0.36, h * 0.07), 'Shoulders', outlinePaint);
    _drawRectRegion(canvas, Offset(ax - h * 0.13, h * 0.30), Size(h * 0.26, h * 0.12), 'Chest', outlinePaint);
    _drawRectRegion(canvas, Offset(ax - h * 0.11, h * 0.43), Size(h * 0.22, h * 0.15), 'Core', outlinePaint);
    _drawRectRegion(canvas, Offset(ax - h * 0.22, h * 0.31), Size(h * 0.07, h * 0.20), 'Biceps', outlinePaint);
    _drawRectRegion(canvas, Offset(ax + h * 0.15, h * 0.31), Size(h * 0.07, h * 0.20), 'Biceps', outlinePaint);
    _drawRectRegion(canvas, Offset(ax - h * 0.12, h * 0.60), Size(h * 0.10, h * 0.20), 'Quads', outlinePaint);
    _drawRectRegion(canvas, Offset(ax + h * 0.02, h * 0.60), Size(h * 0.10, h * 0.20), 'Quads', outlinePaint);
    _drawRectRegion(canvas, Offset(ax - h * 0.11, h * 0.82), Size(h * 0.09, h * 0.14), 'Calves', outlinePaint);
    _drawRectRegion(canvas, Offset(ax + h * 0.02, h * 0.82), Size(h * 0.09, h * 0.14), 'Calves', outlinePaint);

    // Posterior regions: Shoulders, Back, Triceps, Glutes, Hamstrings, Calves
    _drawRectRegion(canvas, Offset(px - h * 0.18, h * 0.22), Size(h * 0.36, h * 0.07), 'Shoulders', outlinePaint);
    _drawRectRegion(canvas, Offset(px - h * 0.14, h * 0.30), Size(h * 0.28, h * 0.18), 'Back', outlinePaint);
    _drawRectRegion(canvas, Offset(px - h * 0.22, h * 0.31), Size(h * 0.07, h * 0.20), 'Triceps', outlinePaint);
    _drawRectRegion(canvas, Offset(px + h * 0.15, h * 0.31), Size(h * 0.07, h * 0.20), 'Triceps', outlinePaint);
    _drawRectRegion(canvas, Offset(px - h * 0.13, h * 0.49), Size(h * 0.26, h * 0.10), 'Glutes', outlinePaint);
    _drawRectRegion(canvas, Offset(px - h * 0.12, h * 0.60), Size(h * 0.10, h * 0.20), 'Hamstrings', outlinePaint);
    _drawRectRegion(canvas, Offset(px + h * 0.02, h * 0.60), Size(h * 0.10, h * 0.20), 'Hamstrings', outlinePaint);
    _drawRectRegion(canvas, Offset(px - h * 0.11, h * 0.82), Size(h * 0.09, h * 0.14), 'Calves', outlinePaint);
    _drawRectRegion(canvas, Offset(px + h * 0.02, h * 0.82), Size(h * 0.09, h * 0.14), 'Calves', outlinePaint);
  }

  void _drawRectRegion(Canvas canvas, Offset topLeft, Size size, String muscle, Paint outlinePaint) {
    final rrect = RRect.fromRectAndRadius(topLeft & size, const Radius.circular(AppDimensions.radiusXS));
    canvas.drawRRect(rrect, _paintFor(muscle));
    canvas.drawRRect(rrect, outlinePaint);
  }

  @override
  bool shouldRepaint(covariant _MiniAnatomicalSilhouettePainter oldDelegate) {
    return oldDelegate.muscleSets != muscleSets;
  }
}
