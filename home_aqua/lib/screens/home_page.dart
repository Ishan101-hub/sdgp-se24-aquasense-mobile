import 'package:flutter/material.dart';
import '../widgets/today_card.dart';
import '../widgets/water_status_card.dart';
import '../widgets/daily_consumption_card.dart';
import '../widgets/bell_button.dart';
import '../widgets/usage_chart_card.dart';
import '../widgets/usage_summary_card.dart'; // ← new import

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
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
                    children: const [
                      Expanded(child: TodayCard()),
                      SizedBox(width: 12),
                      Expanded(child: WaterStatusCard()),
                    ],
                  ),
                ),

                const SizedBox(height: 16),

                // ── Daily Consumption card ──
                const DailyConsumptionCard(),

                const SizedBox(height: 16),

                // ── SCROLL DOWN: Usage Chart ──
                const UsageChartCard(),

                const SizedBox(height: 16),

                // ── SCROLL DOWN: Usage Summary bars ──
                const UsageSummaryCard(),

              ],
            ),
          ),

          // ── BELL BUTTON fixed at bottom right ──
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