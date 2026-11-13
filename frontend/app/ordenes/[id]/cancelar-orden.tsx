"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AlertaErrores } from "@/app/catalogo/errores";
import { cancelarOrden, type EstadoOrden, type Novedad, type Orden } from "@/lib/api";
import { formatCOP } from "@/lib/format";
import { ClayButton, ClayCard, ClayTextarea } from "../../components/ui/clay";
import { mensajesDeOrden } from "../errores";

// Mismo criterio que Orden.cancelar en el backend, que es quien decide.
const ANTES_DEL_SERVICIO: EstadoOrden[] = ["En espera", "Recibida", "Clasificada"];

function clienteNoContinua(novedades: Novedad[]) {
  const ultima = [...novedades].sort((a, b) => a.creado_en.localeCompare(b.creado_en) || a.id - b.id).at(-1);
  return ultima?.decision === "no_continuar";
}

export default function CancelarOrden({ orden, novedades }: { orden: Orden; novedades: Novedad[] | null }) {
  const router = useRouter();
  const [abierto, setAbierto] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [errores, setErrores] = useState<string[]>([]);
  const [pending, setPending] = useState(false);

  const rechazada = orden.estado === "Con novedad" && novedades !== null && clienteNoContinua(novedades);
  if (!ANTES_DEL_SERVICIO.includes(orden.estado) && !rechazada) return null;

  const pagado = Number(orden.total_pagado);

  function descartar() {
    setAbierto(false);
    setMotivo("");
    setErrores([]);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setErrores([]);
    const response = await cancelarOrden(orden.id, motivo.trim()).catch(() => null);
    setPending(false);

    if (response?.ok) {
      descartar();
      router.refresh();
      return;
    }
    setErrores(await mensajesDeOrden(response, "No se pudo cancelar la orden"));
  }

  if (!abierto) {
    return (
      <ClayCard className="mb-6">
        <h2 className="text-sm font-bold text-(--sw-ink)">Cancelar la orden</h2>
        <p className="mt-1 text-sm text-(--sw-ink-soft)">
          {rechazada
            ? "El cliente decidio no continuar con la orden: se puede cancelar indicando el motivo."
            : "Si el cliente se retracta o la orden se registro con un error, se cancela antes de iniciar el servicio."}
        </p>
        <ClayButton type="button" variant="coral" className="mt-3" onClick={() => setAbierto(true)}>
          Cancelar orden
        </ClayButton>
      </ClayCard>
    );
  }

  return (
    <ClayCard className="mb-6">
      <h2 className="text-sm font-bold text-(--sw-ink)">Cancelar la orden</h2>
      <form onSubmit={onSubmit} className="mt-3 flex flex-col gap-4">
        <ClayTextarea
          aria-label="Motivo de la cancelacion"
          placeholder="Por que se cancela (obligatorio)"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          maxLength={255}
          className="min-h-20"
          required
        />
        <ul className="list-inside list-disc text-sm text-(--sw-ink-soft)">
          <li>La cancelacion es definitiva: la orden no se puede reactivar.</li>
          {pagado > 0 && (
            <li>
              Se le devuelven {formatCOP(pagado)} al cliente. La devolucion queda en el historial; los pagos no
              se modifican.
            </li>
          )}
          {orden.operario !== null && <li>La orden sale de la bandeja de su operario.</li>}
        </ul>
        <AlertaErrores titulo="No se pudo cancelar la orden" errores={errores} />
        <div className="flex flex-wrap gap-3">
          <ClayButton type="submit" variant="coral" disabled={pending || motivo.trim() === ""}>
            {pending ? "Cancelando..." : "Confirmar cancelacion"}
          </ClayButton>
          <ClayButton type="button" variant="secundario" onClick={descartar} disabled={pending}>
            No cancelar
          </ClayButton>
        </div>
      </form>
    </ClayCard>
  );
}
