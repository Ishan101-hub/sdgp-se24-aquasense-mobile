import 'package:flutter/material.dart';
import 'dart:math' as math;

import '../models/mobile_models.dart';

// ── LeakageCard ──────────────────────────────────────────────
// Accepts LeakageZone from mobile_models.dart.
// All UI (arc circles, switch, colour scheme) is unchanged.
class LeakageCard extends StatefulWidget {
  final LeakageZone zone;
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
    _isValveOpen = widget.zone.valveState == 'open';
  }

  // Keep local toggle in sync when backend refresh updates valve state
  @override
  void didUpdateWidget(LeakageCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    final nowOpen = widget.zone.valveState == 'open';
    if ((oldWidget.zone.valveState == 'open') != nowOpen) {
      _isValveOpen = nowOpen;
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    // Derived booleans — mapped from LeakageZone fields
    final bool hasLeak  = widget.zone.leak && _isValveOpen;
    final bool isClosed = !_isValveOpen;

    // ── Card colours based on state ───────────────────────────
    // 🔴 Leak    → Red
    // 🟡 Closed  → Yellow
    // 🔵 Normal  → Navy (light) / Green (dark)
    final Color borderColor = hasLeak
        ? const Color(0xFFD80B0B)
        : isClosed
            ? const Color(0xFFE6A817)
            : isDark
                ? const Color(0xFF1A8C4E)
                : const Color(0xFF1A1A6E);

    final Color bgColor = hasLeak
        ? const Color(0xFFD80B0B).withValues(alpha: isDark ? 0.12 : 0.05)
        : isClosed
            ? const Color(0xFFE6A817).withValues(alpha: isDark ? 0.10 : 0.05)
            : isDark
                ? const Color(0xFF1E1E1E)
                : Colors.white;

    final Color switchActiveColor = hasLeak
        ? const Color(0xFFD80B0B)
        : isClosed
            ? const Color(0xFFE6A817)
            : const Color(0xFF1A8C4E);

    final Color switchActiveTrack = switchActiveColor.withValues(alpha: 0.25);

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

          // ── Fixed-height top row: status label + warning icon ──
          SizedBox(
            height: 20,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  hasLeak
                      ? 'Leak Detected'
                      : isClosed
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

          // Zone name — uses zoneName from LeakageZone
          Text(
            widget.zone.zoneName,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: isDark ? Colors.white : borderColor,
            ),
          ),

          // Optional subtitle: zone type · floor
          if (widget.zone.zoneType.isNotEmpty || widget.zone.floor.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Text(
                _subtitle(),
                style: const TextStyle(fontSize: 11, color: Colors.grey),
              ),
            ),

          const SizedBox(height: 12),

          // ── IN circle + Switch + OUT circle ──────────────────
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [

              // IN sensor arc
              _FlowCircle(
                value:    widget.zone.inFlow,
                maxFlow:  maxFlow,
                label:    'IN',
                color:    isDark ? Colors.white70 : borderColor,
                arcColor: borderColor,
                isDark:   isDark,
              ),

              // Valve toggle switch
              Transform.scale(
                scale: 1.3,
                child: Switch(
                  value: _isValveOpen,
                  onChanged: (value) {
                    setState(() => _isValveOpen = value);
                    widget.onValveToggle?.call(value);
                  },
                  activeColor:        switchActiveColor,
                  activeTrackColor:   switchActiveTrack,
                  inactiveThumbColor: const Color(0xFFE6A817),
                  inactiveTrackColor:
                      const Color(0xFFE6A817).withValues(alpha: 0.3),
                ),
              ),

              // OUT sensor arc
              _FlowCircle(
                value:    widget.zone.outFlow,
                maxFlow:  maxFlow,
                label:    'OUT',
                color:    isDark ? Colors.white70 : borderColor,
                arcColor: borderColor,
                isDark:   isDark,
              ),

            ],
          ),

        ],
      ),
    );
  }

  String _subtitle() {
    final parts = <String>[];
    if (widget.zone.zoneType.isNotEmpty) {
      parts.add(_cap(widget.zone.zoneType));
    }
    if (widget.zone.floor.isNotEmpty) {
      parts.add(_cap(widget.zone.floor));
    }
    return parts.join(' · ');
  }

  String _cap(String s) =>
      s.isEmpty ? s : s[0].toUpperCase() + s.substring(1);
}


// ── Flow Circle ───────────────────────────────────────────────
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

              // Background arc track
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

              // Foreground progress arc
              CustomPaint(
                size: const Size(85, 85),
                painter: _ArcPainter(
                  progress: progress,
                  color: arcColor,
                  strokeWidth: 7,
                ),
              ),

              // Value text
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


// ── Arc Painter ───────────────────────────────────────────────
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

    canvas.drawArc(
      Rect.fromCircle(
        center: Offset(size.width / 2, size.height / 2),
        radius: (size.width - strokeWidth) / 2,
      ),
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