import type { EtapaDeSeguimiento, SeguimientoOrden } from "@/lib/api";
import { formatCOP } from "@/lib/format";

const ZONA_HORARIA = "America/Bogota";
const FECHA_HORA = new Intl.DateTimeFormat("es-CO", {
  timeZone: ZONA_HORARIA,
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});
const FECHA_LARGA = new Intl.DateTimeFormat("es-CO", {
  timeZone: ZONA_HORARIA,
  day: "numeric",
  month: "long",
  year: "numeric",
});

/** "11 nov 2026, 3:00 p. m." en hora de Bogota (es-CO por si solo pondria "11 de nov de 2026"). */
export function fechaYHora(iso: string): string {
  const p = Object.fromEntries(FECHA_HORA.formatToParts(new Date(iso)).map((x) => [x.type, x.value]));
  return `${p.day} ${p.month.replace(".", "")} ${p.year}, ${p.hour}:${p.minute} ${p.dayPeriod}`;
}

/** "20 de octubre de 2026" a partir de una fecha AAAA-MM-DD, sin correr el dia por la zona horaria. */
export function fechaLarga(dia: string): string {
  return FECHA_LARGA.format(new Date(`${dia}T12:00:00-05:00`));
}

// Un pago parcial tiene fecha (la del ultimo abono) pero no cuenta como etapa completada.
function completada(etapa: EtapaDeSeguimiento | undefined) {
  return etapa?.fecha != null && etapa.estado_pago !== "parcial";
}

function nombre(etapa: EtapaDeSeguimiento) {
  if (etapa.estado_pago === "parcial") return "Pagada (parcial)";
  if (etapa.estado_pago === "completo") return "Pagada completa";
  return etapa.etapa;
}

export default function LineaTiempo({ orden }: { orden: SeguimientoOrden }) {
  const { etapas, etapa_actual: actual } = orden;

  return (
    // Vertical tambien en escritorio: en el ancho de la tarjeta, siete etapas en fila no se leen.
    <ol aria-label="Etapas de tu pedido" className="flex flex-col">
      {etapas.map((paso, i) => {
        const { etapa, fecha } = paso;
        const hecha = completada(paso);
        const parcial = paso.estado_pago === "parcial";
        const esActual = etapa === actual && !orden.cancelada;
        const tramoPintado = hecha && completada(etapas[i + 1]);
        return (
          <li
            key={etapa}
            aria-current={esActual ? "step" : undefined}
            className="relative flex gap-3 pb-6 last:pb-0"
          >
            {i < etapas.length - 1 && (
              <span
                aria-hidden
                className={`absolute top-7 bottom-0 left-3 w-1 ${
                  tramoPintado ? "bg-(--sw-accent)" : "bg-(--sw-hairline)"
                }`}
              />
            )}
            <span
              aria-hidden
              className={`relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 text-xs font-extrabold ${
                hecha
                  ? "border-(--sw-line) bg-(--sw-accent) text-(--sw-on-accent)"
                  : parcial
                    ? "border-(--sw-line) bg-(--sw-sun) text-(--sw-on-accent)"
                    : "border-(--sw-hairline) bg-(--sw-surface) text-(--sw-ink-soft)"
              } ${esActual ? "ring-4 ring-(--sw-accent)/40" : ""}`}
            >
              {hecha ? "✓" : parcial ? "$" : i + 1}
            </span>
            <div className="min-w-0 pt-0.5">
              <p
                className={`text-sm leading-tight ${hecha || parcial ? "font-bold text-(--sw-ink)" : "text-(--sw-ink-soft)"}`}
              >
                {nombre(paso)}
                {parcial && paso.abonado !== undefined && paso.total !== undefined && (
                  <span className="font-normal text-(--sw-ink-soft)">
                    {" "}
                    · Abono: {formatCOP(paso.abonado)} · Total: {formatCOP(paso.total)}
                  </span>
                )}
              </p>
              <p className="mt-0.5 text-xs text-(--sw-ink-soft)">
                {fecha ? (
                  <>
                    <span className="sr-only">{parcial ? "Ultimo abono el " : "Completada el "}</span>
                    {fechaYHora(fecha)}
                  </>
                ) : (
                  "Pendiente"
                )}
              </p>
              {parcial && paso.abonado !== undefined && paso.total !== undefined && (
                <p className="mt-0.5 text-xs font-semibold text-(--sw-ink)">
                  Saldo pendiente: {formatCOP(Math.max(paso.total - paso.abonado, 0))}
                </p>
              )}
              {esActual && <p className="mt-0.5 text-xs font-extrabold text-(--sw-accent-text)">Etapa actual</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
