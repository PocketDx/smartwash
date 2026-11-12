import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { getCurrentUser, getOrden, getOrdenesConNovedad, getServicios, getTarifas } from "@/lib/api";
import { ClayCard, Encabezado, clayBtnClass } from "../../components/ui/clay";
import DecisionProceso from "../[id]/decision-proceso";
import { tarifasDeHoy } from "../cotizacion";
import NovedadesOrden from "../[id]/novedades-orden";

export default async function OrdenesConNovedadPage() {
  const cookieStore = await cookies();
  const user = await getCurrentUser(cookieStore);
  if (!user) redirect("/login");
  if (user.rol === "operario") redirect("/");

  const [ordenes, servicios, tarifas] = await Promise.all([
    getOrdenesConNovedad(cookieStore),
    getServicios(cookieStore),
    getTarifas(cookieStore, true),
  ]);
  // Para agregar servicios hacen falta las prendas con sus servicios actuales.
  const detalles = await Promise.all((ordenes ?? []).map((o) => getOrden(o.id, cookieStore)));
  const tarifasVigentes = tarifas ? tarifasDeHoy(tarifas) : null;

  return (
    <main className="mx-auto max-w-4xl px-4 py-8 sm:px-8 sm:py-12">
      <Encabezado eyebrow="Incidencias · HU19" titulo="Ordenes con novedad">
        Ordenes detenidas hasta que el cliente decida. Contactalo por el medio que ya usa y registra aqui lo que
        decidio.
      </Encabezado>

      {ordenes === null ? (
        <ClayCard>
          <p className="text-sm text-(--sw-ink-soft)">
            No se pudieron cargar las ordenes con novedad. Verifica que el backend este en ejecucion.
          </p>
        </ClayCard>
      ) : ordenes.length === 0 ? (
        <ClayCard>
          <p className="text-sm text-(--sw-ink-soft)">No hay ordenes con novedad pendiente.</p>
        </ClayCard>
      ) : (
        ordenes.map((orden, i) => (
          <section key={orden.id} className="mb-8">
            <NovedadesOrden
              novedades={orden.novedades}
              encabezado={
                <div>
                  <h2 className="text-lg font-bold text-(--sw-ink)">
                    <Link href={`/ordenes/${orden.id}`} className="hover:underline">
                      {orden.codigo}
                    </Link>
                  </h2>
                  <p className="text-sm text-(--sw-ink-soft)">
                    {orden.cliente_nombre} · Operario: {orden.operario_nombre ?? "Sin asignar"}
                  </p>
                </div>
              }
            >
              {orden.novedades.some((n) => n.origen === "entrega") && (
                <div className="mt-4 border-t border-(--sw-hairline) pt-4">
                  <p className="text-sm text-(--sw-ink-soft)">
                    Detectada en la entrega: el cliente decide si se la lleva con descuento o si se reprocesa.
                  </p>
                  <Link href={`/ordenes/${orden.id}`} className={`${clayBtnClass()} mt-3`}>
                    Registrar la decision
                  </Link>
                </div>
              )}
            </NovedadesOrden>
            {detalles[i] && (
              <DecisionProceso
                orden={detalles[i]}
                novedades={orden.novedades}
                servicios={servicios}
                tarifas={tarifasVigentes}
              />
            )}
          </section>
        ))
      )}
    </main>
  );
}
