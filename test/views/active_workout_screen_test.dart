// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce/hive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/i18n/strings.g.dart';
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/models/workout_step.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/repositories/routine_repository.dart';
import 'package:comunityfitness/repositories/session_repository.dart';
import 'package:comunityfitness/services/sync_service.dart';
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/viewmodels/active_workout_viewmodel.dart';
import 'package:comunityfitness/views/active_workout_screen.dart';
import 'package:comunityfitness/views/dashboard_screen.dart';

class FakeSyncService extends Fake implements SyncService {
  @override
  Future<void> syncAll() async {}
}

class FakeRoutineRepository extends Fake implements RoutineRepository {
  @override
  List<Routine> getRoutines() => const [];

  @override
  Stream<List<Routine>> watchRoutines() => const Stream.empty();
}

class InMemorySessionRepository extends Fake implements SessionRepository {
  final List<WorkoutSession> _sessions = [];

  @override
  List<WorkoutSession> getSessions() => _sessions.where((s) => !s.isDeleted).toList();

  @override
  Future<void> saveSession(WorkoutSession session) async {
    _sessions.add(session);
  }

  @override
  Future<void> deleteSession(String id) async {
    _sessions.removeWhere((s) => s.id == id);
  }

  @override
  Stream<List<WorkoutSession>> watchSessions() => Stream.value(getSessions());
}

class FakeExerciseRepository extends Fake implements ExerciseRepository {
  @override
  Future<void> seedIfNeeded() async {}

  @override
  List<Exercise> getExercises() => const [
    Exercise(
      id: 'dumbbell_row',
      name: 'One-Arm Dumbbell Row',
      primaryMuscleGroup: 'Back',
      equipment: 'Dumbbell',
      animationType: 'rive',
      animationPath: 'assets/animations/dumbbell_row.riv',
      description: 'Single-arm row',
    ),
    Exercise(
      id: 'ex-bench',
      name: 'Bench Press',
      primaryMuscleGroup: 'Chest',
      equipment: 'Barbell',
      animationType: 'rive',
      animationPath: '',
      description: 'Flat barbell bench press',
    ),
    Exercise(
      id: 'dumbbell_bench_press',
      name: 'Dumbbell Bench Press',
      primaryMuscleGroup: 'Chest',
      equipment: 'Dumbbell',
      animationType: 'rive',
      animationPath: '',
      description: 'Flat dumbbell press',
    ),
  ];
}

