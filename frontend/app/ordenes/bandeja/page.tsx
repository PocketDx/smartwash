import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { getBandeja, getCurrentUser } from "@/lib/api";
import { formatFecha } from "@/lib/format";
import { ClayBadge, ClayCard, Encabezado } from "../../components/ui/clay";
import { agruparPrendas, detallesDe } from "../agrupar";
import { COLOR_ESTADO } from "../tabla-ordenes";

function Mensaje({ children }: { children: string }) {
  return (
    <ClayCard>
      <p className="text-sm text-(--sw-ink-soft)">{children}</p>
    </ClayCard>
  );
}

export default async function BandejaPage() {
  const cookieStore = await cookies();
  const user = await getCurrentUser(cookieStore);
  if (!user) redirect("/login");
  if (user.rol !== "operario") redirect("/ordenes");

  const ordenes = await getBandeja(cookieStore);

  return (
    <main className="mx-auto max-w-4xl px-4 py-8 sm:px-8 sm:py-12">
      <Encabezado eyebrow="Operacion · Mi bandeja" titulo="Mi bandeja">
        Ordenes asignadas a ti que aun no se entregan, de la entrega mas proxima a la mas lejana.
      </Encabezado>

      {ordenes === null ? (
        <Mensaje>No se pudo cargar tu bandeja. Verifica que el backend este en ejecucion.</Mensaje>
      ) : ordenes.length === 0 ? (
        <Mensaje>Tu bandeja esta vacia: no tienes ordenes asignadas pendientes.</Mensaje>
      ) : (
        <div className="flex flex-col gap-4">
          {ordenes.map((orden) => (
            <ClayCard key={orden.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <Link href={`/ordenes/${orden.id}`} className="font-bold text-(--sw-ink) hover:underline">
                    {orden.codigo}
                  </Link>
                  <p className="mt-1 text-xs text-(--sw-ink-soft)">
                    Entrega estimada:{" "}
                    {orden.fecha_estimada_entrega ? formatFecha(orden.fecha_estimada_entrega) : "sin fecha"}
                  </p>
                </div>
                <ClayBadge color={COLOR_ESTADO[orden.estado]}>{orden.estado}</ClayBadge>
              </div>
              <ul className="mt-4 flex flex-col gap-2 text-sm">
                {agruparPrendas(orden.prendas, (p) => p.servicios.join(",")).map((grupo) => {
                  const [prenda] = grupo.prendas;
                  const detalles = detallesDe(grupo);
                  return (
                    <li key={prenda.id} className="border-t border-(--sw-hairline) pt-2">
                      <p className="font-semibold text-(--sw-ink)">
                        {grupo.cantidad} × {prenda.tipo_prenda_nombre}
                        <span className="font-normal text-(--sw-ink-soft)"> · {prenda.servicios.join(", ")}</span>
                      </p>
                      {detalles.length > 0 && (
                        <p className="mt-0.5 text-xs text-(--sw-ink-soft)">{detalles.join(" · ")}</p>
                      )}
                      {prenda.estado_inicial && (
                        <p className="mt-0.5 text-xs text-(--sw-ink-soft)">Al recibir: {prenda.estado_inicial}</p>
                      )}
                    </li>
                  );
                })}
              </ul>
            </ClayCard>
          ))}
        </div>
      )}
    </main>
  );
}
