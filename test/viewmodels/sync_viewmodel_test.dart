// 🎯 Dart imports:
import 'dart:async';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/services/connectivity_service.dart';
import 'package:comunityfitness/services/sync_service.dart';
import 'package:comunityfitness/viewmodels/sync_viewmodel.dart';

class MockConnectivityService extends Mock implements ConnectivityService {}

class MockSyncService extends Mock implements SyncService {}

void main() {
  late MockConnectivityService mockConnectivityService;
  late MockSyncService mockSyncService;
  late StreamController<bool> connectivityController;

  setUp(() {
    mockConnectivityService = MockConnectivityService();
    mockSyncService = MockSyncService();
    connectivityController = StreamController<bool>.broadcast();

    when(() => mockConnectivityService.onConnectivityChanged).thenAnswer((_) => connectivityController.stream);
    when(() => mockConnectivityService.isOnline).thenAnswer((_) async => true);
    when(() => mockSyncService.syncAll()).thenAnswer((_) async {});
  });

  tearDown(() {
    connectivityController.close();
  });

  ProviderContainer makeContainer() {
    return ProviderContainer(
      overrides: [connectivityServiceProvider.overrideWithValue(mockConnectivityService), syncServiceProvider.overrideWithValue(mockSyncService)],
    );
  }

  test('SyncViewModel initializes with connectivity status', () async {
    final container = makeContainer();
    final subscription = container.listen(syncViewModelProvider, (prev, next) {});

    await Future<void>.delayed(const Duration(milliseconds: 5));
    expect(container.read(syncViewModelProvider).isOnline, true);

    subscription.close();
  });

  test('SyncViewModel reacts to connectivity changes (Triangulate)', () async {
    final container = makeContainer();
    final subscription = container.listen(syncViewModelProvider, (prev, next) {});

    await Future<void>.delayed(const Duration(milliseconds: 5));

    // Initial check
    expect(container.read(syncViewModelProvider).isOnline, true);

    // Transition to offline
    connectivityController.add(false);
    await Future<void>.delayed(const Duration(milliseconds: 5));
    expect(container.read(syncViewModelProvider).isOnline, false);

    // Transition back to online
    connectivityController.add(true);
    await Future<void>.delayed(const Duration(milliseconds: 5));
    expect(container.read(syncViewModelProvider).isOnline, true);

    subscription.close();
  });

  test('SyncViewModel manual sync triggers syncService.syncAll', () async {
    final container = makeContainer();
    final subscription = container.listen(syncViewModelProvider, (prev, next) {});
    final vm = container.read(syncViewModelProvider.notifier);

    await vm.sync();

    verify(() => mockSyncService.syncAll()).called(1);
    subscription.close();
  });
}
