import 'package:flutter/material.dart';

class InstallationGuideScreen extends StatelessWidget {
  const InstallationGuideScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // Using the AquaSense brand blue
    const Color brandBlue = Color(0xFF0A1B6F);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFF),
      appBar: AppBar(
        title: const Text(
          "Setup Guide",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: brandBlue,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // Header Hero Section
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
                  Icon(Icons.settings_suggest, color: Colors.white, size: 60),
                  SizedBox(height: 10),
                  Text(
                    "3-Step Quick Setup",
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),

            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  _buildStepCard(
                    1,
                    Icons.plumbing,
                    "Mount Sensor",
                    "Attach the flow sensor firmly to the main water inlet pipe of your house.",
                    brandBlue,
                  ),
                  _buildStepCard(
                    2,
                    Icons.electrical_services,
                    "Connect ESP32",
                    "Connect the sensor wires to the GPIO pins of your ESP32 controller box.",
                    Colors.orange,
                  ),
                  _buildStepCard(
                    3,
                    Icons.power,
                    "Power On",
                    "Plug the 5V/2A power adapter into a standard 230V socket and check the LED.",
                    Colors.green,
                  ),

                  const SizedBox(height: 30),

                  // Help Footer
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: brandBlue.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(15),
                      border: Border.all(color: brandBlue.withOpacity(0.1)),
                    ),
                    child: const Row(
                      children: [
                        Icon(Icons.info_outline, color: brandBlue),
                        SizedBox(width: 15),
                        Expanded(
                          child: Text(
                            "Need a professional? Tap the 'Call Us' button on the Support page.",
                            style: TextStyle(color: brandBlue, fontSize: 13),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStepCard(
    int stepNumber,
    IconData icon,
    String title,
    String desc,
    Color color,
  ) {
    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            backgroundColor: color.withOpacity(0.1),
            child: Text(
              "$stepNumber",
              style: TextStyle(color: color, fontWeight: FontWeight.bold),
            ),
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 5),
                Text(
                  desc,
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 13,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
          Icon(icon, color: color.withOpacity(0.3), size: 40),
        ],
      ),
    );
  }
}
