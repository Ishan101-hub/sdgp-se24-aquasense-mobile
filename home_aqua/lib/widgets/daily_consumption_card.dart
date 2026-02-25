import 'package:flutter/material.dart';
import 'dart:math' as math;

// ── Zone model ──────────────────────────────────────────────
class WaterZone {
  final String name;
  final double used;
  final double average;

  const WaterZone({
    required this.name,
    required this.used,
    required this.average,
  });
}

class DailyConsumptionCard extends StatelessWidget {
  final List<WaterZone> zones;

  const DailyConsumptionCard({
    super.key,
    required this.zones,
  });

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
        crossAxisAlignment: CrossAxisAlignment.center,
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

          const SizedBox(height: 20),

          // ── EMPTY STATE ──
          if (zones.isEmpty)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                'No zones found.\nCheck your device connections.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Color(0xFF888888),
                  fontSize: 13,
                ),
              ),
            ),

          // ── DYNAMIC ZONES: rows of 3 ──
          ...List.generate(
            (zones.length / 3).ceil(),
            (rowIndex) {
              final rowZones = zones.sublist(
                rowIndex * 3,
                math.min(rowIndex * 3 + 3, zones.length),
              );
              return Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: rowZones.map((zone) {
                    return _ZoneCircle(zone: zone);
                  }).toList(),
                ),
              );
            },
          ),

        ],
      ),
    );
  }
}


// ── ZONE CIRCLE ──────────────────────────────────────────────
class _ZoneCircle extends StatelessWidget {
  final WaterZone zone;

  const _ZoneCircle({required this.zone});

  @override
  Widget build(BuildContext context) {
    final bool isOverLimit = zone.used >= zone.average;
    final double progress  = isOverLimit
        ? 1.0
        : (zone.used / zone.average).clamp(0.0, 1.0);
    final Color arcColor   = isOverLimit ? const Color(0xFFD80B0B) : const Color(0xFF1A1A6E);
    final Color textColor  = isOverLimit ? const Color(0xFFD80B0B) : const Color(0xFF1A1A6E);

    return Column(
      children: [

        // ── CIRCULAR ARC ──
        SizedBox(
          width: 95,
          height: 95,
          child: Stack(
            alignment: Alignment.center,
            children: [

              // Grey background arc
              CustomPaint(
                size: const Size(95, 95),
                painter: _ArcPainter(
                  progress: 1.0,
                  color: const Color(0xFFE0E0E0),
                  strokeWidth: 8,
                ),
              ),

              // Colored progress arc
              CustomPaint(
                size: const Size(95, 95),
                painter: _ArcPainter(
                  progress: progress,
                  color: arcColor,
                  strokeWidth: 8,
                ),
              ),

              // ── FIXED: 1 decimal point inside circle ──
              Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    // ← toStringAsFixed(1) gives 1 decimal e.g. 80.0
                    zone.used.toStringAsFixed(1),
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: textColor,
                      height: 1.0,
                    ),
                  ),
                  Text(
                    'Liters',
                    style: TextStyle(
                      fontSize: 10,
                      color: textColor,
                      fontWeight: FontWeight.w400,
                    ),
                  ),
                ],
              ),

            ],
          ),
        ),

        const SizedBox(height: 8),

        // Zone name
        Text(
          zone.name,
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.bold,
            color: Color(0xFF1A1A6E),
          ),
        ),

        // Warning if over limit
        if (isOverLimit)
          const Text(
            'Over limit!',
            style: TextStyle(
              fontSize: 10,
              color: const Color(0xFFD80B0B),
              fontWeight: FontWeight.w500,
            ),
          ),

      ],
    );
  }
}


// ── ARC PAINTER ──────────────────────────────────────────────
class _ArcPainter extends CustomPainter {
  final double progress;
  final Color color;
  final double strokeWidth;

  _ArcPainter({
    required this.progress,
    required this.color,
    required this.strokeWidth,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final double centerX = size.width / 2;
    final double centerY = size.height / 2;
    final double radius  = (size.width - strokeWidth) / 2;

    const double startAngle = 140 * math.pi / 180;
    final double sweepAngle = 260 * math.pi / 180 * progress;

    canvas.drawArc(
      Rect.fromCircle(center: Offset(centerX, centerY), radius: radius),
      startAngle,
      sweepAngle,
      false,
      paint,
    );
  }

  @override
  bool shouldRepaint(_ArcPainter oldDelegate) {
    return oldDelegate.progress != progress ||
           oldDelegate.color != color;
  }
}