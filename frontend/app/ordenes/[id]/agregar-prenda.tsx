"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AlertaErrores } from "@/app/catalogo/errores";
import { agregarPrendaAOrden, type Material, type Servicio, type Tarifa, type TipoPrenda } from "@/lib/api";
import { ClayButton } from "../../components/ui/clay";
import { aFormularios, erroresDeServicios, lineaVacia, nombresDeUnidades, type LineaEditable } from "../cotizacion";
import { mensajesDeOrden } from "../errores";
import LineaPrenda from "../linea-prenda";

export default function AgregarPrenda({
  ordenId,
  tiposPrenda,
  materiales,
  servicios,
  tarifas,
}: {
  ordenId: number;
  tiposPrenda: TipoPrenda[];
  materiales: Material[];
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
    const faltantes = erroresDeServicios([linea], tiposPrenda);
    if (faltantes.length > 0) {
      setErrores(faltantes);
      return;
    }
    setPending(true);
    setErrores([]);

    const prendas = aFormularios(linea);
    const nombres = nombresDeUnidades([linea], tiposPrenda);
    let creadas = 0;
    for (const prenda of prendas) {
      const response = await agregarPrendaAOrden(ordenId, prenda).catch(() => null);
      if (!response?.ok) {
        const mensajes = await mensajesDeOrden(response, "No se pudo agregar la prenda");
        setErrores(mensajes.map((m) => `${nombres[creadas]} · ${m}`));
        break;
      }
      creadas += 1;
    }
    setPending(false);
    if (creadas > 0) router.refresh();
    if (creadas === prendas.length) cerrar();
    else if (creadas > 0) {
      // Las ya creadas quedan en la orden: se quitan del formulario para no duplicarlas al reintentar.
      setLinea(
        linea.detallar
          ? { ...linea, cantidad: String(prendas.length - creadas), unidades: linea.unidades.slice(creadas) }
          : { ...linea, cantidad: String(prendas.length - creadas) },
      );
    }
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
        materiales={materiales}
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
