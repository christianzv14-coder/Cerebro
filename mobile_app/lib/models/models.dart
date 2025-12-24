class User {
  final int id;
  final String email;
  final String tecnicoNombre;
  final String role;

  User({required this.id, required this.email, required this.tecnicoNombre, required this.role});

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      email: json['email'],
      tecnicoNombre: json['tecnico_nombre'],
      role: json['role'],
    );
  }
}

class Activity {
  final String ticketId;
  final String fecha;
  final String tecnicoNombre;
  final String? patente;
  final String? cliente;
  final String? direccion;
  final String? tipoTrabajo;
  late final String estado;
  final String? horaInicio;
  final String? horaFin;
  final String? resultadoMotivo;
  final String? observacion;

  Activity({
    required this.ticketId,
    required this.fecha,
    required this.tecnicoNombre,
    this.patente,
    this.cliente,
    this.direccion,
    this.tipoTrabajo,
    required this.estado,
    this.horaInicio,
    this.horaFin,
    this.resultadoMotivo,
    this.observacion,
  });

  factory Activity.fromJson(Map<String, dynamic> json) {
    return Activity(
      ticketId: json['ticket_id'],
      fecha: json['fecha'],
      tecnicoNombre: json['tecnico_nombre'],
      patente: json['patente'],
      cliente: json['cliente'],
      direccion: json['direccion'],
      tipoTrabajo: json['tipo_trabajo'],
      estado: json['estado'],
      horaInicio: json['hora_inicio'],
      horaFin: json['hora_fin'],
      resultadoMotivo: json['resultado_motivo'],
      observacion: json['observacion'],
    );
  }
  
  bool get isPending => estado == 'PENDIENTE';
  bool get isInProgress => estado == 'EN_CURSO';
  bool get isClosed => ['EXITOSO', 'FALLIDO', 'REPROGRAMADO'].contains(estado);
}
