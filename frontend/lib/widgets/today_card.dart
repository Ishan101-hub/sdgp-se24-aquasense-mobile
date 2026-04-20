// import 'package:flutter/material.dart';
// import 'dart:math' as math;

// class TodayCard extends StatelessWidget {
//   final double litresUsed;
//   final double dailyAverageLitres;
//   final double dailyAveragePercent;

//   const TodayCard({
//     super.key,
//     this.litresUsed = 220,
//     this.dailyAverageLitres = 450,
//     this.dailyAveragePercent = 48,
//   });

//   @override
//   Widget build(BuildContext context) {
//     final isDark   = Theme.of(context).brightness == Brightness.dark;
//     double progress = (litresUsed / dailyAverageLitres).clamp(0.0, 1.0);

//     return Container(
//       decoration: BoxDecoration(
//         color: isDark ? const Color(0xFF1E1E1E) : Colors.white, // ← dark card
//         borderRadius: BorderRadius.circular(20),
//         boxShadow: [
//           BoxShadow(
//             color: Colors.blue.withValues(alpha: 0.08),
//             blurRadius: 12,
//             offset: const Offset(0, 4),
//           ),
//         ],
//       ),
//       padding: const EdgeInsets.all(16),
//       child: Column(
//         crossAxisAlignment: CrossAxisAlignment.center,
//         children: [

//           Align(
//             alignment: Alignment.center,
//             child: Text(
//               'Today',
//               style: TextStyle(
//                 fontSize: 18,
//                 fontWeight: FontWeight.bold,
//                 color: isDark ? Colors.white : const Color(0xFF1A1A6E),
//               ),
//             ),
//           ),

//           const SizedBox(height: 16),

//           SizedBox(
//             width: 130,
//             height: 130,
//             child: Stack(
//               alignment: Alignment.center,
//               children: [

//                 SizedBox(
//                   width: 130,
//                   height: 130,
//                   child: CustomPaint(
//                     painter: _CircularBarPainter(
//                       progress: 1.0,
//                       color: isDark
//                           ? const Color(0xFF333333)
//                           : const Color(0xFFE0E0E0),
//                       strokeWidth: 10,
//                     ),
//                   ),
//                 ),

//                 SizedBox(
//                   width: 130,
//                   height: 130,
//                   child: CustomPaint(
//                     painter: _CircularBarPainter(
//                       progress: progress,
//                       color: const Color(0xFF1A1A6E),
//                       strokeWidth: 10,
//                     ),
//                   ),
//                 ),

//                 RichText(
//                   textAlign: TextAlign.center,
//                   text: TextSpan(
//                     children: [
//                       TextSpan(
//                         text: litresUsed.toStringAsFixed(1),
//                         style: TextStyle(
//                           fontSize: 30,
//                           fontWeight: FontWeight.bold,
//                           color: isDark ? Colors.white : const Color(0xFF1A1A6E),
//                         ),
//                       ),
//                       TextSpan(
//                         text: '\nLitres',
//                         style: TextStyle(
//                           fontSize: 13,
//                           color: isDark
//                               ? const Color(0xFF9BA8FF)
//                               : const Color(0xFF6978EC),
//                           fontWeight: FontWeight.w400,
//                         ),
//                       ),
//                     ],
//                   ),
//                 ),

//               ],
//             ),
//           ),

//           const SizedBox(height: 16),

//           Text(
//             '${dailyAveragePercent.toStringAsFixed(1)}% of daily average',
//             style: TextStyle(
//               fontSize: 13,
//               color: isDark
//                   ? const Color(0xFF9BA8FF)
//                   : const Color(0xFF6978EC),
//             ),
//           ),

//         ],
//       ),
//     );
//   }
// }

// class _CircularBarPainter extends CustomPainter {
//   final double progress;
//   final Color  color;
//   final double strokeWidth;

//   _CircularBarPainter({
//     required this.progress,
//     required this.color,
//     required this.strokeWidth,
//   });

//   @override
//   void paint(Canvas canvas, Size size) {
//     final paint = Paint()
//       ..color       = color
//       ..strokeWidth = strokeWidth
//       ..style       = PaintingStyle.stroke
//       ..strokeCap   = StrokeCap.round;

//     final cx     = size.width / 2;
//     final cy     = size.height / 2;
//     final radius = (size.width - strokeWidth) / 2;

//     canvas.drawArc(
//       Rect.fromCircle(center: Offset(cx, cy), radius: radius),
//       140 * math.pi / 180,
//       260 * math.pi / 180 * progress,
//       false,
//       paint,
//     );
//   }

//   @override
//   bool shouldRepaint(_CircularBarPainter old) =>
//       old.progress != progress || old.color != color;
// }

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
    final isDark   = Theme.of(context).brightness == Brightness.dark;
    double progress = (litresUsed / dailyAverageLitres).clamp(0.0, 1.0);

    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
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
              'Today',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: isDark ? Colors.white : const Color(0xFF1A1A6E),
              ),
            ),
          ),

          const SizedBox(height: 16),

          SizedBox(
            width: 130,
            height: 130,
            child: Stack(
              alignment: Alignment.center,
              children: [

                SizedBox(
                  width: 130,
                  height: 130,
                  child: CustomPaint(
                    painter: _CircularBarPainter(
                      progress: 1.0,
                      color: isDark
                          ? const Color(0xFF333333)
                          : const Color(0xFFE0E0E0),
                      strokeWidth: 10,
                    ),
                  ),
                ),

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

                RichText(
                  textAlign: TextAlign.center,
                  text: TextSpan(
                    children: [
                      TextSpan(
                        text: litresUsed.toStringAsFixed(1),
                        style: TextStyle(
                          fontSize: 30,
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : const Color(0xFF1A1A6E),
                        ),
                      ),
                      TextSpan(
                        text: '\nLitres',
                        style: TextStyle(
                          fontSize: 13,
                          color: isDark
                              ? const Color(0xFF9BA8FF)
                              : const Color(0xFF6978EC),
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

          Text(
            '${dailyAveragePercent.toStringAsFixed(1)}% of daily average',
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

class _CircularBarPainter extends CustomPainter {
  final double progress;
  final Color  color;
  final double strokeWidth;

  _CircularBarPainter({
    required this.progress,
    required this.color,
    required this.strokeWidth,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color       = color
      ..strokeWidth = strokeWidth
      ..style       = PaintingStyle.stroke
      ..strokeCap   = StrokeCap.round;

    final cx     = size.width / 2;
    final cy     = size.height / 2;
    final radius = (size.width - strokeWidth) / 2;

    canvas.drawArc(
      Rect.fromCircle(center: Offset(cx, cy), radius: radius),
      140 * math.pi / 180,
      260 * math.pi / 180 * progress,
      false,
      paint,
    );
  }

  @override
  bool shouldRepaint(_CircularBarPainter old) =>
      old.progress != progress || old.color != color;
}