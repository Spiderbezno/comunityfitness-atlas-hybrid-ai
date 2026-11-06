// 📦 Package imports:
import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:hive_ce/hive.dart';

part 'workout_step.freezed.dart';
part 'workout_step.g.dart';

@freezed
@HiveType(typeId: 3)
abstract class WorkoutStep with _$WorkoutStep {
  const factory WorkoutStep({
    @HiveField(0) required String exerciseId,
    @HiveField(1) required int sets,
    @HiveField(2) required int reps,
    @HiveField(3) required double weight,
    @HiveField(4) required int targetDurationSeconds,
    @HiveField(5) required int restDurationSeconds,
    @HiveField(6) required int orderIndex,
    @Default(false) @HiveField(7) bool isWarmup,
  }) = _WorkoutStep;

  factory WorkoutStep.fromJson(Map<String, dynamic> json) => _$WorkoutStepFromJson(json);
}
