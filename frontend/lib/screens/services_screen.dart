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
    // 1. Get Theme Data for Dynamic Styling
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    // Use Brand Blue for Light Mode, and a lighter version or White for Dark Mode title
    final Color titleColor = isDark ? Colors.white : const Color(0xFF0A1B6F);

    // 2. Get Screen Dimensions for Scaling
    final double screenWidth = MediaQuery.of(context).size.width;
    final double scale = screenWidth / 393;

    return Scaffold(
      // Automatically uses theme's background color
      backgroundColor: theme.scaffoldBackgroundColor,
      body: SafeArea(
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(
            parent: BouncingScrollPhysics(),
          ),
          padding: EdgeInsets.all(16.0 * scale),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: EdgeInsets.symmetric(vertical: 10 * scale),
                child: Text(
                  'Our Services',
                  style: theme.textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    fontSize: 26 * scale,
                    color: titleColor, // Dynamically adjusted color
                  ),
                ),
              ),
              SizedBox(height: 10 * scale),
              GridView.count(
                crossAxisCount: 2,
                crossAxisSpacing: 16 * scale,
                mainAxisSpacing: 16 * scale,
                childAspectRatio: 0.85,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  ServiceCard(
                    icon: Icons.build,
                    title: 'New Installation',
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const InstallationScreen(),
                      ),
                    ),
                  ),
                  ServiceCard(
                    icon: Icons.engineering,
                    title: 'Registered Plumbers',
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const PlumbersScreen(),
                      ),
                    ),
                  ),
                  ServiceCard(
                    icon: Icons.report_gmailerrorred,
                    title: 'Report Issue',
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const ReportIssueScreen(),
                      ),
                    ),
                  ),
                  ServiceCard(
                    icon: Icons.headset_mic,
                    title: 'Customer Support',
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const SupportScreen(),
                      ),
                    ),
                  ),
                ],
              ),
              SizedBox(height: 30 * scale),
            ],
          ),
        ),
      ),
    );
  }
}
