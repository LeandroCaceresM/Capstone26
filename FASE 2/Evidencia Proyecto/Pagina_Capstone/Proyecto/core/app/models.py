# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Cargo(models.Model):
    id_cargo = models.UUIDField(primary_key=True)
    nombre_cargo = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cargo'


class Certificado(models.Model):
    id_certificado = models.UUIDField(primary_key=True)
    fecha_emision = models.DateTimeField()
    vecino_id_vecino = models.ForeignKey('Vecino', models.DO_NOTHING, db_column='vecino_id_vecino')
    vecino_id_vecino2 = models.ForeignKey('Vecino', models.DO_NOTHING, db_column='vecino_id_vecino2', related_name='certificado_vecino_id_vecino2_set', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'certificado'


class Comuna(models.Model):
    id_comuna = models.UUIDField(primary_key=True)
    nom_comuna = models.CharField(max_length=100)
    region_id_region = models.ForeignKey('Region', models.DO_NOTHING, db_column='region_id_region')

    class Meta:
        managed = False
        db_table = 'comuna'


class EstadoSolicitud(models.Model):
    id_est = models.UUIDField(primary_key=True)
    nomb_est_sol = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'estado_solicitud'


class HistEstSol(models.Model):
    id_historial = models.UUIDField(primary_key=True)
    fecha_cb_estado = models.DateTimeField()
    solicitud_id_solicitud = models.ForeignKey('Solicitud', models.DO_NOTHING, db_column='solicitud_id_solicitud')
    estado_solicitud_id_est = models.ForeignKey(EstadoSolicitud, models.DO_NOTHING, db_column='estado_solicitud_id_est')

    class Meta:
        managed = False
        db_table = 'hist_est_sol'


class JuntaVecinos(models.Model):
    id_junta = models.UUIDField(primary_key=True)
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=300, blank=True, null=True)
    fecha_creacion = models.DateTimeField()
    sector_id_sector = models.ForeignKey('Sector', models.DO_NOTHING, db_column='sector_id_sector')

    class Meta:
        managed = False
        db_table = 'junta_vecinos'


class Region(models.Model):
    id_region = models.UUIDField(primary_key=True)
    nom_region = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'region'


class Rol(models.Model):
    id_rol = models.UUIDField(primary_key=True)
    nombre_rol = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rol'


class Sector(models.Model):
    id_sector = models.UUIDField(primary_key=True)
    nom_sector = models.CharField(max_length=100)
    comuna_id_comuna = models.ForeignKey(Comuna, models.DO_NOTHING, db_column='comuna_id_comuna')

    class Meta:
        managed = False
        db_table = 'sector'


class Solicitud(models.Model):
    id_solicitud = models.UUIDField(primary_key=True)
    fecha_solicitud = models.DateTimeField()
    comentario = models.CharField(max_length=500, blank=True, null=True)
    vecino_id_vecino = models.ForeignKey('Vecino', models.DO_NOTHING, db_column='vecino_id_vecino')
    tiposolicitud_id_tsolicitud = models.ForeignKey('TipoSolicitud', models.DO_NOTHING, db_column='tiposolicitud_id_tsolicitud')
    estado_actual = models.ForeignKey(EstadoSolicitud, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'solicitud'


class TipoSolicitud(models.Model):
    id_tsolicitud = models.UUIDField(primary_key=True)
    tipo_solicitud = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'tipo_solicitud'


class Vecino(models.Model):
    id_vecino = models.UUIDField(primary_key=True)
    rut = models.CharField(unique=True, max_length=12)
    pri_nombre = models.CharField(max_length=50)
    seg_nombre = models.CharField(max_length=50, blank=True, null=True)
    apell_paterno = models.CharField(max_length=50)
    apell_materno = models.CharField(max_length=50)
    correo = models.CharField(unique=True, max_length=60)
    telefono = models.CharField(max_length=20)
    direccion = models.CharField(max_length=300)
    fecha_registro = models.DateTimeField()
    juntavecinos_id_junta = models.ForeignKey(JuntaVecinos, models.DO_NOTHING, db_column='juntavecinos_id_junta')
    cargo_id_cargo = models.ForeignKey(Cargo, models.DO_NOTHING, db_column='cargo_id_cargo', blank=True, null=True)
    rol_id_rol = models.ForeignKey(Rol, models.DO_NOTHING, db_column='rol_id_rol')
    vigencia = models.BooleanField(db_comment='vigencia del besino xd')

    class Meta:
        managed = False
        db_table = 'vecino'
