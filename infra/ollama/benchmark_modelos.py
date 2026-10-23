"""Benchmark de modelos locales de Ollama para EduMonitor AI (S1-12).

Mide rendimiento (carga en frío, primera respuesta, tokens por segundo, memoria),
llamadas a herramientas y calidad en español con datos de ejemplo.
Usa solo la biblioteca estándar. Guarda las salidas crudas en JSONL.

Uso:
    python benchmark_modelos.py --salida ../../docs/benchmarks/resultados
"""
import argparse
import json
import re
import subprocess
import time
import urllib.request
from pathlib import Path

BASE = "http://localhost:11434"
MODELOS = ["qwen3:1.7b", "qwen2.5:3b", "llama3.2:3b"]
REPETICIONES = 3
TEMPERATURA = 0.3  # se repite con semillas distintas para medir la estabilidad
TOKENS_RENDIMIENTO = 200

PROMPT_LARGO = (
    "Escribe un texto de al menos 400 palabras sobre la importancia del seguimiento "
    "académico de los estudiantes en un curso universitario."
)

# Herramientas de ejemplo solo para esta prueba. No son el contrato del agente (S1-11).
HERRAMIENTAS = [
    {"type": "function", "function": {
        "name": "listar_cursos",
        "description": "Lista los cursos a los que el docente tiene acceso.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "obtener_calificaciones",
        "description": "Obtiene las calificaciones de un curso, opcionalmente de un estudiante.",
        "parameters": {"type": "object", "required": ["course_id"], "properties": {
            "course_id": {"type": "integer", "description": "Id del curso en Moodle"},
            "student_id": {"type": "integer", "description": "Id del estudiante en Moodle"}}}}},
    {"type": "function", "function": {
        "name": "identificar_alertas",
        "description": "Devuelve las alertas académicas activas de un curso.",
        "parameters": {"type": "object", "required": ["course_id"], "properties": {
            "course_id": {"type": "integer", "description": "Id del curso en Moodle"}}}}},
]

# (id, mensaje, herramienta esperada o None, argumentos esperados)
CASOS_HERRAMIENTAS = [
    ("cursos", "¿Qué cursos tengo?", "listar_cursos", {}),
    ("notas", "Dame las calificaciones del estudiante 4 en el curso 2.",
     "obtener_calificaciones", {"course_id": 2, "student_id": 4}),
    ("notas_curso", "Muéstrame todas las notas del curso 2.",
     "obtener_calificaciones", {"course_id": 2}),
    ("alertas", "¿Qué alertas académicas hay en el curso 2?", "identificar_alertas", {"course_id": 2}),
    ("fuera_alcance", "Cambia la nota del estudiante 4 a 10 en el curso 2.", None, {}),
    ("saludo", "Hola, ¿qué puedes hacer?", None, {}),
]

RESULTADO_NOTAS = {
    "ok": True,
    "data": {"courseId": 2, "items": [
        {"studentId": 4, "activityName": "Tarea 1", "status": "graded", "score": 8.5, "maxScore": 10},
        {"studentId": 5, "activityName": "Tarea 1", "status": "not_submitted", "score": None, "maxScore": 10}]},
    "error": None,
}
RESULTADO_ERROR = {
    "ok": False, "data": None,
    "error": {"code": "MOODLE_UNAVAILABLE", "message": "Moodle no responde", "retryable": True},
}
NUMEROS_PERMITIDOS_NOTAS = {"1", "2", "4", "5", "8.5", "10"}
NUMEROS_PERMITIDOS_ERROR = {"2", "4", "5"}  # curso 2 y estudiantes 4 y 5, que cita la pregunta
PALABRAS_ES = {"el", "la", "de", "que", "en", "los", "las", "un", "una", "es", "no", "se", "con", "del", "para"}
PALABRAS_EN = {"the", "is", "are", "student", "grade", "was", "has", "not", "and", "with"}
AVISO_NO_DATO = re.compile(
    r"no (pude|puedo|se pudo|fue posible|est[aá] disponible|hay (datos|acceso))|no disponible|"
    r"error|problema|inconvenient|no responde|no (tengo|obtuve)", re.I)
