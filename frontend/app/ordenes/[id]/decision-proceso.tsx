"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AlertaErrores } from "@/app/catalogo/errores";
import { registrarDecision, type Novedad } from "@/lib/api";
import { ClayButton, ClayCard, ClayTextarea } from "../../components/ui/clay";
import { mensajesDeOrden } from "../errores";

type Opcion = "continuar" | "reprocesar" | "no_continuar";

export default function DecisionProceso({ ordenId, novedades }: { ordenId: number; novedades: Novedad[] }) {
  const router = useRouter();
  // "No continuar" deja la novedad abierta: se puede volver a decidir o cancelar la orden (HU13).
  const pendientes = novedades.filter(
    (n) => n.origen === "proceso" && (n.decision === null || n.decision === "no_continuar"),
  );
  const [opcion, setOpcion] = useState<Opcion | null>(null);
  const [observacion, setObservacion] = useState("");
  const [errores, setErrores] = useState<string[]>([]);
  const [pending, setPending] = useState(false);

  if (pendientes.length === 0) return null;

  const estadoAnterior = pendientes[0].estado_anterior;
  const yaNoContinua = pendientes.some((n) => n.decision === "no_continuar");
  const opciones: { valor: Opcion; etiqueta: string }[] = [
    { valor: "continuar", etiqueta: `Continuar igual (vuelve a "${estadoAnterior}")` },
    { valor: "reprocesar", etiqueta: "Reprocesar, sin costo ni descuento" },
    { valor: "no_continuar", etiqueta: "No continuar" },
  ];

  function cancelar() {
    setOpcion(null);
    setObservacion("");
    setErrores([]);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!opcion) return;
    setPending(true);
    setErrores([]);
    const response = await registrarDecision(ordenId, { decision: opcion, observacion: observacion.trim() }).catch(
      () => null,
    );
    setPending(false);

    if (response?.ok) {
      cancelar();
      router.refresh();
      return;
    }
    setErrores(await mensajesDeOrden(response, "No se pudo registrar la decision"));
  }

  return (
    <ClayCard className="mb-6">
      <h2 className="text-sm font-bold text-(--sw-ink)">Decision del cliente</h2>
      <p className="mt-1 text-sm text-(--sw-ink-soft)">
        La novedad se detecto durante el proceso. Contacta al cliente y registra lo que decidio; la decision
        aplica a toda la orden.
      </p>
      {yaNoContinua && (
        <p role="status" className="mt-2 text-sm font-semibold text-(--sw-ink)">
          El cliente ya dijo que no desea continuar. Puedes registrar una nueva decision o cancelar la orden con
          su motivo.
        </p>
      )}
      <form onSubmit={onSubmit} className="mt-3 flex flex-col gap-4">
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm text-(--sw-ink)">
          {opciones.map((o, i) => (
            <label key={o.valor} className="flex items-center gap-2">
              <input
                type="radio"
                name={`decision-proceso-${ordenId}`}
                checked={opcion === o.valor}
                onChange={() => setOpcion(o.valor)}
                required={i === 0}
              />
              {o.etiqueta}
            </label>
          ))}
        </div>
        <ClayTextarea
          aria-label="Observacion de la decision"
          placeholder="Con quien se hablo y que decidio (obligatorio)"
          value={observacion}
          onChange={(e) => setObservacion(e.target.value)}
          className="min-h-20"
          required
        />
        <AlertaErrores titulo="No se pudo registrar la decision" errores={errores} />
        <div className="flex flex-wrap gap-3">
          <ClayButton type="submit" disabled={pending || opcion === null || observacion.trim() === ""}>
            {pending ? "Registrando..." : "Registrar decision"}
          </ClayButton>
          <ClayButton type="button" variant="secundario" onClick={cancelar} disabled={pending}>
            Cancelar
          </ClayButton>
        </div>
      </form>
    </ClayCard>
  );
}
