// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:cue/cue.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// 🌎 Project imports:
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/viewmodels/routine_list_viewmodel.dart';
import 'package:comunityfitness/viewmodels/sync_viewmodel.dart';
import 'package:comunityfitness/views/exercise_catalog_screen.dart';
import 'package:comunityfitness/views/routine_editor_screen.dart';
import 'package:comunityfitness/views/widgets/app_back_button.dart';

class RoutineListScreen extends ConsumerWidget {
  const RoutineListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final routinesAsync = ref.watch(routineListViewModelProvider);
    final syncState = ref.watch(syncViewModelProvider);
    final syncNotifier = ref.read(syncViewModelProvider.notifier);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: CustomScrollView(
        slivers: [
          // M3 Expressive Collapsing Header
          SliverAppBar(
            automaticallyImplyLeading: false,
            leading: AppBackButton.maybeLeading(context),
            expandedHeight: AppDimensions.appBarExpandedHeight,
            floating: false,
            pinned: true,
            elevation: 0,
            scrolledUnderElevation: 0,
            backgroundColor: AppColors.background,
            flexibleSpace: FlexibleSpaceBar(
              title: const Text(
                'CommunityFitness',
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: AppDimensions.fontXL, letterSpacing: 1.2, color: AppColors.textPrimary),
              ),
              centerTitle: false,
              titlePadding: const EdgeInsets.only(left: AppDimensions.paddingM, bottom: AppDimensions.paddingM),
              background: Container(color: AppColors.background),
            ),
            actions: [
              // Online / Offline Indicator & Sync Action
              Padding(
                padding: const EdgeInsets.only(right: AppDimensions.paddingS),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      decoration: BoxDecoration(
                        color: AppColors.surfaceElevated,
                        borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                        border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXXS),
                      child: Row(
                        children: [
                          FaIcon(
                            syncState.isOnline ? FontAwesomeIcons.wifi : FontAwesomeIcons.ban,
                            color: syncState.isOnline ? AppColors.success : AppColors.error,
                            size: AppDimensions.iconXS,
                          ),
                          const SizedBox(width: AppDimensions.paddingXS),
                          Text(
                            syncState.isOnline ? 'Online' : 'Offline',
                            style: TextStyle(
                              fontSize: AppDimensions.fontXS,
                              fontWeight: FontWeight.bold,
                              color: syncState.isOnline ? AppColors.success : AppColors.error,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: AppDimensions.paddingS),
                    IconButton(
                      onPressed: syncState.isSyncing ? null : () => syncNotifier.sync(),
                      icon: syncState.isSyncing
                          ? const SizedBox(
                              width: AppDimensions.spinnerSize,
                              height: AppDimensions.spinnerSize,
                              child: CircularProgressIndicator(strokeWidth: AppDimensions.strokeWidthThin, color: AppColors.primary),
                            )
                          : const FaIcon(FontAwesomeIcons.rotate, size: AppDimensions.iconM, color: AppColors.textPrimary),
                      tooltip: 'Sync Now',
                    ),
                  ],
                ),
              ),
            ],
          ),

          // High-Performance Athletic Training Briefing Hero
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(AppDimensions.paddingM),
              key: const Key('welcome_card'),
              child: Cue.onMount(
                motion: const CueMotion.easeOutBack(AppDimensions.animDurationVerySlow),
                child: Actor(
                  acts: const [Act.fadeIn(), Act.translateY(from: 0.15)],
                  child: Container(
                    decoration: BoxDecoration(
                      color: AppColors.surfaceElevated,
                      borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                      border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
                    ),
                    padding: const EdgeInsets.all(AppDimensions.paddingL),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXXS),
                          decoration: BoxDecoration(
                            color: AppColors.primary.withValues(alpha: AppColors.opacityLow),
                            borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                            border: Border.all(
                              color: AppColors.primary.withValues(alpha: AppColors.opacityMedium),
                              width: AppDimensions.borderThin,
                            ),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              FaIcon(FontAwesomeIcons.bolt, size: AppDimensions.iconXS, color: AppColors.primary),
                              SizedBox(width: AppDimensions.paddingXS),
                              Text(
                                'TRAINING DISPATCH',
                                style: TextStyle(
                                  fontSize: AppDimensions.fontXXS,
                                  fontWeight: FontWeight.w900,
                                  letterSpacing: 0.8,
                                  color: AppColors.primary,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: AppDimensions.paddingM),
                        const Text(
                          'Welcome back, Athlete!',
                          style: TextStyle(
                            fontSize: AppDimensions.fontXXL,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 0.3,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        const SizedBox(height: AppDimensions.paddingS),
                        const Text(
                          'Ready to crush your limits today? Select a routine or create a new one to get started.',
                          style: TextStyle(fontSize: AppDimensions.fontM, color: AppColors.textSecondary, height: 1.4),
                        ),
                        const SizedBox(height: AppDimensions.paddingL),
                        ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.primary,
                            foregroundColor: AppColors.background,
                            elevation: 0,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
                          ),
                          onPressed: () {
                            Navigator.push(context, MaterialPageRoute<void>(builder: (context) => const ExerciseCatalogScreen()));
                          },
                          icon: const FaIcon(FontAwesomeIcons.magnifyingGlass, size: AppDimensions.iconSM),
                          label: const Text('Browse Exercises', style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5)),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),

          // Routines List Header
          const SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: AppDimensions.paddingM, vertical: AppDimensions.paddingS),
              child: Text(
                'YOUR ROUTINES',
                style: TextStyle(fontSize: AppDimensions.fontXS, fontWeight: FontWeight.w900, letterSpacing: 1.2, color: AppColors.textMuted),
              ),
            ),
          ),

          // Routines Stream Content
          routinesAsync.when(
            data: (routines) {
              if (routines.isEmpty) {
                return const SliverFillRemaining(
                  hasScrollBody: false,
                  child: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        FaIcon(FontAwesomeIcons.dumbbell, size: AppDimensions.iconHuge, color: AppColors.border),
                        SizedBox(height: AppDimensions.paddingM),
                        Text(
                          'No routines found.\nTap the + button to create one!',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: AppColors.textSecondary),
                        ),
                      ],
                    ),
                  ),
                );
              }

