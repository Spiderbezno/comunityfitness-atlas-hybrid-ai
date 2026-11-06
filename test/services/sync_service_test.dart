// ignore_for_file: subtype_of_sealed_class

// 🎯 Dart imports:
import 'dart:async';

// 📦 Package imports:
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart' as firebase_auth;
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce/hive.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/services/connectivity_service.dart';
import 'package:comunityfitness/services/sync_service.dart';

class MockBox<T> extends Mock implements Box<T> {}

class MockConnectivityService extends Mock implements ConnectivityService {}

class MockFirebaseAuth extends Mock implements firebase_auth.FirebaseAuth {}

class MockFirebaseFirestore extends Mock implements FirebaseFirestore {}

class MockUser extends Mock implements firebase_auth.User {}

class MockCollectionReference extends Mock implements CollectionReference<Map<String, dynamic>> {}

class MockDocumentReference extends Mock implements DocumentReference<Map<String, dynamic>> {}

class MockQuerySnapshot extends Mock implements QuerySnapshot<Map<String, dynamic>> {}

class MockQueryDocumentSnapshot extends Mock implements QueryDocumentSnapshot<Map<String, dynamic>> {}

class MockWriteBatch extends Mock implements WriteBatch {}

class MockQuery extends Mock implements Query<Map<String, dynamic>> {}

