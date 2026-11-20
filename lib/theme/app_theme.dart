// 🐦 Flutter imports:
import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  // Matte Carbon / Asphalt Base
  static const Color background = Color(0xFF0E1015);
  static const Color surface = Color(0xFF161920);
  static const Color surfaceElevated = Color(0xFF1F242D);

  // Athletic Energy Anchor & Secondary Accents
  static const Color primary = Color(0xFFFF5400); // Ember Orange
  static const Color primaryDark = Color(0xFFD94100);
  static const Color secondary = Color(0xFF38BDF8); // Sky Steel (analytics & tags)

  // High-Contrast Editorial Typography
  static const Color textPrimary = Color(0xFFF8FAFC);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF8294AC);

  // Crisp Structural Borders
  static const Color border = Color(0xFF262B35);
  static const Color borderSubtle = Color(0xFF1E232B);

  // Status & Utility Colors
  static const Color success = Color(0xFF10B981);
  static const Color warning = Color(0xFFF59E0B);
  static const Color error = Color(0xFFEF4444);

  static const Color transparent = Colors.transparent;
  static const Color white = Color(0xFFFFFFFF);

  // Opacities / Alphas
  static const double opacityLow = 0.15;
  static const double opacityMedium = 0.3;
  static const double opacityHigh = 0.85;
}

class AppDimensions {
  AppDimensions._();

  // Spacing & Padding
  static const double paddingXXS = 2.0;
  static const double paddingXS = 4.0;
  static const double paddingS = 8.0;
  static const double paddingM = 16.0;
  static const double paddingL = 24.0;
  static const double paddingXL = 32.0;

  // Border Radii (Hierarchical)
  static const double radiusBadge = 4.0;
  static const double radiusXS = 4.0;
  static const double radiusS = 8.0;
  static const double radiusCard = 16.0;
  static const double radiusM = 12.0;
  static const double radiusL = 16.0;
  static const double radiusXL = 20.0;
  static const double radiusBottomSheet = 20.0;
  static const double radiusPill = 999.0;

  // Font Sizes (Accessible Material 3 / HIG Scale)
  static const double fontBadge = 10.0;
  static const double fontXXS = 12.0;
  static const double fontXS = 12.5;
  static const double fontS = 14.0;
  static const double fontM = 15.0;
  static const double fontL = 17.0;
  static const double fontXL = 20.0;
  static const double fontXXL = 24.0;
  static const double fontDisplay = 32.0;
  static const double fontHero = 40.0;

  // Icon Sizes
  static const double iconXS = 10.0;
  static const double iconS = 12.0;
  static const double iconSM = 14.0;
  static const double iconM = 16.0;
  static const double iconL = 20.0;
  static const double iconXL = 24.0;
  static const double iconXXL = 36.0;
  static const double iconHuge = 48.0;

  // Component Sizes & Structural Borders
  static const double borderThin = 0.5;
  static const double borderDefault = 1.0;
  static const double borderThick = 1.5;
  static const double borderHighlight = 2.0;
  static const double spinnerSize = 18.0;
  static const double dotSize = 8.0;
  static const double dragHandleWidth = 40.0;
  static const double dragHandleHeight = 4.0;
  static const double animationPlayerHeight = 200.0;
  static const double filterRowHeight = 48.0;
  static const double appBarExpandedHeight = 140.0;
  static const double appBarSelectionLeadingPadding = 56.0;
  static const double sliderLabelWidth = 80.0;
  static const double emptyStateVerticalPadding = 40.0;
  static const double thumbnailSize = 48.0;
  static const int thumbnailCacheSize = 144; // thumbnailSize at 3x density
  static const double exerciseCardHeight = 132.0;
  static const double restTimerRingSize = 44.0;
  static const double setCheckSize = 44.0;
  static const double setCheckAnimSize = 64.0;
  static const double activeHudBottomPadding = 120.0;
  static const double aiSheetHeightFactor = 0.88;
  static const double aiLiveOrbSize = 44.0;
  static const double aiHeroAvatarSize = 96.0;
  static const double aiLiveHeroAvatarSize = 112.0;
  static const double aiSheetAvatarSize = 72.0;
  static const double aiMessageAvatarSize = 48.0;
  static const double aiChipRowHeight = 40.0;
  static const double aiCardRadius = 16.0;
  static const double aiMessageBubbleRadius = 18.0;
  static const double catalogCacheExtent = 1200.0;
  static const double featureTileMinHeight = 140.0;
  static const double webMobileFrameMaxWidth = 480.0;
  static const double strokeWidthThin = 2.0;
  static const double cardElevation = 2.0;