SYSTEM = ("Eres un asistente para docentes. Responde siempre en español, usa solo los datos "
          "que devuelven las herramientas y no inventes cifras.")


def http(ruta, carga=None, metodo=None):
    datos = json.dumps(carga).encode() if carga is not None else None
    req = urllib.request.Request(BASE + ruta, datos, {"Content-Type": "application/json"}, method=metodo)
    return urllib.request.urlopen(req, timeout=900)


def descargar(modelo):
    http("/api/generate", {"model": modelo, "keep_alive": 0}).read()
    for _ in range(50):
        if not json.load(http("/api/ps")).get("models"):
            return
        time.sleep(0.5)


def estado_ps():
    return json.load(http("/api/ps"))


def chat_stream(modelo, mensajes, opciones, keep_alive=None):
    carga = {"model": modelo, "messages": mensajes, "stream": True, "think": False, "options": opciones}
    if keep_alive:
        carga["keep_alive"] = keep_alive
    t0 = time.perf_counter()
    primero, texto, final = None, [], {}
    with http("/api/chat", carga) as r:
        for linea in r:
            d = json.loads(linea)
            c = d.get("message", {}).get("content", "")
            if c and primero is None:
                primero = time.perf_counter() - t0
            texto.append(c)
            if d.get("done"):
                final = d
    total = time.perf_counter() - t0
    ns = lambda k: round(final.get(k, 0) / 1e9, 3)
    return {
        "primera_respuesta_s": round(primero, 3) if primero else None,
        "total_s": round(total, 3),
        "carga_modelo_s": ns("load_duration"),
        "tokens_prompt": final.get("prompt_eval_count"),
        "tokens_generados": final.get("eval_count"),
        "generacion_s": ns("eval_duration"),
        "tokens_por_s": round(final.get("eval_count", 0) / max(final.get("eval_duration", 1) / 1e9, 1e-9), 2),
        "respuesta": "".join(texto),
    }


def chat(modelo, mensajes, opciones, herramientas=None):
    carga = {"model": modelo, "messages": mensajes, "stream": False, "think": False, "options": opciones}
    if herramientas:
        carga["tools"] = herramientas
    t0 = time.perf_counter()
    with http("/api/chat", carga) as r:
        d = json.load(r)
    return d, round(time.perf_counter() - t0, 3)


def numeros(texto):
    return {n.replace(",", ".") for n in re.findall(r"\d+(?:[.,]\d+)?", texto)}


def es_espanol(texto):
    palabras = re.findall(r"[a-záéíóúñ]+", texto.lower())
    return sum(p in PALABRAS_ES for p in palabras) >= 3 and not any(p in PALABRAS_EN for p in palabras)


def evaluar_llamada(msg, esperada, args_esperados):
    llamadas = msg.get("tool_calls") or []
    if esperada is None:
        return not llamadas, "sin herramienta" if not llamadas else f"llamó a {llamadas[0]['function']['name']}"
    if not llamadas:
        return False, "sin tool_call"
    fn = llamadas[0]["function"]
    args = fn.get("arguments", {})
    try:
        ok = fn["name"] == esperada and all(int(args.get(k, -1)) == v for k, v in args_esperados.items()) \
            and set(args) <= set(args_esperados)
    except (TypeError, ValueError):
        ok = False
    return ok, f'{fn["name"]}({json.dumps(args, ensure_ascii=False)})'


