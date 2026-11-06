// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'workout_session.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;

/// @nodoc
mixin _$WorkoutSession {

@HiveField(0) String get id;@HiveField(1) String get userId;@HiveField(2) String? get routineId;@HiveField(3) String? get routineTitle;@HiveField(4) DateTime get startedAt;@HiveField(5) DateTime? get completedAt;@HiveField(6) bool get synced;@HiveField(7) bool get isDeleted;@HiveField(8) DateTime get updatedAt;@HiveField(9) List<WorkoutStep> get steps;
/// Create a copy of WorkoutSession
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$WorkoutSessionCopyWith<WorkoutSession> get copyWith => _$WorkoutSessionCopyWithImpl<WorkoutSession>(this as WorkoutSession, _$identity);

  /// Serializes this WorkoutSession to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is WorkoutSession&&(identical(other.id, id) || other.id == id)&&(identical(other.userId, userId) || other.userId == userId)&&(identical(other.routineId, routineId) || other.routineId == routineId)&&(identical(other.routineTitle, routineTitle) || other.routineTitle == routineTitle)&&(identical(other.startedAt, startedAt) || other.startedAt == startedAt)&&(identical(other.completedAt, completedAt) || other.completedAt == completedAt)&&(identical(other.synced, synced) || other.synced == synced)&&(identical(other.isDeleted, isDeleted) || other.isDeleted == isDeleted)&&(identical(other.updatedAt, updatedAt) || other.updatedAt == updatedAt)&&const DeepCollectionEquality().equals(other.steps, steps));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,userId,routineId,routineTitle,startedAt,completedAt,synced,isDeleted,updatedAt,const DeepCollectionEquality().hash(steps));

@override
String toString() {
  return 'WorkoutSession(id: $id, userId: $userId, routineId: $routineId, routineTitle: $routineTitle, startedAt: $startedAt, completedAt: $completedAt, synced: $synced, isDeleted: $isDeleted, updatedAt: $updatedAt, steps: $steps)';
}


}

/// @nodoc
abstract mixin class $WorkoutSessionCopyWith<$Res>  {
  factory $WorkoutSessionCopyWith(WorkoutSession value, $Res Function(WorkoutSession) _then) = _$WorkoutSessionCopyWithImpl;
@useResult
$Res call({
@HiveField(0) String id,@HiveField(1) String userId,@HiveField(2) String? routineId,@HiveField(3) String? routineTitle,@HiveField(4) DateTime startedAt,@HiveField(5) DateTime? completedAt,@HiveField(6) bool synced,@HiveField(7) bool isDeleted,@HiveField(8) DateTime updatedAt,@HiveField(9) List<WorkoutStep> steps
});




}
/// @nodoc
class _$WorkoutSessionCopyWithImpl<$Res>
    implements $WorkoutSessionCopyWith<$Res> {
  _$WorkoutSessionCopyWithImpl(this._self, this._then);

  final WorkoutSession _self;
  final $Res Function(WorkoutSession) _then;

/// Create a copy of WorkoutSession
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? userId = null,Object? routineId = freezed,Object? routineTitle = freezed,Object? startedAt = null,Object? completedAt = freezed,Object? synced = null,Object? isDeleted = null,Object? updatedAt = null,Object? steps = null,}) {
  return _then(_self.copyWith(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,userId: null == userId ? _self.userId : userId // ignore: cast_nullable_to_non_nullable
as String,routineId: freezed == routineId ? _self.routineId : routineId // ignore: cast_nullable_to_non_nullable
as String?,routineTitle: freezed == routineTitle ? _self.routineTitle : routineTitle // ignore: cast_nullable_to_non_nullable
as String?,startedAt: null == startedAt ? _self.startedAt : startedAt // ignore: cast_nullable_to_non_nullable
as DateTime,completedAt: freezed == completedAt ? _self.completedAt : completedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,synced: null == synced ? _self.synced : synced // ignore: cast_nullable_to_non_nullable
as bool,isDeleted: null == isDeleted ? _self.isDeleted : isDeleted // ignore: cast_nullable_to_non_nullable
as bool,updatedAt: null == updatedAt ? _self.updatedAt : updatedAt // ignore: cast_nullable_to_non_nullable
as DateTime,steps: null == steps ? _self.steps : steps // ignore: cast_nullable_to_non_nullable
as List<WorkoutStep>,
  ));
}

}


