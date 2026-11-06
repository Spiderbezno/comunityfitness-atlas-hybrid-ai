// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'active_workout_viewmodel.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(ActiveWorkoutViewModel)
final activeWorkoutViewModelProvider = ActiveWorkoutViewModelProvider._();

final class ActiveWorkoutViewModelProvider extends $NotifierProvider<ActiveWorkoutViewModel, ActiveWorkoutState> {
  ActiveWorkoutViewModelProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'activeWorkoutViewModelProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$activeWorkoutViewModelHash();

  @$internal
  @override
  ActiveWorkoutViewModel create() => ActiveWorkoutViewModel();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ActiveWorkoutState value) {
    return $ProviderOverride(origin: this, providerOverride: $SyncValueProvider<ActiveWorkoutState>(value));
  }
}

String _$activeWorkoutViewModelHash() => r'62ed9887df83c2ae96a29f01bb21a5dfadd83075';

abstract class _$ActiveWorkoutViewModel extends $Notifier<ActiveWorkoutState> {
  ActiveWorkoutState build();
  @$mustCallSuper
  @override
  WhenComplete runBuild() {
    final ref = this.ref as $Ref<ActiveWorkoutState, ActiveWorkoutState>;
    final element = ref.element as $ClassProviderElement<AnyNotifier<ActiveWorkoutState, ActiveWorkoutState>, ActiveWorkoutState, Object?, Object?>;
    return element.handleCreate(ref, build);
  }
}
