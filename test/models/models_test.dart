// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/models/user.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/models/workout_step.dart';

void main() {
  group('User Model', () {
    test('instantiates and serializes correctly', () {
      final now = DateTime.utc(2026, 6, 23, 12, 0, 0);
      final user = User(id: 'user-123', email: 'test@example.com', displayName: 'Test User', updatedAt: now, synced: false);

      expect(user.id, equals('user-123'));
      expect(user.email, equals('test@example.com'));
      expect(user.displayName, equals('Test User'));
      expect(user.updatedAt, equals(now));
      expect(user.synced, isFalse);

      final json = user.toJson();
      expect(json['id'], equals('user-123'));
      expect(json['email'], equals('test@example.com'));
      expect(json['displayName'], equals('Test User'));
      expect(json['updatedAt'], equals(now.toIso8601String()));
      expect(json['synced'], isFalse);

      final fromJson = User.fromJson(json);
      expect(fromJson, equals(user));
    });
  });

  group('Exercise Model', () {
    test('instantiates and serializes correctly', () {
      const exercise = Exercise(
        id: 'ex-1',
        name: 'Push-Up',
        primaryMuscleGroup: 'Chest',
        equipment: 'Bodyweight',
        animationType: 'rive',
        animationPath: 'assets/animations/push_up.riv',
        description: 'A standard push-up.',
      );

      expect(exercise.id, equals('ex-1'));
      expect(exercise.name, equals('Push-Up'));
      expect(exercise.primaryMuscleGroup, equals('Chest'));
      expect(exercise.equipment, equals('Bodyweight'));
      expect(exercise.animationType, equals('rive'));
      expect(exercise.animationPath, equals('assets/animations/push_up.riv'));
      expect(exercise.description, equals('A standard push-up.'));

      final json = exercise.toJson();
      expect(json['id'], equals('ex-1'));
      expect(json['name'], equals('Push-Up'));
      expect(json['primaryMuscleGroup'], equals('Chest'));

      final fromJson = Exercise.fromJson(json);
      expect(fromJson, equals(exercise));
    });
  });

  group('WorkoutStep Model', () {
    test('instantiates and serializes correctly', () {
      const step = WorkoutStep(exerciseId: 'ex-1', sets: 3, reps: 10, weight: 0.0, targetDurationSeconds: 45, restDurationSeconds: 60, orderIndex: 0);

      expect(step.exerciseId, equals('ex-1'));
      expect(step.sets, equals(3));
      expect(step.reps, equals(10));
      expect(step.weight, equals(0.0));
      expect(step.targetDurationSeconds, equals(45));
      expect(step.restDurationSeconds, equals(60));
      expect(step.orderIndex, equals(0));

      final json = step.toJson();
      expect(json['exerciseId'], equals('ex-1'));
      expect(json['sets'], equals(3));

      final fromJson = WorkoutStep.fromJson(json);
      expect(fromJson, equals(step));
    });
  });

  group('Routine Model', () {
    test('instantiates and serializes correctly', () {
      final now = DateTime.utc(2026, 6, 23, 12, 0, 0);
      const step = WorkoutStep(exerciseId: 'ex-1', sets: 3, reps: 10, weight: 0.0, targetDurationSeconds: 45, restDurationSeconds: 60, orderIndex: 0);
      final routine = Routine(
        id: 'routine-uuid',
        title: 'Morning Routine',
        description: 'Start the day active.',
        createdAt: now,
        updatedAt: now,
        synced: false,
        isDeleted: false,
        steps: [step],
      );

      expect(routine.id, equals('routine-uuid'));
      expect(routine.title, equals('Morning Routine'));
      expect(routine.steps, hasLength(1));
      expect(routine.steps.first.exerciseId, equals('ex-1'));

      final json = routine.toJson();
      expect(json['id'], equals('routine-uuid'));
      expect(json['title'], equals('Morning Routine'));

      final fromJson = Routine.fromJson(json);
      expect(fromJson, equals(routine));
    });
  });

  group('WorkoutSession Model', () {
    test('instantiates and serializes correctly', () {
      final now = DateTime.utc(2026, 6, 23, 12, 0, 0);
      const step = WorkoutStep(exerciseId: 'ex-1', sets: 3, reps: 10, weight: 0.0, targetDurationSeconds: 45, restDurationSeconds: 60, orderIndex: 0);
      final session = WorkoutSession(
        id: 'session-uuid',
        userId: 'user-123',
        routineId: 'routine-uuid',
        routineTitle: 'Morning Routine',
        startedAt: now,
        completedAt: now.add(const Duration(minutes: 30)),
        synced: false,
        isDeleted: false,
        updatedAt: now,
        steps: [step],
      );

      expect(session.id, equals('session-uuid'));
      expect(session.userId, equals('user-123'));
      expect(session.routineId, equals('routine-uuid'));
      expect(session.routineTitle, equals('Morning Routine'));
      expect(session.startedAt, equals(now));
      expect(session.completedAt, equals(now.add(const Duration(minutes: 30))));
      expect(session.synced, isFalse);
      expect(session.isDeleted, isFalse);
      expect(session.updatedAt, equals(now));
      expect(session.steps, hasLength(1));

      final json = session.toJson();
      expect(json['id'], equals('session-uuid'));
      expect(json['userId'], equals('user-123'));

      final fromJson = WorkoutSession.fromJson(json);
      expect(fromJson, equals(session));
    });
  });
}
