# 📦 SMARTWASH ⚙️

Sistema web de gestion operativa y fidelizacion para lavanderias.
Proyecto academico 🚧 en desarrollo.

- Backend: **Django 6 + Django REST Framework** (SQLite en local, ver [La base de datos](#la-base-de-datos))
- Frontend: **Next.js 16 (App Router, TypeScript)**
- Autenticacion: **sesiones de Django + cookies**

> Contexto del proyecto y decisiones tecnicas: [plot.md](plot.md).
> Reglas para agentes de IA: [AGENTS.md](AGENTS.md).

---

## Requisitos

| Herramienta | Version |
|-------------|---------|
| Python      | 3.12 o superior |
| Node.js     | 20.9 o superior |
| Git         | cualquiera |

No hace falta Docker ni PostgreSQL para desarrollar.

Verifica lo que tienes:

```bash
python3 --version && node --version
```

En Windows usa `python --version` en lugar de `python3 --version`.

---

## 1. Clonar

```bash
git clone https://github.com/PocketDx/smartwash.git
cd smartwash
```

---

## 2. Backend (Django)

### 2.1 Instalar dependencias

**macOS / Linux**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Si PowerShell bloquea el script, ejecuta una sola vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 2.2 Configurar variables de entorno

**macOS / Linux**

```bash
cp .env.example .env
```

**Windows (PowerShell)**

```powershell
Copy-Item .env.example .env
```

Genera una clave para `DJANGO_SECRET_KEY` y pegala en tu `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 2.3 Inicializar la base de datos y aplicar migraciones

SQLite se crea sola: basta con migrar.

```bash
python manage.py migrate
```

El archivo queda en `backend/db.sqlite3` y **no se sube al repositorio**. Si te
preguntas por que, esta explicado en [La base de datos](#la-base-de-datos).

### 2.4 Crear las cuentas de prueba

El equipo comparte cuatro cuentas para desarrollo:

```bash
python manage.py seed_usuarios
```

| Usuario | Rol | Entra al Django Admin |
|---------|-----|----------------------|
| `admin` | administrador | si |
| `recepcion` | recepcionista | no |
| `operario1` | operario | no |
| `operario2` | operario | no |

Clave para las cuatro: `smartwash123`. Se puede cambiar con `--password`.

> El comando **se niega a correr con `DEBUG=False`**. Son cuentas con clave
> publicada; en produccion serian cuatro puertas abiertas. Correrlo dos veces no
> duplica nada, pero **si reescribe las claves** de esos cuatro usuarios.

En este sprint todavia **no hay control de acceso por rol**: las cuatro cuentas
pueden hacer todo. El enforcement es T8.

Si prefieres tu propia cuenta:

```bash
python manage.py createsuperuser
```

Asignale el rol desde el Django Admin (paso 2.6).

### 2.5 Iniciar Django

```bash
python manage.py runserver
```

Queda en http://127.0.0.1:8000.

### 2.6 Django Admin

http://127.0.0.1:8000/admin/ — entra con `admin` (paso 2.4).

---

## 3. Frontend (Next.js)

En **otra terminal**, desde la raiz del repositorio:

```bash
cd frontend
npm install
```

Variables de entorno:

**macOS / Linux**

```bash
cp .env.example .env.local
```

**Windows (PowerShell)**

```powershell
Copy-Item .env.example .env.local
```

Iniciar:

```bash
npm run dev
```

Queda en http://localhost:3000.

---

## 4. Verificar que frontend y backend se comunican

Con **ambos servidores corriendo**:

1. Abre http://localhost:3000 — debe redirigirte a `/login`.
2. Entra con `admin` (paso 2.4).
3. Debes ver el dashboard con tu usuario y tu rol.
4. Pulsa **Cerrar sesion** — vuelves a `/login`.

Comprobacion rapida desde la terminal, sin navegador:

```bash
curl http://localhost:3000/api/health
```

Respuesta esperada:

```json
{"status": "ok", "database": "sqlite"}
```

Esa peticion sale de Next.js (`:3000`) y la responde Django (`:8000`): si
devuelve ese JSON, el puente entre ambos funciona.

> El navegador nunca llama a Django directamente: `frontend/next.config.ts`
> reenvia `/api/*` al backend. Por eso las cookies de sesion funcionan sin CORS.

---

## 5. Ejecutar las pruebas

**macOS / Linux**

```bash
cd backend
source .venv/bin/activate
python manage.py test
```

**Windows (PowerShell)**

```powershell
cd backend
.venv\Scripts\Activate.ps1
python manage.py test
```

El frontend no tiene pruebas unitarias; se valida con pruebas funcionales.
Antes de abrir un PR, si comprueba que compila:

```bash
cd frontend && npm run lint && npm run build
```

---

## 6. Flujo de trabajo con Git

Ramas cortas desde `dev` y Pull Request hacia `dev`. `main` recibe solo merges
desde `dev`. Sin `release`, sin Git Flow completo.

```
main                  ← solo recibe merges desde dev
 └── dev              ← aqui se integra el trabajo diario
      ├── feature/login
      ├── feature/customers
      ├── feature/orders
      └── fix/authentication
```

Por cada tarea:

```bash
git switch dev && git pull                          # 1. actualizar dev
git switch -c feature/mi-tarea                      # 2. rama para la tarea
# 3. implementar cambios enfocados
git push -u origin feature/mi-tarea                 # 4. subir la rama
gh pr create --base dev                             # 5. abrir el PR contra dev
# 6. resolver los comentarios de la revision
# 7. merge a dev desde GitHub
```

Reglas:

- **El PR va contra `dev`, no contra `main`.** `main` sigue siendo la rama por
  defecto en GitHub, asi que al abrir el PR desde la interfaz hay que cambiar la
  base a `dev` a mano. Con `gh pr create --base dev` no te puedes equivocar.
- Nunca se commitea directamente sobre `main` ni sobre `dev`.
- Una rama por tarea de Jira; referencia el ticket en el commit
  (`feat(ordenes): registrar prendas (SCRUM-76)`).
- Antes de abrir el PR, actualiza tu rama: `git pull --rebase origin dev`.
- Cambios enfocados: no reformatees archivos completos ni mezcles tareas.

Cuando `dev` esta estable, se abre un PR `dev` -> `main` para publicar.

Si trabajas con un agente de IA, pasale [AGENTS.md](AGENTS.md).

---

## La base de datos

En desarrollo usamos **SQLite**. El archivo `backend/db.sqlite3` lo genera
`migrate` en tu maquina y esta en el `.gitignore` a proposito.

### Por que no se versiona

**Git no sabe fusionar binarios.** Si dos personas commitean su base, al mergear
git responde `Cannot merge binary files` y toca escoger un lado completo. El
archivo no se dana, pero los datos del otro desaparecen sin que nadie se entere.

**Contiene credenciales.** Ahi viven las cuentas de prueba con sus hashes de
contrasena. No es algo que se publique.

**Engorda el repositorio.** Cada commit guarda una copia entera del binario, no
solo lo que cambio.

Lo que si se versiona son las **migraciones**. Ellas son la fuente de verdad del
esquema: con `migrate` cualquiera reconstruye la misma estructura. Si tu base
local se dana o se desordena, borrala y empieza de nuevo:

```bash
rm backend/db.sqlite3
python manage.py migrate
python manage.py seed_usuarios
```

### Datos de prueba compartidos

Como la base no se comparte, **los datos de prueba se comparten en codigo**. Un
comando de gestion que cualquiera corre y deja su base igual a la de los demas.

Ya existe uno, `seed_usuarios`, y el patron se repite para lo que haga falta.
Segun vayan entrando las historias tendra sentido agregar, por ejemplo:

| Comando | Que sembraria |
|---------|---------------|
| `seed_catalogo` | Tipos de prenda, materiales y servicios con sus tarifas |
| `seed_clientes` | Unos cuantos clientes para no inventarlos a mano |
| `seed_ordenes` | Ordenes de ejemplo en distintos estados, para probar el flujo |

Crear uno son pocas lineas. Va en
`backend/<app>/management/commands/<nombre>.py`:

```python
class Command(BaseCommand):
    help = "Siembra el catalogo de servicios para desarrollo."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Solo para desarrollo.")
        for nombre in ("Lavado", "Planchado", "Lavado en seco"):
            Servicio.objects.get_or_create(nombre=nombre)
```

Lo mas facil es copiar `accounts/management/commands/seed_usuarios.py`, que ya
trae lo importante: usa `get_or_create`, asi que correrlo dos veces no duplica
nada, y se niega a correr con `DEBUG=False`.

Tiene dos ventajas sobre pasarse el archivo por WhatsApp: los datos quedan
versionados y se revisan en un PR como cualquier otro codigo, y cuando alguien
agrega un campo nuevo actualiza el seed en el mismo cambio.

### Cuando pasemos a PostgreSQL

No hay que tocar codigo. El proyecto usa `dj-database-url`, asi que basta definir
`DATABASE_URL` en el `.env`:

```bash
DATABASE_URL=postgres://usuario:clave@host:5432/smartwash
```

Django aplica las mismas migraciones sobre PostgreSQL y listo. `psycopg` ya esta
en `requirements.txt`.

Dos cosas que conviene saber antes de hacerlo:

- **Los datos no viajan solos.** El esquema se recrea con `migrate`, pero lo que
  tengas en tu SQLite local se queda ahi. En desarrollo no importa, porque los
  seeds lo vuelven a sembrar.
- **SQLite es mas permisivo que PostgreSQL.** Una consulta que funciona en local
  puede fallar contra PostgreSQL, sobre todo con mayusculas y minusculas en las
  busquedas de texto. Por eso conviene desplegar temprano y no dejar el cambio
  para el final.

---

## Problemas frecuentes

| Sintoma | Causa | Solucion |
|---------|-------|----------|
| `/login` responde pero el login falla con 403 | Django no confia en el origen del frontend | Revisa `DJANGO_CSRF_TRUSTED_ORIGINS` en `backend/.env` |
| `curl http://localhost:3000/api/health` falla | Django no esta corriendo | Inicia `python manage.py runserver` en la otra terminal |
| `ModuleNotFoundError: django` | El entorno virtual no esta activado | Activa `.venv` (paso 2.1) |
| El puerto 8000 esta ocupado | Otro proceso lo usa | `python manage.py runserver 8001` y ajusta `BACKEND_URL` en `frontend/.env.local` |

---

## Despliegue

### Vercel (frontend)

El proyecto de Vercel ya esta conectado al repositorio y despliega `main`
automaticamente. La configuracion vive en el panel de Vercel, no en el
repositorio: **no hay `vercel.json` y no hace falta**.

Dos ajustes en **Settings** del proyecto de Vercel:

| Ajuste | Valor | Por que |
|--------|-------|---------|
| **Root Directory** | `frontend` | La app de Next no esta en la raiz del repo. Ya esta puesto |
| **Environment Variables** → `BACKEND_URL` | URL publica del backend | Sin esto el rewrite apunta a `http://127.0.0.1:8000`, que en Vercel no existe |

> **`BACKEND_URL` se lee en tiempo de build**, porque `next.config.ts` la usa
> para construir el rewrite. Cambiarla en Vercel **exige un redeploy**; no basta
> con reiniciar.

Mientras el backend no este desplegado, `/` redirige a `/login` y el login
responde "No hay conexion con el servidor". Es el comportamiento esperado: el
frontend no se cae, simplemente no tiene con quien hablar.

### Backend (Render, plan gratuito)

El backend **no** se despliega en Vercel. La configuracion esta en
[`render.yaml`](render.yaml): un Web Service de Render con gunicorn, WhiteNoise
para los estaticos del admin y migraciones al arrancar, mas una base PostgreSQL
de Render. Todo vive en el mismo panel.

> Los limites de los planes gratuitos cambian; confirmalos en Render antes de
> depender de ellos. El servicio **se duerme tras ~15 minutos sin trafico** y la
> primera peticion tarda de 30 a 60 segundos: abrelo un par de minutos antes de
> una demo. **La base gratuita de Render caduca** (a la fecha, a los 30 dias) y
> no tiene copias de seguridad: al caducar se pierden las cuentas y los datos.
> Si el sistema debe durar mas, pasa a [Neon](https://neon.tech) (plan gratuito
> sin caducidad): crea el proyecto y pega su cadena en `DATABASE_URL`, sin
> tocar codigo.

**1. Backend y base de datos.** En Render: *New → Blueprint*, elige este
repositorio y la rama `main`. Render lee `render.yaml`, crea la base
`smartwash-db`, conecta `DATABASE_URL` al servicio y pide las variables que no se
versionan:

| Variable | Valor |
|----------|-------|
| `DJANGO_ALLOWED_HOSTS` | El dominio del servicio, ej. `smartwash-backend.onrender.com` (sin `https://`) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | El dominio de Vercel con esquema, ej. `https://smartwash.vercel.app` |
| `FRONTEND_URL` | El mismo dominio de Vercel; se usa en el enlace del correo de recuperacion |

`DJANGO_SECRET_KEY` la genera Render y `DJANGO_DEBUG` queda en `False`. Sin
`DJANGO_SECRET_KEY`, el backend se niega a arrancar con `DEBUG=False`. Si cambias
la version de Python (`PYTHON_VERSION`), debe ser 3.12 o superior.

**2. Frontend.** En Vercel define `BACKEND_URL` con la URL publica del backend
(`https://smartwash-backend.onrender.com`) y **redespliega**: se lee en build.

**3. Primer administrador.** `seed_usuarios` no corre con `DEBUG=False`, y el
plan gratuito de Render no da consola. Crea la cuenta desde tu maquina con la
*External Database URL* de `smartwash-db` (panel de la base en Render):

```bash
cd backend
DATABASE_URL="<External Database URL>" python manage.py migrate
DATABASE_URL="<External Database URL>" python manage.py createsuperuser
```

Despues entra al Django Admin del backend desplegado (`/admin`) y ponle el rol
`administrador` a ese usuario; sin el rol no ve fidelizacion ni trazabilidad.

**4. Correo de recuperacion.** Sin `RESEND_API_KEY` el correo se imprime en
consola y en produccion no llega nada. Render gratuito bloquea los puertos SMTP,
asi que el envio usa la API HTTP de [Resend](https://resend.com). En Render solo
hay que definir `RESEND_API_KEY` (la clave de la API, desde el panel de Resend):
no la pongas en ningun archivo del repositorio.

El remitente (`DEFAULT_FROM_EMAIL`) ya queda en `SmartWash <onboarding@resend.dev>`,
el de pruebas de Resend. Con ese remitente **solo se puede escribir al correo de
tu propia cuenta de Resend**: para que otros usuarios reciban el enlace, verifica
un dominio en Resend y cambia `DEFAULT_FROM_EMAIL` por una direccion de ese dominio.

Limitaciones conocidas: los contadores de intentos de login y de recuperacion
viven en la memoria del proceso (por eso `--workers 1` y se reinician al
dormirse el servicio), y el backend responde `403` a quien no tiene sesion.
