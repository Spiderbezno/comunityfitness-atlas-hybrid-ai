// 📦 Package imports:
import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:hive_ce/hive.dart';

part 'exercise.freezed.dart';
part 'exercise.g.dart';

@freezed
@HiveType(typeId: 1)
abstract class Exercise with _$Exercise {
  const factory Exercise({
    @HiveField(0) required String id,
    @HiveField(1) required String name,
    @HiveField(2) required String primaryMuscleGroup,
    @HiveField(3) required String equipment,
    @HiveField(4) required String animationType, // 'rive' | 'movekit'
    @HiveField(5) required String animationPath, // asset path or URL
    @HiveField(6) required String description,
  }) = _Exercise;

  factory Exercise.fromJson(Map<String, dynamic> json) => _$ExerciseFromJson(json);
}
