// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// 🌎 Project imports:
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/views/widgets/app_back_button.dart';

void main() {
  testWidgets('AppBackButton renders FontAwesomeIcons.chevronLeft on iOS and pops route when tapped', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData(platform: TargetPlatform.iOS),
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: ElevatedButton(
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => Scaffold(
                        appBar: AppBar(leading: const AppBackButton()),
                        body: const Text('Child Page'),
                      ),
                    ),
                  );
                },
                child: const Text('Push'),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Push'));
    await tester.pumpAndSettle();

    expect(find.text('Child Page'), findsOneWidget);
    final faIcon = tester.widget<FaIcon>(find.byType(FaIcon));
    expect(faIcon.icon, FontAwesomeIcons.chevronLeft.data);
    expect(faIcon.size, AppDimensions.iconL);

    final iconButton = tester.widget<IconButton>(find.byType(IconButton));
    expect(iconButton.tooltip, 'Back');

    await tester.tap(find.byType(AppBackButton));
    await tester.pumpAndSettle();

    expect(find.text('Child Page'), findsNothing);
  });

  testWidgets('AppBackButton renders FontAwesomeIcons.arrowLeft on Android', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData(platform: TargetPlatform.android),
        home: Scaffold(appBar: AppBar(leading: const AppBackButton())),
      ),
    );

    final faIcon = tester.widget<FaIcon>(find.byType(FaIcon));
    expect(faIcon.icon, FontAwesomeIcons.arrowLeft.data);
  });
}
