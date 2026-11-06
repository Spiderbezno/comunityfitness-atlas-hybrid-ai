// 🎯 Dart imports:
import 'dart:convert';

// 📦 Package imports:
import 'package:firebase_auth/firebase_auth.dart';
import 'package:uuid/uuid.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/exercise.dart';
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/models/workout_step.dart';

class ImportResult {
  final List<Routine> routines;
  final List<WorkoutSession> sessions;
  final List<Exercise> customExercises;
  final int totalImported;
  final List<String> warnings;

  const ImportResult({
    required this.routines,
    required this.sessions,
    required this.customExercises,
    required this.totalImported,
    this.warnings = const [],
  });
}

/// Data Import and Export Service
///
/// Handles full JSON backups, openGym payload compatibility,
/// and CSV migration from popular apps (Hevy, Strong, FitNotes).
class DataImportExportService {
  const DataImportExportService._();

  static const _uuid = Uuid();

  static String _resolveCurrentUserId() {
    try {
      final uid = FirebaseAuth.instance.currentUser?.uid;
      if (uid != null && uid.trim().isNotEmpty) {
        return uid;
      }
    } catch (_) {}
    return 'local-user';
  }

  static DateTime? _tryParseWorkoutDate(String? raw) {
    if (raw == null) {
      return null;
    }
    final trimmed = raw.trim();
    if (trimmed.isEmpty) {
      return null;
    }
    final iso = DateTime.tryParse(trimmed);
    if (iso != null) {
      return iso;
    }
    final hevyMatch = RegExp(r'^(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})[,\s]+(\d{1,2}):(\d{2})(?::(\d{2}))?').firstMatch(trimmed);
    if (hevyMatch != null) {
      const months = <String, int>{
        'jan': 1,
        'feb': 2,
        'mar': 3,
        'apr': 4,
        'may': 5,
        'jun': 6,
        'jul': 7,
        'aug': 8,
        'sep': 9,
        'oct': 10,
        'nov': 11,
        'dec': 12,
      };
      final day = int.tryParse(hevyMatch.group(1)!);
      final monthKey = hevyMatch.group(2)!.toLowerCase().substring(0, 3);
      final month = months[monthKey];
      final year = int.tryParse(hevyMatch.group(3)!);
      final hour = int.tryParse(hevyMatch.group(4)!) ?? 0;
      final minute = int.tryParse(hevyMatch.group(5)!) ?? 0;
      final second = hevyMatch.group(6) != null ? (int.tryParse(hevyMatch.group(6)!) ?? 0) : 0;
      if (day != null && month != null && year != null) {
        return DateTime(year, month, day, hour, minute, second);
      }
    }
    return null;
  }

  static DateTime _parseWorkoutDate(String raw) {
    return _tryParseWorkoutDate(raw) ?? DateTime.now();
  }

