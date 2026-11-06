// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'exercise.dart';

// **************************************************************************
// TypeAdapterGenerator
// **************************************************************************

class ExerciseAdapter extends TypeAdapter<Exercise> {
  @override
  final typeId = 1;

  @override
  Exercise read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read()};
    return Exercise(
      id: fields[0] as String,
      name: fields[1] as String,
      primaryMuscleGroup: fields[2] as String,
      equipment: fields[3] as String,
      animationType: fields[4] as String,
      animationPath: fields[5] as String,
      description: fields[6] as String,
    );
  }

  @override
  void write(BinaryWriter writer, Exercise obj) {
    writer
      ..writeByte(7)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.name)
      ..writeByte(2)
      ..write(obj.primaryMuscleGroup)
      ..writeByte(3)
      ..write(obj.equipment)
      ..writeByte(4)
      ..write(obj.animationType)
      ..writeByte(5)
      ..write(obj.animationPath)
      ..writeByte(6)
      ..write(obj.description);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) => identical(this, other) || other is ExerciseAdapter && runtimeType == other.runtimeType && typeId == other.typeId;
}

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_Exercise _$ExerciseFromJson(Map<String, dynamic> json) => _Exercise(
  id: json['id'] as String,
  name: json['name'] as String,
  primaryMuscleGroup: json['primaryMuscleGroup'] as String,
  equipment: json['equipment'] as String,
  animationType: json['animationType'] as String,
  animationPath: json['animationPath'] as String,
  description: json['description'] as String,
);

Map<String, dynamic> _$ExerciseToJson(_Exercise instance) => <String, dynamic>{
  'id': instance.id,
  'name': instance.name,
  'primaryMuscleGroup': instance.primaryMuscleGroup,
  'equipment': instance.equipment,
  'animationType': instance.animationType,
  'animationPath': instance.animationPath,
  'description': instance.description,
};
