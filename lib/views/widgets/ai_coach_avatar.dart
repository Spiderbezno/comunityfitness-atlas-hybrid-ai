// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:rive/rive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/theme/app_theme.dart';

/// Visual operating mode for the 3D Biomech Gyro-Core AI Coach Rive avatar.
enum AiCoachAvatarMode { idle, thinking, speaking, listening }

/// Renders the 60 FPS 3D Biomech Gyro-Core Rive avatar (`assets/animations/ai_coach_avatar.riv`)
/// with a mode-reactive circular telemetry frame and a headless-test-safe fallback.
class AiCoachAvatar extends StatefulWidget {
  const AiCoachAvatar({
    super.key,
    this.size = AppDimensions.aiLiveOrbSize,
    this.mode = AiCoachAvatarMode.idle,
    this.assetPath = 'assets/animations/ai_coach_avatar.riv',
  });

  final double size;
  final AiCoachAvatarMode mode;
  final String assetPath;

  @override
  State<AiCoachAvatar> createState() => _AiCoachAvatarState();
}

class _AiCoachAvatarState extends State<AiCoachAvatar> {
  FileLoader? _fileLoader;

  FileLoader? _createLoader() {
    try {
      if (!RiveNative.isInitialized) {
        return null;
      }
      return FileLoader.fromAsset(widget.assetPath, riveFactory: Factory.flutter);
    } on Object {
      return null;
    }
  }

  @override
  void initState() {
    super.initState();
    _fileLoader = _createLoader();
  }

  @override
  void didUpdateWidget(AiCoachAvatar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.assetPath != oldWidget.assetPath) {
      final previous = _fileLoader;
      _fileLoader = _createLoader();
      if (previous != null) {
        WidgetsBinding.instance.addPostFrameCallback((_) => previous.dispose());
      }
    }
  }

  @override
  void dispose() {
    _fileLoader?.dispose();
    super.dispose();
  }

  Color _accentColorForMode(AiCoachAvatarMode mode) {
    return switch (mode) {
      AiCoachAvatarMode.listening => AppColors.error,
      AiCoachAvatarMode.thinking => AppColors.secondary,
      AiCoachAvatarMode.speaking => AppColors.primary,
      AiCoachAvatarMode.idle => AppColors.primary,
    };
  }

  bool get _hasActiveGlow =>
      widget.mode == AiCoachAvatarMode.thinking || widget.mode == AiCoachAvatarMode.speaking || widget.mode == AiCoachAvatarMode.listening;

  @override
  Widget build(BuildContext context) {
    final accentColor = _accentColorForMode(widget.mode);
    final loader = _fileLoader;

    return AnimatedContainer(
      duration: AppDimensions.animDurationFast,
      width: widget.size,
      height: widget.size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: AppColors.surface,
        border: Border.all(
          color: accentColor.withValues(alpha: _hasActiveGlow ? AppColors.opacityHigh : AppColors.opacityMedium),
          width: _hasActiveGlow ? AppDimensions.borderThick : AppDimensions.borderDefault,
        ),
        boxShadow: _hasActiveGlow
            ? [
                BoxShadow(
                  color: accentColor.withValues(alpha: AppColors.opacityMedium),
                  blurRadius: AppDimensions.shadowBlurM,
                ),
              ]
            : const [],
      ),
      child: ClipOval(
        child: loader == null
            ? _GyroCoreFallback(mode: widget.mode, accentColor: accentColor)
            : RiveWidgetBuilder(
                key: ValueKey(widget.assetPath),
                fileLoader: loader,
                builder: (context, state) => switch (state) {
                  RiveLoading() => _GyroCoreFallback(mode: widget.mode, accentColor: accentColor),
                  RiveFailed() => _GyroCoreFallback(mode: widget.mode, accentColor: accentColor),
                  RiveLoaded() => RiveWidget(controller: state.controller, fit: Fit.cover),
                },
              ),
      ),
    );
  }
}

class _GyroCoreFallback extends StatelessWidget {
  const _GyroCoreFallback({required this.mode, required this.accentColor});

  final AiCoachAvatarMode mode;
  final Color accentColor;

  FaIconData _iconForMode(AiCoachAvatarMode mode) {
    return switch (mode) {
      AiCoachAvatarMode.listening => FontAwesomeIcons.microphoneLines,
      AiCoachAvatarMode.thinking => FontAwesomeIcons.atom,
      AiCoachAvatarMode.speaking => FontAwesomeIcons.bolt,
      AiCoachAvatarMode.idle => FontAwesomeIcons.atom,
    };
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            accentColor.withValues(alpha: AppColors.opacityMedium),
            AppColors.background,
          ],
        ),
      ),
      child: Center(
        child: FaIcon(_iconForMode(mode), size: AppDimensions.iconS, color: accentColor),
      ),
    );
  }
}
