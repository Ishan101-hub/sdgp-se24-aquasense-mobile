import 'package:flutter/material.dart';
import '../widgets/custom_bottom_nav.dart';
import 'home_page.dart';
import 'leakages_page.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => HomeScreenState();
}

class HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  // ── Called when user taps a notification ──
  // This switches the bottom nav tab correctly
  void switchTab(int index) {
    setState(() => _currentIndex = index);
  }

  @override
  Widget build(BuildContext context) {
    // ── Pass switchTab as callback into pages ──
    // This way pages can call it from anywhere, even inside Navigator.push
    final List<Widget> pages = [
      HomePage(onSwitchTab: switchTab),       // Tab 0
      LeakagesPage(onSwitchTab: switchTab),   // Tab 1
      const _PlaceholderPage('Report'),       // Tab 2
      const _PlaceholderPage('Service'),      // Tab 3
      const _PlaceholderPage('Settings'),     // Tab 4
    ];

    return Scaffold(
      backgroundColor: const Color(0xFFEEF4FF),
      body: pages[_currentIndex],
      bottomNavigationBar: CustomBottomNav(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
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