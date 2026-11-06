// ignore_for_file: prefer_initializing_formals

// 🎯 Dart imports:
import 'dart:async';

// 📦 Package imports:
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart' as firebase_auth;
import 'package:hive_ce/hive.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/services/connectivity_service.dart';
import 'package:comunityfitness/services/firebase_service.dart';

part 'sync_service.g.dart';

@riverpod
SyncService syncService(Ref ref) {
  final routineBox = Hive.box<Routine>('routines');
  final sessionBox = Hive.box<WorkoutSession>('sessions');
  final metadataBox = Hive.box<dynamic>('sync_metadata');
  final connectivity = ref.read(connectivityServiceProvider);
  final firebase = ref.read(firebaseServiceProvider);

  final service = SyncServiceImpl(
    routineBox: routineBox,
    sessionBox: sessionBox,
    metadataBox: metadataBox,
    connectivityService: connectivity,
    auth: firebase.auth,
    firestore: firebase.firestore,
  );
  ref.onDispose(service.dispose);
  return service;
}

abstract class SyncService {
  Future<void> syncAll();
  Future<void> pullRemoteChanges();
  Future<void> pushLocalChanges();
}

class SyncServiceImpl implements SyncService {
  final Box<Routine> _routineBox;
  final Box<WorkoutSession> _sessionBox;
  final Box<dynamic> _metadataBox;
  final ConnectivityService _connectivityService;
  final firebase_auth.FirebaseAuth _auth;
  final FirebaseFirestore _firestore;
  StreamSubscription<bool>? _connectivitySubscription;
  bool _isSyncing = false;

  SyncServiceImpl({
    required Box<Routine> routineBox,
    required Box<WorkoutSession> sessionBox,
    required Box<dynamic> metadataBox,
    required ConnectivityService connectivityService,
    required firebase_auth.FirebaseAuth auth,
    required FirebaseFirestore firestore,
  }) : _routineBox = routineBox,
       _sessionBox = sessionBox,
       _metadataBox = metadataBox,
       _connectivityService = connectivityService,
       _auth = auth,
       _firestore = firestore {
    _connectivitySubscription = _connectivityService.onConnectivityChanged.listen((isOnline) async {
      if (isOnline) {
        try {
          await syncAll();
        } catch (_) {}
      }
    });
  }

  void dispose() {
    _connectivitySubscription?.cancel();
    _connectivitySubscription = null;
  }

  Map<String, dynamic> _convertFirestoreToMap(Map<String, dynamic> data) {
    final copy = Map<String, dynamic>.from(data);
    copy.forEach((key, value) {
      if (value is Timestamp) {
        copy[key] = value.toDate().toIso8601String();
      } else if (value is Map<String, dynamic>) {
        copy[key] = _convertFirestoreToMap(value);
      } else if (value is List) {
        copy[key] = value.map((item) {
          if (item is Map<String, dynamic>) {
            return _convertFirestoreToMap(item);
          }
          return item;
        }).toList();
      }
    });
    return copy;
  }

  @override
  Future<void> syncAll() async {
    if (_isSyncing) {
      return;
    }
    _isSyncing = true;
    try {
      if (!await _connectivityService.isOnline) {
        return;
      }
      await pullRemoteChanges();
      await pushLocalChanges();
    } finally {
      _isSyncing = false;
    }
  }

  @override
  Future<void> pullRemoteChanges() async {
    final userId = _auth.currentUser?.uid;
    if (userId == null) {
      return;
    }

    final lastSyncStr = _metadataBox.get('lastSyncTime') as String?;
    final lastSyncTime = lastSyncStr != null ? DateTime.parse(lastSyncStr).toUtc() : DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);

    final currentSyncTime = DateTime.now().toUtc();

    // 1. Pull routines
    final routinesRef = _firestore.collection('users').doc(userId).collection('routines');

    final queryRoutines = await routinesRef.where('updatedAt', isGreaterThan: lastSyncTime.toIso8601String()).get();

    for (final doc in queryRoutines.docs) {
      final data = _convertFirestoreToMap(doc.data());
      final remoteRoutine = Routine.fromJson(data);
      final localRoutine = _routineBox.get(remoteRoutine.id);

      if (localRoutine == null || remoteRoutine.updatedAt.isAfter(localRoutine.updatedAt)) {
        await _routineBox.put(remoteRoutine.id, remoteRoutine.copyWith(synced: true));
      }
    }

    // 2. Pull sessions
    final sessionsRef = _firestore.collection('users').doc(userId).collection('sessions');

    final querySessions = await sessionsRef.where('updatedAt', isGreaterThan: lastSyncTime.toIso8601String()).get();

    for (final doc in querySessions.docs) {
      final data = _convertFirestoreToMap(doc.data());
      final remoteSession = WorkoutSession.fromJson(data);
      final localSession = _sessionBox.get(remoteSession.id);

      if (localSession == null || remoteSession.updatedAt.isAfter(localSession.updatedAt)) {
        await _sessionBox.put(remoteSession.id, remoteSession.copyWith(synced: true));
      }
    }

    await _metadataBox.put('lastSyncTime', currentSyncTime.toIso8601String());
  }

  @override
  Future<void> pushLocalChanges() async {
    final userId = _auth.currentUser?.uid;
    if (userId == null) {
      return;
    }

    final unsyncedRoutines = _routineBox.values.where((r) => !r.synced).toList();
    final unsyncedSessions = _sessionBox.values.where((s) => !s.synced).toList();

    final List<dynamic> allUnsynced = [...unsyncedRoutines, ...unsyncedSessions];
    if (allUnsynced.isEmpty) {
      return;
    }

    for (var i = 0; i < allUnsynced.length; i += 50) {
      final end = (i + 50 > allUnsynced.length) ? allUnsynced.length : i + 50;
      final chunk = allUnsynced.sublist(i, end);

      final nowUtc = DateTime.now().toUtc();
      final batch = _firestore.batch();
      for (final item in chunk) {
        if (item is Routine) {
          final docRef = _firestore.collection('users').doc(userId).collection('routines').doc(item.id);
          batch.set(docRef, {...item.toJson(), 'synced': true, 'updatedAt': nowUtc.toIso8601String()});
        } else if (item is WorkoutSession) {
          final docRef = _firestore.collection('users').doc(userId).collection('sessions').doc(item.id);
          batch.set(docRef, {...item.toJson(), 'synced': true, 'updatedAt': nowUtc.toIso8601String()});
        }
      }

      await batch.commit();

      for (final item in chunk) {
        if (item is Routine) {
          final latest = _routineBox.get(item.id) ?? item;
          if (!latest.updatedAt.isAfter(item.updatedAt)) {
            await _routineBox.put(item.id, latest.copyWith(synced: true, updatedAt: nowUtc));
          }
        } else if (item is WorkoutSession) {
          final latest = _sessionBox.get(item.id) ?? item;
          if (!latest.updatedAt.isAfter(item.updatedAt)) {
            await _sessionBox.put(item.id, latest.copyWith(synced: true, updatedAt: nowUtc));
          }
        }
      }
    }
  }
}
