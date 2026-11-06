// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';

// 🌎 Project imports:
import 'package:comunityfitness/utils/rest_progress.dart';

void main() {
  group('restProgress', () {
    test('returns 1 when the full rest remains', () {
      expect(restProgress(90, 90), 1.0);
    });

    test('returns the remaining fraction mid-rest', () {
      expect(restProgress(45, 90), closeTo(0.5, 1e-9));
      expect(restProgress(15, 60), closeTo(0.25, 1e-9));
    });

    test('returns 0 when the rest is finished', () {
      expect(restProgress(0, 90), 0.0);
    });

    test('returns 0 when total is 0 or negative', () {
      expect(restProgress(0, 0), 0.0);
      expect(restProgress(30, 0), 0.0);
      expect(restProgress(30, -10), 0.0);
    });

    test('clamps out-of-range values', () {
      expect(restProgress(120, 90), 1.0);
      expect(restProgress(-5, 90), 0.0);
    });
  });
}
