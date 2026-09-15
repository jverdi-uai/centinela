from centinela.core.rules import transaction_fuzzy_score
from centinela.agents.documents.checks import valid_chilean_rut


def test_fuzzy_boundaries():
    assert transaction_fuzzy_score(0.5, 0, 2) == 0
    assert transaction_fuzzy_score(4, 7, 800) == 1
    assert 0 < transaction_fuzzy_score(1.5, 3, 120) < 1


def test_chilean_rut_modulo_11():
    assert valid_chilean_rut("12.345.678-5")
    assert not valid_chilean_rut("12.345.678-9")

