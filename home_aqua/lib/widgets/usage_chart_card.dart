import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

// ── Chart periods ──
enum ChartPeriod { monthly, weekly, daily }

class UsageChartCard extends StatefulWidget {
  const UsageChartCard({super.key});

  @override
  State<UsageChartCard> createState() => _UsageChartCardState();
}

class _UsageChartCardState extends State<UsageChartCard> {

  // Currently selected period — starts on Monthly
  ChartPeriod _selected = ChartPeriod.monthly;

  // ── PART 1.1: Monthly test data ──
  // X = month index, Y = usage in m³
  // When backend ready, replace with real API data
  final List<FlSpot> _monthlyData = const [
    FlSpot(0, 20), // June
    FlSpot(1, 17), // July
    FlSpot(2, 7),  // Aug
    FlSpot(3, 25), // Sep
    FlSpot(4, 10), // Oct
  ];

  // ── PART 1.2: Weekly test data (placeholder for now) ──
  final List<FlSpot> _weeklyData = const [
    FlSpot(0, 12),
    FlSpot(1, 18),
    FlSpot(2, 15),
    FlSpot(3, 22),
    FlSpot(4, 9),
    FlSpot(5, 14),
    FlSpot(6, 20),
  ];

  // ── PART 1.3: Daily test data (placeholder for now) ──
  final List<FlSpot> _dailyData = const [
    FlSpot(0, 8),
    FlSpot(1, 15),
    FlSpot(2, 11),
    FlSpot(3, 19),
    FlSpot(4, 14),
    FlSpot(5, 22),
    FlSpot(6, 10),
  ];

  // Monthly x-axis labels
  final List<String> _monthLabels = ['June', 'July', 'Aug', 'Sep', 'Oct'];

  // Weekly x-axis labels
  final List<String> _weekLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  // Daily x-axis labels
  final List<String> _dayLabels = ['6am', '9am', '12pm', '3pm', '6pm', '9pm', '12am'];

  // Returns correct data based on selected period
  List<FlSpot> get _currentData {
    switch (_selected) {
      case ChartPeriod.monthly: return _monthlyData;
      case ChartPeriod.weekly:  return _weeklyData;
      case ChartPeriod.daily:   return _dailyData;
    }
  }

  // Returns correct labels based on selected period
  List<String> get _currentLabels {
    switch (_selected) {
      case ChartPeriod.monthly: return _monthLabels;
      case ChartPeriod.weekly:  return _weekLabels;
      case ChartPeriod.daily:   return _dayLabels;
    }
  }

  // Returns period label text
  String get _periodLabel {
    switch (_selected) {
      case ChartPeriod.monthly: return 'Last 5 Months';
      case ChartPeriod.weekly:  return 'Last 7 Days';
      case ChartPeriod.daily:   return 'Today';
    }
  }

