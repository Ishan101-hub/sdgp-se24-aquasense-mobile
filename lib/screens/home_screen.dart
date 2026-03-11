import 'package:flutter/material.dart';
import '../widgets/custom_bottom_nav.dart';
import 'usage_screen.dart';
import 'services_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int selectedIndex = 0;

  final pages = [
    const Center(child: Text("Home", style: TextStyle(fontSize: 22))),
    const Center(child: Text("Leakages", style: TextStyle(fontSize: 22))),
    UsageScreen(), // Now linked to the 'Report' tab
    ServicesScreen(), // Linked to the 'Service' tab
    const Center(child: Text("Settings", style: TextStyle(fontSize: 22))),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: pages[selectedIndex],
      bottomNavigationBar: CustomBottomNav(
        currentIndex: selectedIndex,
        onTap: (index) {
          setState(() {
            selectedIndex = index;
          });
        },
      ),
    );
  }
}
