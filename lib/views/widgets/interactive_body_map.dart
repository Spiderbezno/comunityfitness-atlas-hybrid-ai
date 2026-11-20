// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/services/strength_calculator_service.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/viewmodels/muscle_analytics_viewmodel.dart';

class InteractiveBodyMap extends StatefulWidget {
  final Map<String, MuscleRecoveryInfo> muscleRecovery;
  final String selectedMuscle;
  final ValueChanged<String> onMuscleSelected;
  final VoidCallback onExploreExercises;

  const InteractiveBodyMap({
    super.key,
    required this.muscleRecovery,
    required this.selectedMuscle,
    required this.onMuscleSelected,
    required this.onExploreExercises,
  });

  static const List<String> anteriorMuscles = ['Chest', 'Shoulders', 'Biceps', 'Core', 'Quads', 'Calves'];
  static const List<String> posteriorMuscles = ['Back', 'Shoulders', 'Triceps', 'Glutes', 'Hamstrings', 'Calves'];

  static String formatVolumeZoneLabel(String zone, [Translations? tr]) {
    final analytics = tr?.analytics;
    switch (zone) {
      case 'optimal_mav':
        return analytics?.zoneOptimalMav ?? 'Optimal MAV';
      case 'near_mrv':
        return analytics?.zoneNearMrv ?? 'Near MRV';
      case 'over_mrv':
        return analytics?.zoneOverMrv ?? 'Over MRV';
      case 'under_mev':
      default:
        return analytics?.zoneUnderMev ?? 'Under MEV';
    }
  }

  static Color resolveVolumeZoneColor(String zone) {
    switch (zone) {
      case 'optimal_mav':
        return AppColors.success;
      case 'near_mrv':
        return AppColors.warning;
      case 'over_mrv':
        return AppColors.error;
      case 'under_mev':
      default:
        return AppColors.secondary;
    }
  }

  static Color resolveRecoveryStatusColor(String status) {
    switch (status) {
      case 'recovered':
        return AppColors.success;
      case 'recovering':
        return AppColors.warning;
      case 'fatigued':
      default:
        return AppColors.error;
    }
  }

  @override
  State<InteractiveBodyMap> createState() => _InteractiveBodyMapState();
}

class _InteractiveBodyMapState extends State<InteractiveBodyMap> {
  bool _isPosterior = false;

  @override
  void initState() {
    super.initState();
    _syncOrientationWithSelection(widget.selectedMuscle);
  }

