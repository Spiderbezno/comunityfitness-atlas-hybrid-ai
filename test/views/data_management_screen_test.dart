// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce/hive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/models/workout_step.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/repositories/routine_repository.dart';
import 'package:comunityfitness/repositories/session_repository.dart';
import 'package:comunityfitness/services/sync_service.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/views/data_management_screen.dart';

class FakeSyncService extends Fake implements SyncService {
  @override
  Future<void> syncAll() async {}
}

void main() {
  late Box<Routine> routineBox;
  late Box<WorkoutSession> sessionBox;
  late Box<Exercise> exerciseBox;
  late RoutineRepository routineRepo;
  late SessionRepository sessionRepo;
  late ExerciseRepository exerciseRepo;

  setUpAll(() async {
    final tempDir = '/tmp/hive_view_dm_${DateTime.now().millisecondsSinceEpoch}';
    Hive.init(tempDir);
    if (!Hive.isAdapterRegistered(2)) {
      Hive.registerAdapter(RoutineAdapter());
    }
    if (!Hive.isAdapterRegistered(4)) {
      Hive.registerAdapter(WorkoutSessionAdapter());
    }
    if (!Hive.isAdapterRegistered(3)) {
      Hive.registerAdapter(WorkoutStepAdapter());
    }
    if (!Hive.isAdapterRegistered(1)) {
      Hive.registerAdapter(ExerciseAdapter());
    }

    routineBox = await Hive.openBox<Routine>('test_routines_view_dm');
    sessionBox = await Hive.openBox<WorkoutSession>('test_sessions_view_dm');
    exerciseBox = await Hive.openBox<Exercise>('test_exercises_view_dm');

    routineRepo = RoutineRepository(routineBox: routineBox, syncService: FakeSyncService());
    sessionRepo = SessionRepository(sessionBox: sessionBox, syncService: FakeSyncService());
    exerciseRepo = ExerciseRepository(exerciseBox: exerciseBox);
  });

  tearDownAll(() async {
    await routineBox.close();
    await sessionBox.close();
    await exerciseBox.close();
  });

  tearDown(() async {
    await routineBox.clear();
    await sessionBox.clear();
    await exerciseBox.clear();
  });

  testWidgets('DataManagementScreen renders export and import options', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          routineRepositoryProvider.overrideWithValue(routineRepo),
          sessionRepositoryProvider.overrideWithValue(sessionRepo),
          exerciseRepositoryProvider.overrideWithValue(exerciseRepo),
        ],
        child: MaterialApp(theme: AppTheme.darkTheme, home: const DataManagementScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Data & Migration'), findsOneWidget);
    expect(find.text('Export Full JSON Backup'), findsOneWidget);
    expect(find.text('Import JSON Backup'), findsOneWidget);
    expect(find.text('Import from Hevy (CSV)'), findsOneWidget);
    expect(find.text('Import from Strong (CSV)'), findsOneWidget);
  });
}
