class UsageSummary {
  final double monthlyTotal;
  final double weeklyAvg;
  final double dailyAvg;
  final int leakCount;

  UsageSummary({
    required this.monthlyTotal,
    required this.weeklyAvg,
    required this.dailyAvg,
    required this.leakCount,
  });

  factory UsageSummary.fromJson(Map<String, dynamic> json) {
    return UsageSummary(
      monthlyTotal: (json['monthly_total'] as num).toDouble(),
      weeklyAvg: (json['weekly_avg'] as num).toDouble(),
      dailyAvg: (json['daily_avg'] as num).toDouble(),
      leakCount: json['leak_count'] as int,
    );
  }
}
