import type { PrendaFormulario, Tarifa, TipoPrenda } from "@/lib/api";
import { DIA_ISO } from "@/lib/auditoria";

export const TALLAS = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL", "Única"] as const;

/** Datos propios de una unidad; los numericos son texto del input. */
export type DatosPrenda = {
  peso: string;
  talla: string;
  genero: string;
  color: string;
  estado_inicial: string;
};

export type UnidadEditable = DatosPrenda & { clave: number };

/** Un bloque: un tipo de prenda con su cantidad y servicios. Sin detallar, sus
 * datos valen para todas las unidades; detallado, cada unidad lleva los suyos. */
export type LineaEditable = DatosPrenda & {
  clave: number;
  tipo_prenda: string;
  cantidad: string;
  servicios: number[];
  detallar: boolean;
  unidades: UnidadEditable[];
};

let siguienteClave = 0;

export function lineaVacia(): LineaEditable {
  siguienteClave += 1;
  return {
    clave: siguienteClave,
    tipo_prenda: "",
    cantidad: "1",
    peso: "",
    talla: "",
    genero: "",
    color: "",
    estado_inicial: "",
    servicios: [],
    detallar: false,
    unidades: [],
  };
}

export function datosDe({ peso, talla, genero, color, estado_inicial }: DatosPrenda): DatosPrenda {
  return { peso, talla, genero, color, estado_inicial };
}

export function unidadNueva(datos: DatosPrenda): UnidadEditable {
  siguienteClave += 1;
  return { clave: siguienteClave, ...datosDe(datos) };
}

export function unidadesDeCantidad(linea: LineaEditable): number {
  const n = Math.floor(Number(linea.cantidad));
  return Number.isFinite(n) && n > 0 ? n : 0;
}

/** Ajusta las filas a la cantidad sin tocar las ya editadas; las nuevas copian la ultima. */
export function ajustarUnidades(linea: LineaEditable): UnidadEditable[] {
  const n = unidadesDeCantidad(linea);
  const base = linea.unidades.slice(0, n);
  while (base.length < n) base.push(unidadNueva(base.at(-1) ?? linea));
  return base;
}

export function difierenDelBloque(linea: LineaEditable): boolean {
  const bloque = datosDe(linea);
  return linea.unidades.some((u) => (Object.keys(bloque) as (keyof DatosPrenda)[]).some((k) => u[k] !== bloque[k]));
}

// ?vigentes=1 solo descarta las tarifas cerradas; el backend cotiza ademas con
// vigente_desde <= hoy, asi que una tarifa programada para manana no sirve hoy.
export function tarifasDeHoy(tarifas: Tarifa[]): Tarifa[] {
  const hoy = DIA_ISO.format(new Date());
  return tarifas.filter(
    (t) => t.vigente_desde <= hoy && (t.vigente_hasta === null || t.vigente_hasta > hoy),
  );
}

export function tarifaDe(tarifas: Tarifa[], tipoPrenda: number, servicio: number) {
  return tarifas.find((t) => t.tipo_prenda === tipoPrenda && t.servicio === servicio);
}

export function cobraPorKilo(linea: LineaEditable, tarifas: Tarifa[]): boolean {
  const tipo = Number(linea.tipo_prenda);
  return linea.servicios.some((s) => tarifaDe(tarifas, tipo, s)?.unidad_cobro === "kilo");
}

/** Subtotal del bloque antes de descuentos. Es una vista previa: el valor que
 * cuenta lo calcula y congela el backend al registrar. */
export function subtotalEstimado(linea: LineaEditable, tarifas: Tarifa[]): number {
  const tipo = Number(linea.tipo_prenda);
  const unidades = unidadesDeCantidad(linea);
  const pesoTotal = linea.detallar
    ? linea.unidades.reduce((suma, u) => suma + (Number(u.peso) || 0), 0)
    : (Number(linea.peso) || 0) * unidades;
  return linea.servicios.reduce((total, servicio) => {
    const tarifa = tarifaDe(tarifas, tipo, servicio);
    if (!tarifa) return total;
    return total + Number(tarifa.valor) * (tarifa.unidad_cobro === "kilo" ? pesoTotal : unidades);
  }, 0);
}

function datosPorUnidad(linea: LineaEditable): DatosPrenda[] {
  return linea.detallar ? ajustarUnidades(linea) : Array.from({ length: unidadesDeCantidad(linea) }, () => linea);
}

/** Una prenda de cantidad 1 por unidad del bloque. */
export function aFormularios(linea: LineaEditable): PrendaFormulario[] {
  return datosPorUnidad(linea).map((d) => ({
    tipo_prenda: Number(linea.tipo_prenda),
    cantidad: 1,
    peso: d.peso.trim() === "" ? null : d.peso,
    talla: d.talla,
    genero: d.genero,
    color: d.color.trim(),
    estado_inicial: d.estado_inicial.trim(),
    servicios: linea.servicios,
  }));
}

/** Nombre de cada prenda enviada, en el mismo orden que aFormularios: "Camisa 2". */
export function nombresDeUnidades(lineas: LineaEditable[], tipos: TipoPrenda[]): string[] {
  return lineas.flatMap((linea) => {
    const nombre = tipos.find((t) => t.id === Number(linea.tipo_prenda))?.nombre ?? "Prenda";
    return Array.from({ length: unidadesDeCantidad(linea) }, (_, i) => `${nombre} ${i + 1}`);
  });
}
