// ignore_for_file: prefer_initializing_formals

// 📦 Package imports:
import 'package:hive_ce/hive.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/services/sync_service.dart';

part 'routine_repository.g.dart';

@riverpod
RoutineRepository routineRepository(Ref ref) {
  final box = Hive.box<Routine>('routines');
  final sync = ref.read(syncServiceProvider);
  return RoutineRepository(routineBox: box, syncService: sync);
}

class RoutineRepository {
  final Box<Routine> _routineBox;
  final SyncService _syncService;

  RoutineRepository({required Box<Routine> routineBox, required SyncService syncService}) : _routineBox = routineBox, _syncService = syncService;

  List<Routine> getRoutines() {
    return _routineBox.values.where((r) => !r.isDeleted).toList();
  }

  Routine? getRoutine(String id) {
    final routine = _routineBox.get(id);
    if (routine == null || routine.isDeleted) {
      return null;
    }
    return routine;
  }

  Future<void> saveRoutine(Routine routine) async {
    final updated = routine.copyWith(synced: false, updatedAt: DateTime.now());
    await _routineBox.put(updated.id, updated);
    try {
      await _syncService.syncAll();
    } catch (_) {}
  }

  Future<void> saveRoutinesBatch(List<Routine> routines) async {
    if (routines.isEmpty) {
      return;
    }
    final now = DateTime.now();
    for (final routine in routines) {
      final updated = routine.copyWith(synced: false, updatedAt: now);
      await _routineBox.put(updated.id, updated);
    }
    try {
      await _syncService.syncAll();
    } catch (_) {}
  }

  Future<void> deleteRoutine(String id) async {
    final routine = _routineBox.get(id);
    if (routine != null) {
      final updated = routine.copyWith(isDeleted: true, synced: false, updatedAt: DateTime.now());
      await _routineBox.put(id, updated);
      try {
        await _syncService.syncAll();
      } catch (_) {}
    }
  }

  Stream<List<Routine>> watchRoutines() async* {
    yield getRoutines();
    await for (final _ in _routineBox.watch()) {
      yield getRoutines();
    }
  }
}
