// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'atlas_ai_config_service.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(atlasAiConfigService)
final atlasAiConfigServiceProvider = AtlasAiConfigServiceProvider._();

final class AtlasAiConfigServiceProvider
    extends $FunctionalProvider<AtlasAiConfigService, AtlasAiConfigService, AtlasAiConfigService>
    with $Provider<AtlasAiConfigService> {
  AtlasAiConfigServiceProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'atlasAiConfigServiceProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$atlasAiConfigServiceHash();

  @$internal
  @override
  $ProviderElement<AtlasAiConfigService> $createElement($ProviderPointer pointer) => $ProviderElement(pointer);

  @override
  AtlasAiConfigService create(Ref ref) {
    return atlasAiConfigService(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AtlasAiConfigService value) {
    return $ProviderOverride(origin: this, providerOverride: $SyncValueProvider<AtlasAiConfigService>(value));
  }
}

String _$atlasAiConfigServiceHash() => r'9a4b8c2d1e5f67890123456789abcdef01234567';
