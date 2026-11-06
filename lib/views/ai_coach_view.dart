// 🐦 Flutter imports:
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

// 📦 Package imports:
import 'package:cue/cue.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/ai_coach_models.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/utils/exercise_animation_asset.dart';
import 'package:comunityfitness/viewmodels/active_workout_viewmodel.dart';
import 'package:comunityfitness/viewmodels/ai_coach_viewmodel.dart';
import 'package:comunityfitness/viewmodels/exercise_catalog_viewmodel.dart';
import 'package:comunityfitness/views/active_workout_screen.dart';
import 'package:comunityfitness/views/exercise_detail_screen.dart';
import 'package:comunityfitness/views/language_selector_sheet.dart';
import 'package:comunityfitness/views/widgets/ai_coach_avatar.dart';
import 'package:comunityfitness/views/widgets/app_back_button.dart';
import 'package:comunityfitness/views/widgets/atlas_hybrid_ai_panel.dart';

class AiCoachView extends ConsumerStatefulWidget {
  final Exercise? initialExercise;
  final bool autoRequestAlternatives;

  const AiCoachView({super.key, this.initialExercise, this.autoRequestAlternatives = false});

  static Future<void> showSheet(BuildContext context, {Exercise? initialExercise, bool autoRequestAlternatives = false}) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.transparent,
      elevation: 0,
      builder: (ctx) => FractionallySizedBox(
        heightFactor: AppDimensions.aiSheetHeightFactor,
        child: ClipRRect(
          borderRadius: const BorderRadius.vertical(top: Radius.circular(AppDimensions.radiusBottomSheet)),
          child: AiCoachView(initialExercise: initialExercise, autoRequestAlternatives: autoRequestAlternatives),
        ),
      ),
    );
  }

  static Future<void> showAlternativeSheet(BuildContext context, Exercise exercise) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.transparent,
      elevation: 0,
      builder: (ctx) => FractionallySizedBox(
        heightFactor: AppDimensions.aiSheetHeightFactor,
        child: ClipRRect(
          borderRadius: const BorderRadius.vertical(top: Radius.circular(AppDimensions.radiusBottomSheet)),
          child: AiExerciseAlternativeSheet(exercise: exercise),
        ),
      ),
    );
  }

  @override
  ConsumerState<AiCoachView> createState() => _AiCoachViewState();
}

