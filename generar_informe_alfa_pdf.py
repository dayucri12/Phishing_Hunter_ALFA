import os, json, glob
from datetime import date
from fpdf import FPDF


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
os.makedirs("resultados_alfa", exist_ok=True)
os.makedirs("informes_alfa", exist_ok=True)

# ============ CONFIGURACIÓN COLORES (igual que BRAVO, mantenemos coherencia) ============
COLOR_CABECERA_AZUL = (30, 58, 138)
COLOR_FILAS_PAR = (240, 240, 240)
COLOR_ROJO = (192, 0, 0)
COLOR_VERDE = (0, 128, 0)
COLOR_NARANJA = (230, 140, 0)

def generar_informe_pdf(marca: str, ruta_json: str = ""):
    # 1. LEER JSON
    if not ruta_json:
        jsons = sorted(glob.glob(os.path.join(BASE_DIR, "resultados_alfa", f"{marca.lower()}_resultados_*.json")))
        if not jsons:
            print("No hay JSON de resultados ALFA. Ejecuta primero phishing_hunter.py")
            return
        ruta_json = jsons[-1]
    with open(ruta_json, encoding="utf-8") as f:
        datos = json.load(f)
    
    # Datos compactos para tabla resumen
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
   
    
    # ============ PORTADA ============
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 36)
    pdf.cell(w=0, h=120, text=f"PHISHING HUNTER", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(w=0, h=40, text=f"INFORME DETECCION DOMINIOS SOSPECHOSOS", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(h=20)
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(w=0, h=20, text=f"Marca protegida: {marca.upper()}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(w=0, h=20, text=f"Fecha informe: {date.today().isoformat()}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(w=0, h=20, text=f"Total candidatos analizados: {len(datos)}", new_x="LMARGIN", new_y="NEXT", align="C")
    
    # ============ TABLA RESUMEN ============
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(w=0, h=30, text="TABLA RESUMEN CANDIDATOS", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(h=8)
    
    anchos = [140, 100, 50, 60, 60, 70, 40]  # suma = 520pt ✅
    cabeceras = ["Dominio", "IP", "DNS", "HTTP", "Ratio", "Riesgo", "Alerta"]
    
    # Cabecera azul texto blanco
    pdf.set_fill_color(*COLOR_CABECERA_AZUL)
    pdf.set_text_color(255,255,255)
    pdf.set_font("Helvetica", "B", 9)
    for i, cab in enumerate(cabeceras):
            # ===== DEBUG RÁPIDO: cuántos elementos hay (comentar luego)
        print(f"\n🐛 DEBUG tablas: len anchos={len(anchos)}, len cabeceras={len(cabeceras)}, len primera fila={len(filas[0]) if filas else 0}")
        pdf.cell(w=anchos[i], h=22, text=cab, border=1, fill=True, align="C")
    pdf.ln()
    
    # Filas de datos (zebra)
    pdf.set_text_color(0,0,0)
    for idx, fila in enumerate(filas):
        if idx % 2 == 0:
            pdf.set_fill_color(*COLOR_FILAS_PAR)
        else:
            pdf.set_fill_color(255,255,255)
        
        # Colores riesgo para columna 5 y 6
        riesgo_texto = fila[5]
        alerta_texto = fila[6]
        
        for i, val in enumerate(fila):
            texto = str(val)[:60]
            if i == 5:  # columna Riesgo
                if "ALTO" in riesgo_texto.upper():
                    pdf.set_text_color(*COLOR_ROJO); pdf.set_font("Helvetica","B",9)
                elif "MEDIO" in riesgo_texto.upper():
                    pdf.set_text_color(*COLOR_NARANJA); pdf.set_font("Helvetica","B",9)
                elif "NINGUNO" in riesgo_texto.upper():
                    pdf.set_text_color(*COLOR_VERDE); pdf.set_font("Helvetica","B",9)
                else:
                    pdf.set_text_color(0,0,0); pdf.set_font("Helvetica","",9)
            elif i == 6:  # columna Alerta (SI/NO)
                if alerta_texto == "SI":
                    pdf.set_text_color(*COLOR_ROJO); pdf.set_font("Helvetica","B",9)
                else:
                    pdf.set_text_color(*COLOR_VERDE); pdf.set_font("Helvetica","",9)
            else:
                pdf.set_text_color(0,0,0); pdf.set_font("Helvetica","",9)
            pdf.cell(w=anchos[i], h=20, text=texto, border=1, fill=True, align="C" if i in [2,3,4,6] else "L")
        pdf.ln()
        pdf.set_text_color(0,0,0)
        pdf.set_font("Helvetica", "", 9)
    
    # ============ PÁGINAS INDIVIDUALES POR DOMINIO ACTIVO ============
    pdf.set_font("Helvetica", "B", 18)
    for d in datos:
        if not d.get("dns_ok"):
            continue
        pdf.add_page()
        pdf.cell(w=0, h=30, text=f"ANALISIS: {d.get('dominio')}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(h=10)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(w=0, h=16, text=f"Marca protegida: {d.get('marca_protegida')}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(w=0, h=16, text=f"IP: {d.get('ip')}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(w=0, h=16, text=f"Estado DNS: {' OK' if d.get('dns_ok') else ' FAIL'}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(w=0, h=16, text=f"Estado HTTP: {d.get('status_code') if d.get('http_ok') else ' FAIL'}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(w=0, h=16, text=f"Ratio similitud difflib: {d.get('ratio_similitud', 0.0):.2f}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica","B",11)
        pdf.cell(w=0, h=16, text=f"NIVEL RIESGO: {d.get('nivel_riesgo')}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(w=0, h=16, text=f"POSIBLE PHISHING: {' SI' if d.get('posible_phishing') else 'NO'}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(h=6)
        pdf.set_font("Helvetica","",11)
        pdf.cell(w=0, h=16, text=f"Razón: {d.get('razon_riesgo','')}", new_x="LMARGIN", new_y="NEXT")
        if d.get("titulo_html"):
            pdf.ln(h=6)
            pdf.set_font("Helvetica","B",11)
            pdf.cell(w=0, h=16, text="Título HTML <title> extraído OGParser:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica","",10)
            pdf.multi_cell(w=0, h=14, text=d.get("titulo_html","")[:600], border=1, align="L")
    
    # GUARDAR PDF
    ruta_pdf = f"informes_alfa/INFORME_PHISHING_HUNTER_{marca.upper()}_{date.today().isoformat()}.pdf"
    pdf.output(os.path.join(BASE_DIR, ruta_pdf))
    print(f"\n🎉 PDF INFORME ALFA generado: {ruta_pdf}")
    return ruta_pdf

if __name__ == "__main__":
    generar_informe_pdf(marca="paypal")