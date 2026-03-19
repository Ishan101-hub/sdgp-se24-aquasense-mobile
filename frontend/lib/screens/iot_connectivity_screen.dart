import 'package:flutter/material.dart';
import '../widgets/support_card.dart';

class IoTConnectivityScreen extends StatelessWidget {
  const IoTConnectivityScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const Color brandBlue = Color(0xFF0A1B6F);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: const Text(
          "IoT Connectivity",
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
                  Icon(Icons.wifi_tethering, color: Colors.white, size: 60),
                  SizedBox(height: 10),
                  Text(
                    "Device Pairing Guide",
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
                    icon: Icons.bluetooth_searching,
                    title: "Enable Pairing",
                    desc:
                        "Hold the 'Pair' button on your ESP32 box for 5 seconds until the blue LED blinks.",
                    color: brandBlue,
                  ),
                  SupportCard(
                    step: 2,
                    icon: Icons.wifi,
                    title: "Network Setup",
                    desc:
                        "Connect your phone to the 'AquaSense_Setup' Wi-Fi and enter your home credentials.",
                    color: Colors.orange,
                  ),
                  SupportCard(
                    step: 3,
                    icon: Icons.cloud_done,
                    title: "Cloud Sync",
                    desc:
                        "Once the green LED is solid, your device is successfully pushing data to the dashboard.",
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
