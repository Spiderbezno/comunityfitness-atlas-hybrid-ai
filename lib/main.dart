// 🐦 Flutter imports:
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:firebase_app_check/firebase_app_check.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:rive/rive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/firebase_options.dart';
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/pigeon/live_coach_audio_api.g.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/repositories/user_repository.dart';
import 'package:comunityfitness/services/app_check_security_config.dart';
import 'package:comunityfitness/services/hive_service.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/views/dashboard_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await RiveNative.init();

  // Initialize Hive
  final hiveServiceInstance = HiveService();
  await hiveServiceInstance.init();

  // Open all Hive boxes required by repositories
  await hiveServiceInstance.openUserBox();
  final exerciseBox = await hiveServiceInstance.openExerciseBox();
  await hiveServiceInstance.openRoutineBox();
  await hiveServiceInstance.openSessionBox();
  await hiveServiceInstance.openMetadataBox();

  // Restore saved language preference or detect device language (defaulting to Español if matched)
  final savedLang = UserRepository.readSavedLocaleFromOpenBox();
  final activeLocale = (savedLang != null && savedLang.trim().isNotEmpty) ? LocaleSettings.setLocaleRaw(savedLang) : LocaleSettings.useDeviceLocale();
  try {
    await LiveCoachAudioHostApi().setLanguage(activeLocale.bcp47Code);
  } catch (_) {}

  // Seed static exercises catalog
  final exerciseRepo = ExerciseRepository(exerciseBox: exerciseBox);
  await exerciseRepo.seedIfNeeded();

  // Initialize Firebase
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  // Activate Firebase App Check for Firebase AI Logic attestation
  const appleDebugToken = String.fromEnvironment(
    'FIREBASE_APP_CHECK_IOS_DEBUG_TOKEN',
    defaultValue: String.fromEnvironment('APPLE_APP_CHECK_DEBUG_TOKEN'),
  );
  const androidDebugToken = String.fromEnvironment(
    'FIREBASE_APP_CHECK_ANDROID_DEBUG_TOKEN',
    defaultValue: String.fromEnvironment('ANDROID_APP_CHECK_DEBUG_TOKEN'),
  );
  const webDebugToken = String.fromEnvironment(
    'FIREBASE_APP_CHECK_WEB_DEBUG_TOKEN',
    defaultValue: String.fromEnvironment('WEB_APP_CHECK_DEBUG_TOKEN', defaultValue: String.fromEnvironment('FIREBASE_APP_CHECK_ANDROID_DEBUG_TOKEN')),
  );
  const recaptchaSiteKey = String.fromEnvironment('FIREBASE_APP_CHECK_RECAPTCHA_SITE_KEY');
  try {
    await FirebaseAppCheck.instance.activate(
      providerWeb: AppCheckSecurityConfig.resolveWebProvider(
        isDebugMode: kDebugMode,
        webDebugToken: webDebugToken,
        recaptchaSiteKey: recaptchaSiteKey,
      ),
      providerApple: AppCheckSecurityConfig.resolveAppleProvider(
        isDebugMode: kDebugMode,
        appleDebugToken: appleDebugToken,
      ),
      providerAndroid: AppCheckSecurityConfig.resolveAndroidProvider(
        isDebugMode: kDebugMode,
        androidDebugToken: androidDebugToken,
      ),
    );
  } catch (e) {
    debugPrint('Firebase App Check activation skipped: $e');
  }

  // Ensure Firebase Auth session for Firebase AI Logic requests
  try {
    if (FirebaseAuth.instance.currentUser == null) {
      await FirebaseAuth.instance.signInAnonymously();
    }
  } catch (e) {
    debugPrint('Firebase Auth anonymous sign-in skipped: $e');
  }

  runApp(TranslationProvider(child: MyApp(hiveService: hiveServiceInstance)));
}

class MyApp extends StatelessWidget {
  final HiveService? hiveService;

  const MyApp({super.key, this.hiveService});

  @override
  Widget build(BuildContext context) {
    final localeData = TranslationProvider.of(context);
    return ProviderScope(
      overrides: [if (hiveService != null) hiveServiceProvider.overrideWithValue(hiveService!)],
      child: ColoredBox(
        color: AppColors.background,
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: AppDimensions.webMobileFrameMaxWidth),
            child: DecoratedBox(
              decoration: const BoxDecoration(
                border: Border.symmetric(
                  vertical: BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
                ),
              ),
              position: DecorationPosition.foreground,
              child: ClipRect(
                child: MaterialApp(
                  title: 'CommunityFitness',
                  debugShowCheckedModeBanner: false,
                  locale: localeData.flutterLocale,
                  supportedLocales: AppLocaleUtils.supportedLocales,
                  localizationsDelegates: GlobalMaterialLocalizations.delegates,
                  theme: AppTheme.darkTheme,
                  home: const DashboardScreen(),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
