"use client";

import { useRouter } from "next/navigation";

import { api } from "@/lib/api";

export default function LogoutButton() {
  const router = useRouter();

  async function logout() {
    await api("/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  return (
    <button
      type="button"
      onClick={logout}
      className="rounded border px-3 py-1.5 text-sm"
    >
      Cerrar sesion
    </button>
  );
}
