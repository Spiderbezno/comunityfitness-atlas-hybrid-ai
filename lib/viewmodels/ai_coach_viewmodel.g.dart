// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'ai_coach_viewmodel.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(AiCoachViewModel)
final aiCoachViewModelProvider = AiCoachViewModelProvider._();

final class AiCoachViewModelProvider extends $NotifierProvider<AiCoachViewModel, AiCoachState> {
  AiCoachViewModelProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'aiCoachViewModelProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$aiCoachViewModelHash();

  @$internal
  @override
  AiCoachViewModel create() => AiCoachViewModel();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AiCoachState value) {
    return $ProviderOverride(origin: this, providerOverride: $SyncValueProvider<AiCoachState>(value));
  }
}

String _$aiCoachViewModelHash() => r'3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d';

abstract class _$AiCoachViewModel extends $Notifier<AiCoachState> {
  AiCoachState build();
  @$mustCallSuper
  @override
  WhenComplete runBuild() {
    final ref = this.ref as $Ref<AiCoachState, AiCoachState>;
    final element = ref.element as $ClassProviderElement<AnyNotifier<AiCoachState, AiCoachState>, AiCoachState, Object?, Object?>;
    return element.handleCreate(ref, build);
  }
}