  @override
  Widget build(BuildContext context) {
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

          // ── TOP ROW: Monthly / Weekly / Daily buttons ──
          Row(
            children: [
              _PeriodButton(
                label: 'Monthly',
                isSelected: _selected == ChartPeriod.monthly,
                onTap: () => setState(() => _selected = ChartPeriod.monthly),
              ),
              const SizedBox(width: 16),
              _PeriodButton(
                label: 'Weekly',
                isSelected: _selected == ChartPeriod.weekly,
                onTap: () => setState(() => _selected = ChartPeriod.weekly),
              ),
              const SizedBox(width: 16),
              _PeriodButton(
                label: 'Daily',
                isSelected: _selected == ChartPeriod.daily,
                onTap: () => setState(() => _selected = ChartPeriod.daily),
              ),
            ],
          ),

          const SizedBox(height: 12),

          // ── CHART AREA (navy blue background) ──
          Container(
            height: 220,
            decoration: BoxDecoration(
              color: const Color(0xFF0A1B6F), // navy blue background
              borderRadius: BorderRadius.circular(16),
            ),
            padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [

                // ── Y-axis unit label ──
                const Padding(
                  padding: EdgeInsets.only(left: 8, bottom: 4),
                  child: Text(
                    '(m³)',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                    ),
                  ),
                ),

                // ── LINE CHART ──
                Expanded(
                  child: LineChart(
                    LineChartData(
                      // Grid lines
                      gridData: FlGridData(
                        show: true,
                        drawVerticalLine: true,
                        getDrawingHorizontalLine: (value) => FlLine(
                          color: Colors.white.withValues(alpha: 0.15),
                          strokeWidth: 1,
                        ),
                        getDrawingVerticalLine: (value) => FlLine(
                          color: Colors.white.withValues(alpha: 0.15),
                          strokeWidth: 1,
                        ),
                      ),

                      // Border around chart
                      borderData: FlBorderData(show: false),

                      // X and Y axis titles
                      titlesData: FlTitlesData(
                        // LEFT axis (numbers 10, 20, 30)
                        leftTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 30,
                            interval: 10,
                            getTitlesWidget: (value, meta) {
                              if (value % 10 == 0) {
                                return Text(
                                  '${value.toInt()}',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 11,
                                  ),
                                );
                              }
                              return const SizedBox();
                            },
                          ),
                        ),

                        // BOTTOM axis (month/day labels)
                        bottomTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 28,
                            getTitlesWidget: (value, meta) {
                              int index = value.toInt();
                              if (index >= 0 && index < _currentLabels.length) {
                                return Padding(
                                  padding: const EdgeInsets.only(top: 4),
                                  child: Text(
                                    _currentLabels[index],
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                );
                              }
                              return const SizedBox();
                            },
                          ),
                        ),

                        // Hide right and top axis
                        rightTitles: const AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        topTitles: const AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                      ),

                      // The actual line
                      lineBarsData: [
                        LineChartBarData(
                          spots: _currentData,
                          isCurved: true,           // smooth curved line
                          color: Colors.white,      // white line
                          barWidth: 3,
                          isStrokeCapRound: true,
                          dotData: const FlDotData(show: false), // no dots
                          belowBarData: BarAreaData(show: false),
                        ),
                      ],

                      // Y axis range
                      minY: 0,
                      maxY: 35,
                    ),
                  ),
                ),

              ],
            ),
          ),

          const SizedBox(height: 10),

          // ── BOTTOM ROW: legend + period label ──
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [

              // Blue dot + "Water Usage" label
              Row(
                children: [
                  Container(
                    width: 12,
                    height: 12,
                    decoration: const BoxDecoration(
                      color: Color(0xFF0A1B6F),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'Water Usage',
                    style: TextStyle(
                      fontSize: 13,
                      color: Color(0xFF1A1A6E),
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),

              // Period label (Last 5 Months / Last 7 Days / Today)
              Text(
                _periodLabel,
                style: const TextStyle(
                  fontSize: 13,
                  color: Color(0xFF888888),
                ),
              ),

            ],
          ),

        ],
      ),
    );
  }
}


// ── PERIOD BUTTON (Monthly / Weekly / Daily) ─────────────────
class _PeriodButton extends StatelessWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _PeriodButton({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Row(
        children: [

          // Radio circle
          Container(
            width: 16,
            height: 16,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                color: const Color(0xFF1A1A6E),
                width: 2,
              ),
              color: isSelected
                  ? const Color(0xFF1A1A6E) // filled when selected
                  : Colors.white,           // empty when not selected
            ),
            // Inner white dot when selected
            child: isSelected
                ? const Center(
                    child: Icon(
                      Icons.circle,
                      size: 6,
                      color: Colors.white,
                    ),
                  )
                : null,
          ),

          const SizedBox(width: 6),

          // Label text
          Text(
            label,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: isSelected
                  ? const Color(0xFF1A1A6E)
                  : const Color(0xFF888888),
            ),
          ),

        ],
      ),
    );
  }
}