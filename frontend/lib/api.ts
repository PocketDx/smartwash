// Cliente HTTP unico hacia la API de Django.
//
// En el navegador las rutas son relativas (/api/...) y Next.js las reenvia al
// backend con el rewrite de next.config.ts, asi que la cookie de sesion viaja
// sola. En el servidor hay que reenviar las cookies a mano.

export type Rol = "administrador" | "recepcionista" | "operario";

/** Lo que devuelve UserSerializer en el backend. */
export type User = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  rol: Rol;
};

type Metodo = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

type OpcionesApi = {
  method?: Metodo;
  body?: unknown;
};

/** Cookies ya resueltas de `await cookies()`, lo unico que necesita el server. */
type CookieStore = { toString(): string };

const UNSAFE: ReadonlySet<Metodo> = new Set<Metodo>([
  "POST",
  "PUT",
  "PATCH",
  "DELETE",
]);

function readCookie(name: string): string | undefined {
  return document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${name}=`))
    ?.split("=")[1];
}

/** Peticion desde el navegador. Adjunta el token CSRF en metodos de escritura. */
export async function api(
  path: string,
  { method = "GET", body }: OpcionesApi = {},
): Promise<Response> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";

  if (UNSAFE.has(method)) {
    // GET /api/auth/me lleva @ensure_csrf_cookie: siembra csrftoken si falta.
    if (!readCookie("csrftoken")) await fetch("/api/auth/me");
    headers["X-CSRFToken"] = readCookie("csrftoken") ?? "";
  }

  return fetch(`/api${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

/** Usuario autenticado leido desde un Server Component, o null si no hay sesion.
 *
 * Devuelve null tambien si el backend no responde. Sin esto, un Django caido
 * hace que fetch lance y la pagina entera falle con 500; asi el usuario cae en
 * /login, que al menos es una pantalla util.
 */
export async function getCurrentUser(
  cookieStore: CookieStore,
): Promise<User | null> {
  const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
  try {
    const response = await fetch(`${backend}/api/auth/me`, {
      headers: { cookie: cookieStore.toString() },
      cache: "no-store",
    });
    return response.ok ? ((await response.json()) as User) : null;
  } catch {
    return null;
  }
}