void main() {
  late MockBox<Routine> mockRoutineBox;
  late MockBox<WorkoutSession> mockSessionBox;
  late MockBox<dynamic> mockMetadataBox;
  late MockConnectivityService mockConnectivityService;
  late MockFirebaseAuth mockAuth;
  late MockFirebaseFirestore mockFirestore;
  late MockUser mockUser;
  late StreamController<bool> connectivityController;
  late SyncServiceImpl syncService;

  setUpAll(() {
    registerFallbackValue(Routine(id: 'dummy', title: 'Dummy', description: 'Desc', createdAt: DateTime(2026), updatedAt: DateTime(2026), steps: []));
    registerFallbackValue(WorkoutSession(id: 'dummy', userId: 'u1', startedAt: DateTime(2026), updatedAt: DateTime(2026), steps: []));
  });

  setUp(() {
    mockRoutineBox = MockBox<Routine>();
    mockSessionBox = MockBox<WorkoutSession>();
    mockMetadataBox = MockBox<dynamic>();
    mockConnectivityService = MockConnectivityService();
    mockAuth = MockFirebaseAuth();
    mockFirestore = MockFirebaseFirestore();
    mockUser = MockUser();
    connectivityController = StreamController<bool>.broadcast();

    when(() => mockAuth.currentUser).thenReturn(mockUser);
    when(() => mockUser.uid).thenReturn('user123');
    when(() => mockConnectivityService.onConnectivityChanged).thenAnswer((_) => connectivityController.stream);
    when(() => mockConnectivityService.isOnline).thenAnswer((_) async => true);

    // Default Firestore stubs to prevent null pointer exceptions during creation if a sync gets triggered
    final mockCollection = MockCollectionReference();
    final mockDoc = MockDocumentReference();
    when(() => mockFirestore.collection(any())).thenReturn(mockCollection);
    when(() => mockCollection.doc(any())).thenReturn(mockDoc);
    when(() => mockDoc.collection(any())).thenReturn(mockCollection);

    syncService = SyncServiceImpl(
      routineBox: mockRoutineBox,
      sessionBox: mockSessionBox,
      metadataBox: mockMetadataBox,
      connectivityService: mockConnectivityService,
      auth: mockAuth,
      firestore: mockFirestore,
    );
  });

  tearDown(() {
    connectivityController.close();
  });

  group('SyncService LWW Conflict Resolution (Pull)', () {
    test('overwrites local record when remote is newer', () async {
      final localRoutine = Routine(
        id: 'r1',
        title: 'Old Title',
        description: 'Old Description',
        createdAt: DateTime(2026, 1, 1),
        updatedAt: DateTime(2026, 1, 1),
        steps: [],
      );

      final remoteRoutine = Routine(
        id: 'r1',
        title: 'New Title',
        description: 'New Description',
        createdAt: DateTime(2026, 1, 1),
        updatedAt: DateTime(2026, 1, 2),
        steps: [],
      );

      when(() => mockRoutineBox.get('r1')).thenReturn(localRoutine);
      when(() => mockMetadataBox.get('lastSyncTime')).thenReturn(null);
      when(() => mockMetadataBox.put(any<dynamic>(), any<dynamic>())).thenAnswer((_) async {});
      when(() => mockRoutineBox.put(any<dynamic>(), any())).thenAnswer((_) async {});

      final mockUsersCollection = MockCollectionReference();
      final mockUserDoc = MockDocumentReference();
      final mockRoutinesCollection = MockCollectionReference();
      final mockSessionsCollection = MockCollectionReference();

      final mockRoutinesQuery = MockQuery();
      final mockRoutinesSnapshot = MockQuerySnapshot();
      final mockRoutineDocSnapshot = MockQueryDocumentSnapshot();

      final mockSessionsQuery = MockQuery();
      final mockSessionsSnapshot = MockQuerySnapshot();

      when(() => mockFirestore.collection('users')).thenReturn(mockUsersCollection);
      when(() => mockUsersCollection.doc('user123')).thenReturn(mockUserDoc);
      when(() => mockUserDoc.collection('routines')).thenReturn(mockRoutinesCollection);
      when(() => mockUserDoc.collection('sessions')).thenReturn(mockSessionsCollection);

      // Routines Query Stubs
      when(() => mockRoutinesCollection.where('updatedAt', isGreaterThan: any(named: 'isGreaterThan'))).thenReturn(mockRoutinesQuery);
      when(() => mockRoutinesQuery.get()).thenAnswer((_) async => mockRoutinesSnapshot);
      when(() => mockRoutinesSnapshot.docs).thenReturn([mockRoutineDocSnapshot]);
      when(() => mockRoutineDocSnapshot.data()).thenReturn(remoteRoutine.toJson());

      // Sessions Query Stubs (Empty)
      when(() => mockSessionsCollection.where('updatedAt', isGreaterThan: any(named: 'isGreaterThan'))).thenReturn(mockSessionsQuery);
      when(() => mockSessionsQuery.get()).thenAnswer((_) async => mockSessionsSnapshot);
      when(() => mockSessionsSnapshot.docs).thenReturn([]);

      await syncService.pullRemoteChanges();

      verify(
        () =>
            mockRoutineBox.put('r1', any(that: isA<Routine>().having((r) => r.title, 'title', 'New Title').having((r) => r.synced, 'synced', true))),
      ).called(1);
    });

    test('does not overwrite when local is newer or equal', () async {
      final localRoutine = Routine(
        id: 'r1',
        title: 'Local Newer',
        description: 'Desc',
        createdAt: DateTime(2026, 1, 2),
        updatedAt: DateTime(2026, 1, 2),
        steps: [],
      );

      final remoteRoutine = Routine(
        id: 'r1',
        title: 'Remote Older',
        description: 'Desc',
        createdAt: DateTime(2026, 1, 1),
        updatedAt: DateTime(2026, 1, 1),
        steps: [],
      );

      when(() => mockRoutineBox.get('r1')).thenReturn(localRoutine);
      when(() => mockMetadataBox.get('lastSyncTime')).thenReturn(null);
      when(() => mockMetadataBox.put(any<dynamic>(), any<dynamic>())).thenAnswer((_) async {});

      final mockUsersCollection = MockCollectionReference();
      final mockUserDoc = MockDocumentReference();
      final mockRoutinesCollection = MockCollectionReference();
      final mockSessionsCollection = MockCollectionReference();

      final mockRoutinesQuery = MockQuery();
      final mockRoutinesSnapshot = MockQuerySnapshot();
      final mockRoutineDocSnapshot = MockQueryDocumentSnapshot();

      final mockSessionsQuery = MockQuery();
      final mockSessionsSnapshot = MockQuerySnapshot();

      when(() => mockFirestore.collection('users')).thenReturn(mockUsersCollection);
      when(() => mockUsersCollection.doc('user123')).thenReturn(mockUserDoc);
      when(() => mockUserDoc.collection('routines')).thenReturn(mockRoutinesCollection);
      when(() => mockUserDoc.collection('sessions')).thenReturn(mockSessionsCollection);

      // Routines Query Stubs
      when(() => mockRoutinesCollection.where('updatedAt', isGreaterThan: any(named: 'isGreaterThan'))).thenReturn(mockRoutinesQuery);
      when(() => mockRoutinesQuery.get()).thenAnswer((_) async => mockRoutinesSnapshot);
      when(() => mockRoutinesSnapshot.docs).thenReturn([mockRoutineDocSnapshot]);
      when(() => mockRoutineDocSnapshot.data()).thenReturn(remoteRoutine.toJson());

      // Sessions Query Stubs (Empty)
      when(() => mockSessionsCollection.where('updatedAt', isGreaterThan: any(named: 'isGreaterThan'))).thenReturn(mockSessionsQuery);
      when(() => mockSessionsQuery.get()).thenAnswer((_) async => mockSessionsSnapshot);
      when(() => mockSessionsSnapshot.docs).thenReturn([]);

      await syncService.pullRemoteChanges();

      verifyNever(() => mockRoutineBox.put(any<dynamic>(), any()));
    });
  });

  group('SyncService Batch Push', () {
    test('pushes unsynced items in batches of 50', () async {
      final unsyncedRoutines = List.generate(
        52,
        (index) => Routine(
          id: 'r$index',
          title: 'Routine $index',
          description: 'Desc',
          createdAt: DateTime(2026, 1, 1),
          updatedAt: DateTime(2026, 1, 1),
          synced: false,
          steps: [],
        ),
      );

      when(() => mockRoutineBox.values).thenReturn(unsyncedRoutines);
      when(() => mockSessionBox.values).thenReturn([]);
      when(() => mockRoutineBox.put(any<dynamic>(), any())).thenAnswer((_) async {});

      final mockCollection = MockCollectionReference();
      final mockDoc = MockDocumentReference();
      final mockWriteBatch = MockWriteBatch();

      when(() => mockFirestore.collection('users')).thenReturn(mockCollection);
      when(() => mockCollection.doc(any())).thenReturn(mockDoc);
      when(() => mockDoc.collection(any())).thenReturn(mockCollection);
      when(() => mockCollection.doc(any())).thenReturn(mockDoc);
      when(() => mockFirestore.batch()).thenReturn(mockWriteBatch);
      when(() => mockWriteBatch.commit()).thenAnswer((_) async {});

      await syncService.pushLocalChanges();

      // Pushing 52 items requires 2 batch commits (50 + 2)
      verify(() => mockWriteBatch.commit()).called(2);
      verify(() => mockRoutineBox.put(any<dynamic>(), any(that: isA<Routine>().having((r) => r.synced, 'synced', true)))).called(52);
    });

    test('triggers syncAll when connection transitions from offline to online', () async {
      final mockCollection = MockCollectionReference();
      final mockDoc = MockDocumentReference();
      final mockQuery = MockQuery();
      final mockSnapshot = MockQuerySnapshot();

      when(() => mockFirestore.collection(any())).thenReturn(mockCollection);
      when(() => mockCollection.doc(any())).thenReturn(mockDoc);
      when(() => mockDoc.collection(any())).thenReturn(mockCollection);
      when(() => mockCollection.where(any(), isGreaterThan: any(named: 'isGreaterThan'))).thenReturn(mockQuery);
      when(() => mockQuery.get()).thenAnswer((_) async => mockSnapshot);
      when(() => mockSnapshot.docs).thenReturn([]);

      when(() => mockRoutineBox.values).thenReturn([]);
      when(() => mockSessionBox.values).thenReturn([]);
      when(() => mockMetadataBox.get('lastSyncTime')).thenReturn(null);
      when(() => mockMetadataBox.put(any<dynamic>(), any<dynamic>())).thenAnswer((_) async {});

      connectivityController.add(true);
      await Future<void>.delayed(Duration.zero);

      verify(() => mockConnectivityService.isOnline);
    });
  });
}
