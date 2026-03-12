import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

enum ChartPeriod { monthly, weekly, daily }

class UsageChartCard extends StatefulWidget {

  // ── todayUsage: sum of all zones from home_page ──
  // Daily chart last point ("Now") = this value
  final double todayUsage;

  const UsageChartCard({
    super.key,
    this.todayUsage = 0,
  });

  @override
  State<UsageChartCard> createState() => _UsageChartCardState();
}

class _UsageChartCardState extends State<UsageChartCard> {

  ChartPeriod _selected = ChartPeriod.monthly;

  final List<FlSpot> _monthlyData = const [
    FlSpot(0, 20), FlSpot(1, 17), FlSpot(2, 7), FlSpot(3, 25), FlSpot(4, 10),
  ];

  // Week 1, Week 2, Week 3, Week 4
  final List<FlSpot> _weeklyData = const [
    FlSpot(0, 12), // Week 1
    FlSpot(1, 18), // Week 2
    FlSpot(2, 15), // Week 3
    FlSpot(3, 22), // Week 4
  ];

  // ── Daily: last point uses real todayUsage (litres → m³) ──
  List<FlSpot> get _dailyData => [
    const FlSpot(0, 8),
    const FlSpot(1, 15),
    const FlSpot(2, 11),
    const FlSpot(3, 19),
    const FlSpot(4, 14),
    const FlSpot(5, 22),
    FlSpot(6, widget.todayUsage / 1000), // ← real today usage ✅
  ];

  final List<String> _monthLabels = ['June', 'July', 'Aug', 'Sep', 'Oct'];
  final List<String> _weekLabels  = ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
  final List<String> _dayLabels   = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  List<FlSpot> get _currentData {
    switch (_selected) {
      case ChartPeriod.monthly: return _monthlyData;
      case ChartPeriod.weekly:  return _weeklyData;
      case ChartPeriod.daily:   return _dailyData;
    }
  }

  List<String> get _currentLabels {
    switch (_selected) {
      case ChartPeriod.monthly: return _monthLabels;
      case ChartPeriod.weekly:  return _weekLabels;
      case ChartPeriod.daily:   return _dayLabels;
    }
  }

  String get _periodLabel {
    switch (_selected) {
      case ChartPeriod.monthly: return 'Last 5 Months';
      case ChartPeriod.weekly:  return 'Last 4 Weeks';
      case ChartPeriod.daily:   return 'This Week';
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

          Container(
            height: 220,
            decoration: BoxDecoration(
              color: const Color(0xFF0A1B6F),
              borderRadius: BorderRadius.circular(16),
            ),
            padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Padding(
                  padding: EdgeInsets.only(left: 8, bottom: 4),
                  child: Text(
                    '(m³)',
                    style: TextStyle(color: Colors.white, fontSize: 12),
                  ),
                ),
                Expanded(
                  child: LineChart(
                    LineChartData(
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
                      borderData: FlBorderData(show: false),
                      titlesData: FlTitlesData(
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
                                    color: Colors.white, fontSize: 11,
                                  ),
                                );
                              }
                              return const SizedBox();
                            },
                          ),
                        ),
                        bottomTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 28,
                            interval: 1, // ← exactly one label per data point, no duplicates!
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
                        rightTitles: const AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        topTitles: const AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                      ),
                      lineBarsData: [
                        LineChartBarData(
                          spots: _currentData,
                          isCurved: true,
                          color: Colors.white,
                          barWidth: 3,
                          isStrokeCapRound: true,
                          dotData: const FlDotData(show: false),
                          belowBarData: BarAreaData(show: false),
                        ),
                      ],
                      minY: 0,
                      maxY: 35,
                    ),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 10),

          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
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
              Text(
                _periodLabel,
                style: const TextStyle(fontSize: 13, color: Color(0xFF888888)),
              ),
            ],
          ),

        ],
      ),
    );
  }
}

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
          Container(
            width: 16,
            height: 16,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: const Color(0xFF1A1A6E), width: 2),
              color: isSelected ? const Color(0xFF1A1A6E) : Colors.white,
            ),
            child: isSelected
                ? const Center(
                    child: Icon(Icons.circle, size: 6, color: Colors.white),
                  )
                : null,
          ),
          const SizedBox(width: 6),
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