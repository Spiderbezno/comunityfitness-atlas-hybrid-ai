// 🎯 Dart imports:
import 'dart:async';

// 📦 Package imports:
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/services/connectivity_service.dart';

class MockConnectivity extends Mock implements Connectivity {}

void main() {
  late MockConnectivity mockConnectivity;
  late ConnectivityService connectivityService;

  setUp(() {
    mockConnectivity = MockConnectivity();
    connectivityService = ConnectivityService(mockConnectivity);
  });

  group('ConnectivityService', () {
    test('isOnline returns true when connectivity is wifi or mobile', () async {
      when(() => mockConnectivity.checkConnectivity()).thenAnswer((_) async => [ConnectivityResult.wifi]);

      final result = await connectivityService.isOnline;

      expect(result, isTrue);
    });

    test('isOnline returns true when connectivity is mobile or vpn', () async {
      when(() => mockConnectivity.checkConnectivity()).thenAnswer((_) async => [ConnectivityResult.mobile, ConnectivityResult.vpn]);

      final result = await connectivityService.isOnline;

      expect(result, isTrue);
    });

    test('isOnline returns false when connectivity is none', () async {
      when(() => mockConnectivity.checkConnectivity()).thenAnswer((_) async => [ConnectivityResult.none]);

      final result = await connectivityService.isOnline;

      expect(result, isFalse);
    });

    test('onConnectivityChanged emits true/false based on connection updates', () async {
      final controller = StreamController<List<ConnectivityResult>>();
      when(() => mockConnectivity.onConnectivityChanged).thenAnswer((_) => controller.stream);

      final events = <bool>[];
      final subscription = connectivityService.onConnectivityChanged.listen(events.add);

      controller.add([ConnectivityResult.wifi]);
      controller.add([ConnectivityResult.none]);
      controller.add([ConnectivityResult.ethernet]);

      await Future<void>.delayed(Duration.zero);

      expect(events, equals([true, false, true]));

      await subscription.cancel();
      await controller.close();
    });
  });
}