void main() {
  late Box<WorkoutSession> sessionBox;
  late SessionRepository sessionRepo;

  setUpAll(() async {
    final tempDir = '/tmp/hive_view_active_${DateTime.now().millisecondsSinceEpoch}';
    Hive.init(tempDir);
    if (!Hive.isAdapterRegistered(4)) {
      Hive.registerAdapter(WorkoutSessionAdapter());
    }
    if (!Hive.isAdapterRegistered(3)) {
      Hive.registerAdapter(WorkoutStepAdapter());
    }

    sessionBox = await Hive.openBox<WorkoutSession>('test_sessions_view_active');
    sessionRepo = SessionRepository(sessionBox: sessionBox, syncService: FakeSyncService());
  });

  tearDownAll(() async {
    await sessionBox.close();
  });

  tearDown(() async {
    LocaleSettings.setLocale(AppLocale.en);
    await sessionBox.clear();
  });

  testWidgets('ActiveWorkoutScreen renders active exercises and allows set completion', (tester) async {
    final container = ProviderContainer(overrides: [sessionRepositoryProvider.overrideWithValue(sessionRepo)]);
    addTearDown(container.dispose);

    final vm = container.read(activeWorkoutViewModelProvider.notifier);
    final routine = Routine(
      id: 'r-1',
      title: 'Power Upper',
      description: 'Bench and Rows',
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      steps: [
        const WorkoutStep(exerciseId: 'ex-bench', sets: 3, reps: 8, weight: 80.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 0),
      ],
    );

    final exerciseMap = {
      'ex-bench': const Exercise(
        id: 'ex-bench',
        name: 'Bench Press',
        primaryMuscleGroup: 'Chest',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: '',
        description: 'Flat bench',
      ),
    };

    vm.startFromRoutine(routine, exerciseMap);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(theme: AppTheme.darkTheme, home: const ActiveWorkoutScreen()),
      ),
    );
    await tester.pump();

    expect(find.text('Power Upper'), findsOneWidget);
    expect(find.text('Bench Press'), findsOneWidget);
    expect(find.text('80.0 kg'), findsOneWidget);

    // Complete a set
    vm.toggleSetCompleted(0);
    await tester.pump();

    expect(find.text('1 / 3'), findsOneWidget);
    expect(find.text('REST TIMER'), findsOneWidget);
    expect(find.text('60s'), findsOneWidget);

    container.dispose();
  });

  testWidgets('Freestyle Add Exercise button opens selector and adds chosen exercise', (tester) async {
    final container = ProviderContainer(
      overrides: [sessionRepositoryProvider.overrideWithValue(sessionRepo), exerciseRepositoryProvider.overrideWithValue(FakeExerciseRepository())],
    );
    addTearDown(container.dispose);

    final vm = container.read(activeWorkoutViewModelProvider.notifier);
    vm.startFreestyle();

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(theme: AppTheme.darkTheme, home: const ActiveWorkoutScreen()),
      ),
    );
    await tester.pump();

    expect(find.text('No exercises in session'), findsOneWidget);
    expect(find.text('Add Exercise'), findsOneWidget);

    await tester.tap(find.text('Add Exercise'));
    await tester.pumpAndSettle();

    expect(find.text('Select Exercise'), findsOneWidget);
    expect(find.text('One-Arm Dumbbell Row'), findsOneWidget);

    await tester.tap(find.text('One-Arm Dumbbell Row'));
    await tester.pumpAndSettle();

    expect(find.text('No exercises in session'), findsNothing);
    expect(find.text('One-Arm Dumbbell Row'), findsOneWidget);
    expect(find.text('Add Exercise'), findsOneWidget);

    container.dispose();
  });

  testWidgets('ActiveWorkoutScreen displays Progressive Overload Autopilot badge and supports 1-tap Busy Machine Swap', (tester) async {
    final now = DateTime.now();
    await tester.runAsync(() async {
      await sessionRepo.saveSession(
        WorkoutSession(
          id: 'hist-1',
          userId: 'local-user',
          routineId: 'r-1',
          routineTitle: 'Power Upper',
          startedAt: now.subtract(const Duration(days: 3)),
          completedAt: now.subtract(const Duration(days: 3)),
          updatedAt: now.subtract(const Duration(days: 3)),
          steps: const [
            WorkoutStep(exerciseId: 'ex-bench', sets: 3, reps: 8, weight: 80.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 0),
          ],
        ),
      );
    });

    final container = ProviderContainer(
      overrides: [sessionRepositoryProvider.overrideWithValue(sessionRepo), exerciseRepositoryProvider.overrideWithValue(FakeExerciseRepository())],
    );
    addTearDown(container.dispose);

    final vm = container.read(activeWorkoutViewModelProvider.notifier);
    final routine = Routine(
      id: 'r-1',
      title: 'Power Upper',
      description: 'Bench',
      createdAt: now,
      updatedAt: now,
      steps: const [
        WorkoutStep(exerciseId: 'ex-bench', sets: 3, reps: 8, weight: 80.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 0),
      ],
    );

    final exerciseMap = {
      'ex-bench': const Exercise(
        id: 'ex-bench',
        name: 'Bench Press',
        primaryMuscleGroup: 'Chest',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: 'assets/animations/bench_press.riv',
        description: 'Flat bench',
      ),
    };

    vm.startFromRoutine(routine, exerciseMap);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(theme: AppTheme.darkTheme, home: const ActiveWorkoutScreen()),
      ),
    );
    await tester.pump();

    expect(find.byKey(const Key('autopilot_badge_0')), findsOneWidget);
    expect(find.text('+2.5 kg Autopilot'), findsOneWidget);
    expect(find.text('82.5 kg'), findsOneWidget);

    expect(find.byKey(const Key('busy_machine_swap_button_0')), findsOneWidget);
    await tester.tap(find.byKey(const Key('busy_machine_swap_button_0')));
    await tester.pump();

    expect(find.text('Dumbbell Bench Press'), findsOneWidget);
    expect(find.byKey(const Key('swap_reason_badge_0')), findsOneWidget);
    expect(find.textContaining('Swapped from Bench Press'), findsOneWidget);

    container.dispose();
  });

  testWidgets('ActiveWorkoutScreen renders Ghost Partner HUD Banner and opens Anatomical Summary Sheet on Finish', (tester) async {
    final inMemorySessionRepo = InMemorySessionRepository();
    final container = ProviderContainer(
      overrides: [
        sessionRepositoryProvider.overrideWithValue(inMemorySessionRepo),
        exerciseRepositoryProvider.overrideWithValue(FakeExerciseRepository()),
      ],
    );
    addTearDown(container.dispose);

    final vm = container.read(activeWorkoutViewModelProvider.notifier);
    final routine = Routine(
      id: 'r-ghost',
      title: 'Chest Blast',
      description: 'Bench Press',
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      steps: const [
        WorkoutStep(exerciseId: 'ex-bench', sets: 2, reps: 10, weight: 80.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 0),
      ],
    );

    final exerciseMap = {
      'ex-bench': const Exercise(
        id: 'ex-bench',
        name: 'Bench Press',
        primaryMuscleGroup: 'Chest',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: '',
        description: 'Flat bench press',
      ),
    };

    vm.startFromRoutine(routine, exerciseMap);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(theme: AppTheme.darkTheme, home: const ActiveWorkoutScreen()),
      ),
    );
    await tester.pump();

    expect(find.byKey(const Key('ghost_partner_hud_banner')), findsOneWidget);
    expect(find.byKey(const Key('ghost_partner_delta_badge')), findsOneWidget);
    expect(find.text('On Pace'), findsOneWidget);

    // Complete 1 set (800 kg vs 760 kg benchmark target -> +40 kg Ahead)
    vm.toggleSetCompleted(0);
    vm.skipRestTimer();
    await tester.pump();

    expect(find.textContaining('Ahead'), findsOneWidget);

    // Tap Finish button to open WorkoutAnatomicalSummarySheet
    await tester.tap(find.text('Finish'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.byKey(const Key('workout_anatomical_summary_sheet')), findsOneWidget);
    expect(find.byKey(const Key('summary_ghost_outcome_badge')), findsOneWidget);
    expect(find.byKey(const Key('summary_muscle_chip_Chest')), findsOneWidget);

    container.dispose();
  });

  testWidgets('ActiveWorkoutScreen and WorkoutAnatomicalSummarySheet localize in ES on narrow 320x640 screen without overflow', (tester) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    LocaleSettings.setLocale(AppLocale.es);
    final inMemorySessionRepo = InMemorySessionRepository();
    final container = ProviderContainer(
      overrides: [
        sessionRepositoryProvider.overrideWithValue(inMemorySessionRepo),
        exerciseRepositoryProvider.overrideWithValue(FakeExerciseRepository()),
      ],
    );
    addTearDown(container.dispose);

    final vm = container.read(activeWorkoutViewModelProvider.notifier);
    final routine = Routine(
      id: 'r-es',
      title: 'Pecho Fuerza',
      description: 'Bench Press',
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      steps: const [
        WorkoutStep(exerciseId: 'ex-bench', sets: 2, reps: 10, weight: 80.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 0),
      ],
    );

    final exerciseMap = {
      'ex-bench': const Exercise(
        id: 'ex-bench',
        name: 'Bench Press',
        primaryMuscleGroup: 'Chest',
        equipment: 'Barbell',
        animationType: 'rive',
        animationPath: '',
        description: 'Flat bench press',
      ),
    };

    vm.startFromRoutine(routine, exerciseMap);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: TranslationProvider(
          child: MaterialApp(theme: AppTheme.darkTheme, home: const ActiveWorkoutScreen()),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('En Ritmo'), findsOneWidget);
    expect(find.text('Máquina Ocupada · Cambiar'), findsOneWidget);
    expect(find.text('Finalizar'), findsOneWidget);

    vm.toggleSetCompleted(0);
    vm.skipRestTimer();
    await tester.pump();

    await tester.tap(find.text('Finalizar'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.text('TARJETA ANATÓMICA DE ENTRENO'), findsOneWidget);
    expect(find.byKey(const Key('summary_muscle_chip_Chest')), findsOneWidget);
    expect(tester.takeException(), isNull);

    container.dispose();
  });

  testWidgets(
    'Tapping Finish on empty Freestyle workout pops ActiveWorkoutScreen without opening WorkoutAnatomicalSummarySheet, and DashboardScreen deletes 0-exercise session immediately while requiring confirmation for non-empty session',
    (tester) async {
      final inMemorySessionRepo = InMemorySessionRepository();
      final now = DateTime(2026, 5, 1, 10);
      await inMemorySessionRepo.saveSession(
        WorkoutSession(
          id: 'sess-empty-0',
          userId: 'local-user',
          routineTitle: 'Accidental Empty Freestyle',
          startedAt: now.subtract(const Duration(minutes: 45)),
          completedAt: now.subtract(const Duration(minutes: 44)),
          updatedAt: now.subtract(const Duration(minutes: 44)),
          steps: const [],
        ),
      );
      await inMemorySessionRepo.saveSession(
        WorkoutSession(
          id: 'sess-del-1',
          userId: 'local-user',
          routineTitle: 'Prior Leg Day',
          startedAt: now.subtract(const Duration(minutes: 30)),
          completedAt: now,
          updatedAt: now,
          steps: const [
            WorkoutStep(exerciseId: 'ex-bench', sets: 3, reps: 10, weight: 60.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 0),
          ],
        ),
      );

      final container = ProviderContainer(
        overrides: [
          sessionRepositoryProvider.overrideWithValue(inMemorySessionRepo),
          routineRepositoryProvider.overrideWithValue(FakeRoutineRepository()),
          exerciseRepositoryProvider.overrideWithValue(FakeExerciseRepository()),
        ],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: TranslationProvider(
            child: MaterialApp(theme: AppTheme.darkTheme, home: const DashboardScreen()),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verify both recent sessions are rendered
      expect(find.text('Accidental Empty Freestyle'), findsOneWidget);
      expect(find.text('Prior Leg Day'), findsOneWidget);
      expect(find.byKey(const Key('delete_recent_session_sess-empty-0')), findsOneWidget);
      expect(find.byKey(const Key('delete_recent_session_sess-del-1')), findsOneWidget);

      // Start Freestyle workout from Dashboard
      await tester.tap(find.text('Start Freestyle'));
      await tester.pumpAndSettle();

      expect(find.text('Freestyle Workout'), findsOneWidget);
      expect(find.text('No exercises in session'), findsOneWidget);
      expect(find.byKey(const Key('active_workout_finish_button')), findsOneWidget);

      // Tap Finish with 0 completed exercises -> pops back to Dashboard without opening WorkoutAnatomicalSummarySheet
      await tester.tap(find.byKey(const Key('active_workout_finish_button')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('workout_anatomical_summary_sheet')), findsNothing);
      expect(find.text('COMMUNITY FITNESS'), findsOneWidget);
      expect(inMemorySessionRepo.getSessions().length, equals(2));

      // 1. Delete the 0-exercise session -> deletes immediately without confirmation dialog
      await tester.ensureVisible(find.byKey(const Key('delete_recent_session_sess-empty-0')));
      await tester.tap(find.byKey(const Key('delete_recent_session_sess-empty-0')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('confirm_delete_session_dialog')), findsNothing);
      expect(find.text('Accidental Empty Freestyle'), findsNothing);
      expect(inMemorySessionRepo.getSessions().length, equals(1));

      // 2. Delete the non-empty session (> 0 exercises) -> prompts confirmation dialog first
      await tester.ensureVisible(find.byKey(const Key('delete_recent_session_sess-del-1')));
      await tester.tap(find.byKey(const Key('delete_recent_session_sess-del-1')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('confirm_delete_session_dialog')), findsOneWidget);

      // Cancel keeps the session intact
      await tester.tap(find.byKey(const Key('cancel_delete_session_button')));
      await tester.pumpAndSettle();
      expect(find.text('Prior Leg Day'), findsOneWidget);
      expect(inMemorySessionRepo.getSessions().length, equals(1));

      // Confirm deletes the session
      await tester.tap(find.byKey(const Key('delete_recent_session_sess-del-1')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('confirm_delete_session_button')));
      await tester.pumpAndSettle();

      expect(find.text('Prior Leg Day'), findsNothing);
      expect(inMemorySessionRepo.getSessions(), isEmpty);

      container.dispose();
    },
  );
}
