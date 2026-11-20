// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:cue/cue.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/utils/exercise_animation_asset.dart';
import 'package:comunityfitness/viewmodels/exercise_catalog_viewmodel.dart';
import 'package:comunityfitness/views/ai_coach_view.dart';
import 'package:comunityfitness/views/exercise_detail_screen.dart';
import 'package:comunityfitness/views/widgets/ai_coach_avatar.dart';
import 'package:comunityfitness/views/widgets/app_back_button.dart';

class ExerciseCatalogScreen extends ConsumerWidget {
  final bool isSelectionMode;

  const ExerciseCatalogScreen({super.key, this.isSelectionMode = false});

  static FaIconData _getMuscleIcon(String muscleGroup) {
    switch (muscleGroup.toLowerCase()) {
      case 'chest':
        return FontAwesomeIcons.shield;
      case 'back':
        return FontAwesomeIcons.layerGroup;
      case 'legs':
      case 'upper legs':
      case 'lower legs':
      case 'calves':
      case 'glutes':
      case 'hamstrings':
      case 'quads':
        return FontAwesomeIcons.personWalking;
      case 'shoulders':
        return FontAwesomeIcons.arrowsUpDown;
      case 'arms':
      case 'biceps':
      case 'triceps':
        return FontAwesomeIcons.handFist;
      case 'core':
      case 'waist':
      case 'abs':
        return FontAwesomeIcons.fire;
      case 'cardio':
        return FontAwesomeIcons.heartPulse;
      default:
        return FontAwesomeIcons.fire;
    }
  }