  // Routine Editor Slider Bounds
  static const double sliderSetsMin = 1.0;
  static const double sliderSetsMax = 10.0;
  static const int sliderSetsDivisions = 9;
  static const double sliderRepsMin = 0.0;
  static const double sliderRepsMax = 50.0;
  static const int sliderRepsDivisions = 50;
  static const double sliderWeightMin = 0.0;
  static const double sliderWeightMax = 200.0;
  static const int sliderWeightDivisions = 80;
  static const double sliderRestMin = 0.0;
  static const double sliderRestMax = 300.0;
  static const int sliderRestDivisions = 30;

  // Shadows
  static const double shadowBlurL = 16.0;
  static const Offset shadowOffsetL = Offset(0, 8);
  static const double shadowBlurM = 12.0;
  static const Offset shadowOffsetM = Offset(0, 6);

  // Animations (Durations)
  static const Duration animDurationFast = Duration(milliseconds: 300);
  static const Duration animDurationMedium = Duration(milliseconds: 400);
  static const Duration animDurationSlow = Duration(milliseconds: 500);
  static const Duration animDurationVerySlow = Duration(milliseconds: 600);

  /// Matches the rest timer tick so the ring drains continuously between seconds.
  static const Duration restTimerTickDuration = Duration(seconds: 1);
}

class AppTheme {
  AppTheme._();

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AppColors.background,
      cardTheme: CardThemeData(
        color: AppColors.surfaceElevated,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
          side: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
        ),
      ),
      colorScheme: const ColorScheme.dark(
        primary: AppColors.primary,
        primaryContainer: AppColors.primaryDark,
        secondary: AppColors.secondary,
        surface: AppColors.surface,
        error: AppColors.error,
        onPrimary: AppColors.background,
        onSecondary: AppColors.background,
        onSurface: AppColors.textPrimary,
        onError: AppColors.textPrimary,
      ),
      useMaterial3: true,
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.background,
        elevation: 0,
        scrolledUnderElevation: 0,
        iconTheme: IconThemeData(color: AppColors.textPrimary),
        titleTextStyle: TextStyle(color: AppColors.textPrimary, fontSize: AppDimensions.fontXL, fontWeight: FontWeight.w900, letterSpacing: 0.5),
      ),
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: AppColors.surfaceElevated,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(AppDimensions.radiusBottomSheet))),
      ),
      dividerTheme: const DividerThemeData(color: AppColors.border, thickness: AppDimensions.borderDefault, space: AppDimensions.paddingM),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surfaceElevated,
        contentPadding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM, vertical: AppDimensions.paddingS),
        hintStyle: const TextStyle(color: AppColors.textMuted),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
          borderSide: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
          borderSide: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
          borderSide: const BorderSide(color: AppColors.primary, width: AppDimensions.borderThick),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: AppColors.surface,
        selectedColor: AppColors.primary.withValues(alpha: AppColors.opacityLow),
        secondarySelectedColor: AppColors.secondary.withValues(alpha: AppColors.opacityLow),
        labelStyle: const TextStyle(color: AppColors.textPrimary, fontSize: AppDimensions.fontS),
        secondaryLabelStyle: const TextStyle(color: AppColors.textPrimary, fontSize: AppDimensions.fontS),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDimensions.radiusPill),
          side: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: AppColors.background,
          elevation: 0,
          textStyle: const TextStyle(fontSize: AppDimensions.fontM, fontWeight: FontWeight.bold, letterSpacing: 0.5),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.textPrimary,
          side: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
          textStyle: const TextStyle(fontSize: AppDimensions.fontM, fontWeight: FontWeight.w600),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
        ),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.background,
        elevation: AppDimensions.cardElevation,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
      ),
    );
  }
}
