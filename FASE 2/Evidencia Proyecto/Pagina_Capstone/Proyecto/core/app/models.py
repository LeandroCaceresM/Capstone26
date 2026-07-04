from django.db import models

#Cargo de un vecino en la junta: Presidente, Tesorero, Secretario, Vecino.
class Cargo(models.Model):
    id_cargo = models.UUIDField(primary_key=True)
    nombre_cargo = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cargo'


#Certificado de residencia que vecinos pueden sacar, el presidente sube su "firma digital" y despues el vecino simplemente lo descarga
class CertificadoDeResidencia(models.Model):
    id_certificado = models.UUIDField(primary_key=True)
    fecha_emision = models.DateTimeField()
    id_vecino = models.ForeignKey('Vecino', models.DO_NOTHING, db_column='id_vecino')
    id_vecino2 = models.ForeignKey('Vecino', models.DO_NOTHING, db_column='id_vecino2', related_name='certificadoderesidencia_id_vecino2_set')
    numero_certificado = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'certificado_de_residencia'

#Comuna de una region
class Comuna(models.Model):
    id_comuna = models.UUIDField(primary_key=True)
    nom_comuna = models.CharField(max_length=100)
    id_region = models.ForeignKey('Region', models.DO_NOTHING, db_column='id_region')

    class Meta:
        managed = False
        db_table = 'comuna'
        

#Sector de una comuna
class Sector(models.Model):
    id_sector = models.UUIDField(primary_key=True)
    nombre_sector = models.CharField(max_length=150)
    id_comuna = models.ForeignKey("Comuna", models.DO_NOTHING, db_column="id_comuna")

    class Meta:
        managed = False
        db_table = "sector"

#Directiva que corresponde a x junta durante x fecha
class Directiva(models.Model):
    id_directiva = models.UUIDField(primary_key=True)
    fecha_inicio_direct = models.DateField()
    fecha_fin_direct = models.DateField()
    id_junta = models.ForeignKey('Juntavecinos', models.DO_NOTHING, db_column='id_junta')

    class Meta:
        managed = False
        db_table = 'directiva'

#Estado de proceso de una solicitud: Aprobada, Cancelada, En Proceso.
class EstadoSolicitud(models.Model):
    id_est = models.UUIDField(primary_key=True)
    nomb_est_sol = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'estado_solicitud'

#Historia de cargo de un vecino por ej: o sea si fue presidente de junta en algun momento pero ya no 
class HistCargo(models.Model):
    id_hist_cargo = models.UUIDField(primary_key=True)

    fecha_cargo_tentativa = models.DateField()
    fecha_cargo_fin = models.DateField(blank=True, null=True)
    fecha_cargo_fin_real = models.DateField(blank=True, null=True)

    id_vecino = models.ForeignKey('Vecino', models.DO_NOTHING, db_column='id_vecino')
    id_cargo = models.ForeignKey(Cargo, models.DO_NOTHING, db_column='id_cargo')
    id_directiva = models.ForeignKey(Directiva, models.DO_NOTHING, db_column='id_directiva')

    class Meta:
        managed = False
        db_table = 'hist_cargo'

#Historial de estado solicitud, por ej: se subio el 2 (En proceso) y se aprobó el 17 (Aprobada)
class HistEstSol(models.Model):
    pk = models.CompositePrimaryKey('id_solicitud', 'id_est')
    fecha_cb_estado = models.DateTimeField()
    id_solicitud = models.ForeignKey('Solicitud', models.DO_NOTHING, db_column='id_solicitud')
    id_est = models.ForeignKey(EstadoSolicitud, models.DO_NOTHING, db_column='id_est')

    class Meta:
        managed = False
        db_table = 'hist_est_sol'

#Para saber si un vecino sigue viviendo ahi o si es arrendatario, o en caso de que un vecino se transladó a otra parte
class HistVivienda(models.Model):
    id_hist_vivienda = models.UUIDField(primary_key=True)
    fecha_ini = models.DateField()
    fecha_ter = models.DateField(blank=True, null=True)
    id_vivienda = models.ForeignKey('Vivienda', models.DO_NOTHING, db_column='id_vivienda')
    id_vecino = models.ForeignKey('Vecino', models.DO_NOTHING, db_column='id_vecino')

    class Meta:
        managed = False
        db_table = 'hist_vivienda'

#La junta de vecinos en si
class Juntavecinos(models.Model):
    id_junta = models.UUIDField(primary_key=True)
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=300)
    fecha_creacion = models.DateTimeField()
    id_sector = models.ForeignKey("Sector", models.DO_NOTHING, db_column="id_sector")

    class Meta:
        managed = False
        db_table = 'juntavecinos'

#Regiones de Chile
class Region(models.Model):
    id_region = models.UUIDField(primary_key=True)
    nom_region = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'region'

