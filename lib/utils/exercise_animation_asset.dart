// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';

/// Animation types whose [Exercise.animationPath] points at a Rive binary.
///
/// `.movekit` files are Rive binaries too (they carry the `RIVE` header).
const Set<String> riveAnimationTypes = {'rive', 'movekit'};

/// Returns the bundled Rive asset to render for [exercise], or `null` when the
/// exercise has no local Rive animation (e.g. a GIF URL or an empty path).
String? exerciseRiveAsset(Exercise exercise) {
  final path = exercise.animationPath.trim();
  if (!riveAnimationTypes.contains(exercise.animationType)) {
    return null;
  }
  if (path.isEmpty || !path.startsWith('assets/')) {
    return null;
  }
  return path;
}

/// Pre-rendered catalog thumbnail for [exercise], by convention:
/// `assets/animations/<name>.riv` -> `assets/animations/thumbnails/<name>.png`.
///
/// Returns `null` when the exercise has no local Rive animation. The asset may
/// still be missing for exercises without a rendered thumbnail, so callers
/// must handle load errors (e.g. `Image.asset(errorBuilder: ...)`).
String? exerciseThumbnailAsset(Exercise exercise) {
  final riveAsset = exerciseRiveAsset(exercise);
  if (riveAsset == null) {
    return null;
  }
  final slash = riveAsset.lastIndexOf('/');
  final directory = riveAsset.substring(0, slash);
  final fileName = riveAsset.substring(slash + 1);
  final dot = fileName.lastIndexOf('.');
  final baseName = dot > 0 ? fileName.substring(0, dot) : fileName;
  return '$directory/thumbnails/$baseName.png';
}
