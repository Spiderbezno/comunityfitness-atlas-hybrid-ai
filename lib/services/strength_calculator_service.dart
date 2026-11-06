// 🎯 Dart imports:
import 'dart:math' as math;

// 🌎 Project imports:
import 'package:comunityfitness/models/workout_session.dart';
import 'package:comunityfitness/models/workout_step.dart';

/// Evidence-based weekly hard-set hypertrophy volume landmarks (MEV / MAV / MRV).
class MuscleVolumeLandmarks {
  final int mev;
  final int mavMin;
  final int mavMax;
  final int mrv;

  const MuscleVolumeLandmarks({required this.mev, required this.mavMin, required this.mavMax, required this.mrv});
}

/// Immutable prescription returned by the Progressive Overload Autopilot engine.
class OverloadPrescription {
  final double targetWeight;
  final int targetReps;
  final String? badgeLabel;
  final String rationale;
  final bool isOverloadApplied;

  const OverloadPrescription({
    required this.targetWeight,
    required this.targetReps,
    this.badgeLabel,
    required this.rationale,
    required this.isOverloadApplied,
  });
}

/// Strength and Recovery Calculator Service
///
/// Contains pure mathematical functions for strength assessment,
/// 1RM estimations, effort metrics (RIR/RPE), and muscle fatigue recovery.
class StrengthCalculatorService {
  const StrengthCalculatorService._();

  /// Estimates 1-Rep Max using the Epley formula:
  /// 1RM = Weight * (1 + Reps / 30)
  ///
  /// If [rir] (Reps in Reserve) is provided, effective reps = reps + rir.
  /// If [reps] > 12, formula accuracy drops; it returns the 12-rep estimation.
  static double estimateOneRepMaxEpley({required double weight, required int reps, int? rir}) {
    if (weight <= 0 || reps <= 0) {
      return 0.0;
    }
    final effectiveReps = math.min(12, reps + (rir ?? 0));
    if (effectiveReps == 1) {
      return weight;
    }
    return weight * (1.0 + (effectiveReps / 30.0));
  }

  /// Estimates 1-Rep Max using the Brzycki formula:
  /// 1RM = Weight / (1.0278 - 0.0278 * Reps)
  static double estimateOneRepMaxBrzycki({required double weight, required int reps, int? rir}) {
    if (weight <= 0 || reps <= 0) {
      return 0.0;
    }
    final effectiveReps = math.min(12, reps + (rir ?? 0));
    if (effectiveReps == 1) {
      return weight;
    }
    final denominator = 1.0278 - (0.0278 * effectiveReps);
    if (denominator <= 0) {
      return weight;
    }
    return weight / denominator;
  }

  /// Composite standard 1RM (Average of Epley and Brzycki) rounded to 1 decimal place.
  static double calculateEstimatedOneRepMax({required double weight, required int reps, int? rir}) {
    if (weight <= 0 || reps <= 0) {
      return 0.0;
    }
    if (reps == 1 && (rir == null || rir == 0)) {
      return weight;
    }
    final epley = estimateOneRepMaxEpley(weight: weight, reps: reps, rir: rir);
    final brzycki = estimateOneRepMaxBrzycki(weight: weight, reps: reps, rir: rir);
    final avg = (epley + brzycki) / 2.0;
    return (avg * 10).roundToDouble() / 10.0;
  }

  /// Calculates percentage of 1RM for a target rep count using Epley inversion:
  /// Reps = 30 * (1RM / Weight - 1) => Weight / 1RM = 1 / (1 + Reps / 30)
  static double getPercentageOfOneRepMax(int reps) {
    if (reps <= 1) {
      return 1.0;
    }
    final safeReps = math.min(30, reps);
    return 1.0 / (1.0 + (safeReps / 30.0));
  }

  /// Converts RPE (Rating of Perceived Exertion, 6.0-10.0) to RIR (Reps in Reserve).
  /// RIR = 10.0 - RPE
  static int rpeToRir(double rpe) {
    if (rpe >= 10.0) {
      return 0;
    }
    if (rpe <= 6.0) {
      return 4;
    }
    return (10.0 - rpe).round();
  }