class _AiCoachViewState extends ConsumerState<AiCoachView> {
  final TextEditingController _inputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  bool _isHybridPanelExpanded = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      final vm = ref.read(aiCoachViewModelProvider.notifier);
      if (widget.initialExercise != null) {
        vm.setContextExercise(widget.initialExercise);
        if (widget.autoRequestAlternatives) {
          vm.requestExerciseAlternatives(exercise: widget.initialExercise!);
        }
      }
    });
  }

  @override
  void dispose() {
    _inputController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _handleSend(AiCoachViewModel vm) {
    final text = _inputController.text.trim();
    if (text.isEmpty) {
      vm.toggleMicRecording();
      return;
    }
    _inputController.clear();
    setState(() {});
    vm.sendChatMessage(text);
  }

  @override
  Widget build(BuildContext context) {
    final tr = TranslationProvider.of(context).translations;
    final state = ref.watch(aiCoachViewModelProvider);
    final vm = ref.read(aiCoachViewModelProvider.notifier);

    ref.listen<AiCoachState>(aiCoachViewModelProvider, (previous, next) {
      if (previous != null && next.messages.length > previous.messages.length) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (_scrollController.hasClients) {
            _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
          }
        });
      }
    });

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleSpacing: 0,
        leading: const AppBackButton(key: Key('ai_coach_back_button')),
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            AiCoachAvatar(
              key: const Key('ai_coach_header_avatar'),
              size: AppDimensions.iconXXL,
              mode: state.isLoading
                  ? AiCoachAvatarMode.thinking
                  : (state.liveState == AiLiveCoachState.speaking ? AiCoachAvatarMode.speaking : AiCoachAvatarMode.idle),
            ),
            const SizedBox(width: AppDimensions.paddingS),
            Flexible(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    tr.aiCoach.headerTitle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: AppDimensions.fontS,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.4,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: AppDimensions.paddingXXS),
                  Text(
                    tr.aiCoach.modelBadge,
                    key: const Key('ai_coach_model_badge'),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w700, color: AppColors.secondary),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            key: const Key('ai_coach_language_button'),
            visualDensity: VisualDensity.compact,
            icon: const FaIcon(FontAwesomeIcons.globe, size: AppDimensions.iconS, color: AppColors.secondary),
            tooltip: tr.dashboard.languageTooltip,
            onPressed: () {
              LanguageSelectorSheet.show(context, onLocaleChanged: (_) => vm.refreshLocale());
            },
          ),
          Padding(
            padding: const EdgeInsets.only(right: AppDimensions.paddingXS),
            child: ActionChip(
              key: const Key('ai_coach_hybrid_mode_button'),
              onPressed: () {
                setState(() {
                  _isHybridPanelExpanded = !_isHybridPanelExpanded;
                });
              },
              avatar: FaIcon(
                FontAwesomeIcons.microchip,
                size: AppDimensions.iconXS,
                color: _isHybridPanelExpanded ? AppColors.primary : AppColors.secondary,
              ),
              label: Text(
                'Hybrid NPU',
                style: TextStyle(
                  fontSize: AppDimensions.fontXS,
                  fontWeight: FontWeight.w800,
                  color: _isHybridPanelExpanded ? AppColors.primary : AppColors.textPrimary,
                ),
              ),
              backgroundColor: _isHybridPanelExpanded
                  ? AppColors.primary.withValues(alpha: AppColors.opacityLow)
                  : AppColors.surfaceElevated,
              side: BorderSide(
                color: _isHybridPanelExpanded ? AppColors.primary : AppColors.border,
                width: _isHybridPanelExpanded ? AppDimensions.borderThick : AppDimensions.borderDefault,
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(right: AppDimensions.paddingM),
            child: IconButton(
              key: const Key('ai_live_coach_toggle'),
              tooltip: state.isLiveModeActive ? tr.aiCoach.liveActive : tr.aiCoach.liveVoiceToggle,
              style: IconButton.styleFrom(
                backgroundColor: state.isLiveModeActive ? AppColors.primary.withValues(alpha: AppColors.opacityLow) : AppColors.surfaceElevated,
                side: BorderSide(
                  color: state.isLiveModeActive ? AppColors.primary : AppColors.border,
                  width: state.isLiveModeActive ? AppDimensions.borderThick : AppDimensions.borderDefault,
                ),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
                padding: const EdgeInsets.all(AppDimensions.paddingS),
              ),
              icon: FaIcon(
                state.isLiveModeActive ? FontAwesomeIcons.towerBroadcast : FontAwesomeIcons.headset,
                size: AppDimensions.iconM,
                color: state.isLiveModeActive ? AppColors.primary : AppColors.secondary,
              ),
              onPressed: () => vm.toggleLiveCoachMode(),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          if (state.isLiveModeActive)
            _LiveVoiceCoachBanner(
              state: state,
              onQuickVoicePrompt: (prompt) => vm.sendLiveVoiceTurn(prompt),
              onToggleMic: () => vm.toggleMicRecording(),
              onStopLive: () => vm.toggleLiveCoachMode(),
            ),
          Expanded(
            child: ListView(
              controller: _scrollController,
              scrollCacheExtent: const ScrollCacheExtent.pixels(AppDimensions.catalogCacheExtent),
              padding: const EdgeInsets.all(AppDimensions.paddingM),
              children: [
                if (_isHybridPanelExpanded) ...[
                  AtlasHybridAiPanel(activeExercise: state.contextExercise),
                  const SizedBox(height: AppDimensions.paddingM),
                ],
                if (state.contextExercise != null) ...[
                  _ContextExerciseAlternativeCard(
                    exercise: state.contextExercise!,
                    selectedConstraint: state.selectedAlternativeConstraint,
                    isLoading: state.isLoading,
                    onSelectConstraint: (constraint) {
                      vm.requestExerciseAlternatives(exercise: state.contextExercise!, customConstraint: constraint);
                    },
                    onClearContext: () => vm.setContextExercise(null),
                  ),
                  const SizedBox(height: AppDimensions.paddingM),
                ],
                _MuscleAndEquipmentPlannerCard(
                  selectedMuscles: state.selectedMuscles,
                  selectedEquipment: state.selectedEquipmentConstraint,
                  isLoading: state.isLoading,
                  onToggleMuscle: vm.toggleTargetMuscle,
                  onSelectEquipment: vm.setEquipmentConstraint,
                  onGeneratePlan: () => vm.generateWorkoutForSelectedMuscles(),
                ),
                const SizedBox(height: AppDimensions.paddingM),
                if (state.errorMessage != null)
                  Container(
                    margin: const EdgeInsets.only(bottom: AppDimensions.paddingM),
                    padding: const EdgeInsets.all(AppDimensions.paddingM),
                    decoration: BoxDecoration(
                      color: AppColors.error.withValues(alpha: AppColors.opacityLow),
                      borderRadius: BorderRadius.circular(AppDimensions.aiCardRadius),
                      border: Border.all(color: AppColors.error, width: AppDimensions.borderDefault),
                    ),
                    child: Row(
                      children: [
                        const FaIcon(FontAwesomeIcons.triangleExclamation, size: AppDimensions.iconM, color: AppColors.error),
                        const SizedBox(width: AppDimensions.paddingS),
                        Expanded(
                          child: Text(
                            state.errorMessage!,
                            style: const TextStyle(fontSize: AppDimensions.fontS, color: AppColors.textPrimary),
                          ),
                        ),
                      ],
                    ),
                  ),
                ...state.messages.map(
                  (msg) => _AiChatMessageTile(
                    message: msg,
                    isHeroCoachMessage:
                        msg.role == AiChatRole.coach && msg.id == state.messages.lastWhere((m) => m.role == AiChatRole.coach, orElse: () => msg).id,
                  ),
                ),
                if (state.isLoading)
                  Container(
                    margin: const EdgeInsets.symmetric(vertical: AppDimensions.paddingM),
                    padding: const EdgeInsets.all(AppDimensions.paddingM),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceElevated,
                      borderRadius: BorderRadius.circular(AppDimensions.aiCardRadius),
                      border: Border.all(
                        color: AppColors.secondary.withValues(alpha: AppColors.opacityMedium),
                        width: AppDimensions.borderDefault,
                      ),
                    ),
                    child: Row(
                      children: [
                        const AiCoachAvatar(
                          key: Key('ai_coach_planning_avatar'),
                          size: AppDimensions.aiSheetAvatarSize,
                          mode: AiCoachAvatarMode.thinking,
                        ),
                        const SizedBox(width: AppDimensions.paddingM),
                        Expanded(
                          child: Text(
                            tr.aiCoach.analyzingMovements,
                            style: const TextStyle(fontSize: AppDimensions.fontS, fontWeight: FontWeight.w700, color: AppColors.textSecondary),
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          _CoachChatInputBar(
            controller: _inputController,
            isLiveActive: state.isLiveModeActive,
            isMicRecording: state.isMicRecording,
            isLoading: state.isLoading,
            hasTypedText: _inputController.text.trim().isNotEmpty,
            onTextChanged: (_) => setState(() {}),
            onSend: () => _handleSend(vm),
          ),
        ],
      ),
    );
  }
}

/// Dedicated bottom sheet launched from an Exercise Card or Exercise Detail Screen
/// to find home/no-weights or equipment-specific alternatives in one tap.
class AiExerciseAlternativeSheet extends ConsumerStatefulWidget {
  final Exercise exercise;

  const AiExerciseAlternativeSheet({super.key, required this.exercise});

  @override
  ConsumerState<AiExerciseAlternativeSheet> createState() => _AiExerciseAlternativeSheetState();
}

class _AiExerciseAlternativeSheetState extends ConsumerState<AiExerciseAlternativeSheet> {
  final TextEditingController _customConstraintController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      ref.read(aiCoachViewModelProvider.notifier).requestExerciseAlternatives(exercise: widget.exercise, customConstraint: 'At Home / No Weights');
    });
  }

  @override
  void dispose() {
    _customConstraintController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final tr = TranslationProvider.of(context).translations;
    final state = ref.watch(aiCoachViewModelProvider);
    final vm = ref.read(aiCoachViewModelProvider.notifier);

    return Container(
      decoration: const BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppDimensions.radiusBottomSheet)),
      ),
      padding: const EdgeInsets.all(AppDimensions.paddingL),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
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
          const SizedBox(height: AppDimensions.paddingM),
          Row(
            children: [
              AiCoachAvatar(
                key: const Key('ai_alternatives_sheet_avatar'),
                size: AppDimensions.aiSheetAvatarSize,
                mode: state.isLoading ? AiCoachAvatarMode.thinking : AiCoachAvatarMode.speaking,
              ),
              const SizedBox(width: AppDimensions.paddingM),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      tr.aiCoach.alternativesSheet.title(name: widget.exercise.name),
                      style: const TextStyle(fontSize: AppDimensions.fontL, fontWeight: FontWeight.w900, color: AppColors.textPrimary),
                    ),
                    const SizedBox(height: AppDimensions.paddingXXS),
                    Text(
                      'ATLAS • ${tr.translateMuscle(widget.exercise.primaryMuscleGroup)} (${widget.exercise.equipment})',
                      style: const TextStyle(fontSize: AppDimensions.fontXS, fontWeight: FontWeight.w600, color: AppColors.secondary),
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const FaIcon(FontAwesomeIcons.xmark, size: AppDimensions.iconM, color: AppColors.textSecondary),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingM),
          SizedBox(
            height: AppDimensions.aiChipRowHeight,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              itemCount: AiCoachState.alternativeQuickConstraints.length,
              itemBuilder: (context, index) {
                final constraint = AiCoachState.alternativeQuickConstraints[index];
                final isSelected = state.selectedAlternativeConstraint == constraint;
                return Padding(
                  padding: const EdgeInsets.only(right: AppDimensions.paddingS),
                  child: FilterChip(
                    key: Key('alt_constraint_chip_$constraint'),
                    label: Text(tr.translateConstraint(constraint)),
                    selected: isSelected,
                    onSelected: (_) {
                      vm.requestExerciseAlternatives(exercise: widget.exercise, customConstraint: constraint);
                    },
                    backgroundColor: AppColors.surfaceElevated,
                    selectedColor: AppColors.primary.withValues(alpha: AppColors.opacityLow),
                    checkmarkColor: AppColors.primary,
                    labelStyle: TextStyle(
                      fontSize: AppDimensions.fontXS,
                      fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
                      color: isSelected ? AppColors.primary : AppColors.textSecondary,
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
              },
            ),
          ),
          const SizedBox(height: AppDimensions.paddingM),
          Row(
            children: [
              Expanded(
                child: TextField(
                  key: const Key('custom_alternative_constraint_field'),
                  controller: _customConstraintController,
                  style: const TextStyle(fontSize: AppDimensions.fontS, color: AppColors.textPrimary),
                  decoration: InputDecoration(hintText: tr.aiCoach.alternativesSheet.customHint),
                  onSubmitted: (val) {
                    if (val.trim().isNotEmpty) {
                      vm.requestExerciseAlternatives(exercise: widget.exercise, customConstraint: val.trim());
                    }
                  },
                ),
              ),
              const SizedBox(width: AppDimensions.paddingS),
              IconButton(
                key: const Key('submit_custom_constraint_button'),
                style: IconButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  padding: const EdgeInsets.all(AppDimensions.paddingM),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
                ),
                icon: const FaIcon(FontAwesomeIcons.bolt, size: AppDimensions.iconS, color: AppColors.background),
                onPressed: () {
                  final custom = _customConstraintController.text.trim();
                  vm.requestExerciseAlternatives(
                    exercise: widget.exercise,
                    customConstraint: custom.isNotEmpty ? custom : state.selectedAlternativeConstraint,
                  );
                },
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingM),
          Expanded(
            child: state.isLoading
                ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
                : ListView.builder(
                    itemCount: state.currentAlternatives.length,
                    itemBuilder: (context, index) {
                      final rec = state.currentAlternatives[index];
                      return Padding(
                        padding: const EdgeInsets.only(bottom: AppDimensions.paddingS),
                        child: _AiRecommendationCard(recommendation: rec),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

class _LiveVoiceCoachBanner extends StatelessWidget {
  final AiCoachState state;
  final ValueChanged<String> onQuickVoicePrompt;
  final VoidCallback onToggleMic;
  final VoidCallback onStopLive;

  const _LiveVoiceCoachBanner({required this.state, required this.onQuickVoicePrompt, required this.onToggleMic, required this.onStopLive});

  String _statusLabel(Translations tr, AiLiveCoachState liveState, bool isMicRecording) {
    if (liveState == AiLiveCoachState.speaking) {
      return tr.aiCoach.liveBanner.speaking;
    }
    if (liveState == AiLiveCoachState.thinking) {
      return tr.aiCoach.liveBanner.thinking;
    }
    if (liveState == AiLiveCoachState.connecting) {
      return tr.aiCoach.liveBanner.connecting;
    }
    if (isMicRecording) {
      return tr.aiCoach.liveBanner.listeningMic;
    }
    switch (liveState) {
      case AiLiveCoachState.connecting:
        return tr.aiCoach.liveBanner.connecting;
      case AiLiveCoachState.listening:
        return tr.aiCoach.liveBanner.listening;
      case AiLiveCoachState.thinking:
        return tr.aiCoach.liveBanner.thinking;
      case AiLiveCoachState.speaking:
        return tr.aiCoach.liveBanner.speaking;
      case AiLiveCoachState.disconnected:
        return tr.aiCoach.liveBanner.disconnected;
    }
  }

  @override
  Widget build(BuildContext context) {
    final tr = TranslationProvider.of(context).translations;
    final isActivelyListeningMic = state.isMicRecording && state.liveState == AiLiveCoachState.listening;
    final accentColor = isActivelyListeningMic ? AppColors.error : AppColors.primary;
    return Cue.onMount(
      motion: const CueMotion.easeOutBack(AppDimensions.animDurationFast),
      child: Actor(
        acts: const [Act.fadeIn(), Act.translateY(from: -0.05)],
        child: Container(
          key: const Key('ai_live_voice_banner'),
          width: double.infinity,
          margin: const EdgeInsets.fromLTRB(AppDimensions.paddingM, AppDimensions.paddingS, AppDimensions.paddingM, AppDimensions.paddingXS),
          padding: const EdgeInsets.all(AppDimensions.paddingM),
          decoration: BoxDecoration(
            color: AppColors.surfaceElevated,
            borderRadius: BorderRadius.circular(AppDimensions.aiCardRadius),
            border: Border.all(color: accentColor, width: AppDimensions.borderThick),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  InkWell(
                    key: const Key('ai_live_orb_mic_button'),
                    customBorder: const CircleBorder(),
                    onTap: onToggleMic,
                    child: AiCoachAvatar(
                      size: AppDimensions.aiLiveHeroAvatarSize,
                      mode: isActivelyListeningMic
                          ? AiCoachAvatarMode.listening
                          : (state.liveState == AiLiveCoachState.speaking
                                ? AiCoachAvatarMode.speaking
                                : (state.liveState == AiLiveCoachState.thinking ? AiCoachAvatarMode.thinking : AiCoachAvatarMode.idle)),
                    ),
                  ),
                  const SizedBox(width: AppDimensions.paddingM),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _statusLabel(tr, state.liveState, state.isMicRecording),
                          style: TextStyle(fontSize: AppDimensions.fontXS, fontWeight: FontWeight.w900, letterSpacing: 0.8, color: accentColor),
                        ),
                        const SizedBox(height: AppDimensions.paddingXS),
                        Text(
                          state.liveSpokenCue ?? tr.aiCoach.liveBanner.defaultHint,
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: AppDimensions.fontS, color: AppColors.textPrimary),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const FaIcon(FontAwesomeIcons.circleStop, size: AppDimensions.iconL, color: AppColors.error),
                    tooltip: tr.aiCoach.liveBanner.endSessionTooltip,
                    onPressed: onStopLive,
                  ),
                ],
              ),
              const SizedBox(height: AppDimensions.paddingS),
              Wrap(
                spacing: AppDimensions.paddingS,
                runSpacing: AppDimensions.paddingXS,
                children: [
                  _QuickVoiceChip(
                    label: tr.aiCoach.liveBanner.quickChipChestAbs,
                    onTap: () => onQuickVoicePrompt(tr.aiCoach.liveBanner.quickPromptChestAbs),
                  ),
                  _QuickVoiceChip(
                    label: tr.aiCoach.liveBanner.quickChipBackBiceps,
                    onTap: () => onQuickVoicePrompt(tr.aiCoach.liveBanner.quickPromptBackBiceps),
                  ),
                  _QuickVoiceChip(
                    label: tr.aiCoach.liveBanner.quickChipLegsGlutes,
                    onTap: () => onQuickVoicePrompt(tr.aiCoach.liveBanner.quickPromptLegsGlutes),
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

class _QuickVoiceChip extends StatelessWidget {
  final String label;
  final VoidCallback onTap;

  const _QuickVoiceChip({required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXS),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
          border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const FaIcon(FontAwesomeIcons.microphone, size: AppDimensions.iconXS, color: AppColors.secondary),
            const SizedBox(width: AppDimensions.paddingXS),
            Text(
              label,
              style: const TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
            ),
          ],
        ),
      ),
    );
  }
}

class _ContextExerciseAlternativeCard extends StatelessWidget {
  final Exercise exercise;
  final String selectedConstraint;
  final bool isLoading;
  final ValueChanged<String> onSelectConstraint;
  final VoidCallback onClearContext;

  const _ContextExerciseAlternativeCard({
    required this.exercise,
    required this.selectedConstraint,
    required this.isLoading,
    required this.onSelectConstraint,
    required this.onClearContext,
  });

  @override
  Widget build(BuildContext context) {
    final tr = TranslationProvider.of(context).translations;
    return Container(
      key: const Key('ai_context_exercise_card'),
      padding: const EdgeInsets.all(AppDimensions.paddingM),
      decoration: BoxDecoration(
        color: AppColors.surfaceElevated,
        borderRadius: BorderRadius.circular(AppDimensions.aiCardRadius),
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
              const FaIcon(FontAwesomeIcons.wandMagicSparkles, size: AppDimensions.iconS, color: AppColors.secondary),
              const SizedBox(width: AppDimensions.paddingS),
              Expanded(
                child: Text(
                  tr.aiCoach.contextCard.targetExercise(name: exercise.name.toUpperCase()),
                  style: const TextStyle(fontSize: AppDimensions.fontXS, fontWeight: FontWeight.w900, letterSpacing: 0.8, color: AppColors.secondary),
                ),
              ),
              IconButton(
                icon: const FaIcon(FontAwesomeIcons.xmark, size: AppDimensions.iconS, color: AppColors.textMuted),
                onPressed: onClearContext,
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingXS),
          Text(
            tr.aiCoach.contextCard.subtitle,
            style: const TextStyle(fontSize: AppDimensions.fontXS, color: AppColors.textSecondary),
          ),
          const SizedBox(height: AppDimensions.paddingS),
          Wrap(
            spacing: AppDimensions.paddingS,
            runSpacing: AppDimensions.paddingXS,
            children: AiCoachState.alternativeQuickConstraints.map((constraint) {
              final isSelected = selectedConstraint == constraint;
              return FilterChip(
                label: Text(tr.translateConstraint(constraint)),
                selected: isSelected,
                onSelected: isLoading ? null : (_) => onSelectConstraint(constraint),
                backgroundColor: AppColors.surface,
                selectedColor: AppColors.secondary.withValues(alpha: AppColors.opacityLow),
                checkmarkColor: AppColors.secondary,
                labelStyle: TextStyle(
                  fontSize: AppDimensions.fontXXS,
                  fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
                  color: isSelected ? AppColors.secondary : AppColors.textSecondary,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                  side: BorderSide(
                    color: isSelected ? AppColors.secondary : AppColors.border,
                    width: isSelected ? AppDimensions.borderThick : AppDimensions.borderDefault,
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}

class _MuscleAndEquipmentPlannerCard extends StatelessWidget {
  final List<String> selectedMuscles;
  final String selectedEquipment;
  final bool isLoading;
  final ValueChanged<String> onToggleMuscle;
  final ValueChanged<String> onSelectEquipment;
  final VoidCallback onGeneratePlan;

  const _MuscleAndEquipmentPlannerCard({
    required this.selectedMuscles,
    required this.selectedEquipment,
    required this.isLoading,
    required this.onToggleMuscle,
    required this.onSelectEquipment,
    required this.onGeneratePlan,
  });

  @override
  Widget build(BuildContext context) {
    final tr = TranslationProvider.of(context).translations;
    final localizedMuscles = selectedMuscles.map((m) => tr.translateMuscle(m)).join(' & ');
    final localizedEquipment = tr.translateEquipment(selectedEquipment);

    return Container(
      key: const Key('ai_muscle_planner_card'),
      padding: const EdgeInsets.all(AppDimensions.paddingM),
      decoration: BoxDecoration(
        color: AppColors.surfaceElevated,
        borderRadius: BorderRadius.circular(AppDimensions.aiCardRadius),
        border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const FaIcon(FontAwesomeIcons.dumbbell, size: AppDimensions.iconS, color: AppColors.primary),
              const SizedBox(width: AppDimensions.paddingS),
              Expanded(
                child: Text(
                  tr.aiCoach.plannerCard.title,
                  style: const TextStyle(
                    fontSize: AppDimensions.fontXS,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0.8,
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
            children: AiCoachState.availableTargetMuscles.map((muscle) {
              final isSelected = selectedMuscles.contains(muscle);
              return FilterChip(
                key: Key('ai_muscle_chip_$muscle'),
                label: Text(tr.translateMuscle(muscle)),
                selected: isSelected,
                onSelected: (_) => onToggleMuscle(muscle),
                backgroundColor: AppColors.surface,
                selectedColor: AppColors.primary.withValues(alpha: AppColors.opacityLow),
                checkmarkColor: AppColors.primary,
                labelStyle: TextStyle(
                  fontSize: AppDimensions.fontXS,
                  fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
                  color: isSelected ? AppColors.primary : AppColors.textSecondary,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                  side: BorderSide(
                    color: isSelected ? AppColors.primary : AppColors.border,
                    width: isSelected ? AppDimensions.borderThick : AppDimensions.borderDefault,
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: AppDimensions.paddingM),
          Text(
            tr.aiCoach.plannerCard.availableEquipment,
            style: const TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w900, letterSpacing: 1.0, color: AppColors.textMuted),
          ),
          const SizedBox(height: AppDimensions.paddingXS),
          Wrap(
            spacing: AppDimensions.paddingS,
            runSpacing: AppDimensions.paddingXS,
            children: AiCoachState.availableEquipmentFilters.map((eq) {
              final isSelected = selectedEquipment == eq;
              return FilterChip(
                key: Key('ai_equipment_chip_$eq'),
                label: Text(tr.translateEquipment(eq)),
                selected: isSelected,
                onSelected: (_) => onSelectEquipment(eq),
                backgroundColor: AppColors.surface,
                selectedColor: AppColors.secondary.withValues(alpha: AppColors.opacityLow),
                checkmarkColor: AppColors.secondary,
                labelStyle: TextStyle(
                  fontSize: AppDimensions.fontXS,
                  fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
                  color: isSelected ? AppColors.secondary : AppColors.textSecondary,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                  side: BorderSide(
                    color: isSelected ? AppColors.secondary : AppColors.border,
                    width: isSelected ? AppDimensions.borderThick : AppDimensions.borderDefault,
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: AppDimensions.paddingM),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              key: const Key('generate_ai_workout_button'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: AppColors.background,
                padding: const EdgeInsets.symmetric(vertical: AppDimensions.paddingM),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
              ),
              icon: const FaIcon(FontAwesomeIcons.wandMagicSparkles, size: AppDimensions.iconS),
              label: Text(
                tr.aiCoach.plannerCard.buildPlanButton(muscles: localizedMuscles, equipment: localizedEquipment),
                style: const TextStyle(fontSize: AppDimensions.fontS, fontWeight: FontWeight.w900),
              ),
              onPressed: isLoading ? null : onGeneratePlan,
            ),
          ),
        ],
      ),
    );
  }
}

class _AiChatMessageTile extends ConsumerWidget {
  final AiChatMessage message;
  final bool isHeroCoachMessage;

  const _AiChatMessageTile({required this.message, this.isHeroCoachMessage = false});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tr = TranslationProvider.of(context).translations;
    final isUser = message.role == AiChatRole.user;

    return Padding(
      padding: const EdgeInsets.only(bottom: AppDimensions.paddingM),
      child: Column(
        crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(AppDimensions.paddingM),
            decoration: BoxDecoration(
              color: isUser ? AppColors.primary.withValues(alpha: AppColors.opacityLow) : AppColors.surfaceElevated,
              borderRadius: BorderRadius.circular(AppDimensions.aiMessageBubbleRadius),
              border: Border.all(color: isUser ? AppColors.primary : AppColors.border, width: AppDimensions.borderDefault),
            ),
            child: isUser
                ? Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const FaIcon(FontAwesomeIcons.user, size: AppDimensions.iconXS, color: AppColors.primary),
                          const SizedBox(width: AppDimensions.paddingXS),
                          Flexible(
                            child: Text(
                              tr.aiCoach.youLabel,
                              style: const TextStyle(
                                fontSize: AppDimensions.fontXXS,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 0.6,
                                color: AppColors.primary,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppDimensions.paddingXS),
                      Text(
                        message.text,
                        style: const TextStyle(fontSize: AppDimensions.fontM, color: AppColors.textPrimary),
                      ),
                    ],
                  )
                : Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      AiCoachAvatar(
                        key: Key('ai_coach_message_avatar_${message.id}'),
                        size: isHeroCoachMessage ? AppDimensions.aiHeroAvatarSize : AppDimensions.aiMessageAvatarSize,
                        mode: AiCoachAvatarMode.speaking,
                      ),
                      const SizedBox(width: AppDimensions.paddingM),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              message.isLiveTranscript ? tr.aiCoach.liveCoachBadge : tr.aiCoach.flashCoachBadge,
                              style: const TextStyle(
                                fontSize: AppDimensions.fontXXS,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 0.6,
                                color: AppColors.secondary,
                              ),
                            ),
                            const SizedBox(height: AppDimensions.paddingXS),
                            Text(
                              message.text,
                              style: const TextStyle(fontSize: AppDimensions.fontM, color: AppColors.textPrimary),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
          ),
          if (message.workoutPlan != null) ...[const SizedBox(height: AppDimensions.paddingS), _AiWorkoutPlanCard(plan: message.workoutPlan!)],
          if (message.alternatives != null && message.alternatives!.isNotEmpty) ...[
            const SizedBox(height: AppDimensions.paddingS),
            ...message.alternatives!.map(
              (alt) => Padding(
                padding: const EdgeInsets.only(bottom: AppDimensions.paddingS),
                child: _AiRecommendationCard(recommendation: alt),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _AiWorkoutPlanCard extends ConsumerWidget {
  final AiWorkoutPlan plan;

  const _AiWorkoutPlanCard({required this.plan});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tr = TranslationProvider.of(context).translations;
    return Container(
      padding: const EdgeInsets.all(AppDimensions.paddingM),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppDimensions.aiCardRadius),
        border: Border.all(
          color: AppColors.primary.withValues(alpha: AppColors.opacityMedium),
          width: AppDimensions.borderDefault,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const FaIcon(FontAwesomeIcons.fireFlameCurved, size: AppDimensions.iconM, color: AppColors.primary),
              const SizedBox(width: AppDimensions.paddingS),
              Expanded(
                child: Text(
                  plan.title,
                  style: const TextStyle(fontSize: AppDimensions.fontL, fontWeight: FontWeight.w900, color: AppColors.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppDimensions.paddingS),
          ...plan.exercises.map(
            (rec) => Padding(
              padding: const EdgeInsets.only(bottom: AppDimensions.paddingS),
              child: _AiRecommendationCard(recommendation: rec),
            ),
          ),
          const SizedBox(height: AppDimensions.paddingXS),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              key: Key('start_ai_plan_${plan.title}'),
              style: OutlinedButton.styleFrom(
                backgroundColor: AppColors.primary.withValues(alpha: AppColors.opacityLow),
                side: const BorderSide(color: AppColors.primary, width: AppDimensions.borderDefault),
                padding: const EdgeInsets.symmetric(vertical: AppDimensions.paddingM),
              ),
              icon: const FaIcon(FontAwesomeIcons.play, size: AppDimensions.iconS, color: AppColors.primary),
              label: Text(
                tr.aiCoach.startAiWorkoutNow,
                style: const TextStyle(fontSize: AppDimensions.fontS, fontWeight: FontWeight.w900, color: AppColors.primary),
              ),
              onPressed: () {
                final activeVm = ref.read(activeWorkoutViewModelProvider.notifier);
                activeVm.startFromAiPlan(plan);
                Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const ActiveWorkoutScreen()));
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _AiRecommendationCard extends ConsumerWidget {
  final AiExerciseRecommendation recommendation;

  const _AiRecommendationCard({required this.recommendation});

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

  Exercise? _resolveCatalogExercise(WidgetRef ref) {
    if (recommendation.catalogExercise != null) {
      return recommendation.catalogExercise;
    }
    final allExercises = ref.watch(exerciseCatalogViewModelProvider).allExercises;
    if (allExercises.isEmpty) {
      return null;
    }
    final lowerName = recommendation.exerciseName.toLowerCase();
    for (final ex in allExercises) {
      if (ex.id == recommendation.exerciseId || ex.name.toLowerCase() == lowerName) {
        return ex;
      }
    }
    return null;
  }

  Widget _buildThumbnail(Exercise? exercise) {
    if (exercise != null) {
      if (exercise.animationType == 'gif' && exercise.animationPath.isNotEmpty && exercise.animationPath.startsWith('http')) {
        final thumbnailUrl = exercise.animationPath.replaceAll('/videos/', '/images/').replaceAll('.gif', '.jpg');
        return ClipRRect(
          borderRadius: BorderRadius.circular(AppDimensions.radiusS),
          child: Container(
            key: Key('ai_rec_network_thumb_${exercise.id}'),
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
                return Image.network(exercise.animationPath, fit: BoxFit.cover, errorBuilder: (ctx, err, st) => _buildFallbackIcon(exercise));
              },
            ),
          ),
        );
      }

      final thumbAsset = exerciseThumbnailAsset(exercise);
      if (thumbAsset != null) {
        return ClipRRect(
          borderRadius: BorderRadius.circular(AppDimensions.radiusS),
          child: SizedBox(
            key: Key('ai_rec_asset_thumb_${exercise.id}'),
            width: AppDimensions.thumbnailSize,
            height: AppDimensions.thumbnailSize,
            child: Image.asset(
              thumbAsset,
              fit: BoxFit.cover,
              cacheWidth: AppDimensions.thumbnailCacheSize,
              frameBuilder: (context, child, frame, wasSynchronouslyLoaded) => Stack(fit: StackFit.expand, children: [child, _buildHdBadge()]),
              errorBuilder: (_, _, _) => _buildFallbackIcon(exercise),
            ),
          ),
        );
      }
    }
    return _buildFallbackIcon(exercise);
  }

  Widget _buildFallbackIcon([Exercise? exercise]) {
    final muscle = exercise?.primaryMuscleGroup ?? '';
    final equipment = exercise?.equipment ?? '';
    final Color tint = switch (muscle) {
      'Chest' => AppColors.primary,
      'Legs' => AppColors.secondary,
      'Back' => AppColors.warning,
      'Shoulders' => AppColors.primary,
      'Arms' => AppColors.secondary,
      'Core' => AppColors.warning,
      'Cardio' => AppColors.error,
      _ => AppColors.secondary,
    };
    final FaIconData icon = switch (equipment) {
      'Barbell' => FontAwesomeIcons.weightHanging,
      'Dumbbell' => FontAwesomeIcons.dumbbell,
      'Bodyweight' => FontAwesomeIcons.personRunning,
      'Cable' => FontAwesomeIcons.gripLinesVertical,
      'Machine' => FontAwesomeIcons.gears,
      _ => FontAwesomeIcons.dumbbell,
    };

    return Container(
      width: AppDimensions.thumbnailSize,
      height: AppDimensions.thumbnailSize,
      decoration: BoxDecoration(
        color: tint.withValues(alpha: AppColors.opacityLow),
        borderRadius: BorderRadius.circular(AppDimensions.radiusS),
        border: Border.all(
          color: tint.withValues(alpha: AppColors.opacityMedium),
          width: AppDimensions.borderThin,
        ),
      ),
      child: Center(
        child: FaIcon(icon, size: AppDimensions.iconM, color: tint),
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tr = TranslationProvider.of(context).translations;
    final catalogExercise = _resolveCatalogExercise(ref);

    return InkWell(
      key: Key('ai_rec_card_${recommendation.exerciseId}'),
      borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
      onTap: catalogExercise != null ? () => ExerciseDetailScreen.show(context, catalogExercise) : null,
      child: Container(
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
                _buildThumbnail(catalogExercise),
                const SizedBox(width: AppDimensions.paddingM),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        recommendation.exerciseName,
                        style: const TextStyle(fontSize: AppDimensions.fontM, fontWeight: FontWeight.w900, color: AppColors.textPrimary),
                      ),
                      const SizedBox(height: AppDimensions.paddingXXS),
                      Text(
                        tr.aiCoach.setsRepsRest(sets: recommendation.sets, reps: recommendation.reps, rest: recommendation.restSeconds),
                        style: const TextStyle(fontSize: AppDimensions.fontXS, fontWeight: FontWeight.w700, color: AppColors.primary),
                      ),
                    ],
                  ),
                ),
                if (catalogExercise != null)
                  Builder(
                    builder: (_) {
                      final is3dRive = exerciseRiveAsset(catalogExercise) != null;
                      final badgeColor = is3dRive ? AppColors.secondary : AppColors.primary;
                      final badgeIcon = is3dRive ? FontAwesomeIcons.cube : FontAwesomeIcons.circlePlay;
                      final badgeLabel = is3dRive ? tr.aiCoach.form3dBadge : tr.aiCoach.formDemoBadge;
                      return Container(
                        key: Key(is3dRive ? 'ai_rec_3d_badge_${catalogExercise.id}' : 'ai_rec_demo_badge_${catalogExercise.id}'),
                        padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXS),
                        decoration: BoxDecoration(
                          color: badgeColor.withValues(alpha: AppColors.opacityLow),
                          borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
                          border: Border.all(color: badgeColor, width: AppDimensions.borderThin),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            FaIcon(badgeIcon, size: AppDimensions.iconXS, color: badgeColor),
                            const SizedBox(width: AppDimensions.paddingXS),
                            Text(
                              badgeLabel,
                              style: TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w900, color: badgeColor),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
              ],
            ),
            const SizedBox(height: AppDimensions.paddingS),
            Text(
              recommendation.matchReason,
              style: const TextStyle(fontSize: AppDimensions.fontXS, color: AppColors.textSecondary),
            ),
            if (recommendation.homeAdaptationTip.isNotEmpty) ...[
              const SizedBox(height: AppDimensions.paddingXS),
              Container(
                padding: const EdgeInsets.all(AppDimensions.paddingS),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(AppDimensions.radiusS),
                  border: Border.all(color: AppColors.borderSubtle, width: AppDimensions.borderThin),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const FaIcon(FontAwesomeIcons.house, size: AppDimensions.iconXS, color: AppColors.primary),
                    const SizedBox(width: AppDimensions.paddingS),
                    Expanded(
                      child: Text(
                        recommendation.homeAdaptationTip,
                        style: const TextStyle(fontSize: AppDimensions.fontXS, color: AppColors.textPrimary),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _CoachChatInputBar extends StatelessWidget {
  final TextEditingController controller;
  final bool isLiveActive;
  final bool isMicRecording;
  final bool isLoading;
  final bool hasTypedText;
  final ValueChanged<String> onTextChanged;
  final VoidCallback onSend;

  const _CoachChatInputBar({
    required this.controller,
    required this.isLiveActive,
    required this.isMicRecording,
    required this.isLoading,
    required this.hasTypedText,
    required this.onTextChanged,
    required this.onSend,
  });

  @override
  Widget build(BuildContext context) {
    final tr = TranslationProvider.of(context).translations;
    final buttonColor = isMicRecording ? AppColors.error : AppColors.primary;
    final FaIconData buttonIcon = hasTypedText
        ? FontAwesomeIcons.paperPlane
        : (isMicRecording ? FontAwesomeIcons.stop : FontAwesomeIcons.microphoneLines);

    return Container(
      padding: const EdgeInsets.all(AppDimensions.paddingM),
      decoration: const BoxDecoration(
        color: AppColors.surfaceElevated,
        border: Border(
          top: BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
        ),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            Expanded(
              child: TextField(
                key: const Key('ai_coach_chat_input'),
                controller: controller,
                onChanged: onTextChanged,
                style: const TextStyle(fontSize: AppDimensions.fontM, color: AppColors.textPrimary),
                decoration: InputDecoration(
                  hintText: isMicRecording
                      ? tr.aiCoach.chatInput.listeningHint
                      : (isLiveActive ? tr.aiCoach.chatInput.liveHint : tr.aiCoach.chatInput.defaultHint),
                  fillColor: AppColors.surface,
                ),
                onSubmitted: (_) => onSend(),
              ),
            ),
            const SizedBox(width: AppDimensions.paddingS),
            IconButton(
              key: const Key('ai_coach_send_button'),
              tooltip: hasTypedText
                  ? tr.aiCoach.chatInput.sendTooltip
                  : (isMicRecording ? tr.aiCoach.chatInput.stopMicTooltip : tr.aiCoach.chatInput.startMicTooltip),
              style: IconButton.styleFrom(
                backgroundColor: buttonColor,
                padding: const EdgeInsets.all(AppDimensions.paddingM),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
              ),
              icon: FaIcon(buttonIcon, size: AppDimensions.iconM, color: isMicRecording ? AppColors.textPrimary : AppColors.background),
              onPressed: isLoading ? null : onSend,
            ),
          ],
        ),
      ),
    );
  }
}
