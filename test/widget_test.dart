// 🐦 Flutter imports:
import 'package:flutter/material.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:rive/rive.dart';

// 🌎 Project imports:
import 'package:comunityfitness/main.dart';
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/repositories/routine_repository.dart';
import 'package:comunityfitness/repositories/session_repository.dart';
import 'package:comunityfitness/services/connectivity_service.dart';
import 'package:comunityfitness/services/sync_service.dart';
import 'package:comunityfitness/views/dashboard_screen.dart';

class MockConnectivityService extends Mock implements ConnectivityService {}

class MockSyncService extends Mock implements SyncService {}

class MockRoutineRepository extends Mock implements RoutineRepository {}

class MockExerciseRepository extends Mock implements ExerciseRepository {}

class MockSessionRepository extends Mock implements SessionRepository {}

void main() {
  late MockConnectivityService mockConnectivityService;
  late MockSyncService mockSyncService;
  late MockRoutineRepository mockRoutineRepository;
  late MockExerciseRepository mockExerciseRepository;
  late MockSessionRepository mockSessionRepository;

  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    await RiveNative.init();
  });

  setUp(() {
    mockConnectivityService = MockConnectivityService();
    mockSyncService = MockSyncService();
    mockRoutineRepository = MockRoutineRepository();
    mockExerciseRepository = MockExerciseRepository();
    mockSessionRepository = MockSessionRepository();

    when(() => mockConnectivityService.onConnectivityChanged).thenAnswer((_) => Stream.value(true));
    when(() => mockConnectivityService.isOnline).thenAnswer((_) async => true);
    when(() => mockSyncService.syncAll()).thenAnswer((_) async {});
    when(() => mockRoutineRepository.getRoutines()).thenReturn([]);
    when(() => mockRoutineRepository.watchRoutines()).thenAnswer((_) => Stream.value([]));
    when(() => mockExerciseRepository.getExercises()).thenReturn([]);
    when(() => mockExerciseRepository.seedIfNeeded()).thenAnswer((_) async {});
    when(() => mockSessionRepository.getSessions()).thenReturn([]);
    when(() => mockSessionRepository.watchSessions()).thenAnswer((_) => Stream.value([]));
  });

  testWidgets('Electric Slate theme and DashboardScreen home test', (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          connectivityServiceProvider.overrideWithValue(mockConnectivityService),
          syncServiceProvider.overrideWithValue(mockSyncService),
          routineRepositoryProvider.overrideWithValue(mockRoutineRepository),
          exerciseRepositoryProvider.overrideWithValue(mockExerciseRepository),
          sessionRepositoryProvider.overrideWithValue(mockSessionRepository),
        ],
        child: const MyApp(),
      ),
    );

    await tester.pumpAndSettle();

    // Verify home is DashboardScreen
    expect(find.byType(DashboardScreen), findsOneWidget);

    // Verify theme colors inside DashboardScreen
    final BuildContext context = tester.element(find.byType(DashboardScreen));
    final theme = Theme.of(context);

    expect(theme.brightness, Brightness.dark);
    expect(theme.scaffoldBackgroundColor, const Color(0xFF0E1015));
    expect(theme.colorScheme.primary, const Color(0xFFFF5400));
    expect(theme.colorScheme.secondary, const Color(0xFF38BDF8));
    expect(theme.colorScheme.surface, const Color(0xFF161920));
  });
}
