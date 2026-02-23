import 'package:flutter/material.dart';

class TodayCard extends StatelessWidget {
  const TodayCard({super.key});

  @override
  Widget build(BuildContext context) {

    // ── These values will come from backend later ──
    double totalLiters = 220.4;      // actual usage today with decimal
    double dailyAverage = 458.0;     // average daily usage
    double percentage = totalLiters / dailyAverage; // 0.48 = 48%

    return Card(
      elevation: 4,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Container(
        width: 160,
        height: 200,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [

            // Title: "Today"
            const Text(
              'Today',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFF1A237E),
              ),
            ),

            const SizedBox(height: 12),

            // Part 1.4 - Round loading bar with litres inside
            SizedBox(
              width: 90,
              height: 90,
              child: Stack(
                alignment: Alignment.center,
                children: [

                  // circular progress bar
                  SizedBox(
                    width: 90,
                    height: 90,
                    child: CircularProgressIndicator(
                      value: percentage,
                      strokeWidth: 7,
                      backgroundColor: const Color(0xFFE0E0E0),
                      valueColor: const AlwaysStoppedAnimation<Color>(
                        Color(0xFF1A237E),
                      ),
                    ),
                  ),

                  // Part 1.3 - litres text inside the circle
                  Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [

                      // ✅ toStringAsFixed(1) shows one decimal point
                      // eg: 220.4 instead of 220
                      Text(
                        totalLiters.toStringAsFixed(1),
                        style: const TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF1A237E),
                        ),
                      ),
                      const Text(
                        'Liters',
                        style: TextStyle(
                          fontSize: 11,
                          color: Color(0xFF757575),
                        ),
                      ),
                    ],
                  ),

                ],
              ),
            ),

            const Spacer(),

            // Part 1.2 - percentage text
            Text(
              '${(percentage * 100).toStringAsFixed(1)}% of daily average',
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 11,
                color: Color(0xFF757575),
              ),
            ),

          ],
        ),
      ),
    );
  }
}