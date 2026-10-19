"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { actualizarNivelDificultad, crearNivelDificultad, type NivelDificultad } from "@/lib/api";
import { cx } from "@/lib/cx";
import { ClayButton, ClayField, ClayInput } from "../components/ui/clay";
import { AlertaErrores, mensajesDeError } from "./errores";

const ETIQUETAS = { nombre: "Nombre", factor: "Factor" };

export default function NivelForm({
  nivel,
  onTerminar,
  className,
}: {
  nivel?: NivelDificultad;
  onTerminar?: () => void;
  className?: string;
}) {
  const router = useRouter();
  const [errores, setErrores] = useState<string[]>([]);
  const [creado, setCreado] = useState(false);
  const [pending, setPending] = useState(false);
  const editando = nivel !== undefined;
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
      factor: String(form.get("factor") ?? "").trim(),
    };
    const response = await (
      nivel ? actualizarNivelDificultad(nivel.id, datos) : crearNivelDificultad(datos)
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
    setErrores(await mensajesDeError(response, ETIQUETAS, `No se pudo ${accion} el nivel`));
  }

  return (
    <form onSubmit={onSubmit} className={cx("grid grid-cols-1 gap-4 sm:grid-cols-2", className)}>
      <ClayField label="Nombre del nivel">
        <ClayInput
          name="nombre"
          defaultValue={nivel?.nombre}
          placeholder="Facil, medio, dificil..."
          maxLength={80}
          required
        />
      </ClayField>
      <ClayField label="Factor (multiplica el precio de los servicios)">
        <ClayInput
          name="factor"
          type="number"
          min="0.01"
          step="0.01"
          defaultValue={nivel?.factor}
          placeholder="1.00, 1.30, 1.60..."
          required
        />
      </ClayField>
      <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
        <ClayButton type="submit" disabled={pending}>
          {pending ? "Guardando..." : editando ? "Guardar cambios" : "Agregar nivel"}
        </ClayButton>
        {editando && (
          <ClayButton type="button" variant="secundario" onClick={onTerminar} disabled={pending}>
            Cancelar
          </ClayButton>
        )}
        {creado && (
          <p role="status" className="text-sm text-(--sw-ink-soft)">
            NivelDificultad creado.
          </p>
        )}
      </div>

      {errores.length > 0 && (
        <div className="sm:col-span-2">
          <AlertaErrores titulo={`No se pudo ${accion} el nivel`} errores={errores} />
        </div>
      )}
    </form>
  );
}
