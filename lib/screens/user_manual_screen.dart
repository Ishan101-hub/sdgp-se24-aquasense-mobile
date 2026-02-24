import 'package:flutter/material.dart';
import '../widgets/support_card.dart';

class UserManualScreen extends StatelessWidget {
  const UserManualScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const Color brandBlue = Color(0xFF0A1B6F);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFF),
      appBar: AppBar(
        title: const Text(
          "User Manual",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: brandBlue,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // Header Section
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(25),
              decoration: const BoxDecoration(
                color: brandBlue,
                borderRadius: BorderRadius.only(
                  bottomLeft: Radius.circular(30),
                  bottomRight: Radius.circular(30),
                ),
              ),
              child: const Column(
                children: [
                  Icon(Icons.menu_book, color: Colors.white, size: 60),
                  SizedBox(height: 10),
                  Text(
                    "App Navigation",
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
            // Steps Section
            const Padding(
              padding: EdgeInsets.all(20),
              child: Column(
                children: [
                  SupportCard(
                    step: 1,
                    icon: Icons.home,
                    title: "Home Dashboard",
                    desc:
                        "Monitor your current flow rate and daily consumption total at a glance.",
                    color: brandBlue,
                  ),
                  SupportCard(
                    step: 2,
                    icon: Icons.analytics,
                    title: "Analyze Trends",
                    desc:
                        "Check the 'Report' tab for weekly and monthly water usage bar charts.",
                    color: Colors.orange,
                  ),
                  SupportCard(
                    step: 3,
                    icon: Icons.settings,
                    title: "Settings",
                    desc:
                        "Configure high-flow notifications and manage your IoT device pairing.",
                    color: Colors.green,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
