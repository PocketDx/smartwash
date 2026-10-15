import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { getCurrentUser, getOrdenes } from "@/lib/api";
import { ClayCard, Encabezado, clayBtnClass } from "../components/ui/clay";
import TablaOrdenes from "./tabla-ordenes";

export default async function OrdenesPage() {
  const cookieStore = await cookies();
  const user = await getCurrentUser(cookieStore);
  if (!user) redirect("/login");

  const ordenes = await getOrdenes(cookieStore);

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-8 sm:py-12">
      <Encabezado
        eyebrow="Operacion · EP04"
        titulo="Ordenes"
        acciones={
          user.rol !== "operario" && (
            <Link href="/ordenes/nueva" className={clayBtnClass()}>
              Nueva orden
            </Link>
          )
        }
      >
        Sigue el estado de las ordenes en curso (EP04/EP05).
      </Encabezado>

      {ordenes === null ? (
        <ClayCard>
          <p className="text-sm text-(--sw-ink-soft)">
            No se pudieron cargar las ordenes. Verifica que el backend este en ejecucion.
          </p>
        </ClayCard>
      ) : (
        <TablaOrdenes ordenes={ordenes} />
      )}
    </main>
  );
}
