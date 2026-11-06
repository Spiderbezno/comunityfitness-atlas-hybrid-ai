// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// 🌎 Project imports:
import 'package:comunityfitness/theme/app_theme.dart';

/// Platform-adaptive navigation back button using FontAwesome icons (`FaIcon`)
/// and design tokens (`AppColors`, `AppDimensions`).
///
/// Renders `FontAwesomeIcons.chevronLeft` on iOS/macOS and
/// `FontAwesomeIcons.arrowLeft` on Android/other platforms.
class AppBackButton extends StatelessWidget {
  final Color color;
  final double size;
  final VoidCallback? onPressed;

  const AppBackButton({super.key, this.color = AppColors.textPrimary, this.size = AppDimensions.iconL, this.onPressed});

  /// Returns an [AppBackButton] only when the current [Navigator] can pop,
  /// or `null` when on a root screen.
  static Widget? maybeLeading(
    BuildContext context, {
    Color color = AppColors.textPrimary,
    double size = AppDimensions.iconL,
    VoidCallback? onPressed,
  }) {
    if (!Navigator.of(context).canPop()) {
      return null;
    }
    return AppBackButton(color: color, size: size, onPressed: onPressed);
  }

  @override
  Widget build(BuildContext context) {
    final platform = Theme.of(context).platform;
    final isCupertinoStyle = platform == TargetPlatform.iOS || platform == TargetPlatform.macOS;
    final iconData = isCupertinoStyle ? FontAwesomeIcons.chevronLeft : FontAwesomeIcons.arrowLeft;

    return IconButton(
      icon: FaIcon(iconData, color: color, size: size),
      tooltip: MaterialLocalizations.of(context).backButtonTooltip,
      onPressed: onPressed ?? () => Navigator.of(context).maybePop(),
    );
  }
}