  Widget _buildCategoryFallback(Exercise exercise) {
    final icon = _getMuscleIcon(exercise.primaryMuscleGroup);
    final isHd = exercise.animationType == 'rive' || exercise.animationType == 'movekit';
    final accentColor = isHd ? AppColors.secondary : AppColors.primary;

    return ClipRRect(
      borderRadius: BorderRadius.circular(AppDimensions.radiusS),
      child: Container(
        width: AppDimensions.thumbnailSize,
        height: AppDimensions.thumbnailSize,
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppDimensions.radiusS),
          border: Border.all(
            color: accentColor.withValues(alpha: isHd ? AppColors.opacityHigh : AppColors.opacityLow),
            width: isHd ? AppDimensions.borderDefault : AppDimensions.borderThin,
          ),
        ),
        child: Stack(
          alignment: Alignment.center,
          children: [
            Center(
              child: FaIcon(icon, color: accentColor, size: AppDimensions.iconM),
            ),
            if (isHd) _buildHdBadge(),
          ],
        ),
      ),
    );
  }

  static Widget _buildHdBadge() {
    return Positioned(
      top: AppDimensions.paddingXXS,
      right: AppDimensions.paddingXXS,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingXS, vertical: AppDimensions.paddingXXS),
        decoration: BoxDecoration(color: AppColors.secondary, borderRadius: BorderRadius.circular(AppDimensions.radiusBadge)),
        child: const Text(
          'HD',
          style: TextStyle(fontSize: AppDimensions.fontBadge, fontWeight: FontWeight.w900, color: AppColors.background),
        ),
      ),
    );
  }

  /// Pre-rendered Rive thumbnail; falls back to the category placeholder when
  /// no PNG was rendered for this exercise.
  Widget _buildAssetThumbnail(Exercise exercise, String thumbnailAsset) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppDimensions.radiusS),
      child: SizedBox(
        width: AppDimensions.thumbnailSize,
        height: AppDimensions.thumbnailSize,
        child: Image.asset(
          thumbnailAsset,
          fit: BoxFit.cover,
          cacheWidth: AppDimensions.thumbnailCacheSize,
          frameBuilder: (context, child, frame, wasSynchronouslyLoaded) => Stack(fit: StackFit.expand, children: [child, _buildHdBadge()]),
          errorBuilder: (context, error, stackTrace) => _buildCategoryFallback(exercise),
        ),
      ),
    );
  }

  Widget _buildLeadingThumbnail(Exercise exercise) {
    if (exercise.animationType == 'gif' && exercise.animationPath.isNotEmpty && exercise.animationPath.startsWith('http')) {
      final thumbnailUrl = exercise.animationPath.replaceAll('/videos/', '/images/').replaceAll('.gif', '.jpg');
      return ClipRRect(
        borderRadius: BorderRadius.circular(AppDimensions.radiusS),
        child: Container(
          width: AppDimensions.thumbnailSize,
          height: AppDimensions.thumbnailSize,
          color: AppColors.surface,
          child: Image.network(
            thumbnailUrl,
            fit: BoxFit.cover,
            loadingBuilder: (context, child, loadingProgress) {
              if (loadingProgress == null) {
                return child;
              }
              return Center(
                child: SizedBox(
                  width: AppDimensions.spinnerSize,
                  height: AppDimensions.spinnerSize,
                  child: CircularProgressIndicator(
                    strokeWidth: AppDimensions.strokeWidthThin,
                    color: AppColors.primary.withValues(alpha: AppColors.opacityMedium),
                  ),
                ),
              );
            },
            errorBuilder: (context, error, stackTrace) {
              return Image.network(exercise.animationPath, fit: BoxFit.cover, errorBuilder: (ctx, err, st) => _buildCategoryFallback(exercise));
            },
          ),
        ),
      );
    }

    final thumbnailAsset = exerciseThumbnailAsset(exercise);
    if (thumbnailAsset != null) {
      return _buildAssetThumbnail(exercise, thumbnailAsset);
    }

    return _buildCategoryFallback(exercise);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(exerciseCatalogViewModelProvider);
    final notifier = ref.read(exerciseCatalogViewModelProvider.notifier);

    final muscleGroups = ['Chest', 'Legs', 'Back', 'Shoulders', 'Arms', 'Cardio', 'Core'];
    final equipments = ['Bodyweight', 'Barbell', 'Dumbbell', 'Machine', 'Cable'];

    return Scaffold(
      backgroundColor: AppColors.background,
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          // M3 Expressive Collapsing AppBar
          SliverAppBar(
            expandedHeight: AppDimensions.appBarExpandedHeight,
            floating: false,
            pinned: true,
            elevation: 0,
            scrolledUnderElevation: 0,
            backgroundColor: AppColors.background,
            leading: const AppBackButton(),
            actions: [
              Padding(
                padding: const EdgeInsets.only(right: AppDimensions.paddingM),
                child: IconButton(
                  key: const Key('open_ai_coach_header_button'),
                  tooltip: 'ATLAS • AI Personal Trainer',
                  icon: const AiCoachAvatar(key: Key('catalog_ai_coach_avatar'), size: AppDimensions.iconXXL),
                  onPressed: () {
                    Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const AiCoachView()));
                  },
                ),
              ),
            ],
            flexibleSpace: FlexibleSpaceBar(
              title: Text(
                isSelectionMode ? 'Select Exercise' : 'Exercise Catalog',
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: AppDimensions.fontXL, letterSpacing: 0.3, color: AppColors.textPrimary),
              ),
              centerTitle: false,
              titlePadding: const EdgeInsets.only(left: AppDimensions.appBarSelectionLeadingPadding, bottom: AppDimensions.paddingM),
              background: Container(color: AppColors.background),
            ),
          ),

          // Filters and Search Input section
          SliverToBoxAdapter(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // High-Contrast Search Input
                Padding(
                  padding: const EdgeInsets.all(AppDimensions.paddingM),
                  child: Cue.onMount(
                    motion: const CueMotion.easeOutBack(AppDimensions.animDurationFast),
                    child: Actor(
                      acts: const [Act.fadeIn(), Act.translateY(from: 0.05)],
                      child: TextField(
                        key: const Key('exercise_search_field'),
                        onChanged: (val) => notifier.setSearchQuery(val),
                        decoration: InputDecoration(
                          hintText: 'Search movements...',
                          hintStyle: const TextStyle(color: AppColors.textMuted),
                          prefixIcon: const Padding(
                            padding: EdgeInsets.all(AppDimensions.paddingM),
                            child: FaIcon(FontAwesomeIcons.magnifyingGlass, size: AppDimensions.iconM, color: AppColors.textSecondary),
                          ),
                          fillColor: AppColors.surfaceElevated,
                          enabledBorder: OutlineInputBorder(
                            borderSide: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
                            borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderSide: const BorderSide(color: AppColors.primary, width: AppDimensions.borderThick),
                            borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                          ),
                        ),
                        style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ),
                ),

                // Muscle Group Filter Chips Header
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: AppDimensions.paddingM),
                  child: Text(
                    'MUSCLE GROUPS',
                    style: TextStyle(fontSize: AppDimensions.fontXS, fontWeight: FontWeight.w900, letterSpacing: 1.2, color: AppColors.textMuted),
                  ),
                ),
                const SizedBox(height: AppDimensions.paddingXS),

                // Muscle Group Chips Row
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM),
                  child: Row(
                    children: muscleGroups.map((muscle) {
                      final isSelected = state.selectedMuscleGroup?.toLowerCase() == muscle.toLowerCase();
                      return Padding(
                        padding: const EdgeInsets.only(right: AppDimensions.paddingS),
                        child: FilterChip(
                          label: Text(muscle),
                          selected: isSelected,
                          onSelected: (selected) {
                            notifier.selectMuscleGroup(selected ? muscle : null);
                          },
                          backgroundColor: AppColors.surfaceElevated,
                          selectedColor: AppColors.primary.withValues(alpha: AppColors.opacityLow),
                          checkmarkColor: AppColors.primary,
                          labelStyle: TextStyle(
                            color: isSelected ? AppColors.primary : AppColors.textSecondary,
                            fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
                            fontSize: AppDimensions.fontS,
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                            side: BorderSide(
                              color: isSelected ? AppColors.primary : AppColors.border,
                              width: isSelected ? AppDimensions.borderThick : AppDimensions.borderDefault,
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ),
                const SizedBox(height: AppDimensions.paddingM),

                // Equipment Filter Chips Header
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: AppDimensions.paddingM),
                  child: Text(
                    'EQUIPMENT',
                    style: TextStyle(fontSize: AppDimensions.fontXS, fontWeight: FontWeight.w900, letterSpacing: 1.2, color: AppColors.textMuted),
                  ),
                ),
                const SizedBox(height: AppDimensions.paddingXS),

                // Equipment Chips Row
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM),
                  child: Row(
                    children: equipments.map((equipment) {
                      final isSelected = state.selectedEquipment?.toLowerCase() == equipment.toLowerCase();
                      return Padding(
                        padding: const EdgeInsets.only(right: AppDimensions.paddingS),
                        child: FilterChip(
                          label: Text(equipment),
                          selected: isSelected,
                          onSelected: (selected) {
                            notifier.selectEquipment(selected ? equipment : null);
                          },
                          backgroundColor: AppColors.surfaceElevated,
                          selectedColor: AppColors.secondary.withValues(alpha: AppColors.opacityLow),
                          checkmarkColor: AppColors.secondary,
                          labelStyle: TextStyle(
                            color: isSelected ? AppColors.secondary : AppColors.textSecondary,
                            fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
                            fontSize: AppDimensions.fontS,
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                            side: BorderSide(
                              color: isSelected ? AppColors.secondary : AppColors.border,
                              width: isSelected ? AppDimensions.borderThick : AppDimensions.borderDefault,
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ),
                const SizedBox(height: AppDimensions.paddingM),
              ],
            ),
          ),

          // Exercise List Items
          if (state.exercises.isEmpty)
            const SliverFillRemaining(
              hasScrollBody: false,
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    FaIcon(FontAwesomeIcons.folderOpen, size: AppDimensions.iconHuge, color: AppColors.border),
                    SizedBox(height: AppDimensions.paddingM),
                    Text('No exercises match your search/filters.', style: TextStyle(color: AppColors.textSecondary)),
                  ],
                ),
              ),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate((context, index) {
                  final exercise = state.exercises[index];
                  return Cue.onMount(
                    motion: const CueMotion.easeOutBack(AppDimensions.animDurationMedium),
                    child: Actor(
                      acts: const [Act.fadeIn(), Act.translateY(from: 0.08)],
                      child: Card(
                        color: AppColors.surfaceElevated,
                        margin: const EdgeInsets.only(bottom: AppDimensions.paddingS),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                          side: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
                        ),
                        child: ListTile(
                          contentPadding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM, vertical: AppDimensions.paddingS),
                          leading: _buildLeadingThumbnail(exercise),
                          title: Text(
                            exercise.name,
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: AppDimensions.fontM, color: AppColors.textPrimary),
                          ),
                          subtitle: Padding(
                            padding: const EdgeInsets.only(top: AppDimensions.paddingS),
                            child: Wrap(
                              spacing: AppDimensions.paddingS,
                              runSpacing: AppDimensions.paddingXS,
                              children: [
                                Container(
                                  decoration: BoxDecoration(
                                    color: AppColors.primary.withValues(alpha: AppColors.opacityLow),
                                    borderRadius: BorderRadius.circular(AppDimensions.radiusBadge),
                                    border: Border.all(
                                      color: AppColors.primary.withValues(alpha: AppColors.opacityMedium),
                                      width: AppDimensions.borderThin,
                                    ),
                                  ),
                                  padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXXS),
                                  child: Text(
                                    exercise.primaryMuscleGroup,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontSize: AppDimensions.fontXXS, color: AppColors.primary, fontWeight: FontWeight.bold),
                                  ),
                                ),
                                if (exercise.animationType == 'rive' || exercise.animationType == 'movekit')
                                  Container(
                                    decoration: BoxDecoration(
                                      color: AppColors.secondary.withValues(alpha: AppColors.opacityLow),
                                      borderRadius: BorderRadius.circular(AppDimensions.radiusBadge),
                                      border: Border.all(
                                        color: AppColors.secondary.withValues(alpha: AppColors.opacityMedium),
                                        width: AppDimensions.borderThin,
                                      ),
                                    ),
                                    padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXXS),
                                    child: const Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        FaIcon(FontAwesomeIcons.bolt, size: AppDimensions.iconXS, color: AppColors.secondary),
                                        SizedBox(width: AppDimensions.paddingXS),
                                        Flexible(
                                          child: Text(
                                            'HD 60FPS',
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                            style: TextStyle(
                                              fontSize: AppDimensions.fontXXS,
                                              color: AppColors.secondary,
                                              fontWeight: FontWeight.w900,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                              ],
                            ),
                          ),
                          trailing: isSelectionMode
                              ? IconButton(
                                  icon: const FaIcon(FontAwesomeIcons.circlePlus, color: AppColors.primary, size: AppDimensions.iconL),
                                  onPressed: () {
                                    Navigator.pop(context, exercise);
                                  },
                                )
                              : Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    IconButton(
                                      key: Key('ai_alt_button_${exercise.id}'),
                                      tooltip: 'AI Alternative (Home / No Weights)',
                                      icon: const FaIcon(FontAwesomeIcons.wandMagicSparkles, color: AppColors.primary, size: AppDimensions.iconM),
                                      onPressed: () {
                                        AiCoachView.showAlternativeSheet(context, exercise);
                                      },
                                    ),
                                    IconButton(
                                      icon: const FaIcon(FontAwesomeIcons.circleInfo, color: AppColors.textSecondary, size: AppDimensions.iconM),
                                      onPressed: () {
                                        ExerciseDetailScreen.show(context, exercise);
                                      },
                                    ),
                                  ],
                                ),
                          onTap: isSelectionMode
                              ? () {
                                  Navigator.pop(context, exercise);
                                }
                              : () {
                                  ExerciseDetailScreen.show(context, exercise);
                                },
                        ),
                      ),
                    ),
                  );
                }, childCount: state.exercises.length),
              ),
            ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('open_ai_coach_fab'),
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.background,
        icon: const FaIcon(FontAwesomeIcons.headset, size: AppDimensions.iconM),
        label: const Text(
          'ATLAS',
          style: TextStyle(fontSize: AppDimensions.fontS, fontWeight: FontWeight.w900),
        ),
        onPressed: () {
          Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const AiCoachView()));
        },
      ),
    );
  }
}
