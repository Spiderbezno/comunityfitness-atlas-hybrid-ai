// ignore_for_file: prefer_initializing_formals

// 📦 Package imports:
import 'package:hive_ce/hive.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/services/sync_service.dart';

part 'session_repository.g.dart';

@riverpod
SessionRepository sessionRepository(Ref ref) {
  final box = Hive.box<WorkoutSession>('sessions');
  final sync = ref.read(syncServiceProvider);
  return SessionRepository(sessionBox: box, syncService: sync);
}

class SessionRepository {
  final Box<WorkoutSession> _sessionBox;
  final SyncService _syncService;

  SessionRepository({required Box<WorkoutSession> sessionBox, required SyncService syncService})
    : _sessionBox = sessionBox,
      _syncService = syncService;

  List<WorkoutSession> getSessions() {
    return _sessionBox.values.where((s) => !s.isDeleted).toList();
  }

  WorkoutSession? getSession(String id) {
    final session = _sessionBox.get(id);
    if (session == null || session.isDeleted) {
      return null;
    }
    return session;
  }

  Future<void> saveSession(WorkoutSession session) async {
    final updated = session.copyWith(synced: false, updatedAt: DateTime.now());
    await _sessionBox.put(updated.id, updated);
    try {
      await _syncService.syncAll();
    } catch (_) {}
  }

  Future<void> saveSessionsBatch(List<WorkoutSession> sessions) async {
    if (sessions.isEmpty) {
      return;
    }
    final now = DateTime.now();
    for (final session in sessions) {
      final updated = session.copyWith(synced: false, updatedAt: now);
      await _sessionBox.put(updated.id, updated);
    }
    try {
      await _syncService.syncAll();
    } catch (_) {}
  }

  Future<void> deleteSession(String id) async {
    final session = _sessionBox.get(id);
    if (session != null) {
      final updated = session.copyWith(isDeleted: true, synced: false, updatedAt: DateTime.now());
      await _sessionBox.put(id, updated);
      try {
        await _syncService.syncAll();
      } catch (_) {}
    }
  }

  Stream<List<WorkoutSession>> watchSessions() async* {
    yield getSessions();
    await for (final _ in _sessionBox.watch()) {
      yield getSessions();
    }
  }
}
