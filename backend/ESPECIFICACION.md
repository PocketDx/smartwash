# Especificación Técnica — Backend (Django)

## Proyecto

**GESECA** — Sistema Web Para La Gestión Y Seguimiento De Campañas De Promoción De La Salud Y Prevención De La Enfermedad

Proyecto académico de la materia **Análisis y Diseño de Sistemas**.

## Objetivo del sistema

Desarrollar un sistema de información web para gestionar y evaluar campañas de promoción de la salud y prevención de la enfermedad, mediante la caracterización de actividades, población beneficiaria, coberturas e indicadores.

## Rol de este backend

Este backend expone una **API REST** consumida por el frontend (Next.js), encargada de la lógica de negocio, persistencia de datos y control de acceso del sistema.

## Stack tecnológico

- **Lenguaje:** Python 3.12+
- **Framework:** Django 5.x
- **API:** Django REST Framework (DRF)
- **Base de datos:** PostgreSQL
- **Autenticación:** JWT (`djangorestframework-simplejwt`) o sesiones, según se defina en el diseño de autenticación
- **Entorno virtual:** `venv` o `poetry`
- **Variables de entorno:** `django-environ` / `.env`
- **Documentación de API:** `drf-spectacular` (OpenAPI/Swagger)

## Estructura de carpetas propuesta

```
backend/
├── config/                 # Configuración del proyecto Django (settings, urls, wsgi/asgi)
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── campañas/            # Gestión de campañas de salud
│   ├── actividades/         # Caracterización de actividades por campaña
│   ├── poblacion/           # Población beneficiaria
│   ├── coberturas/          # Cálculo y seguimiento de coberturas
│   ├── indicadores/         # Indicadores de gestión y evaluación
│   └── usuarios/            # Autenticación y roles del sistema
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── manage.py
└── .env.example
```

Cada app de Django debe seguir la convención estándar (`models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `tests/`).

## Módulos funcionales esperados

Basado en el objetivo del sistema, se prevén los siguientes módulos (sujetos a ajuste según el análisis de requerimientos):

1. **Campañas:** registro, edición y ciclo de vida de campañas de promoción/prevención.
2. **Actividades:** caracterización de actividades realizadas dentro de cada campaña.
3. **Población beneficiaria:** registro y clasificación de la población atendida.
4. **Coberturas:** cálculo de cobertura alcanzada vs. población objetivo.
5. **Indicadores:** definición y seguimiento de indicadores de gestión y evaluación.
6. **Usuarios y roles:** gestión de usuarios del sistema con permisos diferenciados (administrador, gestor de campaña, consulta, etc.).
7. **Reportes:** generación de reportes de seguimiento y evaluación.

## Convenciones de la API

- Prefijo de rutas: `/api/v1/`
- Formato de respuesta: JSON
- Nomenclatura de endpoints en plural y en español o inglés (definir y mantener consistencia, por ejemplo `/api/v1/campanas/`)
- Uso de serializers de DRF para validación de entrada y salida
- Paginación estándar de DRF (`PageNumberPagination`) en listados
- Manejo de errores mediante respuestas HTTP estándar (400, 401, 403, 404, 500) con estructura JSON consistente

## Buenas prácticas a seguir

- Separar `settings` por entorno (`base`, `dev`, `prod`)
- No exponer credenciales ni datos sensibles en el repositorio (usar `.env`)
- Escribir migraciones versionadas y revisadas antes de aplicarlas
- Cubrir con pruebas (`pytest-django` o `django.test`) los módulos críticos: campañas, coberturas e indicadores
- Documentar los endpoints mediante OpenAPI/Swagger
- Aplicar principios de diseño vistos en la materia (normalización de base de datos, separación de responsabilidades, modularidad por dominio)

## Pendiente de definir

- Diagrama entidad-relación definitivo de campañas, actividades, población, coberturas e indicadores
- Mecanismo de autenticación definitivo (JWT vs. sesiones)
- Roles y permisos específicos por tipo de usuario
- Requerimientos de reportería (formatos de exportación, periodicidad)
