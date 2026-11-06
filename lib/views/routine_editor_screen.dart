// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:cue/cue.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/workout_step.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/viewmodels/exercise_catalog_viewmodel.dart';
import 'package:comunityfitness/viewmodels/routine_editor_viewmodel.dart';
import 'package:comunityfitness/views/exercise_catalog_screen.dart';
import 'package:comunityfitness/views/widgets/app_back_button.dart';

class RoutineEditorScreen extends ConsumerStatefulWidget {
  final String? routineId;

  const RoutineEditorScreen({super.key, this.routineId});

  @override
  ConsumerState<RoutineEditorScreen> createState() => _RoutineEditorScreenState();
}

class _RoutineEditorScreenState extends ConsumerState<RoutineEditorScreen> {
  late final TextEditingController _titleController;
  late final TextEditingController _descriptionController;

  @override
  void initState() {
    super.initState();
    final state = ref.read(routineEditorViewModelProvider(widget.routineId));
    _titleController = TextEditingController(text: state.title);
    _descriptionController = TextEditingController(text: state.description);

    _titleController.addListener(() {
      ref.read(routineEditorViewModelProvider(widget.routineId).notifier).setTitle(_titleController.text);
    });

    _descriptionController.addListener(() {
      ref.read(routineEditorViewModelProvider(widget.routineId).notifier).setDescription(_descriptionController.text);
    });
  }

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(routineEditorViewModelProvider(widget.routineId));
    final notifier = ref.read(routineEditorViewModelProvider(widget.routineId).notifier);
    final catalogState = ref.watch(exerciseCatalogViewModelProvider);
    final exercises = catalogState.allExercises.isNotEmpty ? catalogState.allExercises : catalogState.exercises;

