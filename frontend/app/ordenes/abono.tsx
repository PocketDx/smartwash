import type { Orden } from "@/lib/api";
import { formatCOP } from "@/lib/format";
import { ClayBadge } from "../components/ui/clay";

/** Si la orden ya alcanzo el abono minimo (HU23) y, si no, cuanto le falta. El
 * backend lo exige al asignar; aqui solo se muestra para no intentarlo a ciegas. */
export default function EstadoAbono({ orden }: { orden: Orden }) {
  if (orden.estado === "Cancelada") return <span className="text-(--sw-ink-soft)">—</span>;
  if (orden.tiene_abono) return <ClayBadge color="mint">Habilitada para asignar</ClayBadge>;

  const falta = Math.max(Number(orden.abono_requerido) - Number(orden.total_pagado), 0);
  return <ClayBadge color="peach">Falta abono: {formatCOP(falta)}</ClayBadge>;
}
