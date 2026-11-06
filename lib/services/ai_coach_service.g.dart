// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'ai_coach_service.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(aiCoachService)
final aiCoachServiceProvider = AiCoachServiceProvider._();

final class AiCoachServiceProvider extends $FunctionalProvider<AiCoachService, AiCoachService, AiCoachService> with $Provider<AiCoachService> {
  AiCoachServiceProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'aiCoachServiceProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$aiCoachServiceHash();

  @$internal
  @override
  $ProviderElement<AiCoachService> $createElement($ProviderPointer pointer) => $ProviderElement(pointer);

  @override
  AiCoachService create(Ref ref) {
    return aiCoachService(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AiCoachService value) {
    return $ProviderOverride(origin: this, providerOverride: $SyncValueProvider<AiCoachService>(value));
  }
}

String _$aiCoachServiceHash() => r'9a4b7d21c6e8f0123456789abcdef0123456789a';
