"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { crearTarifa, type Servicio, type TipoPrenda } from "@/lib/api";
import { cx } from "@/lib/cx";
import { ClayButton, ClayField, ClayInput, ClaySelect } from "../components/ui/clay";
import { AlertaErrores, mensajesDeError } from "./errores";

export const ETIQUETAS_TARIFA = {
  tipo_prenda: "Tipo de prenda",
  servicio: "Servicio",
  valor_base: "Valor base por prenda",
  precio_por_kilo: "Precio por kilo",
  plazo_entrega_dias: "Plazo de entrega",
  vigente_desde: "Vigente desde",
  vigente_hasta: "Vigente hasta",
};

export default function TarifaForm({
  tiposPrenda,
  servicios,
  general,
  className,
}: {
  tiposPrenda: TipoPrenda[];
  servicios: Servicio[];
  general: boolean;
  className?: string;
}) {
  const router = useRouter();
  const [errores, setErrores] = useState<string[]>([]);
  const [creada, setCreada] = useState(false);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // currentTarget queda en null despues del await.
    const formulario = event.currentTarget;
    setPending(true);
    setErrores([]);
    setCreada(false);

    const form = new FormData(formulario);
    const response = await crearTarifa({
      tipo_prenda: general ? null : Number(form.get("tipo_prenda")),
      servicio: Number(form.get("servicio")),
      valor_base: String(form.get("valor_base") ?? "0"),
      precio_por_kilo: String(form.get("precio_por_kilo") ?? "0"),
      plazo_entrega_dias: Number(form.get("plazo_entrega_dias") ?? 1),
      vigente_desde: String(form.get("vigente_desde") ?? ""),
      vigente_hasta: null,
    }).catch(() => null);
    setPending(false);

    if (response?.ok) {
      formulario.reset();
      setCreada(true);
      router.refresh();
      return;
    }
    setErrores(await mensajesDeError(response, ETIQUETAS_TARIFA, "No se pudo crear la tarifa"));
  }

  if ((!general && tiposPrenda.length === 0) || servicios.length === 0) {
    return (
      <p className="text-sm text-(--sw-ink-soft)">
        Para crear una tarifa primero registra al menos un servicio (y un tipo de prenda para una excepcion).
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} className={cx("grid grid-cols-1 gap-4 sm:grid-cols-2", className)}>
      {!general && (
        <ClayField label="Tipo de prenda">
          <ClaySelect name="tipo_prenda" required>
            {tiposPrenda.map((tipo) => (
              <option key={tipo.id} value={tipo.id}>
                {tipo.nombre}
              </option>
            ))}
          </ClaySelect>
        </ClayField>
      )}
      <ClayField label="Servicio">
        <ClaySelect name="servicio" required>
          {servicios.map((servicio) => (
            <option key={servicio.id} value={servicio.id}>
              {servicio.nombre}
            </option>
          ))}
        </ClaySelect>
      </ClayField>
      <ClayField label="Valor base por prenda (COP)">
        <ClayInput name="valor_base" type="number" min="0" step="0.01" defaultValue="0" required />
      </ClayField>
      <ClayField label="Precio por kilo (COP)">
        <ClayInput name="precio_por_kilo" type="number" min="0" step="0.01" defaultValue="0" required />
      </ClayField>
      <ClayField label="Plazo de entrega (dias)">
        <ClayInput name="plazo_entrega_dias" type="number" min="1" required />
      </ClayField>
      <ClayField label="Vigente desde">
        <ClayInput name="vigente_desde" type="date" required />
      </ClayField>

      <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
        <ClayButton type="submit" disabled={pending}>
          {pending ? "Guardando..." : "Agregar tarifa"}
        </ClayButton>
        {creada && (
          <p role="status" className="text-sm text-(--sw-ink-soft)">
            Tarifa creada.
          </p>
        )}
      </div>

      {errores.length > 0 && (
        <div className="sm:col-span-2">
          <AlertaErrores titulo="No se pudo crear la tarifa" errores={errores} />
        </div>
      )}
    </form>
  );
}
