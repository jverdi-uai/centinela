from centinela.core.vector_store import deterministic_embedding


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def test_mock_embeddings_are_deterministic_and_token_sensitive():
    base = deterministic_embedding("beneficiario nuevo monto alto vpn")
    similar = deterministic_embedding("monto alto para beneficiario nuevo")
    different = deterministic_embedding("documento firma fecha emision")
    assert base == deterministic_embedding("beneficiario nuevo monto alto vpn")
    assert cosine(base, similar) > cosine(base, different)
