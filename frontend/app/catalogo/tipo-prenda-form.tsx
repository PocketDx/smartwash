"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { actualizarTipoPrenda, crearTipoPrenda, type TipoPrenda } from "@/lib/api";
import { cx } from "@/lib/cx";
import { ClayButton, ClayField, ClayInput } from "../components/ui/clay";
import { AlertaErrores, mensajesDeError } from "./errores";

const ETIQUETAS = { nombre: "Nombre", peso_estandar: "Peso estandar" };

export default function TipoPrendaForm({
  tipoPrenda,
  onTerminar,
  className,
}: {
  tipoPrenda?: TipoPrenda;
  onTerminar?: () => void;
  className?: string;
}) {
  const router = useRouter();
  const [errores, setErrores] = useState<string[]>([]);
  const [creado, setCreado] = useState(false);
  const [pending, setPending] = useState(false);
  const editando = tipoPrenda !== undefined;
  const accion = editando ? "actualizar" : "crear";

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // currentTarget queda en null despues del await.
    const formulario = event.currentTarget;
    setPending(true);
    setErrores([]);
    setCreado(false);

    const form = new FormData(formulario);
    const datos = {
      nombre: String(form.get("nombre") ?? "").trim(),
      peso_estandar: String(form.get("peso_estandar") ?? "").trim() || null,
    };
    const response = await (
      tipoPrenda ? actualizarTipoPrenda(tipoPrenda.id, datos) : crearTipoPrenda(datos)
    ).catch(() => null);
    setPending(false);

    if (response?.ok) {
      if (editando) {
        onTerminar?.();
      } else {
        formulario.reset();
        setCreado(true);
      }
      router.refresh();
      return;
    }
    setErrores(await mensajesDeError(response, ETIQUETAS, `No se pudo ${accion} el tipo de prenda`));
  }

  return (
    <form onSubmit={onSubmit} className={cx("grid grid-cols-1 gap-4 sm:grid-cols-2", className)}>
      <ClayField label="Nombre del tipo de prenda">
        <ClayInput
          name="nombre"
          defaultValue={tipoPrenda?.nombre}
          placeholder="Camisa, pantalon, cobija..."
          maxLength={80}
          required
        />
      </ClayField>
      <ClayField label="Peso estandar (kg)">
        <ClayInput
          name="peso_estandar"
          type="number"
          min="0.01"
          step="0.01"
          defaultValue={tipoPrenda?.peso_estandar ?? ""}
          placeholder="Prellena el peso al registrar la orden"
        />
      </ClayField>

      <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
        <ClayButton type="submit" disabled={pending}>
          {pending ? "Guardando..." : editando ? "Guardar cambios" : "Agregar tipo de prenda"}
        </ClayButton>
        {editando && (
          <ClayButton type="button" variant="secundario" onClick={onTerminar} disabled={pending}>
            Cancelar
          </ClayButton>
        )}
        {creado && (
          <p role="status" className="text-sm text-(--sw-ink-soft)">
            Tipo de prenda creado.
          </p>
        )}
      </div>

      {errores.length > 0 && (
        <div className="sm:col-span-2">
          <AlertaErrores titulo={`No se pudo ${accion} el tipo de prenda`} errores={errores} />
        </div>
      )}
    </form>
  );
}