  @override
  void didUpdateWidget(covariant InteractiveBodyMap oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.selectedMuscle != widget.selectedMuscle) {
      _syncOrientationWithSelection(widget.selectedMuscle);
    }
  }

  void _syncOrientationWithSelection(String muscle) {
    final inAnterior = InteractiveBodyMap.anteriorMuscles.contains(muscle);
    final inPosterior = InteractiveBodyMap.posteriorMuscles.contains(muscle);
    if (inPosterior && !inAnterior && !_isPosterior) {
      _isPosterior = true;
    } else if (inAnterior && !inPosterior && _isPosterior) {
      _isPosterior = false;
    }
  }

  MuscleRecoveryInfo _resolveInfo(String muscle) {
    final existing = widget.muscleRecovery[muscle];
    if (existing != null) {
      return existing;
    }
    final landmarks = StrengthCalculatorService.getVolumeLandmarks(muscle);
    return MuscleRecoveryInfo(
      muscle: muscle,
      recoveryPercentage: 1.0,
      status: 'recovered',
      weeklySets: 0,
      weeklyVolume: 0.0,
      mev: landmarks.mev,
      mavMin: landmarks.mavMin,
      mavMax: landmarks.mavMax,
      mrv: landmarks.mrv,
      volumeZone: 'under_mev',
    );
  }

  static String _resolveThumbnailForMuscle(String muscle) {
    switch (muscle) {
      case 'Chest':
        return 'assets/animations/thumbnails/barbell_bench_press.png';
      case 'Back':
        return 'assets/animations/thumbnails/lat_pulldown.png';
      case 'Quads':
        return 'assets/animations/thumbnails/barbell_squat.png';
      case 'Hamstrings':
        return 'assets/animations/thumbnails/romanian_deadlift.png';
      case 'Glutes':
        return 'assets/animations/thumbnails/hip_thrust.png';
      case 'Shoulders':
        return 'assets/animations/thumbnails/overhead_press.png';
      case 'Biceps':
        return 'assets/animations/thumbnails/dumbbell_bicep_curl.png';
      case 'Triceps':
        return 'assets/animations/thumbnails/tricep_pushdown.png';
      case 'Core':
        return 'assets/animations/thumbnails/plank.png';
      case 'Calves':
      default:
        return 'assets/animations/thumbnails/calf_raise.png';
    }
  }

  @override
  Widget build(BuildContext context) {
    final tr = TranslationProvider.of(context).translations;
    final activeMuscles = _isPosterior ? InteractiveBodyMap.posteriorMuscles : InteractiveBodyMap.anteriorMuscles;
    final selectedInfo = _resolveInfo(widget.selectedMuscle);

    return Container(
      padding: const EdgeInsets.all(AppDimensions.paddingM),
      decoration: BoxDecoration(
        color: AppColors.surfaceElevated,
        borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
        border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Row 1: Header Title
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(AppDimensions.paddingXS),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: AppColors.opacityLow),
                  borderRadius: BorderRadius.circular(AppDimensions.radiusBadge),
                ),
                child: const FaIcon(FontAwesomeIcons.personRays, size: AppDimensions.iconS, color: AppColors.primary),
              ),
              const SizedBox(width: AppDimensions.paddingS),
              Expanded(
                child: Text(
                  tr.analytics.bodyMapTitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: AppDimensions.fontM, fontWeight: FontWeight.w900, color: AppColors.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingS),

          // Row 2: Full-width Front/Back Orientation Toggle
          _buildOrientationToggle(tr),
          const SizedBox(height: AppDimensions.paddingM),

          // Anatomical Canvas + Interactive Muscle Nodes
          Builder(
            builder: (context) {
              final leftMuscles = activeMuscles.take(3).toList();
              final rightMuscles = activeMuscles.skip(3).take(3).toList();
              return IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Left column of muscle selectors (first 3)
                    Expanded(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          for (int i = 0; i < leftMuscles.length; i++) ...[
                            if (i > 0) const SizedBox(height: AppDimensions.paddingXS),
                            _buildMuscleNodeButton(leftMuscles[i], tr),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(width: AppDimensions.paddingS),
                    // Center 2.5D Anatomical Silhouette Canvas
                    Expanded(
                      child: Container(
                        constraints: const BoxConstraints(minHeight: AppDimensions.animationPlayerHeight),
                        decoration: BoxDecoration(
                          color: AppColors.background,
                          borderRadius: BorderRadius.circular(AppDimensions.radiusM),
                          border: Border.all(color: AppColors.borderSubtle, width: AppDimensions.borderDefault),
                        ),
                        child: CustomPaint(
                          painter: _AnatomicalBodyPainter(
                            isPosterior: _isPosterior,
                            selectedMuscle: widget.selectedMuscle,
                            muscleColors: {
                              for (final m in MuscleAnalyticsViewModel.standardMuscles)
                                m: InteractiveBodyMap.resolveRecoveryStatusColor(_resolveInfo(m).status),
                            },
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: AppDimensions.paddingS),
                    // Right column of muscle selectors (last 3)
                    Expanded(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          for (int i = 0; i < rightMuscles.length; i++) ...[
                            if (i > 0) const SizedBox(height: AppDimensions.paddingXS),
                            _buildMuscleNodeButton(rightMuscles[i], tr),
                          ],
                        ],
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
          const SizedBox(height: AppDimensions.paddingM),

          // Recovery Status Legend
          Wrap(
            spacing: AppDimensions.paddingM,
            runSpacing: AppDimensions.paddingXS,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              _buildLegendDot(tr.analytics.recoveredStatus, AppColors.success),
              _buildLegendDot(tr.analytics.recoveringStatus, AppColors.warning),
              _buildLegendDot(tr.analytics.fatiguedStatus, AppColors.error),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const FaIcon(FontAwesomeIcons.bolt, size: AppDimensions.iconXS, color: AppColors.secondary),
                  const SizedBox(width: AppDimensions.paddingXS),
                  Flexible(
                    child: Text(
                      _isPosterior ? tr.analytics.posteriorChainLabel : tr.analytics.anteriorChainLabel,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w700, color: AppColors.secondary),
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingM),

          // Selected Muscle MEV / MAV / MRV Telemetry Card
          _buildSelectedTelemetryCard(selectedInfo, tr),
        ],
      ),
    );
  }

  Widget _buildOrientationToggle(Translations tr) {
    return Container(
      padding: const EdgeInsets.all(AppDimensions.paddingXXS),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(AppDimensions.radiusS),
        border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
      ),
      child: Row(
        children: [
          Expanded(
            child: GestureDetector(
              key: const Key('body_map_anterior_tab'),
              onTap: () {
                setState(() {
                  _isPosterior = false;
                });
              },
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXS),
                decoration: BoxDecoration(
                  color: !_isPosterior ? AppColors.primary : AppColors.transparent,
                  borderRadius: BorderRadius.circular(AppDimensions.radiusBadge),
                ),
                alignment: Alignment.center,
                child: Text(
                  tr.analytics.frontViewTab,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: AppDimensions.fontXXS,
                    fontWeight: FontWeight.w900,
                    color: !_isPosterior ? AppColors.background : AppColors.textSecondary,
                  ),
                ),
              ),
            ),
          ),
          Expanded(
            child: GestureDetector(
              key: const Key('body_map_posterior_tab'),
              onTap: () {
                setState(() {
                  _isPosterior = true;
                });
              },
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXS),
                decoration: BoxDecoration(
                  color: _isPosterior ? AppColors.primary : AppColors.transparent,
                  borderRadius: BorderRadius.circular(AppDimensions.radiusBadge),
                ),
                alignment: Alignment.center,
                child: Text(
                  tr.analytics.backViewTab,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: AppDimensions.fontXXS,
                    fontWeight: FontWeight.w900,
                    color: _isPosterior ? AppColors.background : AppColors.textSecondary,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMuscleNodeButton(String muscle, Translations tr) {
    final info = _resolveInfo(muscle);
    final isSelected = widget.selectedMuscle == muscle;
    final statusColor = InteractiveBodyMap.resolveRecoveryStatusColor(info.status);

    return GestureDetector(
      key: Key('body_map_muscle_$muscle'),
      onTap: () => widget.onMuscleSelected(muscle),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXS),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.primary.withValues(alpha: AppColors.opacityLow) : AppColors.background,
          borderRadius: BorderRadius.circular(AppDimensions.radiusS),
          border: Border.all(
            color: isSelected ? AppColors.primary : statusColor.withValues(alpha: AppColors.opacityMedium),
            width: isSelected ? AppDimensions.borderThick : AppDimensions.borderDefault,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Flexible(
                  child: Text(
                    tr.translateMuscle(muscle),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: AppDimensions.fontXS,
                      fontWeight: FontWeight.w900,
                      color: isSelected ? AppColors.primary : AppColors.textPrimary,
                    ),
                  ),
                ),
                Container(
                  width: AppDimensions.dotSize,
                  height: AppDimensions.dotSize,
                  decoration: BoxDecoration(shape: BoxShape.circle, color: statusColor),
                ),
              ],
            ),
            const SizedBox(height: AppDimensions.paddingXXS),
            Text(
              '${info.weeklySets}/${info.mavMin}s',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: AppDimensions.fontXXS, color: AppColors.textSecondary, fontWeight: FontWeight.w700),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLegendDot(String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: AppDimensions.dotSize,
          height: AppDimensions.dotSize,
          decoration: BoxDecoration(shape: BoxShape.circle, color: color),
        ),
        const SizedBox(width: AppDimensions.paddingXS),
        Flexible(
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: AppDimensions.fontXXS, color: AppColors.textSecondary, fontWeight: FontWeight.w600),
          ),
        ),
      ],
    );
  }

  String _localizedVolumeZone(String zone, Translations tr) {
    return InteractiveBodyMap.formatVolumeZoneLabel(zone, tr);
  }

  Widget _buildSelectedTelemetryCard(MuscleRecoveryInfo info, Translations tr) {
    final zoneLabel = _localizedVolumeZone(info.volumeZone, tr);
    final zoneColor = InteractiveBodyMap.resolveVolumeZoneColor(info.volumeZone);
    final statusColor = InteractiveBodyMap.resolveRecoveryStatusColor(info.status);
    final thumbnailAsset = _resolveThumbnailForMuscle(info.muscle);

    return Container(
      key: const Key('selected_muscle_telemetry_card'),
      padding: const EdgeInsets.all(AppDimensions.paddingM),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(AppDimensions.radiusM),
        border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              // Rive HD Thumbnail Preview Badge
              ClipRRect(
                borderRadius: BorderRadius.circular(AppDimensions.radiusS),
                child: Container(
                  width: AppDimensions.thumbnailSize,
                  height: AppDimensions.thumbnailSize,
                  decoration: BoxDecoration(
                    color: AppColors.surfaceElevated,
                    borderRadius: BorderRadius.circular(AppDimensions.radiusS),
                    border: Border.all(
                      color: AppColors.secondary.withValues(alpha: AppColors.opacityMedium),
                      width: AppDimensions.borderDefault,
                    ),
                  ),
                  child: Image.asset(
                    thumbnailAsset,
                    fit: BoxFit.cover,
                    cacheWidth: AppDimensions.thumbnailCacheSize,
                    errorBuilder: (context, error, stackTrace) => const Center(
                      child: FaIcon(FontAwesomeIcons.dumbbell, size: AppDimensions.iconM, color: AppColors.secondary),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: AppDimensions.paddingS),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            tr.translateMuscle(info.muscle),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: AppDimensions.fontL, fontWeight: FontWeight.w900, color: AppColors.textPrimary),
                          ),
                        ),
                        const SizedBox(width: AppDimensions.paddingXS),
                        Flexible(
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXXS),
                            decoration: BoxDecoration(
                              color: zoneColor.withValues(alpha: AppColors.opacityLow),
                              borderRadius: BorderRadius.circular(AppDimensions.radiusBadge),
                              border: Border.all(
                                color: zoneColor.withValues(alpha: AppColors.opacityMedium),
                                width: AppDimensions.borderThin,
                              ),
                            ),
                            child: Text(
                              zoneLabel,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w900, color: zoneColor),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppDimensions.paddingXXS),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Flexible(
                          child: Text(
                            tr.analytics.weeklySetsRange(current: info.weeklySets, min: info.mavMin, max: info.mavMax),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: AppDimensions.fontS, fontWeight: FontWeight.w700, color: AppColors.textSecondary),
                          ),
                        ),
                        const SizedBox(width: AppDimensions.paddingXS),
                        Flexible(
                          child: Text(
                            tr.analytics.recoveryPercent(percent: (info.recoveryPercentage * 100).toInt()),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(fontSize: AppDimensions.fontXS, fontWeight: FontWeight.w900, color: statusColor),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingM),

          // MEV / MAV / MRV Segmented Landmark Gauge
          _buildVolumeLandmarkBar(info, zoneColor),
          const SizedBox(height: AppDimensions.paddingXS),

          // Explicit MEV / MAV / MRV Landmark Labels
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Text(
                  'MEV ${info.mev}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w800, color: AppColors.textMuted),
                ),
              ),
              Flexible(
                child: Text(
                  'MAV ${info.mavMin}-${info.mavMax}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w900, color: AppColors.success),
                ),
              ),
              Flexible(
                child: Text(
                  'MRV ${info.mrv}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w800, color: AppColors.warning),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingM),

          // 1-Tap Drill-Down Action Button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              key: const Key('train_selected_muscle_button'),
              onPressed: widget.onExploreExercises,
              icon: const FaIcon(FontAwesomeIcons.bolt, size: AppDimensions.iconS, color: AppColors.background),
              label: Text(
                tr.analytics.exploreMuscleExercises(muscle: tr.translateMuscle(info.muscle)),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: AppDimensions.fontS, fontWeight: FontWeight.w900, color: AppColors.background),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVolumeLandmarkBar(MuscleRecoveryInfo info, Color activeColor) {
    const int totalSegments = 10;
    final double ratio = info.mrv > 0 ? (info.weeklySets / info.mrv).clamp(0.0, 1.0) : 0.0;
    final int activeSegments = info.weeklySets <= 0 ? 0 : (ratio * totalSegments).clamp(1.0, totalSegments.toDouble()).round();

    return Row(
      children: List.generate(totalSegments, (index) {
        final isActive = index < activeSegments;
        return Expanded(
          child: Container(
            height: AppDimensions.paddingS,
            margin: EdgeInsets.only(right: index < totalSegments - 1 ? AppDimensions.paddingXXS : 0),
            decoration: BoxDecoration(
              color: isActive ? activeColor : AppColors.surfaceElevated,
              borderRadius: BorderRadius.circular(AppDimensions.radiusBadge),
              border: Border.all(color: isActive ? activeColor : AppColors.borderSubtle, width: AppDimensions.borderThin),
            ),
          ),
        );
      }),
    );
  }
}

class _AnatomicalBodyPainter extends CustomPainter {
  final bool isPosterior;
  final String selectedMuscle;
  final Map<String, Color> muscleColors;

  const _AnatomicalBodyPainter({required this.isPosterior, required this.selectedMuscle, required this.muscleColors});

  Paint _paintFor(String muscle) {
    final isSelected = selectedMuscle == muscle;
    final baseColor = muscleColors[muscle] ?? AppColors.secondary;
    return Paint()
      ..style = PaintingStyle.fill
      ..color = isSelected ? AppColors.primary : baseColor.withValues(alpha: AppColors.opacityHigh);
  }

  Paint _strokeFor(String muscle) {
    final isSelected = selectedMuscle == muscle;
    return Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = isSelected ? AppDimensions.borderThick : AppDimensions.borderThin
      ..color = isSelected ? AppColors.white : AppColors.border;
  }

  void _drawRegion(Canvas canvas, RRect rrect, String muscle) {
    canvas.drawRRect(rrect, _paintFor(muscle));
    canvas.drawRRect(rrect, _strokeFor(muscle));
  }

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final h = size.height;
    final w = size.width;
    const r = Radius.circular(AppDimensions.radiusXS);

    final silhouettePaint = Paint()
      ..style = PaintingStyle.fill
      ..color = AppColors.surfaceElevated;
    final silhouetteBorder = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = AppDimensions.borderDefault
      ..color = AppColors.border;

    // Head & Neck
    final headRect = Rect.fromCenter(center: Offset(cx, h * 0.10), width: w * 0.18, height: h * 0.11);
    canvas.drawOval(headRect, silhouettePaint);
    canvas.drawOval(headRect, silhouetteBorder);

    // Shoulders (Deltoids)
    _drawRegion(
      canvas,
      RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx - w * 0.24, h * 0.23), width: w * 0.14, height: h * 0.09), r),
      'Shoulders',
    );
    _drawRegion(
      canvas,
      RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx + w * 0.24, h * 0.23), width: w * 0.14, height: h * 0.09), r),
      'Shoulders',
    );

    if (!isPosterior) {
      // Anterior: Chest (Pectorals)
      _drawRegion(canvas, RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx, h * 0.25), width: w * 0.32, height: h * 0.12), r), 'Chest');

      // Anterior: Biceps
      _drawRegion(
        canvas,
        RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx - w * 0.27, h * 0.36), width: w * 0.11, height: h * 0.14), r),
        'Biceps',
      );
      _drawRegion(
        canvas,
        RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx + w * 0.27, h * 0.36), width: w * 0.11, height: h * 0.14), r),
        'Biceps',
      );

      // Anterior: Core (Abs / Obliques)
      _drawRegion(canvas, RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx, h * 0.41), width: w * 0.26, height: h * 0.17), r), 'Core');

      // Anterior: Quads
      _drawRegion(
        canvas,
        RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx - w * 0.09, h * 0.63), width: w * 0.14, height: h * 0.21), r),
        'Quads',
      );
      _drawRegion(
        canvas,
        RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx + w * 0.09, h * 0.63), width: w * 0.14, height: h * 0.21), r),
        'Quads',
      );
    } else {
      // Posterior: Back (Lats / Traps / Erectors)
      _drawRegion(canvas, RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx, h * 0.31), width: w * 0.34, height: h * 0.22), r), 'Back');

      // Posterior: Triceps
      _drawRegion(
        canvas,
        RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx - w * 0.27, h * 0.36), width: w * 0.11, height: h * 0.14), r),
        'Triceps',
      );
      _drawRegion(
        canvas,
        RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx + w * 0.27, h * 0.36), width: w * 0.11, height: h * 0.14), r),
        'Triceps',
      );

      // Posterior: Glutes
      _drawRegion(canvas, RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx, h * 0.49), width: w * 0.28, height: h * 0.11), r), 'Glutes');

      // Posterior: Hamstrings
      _drawRegion(
        canvas,
        RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx - w * 0.09, h * 0.66), width: w * 0.14, height: h * 0.17), r),
        'Hamstrings',
      );
      _drawRegion(
        canvas,
        RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx + w * 0.09, h * 0.66), width: w * 0.14, height: h * 0.17), r),
        'Hamstrings',
      );
    }

    // Calves (Both Anterior & Posterior)
    _drawRegion(
      canvas,
      RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx - w * 0.09, h * 0.85), width: w * 0.11, height: h * 0.15), r),
      'Calves',
    );
    _drawRegion(
      canvas,
      RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(cx + w * 0.09, h * 0.85), width: w * 0.11, height: h * 0.15), r),
      'Calves',
    );
  }

  @override
  bool shouldRepaint(covariant _AnatomicalBodyPainter oldDelegate) {
    return oldDelegate.isPosterior != isPosterior || oldDelegate.selectedMuscle != selectedMuscle || oldDelegate.muscleColors != muscleColors;
  }
}
