// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'workout_step.dart';

// **************************************************************************
// TypeAdapterGenerator
// **************************************************************************

class WorkoutStepAdapter extends TypeAdapter<WorkoutStep> {
  @override
  final typeId = 3;

  @override
  WorkoutStep read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read()};
    return WorkoutStep(
      exerciseId: fields[0] as String,
      sets: (fields[1] as num).toInt(),
      reps: (fields[2] as num).toInt(),
      weight: (fields[3] as num).toDouble(),
      targetDurationSeconds: (fields[4] as num).toInt(),
      restDurationSeconds: (fields[5] as num).toInt(),
      orderIndex: (fields[6] as num).toInt(),
      isWarmup: fields[7] as bool? ?? false,
    );
  }

  @override
  void write(BinaryWriter writer, WorkoutStep obj) {
    writer
      ..writeByte(8)
      ..writeByte(0)
      ..write(obj.exerciseId)
      ..writeByte(1)
      ..write(obj.sets)
      ..writeByte(2)
      ..write(obj.reps)
      ..writeByte(3)
      ..write(obj.weight)
      ..writeByte(4)
      ..write(obj.targetDurationSeconds)
      ..writeByte(5)
      ..write(obj.restDurationSeconds)
      ..writeByte(6)
      ..write(obj.orderIndex)
      ..writeByte(7)
      ..write(obj.isWarmup);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) || other is WorkoutStepAdapter && runtimeType == other.runtimeType && typeId == other.typeId;
}

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_WorkoutStep _$WorkoutStepFromJson(Map<String, dynamic> json) => _WorkoutStep(
  exerciseId: json['exerciseId'] as String,
  sets: (json['sets'] as num).toInt(),
  reps: (json['reps'] as num).toInt(),
  weight: (json['weight'] as num).toDouble(),
  targetDurationSeconds: (json['targetDurationSeconds'] as num).toInt(),
  restDurationSeconds: (json['restDurationSeconds'] as num).toInt(),
  orderIndex: (json['orderIndex'] as num).toInt(),
  isWarmup: json['isWarmup'] as bool? ?? false,
);

Map<String, dynamic> _$WorkoutStepToJson(_WorkoutStep instance) => <String, dynamic>{
  'exerciseId': instance.exerciseId,
  'sets': instance.sets,
  'reps': instance.reps,
  'weight': instance.weight,
  'targetDurationSeconds': instance.targetDurationSeconds,
  'restDurationSeconds': instance.restDurationSeconds,
  'orderIndex': instance.orderIndex,
  'isWarmup': instance.isWarmup,
};
