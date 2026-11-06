// 📦 Package imports:
import 'package:hive_ce_flutter/hive_ce_flutter.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/models/user.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/models/workout_step.dart';

part 'hive_service.g.dart';

@riverpod
HiveService hiveService(Ref ref) {
  throw UnimplementedError('hiveService must be overridden in ProviderScope');
}

class HiveService {
  final String? _subDir;

  // ignore: prefer_initializing_formals
  HiveService({String? subDir}) : _subDir = subDir;

  Future<void> init() async {
    if (_subDir != null) {
      Hive.init(_subDir);
    } else {
      await Hive.initFlutter();
    }

    _registerAdapters();
  }

  void _registerAdapters() {
    Hive.registerAdapter(UserAdapter());
    Hive.registerAdapter(ExerciseAdapter());
    Hive.registerAdapter(WorkoutStepAdapter());
    Hive.registerAdapter(RoutineAdapter());
    Hive.registerAdapter(WorkoutSessionAdapter());
  }

  Future<Box<User>> openUserBox() => Hive.openBox<User>('users');
  Future<Box<Exercise>> openExerciseBox() => Hive.openBox<Exercise>('exercises');
  Future<Box<Routine>> openRoutineBox() => Hive.openBox<Routine>('routines');
  Future<Box<WorkoutSession>> openSessionBox() => Hive.openBox<WorkoutSession>('sessions');
  Future<Box<dynamic>> openMetadataBox() => Hive.openBox('sync_metadata');

  Future<void> close() => Hive.close();
}
