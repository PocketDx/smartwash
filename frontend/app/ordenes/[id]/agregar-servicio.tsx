"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AlertaErrores } from "@/app/catalogo/errores";
import { agregarServicioAPrenda, type PrendaDeOrden, type Servicio, type Tarifa } from "@/lib/api";
import { formatCOP } from "@/lib/format";
import { ClayButton, ClaySelect } from "../../components/ui/clay";
import { tarifaDe } from "../cotizacion";
import { mensajesDeOrden } from "../errores";

export default function AgregarServicio({
  ordenId,
  prenda,
  servicios,
  tarifas,
}: {
  ordenId: number;
  prenda: PrendaDeOrden;
  servicios: Servicio[];
  tarifas: Tarifa[];
}) {
  const router = useRouter();
  const [servicio, setServicio] = useState("");
  const [errores, setErrores] = useState<string[]>([]);
  const [pending, setPending] = useState(false);

  const yaTiene = new Set(prenda.servicios.map((s) => s.servicio));
  const disponibles = servicios.filter(
    (s) => !yaTiene.has(s.id) && tarifaDe(tarifas, prenda.tipo_prenda, s.id),
  );
  if (disponibles.length === 0) return null;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setErrores([]);

    const response = await agregarServicioAPrenda(ordenId, prenda.id, Number(servicio)).catch(() => null);
    setPending(false);

    if (response?.ok) {
      setServicio("");
      router.refresh();
      return;
    }
    setErrores(await mensajesDeOrden(response, "No se pudo agregar el servicio"));
  }

  return (
    <form onSubmit={onSubmit} className="mt-3 flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <ClaySelect
          value={servicio}
          onChange={(e) => setServicio(e.target.value)}
          aria-label={`Servicio adicional para ${prenda.tipo_prenda_nombre}`}
          className="h-9 w-auto text-xs"
          required
        >
          <option value="">Agregar servicio...</option>
          {disponibles.map((s) => {
            const tarifa = tarifaDe(tarifas, prenda.tipo_prenda, s.id);
            return (
              <option key={s.id} value={s.id}>
                {s.nombre}
                {tarifa ? ` · ${formatCOP(tarifa.valor)} por ${tarifa.unidad_cobro}` : ""}
              </option>
            );
          })}
        </ClaySelect>
        <ClayButton type="submit" variant="secundario" disabled={pending || !servicio} className="h-9">
          {pending ? "Agregando..." : "Agregar"}
        </ClayButton>
      </div>
      <AlertaErrores titulo="No se pudo agregar el servicio" errores={errores} />
    </form>
  );
}
