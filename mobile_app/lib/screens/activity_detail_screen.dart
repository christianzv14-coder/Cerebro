import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/api_service.dart';

class ActivityDetailScreen extends StatefulWidget {
  final Activity activity;
  
  const ActivityDetailScreen({super.key, required this.activity});

  @override
  State<ActivityDetailScreen> createState() => _ActivityDetailScreenState();
}

class _ActivityDetailScreenState extends State<ActivityDetailScreen> {
  late Activity _activity;
  final ApiService _api = ApiService();
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _activity = widget.activity;
  }
  
  void _start() async {
    setState(() => _isLoading = true);
    try {
      final updated = await _api.startActivity(_activity.ticketId);
      setState(() => _activity = updated);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Actividad Iniciada')));
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red));
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _showFinishDialog() {
    String? motivo; // For Dropdown
    final obsController = TextEditingController();
    String resultado = 'EXITOSO'; // Default
    
    // Simple hardcoded reasons for MVP
    final reasons = ['CLIENTE_AUSENTE', 'DIRECCION_INCORRECTA', 'FALLA_TECNICA', 'RECHAZO_CLIENTE', 'OTRO'];

    showDialog(context: context, builder: (ctx) {
      return StatefulBuilder(
        builder: (context, setStateDialog) {
          return AlertDialog(
            title: const Text('Finalizar Actividad'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                   // Result Type Toggle
                   Row(
                     children: [
                       Expanded(child: ChoiceChip(label: const Text('EXITOSO'), selected: resultado == 'EXITOSO', onSelected: (b) => setStateDialog(() => resultado = 'EXITOSO'))),
                       const SizedBox(width: 5),
                       Expanded(child: ChoiceChip(label: const Text('FALLIDO'), selected: resultado == 'FALLIDO', onSelected: (b) => setStateDialog(() => resultado = 'FALLIDO'))),
                     ],
                   ),
                   const SizedBox(height: 10),
                   
                   if (resultado == 'FALLIDO')
                     DropdownButtonFormField<String>(
                       decoration: const InputDecoration(labelText: 'Motivo Fallo'),
                       items: reasons.map((r) => DropdownMenuItem(value: r, child: Text(r))).toList(),
                       onChanged: (v) => setStateDialog(() => motivo = v),
                     ),
                     
                   const SizedBox(height: 10),
                   TextField(
                     controller: obsController,
                     decoration: const InputDecoration(labelText: 'Observación', hintText: 'Opcional'),
                     maxLines: 2,
                   )
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
              ElevatedButton(
                onPressed: () {
                   if (resultado == 'FALLIDO' && motivo == null) {
                     ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Motivo obligatorio para Fallido')));
                     return;
                   }
                   Navigator.pop(context); // Close dialog
                   _finish(resultado, motivo, obsController.text);
                },
                child: const Text('Confirmar'),
              )
            ],
          );
        }
      );
    });
  }
  
  void _finish(String res, String? mot, String? obs) async {
    setState(() => _isLoading = true);
    try {
      final updated = await _api.finishActivity(_activity.ticketId, res, mot, obs);
      setState(() => _activity = updated);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Actividad Cerrada Correctamente')));
      Navigator.pop(context); // Go back to Home
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red));
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Detalle Actividad')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
             _infoRow('Ticket', _activity.ticketId),
             _infoRow('Cliente', _activity.cliente),
             _infoRow('Dirección', _activity.direccion),
             _infoRow('Patente', _activity.patente),
             _infoRow('Tipo Trabajo', _activity.tipoTrabajo),
             const SizedBox(height: 20),
             _infoRow('Estado', _activity.estado, isBold: true),
             if (_activity.horaInicio != null) _infoRow('Inicio', _activity.horaInicio),
             if (_activity.horaFin != null) _infoRow('Fin', _activity.horaFin),
             
             const SizedBox(height: 40),
             
             if (_activity.isPending)
               SizedBox(
                 width: double.infinity,
                 child: ElevatedButton(
                   onPressed: _isLoading ? null : _start,
                   style: ElevatedButton.styleFrom(backgroundColor: Colors.blue, foregroundColor: Colors.white, padding: const EdgeInsets.all(20)),
                   child: _isLoading ? const CircularProgressIndicator() : const Text('COMENZAR VIAJE / TRABAJO', style: TextStyle(fontSize: 18)),
                 ),
               ),
               
             if (_activity.isInProgress)
               SizedBox(
                 width: double.infinity,
                 child: ElevatedButton(
                   onPressed: _isLoading ? null : _showFinishDialog,
                   style: ElevatedButton.styleFrom(backgroundColor: Colors.green, foregroundColor: Colors.white, padding: const EdgeInsets.all(20)),
                   child: _isLoading ? const CircularProgressIndicator() : const Text('FINALIZAR TAREA', style: TextStyle(fontSize: 18)),
                 ),
               ),
               
             if (_activity.isClosed)
               const Center(
                 child: Text('Actividad Cerrada', style: TextStyle(fontSize: 20, color: Colors.grey, fontWeight: FontWeight.bold)),
               )
          ],
        ),
      ),
    );
  }
  
  Widget _infoRow(String label, String? value, {bool isBold = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 100, child: Text(label, style: const TextStyle(color: Colors.grey))),
          Expanded(child: Text(value ?? '--', style: TextStyle(fontSize: 16, fontWeight: isBold ? FontWeight.bold : FontWeight.normal))),
        ],
      ),
    );
  }
}
