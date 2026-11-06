// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:rive/rive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/repositories/routine_repository.dart';
import 'package:comunityfitness/services/connectivity_service.dart';
import 'package:comunityfitness/services/sync_service.dart';
import 'package:comunityfitness/views/exercise_catalog_screen.dart';
import 'package:comunityfitness/views/routine_editor_screen.dart';
import 'package:comunityfitness/views/routine_list_screen.dart';

class MockConnectivityService extends Mock implements ConnectivityService {}

class MockSyncService extends Mock implements SyncService {}

class MockRoutineRepository extends Mock implements RoutineRepository {}

class MockExerciseRepository extends Mock implements ExerciseRepository {}

void main() {
  late MockConnectivityService mockConnectivityService;
  late MockSyncService mockSyncService;
  late MockRoutineRepository mockRoutineRepository;
  late MockExerciseRepository mockExerciseRepository;

  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    await RiveNative.init();
  });

  setUp(() {
    mockConnectivityService = MockConnectivityService();
    mockSyncService = MockSyncService();
    mockRoutineRepository = MockRoutineRepository();
    mockExerciseRepository = MockExerciseRepository();

    when(() => mockConnectivityService.onConnectivityChanged).thenAnswer((_) => Stream.value(true));
    when(() => mockConnectivityService.isOnline).thenAnswer((_) async => true);
    when(() => mockSyncService.syncAll()).thenAnswer((_) async {});
    when(() => mockExerciseRepository.getExercises()).thenReturn([]);
    when(() => mockExerciseRepository.seedIfNeeded()).thenAnswer((_) async {});
  });

  testWidgets('Routine List displays routine items and the sync status indicator', (WidgetTester tester) async {
    final sampleRoutine = Routine(
      id: 'r1',
      title: 'Leg Day',
      description: 'Squats and lunges',
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
      synced: true,
      steps: [],
    );

    when(() => mockRoutineRepository.watchRoutines()).thenAnswer((_) => Stream.value([sampleRoutine]));

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          connectivityServiceProvider.overrideWithValue(mockConnectivityService),
          syncServiceProvider.overrideWithValue(mockSyncService),
          routineRepositoryProvider.overrideWithValue(mockRoutineRepository),
        ],
        child: const MaterialApp(home: RoutineListScreen()),
      ),
    );

    await tester.pumpAndSettle();

    // Verify routine item details
    expect(find.text('Leg Day'), findsOneWidget);
    expect(find.text('Squats and lunges'), findsOneWidget);

    // Verify sync state pill (Synced status)
    expect(find.text('Synced'), findsOneWidget);
  });

  testWidgets('Routine Editor shows validation error message on empty title submission', (WidgetTester tester) async {
    when(() => mockRoutineRepository.getRoutine(any())).thenReturn(null);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          routineRepositoryProvider.overrideWithValue(mockRoutineRepository),
          exerciseRepositoryProvider.overrideWithValue(mockExerciseRepository),
        ],
        child: const MaterialApp(home: RoutineEditorScreen()),
      ),
    );

    await tester.pumpAndSettle();

    // Tap Save button when title and steps are empty
    final saveButton = find.byType(FloatingActionButton);
    expect(saveButton, findsOneWidget);
    await tester.tap(saveButton);
    await tester.pumpAndSettle();

    // Verify validation error is displayed
    expect(find.text('Title cannot be empty'), findsOneWidget);
  });

  testWidgets('Exercise Catalog search input filters the exercise list', (WidgetTester tester) async {
    final exercisesList = [
      const Exercise(
        id: '1',
        name: 'Push Up',
        primaryMuscleGroup: 'Chest',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: '',
        description: 'Push up exercise',
      ),
      const Exercise(
        id: '2',
        name: 'Squat',
        primaryMuscleGroup: 'Legs',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: '',
        description: 'Squat exercise',
      ),
    ];

    when(() => mockExerciseRepository.seedIfNeeded()).thenAnswer((_) async {});
    when(() => mockExerciseRepository.getExercises()).thenReturn(exercisesList);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [exerciseRepositoryProvider.overrideWithValue(mockExerciseRepository)],
        child: const MaterialApp(home: ExerciseCatalogScreen()),
      ),
    );

    await tester.pumpAndSettle();

    // Check both are initially visible
    expect(find.text('Push Up'), findsOneWidget);
    expect(find.text('Squat'), findsOneWidget);

    // Enter search text "Push"
    final searchField = find.byKey(const Key('exercise_search_field'));
    expect(searchField, findsOneWidget);
    await tester.enterText(searchField, 'Push');
    await tester.pumpAndSettle();

    // Verify "Push Up" is still visible, but "Squat" is filtered out
    expect(find.text('Push Up'), findsOneWidget);
    expect(find.text('Squat'), findsNothing);
  });
}