/// Adds pattern-matching-related methods to [WorkoutSession].
extension WorkoutSessionPatterns on WorkoutSession {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _WorkoutSession value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _WorkoutSession() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _WorkoutSession value)  $default,){
final _that = this;
switch (_that) {
case _WorkoutSession():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _WorkoutSession value)?  $default,){
final _that = this;
switch (_that) {
case _WorkoutSession() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function(@HiveField(0)  String id, @HiveField(1)  String userId, @HiveField(2)  String? routineId, @HiveField(3)  String? routineTitle, @HiveField(4)  DateTime startedAt, @HiveField(5)  DateTime? completedAt, @HiveField(6)  bool synced, @HiveField(7)  bool isDeleted, @HiveField(8)  DateTime updatedAt, @HiveField(9)  List<WorkoutStep> steps)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _WorkoutSession() when $default != null:
return $default(_that.id,_that.userId,_that.routineId,_that.routineTitle,_that.startedAt,_that.completedAt,_that.synced,_that.isDeleted,_that.updatedAt,_that.steps);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function(@HiveField(0)  String id, @HiveField(1)  String userId, @HiveField(2)  String? routineId, @HiveField(3)  String? routineTitle, @HiveField(4)  DateTime startedAt, @HiveField(5)  DateTime? completedAt, @HiveField(6)  bool synced, @HiveField(7)  bool isDeleted, @HiveField(8)  DateTime updatedAt, @HiveField(9)  List<WorkoutStep> steps)  $default,) {final _that = this;
switch (_that) {
case _WorkoutSession():
return $default(_that.id,_that.userId,_that.routineId,_that.routineTitle,_that.startedAt,_that.completedAt,_that.synced,_that.isDeleted,_that.updatedAt,_that.steps);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function(@HiveField(0)  String id, @HiveField(1)  String userId, @HiveField(2)  String? routineId, @HiveField(3)  String? routineTitle, @HiveField(4)  DateTime startedAt, @HiveField(5)  DateTime? completedAt, @HiveField(6)  bool synced, @HiveField(7)  bool isDeleted, @HiveField(8)  DateTime updatedAt, @HiveField(9)  List<WorkoutStep> steps)?  $default,) {final _that = this;
switch (_that) {
case _WorkoutSession() when $default != null:
return $default(_that.id,_that.userId,_that.routineId,_that.routineTitle,_that.startedAt,_that.completedAt,_that.synced,_that.isDeleted,_that.updatedAt,_that.steps);case _:
  return null;

}
}

}

/// @nodoc

@JsonSerializable(explicitToJson: true)
class _WorkoutSession implements WorkoutSession {
  const _WorkoutSession({@HiveField(0) required this.id, @HiveField(1) required this.userId, @HiveField(2) this.routineId, @HiveField(3) this.routineTitle, @HiveField(4) required this.startedAt, @HiveField(5) this.completedAt, @HiveField(6) this.synced = false, @HiveField(7) this.isDeleted = false, @HiveField(8) required this.updatedAt, @HiveField(9) required List<WorkoutStep> steps}): _steps = steps;
  factory _WorkoutSession.fromJson(Map<String, dynamic> json) => _$WorkoutSessionFromJson(json);

@override@HiveField(0) final  String id;
@override@HiveField(1) final  String userId;
@override@HiveField(2) final  String? routineId;
@override@HiveField(3) final  String? routineTitle;
@override@HiveField(4) final  DateTime startedAt;
@override@HiveField(5) final  DateTime? completedAt;
@override@JsonKey()@HiveField(6) final  bool synced;
@override@JsonKey()@HiveField(7) final  bool isDeleted;
@override@HiveField(8) final  DateTime updatedAt;
 final  List<WorkoutStep> _steps;
@override@HiveField(9) List<WorkoutStep> get steps {
  if (_steps is EqualUnmodifiableListView) return _steps;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_steps);
}


/// Create a copy of WorkoutSession
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$WorkoutSessionCopyWith<_WorkoutSession> get copyWith => __$WorkoutSessionCopyWithImpl<_WorkoutSession>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$WorkoutSessionToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _WorkoutSession&&(identical(other.id, id) || other.id == id)&&(identical(other.userId, userId) || other.userId == userId)&&(identical(other.routineId, routineId) || other.routineId == routineId)&&(identical(other.routineTitle, routineTitle) || other.routineTitle == routineTitle)&&(identical(other.startedAt, startedAt) || other.startedAt == startedAt)&&(identical(other.completedAt, completedAt) || other.completedAt == completedAt)&&(identical(other.synced, synced) || other.synced == synced)&&(identical(other.isDeleted, isDeleted) || other.isDeleted == isDeleted)&&(identical(other.updatedAt, updatedAt) || other.updatedAt == updatedAt)&&const DeepCollectionEquality().equals(other._steps, _steps));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,userId,routineId,routineTitle,startedAt,completedAt,synced,isDeleted,updatedAt,const DeepCollectionEquality().hash(_steps));

