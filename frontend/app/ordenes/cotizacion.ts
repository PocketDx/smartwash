import type { PrendaFormulario, Tarifa, TipoPrenda } from "@/lib/api";
import { DIA_ISO } from "@/lib/auditoria";

export const TALLAS = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL", "Única"] as const;

/** Datos propios de una unidad; los numericos son texto del input. */
export type DatosPrenda = {
  material: string;
  peso: string;
  talla: string;
  genero: string;
  color: string;
  estado_inicial: string;
  servicios: number[];
};

export type UnidadEditable = DatosPrenda & { clave: number };

/** Un bloque: un tipo de prenda con su cantidad. Sin detallar, sus datos y
 * servicios valen para todas las unidades; detallado, cada unidad lleva los suyos. */
export type LineaEditable = DatosPrenda & {
  clave: number;
  tipo_prenda: string;
  cantidad: string;
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
    material: "",
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

export function datosDe(d: DatosPrenda): DatosPrenda {
  return {
    material: d.material,
    peso: d.peso,
    talla: d.talla,
    genero: d.genero,
    color: d.color,
    estado_inicial: d.estado_inicial,
    servicios: [...d.servicios],
  };
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

function huella(d: DatosPrenda): string {
  return JSON.stringify({ ...datosDe(d), servicios: [...d.servicios].sort((a, b) => a - b) });
}

export function difierenDelBloque(linea: LineaEditable): boolean {
  return linea.unidades.some((u) => huella(u) !== huella(linea));
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

export function cobraPorKilo(tipoPrenda: string, servicios: number[], tarifas: Tarifa[]): boolean {
  const tipo = Number(tipoPrenda);
  return servicios.some((s) => tarifaDe(tarifas, tipo, s)?.unidad_cobro === "kilo");
}

function datosPorUnidad(linea: LineaEditable): DatosPrenda[] {
  return linea.detallar ? ajustarUnidades(linea) : Array.from({ length: unidadesDeCantidad(linea) }, () => linea);
}

function subtotalDeUnidad(tipoPrenda: string, datos: DatosPrenda, tarifas: Tarifa[]): number {
  const tipo = Number(tipoPrenda);
  return datos.servicios.reduce((total, servicio) => {
    const tarifa = tarifaDe(tarifas, tipo, servicio);
    if (!tarifa) return total;
    return total + Number(tarifa.valor) * (tarifa.unidad_cobro === "kilo" ? Number(datos.peso) || 0 : 1);
  }, 0);
}

/** Subtotal del bloque antes de descuentos: la suma de cada prenda segun sus
 * servicios. Es una vista previa; el valor que cuenta lo congela el backend. */
export function subtotalEstimado(linea: LineaEditable, tarifas: Tarifa[]): number {
  return datosPorUnidad(linea).reduce((suma, d) => suma + subtotalDeUnidad(linea.tipo_prenda, d, tarifas), 0);
}

/** Una prenda de cantidad 1 por unidad del bloque. */
export function aFormularios(linea: LineaEditable): PrendaFormulario[] {
  return datosPorUnidad(linea).map((d) => ({
    tipo_prenda: Number(linea.tipo_prenda),
    material: Number(d.material),
    cantidad: 1,
    peso: d.peso.trim() === "" ? null : d.peso,
    talla: d.talla,
    genero: d.genero,
    color: d.color.trim(),
    estado_inicial: d.estado_inicial.trim(),
    servicios: d.servicios,
  }));
}

/** Nombre de cada prenda enviada, en el mismo orden que aFormularios: "Camisa 2". */
export function nombresDeUnidades(lineas: LineaEditable[], tipos: TipoPrenda[]): string[] {
  return lineas.flatMap((linea) => {
    const nombre = tipos.find((t) => t.id === Number(linea.tipo_prenda))?.nombre ?? "Prenda";
    return Array.from({ length: unidadesDeCantidad(linea) }, (_, i) => `${nombre} ${i + 1}`);
  });
}

/** Cada prenda necesita al menos un servicio; se avisa antes de llamar a la API. */
export function erroresDeServicios(lineas: LineaEditable[], tipos: TipoPrenda[]): string[] {
  return lineas.flatMap((linea, indice) => {
    const nombre = tipos.find((t) => t.id === Number(linea.tipo_prenda))?.nombre ?? `Prenda ${indice + 1}`;
    if (!linea.detallar) {
      return linea.servicios.length === 0 ? [`${nombre} · Servicios: elige al menos uno.`] : [];
    }
    return ajustarUnidades(linea).flatMap((u, i) =>
      u.servicios.length === 0 ? [`${nombre} ${i + 1} · Servicios: elige al menos uno.`] : [],
    );
  });
}
