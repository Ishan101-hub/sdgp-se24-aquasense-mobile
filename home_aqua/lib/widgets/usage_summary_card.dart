import 'package:flutter/material.dart';

class UsageSummaryCard extends StatelessWidget {

  // Test values for now
  // When backend ready, replace with real API data
  final double dailyAverage;
  final double dailyConsumption;
  final double weeklyAverage;
  final double weeklyConsumption;
  final double monthlyAverage;
  final double monthlyConsumption;

  const UsageSummaryCard({
    super.key,
    this.dailyAverage     = 150,  // test value
    this.dailyConsumption = 220,  // test value
    this.weeklyAverage    = 1050, // test value
    this.weeklyConsumption = 800, // test value
    this.monthlyAverage   = 215,  // test value
    this.monthlyConsumption = 270, // test value
  });

  @override
  Widget build(BuildContext context) {
    // Max value for bar width calculation
    // We use the largest value so bars scale correctly
    double maxValue = [
      dailyAverage,
      dailyConsumption,
      weeklyAverage,
      weeklyConsumption,
      monthlyAverage,
      monthlyConsumption,
    ].reduce((a, b) => a > b ? a : b);

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.blue.withValues(alpha: 0.08),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [

          // ── LEGEND ROW: Average + Consumption ──
          Row(
            children: [

              // Average legend
              Row(
                children: [
                  Container(
                    width: 20,
                    height: 20,
                    decoration: BoxDecoration(
                      color: const Color(0xFFCDD8F0), // light blue
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'Average',
                    style: TextStyle(
                      fontSize: 13,
                      color: Color(0xFF1A1A6E),
                    ),
                  ),
                ],
              ),

              const SizedBox(width: 24),

              // Consumption legend
              Row(
                children: [
                  Container(
                    width: 20,
                    height: 20,
                    decoration: BoxDecoration(
                      color: const Color(0xFF1A1A6E), // navy blue
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'Consumption',
                    style: TextStyle(
                      fontSize: 13,
                      color: Color(0xFF1A1A6E),
                    ),
                  ),
                ],
              ),

            ],
          ),

          const SizedBox(height: 20),

          // ── DAILY ROW ──
          _SummaryRow(
            label: 'Daily',
            averageValue: dailyAverage,
            consumptionValue: dailyConsumption,
            maxValue: maxValue,
          ),

          const SizedBox(height: 16),

          // ── WEEKLY ROW ──
          _SummaryRow(
            label: 'Weekly',
            averageValue: weeklyAverage,
            consumptionValue: weeklyConsumption,
            maxValue: maxValue,
          ),

          const SizedBox(height: 16),

          // ── MONTHLY ROW ──
          _SummaryRow(
            label: 'Monthly',
            averageValue: monthlyAverage,
            consumptionValue: monthlyConsumption,
            maxValue: maxValue,
          ),

        ],
      ),
    );
  }
}


// ── SINGLE SUMMARY ROW ───────────────────────────────────────
// Shows label + 2 horizontal bars (average + consumption)
// Example:
//   Daily   [░░░░░░░░░░░░] 150 liters  ← light blue (average)
//            [████████░░░] 220 liters  ← navy blue (consumption)
class _SummaryRow extends StatelessWidget {
  final String label;
  final double averageValue;
  final double consumptionValue;
  final double maxValue;

  const _SummaryRow({
    required this.label,
    required this.averageValue,
    required this.consumptionValue,
    required this.maxValue,
  });

  @override
  Widget build(BuildContext context) {
    double averageRatio     = (averageValue / maxValue).clamp(0.0, 1.0);
    double consumptionRatio = (consumptionValue / maxValue).clamp(0.0, 1.0);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [

        // ── LABEL (Daily / Weekly / Monthly) ──
        SizedBox(
          width: 65,
          child: Text(
            label,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: Color(0xFF1A1A6E),
            ),
          ),
        ),

        // ── TWO BARS COLUMN ──
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [

              // Average bar (light blue) + value
              Row(
                children: [
                  Expanded(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(
                        value: averageRatio,
                        minHeight: 22,
                        backgroundColor: Colors.transparent,
                        valueColor: const AlwaysStoppedAnimation<Color>(
                          Color(0xFFCDD8F0), // light blue
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '${averageValue.toInt()} liters',
                    style: const TextStyle(
                      fontSize: 11,
                      color: Color(0xFF888888),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 4),

              // Consumption bar (navy blue) + value
              Row(
                children: [
                  Expanded(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(
                        value: consumptionRatio,
                        minHeight: 22,
                        backgroundColor: Colors.transparent,
                        valueColor: const AlwaysStoppedAnimation<Color>(
                          Color(0xFF1A1A6E), // navy blue
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '${consumptionValue.toInt()} liters',
                    style: const TextStyle(
                      fontSize: 11,
                      color: Color(0xFF888888),
                    ),
                  ),
                ],
              ),

            ],
          ),
        ),

      ],
    );
  }
}