@override
String toString() {
  return 'WorkoutSession(id: $id, userId: $userId, routineId: $routineId, routineTitle: $routineTitle, startedAt: $startedAt, completedAt: $completedAt, synced: $synced, isDeleted: $isDeleted, updatedAt: $updatedAt, steps: $steps)';
}


}

/// @nodoc
abstract mixin class _$WorkoutSessionCopyWith<$Res> implements $WorkoutSessionCopyWith<$Res> {
  factory _$WorkoutSessionCopyWith(_WorkoutSession value, $Res Function(_WorkoutSession) _then) = __$WorkoutSessionCopyWithImpl;
@override @useResult
$Res call({
@HiveField(0) String id,@HiveField(1) String userId,@HiveField(2) String? routineId,@HiveField(3) String? routineTitle,@HiveField(4) DateTime startedAt,@HiveField(5) DateTime? completedAt,@HiveField(6) bool synced,@HiveField(7) bool isDeleted,@HiveField(8) DateTime updatedAt,@HiveField(9) List<WorkoutStep> steps
});




}
/// @nodoc
class __$WorkoutSessionCopyWithImpl<$Res>
    implements _$WorkoutSessionCopyWith<$Res> {
  __$WorkoutSessionCopyWithImpl(this._self, this._then);

  final _WorkoutSession _self;
  final $Res Function(_WorkoutSession) _then;

/// Create a copy of WorkoutSession
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? userId = null,Object? routineId = freezed,Object? routineTitle = freezed,Object? startedAt = null,Object? completedAt = freezed,Object? synced = null,Object? isDeleted = null,Object? updatedAt = null,Object? steps = null,}) {
  return _then(_WorkoutSession(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,userId: null == userId ? _self.userId : userId // ignore: cast_nullable_to_non_nullable
as String,routineId: freezed == routineId ? _self.routineId : routineId // ignore: cast_nullable_to_non_nullable
as String?,routineTitle: freezed == routineTitle ? _self.routineTitle : routineTitle // ignore: cast_nullable_to_non_nullable
as String?,startedAt: null == startedAt ? _self.startedAt : startedAt // ignore: cast_nullable_to_non_nullable
as DateTime,completedAt: freezed == completedAt ? _self.completedAt : completedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,synced: null == synced ? _self.synced : synced // ignore: cast_nullable_to_non_nullable
as bool,isDeleted: null == isDeleted ? _self.isDeleted : isDeleted // ignore: cast_nullable_to_non_nullable
as bool,updatedAt: null == updatedAt ? _self.updatedAt : updatedAt // ignore: cast_nullable_to_non_nullable
as DateTime,steps: null == steps ? _self._steps : steps // ignore: cast_nullable_to_non_nullable
as List<WorkoutStep>,
  ));
}


}

// dart format on
