# Especificación Técnica — Frontend (Next.js)

## Proyecto

**GESECA** — Sistema Web Para La Gestión Y Seguimiento De Campañas De Promoción De La Salud Y Prevención De La Enfermedad

Proyecto académico de la materia **Análisis y Diseño de Sistemas**.

## Objetivo del sistema

Desarrollar un sistema de información web para gestionar y evaluar campañas de promoción de la salud y prevención de la enfermedad, mediante la caracterización de actividades, población beneficiaria, coberturas e indicadores.

## Rol de este frontend

Este frontend es la **interfaz web** del sistema, encargada de la interacción con el usuario final (personal de salud, gestores de campañas, administradores) y del consumo de la API expuesta por el backend (Django).

## Stack tecnológico

- **Framework:** Next.js 15+ (App Router)
- **Lenguaje:** TypeScript
- **Estilos:** Tailwind CSS
- **Componentes UI:** shadcn/ui (o similar)
- **Manejo de estado remoto:** TanStack Query (React Query) para consumo de la API
- **Formularios y validación:** React Hook Form + Zod
- **Cliente HTTP:** `fetch` nativo o `axios`
- **Autenticación:** manejo de token JWT (o sesión) entregado por el backend
- **Gestor de paquetes:** npm / pnpm

## Estructura de carpetas propuesta

```
frontend/
├── src/
│   ├── app/
│   │   ├── (auth)/              # Login, recuperación de contraseña
│   │   ├── (dashboard)/
│   │   │   ├── campanas/        # Gestión de campañas
│   │   │   ├── actividades/     # Actividades por campaña
│   │   │   ├── poblacion/       # Población beneficiaria
│   │   │   ├── coberturas/      # Seguimiento de coberturas
│   │   │   ├── indicadores/     # Indicadores de gestión
│   │   │   └── reportes/        # Reportes y evaluación
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── ui/                  # Componentes base reutilizables
│   │   └── forms/               # Formularios de dominio
│   ├── lib/
│   │   ├── api.ts               # Cliente HTTP hacia el backend
│   │   └── auth.ts              # Manejo de sesión/token
│   ├── hooks/
│   ├── types/                   # Tipos TypeScript compartidos (DTOs de la API)
│   └── styles/
├── public/
├── .env.example
├── next.config.ts
├── tailwind.config.ts
└── tsconfig.json
```

## Módulos funcionales esperados

Alineados con los módulos del backend (sujetos a ajuste según el análisis de requerimientos):

1. **Autenticación:** inicio de sesión y control de acceso según rol.
2. **Campañas:** listado, creación, edición y consulta del estado de campañas.
3. **Actividades:** registro y visualización de actividades por campaña.
4. **Población beneficiaria:** consulta y registro de la población atendida.
5. **Coberturas:** visualización de cobertura alcanzada vs. población objetivo (indicadores gráficos).
6. **Indicadores:** dashboards de seguimiento y evaluación.
7. **Reportes:** generación y descarga de reportes.

## Convenciones de desarrollo

- Uso de **Server Components** por defecto; **Client Components** (`"use client"`) solo cuando se requiera interactividad
- Comunicación con el backend a través de una capa centralizada en `lib/api.ts`
- Tipado estricto de las respuestas de la API en `types/`
- Rutas protegidas mediante middleware de autenticación (`middleware.ts`)
- Componentes desacoplados por dominio (campañas, actividades, población, coberturas, indicadores)
- Manejo consistente de estados de carga y error en las vistas que consumen la API

## Buenas prácticas a seguir

- No exponer variables sensibles en el cliente (usar `NEXT_PUBLIC_` solo para datos no sensibles)
- Validar formularios en cliente (Zod) reflejando las mismas reglas del backend
- Diseño responsivo (mobile-first) considerando uso en campo por personal de salud
- Accesibilidad básica (etiquetas, contraste, navegación por teclado)
- Aplicar principios de diseño vistos en la materia (modularidad, separación de responsabilidades entre presentación y lógica de negocio)

## Pendiente de definir

- Wireframes/mockups de las pantallas principales (dashboard, gestión de campañas, indicadores)
- Definición final de roles de usuario y vistas asociadas
- Librería de gráficos para indicadores y coberturas (por ejemplo, Recharts o Chart.js)
- Estrategia de despliegue (Vercel u otro entorno)
