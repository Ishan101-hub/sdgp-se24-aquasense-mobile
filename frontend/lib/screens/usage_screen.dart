import 'package:flutter/material.dart';

class UsageScreen extends StatefulWidget {
  const UsageScreen({super.key});

  @override
  State<UsageScreen> createState() => _UsageScreenState();
}

class _UsageScreenState extends State<UsageScreen> {
  String selectedYear = '2026';
  String selectedMonth = 'January';

  final List<String> years = ['2024', '2025', '2026'];
  final List<String> months = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];

  final Color brandBlue = const Color(0xFF0A1B6F);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFF),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 25),
              child: ConstrainedBox(
                // Forces content to stretch to full screen height
                constraints: BoxConstraints(
                  minHeight: constraints.maxHeight - 50,
                ),
                child: IntrinsicHeight(
                  child: Column(
                    children: [
                      // --- Improved Header Section ---
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              Icon(
                                Icons.water_drop,
                                color: brandBlue,
                                size: 32,
                              ),
                              const SizedBox(width: 10),
                              Text(
                                "Aqua Sense",
                                style: TextStyle(
                                  color: brandBlue,
                                  fontSize: 24,
                                  fontWeight: FontWeight.bold,
                                  fontStyle: FontStyle.italic,
                                  letterSpacing: 0.5,
                                ),
                              ),
                            ],
                          ),
                          _buildLocationBadge(),
                        ],
                      ),
                      const SizedBox(height: 25),

                      // --- Styled Dropdowns Section ---
                      _buildDateSelector(),
                      const SizedBox(height: 35),

                      // --- Main Usage Card (Increased Height) ---
                      _buildDataCard(
                        "Monthly Water Usage",
                        "15,250",
                        "Litres",
                        true,
                      ),

                      // Using Spacers to fill the screen vertically
                      const Spacer(flex: 1),

                      // --- Secondary Analytics Cards ---
                      Row(
                        children: [
                          Expanded(
                            child: _buildDataCard(
                              "Weekly Avg",
                              "3,812",
                              "L",
                              false,
                            ),
                          ),
                          const SizedBox(width: 15),
                          Expanded(
                            child: _buildDataCard(
                              "Daily Avg",
                              "508",
                              "L",
                              false,
                            ),
                          ),
                        ],
                      ),

                      const Spacer(flex: 1),

                      // --- Status Card ---
                      _buildDataCard(
                        "Leaks Detected",
                        "3",
                        "Alerts",
                        true,
                        valueColor: Colors.redAccent,
                        icon: Icons.warning_amber_rounded,
                      ),

                      const Spacer(flex: 2),

                      // --- Enhanced Generate Report Button ---
                      SizedBox(
                        width: double.infinity,
                        height: 60,
                        child: ElevatedButton.icon(
                          onPressed: () {},
                          icon: const Icon(Icons.picture_as_pdf, size: 22),
                          label: const Text(
                            "GENERATE MONTHLY REPORT",
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 1,
                            ),
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: brandBlue,
                            foregroundColor: Colors.white,
                            elevation: 4,
                            shadowColor: brandBlue.withOpacity(0.4),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(15),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildLocationBadge() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(25),
        boxShadow: [
          BoxShadow(
            color: brandBlue.withOpacity(0.08),
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          Icon(Icons.location_on_outlined, size: 18, color: brandBlue),
          const SizedBox(width: 6),
          const Text(
            "Ragama",
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
          ),
          const Icon(Icons.keyboard_arrow_down, size: 18),
        ],
      ),
    );
  }

  Widget _buildDateSelector() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 5),
      decoration: BoxDecoration(
        color: brandBlue,
        borderRadius: BorderRadius.circular(15),
        boxShadow: [
          BoxShadow(
            color: brandBlue.withOpacity(0.3),
            blurRadius: 12,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildDropdown(
            years,
            selectedYear,
            (val) => setState(() => selectedYear = val!),
          ),
          Container(
            width: 1.5,
            height: 25,
            color: Colors.white24,
            margin: const EdgeInsets.symmetric(horizontal: 15),
          ),
          _buildDropdown(
            months,
            selectedMonth,
            (val) => setState(() => selectedMonth = val!),
          ),
        ],
      ),
    );
  }

  Widget _buildDropdown(
    List<String> items,
    String currentVal,
    ValueChanged<String?> onChanged,
  ) {
    return DropdownButtonHideUnderline(
      child: DropdownButton<String>(
        value: currentVal,
        dropdownColor: brandBlue,
        icon: const Icon(Icons.expand_more, color: Colors.white, size: 22),
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.bold,
          fontSize: 17,
        ),
        onChanged: onChanged,
        items: items
            .map((String val) => DropdownMenuItem(value: val, child: Text(val)))
            .toList(),
      ),
    );
  }

  Widget _buildDataCard(
    String title,
    String value,
    String unit,
    bool isFullWidth, {
    Color valueColor = const Color(0xFF0A1B6F),
    IconData? icon,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: 20,
        vertical: 25,
      ), // Increased vertical padding
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: brandBlue.withOpacity(0.05)),
        boxShadow: [
          BoxShadow(
            color: brandBlue.withOpacity(0.06),
            blurRadius: 15,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (icon != null) Icon(icon, color: valueColor, size: 20),
              if (icon != null) const SizedBox(width: 8),
              Text(
                title,
                style: TextStyle(
                  color: brandBlue.withOpacity(0.6),
                  fontWeight: FontWeight.bold,
                  fontSize: 15,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                value,
                style: TextStyle(
                  color: valueColor,
                  fontWeight: FontWeight.bold,
                  fontSize: 34,
                ),
              ),
              const SizedBox(width: 6),
              Text(
                unit,
                style: TextStyle(
                  color: brandBlue.withOpacity(0.4),
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
