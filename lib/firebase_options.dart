// 🐦 Flutter imports:
import 'package:flutter/foundation.dart' show defaultTargetPlatform, kIsWeb, TargetPlatform;

// 📦 Package imports:
import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      return web;
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      default:
        throw UnsupportedError('DefaultFirebaseOptions are not supported for this platform.');
    }
  }

  static const FirebaseOptions web = FirebaseOptions(
    apiKey: 'AIzaSyBF_l_plgEUDj6J7nHlooWarzyOiQH8od4',
    appId: '1:387922095149:web:9abb5b4043722a6fc31ca4',
    messagingSenderId: '387922095149',
    projectId: 'comunityfitness',
    authDomain: 'comunityfitness.firebaseapp.com',
    storageBucket: 'comunityfitness.firebasestorage.app',
  );

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyC8AoqCIrEVMMOLx5X_phrUykKjLiw9Lv0',
    appId: '1:387922095149:android:f77de40983ced7a6c31ca4',
    messagingSenderId: '387922095149',
    projectId: 'comunityfitness',
    storageBucket: 'comunityfitness.firebasestorage.app',
  );

  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: 'AIzaSyBgrj7MCHQ1bZXdp0wklJuH6Nsguz-sPx8',
    appId: '1:387922095149:ios:2c14fd6e84d914eec31ca4',
    messagingSenderId: '387922095149',
    projectId: 'comunityfitness',
    storageBucket: 'comunityfitness.firebasestorage.app',
    iosBundleId: 'ad.spiderbezno.comunityfitness',
  );
}
