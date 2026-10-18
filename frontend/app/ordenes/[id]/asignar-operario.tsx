"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AlertaErrores } from "@/app/catalogo/errores";
import { asignarOperario, type EstadoOrden, type Operario, type Orden, type User } from "@/lib/api";
import { formatCOP } from "@/lib/format";
import { ClayButton, ClayCard, ClayField, ClaySelect } from "../../components/ui/clay";
import { mensajesDeOrden } from "../errores";

// Las mismas reglas que asignar_operario() en el backend, que es quien decide.
const REASIGNABLES: EstadoOrden[] = ["Recibida", "Clasificada"];
const TRABAJO_EN_CURSO: EstadoOrden[] = ["En proceso", "Control de calidad"];

export default function AsignarOperario({
  orden,
  operarios,
  usuario,
}: {
  orden: Orden;
  operarios: Operario[] | null;
  usuario: User;
}) {
  const router = useRouter();
  const [editando, setEditando] = useState(false);
  const [operario, setOperario] = useState("");
  const [errores, setErrores] = useState<string[]>([]);
  const [pending, setPending] = useState(false);

  // /operarios solo trae activos: si el asignado no aparece, fue desactivado.
  const actual = orden.operario === null ? null : operarios?.find((o) => o.id === orden.operario);
  const actualInactivo = orden.operario !== null && operarios !== null && !actual;
  const nombreActual =
    orden.operario === null
      ? "Sin asignar"
      : (actual?.nombre ?? `Operario #${orden.operario}${actualInactivo ? " (inactivo)" : ""}`);

  const excepcionAdmin =
    usuario.rol === "administrador" &&
    TRABAJO_EN_CURSO.includes(orden.estado) &&
    (orden.operario === null || actualInactivo);
  const puedeAsignar = REASIGNABLES.includes(orden.estado) || excepcionAdmin;
  const candidatos = (operarios ?? []).filter((o) => o.id !== orden.operario);

  function cancelar() {
    setEditando(false);
    setOperario("");
    setErrores([]);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setErrores([]);
    const response = await asignarOperario(orden.id, Number(operario)).catch(() => null);
    setPending(false);

    if (response?.ok) {
      cancelar();
      router.refresh();
      return;
    }
    setErrores(await mensajesDeOrden(response, "No se pudo asignar el operario"));
  }

  let aviso: string | null = null;
  if (orden.estado === "En espera") {
    const falta = Math.max(Number(orden.abono_requerido) - Number(orden.total_pagado), 0);
    aviso = `Para asignarla se requiere el abono minimo de ${formatCOP(orden.abono_requerido)} (faltan ${formatCOP(falta)}).`;
  } else if (TRABAJO_EN_CURSO.includes(orden.estado) && !excepcionAdmin) {
    aviso = `La orden esta "${orden.estado}" y queda fija con su operario. Solo el administrador puede reasignarla si el operario fue desactivado.`;
  } else if (puedeAsignar && operarios === null) {
    aviso = "No se pudo cargar la lista de operarios. Verifica que el backend este en ejecucion.";
  } else if (puedeAsignar && candidatos.length === 0) {
    aviso = "No hay otros operarios activos a quienes asignar la orden.";
  }
  const ofrecerAsignar = puedeAsignar && aviso === null;

  return (
    <ClayCard className="mb-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-(--sw-ink)">Operario</h2>
          <p className="mt-1 text-sm text-(--sw-ink-soft)">{nombreActual}</p>
        </div>
        {ofrecerAsignar && !editando && (
          <ClayButton type="button" variant="secundario" onClick={() => setEditando(true)}>
            {orden.operario === null ? "Asignar operario" : "Reasignar"}
          </ClayButton>
        )}
      </div>

      {aviso && <p className="mt-3 text-sm text-(--sw-ink-soft)">{aviso}</p>}

      {editando && (
        <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-3">
          <ClayField label="Operario activo">
            <ClaySelect value={operario} onChange={(e) => setOperario(e.target.value)} required>
              <option value="">Selecciona un operario...</option>
              {candidatos.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.nombre}
                </option>
              ))}
            </ClaySelect>
          </ClayField>
          <AlertaErrores titulo="No se pudo asignar el operario" errores={errores} />
          <div className="flex flex-wrap gap-3">
            <ClayButton type="submit" disabled={pending || !operario}>
              {pending ? "Guardando..." : "Confirmar"}
            </ClayButton>
            <ClayButton type="button" variant="secundario" onClick={cancelar} disabled={pending}>
              Cancelar
            </ClayButton>
          </div>
        </form>
      )}
    </ClayCard>
  );
}
