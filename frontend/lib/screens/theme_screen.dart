import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme_provider.dart';

class ThemeScreen extends StatelessWidget {
  const ThemeScreen({super.key});

  @override
  Widget build(BuildContext context) {

    final themeProvider = context.watch<ThemeProvider>();

    String selectedTheme = themeProvider.selectedTheme;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,

      appBar: AppBar(
        title: const Text('Theme'),
      ),

      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),

        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            /// TITLE
            const Text(
              'Select Theme',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 14),

            /// THEME CARDS - vertical
            _buildThemeCard(
              context: context,
              label: 'Light',
              icon: Icons.wb_sunny_outlined,
              value: 'light',
              selectedTheme: selectedTheme,
            ),

            const SizedBox(height: 12),

            _buildThemeCard(
              context: context,
              label: 'Dark',
              icon: Icons.nights_stay_outlined,
              value: 'dark',
              selectedTheme: selectedTheme,
            ),

            const SizedBox(height: 12),

            _buildThemeCard(
              context: context,
              label: 'System',
              icon: Icons.phone_android_outlined,
              value: 'system',
              selectedTheme: selectedTheme,
            ),

            const SizedBox(height: 28),

            /// SAVE BUTTON
            SizedBox(
              width: double.infinity,

              child: ElevatedButton(
                onPressed: () {

                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(
                        'Theme set to ${selectedTheme[0].toUpperCase()}${selectedTheme.substring(1)}!',
                      ),
                    ),
                  );

                },

                child: const Text('Apply Theme'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// THEME CARD
  Widget _buildThemeCard({
    required BuildContext context,
    required String label,
    required IconData icon,
    required String value,
    required String selectedTheme,
  }) {

    bool isSelected = selectedTheme == value;

    return GestureDetector(

      onTap: () {
        context.read<ThemeProvider>().setTheme(value);
      },

      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),

        padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 20),

        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),

          border: Border.all(
            color: isSelected
                ? Theme.of(context).colorScheme.primary
                : Colors.grey,
            width: isSelected ? 2.5 : 1,
          ),
        ),

        child: Row(
          children: [

            Icon(icon, size: 30),

            const SizedBox(width: 16),

            Text(
              label,
              style: const TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 15,
              ),
            ),

            const Spacer(),

            if (isSelected)
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primary,
                  shape: BoxShape.circle,
                ),
              ),
          ],
        ),
      ),
    );
  }
}