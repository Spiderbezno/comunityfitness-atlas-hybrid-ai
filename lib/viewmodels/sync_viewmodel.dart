// 🎯 Dart imports:
import 'dart:async';

// 📦 Package imports:
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/services/connectivity_service.dart';
import 'package:comunityfitness/services/sync_service.dart';

part 'sync_viewmodel.g.dart';

class SyncViewModelState {
  final bool isOnline;
  final bool isSyncing;
  final String? errorMessage;

  SyncViewModelState({required this.isOnline, required this.isSyncing, this.errorMessage});

  SyncViewModelState copyWith({bool? isOnline, bool? isSyncing, String? errorMessage, bool clearError = false}) {
    return SyncViewModelState(
      isOnline: isOnline ?? this.isOnline,
      isSyncing: isSyncing ?? this.isSyncing,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}

@riverpod
class SyncViewModel extends _$SyncViewModel {
  late final ConnectivityService _connectivityService;
  late final SyncService _syncService;
  StreamSubscription<bool>? _connectivitySub;
  bool _disposed = false;

  @override
  SyncViewModelState build() {
    _disposed = false;
    _connectivityService = ref.watch(connectivityServiceProvider);
    _syncService = ref.watch(syncServiceProvider);

    final initialState = SyncViewModelState(isOnline: true, isSyncing: false);

    _init();

    ref.onDispose(() {
      _disposed = true;
      _connectivitySub?.cancel();
    });

    return initialState;
  }

  Future<void> _init() async {
    final online = await _connectivityService.isOnline;
    if (_disposed) {
      return;
    }
    state = state.copyWith(isOnline: online);

    _connectivitySub = _connectivityService.onConnectivityChanged.listen((online) {
      if (!_disposed) {
        state = state.copyWith(isOnline: online);
      }
    });
  }

  Future<void> sync() async {
    if (state.isSyncing) {
      return;
    }
    state = state.copyWith(isSyncing: true, clearError: true);
    try {
      await _syncService.syncAll();
    } catch (e) {
      if (!_disposed) {
        state = state.copyWith(errorMessage: e.toString());
      }
    } finally {
      if (!_disposed) {
        state = state.copyWith(isSyncing: false);
      }
    }
  }
}
