// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'workout_step.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;

/// @nodoc
mixin _$WorkoutStep {

@HiveField(0) String get exerciseId;@HiveField(1) int get sets;@HiveField(2) int get reps;@HiveField(3) double get weight;@HiveField(4) int get targetDurationSeconds;@HiveField(5) int get restDurationSeconds;@HiveField(6) int get orderIndex;@HiveField(7) bool get isWarmup;
/// Create a copy of WorkoutStep
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$WorkoutStepCopyWith<WorkoutStep> get copyWith => _$WorkoutStepCopyWithImpl<WorkoutStep>(this as WorkoutStep, _$identity);

  /// Serializes this WorkoutStep to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is WorkoutStep&&(identical(other.exerciseId, exerciseId) || other.exerciseId == exerciseId)&&(identical(other.sets, sets) || other.sets == sets)&&(identical(other.reps, reps) || other.reps == reps)&&(identical(other.weight, weight) || other.weight == weight)&&(identical(other.targetDurationSeconds, targetDurationSeconds) || other.targetDurationSeconds == targetDurationSeconds)&&(identical(other.restDurationSeconds, restDurationSeconds) || other.restDurationSeconds == restDurationSeconds)&&(identical(other.orderIndex, orderIndex) || other.orderIndex == orderIndex)&&(identical(other.isWarmup, isWarmup) || other.isWarmup == isWarmup));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,exerciseId,sets,reps,weight,targetDurationSeconds,restDurationSeconds,orderIndex,isWarmup);

@override
String toString() {
  return 'WorkoutStep(exerciseId: $exerciseId, sets: $sets, reps: $reps, weight: $weight, targetDurationSeconds: $targetDurationSeconds, restDurationSeconds: $restDurationSeconds, orderIndex: $orderIndex, isWarmup: $isWarmup)';
}


}

