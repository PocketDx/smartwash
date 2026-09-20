// Cliente HTTP unico hacia la API de Django.
//
// En el navegador las rutas son relativas (/api/...) y Next.js las reenvia al
// backend con el rewrite de next.config.mjs, asi que la cookie de sesion viaja
// sola. En el servidor hay que reenviar las cookies a mano.

const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function readCookie(name) {
  return document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${name}=`))
    ?.split("=")[1];
}

/** Peticion desde el navegador. Adjunta el token CSRF en metodos de escritura. */
export async function api(path, { method = "GET", body } = {}) {
  const headers = {};
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

/** Usuario autenticado leido desde un Server Component, o null si no hay sesion. */
export async function getCurrentUser(cookieStore) {
  const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
  const response = await fetch(`${backend}/api/auth/me`, {
    headers: { cookie: cookieStore.toString() },
    cache: "no-store",
  });
  return response.ok ? response.json() : null;
}
