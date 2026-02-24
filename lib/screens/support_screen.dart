import 'package:flutter/material.dart';

class SupportScreen extends StatelessWidget {
  const SupportScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // Brand Color as per your project report
    const Color brandBlue = Color(0xFF0A1B6F);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFF),
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
            // Header Section
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(25),
              decoration: BoxDecoration(
                color: brandBlue,
                borderRadius: const BorderRadius.only(
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

            const Padding(
              padding: EdgeInsets.fromLTRB(20, 30, 20, 10),
              child: Text(
                "Quick Contact",
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: brandBlue,
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
                  ),
                  const SizedBox(width: 15),
                  _buildContactCard(
                    context,
                    Icons.email,
                    "Email",
                    "General Queries",
                    Colors.orange,
                  ),
                ],
              ),
            ),

            const Padding(
              padding: EdgeInsets.fromLTRB(20, 30, 20, 10),
              child: Text(
                "Support Categories",
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: brandBlue,
                ),
              ),
            ),

            // Support List
            _buildSupportTile(Icons.wifi, "IoT Device Connectivity"),
            _buildSupportTile(Icons.plumbing, "Installation Guide"),
            _buildSupportTile(Icons.account_balance, "NWSDB Coordination"),
            _buildSupportTile(Icons.info_outline, "App User Manual"),
            
            const SizedBox(height: 30),
          ],
        ),
      ),
    );
  }

  Widget _buildContactCard(BuildContext context, IconData icon, String title, String subtitle, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(15),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
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
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
            const SizedBox(height: 4),
            Text(
              subtitle,
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey[600], fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSupportTile(IconData icon, String title) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
      ),
      child: ListTile(
        leading: Icon(icon, color: const Color(0xFF0A1B6F)),
        title: Text(
          title,
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w500),
        ),
        trailing: const Icon(Icons.arrow_forward_ios, size: 14),
        onTap: () {},
      ),
    );
  }
}