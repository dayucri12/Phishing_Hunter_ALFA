import os, socket, random
import json
import urllib.request
import urllib.error
from html.parser import HTMLParser
import difflib
from datetime import date
import socket
socket.setdefaulttimeout(5)  # <-- AÑADIR ESTA LÍNEA. Timeout GLOBAL de socket (5 segundos).



# ============ CLASE OGParser REUTILIZADA de og_scraper.py ============
class OGParser(HTMLParser):
    """REUTILIZADA: Extrae el <title> de un HTML (usado luego para difflib).
       Mismo patrón 3 hooks + bandera booleana que en tu scraper."""
    def __init__(self):
        super().__init__()
        self.en_title = False    # bandera: ¿estamos dentro del tag <title>?
        self.title = ""          # almacenamos el título extraído
    
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "title":
            self.en_title = True
    
    def handle_data(self, data):
        if self.en_title:
            self.title += data.strip()
    
    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.en_title = False
            
# ============ CONFIGURACIÓN GLOBAL ALFA (typosquatting) ============

# HOMOGLIFOS (caracteres que PARECEN IGUALES): o↔0, l↔1, i↔1, s↔5
MAPA_HOMOGLIFOS = {
    'o': '0',
    '0': 'o',
    'l': '1',
    '1': 'l',
    'i': '1',
    's': '5',
    '5': 's',
}

# TECLAS CERCANAS EN TECLADO QWERTY (para adición/substitución)
# Usado: a está cerca de q/s/z; b cerca de v/n/g/h...
TECLAS_CERCANAS = {
    'a': 'qwsz',
    'b': 'vghn',
    'c': 'xdfv',
    'd': 'ersfcx',
    'e': 'wsdfr',
    'f': 'rtdgcv',
    'g': 'tyfhbv',
    'h': 'tygujb',
    'i': 'uojkl',
    'j': 'uikmn',
    'k': 'iojlm',
    'l': 'opk',
    'm': 'njk',
    'n': 'bhjm',
    'o': 'iklp',
    'p': 'ol',
    'q': 'wa',
    'r': 'tedf',
    's': 'waedzx',
    't': 'rfgy',
    'u': 'yihj',
    'v': 'cfgb',
    'w': 'qase',
    'x': 'zsdc',
    'y': 'tghu',
    'z': 'asx',
    '0': '9',
    '1': '2q',
}

# PALABRAS CLAVE SOSPECHOSAS de phishing (insertar antes/despues)
PALABRAS_SOSPECHOSAS = [
    "-login", "-signin", "-verify", "-secure", "-update", "-account",
    "-oficial", "-clientes", "-app", "-web", "-login-portal",
    "-area-cliente", "-acceso", "-seguridad",
]

# TLDs más comunes + TLDs gratuitos sospechosos
TLDS = [
    ".com", ".es", ".net", ".org", ".co.uk", ".eu",
    ".com.es", ".eu.org", ".tk", ".ml", ".ga", ".cf", ".gq", ".xyz"
]

# ============ CAPA 1: GENERADOR DE PERMUTACIONES CANDIDATAS ============