/// @nodoc
abstract mixin class $WorkoutStepCopyWith<$Res>  {
  factory $WorkoutStepCopyWith(WorkoutStep value, $Res Function(WorkoutStep) _then) = _$WorkoutStepCopyWithImpl;
@useResult
$Res call({
@HiveField(0) String exerciseId,@HiveField(1) int sets,@HiveField(2) int reps,@HiveField(3) double weight,@HiveField(4) int targetDurationSeconds,@HiveField(5) int restDurationSeconds,@HiveField(6) int orderIndex,@HiveField(7) bool isWarmup
});




}
/// @nodoc
class _$WorkoutStepCopyWithImpl<$Res>
    implements $WorkoutStepCopyWith<$Res> {
  _$WorkoutStepCopyWithImpl(this._self, this._then);

  final WorkoutStep _self;
  final $Res Function(WorkoutStep) _then;

/// Create a copy of WorkoutStep
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? exerciseId = null,Object? sets = null,Object? reps = null,Object? weight = null,Object? targetDurationSeconds = null,Object? restDurationSeconds = null,Object? orderIndex = null,Object? isWarmup = null,}) {
  return _then(_self.copyWith(
exerciseId: null == exerciseId ? _self.exerciseId : exerciseId // ignore: cast_nullable_to_non_nullable
as String,sets: null == sets ? _self.sets : sets // ignore: cast_nullable_to_non_nullable
as int,reps: null == reps ? _self.reps : reps // ignore: cast_nullable_to_non_nullable
as int,weight: null == weight ? _self.weight : weight // ignore: cast_nullable_to_non_nullable
as double,targetDurationSeconds: null == targetDurationSeconds ? _self.targetDurationSeconds : targetDurationSeconds // ignore: cast_nullable_to_non_nullable
as int,restDurationSeconds: null == restDurationSeconds ? _self.restDurationSeconds : restDurationSeconds // ignore: cast_nullable_to_non_nullable
as int,orderIndex: null == orderIndex ? _self.orderIndex : orderIndex // ignore: cast_nullable_to_non_nullable
as int,isWarmup: null == isWarmup ? _self.isWarmup : isWarmup // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

}


/// Adds pattern-matching-related methods to [WorkoutStep].
extension WorkoutStepPatterns on WorkoutStep {
/// A variant of `map` that fallback to returning `orElse`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _WorkoutStep value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _WorkoutStep() when $default != null:
return $default(_that);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// Callbacks receives the raw object, upcasted.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case final Subclass2 value:
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _WorkoutStep value)  $default,){
final _that = this;
switch (_that) {
case _WorkoutStep():
return $default(_that);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `map` that fallback to returning `null`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _WorkoutStep value)?  $default,){
final _that = this;
switch (_that) {
case _WorkoutStep() when $default != null:
return $default(_that);case _:
  return null;

}
}
/// A variant of `when` that fallback to an `orElse` callback.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function(@HiveField(0)  String exerciseId, @HiveField(1)  int sets, @HiveField(2)  int reps, @HiveField(3)  double weight, @HiveField(4)  int targetDurationSeconds, @HiveField(5)  int restDurationSeconds, @HiveField(6)  int orderIndex, @HiveField(7)  bool isWarmup)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _WorkoutStep() when $default != null:
return $default(_that.exerciseId,_that.sets,_that.reps,_that.weight,_that.targetDurationSeconds,_that.restDurationSeconds,_that.orderIndex,_that.isWarmup);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// As opposed to `map`, this offers destructuring.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case Subclass2(:final field2):
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function(@HiveField(0)  String exerciseId, @HiveField(1)  int sets, @HiveField(2)  int reps, @HiveField(3)  double weight, @HiveField(4)  int targetDurationSeconds, @HiveField(5)  int restDurationSeconds, @HiveField(6)  int orderIndex, @HiveField(7)  bool isWarmup)  $default,) {final _that = this;
switch (_that) {
case _WorkoutStep():
return $default(_that.exerciseId,_that.sets,_that.reps,_that.weight,_that.targetDurationSeconds,_that.restDurationSeconds,_that.orderIndex,_that.isWarmup);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `when` that fallback to returning `null`
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function(@HiveField(0)  String exerciseId, @HiveField(1)  int sets, @HiveField(2)  int reps, @HiveField(3)  double weight, @HiveField(4)  int targetDurationSeconds, @HiveField(5)  int restDurationSeconds, @HiveField(6)  int orderIndex, @HiveField(7)  bool isWarmup)?  $default,) {final _that = this;
switch (_that) {
case _WorkoutStep() when $default != null:
return $default(_that.exerciseId,_that.sets,_that.reps,_that.weight,_that.targetDurationSeconds,_that.restDurationSeconds,_that.orderIndex,_that.isWarmup);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _WorkoutStep implements WorkoutStep {
  const _WorkoutStep({@HiveField(0) required this.exerciseId, @HiveField(1) required this.sets, @HiveField(2) required this.reps, @HiveField(3) required this.weight, @HiveField(4) required this.targetDurationSeconds, @HiveField(5) required this.restDurationSeconds, @HiveField(6) required this.orderIndex, @HiveField(7) this.isWarmup = false});
  factory _WorkoutStep.fromJson(Map<String, dynamic> json) => _$WorkoutStepFromJson(json);

@override@HiveField(0) final  String exerciseId;
@override@HiveField(1) final  int sets;
@override@HiveField(2) final  int reps;
@override@HiveField(3) final  double weight;
@override@HiveField(4) final  int targetDurationSeconds;
@override@HiveField(5) final  int restDurationSeconds;
@override@HiveField(6) final  int orderIndex;
@override@JsonKey()@HiveField(7) final  bool isWarmup;

/// Create a copy of WorkoutStep
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$WorkoutStepCopyWith<_WorkoutStep> get copyWith => __$WorkoutStepCopyWithImpl<_WorkoutStep>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$WorkoutStepToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _WorkoutStep&&(identical(other.exerciseId, exerciseId) || other.exerciseId == exerciseId)&&(identical(other.sets, sets) || other.sets == sets)&&(identical(other.reps, reps) || other.reps == reps)&&(identical(other.weight, weight) || other.weight == weight)&&(identical(other.targetDurationSeconds, targetDurationSeconds) || other.targetDurationSeconds == targetDurationSeconds)&&(identical(other.restDurationSeconds, restDurationSeconds) || other.restDurationSeconds == restDurationSeconds)&&(identical(other.orderIndex, orderIndex) || other.orderIndex == orderIndex)&&(identical(other.isWarmup, isWarmup) || other.isWarmup == isWarmup));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,exerciseId,sets,reps,weight,targetDurationSeconds,restDurationSeconds,orderIndex,isWarmup);

@override
String toString() {
  return 'WorkoutStep(exerciseId: $exerciseId, sets: $sets, reps: $reps, weight: $weight, targetDurationSeconds: $targetDurationSeconds, restDurationSeconds: $restDurationSeconds, orderIndex: $orderIndex, isWarmup: $isWarmup)';
}


}

/// @nodoc
abstract mixin class _$WorkoutStepCopyWith<$Res> implements $WorkoutStepCopyWith<$Res> {
  factory _$WorkoutStepCopyWith(_WorkoutStep value, $Res Function(_WorkoutStep) _then) = __$WorkoutStepCopyWithImpl;
@override @useResult
$Res call({
@HiveField(0) String exerciseId,@HiveField(1) int sets,@HiveField(2) int reps,@HiveField(3) double weight,@HiveField(4) int targetDurationSeconds,@HiveField(5) int restDurationSeconds,@HiveField(6) int orderIndex,@HiveField(7) bool isWarmup
});




}
/// @nodoc
class __$WorkoutStepCopyWithImpl<$Res>
    implements _$WorkoutStepCopyWith<$Res> {
  __$WorkoutStepCopyWithImpl(this._self, this._then);

  final _WorkoutStep _self;
  final $Res Function(_WorkoutStep) _then;

/// Create a copy of WorkoutStep
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? exerciseId = null,Object? sets = null,Object? reps = null,Object? weight = null,Object? targetDurationSeconds = null,Object? restDurationSeconds = null,Object? orderIndex = null,Object? isWarmup = null,}) {
  return _then(_WorkoutStep(
exerciseId: null == exerciseId ? _self.exerciseId : exerciseId // ignore: cast_nullable_to_non_nullable
as String,sets: null == sets ? _self.sets : sets // ignore: cast_nullable_to_non_nullable
as int,reps: null == reps ? _self.reps : reps // ignore: cast_nullable_to_non_nullable
as int,weight: null == weight ? _self.weight : weight // ignore: cast_nullable_to_non_nullable
as double,targetDurationSeconds: null == targetDurationSeconds ? _self.targetDurationSeconds : targetDurationSeconds // ignore: cast_nullable_to_non_nullable
as int,restDurationSeconds: null == restDurationSeconds ? _self.restDurationSeconds : restDurationSeconds // ignore: cast_nullable_to_non_nullable
as int,orderIndex: null == orderIndex ? _self.orderIndex : orderIndex // ignore: cast_nullable_to_non_nullable
as int,isWarmup: null == isWarmup ? _self.isWarmup : isWarmup // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}


}

// dart format on
