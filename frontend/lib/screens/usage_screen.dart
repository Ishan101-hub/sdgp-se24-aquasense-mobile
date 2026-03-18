import 'package:flutter/material.dart';

class UsageScreen extends StatefulWidget {
  const UsageScreen({super.key});

  @override
  State<UsageScreen> createState() => _UsageScreenState();
}

class _UsageScreenState extends State<UsageScreen> {
  String selectedYear = "2026";
  String selectedMonth = "January";

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

  @override
  Widget build(BuildContext context) {
    // 1. Get Theme Data for adaptive styling
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final double screenWidth = MediaQuery.of(context).size.width;
    final double scale = screenWidth / 393;

    // 2. Define Adaptive Palette
    const Color aquaAccent = Color.fromARGB(255, 4, 119, 91);
    // Use pure white for dark mode and your brand blue for light mode
    final Color mainTextColor = isDark ? Colors.white : const Color(0xFF0A1B6F);

    return Scaffold(
      // Uses the background color defined in your main theme (no hardcoded Ash)
      backgroundColor: theme.scaffoldBackgroundColor,
      body: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(
          parent: BouncingScrollPhysics(),
        ),
        padding: EdgeInsets.all(20 * scale),
        child: Column(
          children: [
            // Functional Inline Dropdown
            _buildInlineDateSelector(aquaAccent, scale, theme, isDark),

            SizedBox(height: 25 * scale),

            _buildMainUsageCard(
              mainTextColor,
              theme.cardColor,
              scale,
              "15,250",
              theme,
              isDark,
            ),

            SizedBox(height: 15 * scale),

            Row(
              children: [
                Expanded(
                  child: _buildStatCard(
                    "Weekly Avg",
                    "3,812",
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
                    "508",
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

            _buildAlertCard(theme.cardColor, scale, "3", theme, isDark),

            SizedBox(height: 25 * scale),

            _buildReportButton(aquaAccent, scale),
          ],
        ),
      ),
    );
  }

  // --- ADAPTIVE UI HELPER METHODS ---

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
            selectedYear,
            (val) => setState(() => selectedYear = val),
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
            selectedMonth,
            (val) => setState(() => selectedMonth = val),
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
      itemBuilder: (context) => items.map((String item) {
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

  Widget _buildMainUsageCard(
    Color textColor,
    Color cardBg,
    double scale,
    String value,
    ThemeData theme,
    bool isDark,
  ) {
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
            "Monthly Water Usage",
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

  Widget _buildReportButton(Color color, double scale) {
    return Container(
      width: double.infinity,
      height: 60 * scale,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(15 * scale),
        gradient: LinearGradient(colors: [color, color.withOpacity(0.8)]),
      ),
      child: ElevatedButton.icon(
        onPressed: () {},
        icon: const Icon(Icons.picture_as_pdf, size: 22),
        label: const Text(
          "GENERATE MONTHLY REPORT",
          style: TextStyle(
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
