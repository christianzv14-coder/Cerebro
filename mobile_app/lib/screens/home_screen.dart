import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../providers/auth_provider.dart';
import 'activity_detail_screen.dart';
import 'signature_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final ApiService _api = ApiService();
  List<Activity> _activities = [];
  bool _isLoading = true;
  bool _isSigned = false;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _loadActivities();
  }

  Future<void> _loadActivities() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      // Server defaults to Today if no date is passed.
      // This avoids timezone mismatches between Phone and Server.
      final list = await _api.getActivities();
      final isSigned = await _api.getSignatureStatus();
      debugPrint('DEBUG: _isSigned fetched as $isSigned');
      setState(() {
        _activities = list;
        _isSigned = isSigned;
        _isLoading = false;
      });
    } catch (e, stackTrace) {
      debugPrint('ERROR LOADING ACTIVITIES: $e');
      debugPrint('STACKTRACE: $stackTrace');
      setState(() {
        _errorMessage = "Exception: $e";
        _isLoading = false;
      });
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'PENDIENTE':
        return Colors.grey;
      case 'EN_CURSO':
        return Colors.blue;
      case 'EXITOSO':
        return Colors.green;
      case 'FALLIDO':
        return Colors.red;
      case 'REPROGRAMADO':
        return Colors.orange;
      default:
        return Colors.black;
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = Provider.of<AuthProvider>(context).user;

    // Counters
    final pendingCount = _activities.where((a) => a.isPending).length;
    final inProgressCount = _activities.where((a) => a.isInProgress).length;
    final closedCount = _activities.where((a) => a.isClosed).length;

    debugPrint(
        'DEBUG BUILD: pending=$pendingCount, inProgress=$inProgressCount, closed=$closedCount, isSigned=$_isSigned');
    // STRICT RULE: ONLY show if EVERYTHING is closed, even if it was signed before.
    final showSignatureButton =
        _activities.isNotEmpty && _activities.every((a) => a.isClosed);
    debugPrint('DEBUG BUILD: showSignatureButton=$showSignatureButton');

    return Scaffold(
      appBar: AppBar(
        title: Text('Hola, ${user?.tecnicoNombre ?? ""} (vFixed)'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadActivities,
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () =>
                Provider.of<AuthProvider>(context, listen: false).logout(),
          ),
        ],
      ),
      body: Column(
        children: [
          // SUMMARY CARDS
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                _buildSummaryCard('Pendientes', pendingCount, Colors.grey),
                _buildSummaryCard('En Curso', inProgressCount, Colors.blue),
                _buildSummaryCard('Cerradas', closedCount, Colors.green),
              ],
            ),
          ),

          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _errorMessage.isNotEmpty
                    ? Center(child: Text(_errorMessage))
                    : _activities.isEmpty
                        ? const Center(
                            child: Text("No tienes actividades hoy."))
                        : RefreshIndicator(
                            onRefresh: _loadActivities,
                            child: ListView.builder(
                              itemCount: _activities.length,
                              itemBuilder: (context, index) {
                                final activity = _activities[index];
                                return Card(
                                  margin: const EdgeInsets.symmetric(
                                      horizontal: 10, vertical: 5),
                                  child: ListTile(
                                    leading: CircleAvatar(
                                      backgroundColor:
                                          _getStatusColor(activity.estado),
                                      child: const Icon(Icons.work,
                                          color: Colors.white, size: 20),
                                    ),
                                    title: Text(
                                        activity.cliente ?? "Sin Cliente",
                                        style: const TextStyle(
                                            fontWeight: FontWeight.bold)),
                                    subtitle: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text("${activity.direccion}"),
                                        Row(
                                          children: [
                                            Text("Ticket: ${activity.ticketId}",
                                                style: const TextStyle(
                                                    fontSize: 12)),
                                            const Spacer(),
                                            if (activity.patente != null)
                                              Text(
                                                  "Patente: ${activity.patente}",
                                                  style: const TextStyle(
                                                      fontSize: 12,
                                                      fontWeight:
                                                          FontWeight.bold)),
                                          ],
                                        ),
                                        if (activity.tipoTrabajo != null)
                                          Text(
                                              "Trabajo: ${activity.tipoTrabajo}",
                                              style: const TextStyle(
                                                  fontSize: 12,
                                                  fontStyle: FontStyle.italic)),
                                      ],
                                    ),
                                    trailing: const Icon(Icons.chevron_right),
                                    onTap: () async {
                                      await Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                            builder: (_) =>
                                                ActivityDetailScreen(
                                                    activity: activity)),
                                      );
                                      _loadActivities();
                                    },
                                  ),
                                );
                              },
                            ),
                          ),
          ),

          // SIGNATURE BUTTON
          if (showSignatureButton)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              color: Colors.white,
              child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                    backgroundColor: _isSigned ? Colors.green : Colors.black,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.all(16)),
                onPressed: () async {
                  if (_isSigned) {
                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                        content: Text("Ya está firmado en el servidor.")));
                    _loadActivities(); // Just refresh
                  } else {
                    await Navigator.push(
                        context,
                        MaterialPageRoute(
                            builder: (_) => const SignatureScreen()));
                    _loadActivities();
                  }
                },
                icon: Icon(_isSigned ? Icons.check : Icons.draw),
                label: const Text("FIRMAR JORNADA"),
              ),
            )
        ],
      ),
    );
  }

  Widget _buildSummaryCard(String label, int count, Color color) {
    return Expanded(
      child: Card(
        color: color.withOpacity(0.1),
        elevation: 0,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 16),
          child: Column(
            children: [
              Text(count.toString(),
                  style: TextStyle(
                      fontSize: 24, fontWeight: FontWeight.bold, color: color)),
              Text(label, style: TextStyle(color: color, fontSize: 12)),
            ],
          ),
        ),
      ),
    );
  }
}
