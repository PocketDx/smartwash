"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AlertaErrores } from "@/app/catalogo/errores";
import { registrarDecision, type Novedad, type Orden, type Servicio, type Tarifa } from "@/lib/api";
import { formatCOP } from "@/lib/format";
import { ClayButton, ClayCard, ClayTextarea } from "../../components/ui/clay";
import { tarifaDe } from "../cotizacion";
import { mensajesDeOrden } from "../errores";

type Opcion = "continuar" | "agregar_servicio";
// Clave "prenda:servicio" de cada casilla marcada.
type Marcados = Set<string>;

export default function DecisionProceso({
  orden,
  novedades,
  servicios,
  tarifas,
}: {
  orden: Orden;
  novedades: Novedad[];
  servicios: Servicio[] | null;
  tarifas: Tarifa[] | null;
}) {
  const router = useRouter();
  // "No continuar" ya no se ofrece, pero las ordenes que lo registraron antes siguen pendientes.
  const pendientes = novedades.filter(
    (n) => n.origen === "proceso" && (n.decision === null || n.decision === "no_continuar"),
  );
  const [opcion, setOpcion] = useState<Opcion | null>(null);
  const [marcados, setMarcados] = useState<Marcados>(new Set());
  const [observacion, setObservacion] = useState("");
  const [errores, setErrores] = useState<string[]>([]);
  const [pending, setPending] = useState(false);

  if (pendientes.length === 0) return null;

  const estadoAnterior = pendientes[0].estado_anterior;
  const yaNoContinua = pendientes.some((n) => n.decision === "no_continuar");
  const idsConNovedad = new Set(pendientes.map((n) => n.prenda));
  const prendas = orden.detalle_prendas
    .filter((p) => idsConNovedad.has(p.id))
    .map((prenda) => {
      const yaTiene = new Set(prenda.servicios.map((s) => s.servicio));
      const disponibles = (servicios ?? []).flatMap((s) => {
        const tarifa = tarifas && !yaTiene.has(s.id) ? tarifaDe(tarifas, prenda.tipo_prenda, s.id) : undefined;
        return tarifa ? [{ servicio: s, tarifa }] : [];
      });
      return { prenda, disponibles };
    });
  const listo =
    opcion !== null && observacion.trim() !== "" && (opcion === "continuar" || marcados.size > 0);

  function marcar(clave: string) {
    setMarcados((actual) => {
      const siguiente = new Set(actual);
      if (siguiente.has(clave)) siguiente.delete(clave);
      else siguiente.add(clave);
      return siguiente;
    });
  }

  function cancelar() {
    setOpcion(null);
    setMarcados(new Set());
    setObservacion("");
    setErrores([]);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!opcion) return;
    setPending(true);
    setErrores([]);
    const response = await registrarDecision(orden.id, {
      decision: opcion,
      observacion: observacion.trim(),
      ...(opcion === "agregar_servicio" && {
        servicios: [...marcados].map((clave) => {
          const [prenda, servicio] = clave.split(":").map(Number);
          return { prenda, servicio };
        }),
      }),
    }).catch(() => null);
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
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name={`decision-proceso-${orden.id}`}
              checked={opcion === "continuar"}
              onChange={() => setOpcion("continuar")}
              required
            />
            Continuar igual (vuelve a &quot;{estadoAnterior}&quot;)
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name={`decision-proceso-${orden.id}`}
              checked={opcion === "agregar_servicio"}
              onChange={() => setOpcion("agregar_servicio")}
            />
            Agregar servicio
          </label>
        </div>

        {opcion === "agregar_servicio" && (
          <div className="flex flex-col gap-3">
            {prendas.map(({ prenda, disponibles }) => (
              <fieldset key={prenda.id} className="clay-sm flex flex-col gap-2 p-4 text-sm">
                <legend className="sr-only">Servicios para {prenda.tipo_prenda_nombre}</legend>
                <p className="font-semibold text-(--sw-ink)">
                  {prenda.cantidad} × {prenda.tipo_prenda_nombre}
                  {prenda.material_nombre && ` · ${prenda.material_nombre}`}
                  <span className="font-normal text-(--sw-ink-soft)">
                    {" "}
                    · ya tiene {prenda.servicios.map((s) => s.servicio_nombre).join(", ")}
                  </span>
                </p>
                {disponibles.length === 0 ? (
                  <p className="text-(--sw-ink-soft)">No hay otros servicios con tarifa vigente para esta prenda.</p>
                ) : (
                  disponibles.map(({ servicio, tarifa }) => {
                    const clave = `${prenda.id}:${servicio.id}`;
                    return (
                      <label key={clave} className="flex items-center gap-2 text-(--sw-ink)">
                        <input type="checkbox" checked={marcados.has(clave)} onChange={() => marcar(clave)} />
                        {servicio.nombre}
                        <span className="text-xs text-(--sw-ink-soft)">
                          {formatCOP(tarifa.valor_base)} + {formatCOP(tarifa.precio_por_kilo)}/kg
                        </span>
                      </label>
                    );
                  })
                )}
              </fieldset>
            ))}
            <p className="text-xs text-(--sw-ink-soft)">
              El valor de cada servicio se calcula con el peso y el material de la prenda. Se suma al total y al
              saldo pendiente (el abono ya hecho se conserva), la orden vuelve a &quot;En proceso&quot; y la fecha
              estimada se recalcula desde hoy. La orden no se entrega hasta que se pague completa.
            </p>
          </div>
        )}

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
          <ClayButton type="submit" disabled={pending || !listo}>
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
