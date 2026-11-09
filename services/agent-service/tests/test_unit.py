"""Pruebas unitarias de las piezas sin modelo: validación del token y clasificación de la intención."""
import pytest

from app.errors import ApiError
from app.graph import classify, clean, numbers_in
from app.security import check_token
from conftest import make_token


class TestToken:
    def test_valid_token(self):
        token, teacher = check_token(f"Bearer {make_token(sub='3')}")
        assert teacher == "3" and token.count(".") == 2

    @pytest.mark.parametrize("header", [None, "", "Bearer ", "Basic abc", "Bearer solo-texto", "Bearer a.b.c"])
    def test_invalid_token(self, header):
        with pytest.raises(ApiError) as exc:
            check_token(header)
        assert exc.value.code == "TOKEN_INVALID" and exc.value.status == 401

    def test_expired_token(self):
        with pytest.raises(ApiError) as exc:
            check_token(f"Bearer {make_token(exp_in=-5)}")
        assert exc.value.code == "TOKEN_EXPIRED" and exc.value.status == 401


class TestIntent:
    @pytest.mark.parametrize("message", [
        "Cambia la nota de Ana en la Tarea 1 a 10",
        "Modifica la calificación del estudiante 5",
        "Ponle un 10 en la nota de Luis",
    ])
    def test_cannot_modify_grades(self, message):
        assert classify(message)[0] == "fuera_de_alcance"

    @pytest.mark.parametrize("message", [
        "Envía un correo a los estudiantes con entregas pendientes",
        "Mándales un mensaje de WhatsApp a los que no entregaron",
    ])
    def test_cannot_send_messages(self, message):
        assert classify(message)[0] == "fuera_de_alcance"

    @pytest.mark.parametrize("message", [
        "¿Crees que Luis tiene depresión?",
        "Predice si Ana va a reprobar el semestre y diagnostica su ansiedad",
    ])
    def test_no_psychological_claims(self, message):
        intent, reason = classify(message)
        assert intent == "fuera_de_alcance" and "psicológico" in reason

    @pytest.mark.parametrize("message", ["Hola", "Buenos días", "¿Qué puedes hacer?", "gracias", "ayuda"])
    def test_greeting_and_help(self, message):
        assert classify(message)[0] == "ayuda"

    @pytest.mark.parametrize("message", ["Dame el informe del curso 2", "Hazme un resumen del curso"])
    def test_report(self, message):
        assert classify(message)[0] == "informe"

    @pytest.mark.parametrize("message", [
        "¿Qué cursos tengo?",
        "¿Cómo va Ana en la Tarea 1?",
        "¿Qué puedo hacer para que suban las notas del curso?",  # consejo sobre datos, no pide modificar una nota
        "¿Qué estudiantes tienen entregas pendientes?",
    ])
    def test_data_questions(self, message):
        assert classify(message)[0] == "consulta_datos"


def test_numbers_use_comma_and_dot():
    assert numbers_in("promedio de 5,5 sobre 10 y 44.44 %") == {5.5, 10.0, 44.44}


def test_clean_removes_control_characters_and_truncates():
    assert clean("hola\x00\x07 mundo") == "hola mundo"
    assert len(clean("x" * 10_000, limit=100)) == 100
