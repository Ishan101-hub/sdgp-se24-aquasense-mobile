import 'package:flutter/material.dart';
import 'iot_connectivity_screen.dart';
import 'installation_guide_screen.dart';
import 'nwsdb_coordination_screen.dart';
import 'user_manual_screen.dart';

class SupportScreen extends StatelessWidget {
  const SupportScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const Color brandBlue = Color(0xFF0A1B6F);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: const Text(
          "Customer Support",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: brandBlue,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header Section — always stays brandBlue, no change needed
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
              child: Column(
                children: [
                  const Icon(Icons.headset_mic, color: Colors.white, size: 60),
                  const SizedBox(height: 15),
                  const Text(
                    "How can we help you?",
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "Our team is available for your water management needs",
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.8),
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),

            Padding(
              padding: const EdgeInsets.fromLTRB(20, 30, 20, 10),
              child: Text(
                "Quick Contact",
                style: textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : brandBlue,
                ),
              ),
            ),

            // Contact Buttons
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Row(
                children: [
                  _buildContactCard(
                    context,
                    Icons.phone,
                    "Call Us",
                    "Emergency Leaks",
                    Colors.green,
                    isDark,
                    textTheme,
                  ),
                  const SizedBox(width: 15),
                  _buildContactCard(
                    context,
                    Icons.email,
                    "Email",
                    "General Queries",
                    Colors.orange,
                    isDark,
                    textTheme,
                  ),
                ],
              ),
            ),

            Padding(
              padding: const EdgeInsets.fromLTRB(20, 30, 20, 10),
              child: Text(
                "Support Categories",
                style: textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : brandBlue,
                ),
              ),
            ),

            _buildSupportTile(
              context,
              Icons.wifi,
              "IoT Device Connectivity",
              IoTConnectivityScreen(),
              isDark,
              textTheme,
            ),
            _buildSupportTile(
              context,
              Icons.plumbing,
              "Installation Guide",
              InstallationGuideScreen(),
              isDark,
              textTheme,
            ),
            _buildSupportTile(
              context,
              Icons.account_balance,
              "NWSDB Coordination",
              NWSDBCoordinationScreen(),
              isDark,
              textTheme,
            ),
            _buildSupportTile(
              context,
              Icons.info_outline,
              "App User Manual",
              UserManualScreen(),
              isDark,
              textTheme,
            ),
            const SizedBox(height: 30),
          ],
        ),
      ),
    );
  }

  Widget _buildContactCard(
    BuildContext context,
    IconData icon,
    String title,
    String subtitle,
    Color color,
    bool isDark,
    TextTheme textTheme,
  ) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          borderRadius: BorderRadius.circular(15),
          boxShadow: [
            BoxShadow(
              color: isDark
                  ? Colors.black.withOpacity(0.3)
                  : Colors.black.withOpacity(0.05),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 30),
            const SizedBox(height: 10),
            Text(
              title,
              style: textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              subtitle,
              textAlign: TextAlign.center,
              style: textTheme.bodySmall?.copyWith(
                color: isDark ? Colors.grey[400] : Colors.grey[600],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSupportTile(
    BuildContext context,
    IconData icon,
    String title,
    Widget destination,
    bool isDark,
    TextTheme textTheme,
  ) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: isDark
                ? Colors.black.withOpacity(0.3)
                : Colors.black.withOpacity(0.03),
            blurRadius: 5,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: ListTile(
        leading: Icon(
          icon,
          color: isDark ? Colors.lightBlueAccent : const Color(0xFF0A1B6F),
        ),
        title: Text(
          title,
          style: textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w500),
        ),
        trailing: Icon(
          Icons.arrow_forward_ios,
          size: 14,
          color: isDark ? Colors.grey[400] : Colors.grey[600],
        ),
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (context) => destination),
          );
        },
      ),
    );
  }
}
