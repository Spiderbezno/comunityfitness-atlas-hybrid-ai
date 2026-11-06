// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/utils/exercise_animation_asset.dart';

Exercise _exercise({required String type, required String path}) => Exercise(
  id: 'ab_wheel_rollout',
  name: 'Ab Wheel Rollout',
  primaryMuscleGroup: 'Core',
  equipment: 'Bodyweight',
  animationType: type,
  animationPath: path,
  description: '',
);

void main() {
  group('exerciseRiveAsset', () {
    test('maps Ab Wheel Rollout to its bundled .riv', () {
      final exercise = _exercise(type: 'rive', path: 'assets/animations/ab_wheel_rollout.riv');
      expect(exerciseRiveAsset(exercise), 'assets/animations/ab_wheel_rollout.riv');
    });

    test('accepts movekit assets (Rive binaries)', () {
      final exercise = _exercise(type: 'movekit', path: 'assets/animations/plank.movekit');
      expect(exerciseRiveAsset(exercise), 'assets/animations/plank.movekit');
    });

    test('returns null for GIFs, remote URLs and empty paths', () {
      expect(exerciseRiveAsset(_exercise(type: 'gif', path: 'https://x.test/a.gif')), isNull);
      expect(exerciseRiveAsset(_exercise(type: 'rive', path: 'https://x.test/a.riv')), isNull);
      expect(exerciseRiveAsset(_exercise(type: 'rive', path: '   ')), isNull);
    });
  });

  group('exerciseThumbnailAsset', () {
    test('derives the thumbnail PNG from the .riv path', () {
      final exercise = _exercise(type: 'rive', path: 'assets/animations/ab_wheel_rollout.riv');
      expect(exerciseThumbnailAsset(exercise), 'assets/animations/thumbnails/ab_wheel_rollout.png');
    });

    test('derives the thumbnail PNG from a .movekit path', () {
      final exercise = _exercise(type: 'movekit', path: 'assets/animations/plank.movekit');
      expect(exerciseThumbnailAsset(exercise), 'assets/animations/thumbnails/plank.png');
    });

    test('returns null when there is no local Rive animation', () {
      expect(exerciseThumbnailAsset(_exercise(type: 'gif', path: 'https://x.test/a.gif')), isNull);
      expect(exerciseThumbnailAsset(_exercise(type: 'rive', path: '')), isNull);
    });
  });
}
