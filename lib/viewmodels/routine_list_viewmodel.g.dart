// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'routine_list_viewmodel.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(RoutineListViewModel)
final routineListViewModelProvider = RoutineListViewModelProvider._();

final class RoutineListViewModelProvider extends $StreamNotifierProvider<RoutineListViewModel, List<Routine>> {
  RoutineListViewModelProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'routineListViewModelProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$routineListViewModelHash();

  @$internal
  @override
  RoutineListViewModel create() => RoutineListViewModel();
}

String _$routineListViewModelHash() => r'd028cfc21b41dc9de89f827ed8dfa2cd947ebfa3';

abstract class _$RoutineListViewModel extends $StreamNotifier<List<Routine>> {
  Stream<List<Routine>> build();
  @$mustCallSuper
  @override
  WhenComplete runBuild() {
    final ref = this.ref as $Ref<AsyncValue<List<Routine>>, List<Routine>>;
    final element =
        ref.element as $ClassProviderElement<AnyNotifier<AsyncValue<List<Routine>>, List<Routine>>, AsyncValue<List<Routine>>, Object?, Object?>;
    return element.handleCreate(ref, build);
  }
}
