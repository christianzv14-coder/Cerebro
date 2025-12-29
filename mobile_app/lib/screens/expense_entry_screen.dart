import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../providers/auth_provider.dart';

class ExpenseEntryScreen extends StatefulWidget {
  @override
  _ExpenseEntryScreenState createState() => _ExpenseEntryScreenState();
}

class _ExpenseEntryScreenState extends State<ExpenseEntryScreen> {
  final _formKey = GlobalKey<FormState>();
  final _amountController = TextEditingController();
  final _conceptController = TextEditingController();
  final _categoryController = TextEditingController();

  File? _imageFile;
  final ImagePicker _picker = ImagePicker();
  bool _isLoading = false;

  // Default suggestions
  final List<String> _suggestedCategories = [
    "Departamento",
    "Gastos Fijos",
    "Comidas",
    "Combustible",
    "Materiales"
  ];

  Future<void> _pickImage(ImageSource source) async {
    try {
      final XFile? pickedFile =
          await _picker.pickImage(source: source, imageQuality: 50);
      if (pickedFile != null) {
        setState(() {
          _imageFile = File(pickedFile.path);
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al tomar foto: $e')),
      );
    }
  }

  void _showImageSourceActionSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Wrap(
          children: <Widget>[
            ListTile(
              leading: Icon(Icons.photo_library),
              title: Text('Galería'),
              onTap: () {
                Navigator.of(context).pop();
                _pickImage(ImageSource.gallery);
              },
            ),
            ListTile(
              leading: Icon(Icons.photo_camera),
              title: Text('Cámara'),
              onTap: () {
                Navigator.of(context).pop();
                _pickImage(ImageSource.camera);
              },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _submitExpense() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
    });

    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final apiService = ApiService(
          baseUrl:
              "https://cozy-smile-production.up.railway.app/api/v1"); // Should come from config

      // We need to implement createExpense in ApiService!
      await apiService.createExpense(
          amount: int.parse(_amountController.text),
          concept: _conceptController.text,
          category: _categoryController.text,
          imagePath: _imageFile?.path);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text('¡Gasto guardado y sincronizado!'),
            backgroundColor: Colors.green),
      );

      Navigator.pop(context); // Return to home
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text('Error al guardar: $e'), backgroundColor: Colors.red),
      );
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text("Ingresar Gasto"),
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Amount
              TextFormField(
                controller: _amountController,
                decoration: InputDecoration(
                  labelText: "Monto (\$)",
                  prefixText: "\$ ",
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value == null || value.isEmpty)
                    return 'Por favor ingrese el monto';
                  if (int.tryParse(value) == null)
                    return 'Ingrese un número válido';
                  return null;
                },
              ),
              SizedBox(height: 16),

              // Concept
              TextFormField(
                controller: _conceptController,
                decoration: InputDecoration(
                  labelText: "Concepto (Detalle)",
                  border: OutlineInputBorder(),
                  hintText: "Ej. Almuerzo en ruta",
                ),
                validator: (value) =>
                    value!.isEmpty ? 'Ingrese un concepto' : null,
              ),
              SizedBox(height: 16),

              // Category
              TextFormField(
                controller: _categoryController,
                decoration: InputDecoration(
                  labelText: "Categoría",
                  border: OutlineInputBorder(),
                ),
                validator: (value) =>
                    value!.isEmpty ? 'Ingrese una categoría' : null,
              ),
              // Chips for quick selection
              Wrap(
                spacing: 8.0,
                children: _suggestedCategories.map((cat) {
                  return ActionChip(
                    label: Text(cat),
                    onPressed: () {
                      _categoryController.text = cat;
                    },
                  );
                }).toList(),
              ),
              SizedBox(height: 24),

              // Image Picker
              Text("Comprobante / Boleta (Opcional)",
                  style: TextStyle(fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              if (_imageFile != null)
                Stack(
                  alignment: Alignment.topRight,
                  children: [
                    Image.file(_imageFile!,
                        height: 200, width: double.infinity, fit: BoxFit.cover),
                    IconButton(
                      icon: Icon(Icons.close, color: Colors.red),
                      onPressed: () => setState(() => _imageFile = null),
                    )
                  ],
                )
              else
                OutlinedButton.icon(
                  onPressed: () => _showImageSourceActionSheet(context),
                  icon: Icon(Icons.camera_alt),
                  label: Text("Adjuntar Foto"),
                  style: OutlinedButton.styleFrom(padding: EdgeInsets.all(16)),
                ),

              SizedBox(height: 32),

              // Submit Button
              ElevatedButton(
                onPressed: _isLoading ? null : _submitExpense,
                child: _isLoading
                    ? SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : Text("GUARDAR GASTO", style: TextStyle(fontSize: 18)),
                style: ElevatedButton.styleFrom(
                  padding: EdgeInsets.symmetric(vertical: 16),
                  backgroundColor: Theme.of(context).primaryColor,
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