def generar_permutaciones(marca: str) -> list[str]:
    """Genera TODAS las variaciones typosquatting de una marca.
       Devuelve una LISTA DE STRINGS (dominios candidatos SIN TLD, solo la marca modificada).
       Ej: generar_permutaciones("paypal") → ['aypal','pypal','papal','paypa','paypall', ...]"""
    marca = marca.lower().strip()
    candidatos = set()   # ← ¿Por qué SET en vez de LIST? Pregunta guía P1!

    # ============================================================
    # CASO 1: OMISSION (quitar UNA letra de cada posición)
    # Ej: paypal → paypal[:i] + paypal[i+1:] para i de 0..5
    # ============================================================
    for i in range(len(marca)):
        candidato = marca[:i] + marca[i+1:]
        candidatos.add(candidato)  # añade sin repeticiones gracias al SET

    # AQUÍ LUEGO AÑADIREMOS CASO 2,3,4,5,6 (Addition, Homoglifos, Repeticion, Palabras, TLDs...)
        # ============================================================
    # CASO 2: ADDITION (añadir UNA LETRA CERCANA en cada posición)
    # Ej: paypal (6 letras = 7 posibles posiciones para insertar: ANTES de c/letra + FINAL)
    # ============================================================
    for i in range(len(marca) + 1):  # por cada posición (7 si len=6)
        for letra_cerca in TECLAS_CERCANAS.get(marca[i-1] if i > 0 else marca[0], ''):
            # marca[i-1] si no es primera posic, para letra más próxima al carácter actual
            candidato = marca[:i] + letra_cerca + marca[i:]
            candidatos.add(candidato)
            
        # ============================================================
    # CASO 3: SUBSTITUTION (homoglifos) - cambiamos letra por su gemelo visual
    # Ej: paypal → paypa1 (letra l por 1)
    # ============================================================
    for i in range(len(marca)):
        letra_actual = marca[i]
        if letra_actual in MAPA_HOMOGLIFOS:
            # substitucion UNA letra (por cada i cambiamos solo una posición para no generar demasiados)
            lista = list(marca)
            lista[i] = MAPA_HOMOGLIFOS[letra_actual]
            candidato = ''.join(lista)
            candidatos.add(candidato)
    # Al final convertimos set a lista ordenada y devolvemos
    
        # ============================================================
    # CASO 4: REPETICIÓN - duplicar UNA letra en su posición
    # ============================================================
    for i in range(len(marca)):
        letra_actual = marca[i]
        # duplicamos: pongo la letra DOS veces
        candidato = marca[:i] + (letra_actual * 2) + marca[i+1:]
        candidatos.add(candidato)
        
       # ============================================================
    # CASO 5: PALABRAS SOSPECHOSAS (CORREGIDO DEFINITIVO)
    # Al FINAL  = marca + palabra  (ej: paypal-login   ✅)
    # Al INICIO = palabra sin guion izq + marca  (ej: loginpaypal ✅)
    # ============================================================
    for palabra in PALABRAS_SOSPECHOSAS:
        # 5a. PALABRA DESPUÉS MARCA (más común): paypal-login
        candidatos.add(marca + palabra)                      # con guion
        candidatos.add(marca + palabra.replace('-', ''))     # sin guion: paypallogin
        
        # 5b. PALABRA ANTES MARCA: QUITAMOS GUIONES IZQUIERDOS A LA PALABRA
        pal = palabra.lstrip('-')
        candidatos.add(pal + marca)                          # loginpaypal
        candidatos.add(pal.replace('-', '') + marca)
        
        # ============================================================
    # CASO 6: SUBSTITUTION teclas cercanas (no homoglifos, solo cambio letra por 1 cercana)
    # ============================================================
    for i in range(len(marca)):
        letra_actual = marca[i]
        for letra_cerca in TECLAS_CERCANAS.get(letra_actual, ''):
            lista = list(marca)
            lista[i] = letra_cerca
            candidato = ''.join(lista)
            candidatos.add(candidato)
    return sorted(candidatos)      

def montar_dominios_completos(marca: str) -> list[str]:
    """Coge las permutaciones, les concatena CADA TLD y devuelve lista completa DOMINIOS FINALES.
       Ej: 'aypal' + [.com, .es, .eu.org] → ['aypal.com','aypal.es','aypal.eu.org']
    """
    permutaciones = generar_permutaciones(marca)
    dominios_finales = set()   # sin duplicados
    for perm in permutaciones:
        for tld in TLDS:
            dominios_finales.add(perm + tld)
    # También AÑADIMOS la MARCA ORIGINAL con cada TLD (para comparar el dominio real)
    for tld in TLDS:
        dominios_finales.add(marca.lower() + tld)
    return sorted(dominios_finales)
    


# ===== PRUEBA RÁPIDA CAPA 1 =====

    


    # ============ CAPA 2: COMPROBACIÓN EXISTENCIA EN INTERNET (CASCADA) ============

def comprobar_dns(dominio: str) -> tuple[bool, str]:
    """Devuelve (existe: bool, ip: str). Muy rápido 0.01s.
       Si hay socket.gaierror = NO EXISTE (DNS no resuelve)."""
    try:
        ip = socket.gethostbyname(dominio)
        return (True, ip)
    except socket.gaierror:
        return (False, "")
    except Exception:
        return (False, "")

