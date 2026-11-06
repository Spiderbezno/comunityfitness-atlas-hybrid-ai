// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'muscle_analytics_viewmodel.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(MuscleAnalyticsViewModel)
final muscleAnalyticsViewModelProvider = MuscleAnalyticsViewModelProvider._();

final class MuscleAnalyticsViewModelProvider extends $NotifierProvider<MuscleAnalyticsViewModel, MuscleAnalyticsState> {
  MuscleAnalyticsViewModelProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'muscleAnalyticsViewModelProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$muscleAnalyticsViewModelHash();

  @$internal
  @override
  MuscleAnalyticsViewModel create() => MuscleAnalyticsViewModel();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(MuscleAnalyticsState value) {
    return $ProviderOverride(origin: this, providerOverride: $SyncValueProvider<MuscleAnalyticsState>(value));
  }
}

String _$muscleAnalyticsViewModelHash() => r'f452f99a5410a6a35949dee2ec5b8775aa5e3044';

abstract class _$MuscleAnalyticsViewModel extends $Notifier<MuscleAnalyticsState> {
  MuscleAnalyticsState build();
  @$mustCallSuper
  @override
  WhenComplete runBuild() {
    final ref = this.ref as $Ref<MuscleAnalyticsState, MuscleAnalyticsState>;
    final element =
        ref.element as $ClassProviderElement<AnyNotifier<MuscleAnalyticsState, MuscleAnalyticsState>, MuscleAnalyticsState, Object?, Object?>;
    return element.handleCreate(ref, build);
  }
}
