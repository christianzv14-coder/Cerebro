import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/user.dart'; // activity.dart is imported, models need precise check
import '../models/activity.dart';
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
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _loadActivities();
  }

  Future<void> _loadActivities() async {
    setState(() { _isLoading = true; _errorMessage = ''; });
    try {
      final list = await _api.getActivities(date: DateTime.now());
      setState(() {
        _activities = list;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'PENDIENTE': return Colors.grey;
      case 'EN_CURSO': return Colors.blue;
      case 'EXITOSO': return Colors.green;
      case 'FALLIDO': return Colors.red;
      case 'REPROGRAMADO': return Colors.orange;
      default: return Colors.black;
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = Provider.of<AuthProvider>(context).user;
    
    // Counters
    final pendingCount = _activities.where((a) => a.isPending).length;
    final inProgressCount = _activities.where((a) => a.isInProgress).length;
    final closedCount = _activities.where((a) => a.isClosed).length;

    return Scaffold(
      appBar: AppBar(
        title: Text('Hola, ${user?.tecnicoNombre ?? ""}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadActivities,
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => Provider.of<AuthProvider>(context, listen: false).logout(),
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
                  ? const Center(child: Text("No tienes actividades hoy."))
                  : RefreshIndicator(
                      onRefresh: _loadActivities,
                      child: ListView.builder(
                        itemCount: _activities.length,
                        itemBuilder: (context, index) {
                          final activity = _activities[index];
                          return Card(
                            margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                            child: ListTile(
                              leading: CircleAvatar(
                                backgroundColor: _getStatusColor(activity.estado),
                                child: const Icon(Icons.work, color: Colors.white, size: 20),
                              ),
                              title: Text(activity.cliente ?? "Sin Cliente", style: const TextStyle(fontWeight: FontWeight.bold)),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text("${activity.direccion}"),
                                  Text("Ticket: ${activity.ticketId}", style: const TextStyle(fontSize: 12)),
                                ],
                              ),
                              trailing: const Icon(Icons.chevron_right),
                              onTap: () async {
                                await Navigator.push(
                                  context,
                                  MaterialPageRoute(builder: (_) => ActivityDetailScreen(activity: activity)),
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
          if (!_isLoading && pendingCount == 0 && _activities.isNotEmpty)
             Container(
               width: double.infinity,
               padding: const EdgeInsets.all(16),
               color: Colors.white, // Inset
               child: ElevatedButton.icon(
                 style: ElevatedButton.styleFrom(
                   backgroundColor: Colors.black,
                   foregroundColor: Colors.white,
                   padding: const EdgeInsets.all(16)
                 ),
import 'signature_screen.dart'; // Add import at top manually or here if lazy
// Actually better to replace TODO block 

               onPressed: () {
                   Navigator.push(context, MaterialPageRoute(builder: (_) => const SignatureScreen()));
               }, 
                 icon: const Icon(Icons.draw),
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
              Text(count.toString(), style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: color)),
              Text(label, style: TextStyle(color: color, fontSize: 12)),
            ],
          ),
        ),
      ),
    );
  }
}
