// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/models/workout_step.dart';
import 'package:comunityfitness/services/data_import_export_service.dart';

void main() {
  group('DataImportExportService', () {
    final now = DateTime.utc(2026, 6, 23, 12, 0, 0);

    final testRoutine = Routine(
      id: 'r-1',
      title: 'Leg Day',
      description: 'Squats and lunges',
      createdAt: now,
      updatedAt: now,
      steps: [
        const WorkoutStep(exerciseId: 'ex-squat', sets: 4, reps: 8, weight: 100.0, targetDurationSeconds: 0, restDurationSeconds: 90, orderIndex: 0),
      ],
    );

    final testSession = WorkoutSession(
      id: 's-1',
      userId: 'user-1',
      routineId: 'r-1',
      routineTitle: 'Leg Day',
      startedAt: now,
      completedAt: now.add(const Duration(minutes: 50)),
      updatedAt: now,
      steps: testRoutine.steps,
    );

    const testExercise = Exercise(
      id: 'ex-squat',
      name: 'Barbell Squat',
      primaryMuscleGroup: 'Quads',
      equipment: 'Barbell',
      animationType: 'rive',
      animationPath: '',
      description: 'Deep squat',
    );

    test('exportToJson and importFromJson roundtrip maintains data integrity', () {
      final jsonString = DataImportExportService.exportToJson(routines: [testRoutine], sessions: [testSession], customExercises: [testExercise]);

      expect(jsonString, contains('Leg Day'));
      expect(jsonString, contains('Barbell Squat'));

      final result = DataImportExportService.importFromJson(jsonString);
      expect(result.routines.length, equals(1));
      expect(result.sessions.length, equals(1));
      expect(result.customExercises.length, equals(1));
      expect(result.routines.first.title, equals('Leg Day'));
      expect(result.sessions.first.routineTitle, equals('Leg Day'));
      expect(result.customExercises.first.name, equals('Barbell Squat'));
    });

    test('importFromHevyCsv successfully parses workouts and exercises', () {
      const csv = '''
title,start_time,end_time,description,exercise_title,superset_id,exercise_notes,set_index,set_type,weight_kg,reps,distance_km,duration_seconds,rpe
Chest Day,2026-07-01 10:00:00,2026-07-01 11:00:00,,Bench Press,,Heavy set,0,normal,80.0,8,,,8.5
Chest Day,2026-07-01 10:00:00,2026-07-01 11:00:00,,Bench Press,,Heavy set,1,normal,80.0,8,,,9.0
''';

      final result = DataImportExportService.importFromHevyCsv(csv);
      expect(result.sessions.length, equals(1));
      expect(result.sessions.first.routineTitle, equals('Chest Day'));
      expect(result.sessions.first.steps.length, equals(1));
      expect(result.sessions.first.steps.first.sets, equals(2));
      expect(result.customExercises.length, equals(1));
      expect(result.customExercises.first.name, equals('Bench Press'));
    });

    test('importFromStrongCsv successfully parses workouts and exercises', () {
      const csv = '''
Date,Workout Name,Exercise Name,Set Order,Weight,Weight Unit,Reps,RPE,Distance,Distance Unit,Seconds,Notes,Workout Notes,Workout Duration
2026-07-05 18:00:00,Pull Day,Lat Pulldown,1,60.0,kg,10,8.0,,,,,
2026-07-05 18:00:00,Pull Day,Lat Pulldown,2,65.0,kg,8,9.0,,,,,
''';

      final result = DataImportExportService.importFromStrongCsv(csv);
      expect(result.sessions.length, equals(1));
      expect(result.sessions.first.routineTitle, equals('Pull Day'));
      expect(result.sessions.first.steps.length, equals(1));
      expect(result.sessions.first.steps.first.sets, equals(2));
      expect(result.sessions.first.steps.first.weight, equals(65.0));
      expect(result.customExercises.first.name, equals('Lat Pulldown'));
    });
  });
}
