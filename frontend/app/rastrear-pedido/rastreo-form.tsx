"use client";

import { useState, type FormEvent } from "react";

import { AlertaErrores } from "@/app/catalogo/errores";
import { leerErroresApi, rastrearOrden, type SeguimientoOrden } from "@/lib/api";
import { formatFecha } from "@/lib/format";
import { ClayBadge, ClayButton, ClayCard, ClayField, ClayInput } from "../components/ui/clay";
import { COLOR_ESTADO } from "../ordenes/tabla-ordenes";

type Fallo = { titulo: string; mensaje: string };

// El codigo impreso es SW- y 8 caracteres en mayusculas; la busqueda del backend es exacta.
function normalizar(codigo: string) {
  return codigo.replace(/\s+/g, "").toUpperCase();
}

function Detalle({ orden }: { orden: SeguimientoOrden }) {
  if (orden.estado === "En espera") {
    return <p className="mt-3 text-sm text-(--sw-ink)">Pendiente de abono: la fecha de entrega se asigna al abonar.</p>;
  }
  if (orden.estado === "Cancelada") {
    return <p className="mt-3 text-sm font-semibold text-(--sw-ink)">Esta orden fue cancelada.</p>;
  }
  return (
    <>
      {orden.estado === "Lista para entrega" && (
        <p className="mt-3 text-sm font-semibold text-(--sw-ink)">Tu pedido esta listo: ya puedes recogerlo.</p>
      )}
      {orden.fecha_estimada_entrega && (
        <p className="mt-3 text-sm text-(--sw-ink-soft)">
          Entrega estimada: {formatFecha(orden.fecha_estimada_entrega)}
        </p>
      )}
    </>
  );
}

export default function RastreoForm() {
  const [resultado, setResultado] = useState<SeguimientoOrden | null>(null);
  const [fallo, setFallo] = useState<Fallo | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const codigo = normalizar(String(new FormData(event.currentTarget).get("codigo") ?? ""));
    if (!codigo) return;
    setPending(true);
    setFallo(null);
    setResultado(null);

    const response = await rastrearOrden(codigo).catch(() => null);
    setPending(false);

    if (response?.ok) {
      setResultado((await response.json()) as SeguimientoOrden);
    } else if (response?.status === 404) {
      const { detail } = await leerErroresApi(response);
      setFallo({
        titulo: "Codigo no encontrado",
        mensaje: detail?.[0] ?? "No encontramos una orden con ese codigo. Revisa el comprobante.",
      });
    } else {
      setFallo({
        titulo: "No se pudo consultar",
        mensaje: "No pudimos consultar el estado en este momento. Intenta de nuevo en unos minutos.",
      });
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={onSubmit} className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <div className="flex-1">
          <ClayField label="Codigo de tu pedido">
            <ClayInput name="codigo" placeholder="Ej. SW-ABCD2345" autoCapitalize="characters" autoComplete="off" required />
          </ClayField>
        </div>
        <ClayButton type="submit" disabled={pending}>
          {pending ? "Buscando..." : "Rastrear"}
        </ClayButton>
      </form>

      {resultado && (
        <ClayCard>
          <p className="text-xs font-extrabold tracking-[0.08em] text-(--sw-ink-soft) uppercase">
            Pedido {resultado.codigo}
          </p>
          <div className="mt-2">
            <ClayBadge color={COLOR_ESTADO[resultado.estado]}>{resultado.estado}</ClayBadge>
          </div>
          <Detalle orden={resultado} />
        </ClayCard>
      )}

      {fallo && <AlertaErrores titulo={fallo.titulo} errores={[fallo.mensaje]} />}
    </div>
  );
}
