// lib/models/usage_summary.dart
// AquaSense — Usage summary model
// Maps to the JSON returned by GET /usage/summary

class UsageSummary {
  final double monthlyTotal;
  final double projectedMonthlyTotal;
  final bool isProjected;
  final double weeklyAvg;
  final double dailyAvg;
  final int leakCount;
  final int year;
  final int month;
  final int daysInMonth;
  final int daysWithData;

  const UsageSummary({
    required this.monthlyTotal,
    required this.projectedMonthlyTotal,
    required this.isProjected,
    required this.weeklyAvg,
    required this.dailyAvg,
    required this.leakCount,
    required this.year,
    required this.month,
    required this.daysInMonth,
    required this.daysWithData,
  });

  factory UsageSummary.fromJson(Map<String, dynamic> json) {
    return UsageSummary(
      monthlyTotal: (json['monthly_total'] as num).toDouble(),
      projectedMonthlyTotal: (json['projected_monthly_total'] as num)
          .toDouble(),
      isProjected: (json['is_projected'] as bool? ?? false),
      weeklyAvg: (json['weekly_avg'] as num).toDouble(),
      dailyAvg: (json['daily_avg'] as num).toDouble(),
      leakCount: (json['leak_count'] as num).toInt(),
      year: (json['year'] as num).toInt(),
      month: (json['month'] as num).toInt(),
      daysInMonth: (json['days_in_month'] as num? ?? 0).toInt(),
      daysWithData: (json['days_with_data'] as num? ?? 0).toInt(),
    );
  }

  // Empty summary — shown when no data exists for the selected month.
  factory UsageSummary.empty(int year, int month) {
    return UsageSummary(
      monthlyTotal: 0,
      projectedMonthlyTotal: 0,
      isProjected: false,
      weeklyAvg: 0,
      dailyAvg: 0,
      leakCount: 0,
      year: year,
      month: month,
      daysInMonth: 0,
      daysWithData: 0,
    );
  }
}
