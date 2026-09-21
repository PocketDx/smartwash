# plot.md — contexto de SmartWash para agentes de IA

Lee este archivo antes de escribir codigo. Las instrucciones operativas estan en
[AGENTS.md](AGENTS.md); los pasos de instalacion, en [README.md](README.md).

## Que es SmartWash

Sistema web de **gestion operativa y fidelizacion para una lavanderia**. Proyecto
academico universitario (UFPS). El backlog vive en Jira, proyecto `SCRUM`
(https://smartwashufps.atlassian.net).

Dominio, segun las epicas de Jira:

| Epica | Dominio |
|-------|---------|
| EP01 | Usuarios y roles (administrador, recepcionista, operario) |
| EP02 | Clientes |
| EP03 | Catalogo de servicios y tarifas |
| EP04 | Ordenes y prendas |
| EP05 | Trazabilidad y estados de la orden |
| EP06 | Incidencias y postventa |
| EP07 | Pagos |
| EP08 | Fidelizacion (puntos, promociones, segmentos) |
| EP09 | Notificaciones |
| EP10 | Indicadores y reportes |

## Stack

- **Backend:** Django 6.1 + Django REST Framework. Python 3.12+.
- **Base de datos:** SQLite en local; PostgreSQL mas adelante via `DATABASE_URL`.
- **Frontend:** Next.js 16 (App Router) en **TypeScript**.
- **Estilos:** Tailwind CSS v4.
- **Autenticacion:** sesiones nativas de Django + cookies. Nada de JWT ni OAuth.
- **Despliegue:** el frontend va a Vercel. El backend todavia no tiene destino.

## Organizacion del repositorio

```
smartwash/
├── backend/
│   ├── config/          # settings.py (unico, por entorno), urls.py, wsgi/asgi
│   ├── accounts/        # modelo User con rol + endpoints de autenticacion
│   ├── core/            # health check y utilidades transversales
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/             # App Router: page.tsx (dashboard), login/page.tsx
│   ├── lib/api.ts       # cliente HTTP hacia Django + tipos de la API
│   ├── next.config.ts   # rewrite /api/* -> Django
│   └── .env.example
├── plot.md              # este archivo
├── AGENTS.md            # reglas de trabajo para agentes
└── README.md            # como levantar el proyecto
```

Cada dominio nuevo del backlog entra como **una app de Django** bajo `backend/`
(`clientes/`, `catalogo/`, `ordenes/`, `pagos/`, `fidelizacion/`,
`notificaciones/`). No existen todavia: se crean cuando se implemente su historia.
No crees apps vacias "para despues".

## Como se comunican frontend y backend

El navegador **nunca** llama a Django directamente. `frontend/next.config.ts`
reenvia `/api/:path*` al backend (`BACKEND_URL`):

```
navegador  ──>  Next.js (:3000)  ──rewrite──>  Django (:8000)
```

Consecuencias, que hay que respetar al agregar endpoints:

- La cookie de sesion es **first-party** del origen de Next. No hay CORS ni
  `SameSite=None`. No agregues `django-cors-headers`.
- Django si ve el header `Origin` del frontend, por eso necesita
  `DJANGO_CSRF_TRUSTED_ORIGINS`.
- **Las rutas de la API van sin barra final** (`/api/auth/login`, no
  `/api/auth/login/`). Next 16 responde 308 y elimina la barra antes del rewrite,
  lo que rompe los POST. El admin de Django (`/admin/`) no pasa por el rewrite y
  conserva su barra.
- Peticiones de escritura desde el navegador requieren el header `X-CSRFToken`.
  `lib/api.ts` ya lo resuelve: usalo en lugar de `fetch` directo.

## Endpoints existentes

| Metodo | Ruta | Permiso | Que hace |
|--------|------|---------|----------|
| GET  | `/api/health`       | publico | Verifica app + base de datos |
| POST | `/api/auth/login`   | publico | Crea la sesion. Requiere CSRF |
| POST | `/api/auth/logout`  | sesion  | Cierra la sesion |
| GET  | `/api/auth/me`      | sesion  | Usuario actual. Siembra la cookie `csrftoken` |

`/api/auth/me` responde **403** si no hay sesion; el frontend lo interpreta como
"no autenticado".

## Convenciones

- Codigo, comentarios y mensajes de commit en espanol; nombres de simbolos en
  ingles solo si ya lo estaban.
- **Backend:** una app por dominio, con `models.py`, `serializers.py`, `views.py`,
  `urls.py`, `admin.py`, `tests.py`. Permisos por defecto: `IsAuthenticated`
  (definido en `REST_FRAMEWORK`); usa `AllowAny` explicito para lo publico.
- **Frontend:** Server Components por defecto; `"use client"` solo cuando haya
  interactividad. Todo acceso a la API pasa por `lib/api.ts`. Alias `@/` a la raiz
  de `frontend/`.
- El tipo de cada respuesta de la API se declara en `lib/api.ts` (`User`, `Rol`,
  etc.). Nada de `any`.
- Variables de entorno: toda variable nueva se documenta en el `.env.example`
  correspondiente. Nunca se commitea un `.env` real.

## Pruebas e integracion continua

```bash
cd backend && .venv/bin/python manage.py test     # macOS / Linux
cd backend && .venv\Scripts\python manage.py test # Windows
```

`.github/workflows/ci.yml` corre en cada PR a `dev` y a `main`:

| Job | Que verifica |
|-----|--------------|
| Backend | Que no falten migraciones (`makemigrations --check`) y que pasen las pruebas |
| Frontend | `npm run lint` y `npm run build`, que incluye el chequeo de tipos |

No hay despliegue automatico del backend porque la plataforma aun no se elige.

Runner nativo de Django (`django.test`), sin pytest. Cada historia se cierra con
la prueba de sus escenarios de aceptacion (T7 / SCRUM-54). El frontend no tiene
pruebas unitarias: se valida con pruebas funcionales.

## Decisiones tecnicas tomadas

| Decision | Motivo |
|----------|--------|
| Sesiones de Django, no JWT | Requisito del equipo; menos piezas y CSRF nativo |
| `AUTH_USER_MODEL = accounts.User` desde el dia 1 | Cambiarlo despues de la primera migracion es costoso |
| Campo `rol` persistido pero **sin enforcement** | T3 (SCRUM-55) lo pide; el control de acceso es T8 (SCRUM-57) |
| Rewrite de Next en vez de CORS | Cookies first-party, una sola configuracion, funciona igual en Vercel |
| `settings.py` unico parametrizado por `.env` | Lo unico que varia hoy es `DEBUG`; un split base/dev/prod seria ruido |
| `dj-database-url` | Pasar a PostgreSQL es definir `DATABASE_URL`, sin tocar codigo |
| SQLite versionado como ignorado | Cada integrante genera su propia base local |
| Tailwind v4 | Ya venia en el scaffolding de Next; no agrega trabajo |
| Sin `drf-spectacular`, sin Docker, sin Redux | No hay necesidad todavia |

## Pendiente

**Infraestructura**

- **Decision pendiente: donde se despliega el backend.** Vercel hospeda Next.js,
  **no** Django. El codigo ya esta listo para cualquier PaaS (gunicorn, WhiteNoise,
  `psycopg`, `DATABASE_URL`), pero la plataforma no se ha elegido. Hasta que se
  elija no hay CD del backend: el CI solo corre pruebas.

  Lo que hara falta el dia que se decida:
  - Aprovisionar PostgreSQL y definir `DATABASE_URL`.
  - Definir `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS` con
    el dominio del backend y `DJANGO_CSRF_TRUSTED_ORIGINS` con el de Vercel.
  - Build: `pip install -r requirements.txt && python manage.py collectstatic
    --no-input && python manage.py migrate`. Arranque: `gunicorn config.wsgi:application`.
  - Apuntar `BACKEND_URL` en Vercel al backend desplegado (y redesplegar, porque
    se lee en build time).

  Nota para la eleccion: el Postgres gratuito de Render **expira a los 30 dias** y
  se borra a los 44, lo que no cubre un semestre. Si se elige Render, conviene la
  base en otro proveedor con plan gratuito permanente.
- **`BACKEND_URL` todavia no esta definida en Vercel.** Hasta que exista un
  backend publico al que apuntar, el frontend desplegado no puede autenticar:
  `/` redirige a `/login` y el login avisa que no hay conexion. Es degradacion
  controlada, no un fallo. El detalle de la configuracion de Vercel esta en el
  README; no hay `vercel.json` porque todo vive en el panel.
- Recuperacion de contrasena por correo (HU02): falta backend de email.
- Expiracion de sesion por inactividad y control de acceso por rol (T8/SCRUM-57).

**Funcionalidad**: todas las epicas EP02–EP10 y las HU de EP01 salvo el login.
Ninguna entidad de negocio (cliente, servicio, tarifa, orden, prenda) esta modelada.
