import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getCurrentUser, getMateriales, getServicios, getTarifas, getTiposPrenda } from "@/lib/api";
import { ClayCard, Encabezado } from "../components/ui/clay";
import FiltroVigencia from "./filtro-vigencia";
import MaterialForm from "./material-form";
import ServicioForm from "./servicio-form";
import TablaTarifas from "./tabla-tarifas";
import { TablaMateriales, TablaServicios, TablaTiposPrenda } from "./tabla-catalogo";
import TarifaForm from "./tarifa-form";
import TipoPrendaForm from "./tipo-prenda-form";

function ErrorDeCarga({ recurso }: { recurso: string }) {
  return (
    <ClayCard>
      <p className="text-sm text-(--sw-ink-soft)">
        No se pudieron cargar {recurso}. Verifica que el backend este en ejecucion.
      </p>
    </ClayCard>
  );
}

export default async function CatalogoPage({
  searchParams,
}: {
  searchParams: Promise<{ vigentes?: string }>;
}) {
  const cookieStore = await cookies();
  const user = await getCurrentUser(cookieStore);
  if (!user) redirect("/login");
  const puedeEditar = user.rol === "administrador";

  const soloVigentes = (await searchParams).vigentes === "1";
  const [tiposPrenda, materiales, servicios, tarifas] = await Promise.all([
    getTiposPrenda(cookieStore),
    getMateriales(cookieStore),
    getServicios(cookieStore),
    getTarifas(cookieStore, soloVigentes),
  ]);

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-8 sm:py-12">
      <Encabezado eyebrow="Administracion · EP03" titulo="Catalogo">
        {puedeEditar
          ? "Administra tipos de prenda, materiales, servicios y las tarifas por tipo de prenda y servicio (HU07)."
          : "Consulta tipos de prenda, materiales, servicios y las tarifas por tipo de prenda y servicio (HU07)."}
      </Encabezado>

      {puedeEditar && (
        <ClayCard className="mb-4">
          <h2 className="sw-eyebrow">Nuevo tipo de prenda</h2>
          <TipoPrendaForm className="mt-4" />
        </ClayCard>
      )}
      <div className="mb-6">
        {tiposPrenda === null ? (
          <ErrorDeCarga recurso="los tipos de prenda" />
        ) : (
          <TablaTiposPrenda tiposPrenda={tiposPrenda} editable={puedeEditar} />
        )}
      </div>

      {puedeEditar && (
        <ClayCard className="mb-4">
          <h2 className="sw-eyebrow">Nuevo material</h2>
          <MaterialForm className="mt-4" />
        </ClayCard>
      )}
      <div className="mb-6">
        {materiales === null ? (
          <ErrorDeCarga recurso="los materiales" />
        ) : (
          <TablaMateriales materiales={materiales} editable={puedeEditar} />
        )}
      </div>

      {puedeEditar && (
        <ClayCard className="mb-4">
          <h2 className="sw-eyebrow">Nuevo servicio</h2>
          <ServicioForm className="mt-4" />
        </ClayCard>
      )}
      <div className="mb-6">
        {servicios === null ? (
          <ErrorDeCarga recurso="los servicios" />
        ) : (
          <TablaServicios servicios={servicios} editable={puedeEditar} />
        )}
      </div>

      {puedeEditar && (
        <ClayCard className="mb-6">
          <h2 className="sw-eyebrow">Nueva tarifa</h2>
          <div className="mt-4">
            <TarifaForm tiposPrenda={tiposPrenda ?? []} servicios={servicios ?? []} />
          </div>
        </ClayCard>
      )}

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="sw-eyebrow">Tarifas</h2>
        <FiltroVigencia soloVigentes={soloVigentes} />
      </div>
      {tarifas === null ? <ErrorDeCarga recurso="las tarifas" /> : <TablaTarifas tarifas={tarifas} editable={puedeEditar} />}
    </main>
  );
}
