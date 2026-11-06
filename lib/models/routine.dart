// 📦 Package imports:
import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:hive_ce/hive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/workout_step.dart';

part 'routine.freezed.dart';
part 'routine.g.dart';

@freezed
@HiveType(typeId: 2)
abstract class Routine with _$Routine {
  @JsonSerializable(explicitToJson: true)
  const factory Routine({
    @HiveField(0) required String id, // UUID
    @HiveField(1) required String title,
    @HiveField(2) required String description,
    @HiveField(3) required DateTime createdAt,
    @HiveField(4) required DateTime updatedAt,
    @HiveField(5) @Default(false) bool synced,
    @HiveField(6) @Default(false) bool isDeleted, // Soft delete flag
    @HiveField(7) required List<WorkoutStep> steps,
  }) = _Routine;

  factory Routine.fromJson(Map<String, dynamic> json) => _$RoutineFromJson(json);
}
