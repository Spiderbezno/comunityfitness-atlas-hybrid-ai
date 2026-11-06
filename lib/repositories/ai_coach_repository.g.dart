// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'ai_coach_repository.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(aiCoachRepository)
final aiCoachRepositoryProvider = AiCoachRepositoryProvider._();

final class AiCoachRepositoryProvider extends $FunctionalProvider<AiCoachRepository, AiCoachRepository, AiCoachRepository>
    with $Provider<AiCoachRepository> {
  AiCoachRepositoryProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'aiCoachRepositoryProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$aiCoachRepositoryHash();

  @$internal
  @override
  $ProviderElement<AiCoachRepository> $createElement($ProviderPointer pointer) => $ProviderElement(pointer);

  @override
  AiCoachRepository create(Ref ref) {
    return aiCoachRepository(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AiCoachRepository value) {
    return $ProviderOverride(origin: this, providerOverride: $SyncValueProvider<AiCoachRepository>(value));
  }
}

String _$aiCoachRepositoryHash() => r'7b8c9d0e1f2a3b4c5d6e7f8091a2b3c4d5e6f708';
