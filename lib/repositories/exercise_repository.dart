// 🎯 Dart imports:
import 'dart:convert';

// 🐦 Flutter imports:
import 'package:flutter/services.dart';

// 📦 Package imports:
import 'package:hive_ce/hive.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/utils/exercise_animation_asset.dart';

part 'exercise_repository.g.dart';

/// True when any stored exercise is missing or its catalog fields differ
/// from the bundled catalog, so a single asset or metadata swap triggers an upsert.
bool catalogDrifted(Iterable<Exercise> stored, List<Map<String, dynamic>> catalog) {
  final byId = {for (final e in stored) e.id: e};
  for (final item in catalog) {
    final current = byId[item['id']];
    if (current == null ||
        current.animationPath.isEmpty ||
        current.animationPath != (item['animationPath'] ?? '') ||
        current.animationType != (item['animationType'] ?? '') ||
        current.name != (item['name'] ?? '') ||
        current.primaryMuscleGroup != (item['primaryMuscleGroup'] ?? '') ||
        current.equipment != (item['equipment'] ?? '') ||
        current.description != (item['description'] ?? '')) {
      return true;
    }
  }
  return false;
}

@riverpod
ExerciseRepository exerciseRepository(Ref ref) {
  final box = Hive.box<Exercise>('exercises');
  return ExerciseRepository(exerciseBox: box);
}

class ExerciseRepository {
  final Box<Exercise> _exerciseBox;
  final AssetBundle _assetBundle;

  ExerciseRepository({required this._exerciseBox, AssetBundle? assetBundle}) : _assetBundle = assetBundle ?? rootBundle;

  Future<void> seedIfNeeded() async {
    final jsonString = await _assetBundle.loadString('assets/data/exercises.json');
    final List<dynamic> jsonList = json.decode(jsonString) as List<dynamic>;

    final needsSeeding = _exerciseBox.length < jsonList.length || catalogDrifted(_exerciseBox.values, jsonList.cast<Map<String, dynamic>>());

    if (needsSeeding) {
      for (final item in jsonList) {
        final exercise = Exercise.fromJson(item as Map<String, dynamic>);
        await _exerciseBox.put(exercise.id, exercise);
      }
    }
  }

  List<Exercise> getExercises() {
    final list = _exerciseBox.values.toList();
    list.sort((a, b) {
      final aIsHd = exerciseRiveAsset(a) != null;
      final bIsHd = exerciseRiveAsset(b) != null;
      if (aIsHd != bIsHd) {
        return aIsHd ? -1 : 1;
      }
      return a.id.compareTo(b.id);
    });
    return list;
  }

  Exercise? getExercise(String id) {
    return _exerciseBox.get(id);
  }

  Future<void> saveExercise(Exercise exercise) async {
    await _exerciseBox.put(exercise.id, exercise);
  }

  Stream<List<Exercise>> watchExercises() async* {
    yield getExercises();
    await for (final _ in _exerciseBox.watch()) {
      yield getExercises();
    }
  }
}
