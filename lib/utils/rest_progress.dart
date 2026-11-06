/// Fraction of the rest period still remaining, in the range 0..1.
///
/// 1 means the full rest is left, 0 means the rest is finished. A
/// non-positive [totalSeconds] yields 0 so a missing total never divides by
/// zero or shows a full ring.
double restProgress(int remainingSeconds, int totalSeconds) {
  if (totalSeconds <= 0) {
    return 0;
  }
  return (remainingSeconds / totalSeconds).clamp(0.0, 1.0).toDouble();
}
