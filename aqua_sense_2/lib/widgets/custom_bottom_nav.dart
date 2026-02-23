import 'package:flutter/material.dart';

class CustomBottomNav extends StatelessWidget {
  final int currentIndex;
  final Function(int) onTap;

  const CustomBottomNav({
    super.key,
    required this.currentIndex,
    required this.onTap,
  });

  final List<_NavItem> items = const [
    _NavItem(icon: Icons.home, label: "Home"),
    _NavItem(icon: Icons.water_damage, label: "Leakages"),
    _NavItem(icon: Icons.description, label: "Report"),
    _NavItem(icon: Icons.opacity, label: "Service"),
    _NavItem(icon: Icons.settings, label: "Settings"),
  ];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(12),
      child: Container(
        height: 64,
        decoration: BoxDecoration(
          color: const Color(0xFFDFF4F9),
          borderRadius: BorderRadius.circular(40),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: List.generate(items.length, (index) {
            final bool isActive = index == currentIndex;

            return GestureDetector(
              onTap: () => onTap(index),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                padding: EdgeInsets.symmetric(
                  horizontal: isActive ? 18 : 0,
                ),
                height: 48,
                decoration: BoxDecoration(
                  color: isActive
                      ? const Color(0xFF0A1B6F)
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(30),
                ),
                child: Row(
                  children: [
                    Icon(
                      items[index].icon,
                      color: isActive
                          ? Colors.white
                          : const Color(0xFF0A1B6F),
                    ),
                    if (isActive) ...[
                      const SizedBox(width: 8),
                      Text(
                        items[index].label,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            );
          }),
        ),
      ),
    );
  }
}

class _NavItem {
  final IconData icon;
  final String label;

  const _NavItem({
    required this.icon,
    required this.label,
  });
}