def comprobar_http(dominio: str, timeout: int = 3) -> tuple[bool, int, str, str]:
    """Paso 2 (más lento). Devuelve (responde_http, status_code, html, titulo_extraido).
       html lo devolvemos para luego extraer título con HTMLParser (CAPA 3).
       titulo_extraido aquí lo ponemos "" por ahora, lo llenaremos en CAPA 3."""
    url = f"http://{dominio}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        html_bytes = resp.read()
        try:
            html = html_bytes.decode("utf-8", errors="replace")
        except Exception:
            html = html_bytes.decode("latin-1", errors="replace")
        return (True, resp.status, html, "")
    except urllib.error.HTTPError as e:
        return (True, e.code, "", "")
    except Exception:
        return (False, 0, "", "")


def extraer_titulo(html: str) -> str:
    """Dado un HTML string, usa OGParser (reutilizado) para sacar <title>."""
    if not html:
        return ""
    try:
        parser = OGParser()
        parser.feed(html)
        return parser.title.strip()[:200]  # truncar por si hay títulos muy largos
    except Exception:
        return ""

def calcular_similitud(texto1: str, texto2: str) -> float:
    """MEJORADA: 2 estrategias combinadas.
    (1) ratio difflib normal + (2) si marca está CONTENIDA en título → BONIFICACIÓN extra.
    """
    t1 = texto1.lower().strip()
    t2 = texto2.lower().strip()
    if not t1 or not t2:
        return 0.0
    
    # Estrategia A: difflib clásico
    ratio_difflib = difflib.SequenceMatcher(None, t1, t2).ratio()
    
    # Estrategia B: ¿Contención (si t1 contiene la marca t2 o viceversa
    ratio_contiene = 0.0
    if t2 in t1 or t1 in t2:
        ratio_contiene = 0.90
    
    # Devolvemos el MAYOR de los dos
    return max(ratio_difflib, ratio_contiene)

    

def analizar_todo_candidato(dominio: str, marca: str) -> dict:
    """FUNCIÓN MAESTRA: aplica los 2 pasos en cascada.
       Retorna DICCIONARIO con todos los datos para luego generar JSON/PDF."""
    resultado = {
        "dominio": dominio,
        "marca_protegida": marca,
        "dns_ok": False,
        "ip": "",
        "http_ok": False,
        "status_code": 0,
        "titulo_html": "",
        "ratio_similitud": 0.0,
        "posible_phishing": False,
        "nivel_riesgo": "BAJO",
        "razon_riesgo": "",
    }
    # PASO 1: DNS (muy rápido, 99% descartado aquí)
    resultado["dns_ok"], resultado["ip"] = comprobar_dns(dominio)
    if not resultado["dns_ok"]:
        resultado["razon_riesgo"] = "NO EXISTE DNS (dominio no registrado)."
        return resultado
    
    # PASO 2: HTTP (sólo si pasó DNS)
    resultado["http_ok"], resultado["status_code"], html, _ = comprobar_http(dominio)
    if not resultado["http_ok"] or resultado["status_code"] >= 500:
        resultado["razon_riesgo"] = "Responde DNS pero NO HTTP válido (timeout/error 5xx)."
        return resultado
    
      # ============ CAPA 3 ANÁLISIS TÍTULO + SIMILITUD ============
    # 3a. Extraer TÍTULO HTML con OGParser REUTILIZADO :)
    resultado["titulo_html"] = extraer_titulo(html)
    
    # 3b. CALCULAR SIMILITUD entre TÍTULO y MARCA PROTEGIDA con difflib
    if resultado["titulo_html"]:
        resultado["ratio_similitud"] = calcular_similitud(resultado["titulo_html"], marca)
    
    # 3c. LÓGICA CLASIFICACIÓN PHISHING (umbrales)
    ratio = resultado["ratio_similitud"]
    
    # Si el dominio es EXACTAMENTE el OFICIAL (marca original + TLD común) → 0 riesgo
    dominio_sin_tld = dominio.rsplit(".", 1)[0]
    tld = "." + dominio.rsplit(".", 1)[-1] if "." in dominio else ""
    es_oficial = (dominio_sin_tld == marca.lower()) and (tld in [".com", ".es", ".net", ".org", ".eu"])
    if es_oficial:
        resultado["posible_phishing"] = False
        resultado["nivel_riesgo"] = "NINGUNO (OFICIAL)"
        resultado["razon_riesgo"] = "Dominio OFICIAL confirmado (marca + TLD válido)."
        return resultado
    
    # Umbrales RIESGO
    if ratio >= 0.85:
        resultado["posible_phishing"] = True
        resultado["nivel_riesgo"] = "ALTO"
        resultado["razon_riesgo"] = f"⚠️  SIMILITUD MUY ALTA ({ratio:.0%}) con el título de la marca. ¡POSIBLE PHISHING!"
    elif ratio >= 0.55:
        resultado["nivel_riesgo"] = "MEDIO"
        resultado["razon_riesgo"] = f"Similitud media ({ratio:.0%}). Revisión manual recomendada."
    elif ratio > 0.0:
        resultado["nivel_riesgo"] = "BAJO"
        resultado["razon_riesgo"] = f"Similitud baja ({ratio:.0%}). Poco probable phishing."
    else:
        resultado["nivel_riesgo"] = "BAJO"
        resultado["razon_riesgo"] = "No hay título HTML extraído o no tiene similitud."
    
    return resultado
    
   
