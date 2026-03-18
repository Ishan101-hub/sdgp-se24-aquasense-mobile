import 'package:flutter/material.dart';

class UsageSummaryCard extends StatelessWidget {
  final double dailyAverage;
  final double dailyConsumption;
  final double weeklyAverage;
  final double weeklyConsumption;
  final double monthlyAverage;
  final double monthlyConsumption;

  const UsageSummaryCard({
    super.key,
    this.dailyAverage      = 300,
    this.dailyConsumption  = 0,
    this.weeklyAverage     = 1050,
    this.weeklyConsumption = 800,
    this.monthlyAverage    = 215,
    this.monthlyConsumption = 270,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    double maxValue = [
      dailyAverage, dailyConsumption,
      weeklyAverage, weeklyConsumption,
      monthlyAverage, monthlyConsumption,
    ].reduce((a, b) => a > b ? a : b);

    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E1E1E) : Colors.white, // ← dark card
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

          // ── Legend ──
          Row(
            children: [
              Row(children: [
                Container(width: 20, height: 20,
                    decoration: BoxDecoration(color: const Color(0xFFCDD8F0), borderRadius: BorderRadius.circular(4))),
                const SizedBox(width: 6),
                Text('Average', style: TextStyle(fontSize: 13,
                    color: isDark ? Colors.white70 : const Color(0xFF1A1A6E))),
              ]),
              const SizedBox(width: 24),
              Row(children: [
                Container(width: 20, height: 20,
                    decoration: BoxDecoration(color: const Color(0xFF1A1A6E), borderRadius: BorderRadius.circular(4))),
                const SizedBox(width: 6),
                Text('Consumption', style: TextStyle(fontSize: 13,
                    color: isDark ? Colors.white70 : const Color(0xFF1A1A6E))),
              ]),
            ],
          ),

          const SizedBox(height: 20),

          _SummaryRow(label: 'Daily',   averageValue: dailyAverage,   consumptionValue: dailyConsumption,   maxValue: maxValue, isDark: isDark),
          const SizedBox(height: 16),
          _SummaryRow(label: 'Weekly',  averageValue: weeklyAverage,  consumptionValue: weeklyConsumption,  maxValue: maxValue, isDark: isDark),
          const SizedBox(height: 16),
          _SummaryRow(label: 'Monthly', averageValue: monthlyAverage, consumptionValue: monthlyConsumption, maxValue: maxValue, isDark: isDark),

        ],
      ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  final String label;
  final double averageValue;
  final double consumptionValue;
  final double maxValue;
  final bool   isDark;

  const _SummaryRow({
    required this.label,
    required this.averageValue,
    required this.consumptionValue,
    required this.maxValue,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    double averageRatio     = (averageValue / maxValue).clamp(0.0, 1.0);
    double consumptionRatio = (consumptionValue / maxValue).clamp(0.0, 1.0);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [

        SizedBox(
          width: 65,
          child: Text(label, style: TextStyle(
            fontSize: 14, fontWeight: FontWeight.w600,
            color: isDark ? Colors.white : const Color(0xFF1A1A6E),
          )),
        ),

        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [

              Row(children: [
                Expanded(child: ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: LinearProgressIndicator(
                    value: averageRatio, minHeight: 22,
                    backgroundColor: isDark ? const Color(0xFF333333) : Colors.transparent,
                    valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFFCDD8F0)),
                  ),
                )),
                const SizedBox(width: 8),
                Text('${averageValue.toInt()} liters',
                    style: TextStyle(fontSize: 11,
                        color: isDark ? Colors.white54 : const Color(0xFF888888))),
              ]),

              const SizedBox(height: 4),

              Row(children: [
                Expanded(child: ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: LinearProgressIndicator(
                    value: consumptionRatio, minHeight: 22,
                    backgroundColor: isDark ? const Color(0xFF333333) : Colors.transparent,
                    valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF1A1A6E)),
                  ),
                )),
                const SizedBox(width: 8),
                Text('${consumptionValue.toStringAsFixed(1)} liters',
                    style: TextStyle(fontSize: 11,
                        color: isDark ? Colors.white54 : const Color(0xFF888888))),
              ]),

            ],
          ),
        ),
      ],
    );
  }
}