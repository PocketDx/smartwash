"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AlertaErrores } from "@/app/catalogo/errores";
import { agregarPrendaAOrden, type Servicio, type Tarifa, type TipoPrenda } from "@/lib/api";
import { ClayButton } from "../../components/ui/clay";
import { aFormulario, lineaVacia, type LineaEditable } from "../cotizacion";
import { mensajesDeOrden } from "../errores";
import LineaPrenda from "../linea-prenda";

export default function AgregarPrenda({
  ordenId,
  tiposPrenda,
  servicios,
  tarifas,
}: {
  ordenId: number;
  tiposPrenda: TipoPrenda[];
  servicios: Servicio[];
  tarifas: Tarifa[];
}) {
  const router = useRouter();
  const [linea, setLinea] = useState<LineaEditable | null>(null);
  const [errores, setErrores] = useState<string[]>([]);
  const [pending, setPending] = useState(false);

  function cerrar() {
    setLinea(null);
    setErrores([]);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!linea) return;
    setPending(true);
    setErrores([]);

    const response = await agregarPrendaAOrden(ordenId, aFormulario(linea)).catch(() => null);
    setPending(false);

    if (response?.ok) {
      cerrar();
      router.refresh();
      return;
    }
    setErrores(await mensajesDeOrden(response, "No se pudo agregar la prenda"));
  }

  if (!linea) {
    return (
      <ClayButton type="button" variant="secundario" onClick={() => setLinea(lineaVacia())}>
        + Agregar prenda
      </ClayButton>
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <LineaPrenda
        titulo="Prenda nueva"
        linea={linea}
        tiposPrenda={tiposPrenda}
        servicios={servicios}
        tarifas={tarifas}
        onChange={setLinea}
      />
      <AlertaErrores titulo="No se pudo agregar la prenda" errores={errores} />
      <div className="flex flex-wrap gap-3">
        <ClayButton type="submit" disabled={pending}>
          {pending ? "Agregando..." : "Agregar a la orden"}
        </ClayButton>
        <ClayButton type="button" variant="secundario" disabled={pending} onClick={cerrar}>
          Cancelar
        </ClayButton>
      </div>
    </form>
  );
}
