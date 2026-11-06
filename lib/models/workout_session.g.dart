// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'workout_session.dart';

// **************************************************************************
// TypeAdapterGenerator
// **************************************************************************

class WorkoutSessionAdapter extends TypeAdapter<WorkoutSession> {
  @override
  final typeId = 4;

  @override
  WorkoutSession read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read()};
    return WorkoutSession(
      id: fields[0] as String,
      userId: fields[1] as String,
      routineId: fields[2] as String?,
      routineTitle: fields[3] as String?,
      startedAt: fields[4] as DateTime,
      completedAt: fields[5] as DateTime?,
      synced: fields[6] == null ? false : fields[6] as bool,
      isDeleted: fields[7] == null ? false : fields[7] as bool,
      updatedAt: fields[8] as DateTime,
      steps: (fields[9] as List).cast<WorkoutStep>(),
    );
  }

  @override
  void write(BinaryWriter writer, WorkoutSession obj) {
    writer
      ..writeByte(10)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.userId)
      ..writeByte(2)
      ..write(obj.routineId)
      ..writeByte(3)
      ..write(obj.routineTitle)
      ..writeByte(4)
      ..write(obj.startedAt)
      ..writeByte(5)
      ..write(obj.completedAt)
      ..writeByte(6)
      ..write(obj.synced)
      ..writeByte(7)
      ..write(obj.isDeleted)
      ..writeByte(8)
      ..write(obj.updatedAt)
      ..writeByte(9)
      ..write(obj.steps);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) || other is WorkoutSessionAdapter && runtimeType == other.runtimeType && typeId == other.typeId;
}

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_WorkoutSession _$WorkoutSessionFromJson(Map<String, dynamic> json) => _WorkoutSession(
  id: json['id'] as String,
  userId: json['userId'] as String,
  routineId: json['routineId'] as String?,
  routineTitle: json['routineTitle'] as String?,
  startedAt: DateTime.parse(json['startedAt'] as String),
  completedAt: json['completedAt'] == null ? null : DateTime.parse(json['completedAt'] as String),
  synced: json['synced'] as bool? ?? false,
  isDeleted: json['isDeleted'] as bool? ?? false,
  updatedAt: DateTime.parse(json['updatedAt'] as String),
  steps: (json['steps'] as List<dynamic>).map((e) => WorkoutStep.fromJson(e as Map<String, dynamic>)).toList(),
);

Map<String, dynamic> _$WorkoutSessionToJson(_WorkoutSession instance) => <String, dynamic>{
  'id': instance.id,
  'userId': instance.userId,
  'routineId': instance.routineId,
  'routineTitle': instance.routineTitle,
  'startedAt': instance.startedAt.toIso8601String(),
  'completedAt': instance.completedAt?.toIso8601String(),
  'synced': instance.synced,
  'isDeleted': instance.isDeleted,
  'updatedAt': instance.updatedAt.toIso8601String(),
  'steps': instance.steps.map((e) => e.toJson()).toList(),
};
