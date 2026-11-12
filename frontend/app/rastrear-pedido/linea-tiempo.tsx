import type { SeguimientoOrden } from "@/lib/api";

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

export default function LineaTiempo({ orden }: { orden: SeguimientoOrden }) {
  const { etapas, etapa_actual: actual } = orden;

  return (
    // Vertical tambien en escritorio: en el ancho de la tarjeta, siete etapas en fila no se leen.
    <ol aria-label="Etapas de tu pedido" className="flex flex-col">
      {etapas.map(({ etapa, fecha }, i) => {
        const hecha = fecha !== null;
        const esActual = etapa === actual && !orden.cancelada;
        const tramoPintado = hecha && etapas[i + 1]?.fecha != null;
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
                  : "border-(--sw-hairline) bg-(--sw-surface) text-(--sw-ink-soft)"
              } ${esActual ? "ring-4 ring-(--sw-accent)/40" : ""}`}
            >
              {hecha ? "✓" : i + 1}
            </span>
            <div className="min-w-0 pt-0.5">
              <p className={`text-sm leading-tight ${hecha ? "font-bold text-(--sw-ink)" : "text-(--sw-ink-soft)"}`}>
                {etapa}
              </p>
              <p className="mt-0.5 text-xs text-(--sw-ink-soft)">
                {fecha ? (
                  <>
                    <span className="sr-only">Completada el </span>
                    {fechaYHora(fecha)}
                  </>
                ) : (
                  "Pendiente"
                )}
              </p>
              {esActual && <p className="mt-0.5 text-xs font-extrabold text-(--sw-accent-text)">Etapa actual</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
