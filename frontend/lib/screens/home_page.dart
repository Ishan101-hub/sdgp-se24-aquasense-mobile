import 'package:flutter/material.dart';
import '../widgets/today_card.dart';
import '../widgets/water_status_card.dart';
import '../widgets/daily_consumption_card.dart';
import '../widgets/bell_button.dart';
import '../widgets/usage_chart_card.dart';
import '../widgets/usage_summary_card.dart';

class HomePage extends StatelessWidget {
  final void Function(int tabIndex) onSwitchTab;

  const HomePage({
    super.key,
    required this.onSwitchTab,
  });

  @override
  Widget build(BuildContext context) {

    final isDark = Theme.of(context).brightness == Brightness.dark;

    const List<WaterZone> zones = [
      WaterZone(name: 'Kitchen',  used: 80,  average: 100),
      WaterZone(name: 'Bathroom', used: 140, average: 120),
      WaterZone(name: 'Outdoor',  used: 50,  average: 80),
    ];

    final double totalUsed    = zones.fold(0, (sum, z) => sum + z.used);
    final double totalAverage = zones.fold(0, (sum, z) => sum + z.average);
    final double percent      = totalAverage > 0
        ? (totalUsed / totalAverage * 100).clamp(0, 999)
        : 0;

    final List<AppNotification> notifications = [

      ...zones
          .where((z) => z.used >= z.average)
          .map((z) => AppNotification(
                title: 'Over Limit: ${z.name}',
                message:
                    '${z.name} consumption reached ${z.used.toStringAsFixed(1)}L, '
                    'exceeding the daily average of ${z.average.toStringAsFixed(1)}L.',
                type: 'consumption',
                time: 'Just now',
                targetTabIndex: 0,
              )),

      const AppNotification(
        title: 'Leak Detected: Kitchen',
        message:
            'A water leak has been detected in the Kitchen pipeline. '
            'IN: 23.1 L/min, OUT: 15.7 L/min. Please check immediately.',
        type: 'leak',
        time: '5 mins ago',
        targetTabIndex: 1,
      ),

    ];

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF121212) : const Color(0xFFEEF4FF),

      body: SafeArea(
        child: Stack(
          children: [

            SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),

              child: Column(
                children: [

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

                        const Expanded(
                          child: WaterStatusCard(),
                        ),

                      ],
                    ),
                  ),

                  const SizedBox(height: 16),

                  DailyConsumptionCard(zones: zones),

                  const SizedBox(height: 16),

                  UsageChartCard(todayUsage: totalUsed),

                  const SizedBox(height: 16),

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

            Positioned(
              bottom: 16,
              right: 16,
              child: BellButton(
                hasNotification: notifications.isNotEmpty,
                notifications: notifications,
                onSwitchTab: onSwitchTab,
              ),
            ),

          ],
        ),
      ),
    );
  }
}