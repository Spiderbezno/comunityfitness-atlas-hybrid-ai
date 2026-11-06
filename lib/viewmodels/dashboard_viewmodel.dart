// 📦 Package imports:
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/repositories/routine_repository.dart';
import 'package:comunityfitness/repositories/session_repository.dart';
import 'package:comunityfitness/viewmodels/data_management_viewmodel.dart';
import 'package:comunityfitness/viewmodels/muscle_analytics_viewmodel.dart';

part 'dashboard_viewmodel.g.dart';

class DashboardState {
  final Routine? recommendedRoutine;
  final List<Routine> allRoutines;
  final List<WorkoutSession> recentSessions;
  final int weeklyWorkouts;
  final double weeklyVolume;
  final List<String> readyMuscles;
  final List<String> fatiguedMuscles;
  final bool isLoading;

  const DashboardState({
    this.recommendedRoutine,
    required this.allRoutines,
    required this.recentSessions,
    required this.weeklyWorkouts,
    required this.weeklyVolume,
    required this.readyMuscles,
    required this.fatiguedMuscles,
    this.isLoading = false,
  });
}

@riverpod
class DashboardViewModel extends _$DashboardViewModel {
  @override
  DashboardState build() {
    final routineRepo = ref.watch(routineRepositoryProvider);
    final sessionRepo = ref.watch(sessionRepositoryProvider);
    final analytics = ref.watch(muscleAnalyticsViewModelProvider);

    try {
      final routineSub = routineRepo.watchRoutines().skip(1).listen((_) => ref.invalidateSelf());
      ref.onDispose(routineSub.cancel);
    } catch (_) {}
    try {
      final sessionSub = sessionRepo.watchSessions().skip(1).listen((_) => ref.invalidateSelf());
      ref.onDispose(sessionSub.cancel);
    } catch (_) {}

    final routines = routineRepo.getRoutines();
    final sessions = sessionRepo.getSessions()..sort((a, b) => b.startedAt.compareTo(a.startedAt));

    final recent = sessions.take(5).toList();

    final readyList = <String>[];
    final fatiguedList = <String>[];

    analytics.muscleRecovery.forEach((muscle, info) {
      if (info.status == 'recovered') {
        readyList.add(muscle);
      } else {
        fatiguedList.add(muscle);
      }
    });

    final Routine? recommended = routines.isNotEmpty ? routines.first : null;

    return DashboardState(
      recommendedRoutine: recommended,
      allRoutines: routines,
      recentSessions: recent,
      weeklyWorkouts: analytics.totalWorkoutsThisWeek,
      weeklyVolume: analytics.totalVolumeThisWeek,
      readyMuscles: readyList,
      fatiguedMuscles: fatiguedList,
      isLoading: false,
    );
  }

  Future<void> deleteSession(String id) async {
    await ref.read(sessionRepositoryProvider).deleteSession(id);
    if (!ref.mounted) {
      return;
    }
    ref.invalidateSelf();
    ref.invalidate(muscleAnalyticsViewModelProvider);
    ref.invalidate(dataManagementViewModelProvider);
  }
}