              return SliverList(
                delegate: SliverChildBuilderDelegate((context, index) {
                  final routine = routines[index];
                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM, vertical: AppDimensions.paddingXS),
                    child: Dismissible(
                      key: Key('routine_${routine.id}'),
                      direction: DismissDirection.endToStart,
                      background: Container(
                        alignment: Alignment.centerRight,
                        padding: const EdgeInsets.only(right: AppDimensions.paddingM),
                        decoration: BoxDecoration(color: AppColors.error, borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
                        child: const FaIcon(FontAwesomeIcons.trash, color: AppColors.textPrimary),
                      ),
                      confirmDismiss: (direction) async {
                        return true;
                      },
                      onDismissed: (direction) async {
                        await ref.read(routineListViewModelProvider.notifier).deleteRoutine(routine.id);
                        if (context.mounted) {
                          ScaffoldMessenger.of(
                            context,
                          ).showSnackBar(SnackBar(content: Text('Routine "${routine.title}" deleted'), backgroundColor: AppColors.surfaceElevated));
                        }
                      },
                      child: Cue.onMount(
                        motion: const CueMotion.easeOutBack(AppDimensions.animDurationSlow),
                        child: Actor(
                          acts: const [Act.fadeIn(), Act.translateY(from: 0.1)],
                          child: Card(
                            margin: EdgeInsets.zero,
                            color: AppColors.surfaceElevated,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                              side: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
                            ),
                            child: ListTile(
                              contentPadding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM, vertical: AppDimensions.paddingS),
                              title: Text(
                                routine.title,
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: AppDimensions.fontL, color: AppColors.textPrimary),
                              ),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const SizedBox(height: AppDimensions.paddingXS),
                                  Text(
                                    routine.description.isNotEmpty ? routine.description : 'No description',
                                    style: const TextStyle(color: AppColors.textSecondary, fontSize: AppDimensions.fontM),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  const SizedBox(height: AppDimensions.paddingS),
                                  Row(
                                    children: [
                                      Container(
                                        decoration: BoxDecoration(
                                          color: AppColors.surface,
                                          borderRadius: BorderRadius.circular(AppDimensions.radiusBadge),
                                          border: Border.all(color: AppColors.borderSubtle, width: AppDimensions.borderThin),
                                        ),
                                        padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXXS),
                                        child: Row(
                                          children: [
                                            const FaIcon(FontAwesomeIcons.listCheck, size: AppDimensions.iconXS, color: AppColors.secondary),
                                            const SizedBox(width: AppDimensions.paddingXS),
                                            Text(
                                              '${routine.steps.length} steps',
                                              style: const TextStyle(
                                                fontSize: AppDimensions.fontXXS,
                                                color: AppColors.textPrimary,
                                                fontWeight: FontWeight.bold,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                      const SizedBox(width: AppDimensions.paddingS),
                                      Container(
                                        decoration: BoxDecoration(
                                          color: routine.synced
                                              ? AppColors.success.withValues(alpha: AppColors.opacityLow)
                                              : AppColors.warning.withValues(alpha: AppColors.opacityLow),
                                          borderRadius: BorderRadius.circular(AppDimensions.radiusBadge),
                                          border: Border.all(
                                            color: routine.synced ? AppColors.success : AppColors.warning,
                                            width: AppDimensions.borderThin,
                                          ),
                                        ),
                                        padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXXS),
                                        child: Row(
                                          children: [
                                            FaIcon(
                                              routine.synced ? FontAwesomeIcons.circleCheck : FontAwesomeIcons.cloudArrowUp,
                                              size: AppDimensions.iconXS,
                                              color: routine.synced ? AppColors.success : AppColors.warning,
                                            ),
                                            const SizedBox(width: AppDimensions.paddingXS),
                                            Text(
                                              routine.synced ? 'Synced' : 'Unsynced',
                                              style: TextStyle(
                                                fontSize: AppDimensions.fontXXS,
                                                color: routine.synced ? AppColors.success : AppColors.warning,
                                                fontWeight: FontWeight.bold,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                              trailing: IconButton(
                                icon: const FaIcon(FontAwesomeIcons.penToSquare, color: AppColors.primary, size: AppDimensions.iconM),
                                onPressed: () {
                                  Navigator.push(context, MaterialPageRoute<void>(builder: (context) => RoutineEditorScreen(routineId: routine.id)));
                                },
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }, childCount: routines.length),
              );
            },
            loading: () => const SliverFillRemaining(
              child: Center(child: CircularProgressIndicator(color: AppColors.primary)),
            ),
            error: (err, stack) => SliverFillRemaining(
              child: Center(
                child: Text('Error: $err', style: const TextStyle(color: AppColors.error)),
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.background,
        elevation: AppDimensions.cardElevation,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
        onPressed: () {
          Navigator.push(context, MaterialPageRoute<void>(builder: (context) => const RoutineEditorScreen()));
        },
        child: const FaIcon(FontAwesomeIcons.plus),
      ),
    );
  }
}
