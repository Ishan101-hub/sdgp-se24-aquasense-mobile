import 'package:flutter/material.dart';
import 'package:screen_brightness/screen_brightness.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ThemeProvider extends ChangeNotifier {

  /// Default values
  String _selectedTheme = 'light';
  double _fontSize = 14;
  double _brightness = 0.7;

  /// Getters
  String get selectedTheme => _selectedTheme;
  double get fontSize => _fontSize;
  double get brightness => _brightness;

  /// Convert String to ThemeMode
  ThemeMode get themeMode {
    switch (_selectedTheme) {
      case 'dark':
        return ThemeMode.dark;
      case 'system':
        return ThemeMode.system;
      default:
        return ThemeMode.light;
    }
  }

  /// Initialize provider when app starts
  Future<void> init() async {
    await _loadPrefs();
    await _applyBrightness(_brightness);
  }

  /// Change theme
  Future<void> setTheme(String theme) async {
    _selectedTheme = theme;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('selectedTheme', theme);

    notifyListeners();
  }

  /// Change brightness
  Future<void> setBrightness(double value) async {
    _brightness = value;

    await _applyBrightness(value);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble('brightness', value);

    notifyListeners();
  }

  /// Apply brightness using plugin
  Future<void> _applyBrightness(double value) async {
    try {
      await ScreenBrightness().setScreenBrightness(value);
    } catch (_) {
      // Some platforms don't support brightness control
    }
  }

  /// Reset brightness
  Future<void> resetBrightness() async {
    try {
      await ScreenBrightness().resetScreenBrightness();
    } catch (_) {}
  }

  /// Change font size
  Future<void> setFontSize(double size) async {
    _fontSize = size;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble('fontSize', size);

    notifyListeners();
  }

  /// Load saved settings
  Future<void> _loadPrefs() async {
    final prefs = await SharedPreferences.getInstance();

    _selectedTheme = prefs.getString('selectedTheme') ?? 'light';
    _brightness = prefs.getDouble('brightness') ?? 0.7;
    _fontSize = prefs.getDouble('fontSize') ?? 14;

    notifyListeners();
  }

  /// Light Theme
  static ThemeData lightTheme(double fontSize) {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorSchemeSeed: const Color(0xFF0A1B6F),

      scaffoldBackgroundColor: Colors.grey[100],

      textTheme: _textTheme(fontSize, Colors.black87),

      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xFF0A1B6F),
        foregroundColor: Colors.white,
      ),

      sliderTheme: _sliderTheme(),

      elevatedButtonTheme: _buttonTheme(),

      cardColor: Colors.white,
    );
  }

  /// Dark Theme
  static ThemeData darkTheme(double fontSize) {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorSchemeSeed: const Color(0xFF0A1B6F),

      scaffoldBackgroundColor: const Color(0xFF0D0D1A),

      textTheme: _textTheme(fontSize, Colors.white),

      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xFF0A1B6F),
        foregroundColor: Colors.white,
      ),

      sliderTheme: _sliderTheme(),

      elevatedButtonTheme: _buttonTheme(),

      cardColor: const Color(0xFF1A1A2E),
    );
  }

  /// Text Theme
  static TextTheme _textTheme(double size, Color color) {
    return TextTheme(
      bodySmall: TextStyle(fontSize: size - 2, color: color),
      bodyMedium: TextStyle(fontSize: size, color: color),
      bodyLarge: TextStyle(fontSize: size + 2, color: color),
      titleMedium: TextStyle(
        fontSize: size + 2,
        fontWeight: FontWeight.w600,
      ),
      titleLarge: TextStyle(
        fontSize: size + 4,
        fontWeight: FontWeight.bold,
      ),
    );
  }

  /// Slider Theme
  static SliderThemeData _sliderTheme() {
    return const SliderThemeData(
      activeTrackColor: Color(0xFF0A1B6F),
      inactiveTrackColor: Color(0x330A1B6F),
      thumbColor: Color(0xFF0A1B6F),
      overlayColor: Color(0x220A1B6F),
    );
  }

  /// Button Theme
  static ElevatedButtonThemeData _buttonTheme() {
    return ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: const Color(0xFF0A1B6F),
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(vertical: 16),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
        ),
        textStyle: const TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}