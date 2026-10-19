"use client";

import type { Material, Servicio, Tarifa, TipoPrenda } from "@/lib/api";
import { formatCOP } from "@/lib/format";
import { ClayButton, ClayField, ClayInput, ClaySelect } from "../components/ui/clay";
import {
  ajustarUnidades,
  cotizarUnidad,
  datosDe,
  difierenDelBloque,
  subtotalEstimado,
  TALLAS,
  tarifaDe,
  unidadNueva,
  unidadesDeCantidad,
  type DatosPrenda,
  type LineaEditable,
  type UnidadEditable,
} from "./cotizacion";

function CamposPrenda({
  datos,
  tipo,
  materiales,
  servicios,
  tarifas,
  unidades,
  onChange,
}: {
  datos: DatosPrenda;
  unidades: number;
  tipo: string;
  materiales: Material[];
  servicios: Servicio[];
  tarifas: Tarifa[];
  onChange: (datos: DatosPrenda) => void;
}) {
  const cambiar = (campo: keyof DatosPrenda, valor: string) => onChange({ ...datos, [campo]: valor });
  const hayTallaLibre = datos.talla !== "" && !(TALLAS as readonly string[]).includes(datos.talla);
  const lineas = cotizarUnidad(tipo, datos, tarifas, materiales);
  const nombreDe = (id: number) => servicios.find((x) => x.id === id)?.nombre ?? "";

  function alternarServicio(servicio: number) {
    const elegidos = datos.servicios.includes(servicio)
      ? datos.servicios.filter((s) => s !== servicio)
      : [...datos.servicios, servicio];
    onChange({ ...datos, servicios: elegidos });
  }

  return (
    <>
      <div className="sm:col-span-6">
        <p className="text-sm font-medium text-(--sw-ink-soft)">Servicios</p>
        {!tipo ? (
          <p className="mt-1 text-sm text-(--sw-ink-soft)">Elige primero el tipo de prenda.</p>
        ) : servicios.length === 0 ? (
          <p className="mt-1 text-sm text-(--sw-ink-soft)">Todavia no hay servicios en el catalogo.</p>
        ) : (
          <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
            {servicios.map((s) => {
              const tarifa = tarifaDe(tarifas, Number(tipo), s.id);
              return (
                <label
                  key={s.id}
                  className={`flex items-center gap-2 text-sm ${tarifa ? "text-(--sw-ink)" : "text-(--sw-ink-soft)"}`}
                >
                  <input
                    type="checkbox"
                    className="size-4"
                    checked={datos.servicios.includes(s.id)}
                    disabled={!tarifa}
                    onChange={() => alternarServicio(s.id)}
                  />
                  {s.nombre}
                  <span className="text-(--sw-ink-soft)">
                    {tarifa
                      ? `· ${formatCOP(tarifa.valor_base)} + ${formatCOP(tarifa.precio_por_kilo)}/kg`
                      : "· sin tarifa vigente: pidele al administrador que la configure"}
                  </span>
                </label>
              );
            })}
          </div>
        )}
      </div>
      <div className="sm:col-span-2">
        <ClayField label="Material">
          <ClaySelect value={datos.material} onChange={(e) => cambiar("material", e.target.value)} required>
            <option value="">Selecciona...</option>
            {materiales.map((m) => (
              <option key={m.id} value={m.id}>
                {m.nombre}
              </option>
            ))}
          </ClaySelect>
        </ClayField>
      </div>
      <div className="sm:col-span-2">
        <ClayField label="Peso de la prenda en kg">
          <ClayInput
            type="number"
            min="0.01"
            step="0.01"
            value={datos.peso}
            onChange={(e) => cambiar("peso", e.target.value)}
            required
          />
        </ClayField>
      </div>
      <div className="sm:col-span-2">
        <ClayField label="Talla">
          <ClaySelect value={datos.talla} onChange={(e) => cambiar("talla", e.target.value)}>
            <option value="">Sin especificar</option>
            {hayTallaLibre && <option value={datos.talla}>{datos.talla}</option>}
            {TALLAS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </ClaySelect>
        </ClayField>
      </div>
      <div className="sm:col-span-2">
        <ClayField label="Genero">
          <ClaySelect value={datos.genero} onChange={(e) => cambiar("genero", e.target.value)}>
            <option value="">Sin especificar</option>
            <option value="Femenino">Femenino</option>
            <option value="Masculino">Masculino</option>
            <option value="Unisex">Unisex</option>
            <option value="Infantil">Infantil</option>
          </ClaySelect>
        </ClayField>
      </div>
      <div className="sm:col-span-2">
        <ClayField label="Color">
          <ClayInput value={datos.color} onChange={(e) => cambiar("color", e.target.value)} maxLength={40} />
        </ClayField>
      </div>
      <div className="sm:col-span-4">
        <ClayField label="Estado al recibir">
          <ClayInput
            value={datos.estado_inicial}
            onChange={(e) => cambiar("estado_inicial", e.target.value)}
            placeholder="Manchas, rasgaduras, botones faltantes..."
            maxLength={255}
          />
        </ClayField>
      </div>
      <p className="text-xs text-(--sw-ink-soft) sm:col-span-6">
        El peso y el material cambian el precio: (base + peso x precio por kilo) x factor del material, a la
        centena.
      </p>
      {lineas.length > 0 && (
        <ul className="flex flex-col gap-1 text-xs text-(--sw-ink-soft) sm:col-span-6">
          {lineas.map((l) => (
            <li key={l.servicio}>
              <span className="font-semibold text-(--sw-ink)">{nombreDe(l.servicio)}</span>:{" "}
              {l.tarifa
                ? `${formatCOP(l.tarifa.valor_base)} + ${l.peso} kg x ${formatCOP(l.tarifa.precio_por_kilo)}${
                    l.nivel ? ` · ${l.nivel} x${l.factor}` : ""
                  }${l.tarifa.tipo_prenda !== null ? " · tarifa del tipo" : ""} = ${formatCOP(l.precio)}${
                    unidades > 1 ? ` por prenda (${unidades} prendas: ${formatCOP(l.precio * unidades)})` : ""
                  }`
                : "sin tarifa vigente"}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export default function LineaPrenda({
  titulo,
  linea,
  tiposPrenda,
  materiales,
  servicios,
  tarifas,
  onChange,
  onQuitar,
}: {
  titulo: string;
  linea: LineaEditable;
  tiposPrenda: TipoPrenda[];
  materiales: Material[];
  servicios: Servicio[];
  tarifas: Tarifa[];
  onChange: (linea: LineaEditable) => void;
  onQuitar?: () => void;
}) {
  const tipo = Number(linea.tipo_prenda);
  const subtotal = subtotalEstimado(linea, tarifas, materiales);
  const nombre = tiposPrenda.find((t) => t.id === tipo)?.nombre ?? "Prenda";
  const unidades = linea.unidades;
  const campos = { tipo: linea.tipo_prenda, materiales, servicios, tarifas };
  const prendas = unidadesDeCantidad(linea);

  function cambiarCantidad(valor: string) {
    const nueva = { ...linea, cantidad: valor };
    onChange(linea.detallar ? { ...nueva, unidades: ajustarUnidades(nueva) } : nueva);
  }

  function cambiarTipo(valor: string) {
    const nuevoTipo = Number(valor);
    const vigentes = (elegidos: number[]) => elegidos.filter((s) => tarifaDe(tarifas, nuevoTipo, s));
    const estandar = (id: number) => {
      const peso = tiposPrenda.find((t) => t.id === id)?.peso_estandar;
      return peso ? String(Number(peso)) : null;
    };
    // El peso se reemplaza solo si esta vacio o es el estandar del tipo anterior: lo que
    // la recepcionista escribio a mano se respeta.
    const pesoPara = (actual: string) =>
      actual === "" || actual === estandar(tipo) ? (estandar(nuevoTipo) ?? actual) : actual;
    onChange({
      ...linea,
      tipo_prenda: valor,
      peso: pesoPara(linea.peso),
      servicios: vigentes(linea.servicios),
      unidades: unidades.map((u) => ({ ...u, peso: pesoPara(u.peso), servicios: vigentes(u.servicios) })),
    });
  }

  function alternarDetalle(activar: boolean) {
    if (activar) {
      const n = unidadesDeCantidad(linea);
      onChange({ ...linea, detallar: true, unidades: Array.from({ length: n }, () => unidadNueva(linea)) });
      return;
    }
    if (difierenDelBloque(linea) && !window.confirm("Se descartarán los cambios hechos prenda por prenda. ¿Continuar?")) return;
    onChange({ ...linea, detallar: false, unidades: [] });
  }

  function cambiarUnidad(clave: number, datos: DatosPrenda) {
    onChange({ ...linea, unidades: unidades.map((u: UnidadEditable) => (u.clave === clave ? { ...u, ...datos } : u)) });
  }

  function copiarALasDemas(origen: UnidadEditable) {
    onChange({ ...linea, unidades: unidades.map((u) => ({ ...u, ...datosDe(origen) })) });
  }

  return (
    <fieldset className="clay-sm grid grid-cols-1 gap-4 p-4 sm:grid-cols-6">
      <legend className="px-1 text-sm font-bold text-(--sw-ink)">{titulo}</legend>

      <div className="sm:col-span-3">
        <ClayField label="Tipo de prenda">
          <ClaySelect value={linea.tipo_prenda} onChange={(e) => cambiarTipo(e.target.value)} required>
            <option value="">Selecciona...</option>
            {tiposPrenda.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nombre}
              </option>
            ))}
          </ClaySelect>
        </ClayField>
      </div>
      <div className="sm:col-span-3">
        <ClayField label="Cantidad">
          <ClayInput
            type="number"
            min="1"
            step="1"
            value={linea.cantidad}
            onChange={(e) => cambiarCantidad(e.target.value)}
            required
          />
        </ClayField>
      </div>

      <label className="flex items-center gap-2 text-sm font-medium text-(--sw-ink) sm:col-span-6">
        <input type="checkbox" className="size-4" checked={linea.detallar} onChange={(e) => alternarDetalle(e.target.checked)} />
        Detallar cada prenda
      </label>

      {linea.detallar ? (
        unidades.map((unidad, i) => (
          <fieldset key={unidad.clave} className="clay-sm grid grid-cols-1 gap-4 p-3 sm:col-span-6 sm:grid-cols-6">
            <legend className="px-1 text-xs font-bold text-(--sw-ink-soft)">
              {nombre} {i + 1}
            </legend>
            <CamposPrenda datos={unidad} unidades={1} {...campos} onChange={(d) => cambiarUnidad(unidad.clave, d)} />
            {unidades.length > 1 && (
              <div className="flex items-end sm:col-span-2">
                <ClayButton type="button" variant="secundario" onClick={() => copiarALasDemas(unidad)}>
                  Copiar a las demás
                </ClayButton>
              </div>
            )}
          </fieldset>
        ))
      ) : (
        <CamposPrenda datos={linea} unidades={prendas} {...campos} onChange={(d) => onChange({ ...linea, ...d })} />
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 sm:col-span-6">
        <p className="text-sm text-(--sw-ink-soft)">
          Subtotal estimado: <span className="font-semibold text-(--sw-ink) tabular-nums">{formatCOP(subtotal)}</span>
        </p>
        {onQuitar && (
          <ClayButton type="button" variant="secundario" onClick={onQuitar}>
            Quitar prenda
          </ClayButton>
        )}
      </div>
    </fieldset>
  );
}
