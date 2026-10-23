"""Resume las salidas crudas de benchmark_modelos.py en tablas Markdown.

Uso:
    python resumir_resultados.py ../../docs/benchmarks/resultados
"""
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean


def cargar(carpeta):
    datos = {}
    for f in sorted(Path(carpeta).glob("*.jsonl")):
        filas = [json.loads(linea) for linea in f.read_text(encoding="utf-8").splitlines() if linea]
        datos[filas[0]["modelo"]] = filas
    return datos


def media(filas, campo):
    return round(mean(f[campo] for f in filas), 2) if filas else None


def main(carpeta):
    datos = cargar(carpeta)
    print("### Rendimiento (3 repeticiones por fila)\n")
    print("| Modelo | Situación | Carga del modelo (s) | Primera respuesta (s) | Tokens generados | Tokens/s | Total (s) |")
    print("|---|---|---|---|---|---|---|")
    for m, filas in datos.items():
        for tipo, nombre in (("rendimiento_frio", "En frío"), ("rendimiento_caliente", "Cargado")):
            f = [x for x in filas if x["tipo"] == tipo]
            print(f"| `{m}` | {nombre} | {media(f, 'carga_modelo_s')} | {media(f, 'primera_respuesta_s')} | "
                  f"{media(f, 'tokens_generados')} | {media(f, 'tokens_por_s')} | {media(f, 'total_s')} |")
    print("\n### Detalle de la primera respuesta en frío (s)\n")
    print("| Modelo | Rep. 1 | Rep. 2 | Rep. 3 | Precarga con keep_alive (s) |")
    print("|---|---|---|---|---|")
    for m, filas in datos.items():
        frio = [x["primera_respuesta_s"] for x in filas if x["tipo"] == "rendimiento_frio"]
        pre = next(x["segundos"] for x in filas if x["tipo"] == "precarga_keep_alive")
        print(f"| `{m}` | " + " | ".join(str(v) for v in frio) + f" | {pre} |")
    print("\n### Memoria (`/api/ps` tras cargar el modelo)\n")
    print("| Modelo | Tamaño (GB) | En GPU (GB) | Contexto |")
    print("|---|---|---|---|")
    for m, filas in datos.items():
        for x in (y for y in filas if y["tipo"] == "memoria"):
            for mod in x["ps"].get("models", []):
                print(f"| `{m}` | {round(mod['size'] / 1e9, 2)} | {round(mod.get('size_vram', 0) / 1e9, 2)} | "
                      f"{mod.get('context_length', '?')} |")
    print("\n### Llamadas a herramientas (aciertos / intentos)\n")
    casos = sorted({x["caso"] for f in datos.values() for x in f if x["tipo"] == "herramienta"})
    print("| Modelo | " + " | ".join(casos) + " | Total | Tiempo medio (s) |")
    print("|---|" + "---|" * (len(casos) + 2))
    for m, filas in datos.items():
        h = [x for x in filas if x["tipo"] == "herramienta"]
        celdas = []
        for c in casos:
            sub = [x for x in h if x["caso"] == c]
            celdas.append(f"{sum(x['ok'] for x in sub)}/{len(sub)}")
        print(f"| `{m}` | " + " | ".join(celdas) + f" | {sum(x['ok'] for x in h)}/{len(h)} | {media(h, 'segundos')} |")
    print("\n### Calidad con resultado de herramienta (aciertos / intentos)\n")
    print("| Modelo | Caso | Cifras respaldadas | En español | Avisa si falla | Todo correcto | Ciclo completo (s) |")
    print("|---|---|---|---|---|---|---|")
    for m, filas in datos.items():
        por_caso = defaultdict(list)
        for x in filas:
            if x["tipo"] == "calidad":
                por_caso[x["caso"]].append(x)
        for caso, sub in por_caso.items():
            n = len(sub)
            print(f"| `{m}` | {caso} | {sum(x['ok_numeros'] for x in sub)}/{n} | {sum(x['ok_espanol'] for x in sub)}/{n} | "
                  f"{sum(x['ok_aviso'] for x in sub)}/{n} | {sum(x['ok'] for x in sub)}/{n} | {media(sub, 'segundos_ciclo')} |")


if __name__ == "__main__":
    main(sys.argv[1])
