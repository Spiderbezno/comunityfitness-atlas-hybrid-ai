// 📦 Package imports:
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'connectivity_service.g.dart';

@riverpod
ConnectivityService connectivityService(Ref ref) {
  return ConnectivityService();
}

class ConnectivityService {
  final Connectivity _connectivity;

  ConnectivityService([Connectivity? connectivity]) : _connectivity = connectivity ?? Connectivity();

  Stream<bool> get onConnectivityChanged {
    return _connectivity.onConnectivityChanged.map((results) => !results.contains(ConnectivityResult.none));
  }

  Future<bool> get isOnline async {
    final results = await _connectivity.checkConnectivity();
    return !results.contains(ConnectivityResult.none);
  }
}
