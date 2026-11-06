// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'exercise_catalog_viewmodel.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(ExerciseCatalogViewModel)
final exerciseCatalogViewModelProvider = ExerciseCatalogViewModelProvider._();

final class ExerciseCatalogViewModelProvider extends $NotifierProvider<ExerciseCatalogViewModel, ExerciseCatalogState> {
  ExerciseCatalogViewModelProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'exerciseCatalogViewModelProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$exerciseCatalogViewModelHash();

  @$internal
  @override
  ExerciseCatalogViewModel create() => ExerciseCatalogViewModel();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ExerciseCatalogState value) {
    return $ProviderOverride(origin: this, providerOverride: $SyncValueProvider<ExerciseCatalogState>(value));
  }
}

String _$exerciseCatalogViewModelHash() => r'48167eb97eb5c88be57fc41e9cf6f4d7df7668d2';

abstract class _$ExerciseCatalogViewModel extends $Notifier<ExerciseCatalogState> {
  ExerciseCatalogState build();
  @$mustCallSuper
  @override
  WhenComplete runBuild() {
    final ref = this.ref as $Ref<ExerciseCatalogState, ExerciseCatalogState>;
    final element =
        ref.element as $ClassProviderElement<AnyNotifier<ExerciseCatalogState, ExerciseCatalogState>, ExerciseCatalogState, Object?, Object?>;
    return element.handleCreate(ref, build);
  }
}
