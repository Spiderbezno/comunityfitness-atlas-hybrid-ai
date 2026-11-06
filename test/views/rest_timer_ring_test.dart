// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';
import 'package:rive/rive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/views/widgets/rest_timer_ring.dart';

void main() {
  setUpAll(() async {
    await RiveNative.init();
  });

  Widget host(double progress) => MaterialApp(
    home: Scaffold(
      body: Center(child: RestTimerRing(progress: progress)),
    ),
  );

  testWidgets('updates progress and disposes without errors', (tester) async {
    await tester.pumpWidget(host(1));
    expect(find.byType(RestTimerRing), findsOneWidget);

    await tester.pumpWidget(host(0.5));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpWidget(host(0.25));
    await tester.pump(const Duration(seconds: 1));

    await tester.pumpWidget(const SizedBox.shrink());
    expect(find.byType(RestTimerRing), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