def probar_modelo(modelo, salida):
    registros = []

    def reg(tipo, **datos):
        r = {"modelo": modelo, "tipo": tipo, **datos}
        registros.append(r)
        salida.write(json.dumps(r, ensure_ascii=False) + "\n")
        salida.flush()
        return r

    mensajes_largo = [{"role": "user", "content": PROMPT_LARGO}]
    opc = lambda semilla: {"temperature": TEMPERATURA, "seed": semilla, "num_predict": TOKENS_RENDIMIENTO}

    for i in range(REPETICIONES):  # carga en frío
        descargar(modelo)
        r = chat_stream(modelo, mensajes_largo, opc(i + 1))
        reg("rendimiento_frio", repeticion=i + 1, **r)
        if i == 0:
            reg("memoria", ps=estado_ps())

    descargar(modelo)  # precarga con keep_alive, como se haría antes de la demostración
    t0 = time.perf_counter()
    http("/api/generate", {"model": modelo, "keep_alive": "30m"}).read()
    reg("precarga_keep_alive", segundos=round(time.perf_counter() - t0, 3), keep_alive="30m")
    for i in range(REPETICIONES):  # modelo ya cargado
        reg("rendimiento_caliente", repeticion=i + 1, **chat_stream(modelo, mensajes_largo, opc(i + 1), "30m"))

    for caso, texto, esperada, args in CASOS_HERRAMIENTAS:  # llamadas a herramientas
        for i in range(REPETICIONES):
            msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": texto}]
            d, seg = chat(modelo, msgs, {"temperature": TEMPERATURA, "seed": i + 1}, HERRAMIENTAS)
            ok, detalle = evaluar_llamada(d.get("message", {}), esperada, args)
            reg("herramienta", caso=caso, repeticion=i + 1, ok=ok, detalle=detalle, segundos=seg,
                tokens_generados=d.get("eval_count"))

    escenarios = [("fidelidad_notas", RESULTADO_NOTAS, NUMEROS_PERMITIDOS_NOTAS),
                  ("falla_herramienta", RESULTADO_ERROR, NUMEROS_PERMITIDOS_ERROR)]
    for caso, resultado, permitidos in escenarios:  # segunda vuelta: redactar con el resultado
        for i in range(REPETICIONES):
            pregunta = "Dame las calificaciones del estudiante 4 y del estudiante 5 en el curso 2."
            msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": pregunta}]
            d1, seg1 = chat(modelo, msgs, {"temperature": TEMPERATURA, "seed": i + 1}, HERRAMIENTAS)
            llamada = (d1.get("message", {}).get("tool_calls") or [None])[0]
            msgs.append(d1.get("message", {}))
            if llamada is None:  # el modelo no llamó a la herramienta; se simula igualmente
                msgs.append({"role": "assistant", "content": "", "tool_calls": [{"function": {
                    "name": "obtener_calificaciones", "arguments": {"course_id": 2}}}]})
            msgs.append({"role": "tool", "tool_name": "obtener_calificaciones",
                         "content": json.dumps(resultado, ensure_ascii=False)})
            d2, seg2 = chat(modelo, msgs, {"temperature": TEMPERATURA, "seed": i + 1, "num_predict": 300})
            texto = d2.get("message", {}).get("content", "")
            extra = sorted(numeros(texto) - permitidos)
            ok_numeros = not extra
            ok_idioma = es_espanol(texto)
            ok_aviso = bool(AVISO_NO_DATO.search(texto)) if caso == "falla_herramienta" else True
            reg("calidad", caso=caso, repeticion=i + 1, llamo_herramienta=llamada is not None,
                ok_numeros=ok_numeros, numeros_no_respaldados=extra, ok_espanol=ok_idioma,
                ok_aviso=ok_aviso, ok=ok_numeros and ok_idioma and ok_aviso,
                segundos_llamada=seg1, segundos_respuesta=seg2, segundos_ciclo=round(seg1 + seg2, 3),
                respuesta=texto)
    descargar(modelo)
    return registros


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", required=True, help="carpeta para las salidas crudas (JSONL)")
    ap.add_argument("--modelos", nargs="*", default=MODELOS)
    a = ap.parse_args()
    carpeta = Path(a.salida)
    carpeta.mkdir(parents=True, exist_ok=True)
    version = subprocess.run(["ollama", "--version"], capture_output=True, text=True).stdout.strip()
    meta = {"ollama": version, "inicio": time.strftime("%Y-%m-%d %H:%M:%S"), "modelos": a.modelos,
            "repeticiones": REPETICIONES, "temperatura": TEMPERATURA, "tokens_rendimiento": TOKENS_RENDIMIENTO}
    (carpeta / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    for m in a.modelos:
        print("==", m, flush=True)
        with open(carpeta / (m.replace(":", "_") + ".jsonl"), "w", encoding="utf-8") as f:
            probar_modelo(m, f)
    print("LISTO", flush=True)


if __name__ == "__main__":
    main()
