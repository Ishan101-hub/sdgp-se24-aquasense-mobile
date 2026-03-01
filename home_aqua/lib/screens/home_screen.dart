import 'package:flutter/material.dart';
import '../widgets/custom_bottom_nav.dart';
import 'home_page.dart';
import 'leakages_page.dart'; // ← new import

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {

    // ── Pages for each tab ──
    final List<Widget> pages = const [
      HomePage(),        // Tab 0: Home
      LeakagesPage(),    // Tab 1: Leakages ← connected! ✅
      _PlaceholderPage('Report'),   // Tab 2
      _PlaceholderPage('Service'),  // Tab 3
      _PlaceholderPage('Settings'), // Tab 4
    ];

    return Scaffold(
      backgroundColor: const Color(0xFFEEF4FF),
      body: pages[_currentIndex],
      bottomNavigationBar: CustomBottomNav(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() => _currentIndex = index);
        },
      ),
    );
  }
}

class _PlaceholderPage extends StatelessWidget {
  final String pageName;
  const _PlaceholderPage(this.pageName);

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        '$pageName Page\n(Coming Soon)',
        textAlign: TextAlign.center,
        style: const TextStyle(
          fontSize: 20,
          color: Color(0xFF0A1B6F),
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}