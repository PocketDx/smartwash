"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AlertaErrores } from "@/app/catalogo/errores";
import { crearOrden, type Cliente, type Orden, type Servicio, type Tarifa, type TipoPrenda } from "@/lib/api";
import { formatCOP } from "@/lib/format";
import { ClayButton, ClayCard, ClayField, ClaySelect } from "../../components/ui/clay";
import { aFormulario, lineaVacia, subtotalEstimado, type LineaEditable } from "../cotizacion";
import { mensajesDeOrden } from "../errores";
import LineaPrenda from "../linea-prenda";

export default function OrdenForm({
  clientes,
  tiposPrenda,
  servicios,
  tarifas,
}: {
  clientes: Cliente[];
  tiposPrenda: TipoPrenda[];
  servicios: Servicio[];
  tarifas: Tarifa[];
}) {
  const router = useRouter();
  const [cliente, setCliente] = useState("");
  const [lineas, setLineas] = useState<LineaEditable[]>(() => [lineaVacia()]);
  const [errores, setErrores] = useState<string[]>([]);
  const [pending, setPending] = useState(false);

  const subtotal = lineas.reduce((total, linea) => total + subtotalEstimado(linea, tarifas), 0);

  function actualizarLinea(clave: number, linea: LineaEditable) {
    setLineas((actuales) => actuales.map((l) => (l.clave === clave ? linea : l)));
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setErrores([]);

    const response = await crearOrden(Number(cliente), lineas.map(aFormulario)).catch(() => null);

    if (response?.ok) {
      const orden = (await response.json()) as Orden;
      router.push(`/ordenes/${orden.id}?registrada=1`);
      return;
    }
    setPending(false);
    setErrores(await mensajesDeOrden(response, "No se pudo registrar la orden"));
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-6">
      <ClayCard>
        <ClayField label="Cliente">
          <ClaySelect value={cliente} onChange={(e) => setCliente(e.target.value)} required>
            <option value="">Selecciona el cliente...</option>
            {clientes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre_completo} · {c.documento}
              </option>
            ))}
          </ClaySelect>
        </ClayField>
        <p className="mt-2 text-xs text-(--sw-ink-soft)">
          Si el cliente no aparece, registralo primero en Clientes.
        </p>
      </ClayCard>

      {lineas.length === 0 ? (
        <ClayCard>
          <p className="text-sm text-(--sw-ink-soft)">La orden no tiene prendas.</p>
        </ClayCard>
      ) : (
        lineas.map((linea, indice) => (
          <LineaPrenda
            key={linea.clave}
            titulo={`Prenda ${indice + 1}`}
            linea={linea}
            tiposPrenda={tiposPrenda}
            servicios={servicios}
            tarifas={tarifas}
            onChange={(nueva) => actualizarLinea(linea.clave, nueva)}
            onQuitar={() => setLineas((actuales) => actuales.filter((l) => l.clave !== linea.clave))}
          />
        ))
      )}

      <div>
        <ClayButton type="button" variant="secundario" onClick={() => setLineas((a) => [...a, lineaVacia()])}>
          + Agregar otra prenda
        </ClayButton>
      </div>

      <ClayCard>
        <p className="text-sm text-(--sw-ink-soft)">
          Subtotal estimado:{" "}
          <span className="text-lg font-bold text-(--sw-ink) tabular-nums">{formatCOP(subtotal)}</span>
        </p>
        <p className="mt-1 text-xs text-(--sw-ink-soft)">
          Al registrar, el sistema aplica el descuento de fidelizacion que corresponda y calcula el
          total, el abono requerido (30 %) y la duracion estimada. La orden queda &quot;En espera&quot;
          hasta que se registre el abono.
        </p>
      </ClayCard>

      <AlertaErrores titulo="No se pudo registrar la orden" errores={errores} />

      <div className="flex flex-wrap gap-3">
        <ClayButton type="submit" disabled={pending}>
          {pending ? "Registrando..." : "Registrar orden"}
        </ClayButton>
        <ClayButton type="button" variant="secundario" disabled={pending} onClick={() => router.push("/ordenes")}>
          Cancelar
        </ClayButton>
      </div>
    </form>
  );
}
