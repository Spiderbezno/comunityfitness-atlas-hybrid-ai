// 📦 Package imports:
import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:hive_ce/hive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/workout_step.dart';

part 'workout_session.freezed.dart';
part 'workout_session.g.dart';

@freezed
@HiveType(typeId: 4)
abstract class WorkoutSession with _$WorkoutSession {
  @JsonSerializable(explicitToJson: true)
  const factory WorkoutSession({
    @HiveField(0) required String id, // UUID
    @HiveField(1) required String userId,
    @HiveField(2) String? routineId,
    @HiveField(3) String? routineTitle,
    @HiveField(4) required DateTime startedAt,
    @HiveField(5) DateTime? completedAt,
    @HiveField(6) @Default(false) bool synced,
    @HiveField(7) @Default(false) bool isDeleted, // Soft delete flag
    @HiveField(8) required DateTime updatedAt,
    @HiveField(9) required List<WorkoutStep> steps,
  }) = _WorkoutSession;

  factory WorkoutSession.fromJson(Map<String, dynamic> json) => _$WorkoutSessionFromJson(json);
}
