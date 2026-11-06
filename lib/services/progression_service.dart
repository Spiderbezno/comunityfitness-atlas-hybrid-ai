/// Progression Rules and Adaptive Overload Service
///
/// Implements standard evidence-based progression schemes:
/// - Greyskull LP (AMRAP top sets, double jumps, 10% deloads on failure)
/// - Double Progression (Rep range cycling before load increases)
/// - Linear Progression (Simple set/rep target advancement)
enum ProgressionScheme { greyskullLp, doubleProgression, linear }

class ProgressionResult {
  final double nextWeight;
  final int nextReps;
  final String rationale;
  final bool isDeload;
  final bool isDoubleJump;

  const ProgressionResult({
    required this.nextWeight,
    required this.nextReps,
    required this.rationale,
    this.isDeload = false,
    this.isDoubleJump = false,
  });
}

class ProgressionService {
  const ProgressionService._();

  /// Calculates next session target using Greyskull LP rules.
  ///
  /// - [currentWeight]: current working weight
  /// - [targetReps]: baseline target reps (e.g., 5)
  /// - [actualAmrapReps]: reps achieved on final AMRAP set
  /// - [consecutiveFailures]: number of consecutive sessions where baseline was missed
  /// - [weightIncrement]: standard increment (default 2.5 kg)
  static ProgressionResult calculateGreyskullProgression({
    required double currentWeight,
    required int targetReps,
    required int actualAmrapReps,
    int consecutiveFailures = 0,
    double weightIncrement = 2.5,
  }) {
    if (actualAmrapReps < targetReps) {
      final failures = consecutiveFailures + 1;
      if (failures >= 3) {
        // 10% Deload reset
        final deloadWeight = (currentWeight * 0.90 * 2).roundToDouble() / 2.0; // round to nearest 0.5
        return ProgressionResult(
          nextWeight: deloadWeight,
          nextReps: targetReps,
          rationale: 'Deload 10% after 3 failed sessions. Reset and build momentum.',
          isDeload: true,
        );
      }
      return ProgressionResult(
        nextWeight: currentWeight,
        nextReps: targetReps,
        rationale: 'Missed target ($actualAmrapReps/$targetReps reps). Repeat weight next session.',
      );
    }

    if (actualAmrapReps >= targetReps * 2) {
      // Double jump (e.g., 10+ reps on 5 rep target)
      final doubleJumpIncrement = weightIncrement * 2;
      return ProgressionResult(
        nextWeight: currentWeight + doubleJumpIncrement,
        nextReps: targetReps,
        rationale: 'AMRAP crushed ($actualAmrapReps reps! Double jump +${doubleJumpIncrement}kg applied).',
        isDoubleJump: true,
      );
    }

    // Standard progression
    return ProgressionResult(
      nextWeight: currentWeight + weightIncrement,
      nextReps: targetReps,
      rationale: 'Target completed ($actualAmrapReps reps). Standard increment +${weightIncrement}kg applied.',
    );
  }

  /// Calculates next session target using Double Progression rules.
  ///
  /// - [currentWeight]: current working weight
  /// - [currentReps]: current target reps
  /// - [minReps]: lower bound of rep range (e.g. 8)
  /// - [maxReps]: upper bound of rep range (e.g. 12)
  /// - [allSetsHitMax]: whether every working set hit [maxReps]
  /// - [weightIncrement]: weight bump when rep range is cleared (default 2.5 kg)
  static ProgressionResult calculateDoubleProgression({
    required double currentWeight,
    required int currentReps,
    required int minReps,
    required int maxReps,
    required bool allSetsHitMax,
    double weightIncrement = 2.5,
  }) {
    if (allSetsHitMax) {
      return ProgressionResult(
        nextWeight: currentWeight + weightIncrement,
        nextReps: minReps,
        rationale: 'Hit $maxReps reps across all sets. Increased weight by +${weightIncrement}kg and reset reps to $minReps.',
      );
    }

    final nextRepTarget = currentReps < maxReps ? currentReps + 1 : maxReps;
    return ProgressionResult(
      nextWeight: currentWeight,
      nextReps: nextRepTarget,
      rationale: 'Maintain ${currentWeight}kg and aim for $nextRepTarget reps next session.',
    );
  }

  /// Simple Linear Progression rule.
  static ProgressionResult calculateLinearProgression({
    required double currentWeight,
    required int targetReps,
    required bool completedAllSets,
    double weightIncrement = 2.5,
  }) {
    if (completedAllSets) {
      return ProgressionResult(
        nextWeight: currentWeight + weightIncrement,
        nextReps: targetReps,
        rationale: 'All sets completed. Advanced weight +${weightIncrement}kg.',
      );
    }

    return ProgressionResult(nextWeight: currentWeight, nextReps: targetReps, rationale: 'Sets not fully completed. Maintain weight next session.');
  }
}
