// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';
import 'package:rive/rive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/views/widgets/exercise_animation.dart';

void main() {
  setUpAll(() async {
    await RiveNative.init();
  });

  Widget host(String asset) => MaterialApp(
    home: Scaffold(
      body: SizedBox(width: 320, height: 200, child: ExerciseAnimation(assetPath: asset)),
    ),
  );

  testWidgets('renders, swaps asset and disposes without errors', (tester) async {
    await tester.pumpWidget(host('assets/animations/ab_wheel_rollout.riv'));
    expect(find.byType(ExerciseAnimation), findsOneWidget);
    await tester.pump(const Duration(milliseconds: 100));

    await tester.pumpWidget(host('assets/animations/arnold_press.riv'));
    expect(find.byType(ExerciseAnimation), findsOneWidget);
    await tester.pump(const Duration(milliseconds: 100));

    await tester.pumpWidget(host('assets/animations/push_up.riv'));
    await tester.pump(const Duration(milliseconds: 100));

    await tester.pumpWidget(const SizedBox.shrink());
    expect(find.byType(ExerciseAnimation), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('fallback shows the FontAwesome warning and message', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: ExerciseAnimationFallback())));
    expect(find.text('Demonstration animation unavailable'), findsOneWidget);
  });
}
