import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/lib/api";
import LogoutButton from "./logout-button";

export default async function DashboardPage() {
  const user = await getCurrentUser(await cookies());
  if (!user) redirect("/login");

  return (
    <main className="mx-auto max-w-2xl p-8">
      <header className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">SmartWash</h1>
        <LogoutButton />
      </header>

      <p className="mb-2">
        Sesion iniciada como <strong>{user.username}</strong>.
      </p>
      <p className="text-sm opacity-70">Rol: {user.rol}</p>

      <p className="mt-8 text-sm opacity-70">
        Scaffolding listo. Las funcionalidades de negocio (clientes, ordenes,
        servicios, fidelizacion) se implementan en sus propias ramas.
      </p>
    </main>
  );
}
