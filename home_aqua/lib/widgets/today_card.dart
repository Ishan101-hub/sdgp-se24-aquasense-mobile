import 'package:flutter/material.dart';
import 'dart:math' as math;

class TodayCard extends StatelessWidget {
  final double litresUsed;
  final double dailyAverageLitres;
  final double dailyAveragePercent;

  const TodayCard({
    super.key,
    this.litresUsed = 220,
    this.dailyAverageLitres = 450,
    this.dailyAveragePercent = 48,
  });

  @override
  Widget build(BuildContext context) {
    double progress = (litresUsed / dailyAverageLitres).clamp(0.0, 1.0);

    return Container(
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
          const Align(
            alignment: Alignment.center,
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

          // ── Circular loading bar ──
          SizedBox(
            width: 130,
            height: 130,
            child: Stack(
              alignment: Alignment.center,
              children: [

                // Grey background circle
                SizedBox(
                  width: 130,
                  height: 130,
                  child: CustomPaint(
                    painter: _CircularBarPainter(
                      progress: 1.0,
                      color: const Color(0xFFE0E0E0),
                      strokeWidth: 10,
                    ),
                  ),
                ),

                // Navy blue progress circle
                SizedBox(
                  width: 130,
                  height: 130,
                  child: CustomPaint(
                    painter: _CircularBarPainter(
                      progress: progress,
                      color: const Color(0xFF1A1A6E),
                      strokeWidth: 10,
                    ),
                  ),
                ),

                // ── FIXED: 1 decimal point ──
                RichText(
                  textAlign: TextAlign.center,
                  text: TextSpan(
                    children: [
                      TextSpan(
                        // ← toStringAsFixed(1) gives 1 decimal e.g. 220.0
                        text: litresUsed.toStringAsFixed(1),
                        style: const TextStyle(
                          fontSize: 30,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF1A1A6E),
                        ),
                      ),
                      const TextSpan(
                        text: '\nLitres',
                        style: TextStyle(
                          fontSize: 13,
                          color: Color(0xFF6978EC),
                          fontWeight: FontWeight.w400,
                        ),
                      ),
                    ],
                  ),
                ),

              ],
            ),
          ),

          const SizedBox(height: 16),

          // ── percentage text ──
          Text(
            '${dailyAveragePercent.toStringAsFixed(1)}% of daily average',
            style: const TextStyle(
              fontSize: 13,
              color: Color(0xFF6978EC),
            ),
          ),

        ],
      ),
    );
  }
}

// ── CUSTOM PAINTER ──
class _CircularBarPainter extends CustomPainter {
  final double progress;
  final Color color;
  final double strokeWidth;

  _CircularBarPainter({
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
  bool shouldRepaint(_CircularBarPainter oldDelegate) {
    return oldDelegate.progress != progress ||
           oldDelegate.color != color;
  }
}