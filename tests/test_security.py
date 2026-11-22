import pytest
from security import hashear_password, verificar_password


def test_hash_y_verificacion():
    h = hashear_password("clave-segura-123")
    assert h != "clave-segura-123"
    assert verificar_password("clave-segura-123", h)
    assert not verificar_password("otra-clave", h)


def test_rechaza_password_muy_larga():
    with pytest.raises(ValueError):
        hashear_password("a" * 73)