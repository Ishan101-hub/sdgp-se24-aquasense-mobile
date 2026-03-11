import 'package:flutter/material.dart';
import '../widgets/service_card.dart';
import 'plumbers_screen.dart';
import 'support_screen.dart'; // Added import
import 'report_issue_screen.dart'; // Added import
import 'installation_screen.dart'; // Added import

class ServicesScreen extends StatelessWidget {
  const ServicesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // AquaSense primary color defined in your hardware/software requirements [cite: 177, 183]
    const Color brandBlue = Color(0xFF0A1B6F);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFF),
      appBar: AppBar(
        title: const Text(
          'Our Services',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: brandBlue,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: GridView.count(
          crossAxisCount: 2,
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
          // Ratio set to 0.70 to make cards taller for better visibility on Redmi Note 9S
          childAspectRatio: 0.58,
          children: [
            // 1. New Installation
            ServiceCard(
              icon: Icons.build,
              title: 'New Installation',
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const InstallationScreen(),
                  ),
                );
              },
            ),

            // 2. Registered Plumbers
            ServiceCard(
              icon: Icons.engineering,
              title: 'Registered Plumbers',
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const PlumbersScreen(),
                  ),
                );
              },
            ),

            // 3. Report Issue
            ServiceCard(
              icon: Icons.report_gmailerrorred,
              title: 'Report Issue',
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const ReportIssueScreen(),
                  ),
                );
              },
            ),

            // 4. Customer Support
            ServiceCard(
              icon: Icons.headset_mic,
              title: 'Customer Support',
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const SupportScreen(),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
