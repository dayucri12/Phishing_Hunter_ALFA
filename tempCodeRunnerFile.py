  filas = []
    for d in datos:
        riesgo = d.get("nivel_riesgo", "BAJO")
        alerta_texto = "SI" if d.get("posible_phishing") else "NO"
        filas.append((
            d.get("dominio", ""),
            d.get("ip", ""),
            "SI" if d.get("dns_ok") else "NO",   # ← sin emojis, ASCII puro
            str(d.get("status_code", 0)) if d.get("http_ok") else "NO",
            f"{d.get('ratio_similitud', 0.0):.2f}",
            riesgo if riesgo else "BAJO",
            alerta_texto,
        ))
    
    pdf = FPDF(orientation="P", unit="pt", format="A4")
    pdf.set_auto_page_break(auto=True, margin=40)