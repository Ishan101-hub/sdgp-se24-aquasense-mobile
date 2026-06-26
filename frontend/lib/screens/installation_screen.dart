import 'package:flutter/material.dart';
import '../services/api_service.dart';

class InstallationScreen extends StatefulWidget {
  const InstallationScreen({super.key});

  @override
  State<InstallationScreen> createState() => _InstallationScreenState();
}

class _InstallationScreenState extends State<InstallationScreen> {
  final _formKey = GlobalKey<FormState>();

  final Color brandBlue = const Color(0xFF0A1B6F);

  final TextEditingController _addressController = TextEditingController();
  final TextEditingController _zoneController = TextEditingController();
  DateTime? selectedDate;

  final _api    = ApiService();
  bool _isLoading = false;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: const Text(
          "New Installation",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: brandBlue,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                "Request System Setup",
                style: textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : brandBlue,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                "Provide details to schedule an installation for your multi-zone water management system.",
                style: textTheme.bodySmall?.copyWith(
                  color: isDark ? Colors.grey[400] : Colors.grey,
                ),
              ),
              const SizedBox(height: 30),

              // Installation Address
              Text(
                "Installation Address",
                style: textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _addressController,
                style: textTheme.bodyMedium,
                decoration: _inputDecoration(
                  "e.g., 123 Main St, Ragama",
                  isDark,
                ),
                validator: (value) =>
                    value!.isEmpty ? 'Please enter your address' : null,
              ),
              const SizedBox(height: 20),

              // Number of Zones
              Text(
                "Number of Zones (Lines)",
                style: textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _zoneController,
                keyboardType: TextInputType.number,
                style: textTheme.bodyMedium,
                decoration: _inputDecoration(
                  "e.g., 3 (Kitchen, Bathroom, Garden)",
                  isDark,
                ),
                validator: (value) =>
                    value!.isEmpty ? 'Enter the number of sub-lines' : null,
              ),
              const SizedBox(height: 20),

              // Date Picker
              Text(
                "Preferred Date",
                style: textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 10),
              InkWell(
                onTap: () async {
                  DateTime? pickedDate = await showDatePicker(
                    context: context,
                    initialDate: DateTime.now().add(const Duration(days: 1)),
                    firstDate: DateTime.now(),
                    lastDate: DateTime.now().add(const Duration(days: 30)),
                  );
                  if (pickedDate != null) {
                    setState(() => selectedDate = pickedDate);
                  }
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 15,
                  ),
                  decoration: BoxDecoration(
                    color: Theme.of(context).cardColor,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: isDark
                          ? Colors.white.withOpacity(0.15)
                          : brandBlue.withOpacity(0.1),
                    ),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        selectedDate == null
                            ? "Select Date"
                            : "${selectedDate!.day}/${selectedDate!.month}/${selectedDate!.year}",
                        style: textTheme.bodyMedium?.copyWith(
                          color: selectedDate == null
                              ? (isDark ? Colors.grey[500] : Colors.grey)
                              : (isDark ? Colors.white : Colors.black),
                        ),
                      ),
                      Icon(
                        Icons.calendar_today,
                        color: isDark ? Colors.grey[400] : brandBlue,
                        size: 20,
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 40),

              // Submit Button
              SizedBox(
                width: double.infinity,
                height: 55,
                child: ElevatedButton(
                  onPressed: _isLoading
                      ? null
                      : () async {
                          if (selectedDate == null) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('Please pick a preferred date.'),
                                backgroundColor: Colors.red,
                              ),
                            );
                            return;
                          }

                          if (!(_formKey.currentState?.validate() ?? false)) return;

                          setState(() => _isLoading = true);

                          try {
                            await _api.requestInstallation(
                              address:       _addressController.text.trim(),
                              numZones:      int.parse(_zoneController.text.trim()),
                              preferredDate: selectedDate!,
                            );

                            if (!mounted) return;
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content:         Text('Installation request submitted!'),
                                backgroundColor: Color(0xFF0A1B6F),
                              ),
                            );
                            Navigator.pop(context);
                          } catch (e) {
                            if (!mounted) return;
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content:         Text(e.toString().replaceFirst('Exception: ', '')),
                                backgroundColor: Colors.red,
                              ),
                            );
                          } finally {
                            if (mounted) setState(() => _isLoading = false);
                          }
                        },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: brandBlue,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: _isLoading
                      ? const SizedBox(
                          height: 22,
                          width: 22,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                        )
                      : const Text(
                          "REQUEST INSTALLATION",
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  InputDecoration _inputDecoration(String hint, bool isDark) {
    return InputDecoration(
      hintText: hint,
      hintStyle: TextStyle(color: isDark ? Colors.grey[500] : Colors.grey),
      filled: true,
      fillColor: isDark ? const Color(0xFF1E1E2E) : Colors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(
          color: isDark
              ? Colors.white.withOpacity(0.15)
              : brandBlue.withOpacity(0.2),
        ),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(
          color: isDark
              ? Colors.white.withOpacity(0.12)
              : brandBlue.withOpacity(0.1),
        ),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(
          color: isDark ? Colors.lightBlueAccent : brandBlue,
          width: 2,
        ),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: Colors.redAccent),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: Colors.redAccent, width: 2),
      ),
    );
  }
}
