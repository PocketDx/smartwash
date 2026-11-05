import type { Cliente } from "@/lib/api";
import { formatCOP } from "@/lib/format";
import { ClayBadge } from "../components/ui/clay";

const COLOR = { Ocasional: "blue", Frecuente: "mint", VIP: "lavender" } as const;

export function BadgeClasificacion({ clasificacion }: { clasificacion: Cliente["clasificacion"] }) {
  return <ClayBadge color={COLOR[clasificacion]}>{clasificacion}</ClayBadge>;
}

// Los umbrales viven en el backend (clasificacion_por_consumo); este texto solo los explica.
export function ReglasClasificacion() {
  return (
    <p className="text-xs text-(--sw-ink-soft)">
      Frecuente desde 3 ordenes entregadas; VIP desde 10 entregadas o {formatCOP(500000)} consumidos. Se
      recalcula sola al entregar una orden pagada y nunca baja.
    </p>
  );
}
