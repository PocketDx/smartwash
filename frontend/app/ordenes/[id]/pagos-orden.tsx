"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AlertaErrores } from "@/app/catalogo/errores";
import { registrarPago, type MetodoPago, type Orden, type Pago } from "@/lib/api";
import { FECHA_LEGIBLE } from "@/lib/auditoria";
import { formatCOP } from "@/lib/format";
import { ClayButton, ClayCard, ClayField, ClayInput, ClaySelect } from "../../components/ui/clay";
import { mensajesDeOrden } from "../errores";

const METODOS: Record<MetodoPago, string> = {
  efectivo: "Efectivo",
  transferencia: "Transferencia",
  tarjeta: "Tarjeta",
};

export default function PagosOrden({ orden, pagos }: { orden: Orden; pagos: Pago[] | null }) {
  const router = useRouter();
  const [abierto, setAbierto] = useState(false);
  const [monto, setMonto] = useState("");
  const [metodo, setMetodo] = useState<MetodoPago>("efectivo");
  const [errores, setErrores] = useState<string[]>([]);
  const [registrado, setRegistrado] = useState(false);
  const [pending, setPending] = useState(false);

  const saldo = Number(orden.saldo_pendiente);
  const faltaAbono = Math.max(Number(orden.abono_requerido) - Number(orden.total_pagado), 0);
  const admitePagos = saldo > 0 && orden.estado !== "Cancelada";

  function cerrar() {
    setAbierto(false);
    setMonto("");
    setMetodo("efectivo");
    setErrores([]);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setErrores([]);
    const response = await registrarPago(orden.id, monto, metodo).catch(() => null);
    setPending(false);

    if (response?.ok) {
      cerrar();
      setRegistrado(true);
      router.refresh();
      return;
    }
    setErrores(await mensajesDeOrden(response, "No se pudo registrar el pago"));
  }

  return (
    <ClayCard className="mb-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-bold text-(--sw-ink)">Pagos</h2>
        <p className="text-sm text-(--sw-ink-soft)">
          Pagado <span className="font-semibold text-(--sw-ink) tabular-nums">{formatCOP(orden.total_pagado)}</span> de{" "}
          <span className="tabular-nums">{formatCOP(orden.valor_total)}</span> · Estado:{" "}
          <span className="font-semibold text-(--sw-ink)">{orden.estado_pago}</span>
        </p>
      </div>

      {pagos === null ? (
        <p className="mt-3 text-sm text-(--sw-ink-soft)">No se pudieron cargar los pagos.</p>
      ) : pagos.length === 0 ? (
        <p className="mt-3 text-sm text-(--sw-ink-soft)">Todavia no hay pagos registrados.</p>
      ) : (
        <ul className="mt-3 flex flex-col gap-1 text-sm">
          {pagos.map((pago) => (
            <li key={pago.id} className="flex justify-between gap-4 border-t border-(--sw-hairline) pt-1">
              <span className="text-(--sw-ink-soft)">
                {FECHA_LEGIBLE.format(new Date(pago.creado_en))} · {METODOS[pago.metodo] ?? pago.metodo}
              </span>
              <span className="font-semibold text-(--sw-ink) tabular-nums">{formatCOP(pago.monto)}</span>
            </li>
          ))}
        </ul>
      )}

      {registrado && !abierto && (
        <p role="status" className="mt-3 text-sm text-(--sw-ink-soft)">
          Pago registrado.
        </p>
      )}

      {!admitePagos ? (
        orden.pago_completo && <p className="mt-3 text-sm text-(--sw-ink-soft)">La orden esta pagada por completo.</p>
      ) : !abierto ? (
        <div className="mt-4">
          <ClayButton
            type="button"
            onClick={() => {
              setRegistrado(false);
              setAbierto(true);
            }}
          >
            Registrar pago
          </ClayButton>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <ClayField label={`Monto (saldo ${formatCOP(saldo)})`}>
              <ClayInput
                type="number"
                min="0.01"
                max={orden.saldo_pendiente}
                step="0.01"
                value={monto}
                onChange={(e) => setMonto(e.target.value)}
                required
              />
            </ClayField>
            <ClayField label="Metodo de pago">
              <ClaySelect value={metodo} onChange={(e) => setMetodo(e.target.value as MetodoPago)} required>
                {Object.entries(METODOS).map(([valor, etiqueta]) => (
                  <option key={valor} value={valor}>
                    {etiqueta}
                  </option>
                ))}
              </ClaySelect>
            </ClayField>
          </div>

          <div className="flex flex-wrap gap-2">
            {!orden.tiene_abono && faltaAbono > 0 && faltaAbono < saldo && (
              <ClayButton type="button" variant="secundario" onClick={() => setMonto(faltaAbono.toFixed(2))}>
                Abono minimo: {formatCOP(faltaAbono)}
              </ClayButton>
            )}
            <ClayButton type="button" variant="secundario" onClick={() => setMonto(orden.saldo_pendiente)}>
              Saldo completo: {formatCOP(saldo)}
            </ClayButton>
          </div>

          {!orden.tiene_abono && (
            <p className="text-xs text-(--sw-ink-soft)">
              Al completar el abono minimo de {formatCOP(orden.abono_requerido)} la orden pasa a
              &quot;Recibida&quot; y se calcula su fecha estimada de entrega.
            </p>
          )}

          <AlertaErrores titulo="No se pudo registrar el pago" errores={errores} />

          <div className="flex flex-wrap gap-3">
            <ClayButton type="submit" disabled={pending}>
              {pending ? "Registrando..." : "Registrar pago"}
            </ClayButton>
            <ClayButton type="button" variant="secundario" disabled={pending} onClick={cerrar}>
              Cancelar
            </ClayButton>
          </div>
        </form>
      )}
    </ClayCard>
  );
}
