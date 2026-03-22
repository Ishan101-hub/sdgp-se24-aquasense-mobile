// lib/screens/usage_screen.dart
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:open_filex/open_filex.dart';

import '../models/usage_summary.dart';
import '../services/api_service.dart';

class UsageScreen extends StatefulWidget {
  const UsageScreen({super.key});

  @override
  State<UsageScreen> createState() => _UsageScreenState();
}

class _UsageScreenState extends State<UsageScreen> {
  // ── Date selection ───────────────────────────────────────────────
  late int selectedYear;
  late int selectedMonth;

  final List<String> years = ["2024", "2025", "2026", "2027"];
  final List<String> months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];

  // ── Data state ───────────────────────────────────────────────────
  UsageSummary? _summary;
  int _alertCount = 0;
  bool _isLoading = false;
  bool _isPdfLoading = false;
  String? _error;

  final _api = ApiService();

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    selectedYear = now.year;
    selectedMonth = now.month;
    _loadAll();
  }

  // ── Fetch both summary and alert count in parallel ───────────────
  Future<void> _loadAll() async {
    if (!mounted) return;
    setState(() {
      _isLoading = true;
      _error = null;
    });

    UsageSummary? summary;
    int alertCount = 0;
    String? error;

    try {
      final results = await Future.wait([
        _api.fetchUsageSummary(year: selectedYear, month: selectedMonth),
        _api.fetchUnresolvedAlertCount(),
      ]);
      summary = results[0] as UsageSummary;
      alertCount = results[1] as int;
    } catch (e) {
      error = e.toString();
    }

    if (!mounted) return;
    setState(() {
      _summary = summary ?? _summary;
      _alertCount = alertCount;
      _error = error;
      _isLoading = false;
    });
  }

  // ── Dropdown callbacks ───────────────────────────────────────────
  void _onYearChanged(String val) {
    setState(() => selectedYear = int.parse(val));
    _loadAll();
  }

  void _onMonthChanged(String val) {
    setState(() => selectedMonth = months.indexOf(val) + 1);
    _loadAll();
  }

  // ── PDF generation ───────────────────────────────────────────────
  Future<void> _generateReport() async {
    if (!mounted) return;
    setState(() => _isPdfLoading = true);

    String? errorMsg;

    try {
      final File pdf = await _api.downloadMonthlyReport(
        year: selectedYear,
        month: selectedMonth,
      );
      if (!mounted) return;
      await OpenFilex.open(pdf.path);
    } catch (e) {
      errorMsg = e.toString();
    }

    if (!mounted) return;
    setState(() => _isPdfLoading = false);

    if (errorMsg != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Could not generate report: $errorMsg'),
          backgroundColor: Colors.redAccent,
        ),
      );
    }
  }

  // ── Number formatter ─────────────────────────────────────────────
  String _fmt(double val) {
    return val
        .toStringAsFixed(0)
        .replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (m) => ',');
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final scale = MediaQuery.of(context).size.width / 393;

    const Color aquaAccent = Color.fromARGB(255, 4, 119, 91);
    final Color mainTextColor = isDark ? Colors.white : const Color(0xFF0A1B6F);

    final monthly = _summary != null
        ? _fmt(
            _summary!.isProjected
                ? _summary!.projectedMonthlyTotal
                : _summary!.monthlyTotal,
          )
        : '--';
    final weekly = _summary != null ? _fmt(_summary!.weeklyAvg) : '--';
    final daily = _summary != null ? _fmt(_summary!.dailyAvg) : '--';
    final leaks = _summary != null ? '${_summary!.leakCount}' : '--';

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      body: Stack(
        children: [
          RefreshIndicator(
            color: aquaAccent,
            onRefresh: _loadAll,
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(
                parent: BouncingScrollPhysics(),
              ),
              padding: EdgeInsets.all(20 * scale),
              child: Column(
                children: [
                  Center(
                    child: _buildInlineDateSelector(
                      aquaAccent,
                      scale,
                      theme,
                      isDark,
                    ),
                  ),
                  SizedBox(height: 25 * scale),

                  if (_isLoading)
                    Padding(
                      padding: EdgeInsets.symmetric(vertical: 60 * scale),
                      child: const CircularProgressIndicator(
                        color: Color.fromARGB(255, 4, 119, 91),
                      ),
                    )
                  else if (_error != null)
                    _buildErrorState(scale, isDark)
                  else ...[
                    _buildMainUsageCard(
                      mainTextColor,
                      theme.cardColor,
                      scale,
                      monthly,
                      theme,
                      isDark,
                      isProjected: _summary?.isProjected ?? false,
                      daysWithData: _summary?.daysWithData ?? 0,
                      daysInMonth: _summary?.daysInMonth ?? 0,
                    ),
                    SizedBox(height: 15 * scale),
                    Row(
                      children: [
                        Expanded(
                          child: _buildStatCard(
                            "Weekly Avg",
                            weekly,
                            "L",
                            mainTextColor,
                            theme.cardColor,
                            scale,
                            theme,
                            isDark,
                          ),
                        ),
                        SizedBox(width: 15 * scale),
                        Expanded(
                          child: _buildStatCard(
                            "Daily Avg",
                            daily,
                            "L",
                            mainTextColor,
                            theme.cardColor,
                            scale,
                            theme,
                            isDark,
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 20 * scale),
                    _buildAlertCard(
                      theme.cardColor,
                      scale,
                      leaks,
                      theme,
                      isDark,
                    ),
                    SizedBox(height: 25 * scale),
                    _buildReportButton(aquaAccent, scale),
                    SizedBox(height: 80 * scale),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ── Error state ──────────────────────────────────────────────────
  Widget _buildErrorState(double scale, bool isDark) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(height: 60 * scale),
          const Icon(Icons.wifi_off, size: 60, color: Colors.grey),
          const SizedBox(height: 16),
          const Text(
            'Failed to load data.\nCheck your connection.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey, fontSize: 14),
          ),
          const SizedBox(height: 20),
          ElevatedButton.icon(
            onPressed: () {
              setState(() {
                _isLoading = true;
                _error = null;
              });
              _loadAll();
            },
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF1A1A6E),
              foregroundColor: Colors.white,
            ),
          ),
          SizedBox(height: 60 * scale),
        ],
      ),
    );
  }

  // ── Date selector ────────────────────────────────────────────────
  Widget _buildInlineDateSelector(
    Color color,
    double scale,
    ThemeData theme,
    bool isDark,
  ) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: 12 * scale,
        vertical: 4 * scale,
      ),
      decoration: BoxDecoration(
        color: color.withOpacity(isDark ? 0.15 : 0.1),
        borderRadius: BorderRadius.circular(30 * scale),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildPopupMenu(
            years,
            selectedYear.toString(),
            _onYearChanged,
            theme,
            isDark,
          ),
          Container(
            width: 1,
            height: 18,
            color: isDark ? Colors.white24 : Colors.black12,
            margin: const EdgeInsets.symmetric(horizontal: 8),
          ),
          _buildPopupMenu(
            months,
            months[selectedMonth - 1],
            _onMonthChanged,
            theme,
            isDark,
          ),
        ],
      ),
    );
  }

  Widget _buildPopupMenu(
    List<String> items,
    String currentVal,
    Function(String) onSelect,
    ThemeData theme,
    bool isDark,
  ) {
    return PopupMenuButton<String>(
      offset: const Offset(0, 40),
      color: isDark ? const Color(0xFF1A1A1A) : Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      onSelected: onSelect,
      child: Row(
        children: [
          Text(
            currentVal,
            style: TextStyle(
              color: isDark ? Colors.white : Colors.black87,
              fontSize: 16,
            ),
          ),
          Icon(
            Icons.keyboard_arrow_down,
            color: isDark ? Colors.white : Colors.black54,
            size: 20,
          ),
        ],
      ),
      itemBuilder: (context) => items.map((item) {
        return PopupMenuItem<String>(
          value: item,
          child: Text(
            item,
            style: TextStyle(
              color: item == currentVal
                  ? const Color.fromARGB(255, 4, 119, 91)
                  : (isDark ? Colors.white : Colors.black87),
              fontWeight: item == currentVal
                  ? FontWeight.bold
                  : FontWeight.normal,
            ),
          ),
        );
      }).toList(),
    );
  }

  // ── Cards ────────────────────────────────────────────────────────
  Widget _buildMainUsageCard(
    Color textColor,
    Color cardBg,
    double scale,
    String value,
    ThemeData theme,
    bool isDark, {
    bool isProjected = false,
    int daysWithData = 0,
    int daysInMonth = 0,
  }) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.symmetric(
        vertical: 30 * scale,
        horizontal: 20 * scale,
      ),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(25 * scale),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.4 : 0.05),
            blurRadius: 10,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Column(
        children: [
          Text(
            isProjected ? "Projected Monthly Usage" : "Monthly Water Usage",
            style: theme.textTheme.bodyMedium?.copyWith(
              color: isDark ? Colors.white70 : Colors.grey[600],
              fontSize: 16 * scale,
            ),
          ),
          SizedBox(height: 10 * scale),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                value,
                style: TextStyle(
                  fontSize: 48 * scale,
                  fontWeight: FontWeight.bold,
                  color: textColor,
                ),
              ),
              SizedBox(width: 8 * scale),
              Text(
                "Litres",
                style: TextStyle(
                  fontSize: 18,
                  color: isDark ? Colors.white54 : Colors.grey,
                ),
              ),
            ],
          ),
          if (isProjected && daysWithData > 0) ...[
            SizedBox(height: 10 * scale),
            Container(
              padding: EdgeInsets.symmetric(
                horizontal: 12 * scale,
                vertical: 5 * scale,
              ),
              decoration: BoxDecoration(
                color: const Color.fromARGB(255, 4, 119, 91).withOpacity(0.1),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: const Color.fromARGB(255, 4, 119, 91).withOpacity(0.3),
                ),
              ),
              child: Text(
                "Based on $daysWithData of $daysInMonth days",
                style: TextStyle(
                  fontSize: 12 * scale,
                  color: const Color.fromARGB(255, 4, 119, 91),
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStatCard(
    String title,
    String value,
    String unit,
    Color textColor,
    Color cardBg,
    double scale,
    ThemeData theme,
    bool isDark,
  ) {
    return Container(
      padding: EdgeInsets.all(18 * scale),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(20 * scale),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 5),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              color: isDark ? Colors.white70 : Colors.grey[600],
              fontSize: 13 * scale,
            ),
          ),
          SizedBox(height: 8 * scale),
          Row(
            children: [
              Flexible(
                child: Text(
                  value,
                  style: TextStyle(
                    fontSize: 24 * scale,
                    fontWeight: FontWeight.bold,
                    color: textColor,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              SizedBox(width: 4 * scale),
              Text(
                unit,
                style: TextStyle(
                  fontSize: 14,
                  color: isDark ? Colors.white54 : Colors.grey,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAlertCard(
    Color cardBg,
    double scale,
    String count,
    ThemeData theme,
    bool isDark,
  ) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(22 * scale),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(20 * scale),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.warning_amber_rounded,
                color: Colors.redAccent,
                size: 26,
              ),
              SizedBox(width: 8 * scale),
              Text(
                "Leaks Detected",
                style: TextStyle(
                  fontSize: 17 * scale,
                  color: isDark ? Colors.white : Colors.black87,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          SizedBox(height: 12 * scale),
          Text(
            count,
            style: TextStyle(
              fontSize: 50 * scale,
              color: Colors.redAccent,
              fontWeight: FontWeight.bold,
            ),
          ),
          Text(
            "Alerts",
            style: TextStyle(color: isDark ? Colors.white54 : Colors.grey),
          ),
        ],
      ),
    );
  }

  // ── Report button ────────────────────────────────────────────────
  Widget _buildReportButton(Color color, double scale) {
    return Container(
      width: double.infinity,
      height: 60 * scale,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(15 * scale),
        gradient: LinearGradient(colors: [color, color.withOpacity(0.8)]),
      ),
      child: ElevatedButton.icon(
        onPressed: (_isLoading || _isPdfLoading) ? null : _generateReport,
        icon: _isPdfLoading
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  color: Colors.white,
                  strokeWidth: 2,
                ),
              )
            : const Icon(Icons.picture_as_pdf, size: 22),
        label: Text(
          _isPdfLoading ? "GENERATING..." : "GENERATE MONTHLY REPORT",
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            letterSpacing: 0.5,
          ),
        ),
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.transparent,
          shadowColor: Colors.transparent,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(15 * scale),
          ),
        ),
      ),
    );
  }
}
