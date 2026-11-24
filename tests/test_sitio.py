from sitio import validar_config
from uploads import _extension


def test_color_invalido():
    _, errores = validar_config({"nombre_salon": "Salón", "color_principal": "rojo"})
    assert any("color" in e.lower() for e in errores)


def test_whatsapp_se_limpia_a_digitos():
    limpios, errores = validar_config({
        "nombre_salon": "Salón", "color_principal": "#112233", "whatsapp": "+52 (55) 1234-5678",
    })
    assert not errores
    assert limpios["whatsapp"] == "525512345678"


def test_redes_exigen_https():
    _, errores = validar_config({
        "nombre_salon": "Salón", "color_principal": "#112233", "instagram": "javascript:alert(1)",
    })
    assert errores



def test_detecta_formatos_por_contenido():
    assert _extension(b"\xff\xd8\xff\xe0abc") == "jpg"
    assert _extension(b"\x89PNG\r\n\x1a\n....") == "png"
    assert _extension(b"RIFF1234WEBPdata") == "webp"


def test_rechaza_archivos_disfrazados():
    assert _extension(b"<svg onload=alert(1)>") is None
    assert _extension(b"#!/usr/bin/env python") is None