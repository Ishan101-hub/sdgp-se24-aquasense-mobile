import 'package:flutter/material.dart';
import 'dart:math' as math;

class PipelineZone {
  final String name;
  final double inFlow;
  final double outFlow;
  final bool isValveOpen;
  final bool isValveClosed;

  const PipelineZone({
    required this.name,
    required this.inFlow,
    required this.outFlow,
    required this.isValveOpen,
    this.isValveClosed = false,
  });

  bool get hasLeak => (inFlow - outFlow) >= 0.1;
}

class LeakageCard extends StatefulWidget {
  final PipelineZone zone;
  final Function(bool isOpen)? onValveToggle;

  const LeakageCard({
    super.key,
    required this.zone,
    this.onValveToggle,
  });

  @override
  State<LeakageCard> createState() => _LeakageCardState();
}

class _LeakageCardState extends State<LeakageCard> {
  late bool _isValveOpen;

  @override
  void initState() {
    super.initState();
    _isValveOpen = widget.zone.isValveOpen;
  }

  @override
  Widget build(BuildContext context) {
    final isDark   = Theme.of(context).brightness == Brightness.dark;
    final bool hasLeak = widget.zone.hasLeak && _isValveOpen;

    // ── Card border/bg color based on state ──
    // ── Arc/border color ──
    // Dark mode + normal → GREEN (as requested)
    // Light mode + normal → NAVY
    final Color borderColor = hasLeak
        ? const Color(0xFFD80B0B)           // RED — leak
        : !_isValveOpen
            ? const Color(0xFFE6A817)       // YELLOW — valve closed
            : isDark
                ? const Color(0xFF2ECC71)   // GREEN — dark mode normal ✅
                : const Color(0xFF1A1A6E); // NAVY — light mode normal

    // ── Background color ──
    // Light mode: tinted color
    // Dark mode:  dark card with subtle tint
    final Color bgColor = isDark
        ? hasLeak
            ? const Color(0xFFD80B0B).withValues(alpha: 0.12)
            : !_isValveOpen
                ? const Color(0xFFE6A817).withValues(alpha: 0.10)
                : const Color(0xFF1E1E1E)       // ← dark card, normal state
        : hasLeak
            ? const Color(0xFFD80B0B).withValues(alpha: 0.05)
            : !_isValveOpen
                ? const Color(0xFFE6A817).withValues(alpha: 0.05)
                : Colors.white;

    // ── Switch color ──
    // Normal + valve open → transparent green (as requested)
    // Leak              → red
    // Valve closed      → yellow
    final Color switchActiveColor = hasLeak
        ? const Color(0xFFD80B0B)
        : !_isValveOpen
            ? const Color(0xFFE6A817)
            : const Color(0xFF2ECC71); // green thumb

    // ── Switch track color ──
    // When valve is open and normal → transparent green background
    final Color switchActiveTrack = hasLeak
        ? const Color(0xFFD80B0B).withValues(alpha: 0.3)
        : !_isValveOpen
            ? const Color(0xFFE6A817).withValues(alpha: 0.3)
            : const Color(0xFF2ECC71).withValues(alpha: 0.25); // ← transparent green ✅

    final double maxFlow = widget.zone.inFlow > widget.zone.outFlow
        ? widget.zone.inFlow
        : widget.zone.outFlow;

    return Container(
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: borderColor, width: 2),
        boxShadow: [
          BoxShadow(
            color: borderColor.withValues(alpha: 0.12),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [

          // ── Fixed height top row ──
          SizedBox(
            height: 20,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  hasLeak
                      ? 'Leak Detected'
                      : !_isValveOpen
                          ? 'Valve Closed'
                          : '',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: hasLeak
                        ? const Color(0xFFD80B0B)
                        : const Color(0xFFE6A817),
                  ),
                ),
                Opacity(
                  opacity: hasLeak ? 1.0 : 0.0,
                  child: const Icon(
                    Icons.warning_amber_rounded,
                    color: Color(0xFFD80B0B),
                    size: 20,
                  ),
                ),
              ],
            ),
          ),

          // Zone name
          Text(
            widget.zone.name,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: isDark ? Colors.white : borderColor,
            ),
          ),

          const SizedBox(height: 12),

          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [

              _FlowCircle(
                value:   widget.zone.inFlow,
                maxFlow: maxFlow,
                label:   'IN',
                color:   isDark ? Colors.white70 : borderColor,
                arcColor: borderColor,
                isDark:  isDark,
              ),

              // ── Valve switch ──
              Transform.scale(
                scale: 1.3,
                child: Switch(
                  value: _isValveOpen,
                  onChanged: (value) {
                    setState(() => _isValveOpen = value);
                    widget.onValveToggle?.call(value);
                  },
                  activeColor:      switchActiveColor,
                  activeTrackColor: switchActiveTrack,     // ← transparent green ✅
                  inactiveThumbColor: const Color(0xFFE6A817),
                  inactiveTrackColor: const Color(0xFFE6A817).withValues(alpha: 0.3),
                ),
              ),

              _FlowCircle(
                value:   widget.zone.outFlow,
                maxFlow: maxFlow,
                label:   'OUT',
                color:   isDark ? Colors.white70 : borderColor,
                arcColor: borderColor,
                isDark:  isDark,
              ),

            ],
          ),

        ],
      ),
    );
  }
}

class _FlowCircle extends StatelessWidget {
  final double value;
  final double maxFlow;
  final String label;
  final Color  color;
  final Color  arcColor;
  final bool   isDark;

  const _FlowCircle({
    required this.value,
    required this.maxFlow,
    required this.label,
    required this.color,
    required this.arcColor,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    final double progress = maxFlow > 0
        ? (value / maxFlow).clamp(0.0, 1.0)
        : 0.0;

    return Column(
      children: [
        SizedBox(
          width: 85,
          height: 85,
          child: Stack(
            alignment: Alignment.center,
            children: [

              CustomPaint(
                size: const Size(85, 85),
                painter: _ArcPainter(
                  progress: 1.0,
                  color: isDark
                      ? const Color(0xFF333333)
                      : const Color(0xFFE0E0E0),
                  strokeWidth: 7,
                ),
              ),

              CustomPaint(
                size: const Size(85, 85),
                painter: _ArcPainter(
                  progress: progress,
                  color: arcColor,
                  strokeWidth: 7,
                ),
              ),

              Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    value.toStringAsFixed(1),
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: color,
                      height: 1.0,
                    ),
                  ),
                  Text(
                    'L/min',
                    style: TextStyle(fontSize: 9, color: color),
                  ),
                ],
              ),

            ],
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
      ],
    );
  }
}

class _ArcPainter extends CustomPainter {
  final double progress;
  final Color  color;
  final double strokeWidth;

  _ArcPainter({
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
  bool shouldRepaint(_ArcPainter old) =>
      old.progress != progress || old.color != color;
}