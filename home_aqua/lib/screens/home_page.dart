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

    // ── SINGLE SOURCE OF TRUTH ──
    const List<WaterZone> zones = [
      WaterZone(name: 'Kitchen',  used: 80,  average: 100),
      WaterZone(name: 'Bathroom', used: 140, average: 120),
      WaterZone(name: 'Outdoor',  used: 50,  average: 80),
    ];

    // Auto-calculated from zones
    final double totalUsed    = zones.fold(0, (sum, z) => sum + z.used);
    final double totalAverage = zones.fold(0, (sum, z) => sum + z.average);
    final double percent      = totalAverage > 0
        ? (totalUsed / totalAverage * 100).clamp(0, 999)
        : 0;

    return SafeArea(
      child: Stack(
        children: [

          SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
            child: Column(
              children: [

                // ── Today + Water Status ──
                IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(
                        child: TodayCard(
                          litresUsed: totalUsed,
                          dailyAverageLitres: totalAverage,
                          dailyAveragePercent: percent,
                        ),
                      ),
                      const SizedBox(width: 12),
                      const Expanded(child: WaterStatusCard()),
                    ],
                  ),
                ),

                const SizedBox(height: 16),

                // ── Daily Consumption ──
                DailyConsumptionCard(zones: zones),

                const SizedBox(height: 16),

                // ── Usage Chart ──
                UsageChartCard(todayUsage: totalUsed),

                const SizedBox(height: 16),

                // ── Usage Summary ──
                // Daily < Weekly < Monthly ✅
                // Weekly  = daily × 7
                // Monthly = daily × 30
                UsageSummaryCard(
                  dailyAverage:       totalAverage,
                  dailyConsumption:   totalUsed,
                  weeklyAverage:      totalAverage * 7,
                  weeklyConsumption:  totalUsed * 7,
                  monthlyAverage:     totalAverage * 30,
                  monthlyConsumption: totalUsed * 30,
                ),

              ],
            ),
          ),

          // ── Bell button ──
          Positioned(
            bottom: 16,
            right: 16,
            child: BellButton(hasNotification: false),
          ),

        ],
      ),
    );
  }
}