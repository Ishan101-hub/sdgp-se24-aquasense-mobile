import 'package:flutter/material.dart';
import '../widgets/service_card.dart';
import 'plumbers_screen.dart';
import 'support_screen.dart';
import 'report_issue_screen.dart';
import 'installation_screen.dart';

class ServicesScreen extends StatelessWidget {
  const ServicesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const Color brandBlue = Color(0xFF0A1B6F);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFF),
      appBar: AppBar(
        title: const Text('Our Services', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: brandBlue,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: GridView.count(
          crossAxisCount:   2,
          crossAxisSpacing: 16,
          mainAxisSpacing:  16,
          childAspectRatio: 0.58,
          children: [

            ServiceCard(
              icon:  Icons.build,
              title: 'New Installation',
              onTap: () => Navigator.push(context,
                  MaterialPageRoute(builder: (_) => const InstallationScreen())),
            ),

            ServiceCard(
              icon:  Icons.engineering,
              title: 'Registered Plumbers',
              onTap: () => Navigator.push(context,
                  MaterialPageRoute(builder: (_) => const PlumbersScreen())),
            ),

            ServiceCard(
              icon:  Icons.report_gmailerrorred,
              title: 'Report Issue',
              onTap: () => Navigator.push(context,
                  MaterialPageRoute(builder: (_) => const ReportIssueScreen())),
            ),

            ServiceCard(
              icon:  Icons.headset_mic,
              title: 'Customer Support',
              onTap: () => Navigator.push(context,
                  MaterialPageRoute(builder: (_) => const SupportScreen())),
            ),

          ],
        ),
      ),
    );
  }
}