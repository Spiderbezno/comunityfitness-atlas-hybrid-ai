// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'sync_viewmodel.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(SyncViewModel)
final syncViewModelProvider = SyncViewModelProvider._();

final class SyncViewModelProvider extends $NotifierProvider<SyncViewModel, SyncViewModelState> {
  SyncViewModelProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'syncViewModelProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$syncViewModelHash();

  @$internal
  @override
  SyncViewModel create() => SyncViewModel();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(SyncViewModelState value) {
    return $ProviderOverride(origin: this, providerOverride: $SyncValueProvider<SyncViewModelState>(value));
  }
}

String _$syncViewModelHash() => r'b2736160f890c27fd4d9c6271aa9193146ba7820';

abstract class _$SyncViewModel extends $Notifier<SyncViewModelState> {
  SyncViewModelState build();
  @$mustCallSuper
  @override
  WhenComplete runBuild() {
    final ref = this.ref as $Ref<SyncViewModelState, SyncViewModelState>;
    final element = ref.element as $ClassProviderElement<AnyNotifier<SyncViewModelState, SyncViewModelState>, SyncViewModelState, Object?, Object?>;
    return element.handleCreate(ref, build);
  }
}
