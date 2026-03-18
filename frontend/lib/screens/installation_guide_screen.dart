import 'package:flutter/material.dart';
import '../widgets/support_card.dart';

class InstallationGuideScreen extends StatelessWidget {
  const InstallationGuideScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const Color brandBlue = Color(0xFF0A1B6F);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
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
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header Banner — stays brandBlue in both modes
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
                  Icon(Icons.plumbing, color: Colors.white, size: 60),
                  SizedBox(height: 10),
                  Text(
                    "Hardware Setup",
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
              padding: const EdgeInsets.fromLTRB(20, 25, 20, 10),
              child: Text(
                "Setup Steps",
                style: textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : brandBlue,
                ),
              ),
            ),

            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 20),
              child: Column(
                children: [
                  SupportCard(
                    step: 1,
                    icon: Icons.water_drop,
                    title: "Mount Sensor",
                    desc:
                        "Install the flow sensor on the main water inlet pipe of your house.",
                    color: brandBlue,
                  ),
                  SupportCard(
                    step: 2,
                    icon: Icons.electrical_services,
                    title: "Connect Pins",
                    desc:
                        "Plug the sensor wires into the designated GPIO pins on your AquaSense box.",
                    color: Colors.orange,
                  ),
                  SupportCard(
                    step: 3,
                    icon: Icons.power,
                    title: "Power On",
                    desc:
                        "Plug in the 5V adapter. The status LED should turn blue.",
                    color: Colors.green,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}
