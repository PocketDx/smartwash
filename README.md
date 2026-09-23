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
| `seed_catalogo` | Tipos de prenda y servicios con sus tarifas |
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

### Backend

El backend **no** se despliega en Vercel. Lo pendiente para llevarlo a
produccion con PostgreSQL esta en la seccion *Pendiente* de [plot.md](plot.md).
