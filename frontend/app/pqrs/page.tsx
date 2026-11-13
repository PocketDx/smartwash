import { ClayCard, Encabezado } from "../components/ui/clay";
import PqrsForm, { TIPOS } from "./pqrs-form";

export default async function PqrsPage({
  searchParams,
}: {
  searchParams: Promise<{ codigo?: string; tipo?: string }>;
}) {
  const { codigo, tipo } = await searchParams;
  const tipoInicial = TIPOS.find((t) => t.valor === tipo?.toLowerCase())?.valor ?? "peticion";

  return (
    <main className="mx-auto max-w-2xl px-4 py-8 sm:px-8 sm:py-12">
      <Encabezado eyebrow="Atencion al cliente" titulo="PQRS">
        Peticiones, quejas, reclamos y sugerencias. No necesitas iniciar sesion.
      </Encabezado>

      <ClayCard>
        <PqrsForm tipoInicial={tipoInicial} codigoInicial={(codigo ?? "").toUpperCase()} />
      </ClayCard>
    </main>
  );
}
