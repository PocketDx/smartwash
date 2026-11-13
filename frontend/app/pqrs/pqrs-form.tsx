"use client";

import { useState, type FormEvent } from "react";

import { crearPqrs, type PqrsFormulario } from "@/lib/api";
import { AlertaErrores, mensajesDeError } from "../catalogo/errores";
import { ClayButton, ClayField, ClayInput, ClaySelect, ClayTextarea } from "../components/ui/clay";

type Tipo = PqrsFormulario["tipo"];

export const TIPOS: { valor: Tipo; etiqueta: string }[] = [
  { valor: "peticion", etiqueta: "Peticion" },
  { valor: "queja", etiqueta: "Queja" },
  { valor: "reclamo", etiqueta: "Reclamo" },
  { valor: "sugerencia", etiqueta: "Sugerencia" },
];

const ETIQUETAS: Record<string, string> = {
  tipo: "Tipo de solicitud",
  codigo_orden: "Codigo del pedido",
  nombre: "Nombre",
  documento: "Documento",
  correo: "Correo",
  telefono: "Telefono",
  mensaje: "Mensaje",
};

const normalizarCodigo = (valor: string) => valor.replace(/\s+/g, "").toUpperCase();

export default function PqrsForm({
  tipoInicial,
  codigoInicial,
}: {
  tipoInicial: Tipo;
  codigoInicial: string;
}) {
  const [tipo, setTipo] = useState<Tipo>(tipoInicial);
  const [codigo, setCodigo] = useState(codigoInicial);
  const [version, setVersion] = useState(0);
  const [pending, setPending] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [errores, setErrores] = useState<string[]>([]);

  const codigoObligatorio = tipo !== "sugerencia";

  function limpiar() {
    setTipo(tipoInicial);
    setCodigo(codigoInicial);
    setErrores([]);
    setVersion((v) => v + 1);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setEnviado(false);

    const codigoLimpio = normalizarCodigo(codigo);
    if (codigoObligatorio && !codigoLimpio) {
      setErrores(["Indica el codigo de rastreo de tu pedido. Es obligatorio para peticiones, quejas y reclamos."]);
      return;
    }

    setPending(true);
    setErrores([]);
    const form = new FormData(event.currentTarget);
    const datos: PqrsFormulario = {
      tipo,
      codigo_orden: codigoLimpio,
      nombre: String(form.get("nombre") ?? ""),
      documento: String(form.get("documento") ?? ""),
      correo: String(form.get("correo") ?? ""),
      telefono: String(form.get("telefono") ?? ""),
      mensaje: String(form.get("mensaje") ?? ""),
    };

    const response = await crearPqrs(datos).catch(() => null);
    setPending(false);

    if (response?.ok) {
      setEnviado(true);
      limpiar();
    } else if (response?.status === 429) {
      setErrores(["Alcanzaste el limite de envios por ahora. Intenta de nuevo mas tarde."]);
    } else {
      setErrores(await mensajesDeError(response, ETIQUETAS, "No se pudo registrar tu solicitud"));
    }
  }

  return (
    <form
      key={version}
      onSubmit={onSubmit}
      noValidate
      className="grid grid-cols-1 gap-4 sm:grid-cols-2"
    >
      {enviado && (
        <p
          role="status"
          className="clay-sm border-l-8 border-l-(--sw-accent) p-3 text-sm font-semibold sm:col-span-2"
        >
          Tu solicitud quedo registrada y esta pendiente de gestion manual por la Recepcionista.
        </p>
      )}

      <ClayField label="Tipo de solicitud">
        <ClaySelect name="tipo" value={tipo} onChange={(e) => setTipo(e.target.value as Tipo)}>
          {TIPOS.map((t) => (
            <option key={t.valor} value={t.valor}>
              {t.etiqueta}
            </option>
          ))}
        </ClaySelect>
      </ClayField>
      <ClayField label={codigoObligatorio ? "Codigo de rastreo de tu pedido" : "Codigo de rastreo (opcional)"}>
        <ClayInput
          name="codigo_orden"
          value={codigo}
          onChange={(e) => setCodigo(e.target.value)}
          placeholder="SW-XXXXXXXX"
          aria-required={codigoObligatorio}
        />
      </ClayField>
      <ClayField label="Nombre completo">
        <ClayInput name="nombre" required />
      </ClayField>
      <ClayField label="Documento">
        <ClayInput name="documento" required />
      </ClayField>
      <ClayField label="Correo">
        <ClayInput name="correo" type="email" required />
      </ClayField>
      <ClayField label="Telefono">
        <ClayInput name="telefono" />
      </ClayField>

      <div className="sm:col-span-2">
        <ClayField label="Cuentanos que paso">
          <ClayTextarea name="mensaje" required />
        </ClayField>
      </div>

      {errores.length > 0 && (
        <div className="sm:col-span-2">
          <AlertaErrores titulo="No pudimos enviar tu solicitud" errores={errores} />
        </div>
      )}

      <div className="flex gap-3 sm:col-span-2">
        <ClayButton type="submit" disabled={pending}>
          {pending ? "Enviando..." : "Enviar solicitud"}
        </ClayButton>
        <ClayButton type="button" variant="secundario" onClick={limpiar} disabled={pending}>
          Cancelar
        </ClayButton>
      </div>
    </form>
  );
}