  static List<WorkoutStep> _aggregateSessionSteps(List<Map<String, dynamic>> rows) {
    final Map<String, ({int sets, int reps, double weight})> aggregatedByExercise = {};
    final List<String> exerciseOrder = [];
    for (final r in rows) {
      final exName = r['exercise'] as String;
      final exSlug = 'imported-${exName.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'), '-')}';
      final rowReps = r['reps'] as int;
      final rowWeight = r['weight'] as double;
      final existing = aggregatedByExercise[exSlug];
      if (existing == null) {
        exerciseOrder.add(exSlug);
        aggregatedByExercise[exSlug] = (sets: 1, reps: rowReps, weight: rowWeight);
      } else {
        final useNewBest = rowWeight > existing.weight || (rowWeight == existing.weight && rowReps > existing.reps);
        aggregatedByExercise[exSlug] = (
          sets: existing.sets + 1,
          reps: useNewBest ? rowReps : existing.reps,
          weight: useNewBest ? rowWeight : existing.weight,
        );
      }
    }

    final List<WorkoutStep> steps = [];
    for (int sIdx = 0; sIdx < exerciseOrder.length; sIdx++) {
      final exSlug = exerciseOrder[sIdx];
      final agg = aggregatedByExercise[exSlug]!;
      steps.add(
        WorkoutStep(
          exerciseId: exSlug,
          sets: agg.sets,
          reps: agg.reps,
          weight: agg.weight,
          targetDurationSeconds: 0,
          restDurationSeconds: 60,
          orderIndex: sIdx,
        ),
      );
    }
    return steps;
  }

  /// Exports current app data into a standardized JSON backup string.
  static String exportToJson({required List<Routine> routines, required List<WorkoutSession> sessions, required List<Exercise> customExercises}) {
    final payload = {
      'version': '1.0.0',
      'exportedAt': DateTime.now().toIso8601String(),
      'routines': routines.map((r) => r.toJson()).toList(),
      'sessions': sessions.map((s) => s.toJson()).toList(),
      'customExercises': customExercises.map((e) => e.toJson()).toList(),
    };
    return const JsonEncoder.withIndent('  ').convert(payload);
  }

  /// Imports from JSON backup string.
  static ImportResult importFromJson(String jsonString) {
    final dynamic decoded = jsonDecode(jsonString);
    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('Invalid JSON root format');
    }

    final routinesJson = decoded['routines'] as List<dynamic>? ?? [];
    final sessionsJson = decoded['sessions'] as List<dynamic>? ?? [];
    final exercisesJson = decoded['customExercises'] as List<dynamic>? ?? [];

    final routines = routinesJson.map((r) => Routine.fromJson(r as Map<String, dynamic>)).toList();
    final sessions = sessionsJson.map((s) => WorkoutSession.fromJson(s as Map<String, dynamic>)).toList();
    final customExercises = exercisesJson.map((e) => Exercise.fromJson(e as Map<String, dynamic>)).toList();

    return ImportResult(
      routines: routines,
      sessions: sessions,
      customExercises: customExercises,
      totalImported: routines.length + sessions.length + customExercises.length,
    );
  }

  /// Imports historical workout logs from Hevy CSV export.
  ///
  /// Columns: title, start_time, end_time, description, exercise_title,
  /// superset_id, exercise_notes, set_index, set_type, weight_kg, reps, distance_km, duration_seconds, rpe
  static ImportResult importFromHevyCsv(String csvContent) {
    final lines = const LineSplitter().convert(csvContent.replaceFirst('\uFEFF', '').trim());
    if (lines.isEmpty) {
      return const ImportResult(routines: [], sessions: [], customExercises: [], totalImported: 0);
    }

    final header = _splitCsvLine(lines.first.replaceFirst('\uFEFF', '').toLowerCase()).map((h) => h.trim()).toList();
    final titleIdx = header.indexOf('title');
    final startTimeIdx = header.indexOf('start_time');
    final endTimeIdx = header.indexOf('end_time');
    final exerciseIdx = header.indexOf('exercise_title');
    final weightIdx = header.indexOf('weight_kg');
    final repsIdx = header.indexOf('reps');
    final rpeIdx = header.indexOf('rpe');

    if (startTimeIdx == -1 || exerciseIdx == -1) {
      throw const FormatException('Unrecognized Hevy CSV format: missing required columns.');
    }

    final Map<String, List<Map<String, dynamic>>> sessionBuckets = {};
    final Set<String> foundExerciseNames = {};

    for (int i = 1; i < lines.length; i++) {
      final line = lines[i].trim();
      if (line.isEmpty) {
        continue;
      }
      final cols = _splitCsvLine(line);
      if (cols.length <= mathMax(startTimeIdx, exerciseIdx)) {
        continue;
      }

      final title = titleIdx != -1 && titleIdx < cols.length ? cols[titleIdx] : 'Hevy Workout';
      final startTimeStr = cols[startTimeIdx];
      final endTimeStr = endTimeIdx != -1 && endTimeIdx < cols.length ? cols[endTimeIdx] : '';
      final exerciseName = cols[exerciseIdx];
      final weight = weightIdx != -1 && weightIdx < cols.length ? double.tryParse(cols[weightIdx]) ?? 0.0 : 0.0;
      final reps = repsIdx != -1 && repsIdx < cols.length ? int.tryParse(cols[repsIdx]) ?? 0 : 0;
      final rpe = rpeIdx != -1 && rpeIdx < cols.length ? double.tryParse(cols[rpeIdx]) : null;

      foundExerciseNames.add(exerciseName);

      final sessionKey = '$startTimeStr||$title';
      sessionBuckets.putIfAbsent(sessionKey, () => []).add({
        'title': title,
        'startTime': startTimeStr,
        'endTime': endTimeStr,
        'exercise': exerciseName,
        'weight': weight,
        'reps': reps,
        'rpe': rpe,
      });
    }

    final List<WorkoutSession> sessions = [];
    final List<Exercise> customExercises = foundExerciseNames.map((name) {
      final slug = name.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'), '-');
      return Exercise(
        id: 'imported-$slug',
        name: name,
        primaryMuscleGroup: 'Full Body',
        equipment: 'Other',
        animationType: 'rive',
        animationPath: '',
        description: 'Imported from Hevy',
      );
    }).toList();

    final resolvedUserId = _resolveCurrentUserId();
    for (final entry in sessionBuckets.entries) {
      final rows = entry.value;
      if (rows.isEmpty) {
        continue;
      }
      final first = rows.first;
      final startedAt = _parseWorkoutDate(first['startTime'] as String);
      final completedAt = _tryParseWorkoutDate(first['endTime'] as String?);
      final title = first['title'] as String;
      final steps = _aggregateSessionSteps(rows);

      sessions.add(
        WorkoutSession(
          id: _uuid.v4(),
          userId: resolvedUserId,
          routineTitle: title,
          startedAt: startedAt,
          completedAt: completedAt,
          updatedAt: startedAt,
          steps: steps,
        ),
      );
    }

    return ImportResult(routines: [], sessions: sessions, customExercises: customExercises, totalImported: sessions.length);
  }

  /// Imports from Strong CSV export.
  static ImportResult importFromStrongCsv(String csvContent) {
    final lines = const LineSplitter().convert(csvContent.replaceFirst('\uFEFF', '').trim());
    if (lines.isEmpty) {
      return const ImportResult(routines: [], sessions: [], customExercises: [], totalImported: 0);
    }

    final header = _splitCsvLine(lines.first.replaceFirst('\uFEFF', '').toLowerCase()).map((h) => h.trim()).toList();
    final dateIdx = header.indexOf('date');
    final workoutNameIdx = header.indexOf('workout name');
    final exerciseIdx = header.indexOf('exercise name');
    final weightIdx = header.indexOf('weight');
    final repsIdx = header.indexOf('reps');

    if (dateIdx == -1 || exerciseIdx == -1) {
      throw const FormatException('Unrecognized Strong CSV format: missing Date or Exercise Name');
    }

    final Map<String, List<Map<String, dynamic>>> sessionBuckets = {};
    final Set<String> foundExerciseNames = {};

    for (int i = 1; i < lines.length; i++) {
      final line = lines[i].trim();
      if (line.isEmpty) {
        continue;
      }
      final cols = _splitCsvLine(line);
      if (cols.length <= mathMax(dateIdx, exerciseIdx)) {
        continue;
      }

      final dateStr = cols[dateIdx];
      final workoutName = workoutNameIdx != -1 && workoutNameIdx < cols.length ? cols[workoutNameIdx] : 'Strong Workout';
      final exerciseName = cols[exerciseIdx];
      final weight = weightIdx != -1 && weightIdx < cols.length ? double.tryParse(cols[weightIdx]) ?? 0.0 : 0.0;
      final reps = repsIdx != -1 && repsIdx < cols.length ? int.tryParse(cols[repsIdx]) ?? 0 : 0;

      foundExerciseNames.add(exerciseName);

      final key = '$dateStr||$workoutName';
      sessionBuckets.putIfAbsent(key, () => []).add({
        'date': dateStr,
        'title': workoutName,
        'exercise': exerciseName,
        'weight': weight,
        'reps': reps,
      });
    }

    final List<WorkoutSession> sessions = [];
    final List<Exercise> customExercises = foundExerciseNames.map((name) {
      final slug = name.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'), '-');
      return Exercise(
        id: 'imported-$slug',
        name: name,
        primaryMuscleGroup: 'Full Body',
        equipment: 'Other',
        animationType: 'rive',
        animationPath: '',
        description: 'Imported from Strong',
      );
    }).toList();

    final resolvedUserId = _resolveCurrentUserId();
    for (final entry in sessionBuckets.entries) {
      final rows = entry.value;
      if (rows.isEmpty) {
        continue;
      }
      final first = rows.first;
      final startedAt = _parseWorkoutDate(first['date'] as String);
      final title = first['title'] as String;
      final steps = _aggregateSessionSteps(rows);

      sessions.add(
        WorkoutSession(
          id: _uuid.v4(),
          userId: resolvedUserId,
          routineTitle: title,
          startedAt: startedAt,
          completedAt: startedAt.add(const Duration(minutes: 45)),
          updatedAt: startedAt,
          steps: steps,
        ),
      );
    }

    return ImportResult(routines: [], sessions: sessions, customExercises: customExercises, totalImported: sessions.length);
  }

  static int mathMax(int a, int b) => a > b ? a : b;

  static List<String> _splitCsvLine(String line) {
    final List<String> result = [];
    final StringBuffer current = StringBuffer();
    bool inQuotes = false;

    for (int i = 0; i < line.length; i++) {
      final char = line[i];
      if (char == '"') {
        inQuotes = !inQuotes;
      } else if (char == ',' && !inQuotes) {
        result.add(current.toString().trim());
        current.clear();
      } else {
        current.write(char);
      }
    }
    result.add(current.toString().trim());
    return result;
  }
}
