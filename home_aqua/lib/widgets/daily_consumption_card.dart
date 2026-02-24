import 'package:flutter/material.dart';

class DailyConsumptionCard extends StatelessWidget {
  const DailyConsumptionCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
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

          // ── TITLE ──
          const Text(
            'Daily Consumption',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Color(0xFF1A1A6E),
            ),
          ),

          const SizedBox(height: 16),

          // ── PLACEHOLDER for sub-line bars (Parts 3.2, 3.3, 3.4) ──
          const Text(
            '(Sub-line bars coming soon)',
            style: TextStyle(color: Colors.grey),
          ),

        ],
      ),
    );
  }
}