# 🎓 PROYECTO CAPSTONE
Proyecto de Titulación Duoc UC 2026


## Colaboradores
- Leandro Caceres Mayorinca
- Edinson Delgado Reinoso

🏘️ UrbanLink - Sistema de Gestión para Juntas de Vecinos

Proyecto de desarrollo web - Plataforma para la administración y comunicación comunitaria.

## 📋 Descripción

UrbanLink es una plataforma web para la gestión de juntas de vecinos, orientada a digitalizar y centralizar los procesos comunitarios como administración de usuarios, vecinos, viviendas, certificados, reservas, postulaciones y comunicación.

El sistema fue desarrollado utilizando **Django** como framework backend, **HTML5 y CSS3** para la interfaz de usuario, y **Supabase con PostgreSQL** como servicio de base de datos y almacenamiento.

Además, incorpora **ReportLab** para la generación de documentos PDF, permitiendo crear certificados de residencia de forma automática.

La plataforma busca mejorar la organización de la información, optimizar la gestión administrativa y facilitar la comunicación entre vecinos y directiva.

## 1. Clonar repositorio

```bash
git clone https://github.com/LeandroCaceresM/Capstone26.git
cd Capstone26
```


## Acceder al Proyecto 

```bash
cd Capstone26\FASE 2\Evidencia Proyecto\Pagina_Capstone\Proyecto\core
```

## Ejecutar:

```bash
py -m pip install -r requirements.txt
```

## 4. Configurar variables de entorno

## Crear archivo:

```bash
.env
```

## Agregar credenciales de Supabase:

```bash
SUPABASE_URL=

SUPABASE_ANON_KEY=

SUPABASE_SERVICE_ROLE_KEY=
```

## 5. Ejecutar aplicación

```bash
python manage.py runserver
```
La aplicación estará disponible en:

http://127.0.0.1:8000/
