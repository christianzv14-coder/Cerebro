import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/app_drawer.dart';
import 'home_screen.dart'; // We can reuse HomeScreen or create a detail variant

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  final ApiService _api = ApiService();
  List<String> _dates = [];
  bool _isLoading = true;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _loadDates();
  }

  Future<void> _loadDates() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      final dates = await _api.getDates();
      setState(() {
        _dates = dates;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = "Error al cargar historial: $e";
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Historial de Tareas')),
      drawer: const AppDrawer(),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage.isNotEmpty
              ? Center(child: Text(_errorMessage))
              : _dates.isEmpty
                  ? const Center(child: Text("No tienes historial disponible."))
                  : ListView.builder(
                      itemCount: _dates.length,
                      itemBuilder: (context, index) {
                        final dateStr = _dates[index];
                        return Card(
                          margin: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 5),
                          child: ListTile(
                            leading:
                                const Icon(Icons.folder, color: Colors.blue),
                            title: Text("Fecha: $dateStr"),
                            trailing: const Icon(Icons.chevron_right),
                            onTap: () {
                              // Navigate to HomeScreen but with a SPECIFIC DATE
                              // We need to modify HomeScreen to accept a date!
                              Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (_) => HomeScreen(
                                          initialDate:
                                              DateTime.parse(dateStr))));
                            },
                          ),
                        );
                      },
                    ),
    );
  }
}
