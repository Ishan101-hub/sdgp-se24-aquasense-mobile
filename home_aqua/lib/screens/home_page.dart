import 'package:flutter/material.dart';
import '../widgets/today_card.dart';
import '../widgets/water_status_card.dart'; // ← new import

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFEEF4FF),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [

              // ── TOP ROW: Today card + Water Status card ──
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [

                  // Today Card (left side)
                  Expanded(
                    child: TodayCard(),
                  ),

                  const SizedBox(width: 12),

                  // Water Status Card (right side)
                  Expanded(
                    child: WaterStatusCard(), // ← replaced placeholder
                  ),

                ],
              ),

              const SizedBox(height: 16),

              // ── Daily Consumption card placeholder ──
              Container(
                width: double.infinity,
                height: 160,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.blue.withOpacity(0.08),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: const Center(
                  child: Text(
                    'Daily Consumption\n(coming soon)',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.grey),
                  ),
                ),
              ),

            ],
          ),
        ),
      ),
    );
  }
}