import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'screens/home_screen.dart';
import 'screens/login_page.dart';
import 'screens/registration_page.dart';
import 'screens/splash_screen.dart';
import 'theme_provider.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final themeProvider = ThemeProvider();
  await themeProvider.init();

  runApp(
    ChangeNotifierProvider(
      create: (context) => themeProvider,
      child: MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  MyApp({super.key});

  @override
  Widget build(BuildContext context) {

    final tp = context.watch<ThemeProvider>();

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Aqua Sense',

      /// Theme mode
      themeMode: tp.themeMode,

      /// Light theme
      theme: ThemeProvider.lightTheme(tp.fontSize).copyWith(
        primaryColor: const Color(0xFF0A1B6F),
      ),

      /// Dark theme
      darkTheme: ThemeProvider.darkTheme(tp.fontSize).copyWith(
        primaryColor: const Color(0xFF0A1B6F),
      ),

      initialRoute: '/splash',

      routes: {
        '/splash': (context) => SplashScreen(),
        '/login': (context) => LoginPage(),
        '/register': (context) => RegistrationPage(),
        '/home': (context) => HomeScreen(),
      },
    );
  }
}