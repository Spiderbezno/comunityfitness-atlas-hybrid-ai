// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/viewmodels/exercise_catalog_viewmodel.dart';
import 'package:comunityfitness/viewmodels/muscle_analytics_viewmodel.dart';
import 'package:comunityfitness/views/exercise_catalog_screen.dart';
import 'package:comunityfitness/views/widgets/app_back_button.dart';
import 'package:comunityfitness/views/widgets/interactive_body_map.dart';

class MuscleAnalyticsScreen extends ConsumerStatefulWidget {
  const MuscleAnalyticsScreen({super.key});

  @override
  ConsumerState<MuscleAnalyticsScreen> createState() => _MuscleAnalyticsScreenState();
}

class _MuscleAnalyticsScreenState extends ConsumerState<MuscleAnalyticsScreen> {
  String _selectedMuscle = 'Chest';

  static String _mapToCatalogMuscle(String muscle) {
    switch (muscle) {
      case 'Quads':
      case 'Hamstrings':
      case 'Glutes':
      case 'Calves':
        return 'Legs';
      case 'Biceps':
      case 'Triceps':
        return 'Arms';
      default:
        return muscle;
    }
  }

  void _exploreSelectedMuscleExercises() {
    final catalogMuscle = _mapToCatalogMuscle(_selectedMuscle);
    ref.read(exerciseCatalogViewModelProvider.notifier).selectMuscleGroup(catalogMuscle);
    Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const ExerciseCatalogScreen()));
  }

  @override
  Widget build(BuildContext context) {
    final tr = TranslationProvider.of(context).translations;
    final state = ref.watch(muscleAnalyticsViewModelProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        scrolledUnderElevation: 0,
        leading: const AppBackButton(),
        title: Text(
          tr.analytics.screenTitle,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: AppDimensions.fontXL, fontWeight: FontWeight.w900, letterSpacing: 0.3, color: AppColors.textPrimary),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppDimensions.paddingM),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top Athletic Summary Cards
            Row(
              children: [
                Expanded(
                  child: _SummaryCard(
                    icon: FontAwesomeIcons.fire,
                    iconColor: AppColors.primary,
                    title: tr.analytics.workoutsTitle,
                    value: '${state.totalWorkoutsThisWeek}',
                    subtitle: tr.analytics.thisWeekSubtitle,
                  ),
                ),
                const SizedBox(width: AppDimensions.paddingM),
                Expanded(
                  child: _SummaryCard(
                    icon: FontAwesomeIcons.dumbbell,
                    iconColor: AppColors.secondary,
                    title: tr.analytics.volumeTitle,
                    value: '${(state.totalVolumeThisWeek / 1000).toStringAsFixed(1)}t',
                    subtitle: '${state.totalVolumeThisWeek.toStringAsFixed(0)} kg',
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppDimensions.paddingL),

            // Interactive 3D/2.5D Anatomical Body Map with MEV/MAV/MRV Telemetry
            InteractiveBodyMap(
              muscleRecovery: state.muscleRecovery,
              selectedMuscle: _selectedMuscle,
              onMuscleSelected: (muscle) {
                setState(() {
                  _selectedMuscle = muscle;
                });
              },
              onExploreExercises: _exploreSelectedMuscleExercises,
            ),
            const SizedBox(height: AppDimensions.paddingL),

            // Muscle Recovery Status Section
            Builder(
              builder: (context) {
                final readyCount = state.muscleRecovery.values.where((m) => m.status == 'recovered').length;
                final totalCount = state.muscleRecovery.length;
                return Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        tr.analytics.muscleRecoverySectionTitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: AppDimensions.fontL,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 0.2,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                    const SizedBox(width: AppDimensions.paddingS),
                    Flexible(
                      child: Text(
                        tr.analytics.readyCountBadge(ready: readyCount, total: totalCount),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: AppDimensions.fontXXS,
                          fontWeight: FontWeight.w900,
                          color: AppColors.secondary,
                          letterSpacing: 0.8,
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
            const SizedBox(height: AppDimensions.paddingS),

            if (state.muscleRecovery.isEmpty)
              Container(
                padding: const EdgeInsets.all(AppDimensions.paddingL),
                decoration: BoxDecoration(
                  color: AppColors.surfaceElevated,
                  borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                  border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
                ),
                child: Center(
                  child: Text(tr.dashboard.noWorkoutsYet, style: const TextStyle(color: AppColors.textSecondary)),
                ),
              )
            else
              ...state.muscleRecovery.values.map((info) {
                final isReady = info.status == 'recovered';
                final isRecovering = info.status == 'recovering';
                final isSelected = info.muscle == _selectedMuscle;
                final statusColor = isReady ? AppColors.secondary : (isRecovering ? AppColors.warning : AppColors.primary);
                final statusLabel = isReady
                    ? tr.analytics.recoveredStatus
                    : (isRecovering ? tr.analytics.recoveringStatus : tr.analytics.fatiguedStatus);
                final zoneLabel = InteractiveBodyMap.formatVolumeZoneLabel(info.volumeZone, tr);
                final zoneColor = InteractiveBodyMap.resolveVolumeZoneColor(info.volumeZone);

                return GestureDetector(
                  onTap: () {
                    setState(() {
                      _selectedMuscle = info.muscle;
                    });
                  },
                  child: Container(
                    margin: const EdgeInsets.only(bottom: AppDimensions.paddingS),
                    padding: const EdgeInsets.all(AppDimensions.paddingM),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceElevated,
                      borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                      border: Border.all(
                        color: isSelected
                            ? AppColors.primary
                            : (isReady ? AppColors.secondary.withValues(alpha: AppColors.opacityLow) : AppColors.border),
                        width: (isSelected || isReady) ? AppDimensions.borderThick : AppDimensions.borderDefault,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Expanded(
                              child: Row(
                                children: [
                                  Flexible(
                                    child: Text(
                                      tr.translateMuscle(info.muscle),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        fontSize: AppDimensions.fontM,
                                        fontWeight: FontWeight.w900,
                                        color: AppColors.textPrimary,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: AppDimensions.paddingXS),
                                  Flexible(
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingXS, vertical: AppDimensions.paddingXXS),
                                      decoration: BoxDecoration(
                                        color: zoneColor.withValues(alpha: AppColors.opacityLow),
                                        borderRadius: BorderRadius.circular(AppDimensions.radiusBadge),
                                      ),
                                      child: Text(
                                        zoneLabel,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w800, color: zoneColor),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: AppDimensions.paddingXS),
                            Flexible(
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    width: AppDimensions.dotSize,
                                    height: AppDimensions.dotSize,
                                    decoration: BoxDecoration(shape: BoxShape.circle, color: statusColor),
                                  ),
                                  const SizedBox(width: AppDimensions.paddingXS),
                                  Flexible(
                                    child: Text(
                                      '${(info.recoveryPercentage * 100).toInt()}% $statusLabel',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        fontSize: AppDimensions.fontXS,
                                        fontWeight: FontWeight.w900,
                                        letterSpacing: 0.5,
                                        color: statusColor,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: AppDimensions.paddingS),
                        _buildSegmentedBar(info.recoveryPercentage, statusColor),
                        const SizedBox(height: AppDimensions.paddingS),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Expanded(
                              child: Text(
                                tr.analytics.setsMevSummary(sets: info.weeklySets, mavMax: info.mavMax, mev: info.mev),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: AppDimensions.fontXS, color: AppColors.textSecondary, fontWeight: FontWeight.w500),
                              ),
                            ),
                            const SizedBox(width: AppDimensions.paddingS),
                            Flexible(
                              child: Text(
                                '${info.weeklyVolume.toStringAsFixed(0)} kg',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontSize: AppDimensions.fontXXS,
                                  fontWeight: FontWeight.w700,
                                  color: isReady ? AppColors.textSecondary : AppColors.warning,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              }),

            const SizedBox(height: AppDimensions.paddingL),

            // Personal Records (Estimated 1RM)
            Text(
              tr.analytics.estimated1rmSectionTitle,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: AppDimensions.fontL, fontWeight: FontWeight.w900, letterSpacing: 0.2, color: AppColors.textPrimary),
            ),
            const SizedBox(height: AppDimensions.paddingS),

            if (state.personalRecords.isEmpty)
              Container(
                padding: const EdgeInsets.all(AppDimensions.paddingL),
                decoration: BoxDecoration(
                  color: AppColors.surfaceElevated,
                  borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                  border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
                ),
                child: Center(
                  child: Text(tr.analytics.noPrsYet, style: const TextStyle(color: AppColors.textSecondary)),
                ),
              )
            else
              ...state.personalRecords.map((pr) {
                return Container(
                  margin: const EdgeInsets.only(bottom: AppDimensions.paddingS),
                  padding: const EdgeInsets.all(AppDimensions.paddingM),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceElevated,
                    borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                    border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              pr.exerciseName,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: AppDimensions.fontM, fontWeight: FontWeight.w900, color: AppColors.textPrimary),
                            ),
                            const SizedBox(height: AppDimensions.paddingXXS),
                            Text(
                              tr.analytics.bestSetSubtitle(weight: pr.bestWeight, reps: pr.bestReps),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: AppDimensions.fontS, color: AppColors.textSecondary, fontWeight: FontWeight.w500),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: AppDimensions.paddingS),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            '${pr.estimated1RM.toStringAsFixed(1)} kg',
                            style: const TextStyle(fontSize: AppDimensions.fontXL, fontWeight: FontWeight.w900, color: AppColors.primary),
                          ),
                          const Text(
                            'EST. 1RM',
                            style: TextStyle(
                              fontSize: AppDimensions.fontXXS,
                              color: AppColors.textMuted,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }

  static Widget _buildSegmentedBar(double percentage, Color color) {
    const int totalSegments = 4;
    final int activeSegments = percentage <= 0 ? 0 : (percentage * totalSegments).clamp(1.0, totalSegments.toDouble()).round();

    return Row(
      children: List.generate(totalSegments, (index) {
        final isActive = index < activeSegments;
        return Expanded(
          child: Container(
            height: AppDimensions.paddingS,
            margin: EdgeInsets.only(right: index < totalSegments - 1 ? AppDimensions.paddingXS : 0),
            decoration: BoxDecoration(
              color: isActive ? color : AppColors.surface,
              borderRadius: BorderRadius.circular(AppDimensions.radiusBadge),
              border: Border.all(color: isActive ? color : AppColors.borderSubtle, width: AppDimensions.borderThin),
            ),
          ),
        );
      }),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final FaIconData icon;
  final Color iconColor;
  final String title;
  final String value;
  final String subtitle;

  const _SummaryCard({required this.icon, required this.iconColor, required this.title, required this.value, required this.subtitle});

  @override
  Widget build(BuildContext context) {
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
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(AppDimensions.paddingXS),
                decoration: BoxDecoration(
                  color: iconColor.withValues(alpha: AppColors.opacityLow),
                  borderRadius: BorderRadius.circular(AppDimensions.radiusBadge),
                ),
                child: FaIcon(icon, size: AppDimensions.iconS, color: iconColor),
              ),
              const SizedBox(width: AppDimensions.paddingS),
              Expanded(
                child: Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: AppDimensions.fontS, color: AppColors.textSecondary, fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingS),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: AppDimensions.fontXXL, fontWeight: FontWeight.w900, color: AppColors.textPrimary),
          ),
          Text(
            subtitle,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: AppDimensions.fontXXS, color: AppColors.textMuted, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}
