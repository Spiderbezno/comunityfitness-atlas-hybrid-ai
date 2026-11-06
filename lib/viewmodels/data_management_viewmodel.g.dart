// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'data_management_viewmodel.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(DataManagementViewModel)
final dataManagementViewModelProvider = DataManagementViewModelProvider._();

final class DataManagementViewModelProvider extends $NotifierProvider<DataManagementViewModel, DataManagementState> {
  DataManagementViewModelProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'dataManagementViewModelProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$dataManagementViewModelHash();

  @$internal
  @override
  DataManagementViewModel create() => DataManagementViewModel();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(DataManagementState value) {
    return $ProviderOverride(origin: this, providerOverride: $SyncValueProvider<DataManagementState>(value));
  }
}

String _$dataManagementViewModelHash() => r'dd1e4e1a54d17d038d3235c2d9a40ae4b583c387';

abstract class _$DataManagementViewModel extends $Notifier<DataManagementState> {
  DataManagementState build();
  @$mustCallSuper
  @override
  WhenComplete runBuild() {
    final ref = this.ref as $Ref<DataManagementState, DataManagementState>;
    final element =
        ref.element as $ClassProviderElement<AnyNotifier<DataManagementState, DataManagementState>, DataManagementState, Object?, Object?>;
    return element.handleCreate(ref, build);
  }
}
