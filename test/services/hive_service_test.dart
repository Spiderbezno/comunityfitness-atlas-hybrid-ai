// 🎯 Dart imports:
import 'dart:io';

// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';

// 🌎 Project imports:
import 'package:comunityfitness/services/hive_service.dart';

void main() {
  late Directory tempDir;
  late HiveService hiveService;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('hive_test');
    hiveService = HiveService(subDir: tempDir.path);
  });

  tearDown(() async {
    await hiveService.close();
    if (tempDir.existsSync()) {
      tempDir.deleteSync(recursive: true);
    }
  });

  test('HiveService initializes and opens all boxes', () async {
    await hiveService.init();

    final userBox = await hiveService.openUserBox();
    expect(userBox.isOpen, isTrue);
    expect(userBox.isEmpty, isTrue);

    final exerciseBox = await hiveService.openExerciseBox();
    expect(exerciseBox.isOpen, isTrue);

    final routineBox = await hiveService.openRoutineBox();
    expect(routineBox.isOpen, isTrue);

    final sessionBox = await hiveService.openSessionBox();
    expect(sessionBox.isOpen, isTrue);

    final metadataBox = await hiveService.openMetadataBox();
    expect(metadataBox.isOpen, isTrue);
  });
}
