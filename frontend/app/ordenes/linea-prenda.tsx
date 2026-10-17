"use client";

import type { Servicio, Tarifa, TipoPrenda } from "@/lib/api";
import { formatCOP } from "@/lib/format";
import { ClayButton, ClayField, ClayInput, ClaySelect } from "../components/ui/clay";
import { cobraPorKilo, subtotalEstimado, tarifaDe, type LineaEditable } from "./cotizacion";

export default function LineaPrenda({
  titulo,
  linea,
  tiposPrenda,
  servicios,
  tarifas,
  onChange,
  onQuitar,
}: {
  titulo: string;
  linea: LineaEditable;
  tiposPrenda: TipoPrenda[];
  servicios: Servicio[];
  tarifas: Tarifa[];
  onChange: (linea: LineaEditable) => void;
  onQuitar?: () => void;
}) {
  const tipo = Number(linea.tipo_prenda);
  const disponibles = linea.tipo_prenda
    ? servicios.filter((s) => tarifaDe(tarifas, tipo, s.id))
    : [];
  const porKilo = cobraPorKilo(linea, tarifas);
  const subtotal = subtotalEstimado(linea, tarifas);

  function cambiar(campo: keyof LineaEditable, valor: string) {
    onChange({ ...linea, [campo]: valor });
  }

  function cambiarTipo(valor: string) {
    const nuevoTipo = Number(valor);
    onChange({
      ...linea,
      tipo_prenda: valor,
      servicios: linea.servicios.filter((s) => tarifaDe(tarifas, nuevoTipo, s)),
    });
  }

  function alternarServicio(servicio: number) {
    const servicios = linea.servicios.includes(servicio)
      ? linea.servicios.filter((s) => s !== servicio)
      : [...linea.servicios, servicio];
    onChange({ ...linea, servicios });
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
                {t.material ? `${t.nombre} (${t.material})` : t.nombre}
              </option>
            ))}
          </ClaySelect>
        </ClayField>
      </div>
      <div className="sm:col-span-1">
        <ClayField label="Cantidad">
          <ClayInput
            type="number"
            min="1"
            step="1"
            value={linea.cantidad}
            onChange={(e) => cambiar("cantidad", e.target.value)}
            required
          />
        </ClayField>
      </div>
      <div className="sm:col-span-2">
        <ClayField label={porKilo ? "Peso en kg (obligatorio)" : "Peso en kg"}>
          <ClayInput
            type="number"
            min="0.01"
            step="0.01"
            value={linea.peso}
            onChange={(e) => cambiar("peso", e.target.value)}
            required={porKilo}
          />
        </ClayField>
      </div>

      <div className="sm:col-span-6">
        <p className="text-sm font-medium text-(--sw-ink-soft)">Servicios</p>
        {!linea.tipo_prenda ? (
          <p className="mt-1 text-sm text-(--sw-ink-soft)">Elige primero el tipo de prenda.</p>
        ) : disponibles.length === 0 ? (
          <p className="mt-1 text-sm text-(--sw-ink-soft)">
            Este tipo de prenda no tiene tarifas vigentes. Configuralas en el catalogo.
          </p>
        ) : (
          <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
            {disponibles.map((s) => {
              const tarifa = tarifaDe(tarifas, tipo, s.id);
              return (
                <label key={s.id} className="flex items-center gap-2 text-sm text-(--sw-ink)">
                  <input
                    type="checkbox"
                    className="size-4"
                    checked={linea.servicios.includes(s.id)}
                    onChange={() => alternarServicio(s.id)}
                  />
                  {s.nombre}
                  {tarifa && (
                    <span className="text-(--sw-ink-soft)">
                      · {formatCOP(tarifa.valor)} por {tarifa.unidad_cobro}
                    </span>
                  )}
                </label>
              );
            })}
          </div>
        )}
      </div>

      <div className="sm:col-span-2">
        <ClayField label="Talla">
          <ClayInput value={linea.talla} onChange={(e) => cambiar("talla", e.target.value)} maxLength={20} />
        </ClayField>
      </div>
      <div className="sm:col-span-2">
        <ClayField label="Genero">
          <ClaySelect value={linea.genero} onChange={(e) => cambiar("genero", e.target.value)}>
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
          <ClayInput value={linea.color} onChange={(e) => cambiar("color", e.target.value)} maxLength={40} />
        </ClayField>
      </div>
      <div className="sm:col-span-6">
        <ClayField label="Estado al recibir">
          <ClayInput
            value={linea.estado_inicial}
            onChange={(e) => cambiar("estado_inicial", e.target.value)}
            placeholder="Manchas, rasgaduras, botones faltantes..."
            maxLength={255}
          />
        </ClayField>
      </div>

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
