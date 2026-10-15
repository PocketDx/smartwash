import type { PrendaFormulario, Tarifa } from "@/lib/api";
import { DIA_ISO } from "@/lib/auditoria";

/** Estado de una linea mientras se edita: los campos numericos son texto del input. */
export type LineaEditable = {
  clave: number;
  tipo_prenda: string;
  cantidad: string;
  peso: string;
  talla: string;
  genero: string;
  color: string;
  estado_inicial: string;
  servicios: number[];
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
  };
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

/** Subtotal de la linea antes de descuentos. Es una vista previa: el valor que
 * cuenta lo calcula y congela el backend al registrar. */
export function subtotalEstimado(linea: LineaEditable, tarifas: Tarifa[]): number {
  const tipo = Number(linea.tipo_prenda);
  return linea.servicios.reduce((total, servicio) => {
    const tarifa = tarifaDe(tarifas, tipo, servicio);
    if (!tarifa) return total;
    const unidades = tarifa.unidad_cobro === "kilo" ? Number(linea.peso) || 0 : Number(linea.cantidad) || 0;
    return total + Number(tarifa.valor) * unidades;
  }, 0);
}

export function aFormulario(linea: LineaEditable): PrendaFormulario {
  return {
    tipo_prenda: Number(linea.tipo_prenda),
    cantidad: Number(linea.cantidad),
    peso: linea.peso.trim() === "" ? null : linea.peso,
    talla: linea.talla.trim(),
    genero: linea.genero,
    color: linea.color.trim(),
    estado_inicial: linea.estado_inicial.trim(),
    servicios: linea.servicios,
  };
}
