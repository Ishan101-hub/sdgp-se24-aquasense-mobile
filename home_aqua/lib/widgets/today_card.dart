import 'package:flutter/material.dart';

class TodayCard extends StatelessWidget {
  const TodayCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.blue.withOpacity(0.08),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [

          // ── TITLE ──
          const Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'Today',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFF1A1A6E),
              ),
            ),
          ),

          const SizedBox(height: 16),

          // ── PLACEHOLDER for circular bar + 220 Litres ──
          const Text(
            '(Circle + Litres here)',
            style: TextStyle(color: Colors.grey),
          ),

          const SizedBox(height: 16),

          // ── PLACEHOLDER for 48% text ──
          const Text(
            '(48% text here)',
            style: TextStyle(color: Colors.grey, fontSize: 13),
          ),

        ],
      ),
    );
  }
}