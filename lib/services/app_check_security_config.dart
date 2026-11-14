// 📦 Package imports:
import 'package:firebase_app_check/firebase_app_check.dart';

/// Security policy helpers for hackathon and production Firebase App Check activation.
abstract final class AppCheckSecurityConfig {
  static final RegExp _uuidPattern = RegExp(
    r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
  );

  /// Returns whether [token] is a syntactically valid UUID debug token.
  static bool isValidDebugTokenUuid(String token) {
    return _uuidPattern.hasMatch(token.trim());
  }

  static String? _normalizedDebugToken(String token) {
    final trimmed = token.trim();
    return isValidDebugTokenUuid(trimmed) ? trimmed : null;
  }

  /// Resolves the Web App Check provider, honoring a valid judge UUID token in release builds
  /// while preventing release mode from auto-minting random unvalidated debug tokens.
  static WebProvider? resolveWebProvider({
    required bool isDebugMode,
    required String webDebugToken,
    String recaptchaSiteKey = '',
  }) {
    final trimmedRecaptcha = recaptchaSiteKey.trim();
    final hasValidUuid = isValidDebugTokenUuid(webDebugToken);

    if (trimmedRecaptcha.isNotEmpty && !isDebugMode && !hasValidUuid) {
      return ReCaptchaV3Provider(trimmedRecaptcha);
    }
    if (isDebugMode) {
      return WebDebugProvider(debugToken: _normalizedDebugToken(webDebugToken));
    }
    if (hasValidUuid) {
      return WebDebugProvider(debugToken: webDebugToken.trim());
    }
    return null;
  }

  /// Resolves the Apple App Check provider, falling back to App Attest / DeviceCheck in release
  /// unless an explicit valid UUID debug token is supplied for judge verification.
  static AppleAppCheckProvider resolveAppleProvider({
    required bool isDebugMode,
    required String appleDebugToken,
  }) {
    if (isDebugMode || isValidDebugTokenUuid(appleDebugToken)) {
      return AppleDebugProvider(debugToken: _normalizedDebugToken(appleDebugToken));
    }
    return const AppleAppAttestWithDeviceCheckFallbackProvider();
  }

  /// Resolves the Android App Check provider, falling back to Play Integrity in release
  /// unless an explicit valid UUID debug token is supplied for judge verification.
  static AndroidAppCheckProvider resolveAndroidProvider({
    required bool isDebugMode,
    required String androidDebugToken,
  }) {
    if (isDebugMode || isValidDebugTokenUuid(androidDebugToken)) {
      return AndroidDebugProvider(debugToken: _normalizedDebugToken(androidDebugToken));
    }
    return const AndroidPlayIntegrityProvider();
  }
}
