// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/models/workout_step.dart';
import 'package:comunityfitness/services/strength_calculator_service.dart';

void main() {
  group('StrengthCalculatorService', () {
    test('estimateOneRepMaxEpley calculates expected 1RM', () {
      // 100kg for 10 reps => 100 * (1 + 10/30) = 133.33 kg
      final epley = StrengthCalculatorService.estimateOneRepMaxEpley(weight: 100, reps: 10);
      expect(epley, closeTo(133.33, 0.1));

      // 1 rep should equal working weight
      final oneRep = StrengthCalculatorService.estimateOneRepMaxEpley(weight: 120, reps: 1);
      expect(oneRep, equals(120.0));

      // with RIR (8 reps + 2 RIR = 10 effective reps)
      final withRir = StrengthCalculatorService.estimateOneRepMaxEpley(weight: 100, reps: 8, rir: 2);
      expect(withRir, closeTo(133.33, 0.1));
    });

    test('estimateOneRepMaxBrzycki calculates expected 1RM', () {
      // 100kg for 10 reps => 100 / (1.0278 - 0.278) = 133.36 kg
      final brzycki = StrengthCalculatorService.estimateOneRepMaxBrzycki(weight: 100, reps: 10);
      expect(brzycki, closeTo(133.36, 0.1));
    });

    test('calculateEstimatedOneRepMax returns rounded composite 1RM', () {
      final composite = StrengthCalculatorService.calculateEstimatedOneRepMax(weight: 100, reps: 10);
      expect(composite, closeTo(133.3, 0.1));
    });

    test('RPE and RIR conversion functions work reciprocally', () {
      expect(StrengthCalculatorService.rpeToRir(10.0), equals(0));
      expect(StrengthCalculatorService.rpeToRir(8.0), equals(2));
      expect(StrengthCalculatorService.rpeToRir(7.0), equals(3));

      expect(StrengthCalculatorService.rirToRpe(0), equals(10.0));
      expect(StrengthCalculatorService.rirToRpe(2), equals(8.0));
      expect(StrengthCalculatorService.rirToRpe(3), equals(7.0));
    });

    test('calculateVolume ignores warm-ups and calculates working tonnage', () {
      final workingVolume = StrengthCalculatorService.calculateVolume(sets: 4, reps: 10, weight: 80.0, isWarmup: false);
      expect(workingVolume, equals(3200.0));

      final warmupVolume = StrengthCalculatorService.calculateVolume(sets: 2, reps: 10, weight: 50.0, isWarmup: true);
      expect(warmupVolume, equals(0.0));
    });

    test('calculateMuscleRecoveryPercentage models exponential recovery decay', () {
      // Immediately after training (0 hours)
      final zeroHours = StrengthCalculatorService.calculateMuscleRecoveryPercentage(hoursSinceTrained: 0, effectiveSets: 5);
      expect(zeroHours, equals(0.1));

      // After 72+ hours => fully recovered
      final fullRecovery = StrengthCalculatorService.calculateMuscleRecoveryPercentage(hoursSinceTrained: 80, effectiveSets: 5);
      expect(fullRecovery, equals(1.0));
      expect(StrengthCalculatorService.getRecoveryStatus(fullRecovery), equals('recovered'));

      // Partial recovery (24 hours after moderate volume)
      final partialRecovery = StrengthCalculatorService.calculateMuscleRecoveryPercentage(hoursSinceTrained: 24, effectiveSets: 4);
      expect(partialRecovery, greaterThan(0.5));
      expect(partialRecovery, lessThan(1.0));
    });

    test('getVolumeLandmarks returns expected MEV, MAV, and MRV landmarks for standard muscles and fallback', () {
      final chest = StrengthCalculatorService.getVolumeLandmarks('Chest');
      expect(chest.mev, equals(8));
      expect(chest.mavMin, equals(12));
      expect(chest.mavMax, equals(18));
      expect(chest.mrv, equals(22));

      final back = StrengthCalculatorService.getVolumeLandmarks('Back');
      expect(back.mev, equals(10));
      expect(back.mavMin, equals(14));
      expect(back.mavMax, equals(20));
      expect(back.mrv, equals(25));

      final triceps = StrengthCalculatorService.getVolumeLandmarks('Triceps');
      expect(triceps.mev, equals(6));
      expect(triceps.mavMin, equals(10));
      expect(triceps.mavMax, equals(14));
      expect(triceps.mrv, equals(18));

      final fallback = StrengthCalculatorService.getVolumeLandmarks('UnknownMuscle');
      expect(fallback.mev, equals(6));
      expect(fallback.mavMin, equals(10));
      expect(fallback.mavMax, equals(16));
      expect(fallback.mrv, equals(20));
    });

    test('evaluateVolumeZone classifies weekly hard sets into under_mev, optimal_mav, near_mrv, and over_mrv', () {
      // Chest: mev=8, mavMin=12, mavMax=18, mrv=22
      expect(StrengthCalculatorService.evaluateVolumeZone('Chest', 0), equals('under_mev'));
      expect(StrengthCalculatorService.evaluateVolumeZone('Chest', 7), equals('under_mev'));
      expect(StrengthCalculatorService.evaluateVolumeZone('Chest', 8), equals('optimal_mav'));
      expect(StrengthCalculatorService.evaluateVolumeZone('Chest', 15), equals('optimal_mav'));
      expect(StrengthCalculatorService.evaluateVolumeZone('Chest', 18), equals('optimal_mav'));
      expect(StrengthCalculatorService.evaluateVolumeZone('Chest', 19), equals('near_mrv'));
      expect(StrengthCalculatorService.evaluateVolumeZone('Chest', 22), equals('near_mrv'));
      expect(StrengthCalculatorService.evaluateVolumeZone('Chest', 23), equals('over_mrv'));
    });

    test('calculateMavProgress computes normalized MAV progress clamped between 0.0 and 1.5', () {
      // Chest mavMax = 18
      expect(StrengthCalculatorService.calculateMavProgress('Chest', 0), equals(0.0));
      expect(StrengthCalculatorService.calculateMavProgress('Chest', -2), equals(0.0));
      expect(StrengthCalculatorService.calculateMavProgress('Chest', 9), closeTo(0.5, 0.001));
      expect(StrengthCalculatorService.calculateMavProgress('Chest', 18), closeTo(1.0, 0.001));
      expect(StrengthCalculatorService.calculateMavProgress('Chest', 36), equals(1.5));
    });

    group('prescribeProgressiveOverload', () {
      WorkoutSession buildSession({required String id, required DateTime completedAt, required List<WorkoutStep> steps, bool isDeleted = false}) {
        return WorkoutSession(
          id: id,
          userId: 'u-1',
          startedAt: completedAt.subtract(const Duration(minutes: 45)),
          completedAt: completedAt,
          updatedAt: completedAt,
          isDeleted: isDeleted,
          steps: steps,
        );
      }

      test('returns baseline target when history has no matching non-warmup exercise', () {
        final history = [
          buildSession(
            id: 's-1',
            completedAt: DateTime(2026, 4, 10, 12),
            steps: const [
              WorkoutStep(
                exerciseId: 'barbell_bench_press',
                sets: 2,
                reps: 10,
                weight: 60.0,
                targetDurationSeconds: 0,
                restDurationSeconds: 60,
                orderIndex: 0,
                isWarmup: true,
              ),
            ],
          ),
        ];

        final prescription = StrengthCalculatorService.prescribeProgressiveOverload(
          exerciseId: 'barbell_bench_press',
          baseReps: 10,
          baseWeight: 70.0,
          history: history,
        );

        expect(prescription.isOverloadApplied, isFalse);
        expect(prescription.targetWeight, equals(70.0));
        expect(prescription.targetReps, equals(10));
        expect(prescription.badgeLabel, isNull);
        expect(prescription.rationale, equals('Baseline target'));
      });

      test('prescribes +2.5 kg when most recent session met or exceeded target reps', () {
        final olderSession = buildSession(
          id: 's-old',
          completedAt: DateTime(2026, 4, 1, 12),
          steps: const [
            WorkoutStep(
              exerciseId: 'barbell_bench_press',
              sets: 3,
              reps: 8,
              weight: 75.0,
              targetDurationSeconds: 0,
              restDurationSeconds: 60,
              orderIndex: 0,
            ),
          ],
        );
        final newerSession = buildSession(
          id: 's-new',
          completedAt: DateTime(2026, 4, 8, 12),
          steps: const [
            WorkoutStep(
              exerciseId: 'barbell_bench_press',
              sets: 3,
              reps: 10,
              weight: 80.0,
              targetDurationSeconds: 0,
              restDurationSeconds: 60,
              orderIndex: 0,
            ),
          ],
        );
        final deletedNewest = buildSession(
          id: 's-deleted',
          completedAt: DateTime(2026, 4, 12, 12),
          isDeleted: true,
          steps: const [
            WorkoutStep(
              exerciseId: 'barbell_bench_press',
              sets: 3,
              reps: 10,
              weight: 100.0,
              targetDurationSeconds: 0,
              restDurationSeconds: 60,
              orderIndex: 0,
            ),
          ],
        );

        final prescription = StrengthCalculatorService.prescribeProgressiveOverload(
          exerciseId: 'barbell_bench_press',
          baseReps: 10,
          baseWeight: 70.0,
          history: [olderSession, newerSession, deletedNewest],
        );

        expect(prescription.isOverloadApplied, isTrue);
        expect(prescription.targetWeight, equals(82.5));
        expect(prescription.targetReps, equals(10));
        expect(prescription.badgeLabel, equals('+2.5 kg Autopilot'));
        expect(prescription.rationale, equals('Last session: 80.0 kg × 10 reps'));
      });

      test('prescribes +1 rep at same weight when most recent session fell short of baseReps', () {
        final history = [
          buildSession(
            id: 's-1',
            completedAt: DateTime(2026, 4, 10, 12),
            steps: const [
              WorkoutStep(
                exerciseId: 'barbell_bench_press',
                sets: 3,
                reps: 8,
                weight: 80.0,
                targetDurationSeconds: 0,
                restDurationSeconds: 60,
                orderIndex: 0,
              ),
            ],
          ),
        ];

        final prescription = StrengthCalculatorService.prescribeProgressiveOverload(
          exerciseId: 'barbell_bench_press',
          baseReps: 10,
          baseWeight: 75.0,
          history: history,
        );

        expect(prescription.isOverloadApplied, isTrue);
        expect(prescription.targetWeight, equals(80.0));
        expect(prescription.targetReps, equals(9));
        expect(prescription.badgeLabel, equals('+1 rep Autopilot'));
        expect(prescription.rationale, equals('Build to 10 reps at 80.0 kg'));
      });

      test('prescribes +1 rep for bodyweight exercises', () {
        final history = [
          buildSession(
            id: 's-bw',
            completedAt: DateTime(2026, 4, 10, 12),
            steps: const [
              WorkoutStep(exerciseId: 'pull_ups', sets: 3, reps: 12, weight: 0.0, targetDurationSeconds: 0, restDurationSeconds: 60, orderIndex: 0),
            ],
          ),
        ];

        final prescription = StrengthCalculatorService.prescribeProgressiveOverload(
          exerciseId: 'pull_ups',
          baseReps: 10,
          baseWeight: 0.0,
          history: history,
        );

        expect(prescription.isOverloadApplied, isTrue);
        expect(prescription.targetWeight, equals(0.0));
        expect(prescription.targetReps, equals(13));
        expect(prescription.badgeLabel, equals('+1 rep Autopilot'));
        expect(prescription.rationale, equals('Last session: 12 reps'));
      });
    });
  });
}