  /// Converts RIR to estimated RPE.
  /// RPE = 10.0 - RIR
  static double rirToRpe(int rir) {
    if (rir <= 0) {
      return 10.0;
    }
    if (rir >= 4) {
      return 6.0;
    }
    return 10.0 - rir.toDouble();
  }

  /// Calculates total training volume (tonnage) in kg/lbs:
  /// Volume = Sets * Reps * Weight
  static double calculateVolume({required int sets, required int reps, required double weight, bool isWarmup = false}) {
    if (isWarmup || sets <= 0 || reps <= 0 || weight <= 0) {
      return 0.0;
    }
    return sets * reps * weight;
  }

  /// Calculates muscle recovery percentage (0.0 to 1.0) given:
  /// - [hoursSinceTrained]: elapsed hours since last workout targeting this muscle
  /// - [effectiveSets]: number of working sets performed
  ///
  /// Standard recovery model:
  /// Full recovery (100%) takes between 36h (low volume: 1-3 sets) to 72h (high volume: 8+ sets).
  static double calculateMuscleRecoveryPercentage({required double hoursSinceTrained, required int effectiveSets}) {
    if (effectiveSets <= 0 || hoursSinceTrained >= 72.0) {
      return 1.0;
    }
    if (hoursSinceTrained <= 0) {
      return 0.1;
    }

    // Required recovery hours based on volume
    final requiredRecoveryHours = math.min(72.0, 36.0 + (effectiveSets * 3.5));

    // Smooth recovery curve
    final ratio = hoursSinceTrained / requiredRecoveryHours;
    if (ratio >= 1.0) {
      return 1.0;
    }

    final recovery = 1.0 - math.exp(-2.5 * ratio);
    return math.max(0.0, math.min(1.0, (recovery * 100).roundToDouble() / 100.0));
  }

  /// Classifies recovery status into readable categories:
  /// - 'recovered' (>= 95%)
  /// - 'recovering' (50% - 94%)
  /// - 'fatigued' (< 50%)
  static String getRecoveryStatus(double recoveryPercentage) {
    if (recoveryPercentage >= 0.95) {
      return 'recovered';
    }
    if (recoveryPercentage >= 0.50) {
      return 'recovering';
    }
    return 'fatigued';
  }

  static const Map<String, MuscleVolumeLandmarks> _volumeLandmarksByMuscle = {
    'Chest': MuscleVolumeLandmarks(mev: 8, mavMin: 12, mavMax: 18, mrv: 22),
    'Back': MuscleVolumeLandmarks(mev: 10, mavMin: 14, mavMax: 20, mrv: 25),
    'Quads': MuscleVolumeLandmarks(mev: 8, mavMin: 12, mavMax: 18, mrv: 20),
    'Hamstrings': MuscleVolumeLandmarks(mev: 6, mavMin: 10, mavMax: 16, mrv: 20),
    'Shoulders': MuscleVolumeLandmarks(mev: 8, mavMin: 12, mavMax: 18, mrv: 22),
    'Biceps': MuscleVolumeLandmarks(mev: 6, mavMin: 10, mavMax: 16, mrv: 20),
    'Triceps': MuscleVolumeLandmarks(mev: 6, mavMin: 10, mavMax: 14, mrv: 18),
    'Core': MuscleVolumeLandmarks(mev: 6, mavMin: 10, mavMax: 16, mrv: 20),
    'Glutes': MuscleVolumeLandmarks(mev: 6, mavMin: 10, mavMax: 16, mrv: 20),
    'Calves': MuscleVolumeLandmarks(mev: 6, mavMin: 10, mavMax: 16, mrv: 20),
  };

  static const MuscleVolumeLandmarks _defaultLandmarks = MuscleVolumeLandmarks(mev: 6, mavMin: 10, mavMax: 16, mrv: 20);

