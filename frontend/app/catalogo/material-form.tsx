"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { actualizarMaterial, crearMaterial, type Material, type NivelDificultad } from "@/lib/api";
import { cx } from "@/lib/cx";
import { ClayButton, ClayField, ClayInput, ClaySelect } from "../components/ui/clay";
import { AlertaErrores, mensajesDeError } from "./errores";

const ETIQUETAS = { nombre: "Nombre", nivel_dificultad: "Nivel de dificultad" };

export default function MaterialForm({
  material,
  niveles,
  onTerminar,
  className,
}: {
  material?: Material;
  niveles: NivelDificultad[];
  onTerminar?: () => void;
  className?: string;
}) {
  const router = useRouter();
  const [errores, setErrores] = useState<string[]>([]);
  const [creado, setCreado] = useState(false);
  const [pending, setPending] = useState(false);
  const editando = material !== undefined;
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
      nivel_dificultad: Number(form.get("nivel_dificultad")),
    };
    const response = await (
      material ? actualizarMaterial(material.id, datos) : crearMaterial(datos)
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
    setErrores(await mensajesDeError(response, ETIQUETAS, `No se pudo ${accion} el material`));
  }

  return (
    <form onSubmit={onSubmit} className={cx("grid grid-cols-1 gap-4 sm:grid-cols-2", className)}>
      <ClayField label="Nombre del material">
        <ClayInput
          name="nombre"
          defaultValue={material?.nombre}
          placeholder="Algodon, jean, lana, seda..."
          maxLength={80}
          required
        />
      </ClayField>
      <ClayField label="Nivel de dificultad">
        <ClaySelect name="nivel_dificultad" defaultValue={material?.nivel_dificultad ?? ""} required>
          <option value="">Selecciona...</option>
          {niveles.map((n) => (
            <option key={n.id} value={n.id}>
              {n.nombre} (x{Number(n.factor)})
            </option>
          ))}
        </ClaySelect>
      </ClayField>
      <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
        <ClayButton type="submit" disabled={pending}>
          {pending ? "Guardando..." : editando ? "Guardar cambios" : "Agregar material"}
        </ClayButton>
        {editando && (
          <ClayButton type="button" variant="secundario" onClick={onTerminar} disabled={pending}>
            Cancelar
          </ClayButton>
        )}
        {creado && (
          <p role="status" className="text-sm text-(--sw-ink-soft)">
            Material creado.
          </p>
        )}
      </div>

      {errores.length > 0 && (
        <div className="sm:col-span-2">
          <AlertaErrores titulo={`No se pudo ${accion} el material`} errores={errores} />
        </div>
      )}
    </form>
  );
}