# ============ CAPA 4: GUARDAR RESULTADOS JSON ============
def guardar_resultados_json(resultados: list[dict], marca: str):
    os.makedirs("resultados_alfa", exist_ok=True)
    ruta = f"resultados_alfa/{marca.lower()}_resultados_{date.today().isoformat()}.json"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"\n💾 JSON guardado correctamente: {ruta} ({len(resultados)} registros)")
    return ruta    
    
    
    
if __name__ == "__main__":
    os.makedirs("resultados_alfa", exist_ok=True)
    
    print("\n" + "="*70)
    print("🧪 PRUEBA RÁPIDA CAPA 1 + CAPA 2: 15 dominios candidatos paypal")
    print("="*70)
    
    TODOS = montar_dominios_completos("paypal")
    random.shuffle(TODOS)  # mezcla aleatoria, no orden alfabetico
    doms_prueba = TODOS[:10] 
    
        # asegurarnos de incluir el dominio oficial para ver que lo marca como DNS OK
    doms_prueba[0] = "paypal.com"
    
   # SOLO 15, no 1372!
    
    resultados = []
    for i, dominio in enumerate(doms_prueba, start=1):
        print(f"\n[{i}/{len(doms_prueba)}] Analizando: {dominio}")
        res = analizar_todo_candidato(dominio, "paypal")
        resultados.append(res)
        
        # Resumen compacto en consola
        color_dns = "✅ DNS" if res["dns_ok"] else "❌ DNS"
        color_http = f"✅ HTTP {res['status_code']}" if res["http_ok"] else "❌ HTTP"
        similitud = f"Ratio: {res['ratio_similitud']:.2f}" if res['ratio_similitud']>0 else ""
        riesgo = f"⚠️  RIESGO: {res['nivel_riesgo']}" if res["nivel_riesgo"] != "BAJO" else "BAJO"
        print(f"    → {color_dns} | {color_http} | IP: {res['ip']} | {similitud} | {riesgo}")
        print(f"    → Razón: {res['razon_riesgo']}")
    
    if res["titulo_html"]:
        print(f"    📄 Título: {res['titulo_html'][:100]}...")
    
    print("\n" + "="*70)
    print("📊 RESUMEN FINAL PRUEBA:")
    print("="*70)
    con_dns = sum(1 for r in resultados if r["dns_ok"])
    con_http = sum(1 for r in resultados if r["http_ok"])
    print(f"✅ Total analizados: {len(resultados)}")
    print(f"🟢 Con DNS activo: {con_dns}/{len(resultados)}")
    print(f"🔵 Con HTTP válido: {con_http}/{len(resultados)}")
    print(f"🔴 Posibles phishings (CAPA3): {sum(1 for r in resultados if r['posible_phishing'])}/{len(resultados)}")
    
        # GUARDAR JSON
    ruta_json = guardar_resultados_json(resultados, marca="paypal")