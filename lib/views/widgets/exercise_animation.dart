// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:rive/rive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/theme/app_theme.dart';

/// Plays a bundled Rive exercise demonstration from [assetPath].
///
/// The [FileLoader] is created once per asset and disposed with the widget, so
/// parent rebuilds never reload the file. Shows a spinner while loading and a
/// FontAwesome fallback when the asset cannot be loaded.
class ExerciseAnimation extends StatefulWidget {
  const ExerciseAnimation({super.key, required this.assetPath});

  final String assetPath;

  @override
  State<ExerciseAnimation> createState() => _ExerciseAnimationState();
}

class _ExerciseAnimationState extends State<ExerciseAnimation> {
  late FileLoader _fileLoader = _createLoader();

  FileLoader _createLoader() => FileLoader.fromAsset(widget.assetPath, riveFactory: Factory.flutter);

  @override
  void didUpdateWidget(ExerciseAnimation oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.assetPath != oldWidget.assetPath) {
      final previous = _fileLoader;
      _fileLoader = _createLoader();
      // Dispose after the frame so the builder has switched to the new loader.
      WidgetsBinding.instance.addPostFrameCallback((_) => previous.dispose());
    }
  }

  @override
  void dispose() {
    _fileLoader.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return RiveWidgetBuilder(
      // Remount on asset change so the old controller is disposed before the
      // previous loader (and its file) is released post-frame.
      key: ValueKey(widget.assetPath),
      fileLoader: _fileLoader,
      builder: (context, state) => switch (state) {
        RiveLoading() => const Center(child: CircularProgressIndicator(color: AppColors.primary)),
        RiveFailed() => const ExerciseAnimationFallback(),
        RiveLoaded() => RiveWidget(controller: state.controller, fit: Fit.contain),
      },
    );
  }
}

/// Fallback shown when an exercise demonstration cannot be rendered.
class ExerciseAnimationFallback extends StatelessWidget {
  const ExerciseAnimationFallback({super.key, this.message = 'Demonstration animation unavailable'});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const FaIcon(FontAwesomeIcons.circleExclamation, color: AppColors.warning, size: AppDimensions.iconXL),
          const SizedBox(height: AppDimensions.paddingS),
          Text(
            message,
            style: const TextStyle(color: AppColors.textSecondary, fontSize: AppDimensions.fontS),
          ),
        ],
      ),
    );
  }
}
