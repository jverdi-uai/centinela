from scripts.load_xlsx import load_transactions


def test_xlsx_contract_loads_all_rows():
    rows = load_transactions("data/synthetic/datos_prueba_centinela.xlsx")
    assert len(rows) == 300
    assert sum(label == "fraude" for _, label, _ in rows) == 25
    assert isinstance(rows[0][0].device.vpn, bool)

