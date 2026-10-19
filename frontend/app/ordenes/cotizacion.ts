import type { Material, PrendaFormulario, Tarifa, TipoPrenda } from "@/lib/api";
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

/** La excepcion vigente del tipo de prenda y, si no hay, la general del servicio. */
export function tarifaDe(tarifas: Tarifa[], tipoPrenda: number, servicio: number): Tarifa | undefined {
  const delServicio = tarifas.filter((t) => t.servicio === servicio);
  return delServicio.find((t) => t.tipo_prenda === tipoPrenda) ?? delServicio.find((t) => t.tipo_prenda === null);
}

/** (base + peso x precio por kilo) x factor, a la centena mas cercana. Todo en enteros
 * (centavos, centesimas de kilo y de factor) para que el medio suba igual que en Decimal. */
export function precioUnitario(base: string, porKilo: string, peso: string, factor: string): number {
  const bruto = Math.round(Number(base) * 100) * 100 + Math.round(Number(peso) * 100) * Math.round(Number(porKilo) * 100);
  return Math.floor((bruto * Math.round(Number(factor) * 100) + 5e7) / 1e8) * 100;
}

export type LineaCotizada = {
  servicio: number;
  tarifa: Tarifa | null;
  precio: number;
  peso: number;
  nivel: string;
  factor: string;
};

export function cotizarUnidad(
  tipoPrenda: string,
  datos: DatosPrenda,
  tarifas: Tarifa[],
  materiales: Material[],
): LineaCotizada[] {
  const material = materiales.find((m) => m.id === Number(datos.material));
  const factor = material?.factor ?? "1";
  return datos.servicios.map((servicio) => {
    const tarifa = tarifaDe(tarifas, Number(tipoPrenda), servicio) ?? null;
    const precio = tarifa ? precioUnitario(tarifa.valor_base, tarifa.precio_por_kilo, datos.peso || "0", factor) : 0;
    return { servicio, tarifa, precio, peso: Number(datos.peso) || 0, nivel: material?.nivel_dificultad_nombre ?? "", factor: String(Number(factor)) };
  });
}

export function datosPorUnidad(linea: LineaEditable): DatosPrenda[] {
  return linea.detallar ? ajustarUnidades(linea) : Array.from({ length: unidadesDeCantidad(linea) }, () => linea);
}

/** Subtotal del bloque antes de descuentos: la suma de cada prenda segun su peso,
 * material y servicios. Es una vista previa; el valor que cuenta lo congela el backend. */
export function subtotalEstimado(linea: LineaEditable, tarifas: Tarifa[], materiales: Material[]): number {
  return datosPorUnidad(linea).reduce(
    (suma, d) => suma + cotizarUnidad(linea.tipo_prenda, d, tarifas, materiales).reduce((s, l) => s + l.precio, 0),
    0,
  );
}

/** Una prenda de cantidad 1 por unidad del bloque. */
export function aFormularios(linea: LineaEditable): PrendaFormulario[] {
  return datosPorUnidad(linea).map((d) => ({
    tipo_prenda: Number(linea.tipo_prenda),
    material: Number(d.material),
    cantidad: 1,
    peso: d.peso,
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
