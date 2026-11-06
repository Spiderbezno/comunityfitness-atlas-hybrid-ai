// 🐦 Flutter imports:
import 'package:flutter/services.dart';

// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce/hive.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';

class MockBox extends Mock implements Box<Exercise> {}

class MockAssetBundle extends Mock implements AssetBundle {}

void main() {
  late MockBox mockBox;
  late MockAssetBundle mockAssetBundle;
  late ExerciseRepository repository;

  setUpAll(() {
    registerFallbackValue(
      const Exercise(id: '', name: '', primaryMuscleGroup: '', equipment: '', animationType: '', animationPath: '', description: ''),
    );
  });

  setUp(() {
    mockBox = MockBox();
    mockAssetBundle = MockAssetBundle();
    repository = ExerciseRepository(exerciseBox: mockBox, assetBundle: mockAssetBundle);
  });

  group('ExerciseRepository', () {
    const dummyExercisesJson = '''
    [
      {
        "id": "push_up",
        "name": "Push Up",
        "primaryMuscleGroup": "Chest",
        "equipment": "Bodyweight",
        "animationType": "rive",
        "animationPath": "assets/animations/push_up.riv",
        "description": "Chest press"
      }
    ]
    ''';

    test('seeds exercises when box is empty', () async {
      when(() => mockBox.length).thenReturn(0);
      when(() => mockBox.clear()).thenAnswer((_) async => 0);
      when(() => mockAssetBundle.loadString('assets/data/exercises.json')).thenAnswer((_) async => dummyExercisesJson);

      const expectedExercise = Exercise(
        id: 'push_up',
        name: 'Push Up',
        primaryMuscleGroup: 'Chest',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: 'assets/animations/push_up.riv',
        description: 'Chest press',
      );

      when(() => mockBox.put('push_up', any())).thenAnswer((_) async {});

      await repository.seedIfNeeded();

      verify(() => mockAssetBundle.loadString('assets/data/exercises.json')).called(1);
      verifyNever(() => mockBox.clear());
      verify(() => mockBox.put('push_up', expectedExercise)).called(1);
    });

    test('does not seed when box has matching length', () async {
      const dummyExercise = Exercise(
        id: 'push_up',
        name: 'Push Up',
        primaryMuscleGroup: 'Chest',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: 'assets/animations/push_up.riv',
        description: 'Chest press',
      );
      when(() => mockBox.length).thenReturn(1);
      when(() => mockBox.values).thenReturn([dummyExercise]);
      when(() => mockAssetBundle.loadString('assets/data/exercises.json')).thenAnswer((_) async => dummyExercisesJson);

      await repository.seedIfNeeded();

      verifyNever(() => mockBox.clear());
      verifyNever(() => mockBox.put(any<dynamic>(), any()));
    });

    test('reseeds when any exercise animation drifts from the catalog without clearing custom exercises', () async {
      const stale = Exercise(
        id: 'push_up',
        name: 'Push Up',
        primaryMuscleGroup: 'Chest',
        equipment: 'Bodyweight',
        animationType: 'movekit',
        animationPath: 'assets/animations/push_up.movekit',
        description: 'Chest press',
      );
      when(() => mockBox.length).thenReturn(1);
      when(() => mockBox.values).thenReturn([stale]);
      when(() => mockBox.put(any<dynamic>(), any())).thenAnswer((_) async {});
      when(() => mockAssetBundle.loadString('assets/data/exercises.json')).thenAnswer((_) async => dummyExercisesJson);

      await repository.seedIfNeeded();

      verifyNever(() => mockBox.clear());
      verify(() => mockBox.put('push_up', any())).called(1);
    });

    test('preserves custom/imported exercises when box has extra entries and catalog is up to date', () async {
      const catalogExercise = Exercise(
        id: 'push_up',
        name: 'Push Up',
        primaryMuscleGroup: 'Chest',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: 'assets/animations/push_up.riv',
        description: 'Chest press',
      );
      const customImported = Exercise(
        id: 'imported-incline-press',
        name: 'Incline Press',
        primaryMuscleGroup: 'Chest',
        equipment: 'Dumbbell',
        animationType: 'rive',
        animationPath: '',
        description: 'Imported from Hevy',
      );
      when(() => mockBox.length).thenReturn(2);
      when(() => mockBox.values).thenReturn([catalogExercise, customImported]);
      when(() => mockAssetBundle.loadString('assets/data/exercises.json')).thenAnswer((_) async => dummyExercisesJson);

      await repository.seedIfNeeded();

      verifyNever(() => mockBox.clear());
      verifyNever(() => mockBox.put(any<dynamic>(), any()));
    });

    test('returns all exercises from box with HD Rive exercises sorted before remote GIF exercises', () {
      const rearDeltFly = Exercise(
        id: 'rear_delt_fly',
        name: 'Rear Delt Fly',
        primaryMuscleGroup: 'Shoulders',
        equipment: 'Dumbbell',
        animationType: 'rive',
        animationPath: 'assets/animations/rear_delt_fly.riv',
        description: 'Rear deltoid isolation',
      );
      const remoteGif = Exercise(
        id: 'remote_0001',
        name: '3/4 Sit-Up',
        primaryMuscleGroup: 'Core',
        equipment: 'Bodyweight',
        animationType: 'gif',
        animationPath: 'assets/animations/gif/0001.gif',
        description: 'Abdominal exercise',
      );
      const romanianDeadlift = Exercise(
        id: 'romanian_deadlift',
        name: 'Romanian Deadlift',
        primaryMuscleGroup: 'Legs',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: 'assets/animations/romanian_deadlift.riv',
        description: 'Hip hinge',
      );
      const squat = Exercise(
        id: 'squat',
        name: 'Barbell Squat',
        primaryMuscleGroup: 'Legs',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: 'assets/animations/squat.riv',
        description: 'Compound leg exercise',
      );
      when(() => mockBox.values).thenReturn([rearDeltFly, remoteGif, romanianDeadlift, squat]);

      final result = repository.getExercises();

      expect(result, [rearDeltFly, romanianDeadlift, squat, remoteGif]);
    });
  });
}
