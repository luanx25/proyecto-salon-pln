from sitio import validar_config


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