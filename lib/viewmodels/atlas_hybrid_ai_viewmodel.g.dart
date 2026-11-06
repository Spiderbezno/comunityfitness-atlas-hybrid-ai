// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'atlas_hybrid_ai_viewmodel.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(AtlasHybridAiViewModel)
final atlasHybridAiViewModelProvider = AtlasHybridAiViewModelProvider._();

final class AtlasHybridAiViewModelProvider
    extends $NotifierProvider<AtlasHybridAiViewModel, AtlasHybridAiState> {
  AtlasHybridAiViewModelProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'atlasHybridAiViewModelProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$atlasHybridAiViewModelHash();

  @$internal
  @override
  AtlasHybridAiViewModel create() => AtlasHybridAiViewModel();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AtlasHybridAiState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<AtlasHybridAiState>(value),
    );
  }
}

String _$atlasHybridAiViewModelHash() => r'4a9d8c7b6e5f1234567890abcdef1234567890ab';

abstract class _$AtlasHybridAiViewModel extends $Notifier<AtlasHybridAiState> {
  AtlasHybridAiState build();
  @$mustCallSuper
  @override
  WhenComplete runBuild() {
    final ref = this.ref as $Ref<AtlasHybridAiState, AtlasHybridAiState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AtlasHybridAiState, AtlasHybridAiState>,
              AtlasHybridAiState,
              Object?,
              Object?
            >;
    return element.handleCreate(ref, build);
  }
}
