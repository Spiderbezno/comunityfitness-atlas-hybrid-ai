// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/views/exercise_catalog_screen.dart';

class _MockExerciseRepository extends Mock implements ExerciseRepository {}

void main() {
  testWidgets('catalog cards render pre-rendered thumbnails and fall back when missing', (tester) async {
    final repository = _MockExerciseRepository();
    when(() => repository.seedIfNeeded()).thenAnswer((_) async {});
    when(() => repository.getExercises()).thenReturn(const [
      Exercise(
        id: 'ab_wheel_rollout',
        name: 'Ab Wheel Rollout',
        primaryMuscleGroup: 'Core',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: 'assets/animations/ab_wheel_rollout.riv',
        description: 'Rollout',
      ),
      Exercise(
        id: 'no_thumb',
        name: 'No Thumbnail Move',
        primaryMuscleGroup: 'Core',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: 'assets/animations/does_not_exist.riv',
        description: 'Missing thumbnail',
      ),
    ]);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [exerciseRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: ExerciseCatalogScreen()),
      ),
    );
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 200)));
    await tester.pumpAndSettle();

    expect(find.text('Ab Wheel Rollout'), findsOneWidget);
    expect(find.text('No Thumbnail Move'), findsOneWidget);

    bool isThumbnail(Widget widget, String asset) {
      if (widget is! Image) {
        return false;
      }
      final provider = widget.image;
      final assetName = provider is ResizeImage ? (provider.imageProvider as AssetImage).assetName : (provider as AssetImage).assetName;
      return assetName == asset;
    }

    expect(find.byWidgetPredicate((w) => isThumbnail(w, 'assets/animations/thumbnails/ab_wheel_rollout.png')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('renders arnold_press thumbnail when available', (tester) async {
    final repository = _MockExerciseRepository();
    when(() => repository.seedIfNeeded()).thenAnswer((_) async {});
    when(() => repository.getExercises()).thenReturn(const [
      Exercise(
        id: 'arnold_press',
        name: 'Arnold Press',
        primaryMuscleGroup: 'Core',
        equipment: 'Dumbbell',
        animationType: 'rive',
        animationPath: 'assets/animations/arnold_press.riv',
        description: 'Arnold Press',
      ),
    ]);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [exerciseRepositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: ExerciseCatalogScreen()),
      ),
    );
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 200)));
    await tester.pumpAndSettle();

    expect(find.text('Arnold Press'), findsOneWidget);

    bool isThumbnail(Widget widget, String asset) {
      if (widget is! Image) {
        return false;
      }
      final provider = widget.image;
      final assetName = provider is ResizeImage ? (provider.imageProvider as AssetImage).assetName : (provider as AssetImage).assetName;
      return assetName == asset;
    }

    expect(find.byWidgetPredicate((w) => isThumbnail(w, 'assets/animations/thumbnails/arnold_press.png')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
