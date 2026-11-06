// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:rive/rive.dart' hide Animation;

// 🌎 Project imports:
import 'package:comunityfitness/theme/app_theme.dart';

/// Rive rest timer ring whose drain, colour shift and hourglass sand follow
/// [progress] (1 = full rest left, 0 = rest finished).
///
/// The value is written to the `progress` number of the artboard's
/// `RestTimerVM` view model (auto-bound default instance). Changes are tweened
/// over one timer tick so the ring drains smoothly instead of jumping each
/// second. Falls back to a stopwatch icon while loading or on failure.
class RestTimerRing extends StatefulWidget {
  const RestTimerRing({super.key, required this.progress});

  static const String assetPath = 'assets/animations/rest_timer.riv';
  static const String progressPropertyName = 'progress';

  /// Remaining rest fraction in the range 0..1.
  final double progress;

  @override
  State<RestTimerRing> createState() => _RestTimerRingState();
}

class _RestTimerRingState extends State<RestTimerRing> with SingleTickerProviderStateMixin {
  FileLoader? _fileLoader;
  late final AnimationController _controller = AnimationController(vsync: this, duration: AppDimensions.restTimerTickDuration)
    ..addListener(_pushProgress);
  late Animation<double> _progress = AlwaysStoppedAnimation(widget.progress);
  ViewModelInstanceNumber? _progressProperty;

  static FileLoader? _createLoader() {
    try {
      if (!RiveNative.isInitialized) {
        return null;
      }
      return FileLoader.fromAsset(RestTimerRing.assetPath, riveFactory: Factory.flutter);
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
  void didUpdateWidget(RestTimerRing oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.progress != oldWidget.progress) {
      _progress = Tween<double>(begin: _progress.value, end: widget.progress).animate(_controller);
      _controller.forward(from: 0);
    }
  }

  void _onLoaded(RiveLoaded state) {
    _progressProperty?.dispose();
    _progressProperty = state.viewModelInstance?.number(RestTimerRing.progressPropertyName);
    _pushProgress();
  }

  void _pushProgress() {
    _progressProperty?.value = _progress.value;
  }

  @override
  void dispose() {
    _controller.dispose();
    _progressProperty?.dispose();
    _progressProperty = null;
    _fileLoader?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final loader = _fileLoader;
    return SizedBox.square(
      dimension: AppDimensions.restTimerRingSize,
      child: loader == null
          ? const Center(
              child: FaIcon(FontAwesomeIcons.stopwatch, size: AppDimensions.iconL, color: AppColors.primary),
            )
          : RiveWidgetBuilder(
              fileLoader: loader,
              dataBind: DataBind.auto(),
              onLoaded: _onLoaded,
              builder: (context, rState) => switch (rState) {
                RiveLoaded() => RiveWidget(controller: rState.controller, fit: Fit.contain),
                _ => const Center(
                  child: FaIcon(FontAwesomeIcons.stopwatch, size: AppDimensions.iconL, color: AppColors.primary),
                ),
              },
            ),
    );
  }
}
