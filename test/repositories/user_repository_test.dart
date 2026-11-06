// 📦 Package imports:
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce/hive.dart';
import 'package:mocktail/mocktail.dart';

// 🌎 Project imports:
import 'package:comunityfitness/models/user.dart';
import 'package:comunityfitness/repositories/user_repository.dart';

class MockBox extends Mock implements Box<User> {}

void main() {
  late MockBox mockBox;
  late UserRepository repository;

  setUpAll(() {
    registerFallbackValue(User(id: 'dummy', email: 'dummy@test.com', displayName: 'Dummy', updatedAt: DateTime(2026)));
  });

  setUp(() {
    mockBox = MockBox();
    repository = UserRepository(userBox: mockBox);
  });

  group('UserRepository', () {
    final user = User(id: 'u1', email: 'jorge@test.com', displayName: 'Jorge', updatedAt: DateTime(2026, 1, 1), synced: true);

    test('getUser returns user by id', () {
      when(() => mockBox.get('u1')).thenReturn(user);
      when(() => mockBox.get('u2')).thenReturn(null);

      expect(repository.getUser('u1')?.id, 'u1');
      expect(repository.getUser('u2'), null);
    });

    test('saveUser updates updatedAt, sets synced = false, and puts in box', () async {
      when(() => mockBox.put(any<dynamic>(), any())).thenAnswer((_) async {});

      await repository.saveUser(user);

      verify(
        () => mockBox.put(
          'u1',
          any(
            that: isA<User>().having((u) => u.synced, 'synced', false).having((u) => u.updatedAt.isAfter(user.updatedAt), 'updatedAt updated', true),
          ),
        ),
      ).called(1);
    });
  });
}
