// 📦 Package imports:
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/services/firebase_service.dart';

class MockFirebaseAuth extends Mock implements FirebaseAuth {}

class MockFirebaseFirestore extends Mock implements FirebaseFirestore {}

void main() {
  group('FirebaseService', () {
    test('returns injected instances', () {
      final mockAuth = MockFirebaseAuth();
      final mockFirestore = MockFirebaseFirestore();

      final firebaseService = FirebaseService(auth: mockAuth, firestore: mockFirestore);

      expect(firebaseService.auth, equals(mockAuth));
      expect(firebaseService.firestore, equals(mockFirestore));
    });
  });
}
