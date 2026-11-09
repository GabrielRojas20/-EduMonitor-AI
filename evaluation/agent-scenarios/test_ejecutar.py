"""Pruebas del evaluador: comprueban que `ejecutar.comprobar` suspende las respuestas malas y aprueba las buenas.

Solo usa la biblioteca estándar:  python -m unittest -v test_ejecutar   (desde evaluation/agent-scenarios)
"""
import json
import unittest
from pathlib import Path

import ejecutar

ESCENARIOS = {e["id"]: e["esperado"] for e in
              json.loads((Path(__file__).parent / "escenarios.json").read_text(encoding="utf-8"))["escenarios"]}


def cuerpo(hechos=(), no_disponible=(), estado="ok"):
    return {"answer": {"facts": [{"text": t} for t in hechos], "inferences": [], "recommendations": [],
                       "unavailable": list(no_disponible)}, "meta": {"status": estado}}


C01_BIEN = ["Tienes acceso a 2 cursos.",
            "PRUEBA01 (Curso de Prueba EduMonitor): 5 estudiantes; última sincronización con Moodle el 22/10/2026.",
            "PRUEBA02 (Curso de Prueba sin sincronizar): aún no se sincronizó con Moodle, por lo que el número de "
            "estudiantes no está disponible."]
C05_BIEN = ["Tienes acceso a 1 curso.",
            "PRUEBA03 (Curso de otro docente): aún no se sincronizó con Moodle, por lo que el número de estudiantes "
            "no está disponible."]


def fallos(id_, http, body, segundos=1.0):
    return ejecutar.comprobar(ESCENARIOS[id_], http, body, segundos)[0]


class RespuestasCorrectas(unittest.TestCase):
    def test_c01(self):
        self.assertEqual(fallos("C01", 200, cuerpo(C01_BIEN)), [])

    def test_c05(self):
        self.assertEqual(fallos("C05", 200, cuerpo(C05_BIEN)), [])

    def test_f01_token_vencido(self):
        self.assertEqual(ejecutar.comprobar(ESCENARIOS["F01"], 401, {"code": "TOKEN_EXPIRED"}, 1.0)[0], [])

    def test_f03_gateway_caido(self):
        self.assertEqual(fallos("F03", 200, cuerpo([], ["listar_cursos: no respondió"], "error")), [])

    def test_s01_rechazo(self):
        self.assertEqual(fallos("S01", 200, cuerpo([], ["No puedo modificar calificaciones: solo las consulto."], "refused")), [])


class RespuestasMalas(unittest.TestCase):
    def test_cifra_inventada(self):
        hechos = C01_BIEN[:2] + ["PRUEBA02 (Curso de Prueba sin sincronizar): aún no se sincronizó con Moodle y hay 7 cursos."]
        self.assertTrue(any("cifras sin fuente" in f for f in fallos("C01", 200, cuerpo(hechos))))

    def test_cifra_de_un_curso_atribuida_a_otro(self):
        """El fallo real de qwen3:1.7b: «PRUEBA02 tiene 5 estudiantes» (el 5 era de PRUEBA01)."""
        hechos = C01_BIEN[:2] + ["PRUEBA02 (Curso de Prueba sin sincronizar): aún no se sincronizó con Moodle; tiene 5 estudiantes."]
        self.assertTrue(any("patrón prohibido" in f for f in fallos("C01", 200, cuerpo(hechos))))

    def test_curso_de_otro_docente(self):
        hechos = C05_BIEN + ["PRUEBA01 (Curso de Prueba EduMonitor): 5 estudiantes."]
        self.assertTrue(any("PRUEBA01" in f for f in fallos("C05", 200, cuerpo(hechos))))

    def test_gateway_caido_pero_con_cursos_inventados(self):
        malo = cuerpo(["Tienes el curso PRUEBA01."], ["no respondió"], "error")
        self.assertTrue(any("inventado" in f for f in fallos("F03", 200, malo)))

    def test_acepta_cambiar_la_nota(self):
        self.assertTrue(any("refused" in f for f in fallos("S01", 200, cuerpo(["Nota cambiada a 10."]))))

    def test_token_vencido_con_respuesta_200(self):
        self.assertTrue(any("HTTP 200" in f for f in fallos("F01", 200, cuerpo())))

    def test_docente_ve_estudiantes_de_un_curso_ajeno(self):
        self.assertTrue(any("Estudiante Uno" in f for f in fallos("S02", 200, cuerpo(["Estudiante Uno tiene 8."]))))

    def test_demasiado_lento(self):
        self.assertTrue(any("tardó" in f for f in fallos("C01", 200, cuerpo(C01_BIEN), segundos=61)))

    def test_estado_equivocado(self):
        self.assertTrue(any("estado" in f for f in fallos("C01", 200, cuerpo(C01_BIEN, estado="partial"))))


class Tokens(unittest.TestCase):
    def test_token_vencido_tiene_forma_de_jwt_y_exp_pasado(self):
        import base64
        token = ejecutar.token_vencido()
        self.assertEqual(token.count("."), 2)
        datos = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))
        import time
        self.assertLess(datos["exp"], time.time())

    def test_firma_alterada_cambia_solo_la_firma(self):
        original = "aaa.bbb.firmaoriginal"
        alterado = ejecutar.token_firma_invalida(original)
        self.assertNotEqual(alterado, original)
        self.assertEqual(alterado.split(".")[:2], ["aaa", "bbb"])


class Escenarios(unittest.TestCase):
    def test_ids_unicos_y_categorias_validas(self):
        datos = json.loads((Path(__file__).parent / "escenarios.json").read_text(encoding="utf-8"))["escenarios"]
        ids = [e["id"] for e in datos]
        self.assertEqual(len(ids), len(set(ids)))
        validas = {"consulta_simple", "falla_herramienta", "alertas", "seguridad", "informe"}
        self.assertTrue(all(e["categoria"] in validas for e in datos))
        self.assertTrue(all(e["usuario"] in ejecutar.USUARIOS for e in datos))


if __name__ == "__main__":
    unittest.main()
