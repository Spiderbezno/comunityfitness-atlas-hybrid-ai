// 🐦 Flutter imports:
import 'package:flutter/services.dart';

// 📦 Package imports:
import 'package:rive/rive.dart' as rive;
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'animation_cache_service.g.dart';

@riverpod
AnimationCacheService animationCacheService(Ref ref) {
  return AnimationCacheService();
}

class AnimationCacheService {
  final Map<String, rive.File> _cache = {};
  final Future<ByteData> Function(String path) _assetLoader;

  AnimationCacheService({Future<ByteData> Function(String path)? assetLoader}) : _assetLoader = assetLoader ?? rootBundle.load;

  Future<rive.File?> getRiveFile(String path) async {
    if (_cache.containsKey(path)) {
      return _cache[path];
    }

    try {
      final data = await _assetLoader(path);
      final bytes = data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes);
      final file = await rive.File.decode(bytes, riveFactory: rive.Factory.flutter);
      if (file != null) {
        _cache[path] = file;
      }
      return file;
    } catch (e) {
      // Graceful fallback for loading errors
      return null;
    }
  }

  bool isCached(String path) => _cache.containsKey(path);
}
