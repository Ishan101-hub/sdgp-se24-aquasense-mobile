import 'package:flutter/material.dart';
import '../widgets/today_card.dart';
import '../widgets/water_status_card.dart';
import '../widgets/daily_consumption_card.dart'; // ← new import

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [

            // ── TOP ROW: Today card + Water Status card ──
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [

                // Today Card (left side)
                Expanded(
                  child: TodayCard(),
                ),

                SizedBox(width: 12),

                // Water Status Card (right side)
                Expanded(
                  child: WaterStatusCard(),
                ),

              ],
            ),

            const SizedBox(height: 16),

            // ── PART 3.1: Daily Consumption card ──
            const DailyConsumptionCard(), // ← replaced placeholder

          ],
        ),
      ),
    );
  }
}