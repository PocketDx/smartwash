const ETIQUETAS: Record<string, string> = {
  cliente: "Cliente",
  prendas: "Prendas",
  tipo_prenda: "Tipo de prenda",
  cantidad: "Cantidad",
  peso: "Peso",
  talla: "Talla",
  genero: "Genero",
  color: "Color",
  estado_inicial: "Estado al recibir",
  servicios: "Servicios",
  servicio: "Servicio",
  estado: "Estado",
  monto: "Monto",
  metodo: "Metodo de pago",
  operario: "Operario",
};

const SIN_ETIQUETA = new Set(["non_field_errors", "detail"]);

function prenda(indice: number, ruta: string[]): string[] {
  return [...ruta.filter((r) => r !== ETIQUETAS.prendas), `Prenda ${indice + 1}`];
}

// DRF anida los errores de cada prenda por su posicion, como lista o como
// objeto con indices: {"prendas": {"0": {"peso": ["..."]}}}. leerErroresApi
// solo aplana un nivel, por eso aqui se recorre todo el arbol.
function aplanar(valor: unknown, ruta: string[]): string[] {
  if (typeof valor === "string") {
    const prefijo = ruta.filter(Boolean).join(" · ");
    return [prefijo ? `${prefijo}: ${valor}` : valor];
  }
  if (Array.isArray(valor)) {
    return valor.flatMap((item, indice) =>
      item && typeof item === "object" && !Array.isArray(item)
        ? aplanar(item, prenda(indice, ruta))
        : aplanar(item, ruta),
    );
  }
  if (valor && typeof valor === "object") {
    return Object.entries(valor).flatMap(([campo, hijo]) => {
      if (/^\d+$/.test(campo)) return aplanar(hijo, prenda(Number(campo), ruta));
      return aplanar(hijo, [...ruta, SIN_ETIQUETA.has(campo) ? "" : (ETIQUETAS[campo] ?? campo)]);
    });
  }
  return [];
}

export async function mensajesDeOrden(response: Response | null, porDefecto: string): Promise<string[]> {
  if (!response) return ["No se pudo conectar con el servidor. Intenta de nuevo."];
  const data: unknown = await response.json().catch(() => null);
  const mensajes = aplanar(data, []);
  return mensajes.length ? mensajes : [`${porDefecto} (error ${response.status}).`];
}
