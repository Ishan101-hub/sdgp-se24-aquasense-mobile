import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/auth_service.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {

  // ── Profile fields ───────────────────────────────────────
  String _fullName      = '';
  String _email         = '';
  String _phone         = '';
  String _location      = '';  // maps to address in backend
  String _waterSource   = '';
  String _householdSize = '';
  String _deviceId      = '';
  String _installDate   = '';

  bool _isLoading  = true;
  bool _isSaving   = false;
  bool _isDeleting = false;

  File? _profileImage;
  final ImagePicker _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  // ── Load profile from backend ────────────────────────────
  Future<void> _loadProfile() async {
    setState(() => _isLoading = true);

    final result = await AuthService.getProfile();

    setState(() => _isLoading = false);

    if (result['success']) {
      setState(() {
        _fullName      = result['name']           ?? '';
        _email         = result['email']          ?? '';
        _phone         = result['phone']          ?? '';
        _location      = result['address']        ?? '';
        _waterSource   = result['water_source']   ?? '';
        _householdSize = result['household_size']?.toString() ?? '';
        _deviceId      = result['device_id']      ?? 'Not registered';
        _installDate   = result['install_date'] != null
            ? result['install_date'].toString().split('T')[0]
            : 'N/A';
      });
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result['message']), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _pickImage(ImageSource source) async {
    final XFile? picked = await _picker.pickImage(
      source: source,
      imageQuality: 85,
      maxWidth: 512,
      maxHeight: 512,
    );
    if (picked != null) {
      setState(() => _profileImage = File(picked.path));
    }
  }

  void _showPhotoOptions() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    showModalBottomSheet(
      context: context,
      backgroundColor: isDark ? const Color(0xFF1E1E1E) : Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 10),
            ListTile(
              leading: const Icon(Icons.camera_alt),
              title: const Text("Take Photo"),
              onTap: () { Navigator.pop(context); _pickImage(ImageSource.camera); },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text("Choose from Gallery"),
              onTap: () { Navigator.pop(context); _pickImage(ImageSource.gallery); },
            ),
            if (_profileImage != null)
              ListTile(
                leading: const Icon(Icons.delete, color: Colors.red),
                title: const Text("Remove Photo", style: TextStyle(color: Colors.red)),
                onTap: () {
                  Navigator.pop(context);
                  setState(() => _profileImage = null);
                },
              ),
            const SizedBox(height: 10),
          ],
        ),
      ),
    );
  }

  // ── Delete account dialog ────────────────────────────────
  void _showDeleteDialog() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: isDark ? const Color(0xFF1E1E1E) : Colors.white,
        title: const Text("Delete Account"),
        content: const Text(
          "Are you sure you want to delete your account? This action cannot be undone."),
        actions: [
          TextButton(
            child: const Text("Cancel"),
            onPressed: () => Navigator.pop(context),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            onPressed: _isDeleting
                ? null
                : () async {
                    setState(() => _isDeleting = true);

                    final result = await AuthService.deleteAccount();

                    setState(() => _isDeleting = false);

                    Navigator.pop(context);

                    if (result['success']) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Account deleted successfully.'),
                          backgroundColor: Color(0xFF0A1B6F),
                        ),
                      );
                      // Navigate to login and clear all routes
                      Navigator.pushNamedAndRemoveUntil(
                        context, '/login', (route) => false);
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(result['message']),
                          backgroundColor: Colors.red,
                        ),
                      );
                    }
                  },
            child: _isDeleting
                ? const SizedBox(
                    height: 18, width: 18,
                    child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                : const Text("Delete", style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  // ── Edit profile bottom sheet ────────────────────────────
  void _showEditSheet() {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final nameCtrl  = TextEditingController(text: _fullName);
    final phoneCtrl = TextEditingController(text: _phone);
    final locCtrl   = TextEditingController(text: _location);

    // Note: email, water_source, household_size are read-only
    // (not supported by UpdateProfileSchema)

    bool isSavingLocal = false;

    showModalBottomSheet(
      context: context,
      backgroundColor: isDark ? const Color(0xFF1E1E1E) : Colors.white,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(25)),
      ),
      builder: (sheetCtx) => StatefulBuilder(
        builder: (sheetCtx, setSheetState) {
          return Padding(
            padding: EdgeInsets.only(
              bottom: MediaQuery.of(context).viewInsets.bottom,
              left: 20, right: 20, top: 25,
            ),
            // Wrapped in SingleChildScrollView so the sheet scrolls
            // instead of overflowing once the keyboard eats into the
            // available height (6 fields + button is a lot of content).
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [

                  const Text(
                    "Edit Profile",
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),

                  const SizedBox(height: 6),

                  const Text(
                    'You can update your name, phone and location.',
                    style: TextStyle(fontSize: 12, color: Colors.grey),
                  ),

                  const SizedBox(height: 16),

                  _editField(nameCtrl,  "Full Name"),
                  _editField(phoneCtrl, "Phone Number (e.g. +94XXXXXXXXX)"),
                  _editField(locCtrl,   "Location / Address"),

                  // ── Read-only info ───────────────────────
                  _readOnlyField("Email",          _email),
                  _readOnlyField("Water Source",   _waterSource),
                  _readOnlyField("Household Size", _householdSize),

                  const SizedBox(height: 20),

                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        backgroundColor: const Color(0xFF0A1B6F),
                        disabledBackgroundColor: Colors.grey[300],
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      onPressed: isSavingLocal
                          ? null
                          : () async {
                              setSheetState(() => isSavingLocal = true);

                              final result = await AuthService.updateProfile(
                                name:    nameCtrl.text.trim().isNotEmpty
                                    ? nameCtrl.text.trim() : null,
                                phone:   phoneCtrl.text.trim().isNotEmpty
                                    ? phoneCtrl.text.trim() : null,
                                address: locCtrl.text.trim().isNotEmpty
                                    ? locCtrl.text.trim() : null,
                              );

                              setSheetState(() => isSavingLocal = false);

                              if (result['success']) {
                                // Update local state
                                setState(() {
                                  _fullName = nameCtrl.text.trim();
                                  _phone    = phoneCtrl.text.trim();
                                  _location = locCtrl.text.trim();
                                });
                                Navigator.pop(sheetCtx);
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text('Profile updated successfully!'),
                                    backgroundColor: Color(0xFF0A1B6F),
                                  ),
                                );
                              } else {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(result['message']),
                                    backgroundColor: Colors.red,
                                  ),
                                );
                              }
                            },
                      child: isSavingLocal
                          ? const SizedBox(
                              height: 20, width: 20,
                              child: CircularProgressIndicator(
                                  color: Colors.white, strokeWidth: 2))
                          : const Text(
                              "Save Changes",
                              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                            ),
                    ),
                  ),

                  const SizedBox(height: 20),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _editField(TextEditingController ctrl, String label) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        controller: ctrl,
        decoration: InputDecoration(
          labelText: label,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
    );
  }

  Widget _readOnlyField(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        readOnly: true,
        controller: TextEditingController(text: value),
        decoration: InputDecoration(
          labelText: '$label (read-only)',
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          filled: true,
          fillColor: Colors.grey[100],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF121212) : const Color(0xFFF5F7FB),
      appBar: AppBar(
        title: const Text("Profile", style: TextStyle(color: Colors.white)),
        backgroundColor: const Color(0xFF0A1B6F),
        iconTheme: const IconThemeData(color: Colors.white),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white),
            onPressed: _loadProfile,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Color(0xFF0A1B6F)))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [

                  // ── Profile card ─────────────────────────
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: [
                        BoxShadow(blurRadius: 10, color: Colors.black.withOpacity(.08))
                      ],
                    ),
                    child: Column(
                      children: [
                        Stack(
                          alignment: Alignment.bottomRight,
                          children: [
                            Container(
                              width: 90,
                              height: 90,
                              decoration: const BoxDecoration(
                                color: Color(0xFF0A1B6F),
                                shape: BoxShape.circle,
                              ),
                              child: ClipOval(
                                child: _profileImage != null
                                    ? Image.file(_profileImage!, fit: BoxFit.cover)
                                    : const Icon(Icons.person, size: 50, color: Colors.white),
                              ),
                            ),
                            GestureDetector(
                              onTap: _showPhotoOptions,
                              child: Container(
                                width: 28,
                                height: 28,
                                decoration: BoxDecoration(
                                  color: Colors.lightBlue,
                                  shape: BoxShape.circle,
                                  border: Border.all(color: Colors.white, width: 2),
                                ),
                                child: const Icon(Icons.camera_alt, color: Colors.white, size: 16),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Text(
                          _fullName.isNotEmpty ? _fullName : 'No name set',
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                            color: isDark ? Colors.white : Colors.black,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(_email, style: const TextStyle(color: Colors.grey)),
                      ],
                    ),
                  ),

                  const SizedBox(height: 25),

                  // ── Info tiles ───────────────────────────
                  Container(
                    decoration: BoxDecoration(
                      color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Column(
                      children: [
                        _infoTile(Icons.phone,          "Phone",          _phone.isNotEmpty ? _phone : '—'),
                        _divider(),
                        _infoTile(Icons.location_on,    "Location",       _location.isNotEmpty ? _location : '—'),
                        _divider(),
                        _infoTile(Icons.qr_code,        "Device ID",      _deviceId),
                        _divider(),
                        _infoTile(Icons.calendar_today, "Install Date",   _installDate),
                        _divider(),
                        _infoTile(Icons.water_drop,     "Water Source",   _waterSource.isNotEmpty ? _waterSource : '—'),
                        _divider(),
                        _infoTile(Icons.people,         "Household Size", _householdSize.isNotEmpty ? _householdSize.toString() : '—'),
                      ],
                    ),
                  ),

                  const SizedBox(height: 30),

                  // ── Edit Profile button ──────────────────
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      icon: const Icon(Icons.edit, color: Colors.white),
                      label: const Text("Edit Profile",
                          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        backgroundColor: const Color(0xFF0A1B6F),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                      onPressed: _showEditSheet,
                    ),
                  ),

                  const SizedBox(height: 12),

                  // ── Delete Account button ────────────────
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      icon: const Icon(Icons.delete, color: Colors.red),
                      label: const Text("Delete Account",
                          style: TextStyle(color: Colors.red)),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: Colors.red),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                      onPressed: _showDeleteDialog,
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _infoTile(IconData icon, String title, String value) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return ListTile(
      leading: Icon(icon, color: const Color(0xFF0A1B6F)),
      title: Text(title, style: TextStyle(color: isDark ? Colors.white : Colors.black)),
      trailing: Text(value, style: const TextStyle(color: Colors.grey)),
    );
  }

  Widget _divider() => const Divider(height: 1);
}