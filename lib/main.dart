import 'package:flutter/material.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Aqua Sense',
      theme: ThemeData(primaryColor: const Color(0xFF0A1B6F)),
      home: HomeScreen(),
    );
  }
}
