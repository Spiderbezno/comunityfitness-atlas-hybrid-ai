// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'dashboard_viewmodel.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(DashboardViewModel)
final dashboardViewModelProvider = DashboardViewModelProvider._();

final class DashboardViewModelProvider extends $NotifierProvider<DashboardViewModel, DashboardState> {
  DashboardViewModelProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'dashboardViewModelProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$dashboardViewModelHash();

  @$internal
  @override
  DashboardViewModel create() => DashboardViewModel();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(DashboardState value) {
    return $ProviderOverride(origin: this, providerOverride: $SyncValueProvider<DashboardState>(value));
  }
}

String _$dashboardViewModelHash() => r'2171e60a8a7f7adef8e85cc14538e382c43ab9bf';

abstract class _$DashboardViewModel extends $Notifier<DashboardState> {
  DashboardState build();
  @$mustCallSuper
  @override
  WhenComplete runBuild() {
    final ref = this.ref as $Ref<DashboardState, DashboardState>;
    final element = ref.element as $ClassProviderElement<AnyNotifier<DashboardState, DashboardState>, DashboardState, Object?, Object?>;
    return element.handleCreate(ref, build);
  }
}
