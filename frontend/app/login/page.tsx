"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);

    const form = new FormData(event.currentTarget);

    let response: Response;
    try {
      response = await api("/auth/login", {
        method: "POST",
        body: {
          username: form.get("username"),
          password: form.get("password"),
        },
      });
    } catch {
      // El backend no responde: sin esto el boton se queda en "Ingresando...".
      setError("No hay conexion con el servidor. Intentalo de nuevo.");
      setPending(false);
      return;
    }

    if (response.ok) {
      router.replace("/");
      router.refresh();
      return;
    }

    const data = (await response.json().catch(() => ({}))) as {
      detail?: string;
    };
    setError(data.detail ?? "No fue posible iniciar sesion.");
    setPending(false);
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center p-8">
      <h1 className="mb-6 text-2xl font-semibold">SmartWash</h1>

      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm">
          Usuario
          <input
            name="username"
            autoComplete="username"
            required
            className="rounded border px-3 py-2"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          Contrasena
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            className="rounded border px-3 py-2"
          />
        </label>

        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={pending}
          className="rounded border px-3 py-2 disabled:opacity-50"
        >
          {pending ? "Ingresando..." : "Iniciar sesion"}
        </button>
      </form>
    </main>
  );
}
