# 📦 SMARTWASH ⚙️

Sistema web de gestion operativa y fidelizacion para lavanderias.
Proyecto academico 🚧 en desarrollo.

- Backend: **Django 6 + Django REST Framework** (SQLite en local)
- Frontend: **Next.js 16 (App Router, JavaScript)**
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

### 2.4 Crear un superusuario

```bash
python manage.py createsuperuser
```

Asignale el rol de administrador desde el admin de Django (paso 2.6) o asi:

```bash
python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); u=U.objects.get(username='TU_USUARIO'); u.rol=U.Rol.ADMINISTRADOR; u.save()"
```

### 2.5 Iniciar Django

```bash
python manage.py runserver
```

Queda en http://127.0.0.1:8000.

### 2.6 Django Admin

http://127.0.0.1:8000/admin/ — entra con el superusuario del paso 2.4.

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
2. Entra con el superusuario del paso 2.4.
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

> El navegador nunca llama a Django directamente: `frontend/next.config.mjs`
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

Ramas cortas desde `main` y Pull Request hacia `main`. Sin `develop`, sin
`release`, sin Git Flow.

```
main
 ├── feature/login
 ├── feature/customers
 ├── feature/orders
 └── fix/authentication
```

Por cada tarea:

```bash
git switch main && git pull          # 1. actualizar main
git switch -c feature/mi-tarea       # 2. rama para la tarea
# 3. implementar cambios enfocados
git push -u origin feature/mi-tarea  # 4. abrir el Pull Request
# 5. resolver los comentarios de la revision
# 6. merge a main desde GitHub
```

Reglas:

- Nunca se commitea directamente sobre `main`.
- Una rama por tarea de Jira; referencia el ticket en el commit
  (`feat(ordenes): registrar prendas (SCRUM-76)`).
- Antes de abrir el PR, actualiza tu rama: `git pull --rebase origin main`.
- Cambios enfocados: no reformatees archivos completos ni mezcles tareas.

Si trabajas con un agente de IA, pasale [AGENTS.md](AGENTS.md).

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

> **`BACKEND_URL` se lee en tiempo de build**, porque `next.config.mjs` la usa
> para construir el rewrite. Cambiarla en Vercel **exige un redeploy**; no basta
> con reiniciar.

Mientras el backend no este desplegado, `/` redirige a `/login` y el login
responde "No hay conexion con el servidor". Es el comportamiento esperado: el
frontend no se cae, simplemente no tiene con quien hablar.

### Backend

El backend **no** se despliega en Vercel. Lo pendiente para llevarlo a
produccion con PostgreSQL esta en la seccion *Pendiente* de [plot.md](plot.md).
