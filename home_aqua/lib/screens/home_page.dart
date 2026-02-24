import 'package:flutter/material.dart';
import '../widgets/today_card.dart';
import '../widgets/water_status_card.dart';
import '../widgets/daily_consumption_card.dart';

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
            // ── FIXED: CrossAxisAlignment.stretch makes both cards same height ──
            IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch, // ← KEY FIX
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
            ),

            const SizedBox(height: 16),

            // ── Daily Consumption card ──
            const DailyConsumptionCard(),

          ],
        ),
      ),
    );
  }
}