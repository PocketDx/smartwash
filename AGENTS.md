# AGENTS.md — reglas de trabajo para agentes de IA en SmartWash

Cada integrante usa su propio agente sobre el mismo repositorio. Estas reglas
existen para que los cambios no choquen entre si.

## Antes de escribir codigo

1. Lee [plot.md](plot.md): stack, estructura, convenciones y decisiones ya tomadas.
2. Lee el ticket de Jira de tu tarea (proyecto `SCRUM`) y sus criterios de
   aceptacion. Si la tarea es una subtarea `[Desarrollo Backend]` o
   `[Desarrollo Frontend]`, la especificacion completa esta en la historia padre.
3. Mira el codigo que ya existe en la zona que vas a tocar. Reutiliza lo que haya
   antes de crear algo nuevo.

## Rama y commits

```bash
git switch main && git pull
git switch -c feature/nombre-corto   # o fix/nombre-corto
```

- **Nunca** commitees directamente sobre `main`. Todo entra por Pull Request.
- Una rama por tarea de Jira. Nombres: `feature/<tema>` o `fix/<tema>`.
- Referencia el ticket en el commit: `feat(ordenes): registrar prendas (SCRUM-76)`.
- Antes de abrir el PR: `git switch main && git pull && git switch - && git rebase main`.

## Alcance del cambio

- Toca **solo** los archivos que tu tarea necesita. Si encuentras algo mal fuera
  de tu alcance, reportalo; no lo arregles en esta rama.
- No reformatees archivos completos por un cambio pequeno. El diff debe leerse.
- No hagas refactors globales sin justificarlos primero con el equipo.
- No agregues dependencias si el stdlib, Django, DRF, Next.js o una dependencia ya
  instalada resuelven el problema. Si agregas una, explica por que en el PR.
- No cambies `config/settings.py`, `next.config.mjs`, `requirements.txt` ni
  `package.json` salvo que tu tarea lo exija; son los archivos que mas conflictos
  generan entre ramas.
- No toques `plot.md` ni `AGENTS.md` salvo que tu cambio invalide algo que dicen.

## Convenciones que debes respetar

- Backend: una app de Django por dominio. Rutas de la API **sin barra final**.
- Frontend: JavaScript, nunca TypeScript. Server Components por defecto. Toda
  llamada a la API pasa por `lib/api.js`.
- Toda variable de entorno nueva se documenta en el `.env.example` correspondiente.
- Nunca commitees un `.env`, credenciales, tokens ni la base `db.sqlite3`.

## Antes de abrir el PR

```bash
cd backend  && .venv/bin/python manage.py test
cd frontend && npm run lint && npm run build
```

Si tu tarea es una historia de usuario, agrega la prueba de sus escenarios de
aceptacion. Si es infraestructura, verifica que el flujo de login siga pasando.

## Migraciones

Genera la migracion en tu rama (`manage.py makemigrations <app>`) y commitea el
archivo. Si al rebasar aparece un conflicto de numeracion con otra rama, renumera
la tuya; no borres la migracion ajena.
