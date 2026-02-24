import 'package:flutter/material.dart';
import '../widgets/custom_bottom_nav.dart';
import 'home_page.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  // ── FIXED: added const to all _PlaceholderPage ──
  final List<Widget> _pages = const [
    HomePage(),
    _PlaceholderPage('Leakages'),
    _PlaceholderPage('Report'),
    _PlaceholderPage('Service'),
    _PlaceholderPage('Settings'),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFEEF4FF),
      body: _pages[_currentIndex],
      bottomNavigationBar: CustomBottomNav(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });
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