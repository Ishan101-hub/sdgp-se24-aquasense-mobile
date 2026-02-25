import 'package:flutter/material.dart';
import '../widgets/today_card.dart';
import '../widgets/water_status_card.dart';
import '../widgets/daily_consumption_card.dart';
import '../widgets/bell_button.dart';
import '../widgets/usage_chart_card.dart';
import '../widgets/usage_summary_card.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {

    // ── ZONES (single source of truth) ──
    // This is the ONLY place where zone data is defined
    // Both TodayCard and DailyConsumptionCard use this same data
    // So they will ALWAYS match! ✅
    const List<WaterZone> zones = [
      WaterZone(name: 'Kitchen',  used: 80,  average: 100),
      WaterZone(name: 'Bathroom', used: 140, average: 120), // over → red
      WaterZone(name: 'Outdoor',  used: 50,  average: 80),
      // Add more zones here to test:
      // WaterZone(name: 'Kitchen 2', used: 60, average: 90),
    ];

    // ── AUTO CALCULATE total usage from zones ──
    // 80 + 140 + 50 = 270L → Today card shows 270L
    final double totalUsed = zones.fold(
      0,
      (sum, zone) => sum + zone.used,
    );

    // ── AUTO CALCULATE total average from zones ──
    // 100 + 120 + 80 = 300L → daily average is 300L
    final double totalAverage = zones.fold(
      0,
      (sum, zone) => sum + zone.average,
    );

    // ── AUTO CALCULATE percentage ──
    // 270 / 300 = 90% of daily average
    final double dailyAveragePercent = totalAverage > 0
        ? (totalUsed / totalAverage * 100).clamp(0, 999)
        : 0;

    return SafeArea(
      child: Stack(
        children: [

          // ── SCROLLABLE CONTENT ──
          SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
            child: Column(
              children: [

                // ── TOP ROW: Today card + Water Status card ──
                IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [

                      // Today Card gets auto-calculated values from zones
                      Expanded(
                        child: TodayCard(
                          litresUsed: totalUsed,           // sum of all zones ✅
                          dailyAverageLitres: totalAverage, // sum of all averages ✅
                          dailyAveragePercent: dailyAveragePercent, // auto % ✅
                        ),
                      ),

                      const SizedBox(width: 12),

                      const Expanded(
                        child: WaterStatusCard(),
                      ),

                    ],
                  ),
                ),

                const SizedBox(height: 16),

                // Daily Consumption card gets same zones list
                DailyConsumptionCard(zones: zones),

                const SizedBox(height: 16),

                // Usage Chart
                const UsageChartCard(),

                const SizedBox(height: 16),

                // Usage Summary
                const UsageSummaryCard(),

              ],
            ),
          ),

          // ── BELL BUTTON ──
          Positioned(
            bottom: 16,
            right: 16,
            child: BellButton(
              hasNotification: false,
            ),
          ),

        ],
      ),
    );
  }
}