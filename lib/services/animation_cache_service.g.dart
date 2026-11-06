// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'animation_cache_service.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(animationCacheService)
final animationCacheServiceProvider = AnimationCacheServiceProvider._();

final class AnimationCacheServiceProvider extends $FunctionalProvider<AnimationCacheService, AnimationCacheService, AnimationCacheService>
    with $Provider<AnimationCacheService> {
  AnimationCacheServiceProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'animationCacheServiceProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$animationCacheServiceHash();

  @$internal
  @override
  $ProviderElement<AnimationCacheService> $createElement($ProviderPointer pointer) => $ProviderElement(pointer);

  @override
  AnimationCacheService create(Ref ref) {
    return animationCacheService(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AnimationCacheService value) {
    return $ProviderOverride(origin: this, providerOverride: $SyncValueProvider<AnimationCacheService>(value));
  }
}

String _$animationCacheServiceHash() => r'e941a3070454ee4b6799e35d5c76e796245ed4de';
