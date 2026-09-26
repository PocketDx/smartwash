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
│   ├── clientes/        # Cliente (EP02)
│   ├── catalogo/        # Servicio y Tarifa (EP03)
│   ├── ordenes/         # Orden y Prenda (EP04, EP05)
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

Cada dominio nuevo del backlog entra como **una app de Django** bajo `backend/`.
Ya existen `clientes/`, `catalogo/` y `ordenes/`, con sus modelos pero **sin
endpoints**: T2 (SCRUM-51) pedia solo las entidades nucleo. Faltan `pagos/`,
`fidelizacion/` y `notificaciones/`: se crean cuando se implemente su historia.
No crees apps vacias "para despues".

### Modelo de datos

Sigue el modelo relacional acordado por el equipo. Solo estan las entidades
nucleo (T2); el resto de tablas del modelo entra con su historia.

| Modelo | App | Notas |
|--------|-----|-------|
| `Cliente` | clientes | `documento` unico. `clasificacion` la actualiza RF38 |
| `TipoPrenda` | catalogo | Camisa, pantalon, cobija. La tarifa depende de esto |
| `Servicio` | catalogo | Lavado, planchado, lavado en seco |
| `Tarifa` | catalogo | Por `(tipo_prenda, servicio)`, con vigencia. Una sola vigente por par |
| `Orden` | ordenes | `codigo` unico y publico. `operario` es nulo hasta HU10 |
| `Prenda` | ordenes | Pertenece a una orden y tiene un `TipoPrenda` |
| `OrdenServicio` | ordenes | Que servicios recibe cada prenda, con `valor_aplicado` congelado |

Una prenda puede recibir **varios servicios**: una camisa va a lavado y a
planchado. Por eso existe `OrdenServicio` y no un FK directo.

Todo modelo de dominio hereda de `core.models.ModeloConAutoria`, que agrega
`creado_por` / `actualizado_por` ademas de los timestamps (T3). **Cada vista que
escriba debe llamar a `registrar_autoria(request.user)` antes de `save()`**; el
Django Admin ya lo hace via `core.admin.AutoriaAdminMixin`.

Las cuatro cuentas de prueba se crean con `manage.py seed_usuarios` (ver README).
El comando se niega a correr con `DEBUG=False`.

Reglas que valen para todo el dominio:

- **El dinero va en `DecimalField`, nunca en `FloatField`.** Un float redondea y
  el total de una orden queda mal.
- **Los precios no se releen, se congelan.** `OrdenServicio.valor_aplicado` copia
  el valor de la tarifa al registrar la orden. Si manana sube el precio, lo ya
  cobrado no cambia.
- Las reglas de integridad se declaran como `constraints` en el modelo, no solo
  en el serializer: dos peticiones simultaneas se saltan una validacion que solo
  vive en Python.
- `on_delete` se elige a conciencia: `PROTECT` para lo que no se puede borrar si
  ya se uso (cliente con ordenes, tarifa ya cobrada), `CASCADE` para lo que no
  existe sin su padre (prendas de una orden), `SET_NULL` para el operario.

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

## Pruebas

```bash
cd backend && .venv/bin/python manage.py test     # macOS / Linux
cd backend && .venv\Scripts\python manage.py test # Windows
```

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

- Desplegar el backend: Vercel hospeda Next.js, **no** Django. Falta elegir
  destino (Render, Railway, Fly.io o similar), aprovisionar PostgreSQL gestionado,
  definir `DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`,
  `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS` con el dominio de Vercel,
  agregar `psycopg[binary]` a `requirements.txt`, servir estaticos del admin
  (WhiteNoise) y apuntar `BACKEND_URL` en Vercel al backend desplegado.
- **`BACKEND_URL` todavia no esta definida en Vercel.** Hasta que exista un
  backend publico al que apuntar, el frontend desplegado no puede autenticar:
  `/` redirige a `/login` y el login avisa que no hay conexion. Es degradacion
  controlada, no un fallo. El detalle de la configuracion de Vercel esta en el
  README; no hay `vercel.json` porque todo vive en el panel.
- Recuperacion de contrasena por correo (HU02): falta backend de email.
- Expiracion de sesion por inactividad y control de acceso por rol (T8/SCRUM-57).

**Funcionalidad**: todas las epicas EP02–EP10 y las HU de EP01 salvo el login.
Ninguna entidad de negocio (cliente, servicio, tarifa, orden, prenda) esta modelada.
