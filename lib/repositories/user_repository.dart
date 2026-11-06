// 📦 Package imports:
import 'package:hive_ce/hive.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/user.dart';

part 'user_repository.g.dart';

@riverpod
UserRepository userRepository(Ref ref) {
  final box = Hive.box<User>('users');
  return UserRepository(userBox: box);
}

class UserRepository {
  static const String metadataBoxName = 'sync_metadata';
  static const String languageMetadataKey = 'preferred_locale';

  final Box<User> _userBox;

  UserRepository({required this._userBox});

  User? getUser(String id) {
    return _userBox.get(id);
  }

  User? getCurrentUser() {
    try {
      if (_userBox.values.isNotEmpty) {
        return _userBox.values.first;
      }
    } catch (_) {}
    return null;
  }

  Future<void> saveUser(User user) async {
    final updated = user.copyWith(synced: false, updatedAt: DateTime.now());
    await _userBox.put(updated.id, updated);
  }

  Future<void> savePreferredLocale(String rawCode) async {
    await persistPreferredLocaleCode(rawCode);
  }

  static String? readSavedLocaleFromOpenBox() {
    try {
      if (Hive.isBoxOpen(metadataBoxName)) {
        final box = Hive.box<dynamic>(metadataBoxName);
        final raw = box.get(languageMetadataKey) ?? box.get('app_language_code');
        return raw?.toString();
      }
    } catch (_) {}
    return null;
  }

  static Future<void> persistPreferredLocaleCode(String rawCode) async {
    try {
      if (Hive.isBoxOpen(metadataBoxName)) {
        final box = Hive.box<dynamic>(metadataBoxName);
        await box.put(languageMetadataKey, rawCode);
      }
    } catch (_) {}
  }
}