    ref.listen<RoutineEditorState>(routineEditorViewModelProvider(widget.routineId), (previous, next) {
      if (next.saveSuccess && !(previous?.saveSuccess ?? false)) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Routine saved successfully!'), backgroundColor: AppColors.surfaceElevated));
        Navigator.pop(context);
      }
    });

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            // Custom Expressive Header
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM, vertical: AppDimensions.paddingS),
              child: Row(
                children: [
                  const AppBackButton(),
                  const SizedBox(width: AppDimensions.paddingS),
                  Text(
                    widget.routineId == null ? 'Create Routine' : 'Edit Routine',
                    style: const TextStyle(
                      fontSize: AppDimensions.fontXXL,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.3,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ],
              ),
            ),

            // Validation Error Card
            if (state.validationError != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM),
                child: Container(
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: AppColors.error.withValues(alpha: AppColors.opacityLow),
                    borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                    border: Border.all(color: AppColors.error.withValues(alpha: AppColors.opacityLow)),
                  ),
                  padding: const EdgeInsets.all(AppDimensions.paddingM),
                  margin: const EdgeInsets.only(bottom: AppDimensions.paddingM),
                  child: Row(
                    children: [
                      const FaIcon(FontAwesomeIcons.circleExclamation, color: AppColors.error, size: AppDimensions.iconM),
                      const SizedBox(width: AppDimensions.paddingS),
                      Expanded(
                        child: Text(
                          state.validationError!,
                          style: const TextStyle(color: AppColors.error, fontWeight: FontWeight.bold, fontSize: AppDimensions.fontM),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            Expanded(
              child: SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                padding: const EdgeInsets.all(AppDimensions.paddingM),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Form fields
                    Cue.onMount(
                      motion: const CueMotion.easeOutBack(AppDimensions.animDurationMedium),
                      child: Actor(
                        acts: const [Act.fadeIn(), Act.translateY(from: 0.05)],
                        child: TextField(
                          controller: _titleController,
                          key: const Key('title_field'),
                          decoration: InputDecoration(
                            labelText: 'Routine Title',
                            labelStyle: const TextStyle(color: AppColors.textSecondary),
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
                    const SizedBox(height: AppDimensions.paddingM),
                    Cue.onMount(
                      motion: const CueMotion.easeOutBack(AppDimensions.animDurationSlow),
                      child: Actor(
                        acts: const [Act.fadeIn(), Act.translateY(from: 0.05)],
                        child: TextField(
                          controller: _descriptionController,
                          key: const Key('description_field'),
                          decoration: InputDecoration(
                            labelText: 'Description',
                            labelStyle: const TextStyle(color: AppColors.textSecondary),
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
                          maxLines: 2,
                        ),
                      ),
                    ),
                    const SizedBox(height: AppDimensions.paddingXL),

                    // Steps Header Row
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Workout Steps',
                          style: TextStyle(
                            fontSize: AppDimensions.fontXL,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 0.3,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.surfaceElevated,
                            foregroundColor: AppColors.textPrimary,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                              side: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
                            ),
                          ),
                          onPressed: () async {
                            final Exercise? chosen = await Navigator.push<Exercise>(
                              context,
                              MaterialPageRoute(builder: (context) => const ExerciseCatalogScreen(isSelectionMode: true)),
                            );
                            if (chosen != null) {
                              notifier.addStep(
                                WorkoutStep(
                                  exerciseId: chosen.id,
                                  sets: 3,
                                  reps: 10,
                                  weight: 0.0,
                                  targetDurationSeconds: 0,
                                  restDurationSeconds: 60,
                                  orderIndex: state.steps.length,
                                ),
                              );
                            }
                          },
                          icon: const FaIcon(FontAwesomeIcons.plus, size: AppDimensions.iconS),
                          label: const Text('Add Step', style: TextStyle(fontWeight: FontWeight.bold)),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppDimensions.paddingM),

                    // Steps List
                    if (state.steps.isEmpty)
                      Cue.onMount(
                        motion: const CueMotion.easeOutBack(AppDimensions.animDurationSlow),
                        child: Actor(
                          acts: const [Act.fadeIn(), Act.translateY(from: 0.1)],
                          child: Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(vertical: AppDimensions.emptyStateVerticalPadding),
                            decoration: BoxDecoration(
                              color: AppColors.surfaceElevated,
                              border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
                              borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                            ),
                            child: const Center(
                              child: Column(
                                children: [
                                  FaIcon(FontAwesomeIcons.clipboardList, size: AppDimensions.iconXXL, color: AppColors.border),
                                  SizedBox(height: AppDimensions.paddingM),
                                  Text(
                                    'No steps added yet.\nAdd at least one exercise to save the routine.',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(color: AppColors.textSecondary, fontSize: AppDimensions.fontM),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      )
                    else
                      ListView.builder(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: state.steps.length,
                        itemBuilder: (context, index) {
                          final step = state.steps[index];
                          final exercise = exercises.firstWhere(
                            (e) => e.id == step.exerciseId,
                            orElse: () => Exercise(
                              id: step.exerciseId,
                              name: 'Unknown Exercise',
                              primaryMuscleGroup: 'Unknown',
                              equipment: 'None',
                              animationType: 'rive',
                              animationPath: '',
                              description: '',
                            ),
                          );

                          return Cue.onMount(
                            motion: const CueMotion.easeOutBack(AppDimensions.animDurationMedium),
                            child: Actor(
                              acts: const [Act.fadeIn(), Act.translateY(from: 0.08)],
                              child: Card(
                                key: ValueKey('step_${step.exerciseId}_${step.orderIndex}'),
                                color: AppColors.surfaceElevated,
                                margin: const EdgeInsets.only(bottom: AppDimensions.paddingM),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                                  side: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
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
                                            child: Text(
                                              exercise.name,
                                              style: const TextStyle(
                                                fontWeight: FontWeight.bold,
                                                fontSize: AppDimensions.fontL,
                                                color: AppColors.textPrimary,
                                              ),
                                            ),
                                          ),
                                          IconButton(
                                            icon: const FaIcon(FontAwesomeIcons.trashCan, color: AppColors.error, size: AppDimensions.iconM),
                                            onPressed: () => notifier.removeStep(index),
                                          ),
                                        ],
                                      ),
                                      const Divider(color: AppColors.border, height: AppDimensions.paddingM),

                                      // Sets Slider
                                      Row(
                                        children: [
                                          const SizedBox(
                                            width: AppDimensions.sliderLabelWidth,
                                            child: Text(
                                              'Sets',
                                              style: TextStyle(color: AppColors.textSecondary, fontWeight: FontWeight.w600),
                                            ),
                                          ),
                                          Expanded(
                                            child: Slider(
                                              value: step.sets.toDouble().clamp(AppDimensions.sliderSetsMin, AppDimensions.sliderSetsMax),
                                              min: AppDimensions.sliderSetsMin,
                                              max: AppDimensions.sliderSetsMax,
                                              divisions: AppDimensions.sliderSetsDivisions,
                                              activeColor: AppColors.primary,
                                              inactiveColor: AppColors.border,
                                              label: '${step.sets}',
                                              onChanged: (val) {
                                                notifier.updateStep(index, step.copyWith(sets: val.toInt()));
                                              },
                                            ),
                                          ),
                                          Text(
                                            '${step.sets}',
                                            style: const TextStyle(
                                              fontWeight: FontWeight.w900,
                                              color: AppColors.primary,
                                              fontSize: AppDimensions.fontM,
                                            ),
                                          ),
                                        ],
                                      ),

                                      // Reps Slider
                                      Row(
                                        children: [
                                          const SizedBox(
                                            width: AppDimensions.sliderLabelWidth,
                                            child: Text(
                                              'Reps',
                                              style: TextStyle(color: AppColors.textSecondary, fontWeight: FontWeight.w600),
                                            ),
                                          ),
                                          Expanded(
                                            child: Slider(
                                              value: step.reps.toDouble().clamp(AppDimensions.sliderRepsMin, AppDimensions.sliderRepsMax),
                                              min: AppDimensions.sliderRepsMin,
                                              max: AppDimensions.sliderRepsMax,
                                              divisions: AppDimensions.sliderRepsDivisions,
                                              activeColor: AppColors.primary,
                                              inactiveColor: AppColors.border,
                                              label: '${step.reps}',
                                              onChanged: (val) {
                                                notifier.updateStep(index, step.copyWith(reps: val.toInt()));
                                              },
                                            ),
                                          ),
                                          Text(
                                            '${step.reps}',
                                            style: const TextStyle(
                                              fontWeight: FontWeight.w900,
                                              color: AppColors.primary,
                                              fontSize: AppDimensions.fontM,
                                            ),
                                          ),
                                        ],
                                      ),

                                      // Weight Slider
                                      Row(
                                        children: [
                                          const SizedBox(
                                            width: AppDimensions.sliderLabelWidth,
                                            child: Text(
                                              'Weight (kg)',
                                              style: TextStyle(color: AppColors.textSecondary, fontWeight: FontWeight.w600),
                                            ),
                                          ),
                                          Expanded(
                                            child: Slider(
                                              value: step.weight.clamp(AppDimensions.sliderWeightMin, AppDimensions.sliderWeightMax),
                                              min: AppDimensions.sliderWeightMin,
                                              max: AppDimensions.sliderWeightMax,
                                              divisions: AppDimensions.sliderWeightDivisions,
                                              activeColor: AppColors.primary,
                                              inactiveColor: AppColors.border,
                                              label: '${step.weight.toStringAsFixed(1)} kg',
                                              onChanged: (val) {
                                                notifier.updateStep(index, step.copyWith(weight: val));
                                              },
                                            ),
                                          ),
                                          Text(
                                            step.weight.toStringAsFixed(1),
                                            style: const TextStyle(
                                              fontWeight: FontWeight.w900,
                                              color: AppColors.primary,
                                              fontSize: AppDimensions.fontM,
                                            ),
                                          ),
                                        ],
                                      ),

                                      // Rest Duration Slider
                                      Row(
                                        children: [
                                          const SizedBox(
                                            width: AppDimensions.sliderLabelWidth,
                                            child: Text(
                                              'Rest (s)',
                                              style: TextStyle(color: AppColors.textSecondary, fontWeight: FontWeight.w600),
                                            ),
                                          ),
                                          Expanded(
                                            child: Slider(
                                              value: step.restDurationSeconds.toDouble().clamp(
                                                AppDimensions.sliderRestMin,
                                                AppDimensions.sliderRestMax,
                                              ),
                                              min: AppDimensions.sliderRestMin,
                                              max: AppDimensions.sliderRestMax,
                                              divisions: AppDimensions.sliderRestDivisions,
                                              activeColor: AppColors.primary,
                                              inactiveColor: AppColors.border,
                                              label: '${step.restDurationSeconds}s',
                                              onChanged: (val) {
                                                notifier.updateStep(index, step.copyWith(restDurationSeconds: val.toInt()));
                                              },
                                            ),
                                          ),
                                          Text(
                                            '${step.restDurationSeconds}s',
                                            style: const TextStyle(
                                              fontWeight: FontWeight.w900,
                                              color: AppColors.primary,
                                              fontSize: AppDimensions.fontM,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          );
                        },
                      ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: state.isSaving ? null : () => notifier.saveRoutine(),
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.background,
        elevation: AppDimensions.cardElevation,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
        icon: state.isSaving
            ? const SizedBox(
                width: AppDimensions.spinnerSize,
                height: AppDimensions.spinnerSize,
                child: CircularProgressIndicator(strokeWidth: AppDimensions.strokeWidthThin, color: AppColors.background),
              )
            : const FaIcon(FontAwesomeIcons.check, size: AppDimensions.iconSM),
        label: const Text('Save Routine', style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5)),
      ),
    );
  }
}