  /// Returns weekly hard-set hypertrophy volume landmarks (MEV, MAV range, MRV) for [muscle].
  static MuscleVolumeLandmarks getVolumeLandmarks(String muscle) {
    return _volumeLandmarksByMuscle[muscle] ?? _defaultLandmarks;
  }

  /// Evaluates weekly working sets against MEV/MAV/MRV thresholds:
  /// - `'under_mev'` when `weeklySets < mev`
  /// - `'optimal_mav'` when `weeklySets >= mev && weeklySets <= mavMax`
  /// - `'near_mrv'` when `weeklySets > mavMax && weeklySets <= mrv`
  /// - `'over_mrv'` when `weeklySets > mrv`
  static String evaluateVolumeZone(String muscle, int weeklySets) {
    final landmarks = getVolumeLandmarks(muscle);
    if (weeklySets < landmarks.mev) {
      return 'under_mev';
    }
    if (weeklySets <= landmarks.mavMax) {
      return 'optimal_mav';
    }
    if (weeklySets <= landmarks.mrv) {
      return 'near_mrv';
    }
    return 'over_mrv';
  }

  /// Calculates normalized MAV progress (`0.0` to `1.5`) relative to `mavMax`.
  static double calculateMavProgress(String muscle, int weeklySets) {
    if (weeklySets <= 0) {
      return 0.0;
    }
    final landmarks = getVolumeLandmarks(muscle);
    return (weeklySets / landmarks.mavMax).clamp(0.0, 1.5);
  }

  /// Prescribes progressive overload (double progression: +2.5 kg or +1 rep)
  /// based on the most recent non-warmup [WorkoutStep] for [exerciseId] in [history].
  static OverloadPrescription prescribeProgressiveOverload({
    required String exerciseId,
    required int baseReps,
    required double baseWeight,
    required List<WorkoutSession> history,
  }) {
    final activeSessions = history.where((s) => !s.isDeleted).toList()
      ..sort((a, b) {
        final aTime = a.completedAt ?? a.startedAt;
        final bTime = b.completedAt ?? b.startedAt;
        return bTime.compareTo(aTime);
      });

    WorkoutStep? priorStep;
    for (final session in activeSessions) {
      for (final step in session.steps.reversed) {
        if (!step.isWarmup && step.exerciseId == exerciseId) {
          priorStep = step;
          break;
        }
      }
      if (priorStep != null) {
        break;
      }
    }

    if (priorStep == null) {
      return OverloadPrescription(
        targetWeight: baseWeight,
        targetReps: baseReps,
        badgeLabel: null,
        rationale: 'Baseline target',
        isOverloadApplied: false,
      );
    }

    if (priorStep.weight > 0) {
      if (priorStep.reps >= baseReps) {
        return OverloadPrescription(
          targetWeight: priorStep.weight + 2.5,
          targetReps: baseReps,
          badgeLabel: '+2.5 kg Autopilot',
          rationale: 'Last session: ${priorStep.weight.toStringAsFixed(1)} kg × ${priorStep.reps} reps',
          isOverloadApplied: true,
        );
      }
      return OverloadPrescription(
        targetWeight: priorStep.weight,
        targetReps: priorStep.reps + 1,
        badgeLabel: '+1 rep Autopilot',
        rationale: 'Build to $baseReps reps at ${priorStep.weight.toStringAsFixed(1)} kg',
        isOverloadApplied: true,
      );
    }

    if (priorStep.weight <= 0 && baseWeight <= 0 && priorStep.reps > 0) {
      return OverloadPrescription(
        targetWeight: 0.0,
        targetReps: (priorStep.reps >= baseReps ? priorStep.reps : baseReps) + 1,
        badgeLabel: '+1 rep Autopilot',
        rationale: 'Last session: ${priorStep.reps} reps',
        isOverloadApplied: true,
      );
    }

    return OverloadPrescription(
      targetWeight: baseWeight,
      targetReps: baseReps,
      badgeLabel: null,
      rationale: 'Baseline target',
      isOverloadApplied: false,
    );
  }
}
