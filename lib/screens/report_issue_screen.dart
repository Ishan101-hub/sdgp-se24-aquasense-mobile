import 'package:flutter/material.dart';

class ReportIssueScreen extends StatefulWidget {
  const ReportIssueScreen({super.key});

  @override
  State<ReportIssueScreen> createState() => _ReportIssueScreenState();
}

class _ReportIssueScreenState extends State<ReportIssueScreen> {
  final _formKey = GlobalKey<FormState>();
  String? selectedIssueType;
  final TextEditingController _descriptionController = TextEditingController();

  // AquaSense Brand Color
  final Color brandBlue = const Color(0xFF0A1B6F);

  final List<String> issueTypes = [
    'Sensor Malfunction',
    'Leaking Valve',
    'Connectivity Issue',
    'Inaccurate Usage Data',
    'Physical Damage',
    'Other'
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFF),
      appBar: AppBar(
        title: const Text("Report Issue", style: TextStyle(fontWeight: FontWeight.bold)),
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
                "Submit a Maintenance Request",
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: brandBlue,
                ),
              ),
              const SizedBox(height: 10),
              const Text(
                "Describe the problem you're experiencing with your AquaSense system.",
                style: TextStyle(color: Colors.grey, fontSize: 14),
              ),
              const SizedBox(height: 30),

              // Issue Type Dropdown
              const Text("Issue Category", style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 10),
              DropdownButtonFormField<String>(
                decoration: _inputDecoration("Select Category"),
                items: issueTypes.map((type) {
                  return DropdownMenuItem(value: type, child: Text(type));
                }).toList(),
                onChanged: (value) => setState(() => selectedIssueType = value),
                validator: (value) => value == null ? 'Please select a category' : null,
              ),
              const SizedBox(height: 25),

              // Description Field
              const Text("Description", style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 10),
              TextFormField(
                controller: _descriptionController,
                maxLines: 5,
                decoration: _inputDecoration("Provide more details..."),
                validator: (value) => value == null || value.isEmpty ? 'Please enter a description' : null,
              ),
              const SizedBox(height: 40),

              // Submit Button
              SizedBox(
                width: double.infinity,
                height: 55,
                child: ElevatedButton(
                  onPressed: () {
                    if (_formKey.currentState!.validate()) {
                      // This will integrate with your FastAPI backend later [cite: 811]
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text("Issue reported successfully!")),
                      );
                      Navigator.pop(context);
                    }
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: brandBlue,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  child: const Text("SUBMIT REPORT", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  InputDecoration _inputDecoration(String hint) {
    return InputDecoration(
      hintText: hint,
      filled: true,
      fillColor: Colors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: brandBlue.withOpacity(0.2)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: brandBlue.withOpacity(0.1)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: brandBlue, width: 2),
      ),
    );
  }
}