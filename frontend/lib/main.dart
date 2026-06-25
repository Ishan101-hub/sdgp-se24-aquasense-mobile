import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:firebase_core/firebase_core.dart'; 
import 'package:firebase_messaging/firebase_messaging.dart'; 

import 'firebase_options.dart'; // Handles platform profiles dynamically
import 'screens/home_screen.dart';
import 'screens/login_page.dart';
import 'screens/registration_page.dart';
import 'screens/splash_screen.dart';
import 'theme_provider.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Firebase securely with multi-platform cross-options
  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform, // ← Added cross-platform options
    );
    
    // Request notification permissions for iOS and Android 13+
    FirebaseMessaging messaging = FirebaseMessaging.instance;
    await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    // BACKGROUND/TERMINATED LISTENER
    // This allows your app to handle notifications when it is closed or minimized
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

  } catch (e) {
    debugPrint("Firebase initialization error: $e");
  }

  // Theme setup remains untouched
  final themeProvider = ThemeProvider();
  await themeProvider.init();

  runApp(
    ChangeNotifierProvider(
      create: (context) => themeProvider,
      child: MyApp(),
    ),
  );
}

// Top-level function required for handling notifications when app is in background/terminated
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform, // ← Added cross-platform options here too
  );
  // Handle background notification payload data here if needed
}

class MyApp extends StatelessWidget {
  MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    final tp = context.watch<ThemeProvider>();

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'AquaSense',
      themeMode: tp.themeMode,
      theme: ThemeProvider.lightTheme(tp.fontSize).copyWith(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0A1B6F),
        ),
        primaryColor: const Color(0xFF0A1B6F),
      ),
      darkTheme: ThemeProvider.darkTheme(tp.fontSize).copyWith(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0A1B6F),
          brightness: Brightness.dark,
        ),
        primaryColor: const Color(0xFF0A1B6F),
      ),
      initialRoute: '/splash',
      routes: {
        '/splash': (context) => SplashScreen(),
        '/login': (context) => LoginPage(),
        '/register': (context) => RegistrationPage(),
        '/home': (context) => const HomeScreen(),
      },
    );
  }
}