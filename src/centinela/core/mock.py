def mock_customer_message(process: str, verdict: str) -> str:
    if process == "transaction":
        return {
            "aprobar": "La operación fue aprobada.",
            "validacion_adicional": "Necesitamos confirmar esta operación con una validación adicional.",
            "bloquear": "Por tu seguridad, la operación quedó en revisión. Un ejecutivo puede ayudarte.",
        }[verdict]
    return {
        "autentico": "El documento fue validado correctamente.",
        "sospechoso": "Necesitamos una captura más nítida o el documento original para continuar.",
        "falso": "El documento quedó en revisión con un ejecutivo.",
    }[verdict]

