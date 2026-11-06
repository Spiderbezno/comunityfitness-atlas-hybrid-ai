// 📦 Package imports:
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/repositories/exercise_repository.dart';
import 'package:comunityfitness/repositories/routine_repository.dart';
import 'package:comunityfitness/repositories/session_repository.dart';
import 'package:comunityfitness/services/data_import_export_service.dart';
import 'package:comunityfitness/viewmodels/dashboard_viewmodel.dart';
import 'package:comunityfitness/viewmodels/exercise_catalog_viewmodel.dart';
import 'package:comunityfitness/viewmodels/muscle_analytics_viewmodel.dart';
import 'package:comunityfitness/viewmodels/routine_list_viewmodel.dart';

part 'data_management_viewmodel.g.dart';

class DataManagementState {
  final bool isProcessing;
  final String? successMessage;
  final String? errorMessage;
  final int totalRoutines;
  final int totalSessions;
  final int totalExercises;

  const DataManagementState({
    this.isProcessing = false,
    this.successMessage,
    this.errorMessage,
    this.totalRoutines = 0,
    this.totalSessions = 0,
    this.totalExercises = 0,
  });

  DataManagementState copyWith({
    bool? isProcessing,
    String? successMessage,
    String? errorMessage,
    int? totalRoutines,
    int? totalSessions,
    int? totalExercises,
  }) {
    return DataManagementState(
      isProcessing: isProcessing ?? this.isProcessing,
      successMessage: successMessage,
      errorMessage: errorMessage,
      totalRoutines: totalRoutines ?? this.totalRoutines,
      totalSessions: totalSessions ?? this.totalSessions,
      totalExercises: totalExercises ?? this.totalExercises,
    );
  }
}

@Riverpod(keepAlive: true)
class DataManagementViewModel extends _$DataManagementViewModel {
  @override
  DataManagementState build() {
    final routineRepo = ref.watch(routineRepositoryProvider);
    final sessionRepo = ref.watch(sessionRepositoryProvider);
    final exerciseRepo = ref.watch(exerciseRepositoryProvider);

    void refreshCounts() {
      state = state.copyWith(
        successMessage: state.successMessage,
        errorMessage: state.errorMessage,
        totalRoutines: routineRepo.getRoutines().length,
        totalSessions: sessionRepo.getSessions().length,
        totalExercises: exerciseRepo.getExercises().length,
      );
    }

    try {
      final routineSub = routineRepo.watchRoutines().skip(1).listen((_) => refreshCounts());
      ref.onDispose(routineSub.cancel);
    } catch (_) {}
    try {
      final sessionSub = sessionRepo.watchSessions().skip(1).listen((_) => refreshCounts());
      ref.onDispose(sessionSub.cancel);
    } catch (_) {}
    try {
      final exerciseSub = exerciseRepo.watchExercises().skip(1).listen((_) => refreshCounts());
      ref.onDispose(exerciseSub.cancel);
    } catch (_) {}

    return DataManagementState(
      totalRoutines: routineRepo.getRoutines().length,
      totalSessions: sessionRepo.getSessions().length,
      totalExercises: exerciseRepo.getExercises().length,
    );
  }

  String exportFullBackupJson() {
    final routineRepo = ref.read(routineRepositoryProvider);
    final sessionRepo = ref.read(sessionRepositoryProvider);
    final exerciseRepo = ref.read(exerciseRepositoryProvider);

    return DataImportExportService.exportToJson(
      routines: routineRepo.getRoutines(),
      sessions: sessionRepo.getSessions(),
      customExercises: exerciseRepo.getExercises(),
    );
  }

  Future<ImportResult> importBackupJson(String jsonString) async {
    state = state.copyWith(isProcessing: true, errorMessage: null, successMessage: null);
    try {
      final result = DataImportExportService.importFromJson(jsonString);
      await _persistImportResult(result);

      state = state.copyWith(isProcessing: false, successMessage: 'Successfully imported ${result.totalImported} items!');
      return result;
    } catch (e) {
      state = state.copyWith(isProcessing: false, errorMessage: 'Import failed: $e');
      rethrow;
    }
  }

  Future<ImportResult> importHevyCsv(String csvContent) async {
    state = state.copyWith(isProcessing: true, errorMessage: null, successMessage: null);
    try {
      final result = DataImportExportService.importFromHevyCsv(csvContent);
      await _persistImportResult(result);

      state = state.copyWith(isProcessing: false, successMessage: 'Imported ${result.sessions.length} workouts from Hevy!');
      return result;
    } catch (e) {
      state = state.copyWith(isProcessing: false, errorMessage: 'Hevy import failed: $e');
      rethrow;
    }
  }

  Future<ImportResult> importStrongCsv(String csvContent) async {
    state = state.copyWith(isProcessing: true, errorMessage: null, successMessage: null);
    try {
      final result = DataImportExportService.importFromStrongCsv(csvContent);
      await _persistImportResult(result);

      state = state.copyWith(isProcessing: false, successMessage: 'Imported ${result.sessions.length} workouts from Strong!');
      return result;
    } catch (e) {
      state = state.copyWith(isProcessing: false, errorMessage: 'Strong import failed: $e');
      rethrow;
    }
  }

  Future<void> _persistImportResult(ImportResult result) async {
    final routineRepo = ref.read(routineRepositoryProvider);
    final sessionRepo = ref.read(sessionRepositoryProvider);
    final exerciseRepo = ref.read(exerciseRepositoryProvider);

    await routineRepo.saveRoutinesBatch(result.routines);
    await sessionRepo.saveSessionsBatch(result.sessions);
    for (final e in result.customExercises) {
      await exerciseRepo.saveExercise(e);
    }

    state = state.copyWith(
      totalRoutines: routineRepo.getRoutines().length,
      totalSessions: sessionRepo.getSessions().length,
      totalExercises: exerciseRepo.getExercises().length,
    );

    ref.invalidate(dashboardViewModelProvider);
    ref.invalidate(muscleAnalyticsViewModelProvider);
    ref.invalidate(exerciseCatalogViewModelProvider);
    ref.invalidate(routineListViewModelProvider);
  }
}
