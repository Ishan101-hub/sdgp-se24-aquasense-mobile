import 'package:flutter/material.dart';
import '../widgets/support_card.dart';

class NWSDBCoordinationScreen extends StatelessWidget {
  const NWSDBCoordinationScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const Color brandBlue = Color(0xFF0A1B6F);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFF),
      appBar: AppBar(
        title: const Text(
          "NWSDB Coordination",
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
                  Icon(Icons.account_balance, color: Colors.white, size: 60),
                  SizedBox(height: 10),
                  Text(
                    "Official Coordination",
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
                    icon: Icons.report_problem,
                    title: "Report Leak",
                    desc:
                        "Share your app's leak logs with NWSDB for faster emergency repairs.",
                    color: brandBlue,
                  ),
                  SupportCard(
                    step: 2,
                    icon: Icons.receipt_long,
                    title: "Billing Proof",
                    desc:
                        "Use your 'Usage History' to dispute inaccurate water bills at the NWSDB office.",
                    color: Colors.orange,
                  ),
                  SupportCard(
                    step: 3,
                    icon: Icons.phone_in_talk,
                    title: "Call Hotline",
                    desc:
                        "Dial 1939 directly for government water supply emergencies.",
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
