// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/viewmodels/active_workout_viewmodel.dart';
import 'package:comunityfitness/viewmodels/ai_coach_viewmodel.dart';
import 'package:comunityfitness/viewmodels/dashboard_viewmodel.dart';
import 'package:comunityfitness/viewmodels/exercise_catalog_viewmodel.dart';
import 'package:comunityfitness/views/active_workout_screen.dart';
import 'package:comunityfitness/views/ai_coach_view.dart';
import 'package:comunityfitness/views/data_management_screen.dart';
import 'package:comunityfitness/views/exercise_catalog_screen.dart';
import 'package:comunityfitness/views/language_selector_sheet.dart';
import 'package:comunityfitness/views/muscle_analytics_screen.dart';
import 'package:comunityfitness/views/routine_list_screen.dart';
import 'package:comunityfitness/views/widgets/ai_coach_avatar.dart';
import 'package:comunityfitness/views/widgets/workout_anatomical_summary_sheet.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  Future<bool> _confirmOrDeleteSession(BuildContext context, Translations tr, WorkoutSession session) async {
    if (session.steps.isEmpty) {
      return true;
    }
    final sessionTitle = session.routineTitle ?? tr.dashboard.workoutSession;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        key: const Key('confirm_delete_session_dialog'),
        backgroundColor: AppColors.surfaceElevated,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
          side: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
        ),
        title: Row(
          children: [
            const FaIcon(FontAwesomeIcons.triangleExclamation, size: AppDimensions.iconM, color: AppColors.error),
            const SizedBox(width: AppDimensions.paddingS),
            Expanded(
              child: Text(
                tr.dashboard.deleteSessionConfirmTitle,
                style: const TextStyle(fontSize: AppDimensions.fontL, fontWeight: FontWeight.w900, color: AppColors.textPrimary),
              ),
            ),
          ],
        ),
        content: Text(
          tr.dashboard.deleteSessionConfirmMessage(title: sessionTitle),
          style: const TextStyle(fontSize: AppDimensions.fontS, color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            key: const Key('cancel_delete_session_button'),
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: Text(
              tr.common.cancel,
              style: const TextStyle(fontSize: AppDimensions.fontS, fontWeight: FontWeight.bold, color: AppColors.textSecondary),
            ),
          ),
          ElevatedButton.icon(
            key: const Key('confirm_delete_session_button'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.error,
              foregroundColor: AppColors.textPrimary,
              elevation: 0,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusS)),
            ),
            icon: const FaIcon(FontAwesomeIcons.trashCan, size: AppDimensions.iconXS),
            label: Text(
              tr.dashboard.deleteSessionConfirmButton,
              style: const TextStyle(fontSize: AppDimensions.fontS, fontWeight: FontWeight.w900),
            ),
            onPressed: () => Navigator.of(dialogContext).pop(true),
          ),
        ],
      ),
    );
    return confirmed ?? false;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tr = TranslationProvider.of(context).translations;
    final state = ref.watch(dashboardViewModelProvider);
    final activeVm = ref.read(activeWorkoutViewModelProvider.notifier);
    final catalogState = ref.watch(exerciseCatalogViewModelProvider);

    final exerciseMap = {for (final e in catalogState.allExercises) e.id: e};

    final recommended = state.recommendedRoutine;
    final totalPlannedSets = recommended != null ? recommended.steps.fold<int>(0, (sum, step) => sum + step.sets) : 0;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleSpacing: AppDimensions.paddingM,
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const FaIcon(FontAwesomeIcons.bolt, color: AppColors.primary, size: AppDimensions.iconS),
            const SizedBox(width: AppDimensions.paddingXS),
            Flexible(
              child: Text(
                tr.common.appName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: AppDimensions.fontL, fontWeight: FontWeight.w900, letterSpacing: 0.4, color: AppColors.textPrimary),
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            key: const Key('dashboard_language_button'),
            visualDensity: VisualDensity.compact,
            icon: const FaIcon(FontAwesomeIcons.globe, size: AppDimensions.iconM, color: AppColors.secondary),
            tooltip: tr.dashboard.languageTooltip,
            onPressed: () {
              LanguageSelectorSheet.show(
                context,
                onLocaleChanged: (_) {
                  ref.read(aiCoachViewModelProvider.notifier).refreshLocale();
                },
              );
            },
          ),
          Padding(
            padding: const EdgeInsets.only(right: AppDimensions.paddingXS),
            child: IconButton(
              key: const Key('dashboard_ai_coach_button'),
              visualDensity: VisualDensity.compact,
              icon: const AiCoachAvatar(key: Key('dashboard_ai_coach_avatar'), size: AppDimensions.iconXXL),
              tooltip: tr.dashboard.aiCoachTooltip,
              onPressed: () {
                Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const AiCoachView()));
              },
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppDimensions.paddingM),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // High-Impact Athletic Training Hero Card
            Container(
              padding: const EdgeInsets.all(AppDimensions.paddingL),
              decoration: BoxDecoration(
                color: AppColors.surfaceElevated,
                borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Status Header Row
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Flexible(
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXXS),
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
                              const FaIcon(FontAwesomeIcons.fire, size: AppDimensions.iconXS, color: AppColors.primary),
                              const SizedBox(width: AppDimensions.paddingXS),
                              Flexible(
                                child: Text(
                                  tr.dashboard.readyToTrain,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    fontSize: AppDimensions.fontXXS,
                                    fontWeight: FontWeight.w900,
                                    letterSpacing: 0.8,
                                    color: AppColors.primary,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: AppDimensions.paddingS),
                      Flexible(
                        child: Text(
                          tr.dashboard.workoutsThisWeek(count: state.weeklyWorkouts),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          textAlign: TextAlign.end,
                          style: const TextStyle(fontSize: AppDimensions.fontXS, color: AppColors.textSecondary, fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppDimensions.paddingM),

                  // Hero Routine Title
                  Text(
                    recommended != null ? recommended.title : tr.dashboard.freestyleTraining,
                    style: const TextStyle(
                      fontSize: AppDimensions.fontXXL,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.3,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: AppDimensions.paddingXS),
                  Text(
                    recommended != null ? tr.dashboard.exercisesPlanned(count: recommended.steps.length) : tr.dashboard.buildOnTheFly,
                    style: const TextStyle(fontSize: AppDimensions.fontM, color: AppColors.textSecondary),
                  ),

                  // Athletic Planned Stats Strip
                  if (recommended != null) ...[
                    const SizedBox(height: AppDimensions.paddingL),
                    Container(
                      padding: const EdgeInsets.all(AppDimensions.paddingM),
                      decoration: BoxDecoration(
                        color: AppColors.surface,
                        borderRadius: BorderRadius.circular(AppDimensions.radiusS),
                        border: Border.all(color: AppColors.borderSubtle, width: AppDimensions.borderThin),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          Expanded(
                            child: _HeroMetricCell(label: tr.dashboard.totalSets, value: '$totalPlannedSets'),
                          ),
                          Container(height: AppDimensions.paddingL, width: AppDimensions.borderDefault, color: AppColors.border),
                          Expanded(
                            child: _HeroMetricCell(label: tr.dashboard.movements, value: '${recommended.steps.length}'),
                          ),
                          Container(height: AppDimensions.paddingL, width: AppDimensions.borderDefault, color: AppColors.border),
                          Expanded(
                            child: _HeroMetricCell(label: tr.dashboard.targetIntensity, value: 'RPE 8-9'),
                          ),
                        ],
                      ),
                    ),
                  ],

                  const SizedBox(height: AppDimensions.paddingL),

                  // High-Contrast Quick Workout Action Buttons
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.primary,
                            foregroundColor: AppColors.background,
                            padding: const EdgeInsets.symmetric(vertical: AppDimensions.paddingM),
                            elevation: 0,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
                          ),
                          icon: const FaIcon(FontAwesomeIcons.play, size: AppDimensions.iconS),
                          label: Text(
                            recommended != null ? tr.dashboard.startRoutine : tr.dashboard.startFreestyle,
                            style: const TextStyle(fontSize: AppDimensions.fontM, fontWeight: FontWeight.w900, letterSpacing: 0.5),
                          ),
                          onPressed: () {
                            if (recommended != null) {
                              activeVm.startFromRoutine(recommended, exerciseMap);
                            } else {
                              activeVm.startFreestyle();
                            }
                            Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const ActiveWorkoutScreen()));
                          },
                        ),
                      ),
                      const SizedBox(width: AppDimensions.paddingS),
                      IconButton(
                        style: IconButton.styleFrom(
                          backgroundColor: AppColors.surface,
                          padding: const EdgeInsets.all(AppDimensions.paddingM),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                            side: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
                          ),
                        ),
                        icon: const FaIcon(FontAwesomeIcons.dumbbell, size: AppDimensions.iconM, color: AppColors.textPrimary),
                        tooltip: tr.dashboard.startFreestyle,
                        onPressed: () {
                          activeVm.startFreestyle();
                          Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const ActiveWorkoutScreen()));
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppDimensions.paddingL),

            // Navigation Feature Grid (4 Pillars)
            Text(
              tr.dashboard.exploreAndManage,
              style: const TextStyle(fontSize: AppDimensions.fontXS, fontWeight: FontWeight.w900, letterSpacing: 1.2, color: AppColors.textMuted),
            ),
            const SizedBox(height: AppDimensions.paddingS),

            GridView.count(
              crossAxisCount: 2,
              crossAxisSpacing: AppDimensions.paddingM,
              mainAxisSpacing: AppDimensions.paddingM,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              children: [
                _FeatureGridTile(
                  title: tr.dashboard.routinesTitle,
                  subtitle: tr.dashboard.routinesSubtitle(count: state.allRoutines.length),
                  icon: FontAwesomeIcons.clipboardList,
                  iconColor: AppColors.primary,
                  onTap: () {
                    Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const RoutineListScreen()));
                  },
                ),
                _FeatureGridTile(
                  title: tr.dashboard.muscleRecoveryTitle,
                  subtitle: tr.dashboard.muscleRecoverySubtitle(count: state.readyMuscles.length),
                  icon: FontAwesomeIcons.heartPulse,
                  iconColor: AppColors.secondary,
                  onTap: () {
                    Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const MuscleAnalyticsScreen()));
                  },
                ),
                _FeatureGridTile(
                  title: tr.dashboard.exerciseCatalogTitle,
                  subtitle: tr.dashboard.exerciseCatalogSubtitle(count: catalogState.allExercises.length),
                  icon: FontAwesomeIcons.bookBookmark,
                  iconColor: AppColors.warning,
                  onTap: () {
                    Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const ExerciseCatalogScreen()));
                  },
                ),
                _FeatureGridTile(
                  title: tr.dashboard.dataMigrationTitle,
                  subtitle: tr.dashboard.dataMigrationSubtitle,
                  icon: FontAwesomeIcons.arrowsRotate,
                  iconColor: AppColors.primary,
                  onTap: () {
                    Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const DataManagementScreen()));
                  },
                ),
              ],
            ),
            const SizedBox(height: AppDimensions.paddingL),

            // Muscle Readiness Overview
            if (state.readyMuscles.isNotEmpty) ...[
              Text(
                tr.dashboard.targetMusclesReady,
                style: const TextStyle(fontSize: AppDimensions.fontXS, fontWeight: FontWeight.w900, letterSpacing: 1.2, color: AppColors.textMuted),
              ),
              const SizedBox(height: AppDimensions.paddingS),
              Wrap(
                spacing: AppDimensions.paddingS,
                runSpacing: AppDimensions.paddingS,
                children: state.readyMuscles.map((muscle) {
                  return Container(
                    padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM, vertical: AppDimensions.paddingS),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceElevated,
                      borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                      border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: AppDimensions.dotSize,
                          height: AppDimensions.dotSize,
                          decoration: const BoxDecoration(shape: BoxShape.circle, color: AppColors.secondary),
                        ),
                        const SizedBox(width: AppDimensions.paddingS),
                        Text(
                          tr.translateMuscle(muscle),
                          style: const TextStyle(fontSize: AppDimensions.fontS, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ],
            const SizedBox(height: AppDimensions.paddingL),

            // Recent Sessions Section
            Text(
              tr.dashboard.recentWorkouts,
              style: const TextStyle(fontSize: AppDimensions.fontXS, fontWeight: FontWeight.w900, letterSpacing: 1.2, color: AppColors.textMuted),
            ),
            const SizedBox(height: AppDimensions.paddingS),

            if (state.recentSessions.isEmpty)
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
              ...state.recentSessions.map((session) {
                final dateStr = '${session.startedAt.day}/${session.startedAt.month}/${session.startedAt.year}';
                final durationMin = session.completedAt != null ? session.completedAt!.difference(session.startedAt).inMinutes : 0;

                return Padding(
                  padding: const EdgeInsets.only(bottom: AppDimensions.paddingS),
                  child: Dismissible(
                    key: Key('dismiss_recent_session_${session.id}'),
                    direction: DismissDirection.endToStart,
                    confirmDismiss: (_) => _confirmOrDeleteSession(context, tr, session),
                    onDismissed: (_) => ref.read(dashboardViewModelProvider.notifier).deleteSession(session.id),
                    background: Container(
                      alignment: Alignment.centerRight,
                      padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingL),
                      decoration: BoxDecoration(
                        color: AppColors.error.withValues(alpha: AppColors.opacityLow),
                        borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                        border: Border.all(
                          color: AppColors.error.withValues(alpha: AppColors.opacityMedium),
                          width: AppDimensions.borderDefault,
                        ),
                      ),
                      child: const FaIcon(FontAwesomeIcons.trashCan, size: AppDimensions.iconM, color: AppColors.error),
                    ),
                    child: InkWell(
                      key: Key('recent_session_card_${session.id}'),
                      borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                      onTap: () {
                        showModalBottomSheet<void>(
                          context: context,
                          isScrollControlled: true,
                          backgroundColor: AppColors.background,
                          builder: (_) => WorkoutAnatomicalSummarySheet.fromSession(session: session, exercisesById: exerciseMap),
                        );
                      },
                      child: Container(
                        padding: const EdgeInsets.all(AppDimensions.paddingM),
                        decoration: BoxDecoration(
                          color: AppColors.surfaceElevated,
                          borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                          border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
                        ),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(AppDimensions.paddingM),
                              decoration: BoxDecoration(
                                color: AppColors.surface,
                                borderRadius: BorderRadius.circular(AppDimensions.radiusS),
                                border: Border.all(color: AppColors.borderSubtle, width: AppDimensions.borderThin),
                              ),
                              child: const FaIcon(FontAwesomeIcons.dumbbell, size: AppDimensions.iconM, color: AppColors.primary),
                            ),
                            const SizedBox(width: AppDimensions.paddingM),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    session.routineTitle ?? tr.dashboard.workoutSession,
                                    style: const TextStyle(fontSize: AppDimensions.fontM, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                                  ),
                                  const SizedBox(height: AppDimensions.paddingXXS),
                                  Text(
                                    '$dateStr · ${tr.dashboard.exercisesCount(count: session.steps.length)} ${durationMin > 0 ? '· ${durationMin}m' : ''}',
                                    style: const TextStyle(fontSize: AppDimensions.fontXS, color: AppColors.textSecondary),
                                  ),
                                ],
                              ),
                            ),
                            const FaIcon(FontAwesomeIcons.check, size: AppDimensions.iconS, color: AppColors.primary),
                            const SizedBox(width: AppDimensions.paddingXS),
                            IconButton(
                              key: Key('delete_recent_session_${session.id}'),
                              visualDensity: VisualDensity.compact,
                              icon: const FaIcon(FontAwesomeIcons.trashCan, size: AppDimensions.iconS, color: AppColors.textMuted),
                              tooltip: tr.dashboard.deleteSessionTooltip,
                              onPressed: () async {
                                final confirmed = await _confirmOrDeleteSession(context, tr, session);
                                if (confirmed) {
                                  await ref.read(dashboardViewModelProvider.notifier).deleteSession(session.id);
                                }
                              },
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }
}

class _HeroMetricCell extends StatelessWidget {
  final String label;
  final String value;

  const _HeroMetricCell({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: const TextStyle(fontSize: AppDimensions.fontL, fontWeight: FontWeight.w900, color: AppColors.textPrimary),
        ),
        const SizedBox(height: AppDimensions.paddingXXS),
        Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: AppColors.textMuted),
        ),
      ],
    );
  }
}

class _FeatureGridTile extends StatelessWidget {
  final String title;
  final String subtitle;
  final FaIconData icon;
  final Color iconColor;
  final VoidCallback onTap;

  const _FeatureGridTile({required this.title, required this.subtitle, required this.icon, required this.iconColor, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
      child: Container(
        padding: const EdgeInsets.all(AppDimensions.paddingM),
        decoration: BoxDecoration(
          color: AppColors.surfaceElevated,
          borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
          border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Container(
              padding: const EdgeInsets.all(AppDimensions.paddingS),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(AppDimensions.radiusS),
                border: Border.all(color: AppColors.borderSubtle, width: AppDimensions.borderThin),
              ),
              child: FaIcon(icon, size: AppDimensions.iconM, color: iconColor),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: AppDimensions.fontM, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                ),
                const SizedBox(height: AppDimensions.paddingXXS),
                Text(
                  subtitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: AppDimensions.fontXXS, color: AppColors.textSecondary),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
