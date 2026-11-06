// 📦 Package imports:
import 'package:riverpod_annotation/riverpod_annotation.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/routine.dart';
import 'package:comunityfitness/repositories/routine_repository.dart';
import 'package:comunityfitness/viewmodels/dashboard_viewmodel.dart';
import 'package:comunityfitness/viewmodels/data_management_viewmodel.dart';

part 'routine_list_viewmodel.g.dart';

@riverpod
class RoutineListViewModel extends _$RoutineListViewModel {
  @override
  Stream<List<Routine>> build() {
    return ref.watch(routineRepositoryProvider).watchRoutines();
  }

  Future<void> deleteRoutine(String id) async {
    await ref.read(routineRepositoryProvider).deleteRoutine(id);
    ref.invalidate(dashboardViewModelProvider);
    ref.invalidate(dataManagementViewModelProvider);
  }
}
