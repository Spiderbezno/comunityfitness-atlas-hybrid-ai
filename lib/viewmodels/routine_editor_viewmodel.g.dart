// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'routine_editor_viewmodel.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(RoutineEditorViewModel)
final routineEditorViewModelProvider = RoutineEditorViewModelFamily._();

final class RoutineEditorViewModelProvider extends $NotifierProvider<RoutineEditorViewModel, RoutineEditorState> {
  RoutineEditorViewModelProvider._({required RoutineEditorViewModelFamily super.from, required String? super.argument})
    : super(retry: null, name: r'routineEditorViewModelProvider', isAutoDispose: true, dependencies: null, $allTransitiveDependencies: null);

  @override
  String debugGetCreateSourceHash() => _$routineEditorViewModelHash();

  @override
  String toString() {
    return r'routineEditorViewModelProvider'
        ''
        '($argument)';
  }

  @$internal
  @override
  RoutineEditorViewModel create() => RoutineEditorViewModel();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(RoutineEditorState value) {
    return $ProviderOverride(origin: this, providerOverride: $SyncValueProvider<RoutineEditorState>(value));
  }

  @override
  bool operator ==(Object other) {
    return other is RoutineEditorViewModelProvider && other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$routineEditorViewModelHash() => r'fc8ccb7f958eb6491dc1eb2e74ecf072d433c76e';

final class RoutineEditorViewModelFamily extends $Family
    with $ClassFamilyOverride<RoutineEditorViewModel, RoutineEditorState, RoutineEditorState, RoutineEditorState, String?> {
  RoutineEditorViewModelFamily._()
    : super(retry: null, name: r'routineEditorViewModelProvider', dependencies: null, $allTransitiveDependencies: null, isAutoDispose: true);

  RoutineEditorViewModelProvider call(String? routineId) => RoutineEditorViewModelProvider._(argument: routineId, from: this);

  @override
  String toString() => r'routineEditorViewModelProvider';
}

abstract class _$RoutineEditorViewModel extends $Notifier<RoutineEditorState> {
  late final _$args = ref.$arg as String?;
  String? get routineId => _$args;

  RoutineEditorState build(String? routineId);
  @$mustCallSuper
  @override
  WhenComplete runBuild() {
    final ref = this.ref as $Ref<RoutineEditorState, RoutineEditorState>;
    final element = ref.element as $ClassProviderElement<AnyNotifier<RoutineEditorState, RoutineEditorState>, RoutineEditorState, Object?, Object?>;
    return element.handleCreate(ref, () => build(_$args));
  }
}
