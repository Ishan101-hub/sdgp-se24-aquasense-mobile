import 'package:flutter/material.dart';
import 'dart:math' as math;

// ── SubLine model ──
// This represents one sub-line (zone) from your backend
// Example: SubLine(name: 'kitchen1', litres: 30)
class SubLine {
  final String name;   // name from backend e.g. kitchen1, outdoor2
  final double litres; // usage in litres

  const SubLine({
    required this.name,
    required this.litres,
  });
}

class DailyConsumptionCard extends StatelessWidget {

  // ── List of sub-lines (dynamic from backend later) ──
  // Right now using test data with 3 zones
  // When backend is ready, replace this list with real data
  final List<SubLine> subLines;
  final double maxLitres; // full circle = this value

  const DailyConsumptionCard({
    super.key,
    this.subLines = const [
      SubLine(name: 'Kitchen',  litres: 30),  // test value
      SubLine(name: 'Bathroom', litres: 140), // test value
      SubLine(name: 'Outdoor',  litres: 50),  // test value
    ],
    this.maxLitres = 150, // test value
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

          // ── DYNAMIC sub-line circles ──
          // This Row is built from the subLines list
          // So if backend sends 2 zones or 4 zones, it adjusts automatically!
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: subLines.map((subLine) {
              // For each SubLine in the list, create one _CircleBar
              return _CircleBar(
                litres: subLine.litres,
                maxLitres: maxLitres,
                label: subLine.name, // ← dynamic name from backend!
              );
            }).toList(),
          ),

          const SizedBox(height: 8),

        ],
      ),
    );
  }
}


// ── SINGLE CIRCLE BAR WIDGET ─────────────────────────────────
class _CircleBar extends StatelessWidget {
  final double litres;
  final double maxLitres;
  final String label;

  const _CircleBar({
    required this.litres,
    required this.maxLitres,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    double progress = (litres / maxLitres).clamp(0.0, 1.0);

    return Column(
      children: [

        // ── CIRCLE with number inside ──
        SizedBox(
          width: 90,
          height: 90,
          child: Stack(
            alignment: Alignment.center,
            children: [

              // Grey background arc
              SizedBox(
                width: 90,
                height: 90,
                child: CustomPaint(
                  painter: _ArcPainter(
                    progress: 1.0,
                    color: const Color(0xFFE0E0E0),
                    strokeWidth: 8,
                  ),
                ),
              ),

              // Navy blue progress arc
              SizedBox(
                width: 90,
                height: 90,
                child: CustomPaint(
                  painter: _ArcPainter(
                    progress: progress,
                    color: const Color(0xFF1A1A6E),
                    strokeWidth: 8,
                  ),
                ),
              ),

              // Number + Liters inside circle
              Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    '${litres.toInt()}',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF1A1A6E),
                      height: 1.0,
                    ),
                  ),
                  const Text(
                    'Liters',
                    style: TextStyle(
                      fontSize: 10,
                      color: Color(0xFF1A1A6E),
                      fontWeight: FontWeight.w400,
                    ),
                  ),
                ],
              ),

            ],
          ),
        ),

        const SizedBox(height: 8),

        // ── DYNAMIC LABEL below circle ──
        Text(
          label, // ← comes from SubLine.name (dynamic!)
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.bold,
            color: Color(0xFF1A1A6E),
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
    final double radius = (size.width - strokeWidth) / 2;

    const double startAngle = 140 * math.pi / 180;
    final double sweepAngle = 260 * math.pi / 180 * progress;

    canvas.drawArc(
      Rect.fromCircle(
        center: Offset(centerX, centerY),
        radius: radius,
      ),
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