#Rol de un vecino en el sf (Usuario, Admin, Superadmin)
class Rol(models.Model):
    id_rol = models.UUIDField(primary_key=True)
    nombre_rol = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rol'

#Solicitudes que pueden hacer los vecinos
class Solicitud(models.Model):
    id_solicitud = models.UUIDField(primary_key=True)
    fecha_solicitud = models.DateTimeField()
    estado = models.CharField(max_length=50)
    descripcion = models.TextField()
    comentario_presidente = models.TextField(blank=True, null=True)
    id_vecino = models.ForeignKey('Vecino', models.DO_NOTHING, db_column='id_vecino')
    id_tsolicitud = models.ForeignKey('Tiposolicitud', models.DO_NOTHING, db_column='id_tsolicitud')

    class Meta:
        managed = False
        db_table = 'solicitud'

#Tipo de discapacidad que puede tener un vecino (Adulto Mayor, ElectroDependiente y Movilidad Reducida) puede tener los 3
class TipoDiscapacidad(models.Model):
    id_tipo_discap = models.UUIDField(primary_key=True)
    nom_tipo_discap = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'tipo_discapacidad'

#Tipo de solicitud ya sea Reserva de espacios, Autorizacion, Reporte, Ayuda, Postulacion, Registro, Reclamo
class Tiposolicitud(models.Model):
    id_tsolicitud = models.UUIDField(primary_key=True)
    tipo_solicitud = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'tiposolicitud'

#El vecino en si
class Vecino(models.Model):
    id_vecino = models.UUIDField(primary_key=True)
    supabase_uid = models.UUIDField(unique=True, blank=True, null=True)    

    rut = models.CharField(max_length=12)
    pri_nombre = models.CharField(max_length=50)
    seg_nombre = models.CharField(max_length=50, blank=True, null=True)
    apell_paterno = models.CharField(max_length=50)
    apell_materno = models.CharField(max_length=50)
    correo = models.CharField(max_length=60, blank=True, null=True)
    telefono = models.BigIntegerField()
    fecha_de_nacimiento = models.DateField()
    vigencia = models.CharField(max_length=1)
    fecha_registro = models.DateTimeField()
    firma_digital = models.CharField(max_length=255, blank=True, null=True)
    id_rol = models.ForeignKey(Rol, models.DO_NOTHING, db_column='id_rol')

    class Meta:
        managed = False
        db_table = 'vecino'


class VecinoDiscap(models.Model):
    pk = models.CompositePrimaryKey('id_tipo_discap', 'id_vecino')
    fecha_registro_discap = models.DateField()
    id_tipo_discap = models.ForeignKey(TipoDiscapacidad, models.DO_NOTHING, db_column='id_tipo_discap')
    id_vecino = models.ForeignKey(Vecino, models.DO_NOTHING, db_column='id_vecino')

    class Meta:
        managed = False
        db_table = 'vecino_discap'

#Domicilio que corresponde a un vecino, en caso de que viva en dpto entonces tambien se le solicita numero de block y dpto
class Vivienda(models.Model):
    id_vivienda = models.UUIDField(primary_key=True)
    tipo_vivienda = models.CharField(max_length=1)
    nombre_calle = models.CharField(max_length=150)
    numero_calle = models.IntegerField()
    num_block = models.IntegerField(blank=True, null=True)
    num_dpto = models.IntegerField(blank=True, null=True)

    observacion = models.CharField(max_length=255, blank=True, null=True)
    vigencia = models.CharField(max_length=1, default="S")

    id_junta = models.ForeignKey(Juntavecinos, models.DO_NOTHING, db_column='id_junta')

    class Meta:
        managed = False
        db_table = 'vivienda'

class Noticia(models.Model):
    id_noticia = models.UUIDField(primary_key=True)
    titulo = models.CharField(max_length=120)
    descripcion = models.TextField()
    fecha_publicacion = models.DateTimeField()
    vigencia = models.CharField(max_length=1, default="S")

    id_junta = models.ForeignKey(
        Juntavecinos,
        on_delete=models.CASCADE,
        db_column="id_junta"
    )

    id_vecino = models.ForeignKey(
        Vecino,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_vecino"
    )

    class Meta:
        db_table = "noticia"
        
        
class Evento(models.Model):
    id_evento = models.UUIDField(primary_key=True)
    titulo = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True, null=True)
    fecha_evento = models.DateTimeField()
    lugar = models.CharField(max_length=150, blank=True, null=True)
    vigencia = models.CharField(max_length=1, default="S")

    id_junta = models.ForeignKey(
        Juntavecinos,
        on_delete=models.CASCADE,
        db_column="id_junta"
    )

    id_vecino = models.ForeignKey(
        Vecino,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_vecino"
    )

    class Meta:
        db_table = "evento"