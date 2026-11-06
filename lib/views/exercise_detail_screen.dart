// 🎯 Dart imports:
import 'dart:ui';

// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/utils/exercise_animation_asset.dart';
import 'package:comunityfitness/views/ai_coach_view.dart';
import 'package:comunityfitness/views/widgets/exercise_animation.dart';

class ExerciseDetailScreen extends StatelessWidget {
  final Exercise exercise;

  const ExerciseDetailScreen({super.key, required this.exercise});

  static void show(BuildContext context, Exercise exercise) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.transparent,
      elevation: 0,
      builder: (context) => ExerciseDetailScreen(exercise: exercise),
    );
  }

  Widget _buildGifPlayer() {
    return Image.network(
      exercise.animationPath,
      fit: BoxFit.contain,
      loadingBuilder: (context, child, loadingProgress) {
        if (loadingProgress == null) {
          return child;
        }
        return const Center(child: CircularProgressIndicator(color: AppColors.primary));
      },
      errorBuilder: (context, error, stackTrace) {
        return const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              FaIcon(FontAwesomeIcons.circleExclamation, color: AppColors.warning, size: AppDimensions.iconXL),
              SizedBox(height: AppDimensions.paddingS),
              Text(
                'Demonstration GIF unavailable',
                style: TextStyle(color: AppColors.textSecondary, fontSize: AppDimensions.fontS),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildDemonstration() {
    if (exercise.animationPath.isEmpty) {
      return const ExerciseAnimationFallback(message: 'No animation path provided');
    }
    if (exercise.animationType == 'gif') {
      return _buildGifPlayer();
    }
    final riveAsset = exerciseRiveAsset(exercise);
    return riveAsset != null ? ExerciseAnimation(assetPath: riveAsset) : const ExerciseAnimationFallback();
  }

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(AppDimensions.radiusBottomSheet)),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: AppDimensions.shadowBlurL, sigmaY: AppDimensions.shadowBlurL),
        child: Container(
          padding: const EdgeInsets.all(AppDimensions.paddingL),
          decoration: BoxDecoration(
            color: AppColors.surfaceElevated.withValues(alpha: AppColors.opacityHigh),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(AppDimensions.radiusBottomSheet)),
            border: const Border(
              top: BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Grab handle
              Center(
                child: Container(
                  width: AppDimensions.dragHandleWidth,
                  height: AppDimensions.dragHandleHeight,
                  decoration: BoxDecoration(
                    color: AppColors.textMuted.withValues(alpha: AppColors.opacityMedium),
                    borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                  ),
                ),
              ),
              const SizedBox(height: AppDimensions.paddingL),

              // Title Name
              Text(
                exercise.name,
                style: const TextStyle(
                  fontSize: AppDimensions.fontXXL,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 0.3,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: AppDimensions.paddingS),

              // Tags
              Row(
                children: [
                  Container(
                    decoration: BoxDecoration(
                      color: AppColors.primary.withValues(alpha: AppColors.opacityLow),
                      borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                      border: Border.all(
                        color: AppColors.primary.withValues(alpha: AppColors.opacityMedium),
                        width: AppDimensions.borderThin,
                      ),
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM, vertical: AppDimensions.paddingXXS),
                    child: Text(
                      exercise.primaryMuscleGroup,
                      style: const TextStyle(fontSize: AppDimensions.fontS, color: AppColors.primary, fontWeight: FontWeight.bold),
                    ),
                  ),
                  const SizedBox(width: AppDimensions.paddingS),
                  Container(
                    decoration: BoxDecoration(
                      color: AppColors.secondary.withValues(alpha: AppColors.opacityLow),
                      borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                      border: Border.all(
                        color: AppColors.secondary.withValues(alpha: AppColors.opacityMedium),
                        width: AppDimensions.borderThin,
                      ),
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM, vertical: AppDimensions.paddingXXS),
                    child: Text(
                      exercise.equipment,
                      style: const TextStyle(fontSize: AppDimensions.fontS, color: AppColors.secondary, fontWeight: FontWeight.bold),
                    ),
                  ),
                  if (exercise.animationType == 'rive' || exercise.animationType == 'movekit') ...[
                    const SizedBox(width: AppDimensions.paddingS),
                    Container(
                      decoration: BoxDecoration(
                        color: AppColors.secondary.withValues(alpha: AppColors.opacityLow),
                        borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
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
                          Text(
                            'HD 60FPS',
                            style: TextStyle(fontSize: AppDimensions.fontS, color: AppColors.secondary, fontWeight: FontWeight.w900),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: AppDimensions.paddingL),

              // Instructions Header
              const Text(
                'Instructions',
                style: TextStyle(fontSize: AppDimensions.fontL, fontWeight: FontWeight.w900, letterSpacing: 0.3, color: AppColors.textPrimary),
              ),
              const SizedBox(height: AppDimensions.paddingS),
              Text(
                exercise.description,
                style: const TextStyle(fontSize: AppDimensions.fontM, color: AppColors.textSecondary, height: 1.5),
              ),
              const SizedBox(height: AppDimensions.paddingL),

              // Demonstration Player
              const Text(
                'Demonstration',
                style: TextStyle(fontSize: AppDimensions.fontL, fontWeight: FontWeight.w900, letterSpacing: 0.3, color: AppColors.textPrimary),
              ),
              const SizedBox(height: AppDimensions.paddingS),
              ClipRRect(
                borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                child: Container(
                  height: AppDimensions.animationPlayerHeight,
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                    border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
                  ),
                  child: RepaintBoundary(child: _buildDemonstration()),
                ),
              ),
              const SizedBox(height: AppDimensions.paddingM),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  key: const Key('ai_alternative_detail_button'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: AppColors.background,
                    padding: const EdgeInsets.symmetric(vertical: AppDimensions.paddingM),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
                  ),
                  icon: const FaIcon(FontAwesomeIcons.wandMagicSparkles, size: AppDimensions.iconS),
                  label: const Text(
                    'AI Alternative (Home / No Weights)',
                    style: TextStyle(fontSize: AppDimensions.fontM, fontWeight: FontWeight.w900),
                  ),
                  onPressed: () {
                    Navigator.pop(context);
                    AiCoachView.showAlternativeSheet(context, exercise);
                  },
                ),
              ),
              const SizedBox(height: AppDimensions.paddingL),
            ],
          ),
        ),
      ),
    );
  }
}
