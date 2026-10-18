type Agrupable = {
  tipo_prenda_nombre: string;
  cantidad: number;
  peso: string | null;
  talla: string;
  genero: string;
  color: string;
  estado_inicial: string;
};

export type GrupoDePrendas<T> = { prendas: T[]; cantidad: number };

/** Junta las prendas identicas (mismos datos y mismos servicios) en una sola linea. */
export function agruparPrendas<T extends Agrupable>(
  prendas: T[],
  servicios: (prenda: T) => string,
): GrupoDePrendas<T>[] {
  const grupos = new Map<string, GrupoDePrendas<T>>();
  for (const p of prendas) {
    const clave = JSON.stringify([
      p.tipo_prenda_nombre,
      p.talla,
      p.genero,
      p.color,
      p.estado_inicial,
      p.peso === null ? null : Number(p.peso),
      servicios(p),
    ]);
    const grupo = grupos.get(clave) ?? { prendas: [], cantidad: 0 };
    grupo.prendas.push(p);
    grupo.cantidad += p.cantidad;
    grupos.set(clave, grupo);
  }
  return [...grupos.values()];
}

export function detallesDe<T extends Agrupable>(grupo: GrupoDePrendas<T>): string[] {
  const [p] = grupo.prendas;
  const porUnidad = grupo.prendas.length > 1 ? " c/u" : "";
  return [p.peso && `${Number(p.peso)} kg${porUnidad}`, p.talla && `talla ${p.talla}`, p.genero, p.color].filter(
    (d): d is string => Boolean(d),
  );
}
