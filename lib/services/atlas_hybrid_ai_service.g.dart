// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'atlas_hybrid_ai_service.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(atlasHybridAiService)
final atlasHybridAiServiceProvider = AtlasHybridAiServiceProvider._();

final class AtlasHybridAiServiceProvider
    extends $FunctionalProvider<AtlasHybridAiService, AtlasHybridAiService, AtlasHybridAiService>
    with $Provider<AtlasHybridAiService> {
  AtlasHybridAiServiceProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'atlasHybridAiServiceProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$atlasHybridAiServiceHash();

  @$internal
  @override
  $ProviderElement<AtlasHybridAiService> $createElement($ProviderPointer pointer) => $ProviderElement(pointer);

  @override
  AtlasHybridAiService create(Ref ref) {
    return atlasHybridAiService(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AtlasHybridAiService value) {
    return $ProviderOverride(origin: this, providerOverride: $SyncValueProvider<AtlasHybridAiService>(value));
  }
}

String _$atlasHybridAiServiceHash() => r'7f1c2e3b4a5d6890123456789abcdef012345678';
