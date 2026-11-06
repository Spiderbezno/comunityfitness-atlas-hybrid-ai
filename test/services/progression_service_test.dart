// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';

// 🌎 Project imports:
import 'package:comunityfitness/services/progression_service.dart';

void main() {
  group('ProgressionService', () {
    group('Greyskull LP', () {
      test('advances standard increment when baseline target is reached', () {
        final result = ProgressionService.calculateGreyskullProgression(currentWeight: 80.0, targetReps: 5, actualAmrapReps: 6, weightIncrement: 2.5);

        expect(result.nextWeight, equals(82.5));
        expect(result.nextReps, equals(5));
        expect(result.isDeload, isFalse);
        expect(result.isDoubleJump, isFalse);
      });

      test('triggers double jump when AMRAP is 2x target reps', () {
        final result = ProgressionService.calculateGreyskullProgression(
          currentWeight: 80.0,
          targetReps: 5,
          actualAmrapReps: 11,
          weightIncrement: 2.5,
        );

        expect(result.nextWeight, equals(85.0)); // +5.0kg
        expect(result.isDoubleJump, isTrue);
      });

      test('maintains weight when target reps are not met on 1st or 2nd try', () {
        final result = ProgressionService.calculateGreyskullProgression(
          currentWeight: 80.0,
          targetReps: 5,
          actualAmrapReps: 4,
          consecutiveFailures: 1,
        );

        expect(result.nextWeight, equals(80.0));
        expect(result.isDeload, isFalse);
      });

      test('triggers 10% deload after 3 consecutive failures', () {
        final result = ProgressionService.calculateGreyskullProgression(
          currentWeight: 100.0,
          targetReps: 5,
          actualAmrapReps: 4,
          consecutiveFailures: 2, // will become 3
        );

        expect(result.nextWeight, equals(90.0));
        expect(result.isDeload, isTrue);
      });
    });

    group('Double Progression', () {
      test('increments weight and resets reps when max reps are cleared across all sets', () {
        final result = ProgressionService.calculateDoubleProgression(
          currentWeight: 20.0,
          currentReps: 12,
          minReps: 8,
          maxReps: 12,
          allSetsHitMax: true,
          weightIncrement: 2.5,
        );

        expect(result.nextWeight, equals(22.5));
        expect(result.nextReps, equals(8));
      });

      test('increments rep target when not all sets hit max', () {
        final result = ProgressionService.calculateDoubleProgression(
          currentWeight: 20.0,
          currentReps: 9,
          minReps: 8,
          maxReps: 12,
          allSetsHitMax: false,
        );

        expect(result.nextWeight, equals(20.0));
        expect(result.nextReps, equals(10));
      });
    });

    group('Linear Progression', () {
      test('adds increment on completion', () {
        final result = ProgressionService.calculateLinearProgression(
          currentWeight: 50.0,
          targetReps: 10,
          completedAllSets: true,
          weightIncrement: 2.5,
        );

        expect(result.nextWeight, equals(52.5));
      });

      test('keeps weight if not completed', () {
        final result = ProgressionService.calculateLinearProgression(currentWeight: 50.0, targetReps: 10, completedAllSets: false);

        expect(result.nextWeight, equals(50.0));
      });
    });
  });
}
