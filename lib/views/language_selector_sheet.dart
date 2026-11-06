// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/pigeon/live_coach_audio_api.g.dart';
import 'package:comunityfitness/repositories/user_repository.dart';
import 'package:comunityfitness/theme/app_theme.dart';

class LanguageSelectorSheet extends ConsumerWidget {
  final ValueChanged<AppLocale>? onLocaleChanged;

  const LanguageSelectorSheet({super.key, this.onLocaleChanged});

  static const String metadataBoxName = UserRepository.metadataBoxName;
  static const String languageMetadataKey = UserRepository.languageMetadataKey;

  static Future<void> applyAndPersistLocale(AppLocale locale, {WidgetRef? ref}) async {
    LocaleSettings.setLocale(locale);
    try {
      if (ref != null) {
        await ref.read(userRepositoryProvider).savePreferredLocale(locale.languageCode);
      } else {
        await UserRepository.persistPreferredLocaleCode(locale.languageCode);
      }
    } catch (_) {
      await UserRepository.persistPreferredLocaleCode(locale.languageCode);
    }
    try {
      await LiveCoachAudioHostApi().setLanguage(locale.bcp47Code);
    } catch (_) {}
  }

  static Future<void> show(BuildContext context, {ValueChanged<AppLocale>? onLocaleChanged}) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.transparent,
      elevation: 0,
      builder: (ctx) => LanguageSelectorSheet(onLocaleChanged: onLocaleChanged),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentLocale = TranslationProvider.of(context).locale;
    final tr = TranslationProvider.of(context).translations;

    return Container(
      key: const Key('language_selector_sheet'),
      decoration: const BoxDecoration(
        color: AppColors.surfaceElevated,
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppDimensions.radiusBottomSheet)),
        border: Border(
          top: BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
        ),
      ),
      padding: const EdgeInsets.all(AppDimensions.paddingL),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
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
                  const FaIcon(FontAwesomeIcons.globe, size: AppDimensions.iconM, color: AppColors.primary),
                  const SizedBox(width: AppDimensions.paddingS),
                  Expanded(
                    child: Text(
                      tr.common.selectLanguage,
                      style: const TextStyle(fontSize: AppDimensions.fontL, fontWeight: FontWeight.w900, color: AppColors.textPrimary),
                    ),
                  ),
                  IconButton(
                    icon: const FaIcon(FontAwesomeIcons.xmark, size: AppDimensions.iconM, color: AppColors.textSecondary),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const SizedBox(height: AppDimensions.paddingM),
              ...AppLocale.values.map((locale) {
                final isSelected = locale == currentLocale;
                return Padding(
                  padding: const EdgeInsets.only(bottom: AppDimensions.paddingS),
                  child: InkWell(
                    key: Key('language_option_${locale.languageCode}'),
                    borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                    onTap: () async {
                      await applyAndPersistLocale(locale, ref: ref);
                      onLocaleChanged?.call(locale);
                      if (context.mounted) {
                        Navigator.pop(context);
                      }
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingM, vertical: AppDimensions.paddingM),
                      decoration: BoxDecoration(
                        color: isSelected ? AppColors.primary.withValues(alpha: AppColors.opacityLow) : AppColors.surface,
                        borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
                        border: Border.all(
                          color: isSelected ? AppColors.primary : AppColors.border,
                          width: isSelected ? AppDimensions.borderThick : AppDimensions.borderDefault,
                        ),
                      ),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: AppDimensions.paddingS, vertical: AppDimensions.paddingXXS),
                            decoration: BoxDecoration(
                              color: AppColors.surfaceElevated,
                              borderRadius: BorderRadius.circular(AppDimensions.radiusS),
                              border: Border.all(color: isSelected ? AppColors.primary : AppColors.borderSubtle, width: AppDimensions.borderThin),
                            ),
                            child: Text(
                              locale.languageCode.toUpperCase(),
                              style: TextStyle(
                                fontSize: AppDimensions.fontXS,
                                fontWeight: FontWeight.w900,
                                color: isSelected ? AppColors.primary : AppColors.textSecondary,
                              ),
                            ),
                          ),
                          const SizedBox(width: AppDimensions.paddingM),
                          Expanded(
                            child: Text(
                              locale.nativeName,
                              style: TextStyle(
                                fontSize: AppDimensions.fontM,
                                fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ),
                          if (isSelected) const FaIcon(FontAwesomeIcons.circleCheck, size: AppDimensions.iconM, color: AppColors.primary),
                        ],
                      ),
                    ),
                  ),
                );
              }),
            ],
          ),
        ),
      ),
    );
  }
}
