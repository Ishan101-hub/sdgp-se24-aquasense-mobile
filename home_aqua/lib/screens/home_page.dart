import 'package:flutter/material.dart';
import '../widgets/today_card.dart';
import '../widgets/water_status_card.dart';
import '../widgets/daily_consumption_card.dart';
import '../widgets/bell_button.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(
        children: [

          // ── SCROLLABLE CONTENT ──
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
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

                ],
              ),
            ),
          ),

          // ── BELL BUTTON at bottom right ──
          Padding(
            padding: const EdgeInsets.only(
              right: 16,
              bottom: 16,
            ),
            child: const Align(
              alignment: Alignment.centerRight,
              child: BellButton(
                hasNotification: false, // no red dot for now
              ),
            ),
          ),

        ],
      ),
    );
  }
}