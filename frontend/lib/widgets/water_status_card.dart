import 'package:flutter/material.dart';

class WaterStatusCard extends StatelessWidget {
  final double flowRate;

  const WaterStatusCard({
    super.key,
    this.flowRate = 23.1,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

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
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [

          Align(
            alignment: Alignment.center,
            child: Text(
              'Water Status',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: isDark ? Colors.white : const Color(0xFF1A1A6E),
              ),
            ),
          ),

          const SizedBox(height: 16),

          Container(
            width: 110,
            height: 110,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                color: const Color(0xFF1A1A6E),
                width: 4,
              ),
              color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [

                Text(
                  flowRate.toStringAsFixed(1),
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: isDark ? Colors.white : const Color(0xFF1A1A6E),
                    height: 1.0,
                  ),
                ),

                const SizedBox(height: 2),

                Text(
                  'L/min',
                  style: TextStyle(
                    fontSize: 12,
                    color: isDark
                        ? const Color(0xFF9BA8FF)
                        : const Color(0xFF6978EC),
                    fontWeight: FontWeight.w400,
                  ),
                ),

              ],
            ),
          ),

          const SizedBox(height: 16),

          Text(
            'Water running speed',
            style: TextStyle(
              fontSize: 13,
              color: isDark
                  ? const Color(0xFF9BA8FF)
                  : const Color(0xFF6978EC),
            ),
          ),

        ],
      ),
    );
  }
}