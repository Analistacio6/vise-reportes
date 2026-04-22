#!/usr/bin/env python3
"""
=================================================================
VISE · RADAR ESTRATÉGICO v2.0
Generador de Informe con IA + Mapa + GitHub Pages
=================================================================
Uso:
  python generar_reporte_vise.py              # Demo (sin internet)
  python generar_reporte_vise.py --real       # Con RSS + Gemini
  python generar_reporte_vise.py --real --publicar  # + sube a GitHub
  python generar_reporte_vise.py --region bogota    # Enfoque regional
=================================================================
"""

import json, datetime, os, sys, random, re, argparse, base64, subprocess
import urllib.request, urllib.parse, urllib.error
from pathlib import Path

# ── Cargar .env ──────────────────────────────────────────────
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

# ─── CONFIGURACIÓN ───────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "PEGA_TU_API_KEY_AQUI")
LOGO_PATH      = os.environ.get("VISE_LOGO", "logo_vise.png")
PLANTILLA_PATH = Path(__file__).parent / "plantilla_vise.html"
SALIDA_PATH    = Path(__file__).parent / "reporte_vise.html"

FUENTES_RSS = [
    {"url": "https://caracol.com.co/feed/",                        "fuente": "Caracol Radio"},
    {"url": "https://www.rcnradio.com/feed",                       "fuente": "RCN Radio"},
    {"url": "https://www.elespectador.com/arc/outboundfeeds/rss/", "fuente": "El Espectador"},
    {"url": "https://www.semana.com/rss/rss.xml",                  "fuente": "Semana"},
    {"url": "https://www.pulzo.com/rss.xml",                       "fuente": "Pulzo"},
    {"url": "https://www.bluradio.com/feed",                       "fuente": "Blu Radio"},
    {"url": "https://www.wradio.com.co/feed/",                     "fuente": "W Radio"},
    {"url": "https://noticias.caracoltv.com/rss",                  "fuente": "Caracol TV"},
    {"url": "https://www.noticiasrcn.com/rss.xml",                 "fuente": "Noticias RCN"},
]

COORDS = {
    "bogotá":[4.7110,-74.0721],"bogota":[4.7110,-74.0721],
    "medellín":[6.2442,-75.5812],"medellin":[6.2442,-75.5812],
    "cali":[3.4516,-76.5320],"barranquilla":[10.9685,-74.7813],
    "cartagena":[10.3910,-75.4794],"bucaramanga":[7.1254,-73.1198],
    "pereira":[4.8133,-75.6961],"manizales":[5.0703,-75.5138],
    "santa marta":[11.2408,-74.2110],"cúcuta":[7.8939,-72.5078],
    "cucuta":[7.8939,-72.5078],"ibagué":[4.4389,-75.2322],
    "pasto":[1.2136,-77.2811],"montería":[8.7479,-75.8814],
    "villavicencio":[4.1420,-73.6266],"armenia":[4.5339,-75.6811],
    "neiva":[2.9273,-75.2819],"valledupar":[10.4631,-73.2532],
    "florencia":[1.6143,-75.6062],"quibdó":[5.6920,-76.6584],
    "riohacha":[11.5444,-72.9072],"leticia":[-4.2153,-69.9406],
    "antioquia":[6.2442,-75.5812],"cundinamarca":[4.7110,-74.0721],
    "valle del cauca":[3.4516,-76.5320],"atlántico":[10.9685,-74.7813],
    "caquetá":[1.6143,-75.6062],"chocó":[5.6920,-76.6584],
    "nariño":[1.2136,-77.2811],"córdoba":[8.7479,-75.8814],
    "santander":[7.1254,-73.1198],"meta":[4.1420,-73.6266],
    "huila":[2.9273,-75.2819],"tolima":[4.4389,-75.2322],
    "cauca":[2.4448,-76.6147],"norte de santander":[7.8939,-72.5078],
    "cesar":[10.4631,-73.2532],"sucre":[9.3047,-75.3978],
    "nacional":[4.5709,-74.2973],"colombia":[4.5709,-74.2973],
}

COLORES_CAT = {
    "homicidio":"#e74c3c","combate":"#e74c3c","captura":"#e67e22",
    "atentado":"#c0392b","desastre":"#2ecc71","protesta":"#f1c40f",
    "trafico":"#3498db","corrupcion":"#9b59b6","otro":"#8fafc8"
}

ICONOS_CAT = {
    "homicidio":"💀","combate":"⚔️","captura":"🚔","atentado":"💣",
    "desastre":"🌊","protesta":"✊","trafico":"🚗","corrupcion":"💰","otro":"📍"
}

# ─── DATOS DE DEMOSTRACIÓN ────────────────────────────────────
DEMO_NOTICIAS = [
    {"titulo":"Despliegue operativo en Suroccidente tras alertas sobre grupos residuales","descripcion":"Fuerzas Militares activan plan de contingencia en zona minero-energética","link":"#","fuente":"Caracol Radio","fecha":datetime.datetime.now().isoformat(),"alto_impacto":True,"categoria":"combate","region":"Antioquia","resumen":"Vigilancia reforzada en infraestructura minero-energética del Bajo Cauca.","nivel":"CRITICO"},
    {"titulo":"Vía Panamericana cierre preventivo sector Rosas por contingencia geológica","descripcion":"Falla geológica activa genera cierre total en Ruta 25 Sur","link":"#","fuente":"INVIAS","fecha":datetime.datetime.now().isoformat(),"alto_impacto":True,"categoria":"trafico","region":"Cauca","resumen":"Cierre total en Rosas-Cauca. Desvío disponible con demoras de 2h.","nivel":"CRITICO"},
    {"titulo":"Captura de presunto cabecilla de banda criminal en Medellín","descripcion":"Operativo policial conjunto en comunas nororientales","link":"#","fuente":"Policía Nacional","fecha":datetime.datetime.now().isoformat(),"alto_impacto":True,"categoria":"captura","region":"Medellín","resumen":"Captura exitosa. Desarticulación parcial de estructura delictiva.","nivel":"ALTO"},
    {"titulo":"Atentado con explosivo contra torre de energía en Norte de Santander","descripcion":"Artefacto explosivo causa interrupción del servicio","link":"#","fuente":"RCN Radio","fecha":datetime.datetime.now().isoformat(),"alto_impacto":True,"categoria":"atentado","region":"Norte de Santander","resumen":"Atentado contra infraestructura energética. Sin víctimas fatales.","nivel":"CRITICO"},
    {"titulo":"Bloqueo en acceso norte de Bogotá por protesta de transportadores","descripcion":"Transportadores bloquean Autopista Norte exigiendo reducción de peajes","link":"#","fuente":"Blu Radio","fecha":datetime.datetime.now().isoformat(),"alto_impacto":True,"categoria":"protesta","region":"Bogotá","resumen":"Bloqueo Autopista Norte desde 6am. Policía en lugar.","nivel":"ALTO"},
    {"titulo":"Restricción vehicular KM 58 vía al Llano por lluvias intensas","descripcion":"Paso por franjas horarias en Vía al Llano sector KM 58","link":"#","fuente":"INVIAS","fecha":datetime.datetime.now().isoformat(),"alto_impacto":True,"categoria":"trafico","region":"Cundinamarca","resumen":"Restricción horaria KM 58 vía al Llano. Paso 6am-10am y 2pm-6pm.","nivel":"MEDIO"},
    {"titulo":"Derrumbe en Quibdó bloquea vía secundaria por lluvias del Pacífico","descripcion":"Emergencia geológica en Chocó","link":"#","fuente":"Defensa Civil","fecha":datetime.datetime.now().isoformat(),"alto_impacto":True,"categoria":"desastre","region":"Chocó","resumen":"Derrumbe en vía secundaria Quibdó. Comunidades aisladas temporalmente.","nivel":"ALTO"},
    {"titulo":"Plan Corredores Logísticos Seguros activa 12 nodos del Ejército","descripcion":"Ejército Nacional despliega unidades para garantizar flujo de carga","link":"#","fuente":"Mindefensa","fecha":datetime.datetime.now().isoformat(),"alto_impacto":True,"categoria":"combate","region":"Nacional","resumen":"Activación Plan Corredores Logísticos Seguros. 12 nodos críticos protegidos.","nivel":"MEDIO"},
]

# ─── FUNCIONES UTILITARIAS ────────────────────────────────────
def get_coords(region):
    if not region: return [4.5709 + random.uniform(-.3,.3), -74.2973 + random.uniform(-.3,.3)]
    r = region.lower().strip()
    for k, v in COORDS.items():
        if k in r or r in k:
            return [v[0]+random.uniform(-.05,.05), v[1]+random.uniform(-.05,.05)]
    return [4.5709+random.uniform(-2,2), -74.2973+random.uniform(-2,2)]

def esc(s):
    if not s: return ''
    return str(s).replace('\\','\\\\').replace('`',"'").replace('${','\\${').replace('\n',' ').replace('\r','')

def get_logo_tag():
    """Carga el logo como base64 para incrustar en el HTML."""
    logo = Path(__file__).parent / LOGO_PATH
    if logo.exists():
        try:
            data = logo.read_bytes()
            ext = logo.suffix.lower().replace('.', '')
            if ext == 'jpg': ext = 'jpeg'
            b64 = base64.b64encode(data).decode()
            return f'<img src="data:image/{ext};base64,{b64}" alt="VISE" style="width:100%;height:100%;object-fit:contain">'
        except Exception as e:
            print(f"  ⚠ Error cargando logo: {e}")
    return '<svg class="logo-svg" viewBox="0 0 40 40"><text y="30" font-size="28" fill="#00c9a7">V</text></svg>'

def fetch_rss(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  ⚠ Error RSS {url[:50]}: {e}")
        return ''

def parse_rss(xml, fuente, max_items=6):
    items = re.findall(r'<item>([\s\S]*?)</item>', xml)
    result = []
    for item in items[:max_items]:
        def get(tag):
            m = re.search(r'<'+tag+r'>\s*<!\[CDATA\[([\s\S]*?)\]\]>\s*</'+tag+r'>', item)
            if not m: m = re.search(r'<'+tag+r'>([^<]*)</'+tag+r'>', item)
            return m.group(1).strip() if m else ''
        titulo = get('title')
        if not titulo or len(titulo) < 10: continue
        desc = re.sub(r'<[^>]+>', '', get('description'))
        desc = desc.replace('&nbsp;',' ').replace('&amp;','&').replace('&lt;','<').replace('&gt;','>').strip()
        result.append({'titulo': titulo[:200], 'descripcion': desc[:400],
                       'link': get('link') or get('guid'),
                       'fuente': fuente, 'fecha': datetime.datetime.now().isoformat()})
    return result

def llamar_gemini(prompt, max_tokens=3000):
    if GEMINI_API_KEY in ('PEGA_TU_API_KEY_AQUI', ''):
        print("  ⚠ API Key no configurada, usando datos demo")
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
        payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                              "generationConfig": {"temperature": 0.15, "maxOutputTokens": max_tokens}}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type':'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode('utf-8'))
            return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"  ⚠ Error Gemini: {e}")
        return None

def obtener_noticias_reales():
    """Obtiene noticias de todas las fuentes RSS configuradas."""
    todas = []
    for src in FUENTES_RSS:
        print(f"  📡 {src['fuente']}...")
        xml = fetch_rss(src['url'])
        if xml:
            items = parse_rss(xml, src['fuente'])
            todas.extend(items)
            print(f"     ✓ {len(items)} noticias")
    return todas

def clasificar_noticias(raw_items):
    if not raw_items: return DEMO_NOTICIAS
    titulos = "\n".join([f"[{i}][{n['fuente']}] {n['titulo']}" for i,n in enumerate(raw_items[:25])])
    prompt = f"""Eres analista de seguridad de VISE Ltda Colombia.
Clasifica estas noticias. Devuelve SOLO un array JSON sin markdown, un objeto por noticia:
titulo, fuente, alto_impacto (bool), categoria (homicidio/combate/captura/atentado/desastre/protesta/trafico/corrupcion/otro), region (ciudad o departamento exacto), resumen (máx 2 líneas), nivel (CRITICO/ALTO/MEDIO/BAJO)

NOTICIAS:
{titulos}

Solo el array JSON:"""
    resp = llamar_gemini(prompt)
    if not resp: return DEMO_NOTICIAS
    try:
        limpio = resp.strip().replace('```json','').replace('```','').strip()
        clasificadas = json.loads(limpio)
        for i, n in enumerate(clasificadas):
            if i < len(raw_items):
                n['link'] = raw_items[i].get('link','#')
                n['fecha'] = raw_items[i].get('fecha', datetime.datetime.now().isoformat())
                n['descripcion'] = raw_items[i].get('descripcion','')
        return clasificadas
    except Exception as e:
        print(f"  ⚠ Error parseando Gemini: {e}")
        return DEMO_NOTICIAS

def generar_analisis_ia(noticias, region=None):
    titulos = "\n".join([f"[{n.get('nivel','')}] {n.get('titulo','')}" for n in noticias[:20]])
    enfoque = f"con énfasis especial en {region}" if region else "con énfasis en Bogotá"
    prompt = f"""Eres el analista jefe de VISE Ltda, empresa de vigilancia y seguridad colombiana.
Basándote en estas noticias de hoy, genera análisis para el Boletín Radar Estratégico {enfoque}.

NOTICIAS:
{titulos}

Genera en formato JSON (sin markdown):
{{
  "resumen_tactico": [
    {{"tipo": "critico|tech|norma|alerta|info", "nombre": "título corto", "descripcion": "1 línea"}}
  ],
  "distribucion": [
    {{"region": "nombre región", "eventos": número, "pct": porcentaje_0_100}}
  ],
  "corredores": [
    {{"ruta": "nombre ruta", "estado": "CIERRE TOTAL|RESTRINGIDO|NORMAL|ALERTA", "nombre": "Sector", "descripcion": "1 línea"}}
  ],
  "recomendaciones": [
    {{"categoria": "LOGÍSTICA|PERÍMETROS|DIGITAL|OPERACIONAL", "texto": "recomendación concreta"}}
  ]
}}

Máximo 4 items por sección. Solo JSON."""
    resp = llamar_gemini(prompt)
    default = {
        "resumen_tactico": [
            {"tipo":"critico","nombre":"Monitoreo Activo","descripcion":"Sistema en modo de vigilancia activa"},
            {"tipo":"info","nombre":"Fuentes Verificadas","descripcion":"RSS de medios nacionales consultados"}
        ],
        "distribucion": [
            {"region":"Bogotá","eventos":3,"pct":35},{"region":"Antioquia","eventos":2,"pct":25},
            {"region":"Valle del Cauca","eventos":1,"pct":15},{"region":"Otras","eventos":2,"pct":25}
        ],
        "corredores": [
            {"ruta":"Ruta 25","estado":"RESTRINGIDO","nombre":"Sur-Cauca","descripcion":"Verificar condiciones"},
            {"ruta":"Autopista Norte","estado":"ALERTA","nombre":"Bogotá Norte","descripcion":"Monitoreo activo"}
        ],
        "recomendaciones": [
            {"categoria":"LOGÍSTICA","texto":"Coordinar con proveedores ante posibles demoras en vías del sur"},
            {"categoria":"PERÍMETROS","texto":"Reforzar protocolos de acceso en instalaciones críticas"},
            {"categoria":"DIGITAL","texto":"Mantener canales de comunicación de respaldo activos"}
        ]
    }
    if not resp: return default
    try:
        limpio = resp.strip().replace('```json','').replace('```','').strip()
        return json.loads(limpio)
    except:
        return default

# ─── GENERACIÓN DE HTML ───────────────────────────────────────
def construir_tarjetas(noticias):
    html = ''
    cats_html = {'homicidio':('💀','ic-red'),'combate':('⚔️','ic-red'),'captura':('🚔','ic-amber'),
                 'atentado':('💣','ic-red'),'desastre':('🌊','ic-cyan'),'protesta':('✊','ic-amber'),
                 'trafico':('🚗','ic-blue'),'corrupcion':('💰','ic-cyan'),'otro':('📍','ic-green')}
    nivel_badge = {'CRITICO':'badge-red','ALTO':'badge-amber','MEDIO':'badge-green','BAJO':'badge-gray'}

    for n in noticias[:12]:
        nivel = n.get('nivel','BAJO')
        cat   = n.get('categoria','otro')
        icon, ic_class = cats_html.get(cat, ('📍','ic-green'))
        badge = nivel_badge.get(nivel,'badge-gray')
        nivel_class = nivel.lower()
        link = n.get('link','#')
        link_html = f'<a href="{link}" target="_blank" class="news-link">Ver noticia →</a>' if link and link != '#' else ''
        fecha_str = ''
        try:
            fecha_str = datetime.datetime.fromisoformat(n.get('fecha','')).strftime('%H:%M')
        except: pass

        html += f'''<div class="news-card {nivel_class}">
  <div class="news-icon-wrap {ic_class}">{icon}</div>
  <div>
    <div class="news-title">{n.get('titulo','')[:120]}</div>
    <div class="news-body">{n.get('resumen', n.get('descripcion',''))[:200]}</div>
    <div class="news-meta">
      <span class="badge {badge}">{nivel}</span>
      <span class="badge badge-gray">{cat.upper()}</span>
      <span class="news-src">📰 {n.get('fuente','')} {fecha_str}</span>
      {link_html}
    </div>
  </div>
</div>'''
    return html

def construir_resumen_tactico(items):
    html = ''
    tipo_badge = {'critico':'critico','tech':'tech','norma':'norma','alerta':'alerta','info':'info'}
    for item in items[:4]:
        badge = tipo_badge.get(item.get('tipo','info'),'info')
        html += f'''<div class="rt-item">
  <div class="rt-badge {badge}">{item.get('tipo','INFO').upper()}</div>
  <div><div class="rt-name">{item.get('nombre','')}</div>
  <div class="rt-desc">{item.get('descripcion','')}</div></div>
</div>'''
    return html

def construir_distribucion(items):
    html = ''
    colores = ['#e74c3c','#e67e22','#00c9a7','#1e88e5','#9b59b6']
    for i, item in enumerate(items[:5]):
        color = colores[i % len(colores)]
        pct = min(item.get('pct', 20), 100)
        html += f'''<div class="dist-row">
  <div class="dist-head"><span class="dist-label">{item.get('region','')}</span>
  <span class="dist-num">{item.get('eventos',0)} eventos</span></div>
  <div class="dist-bar"><div class="dist-fill" style="width:{pct}%;background:{color}"></div></div>
</div>'''
    return html

def construir_corredores(items):
    html = ''
    st_class = {'CIERRE TOTAL':'st-cierre','RESTRINGIDO':'st-restringido','NORMAL':'st-normal','ALERTA':'st-alerta'}
    for item in items[:6]:
        estado = item.get('estado','NORMAL')
        sc = st_class.get(estado,'st-normal')
        html += f'''<div class="corredor-card">
  <div class="corredor-label">{item.get('ruta','')}</div>
  <div class="corredor-status {sc}">{estado}</div>
  <div class="corredor-name">{item.get('nombre','')}</div>
  <div class="corredor-desc">{item.get('descripcion','')}</div>
</div>'''
    return html

def construir_recomendaciones(items):
    html = ''
    for item in items[:6]:
        html += f'''<div class="recom-card">
  <div class="recom-cat">{item.get('categoria','')}</div>
  <div class="recom-text">{item.get('texto','')}</div>
</div>'''
    return html

def generar_html(noticias, analisis, region=None):
    """Genera el HTML final del reporte."""
    plantilla = PLANTILLA_PATH.read_text(encoding='utf-8')

    now = datetime.datetime.now()
    fecha_str  = now.strftime('%d/%m/%Y %H:%M')
    anio_str   = str(now.year)

    # Estadísticas
    total    = len(noticias)
    criticos = sum(1 for n in noticias if n.get('nivel')=='CRITICO')
    altos    = sum(1 for n in noticias if n.get('nivel')=='ALTO')
    medios   = sum(1 for n in noticias if n.get('nivel')=='MEDIO')
    fuentes  = len(set(n.get('fuente','') for n in noticias))
    enfoque  = region.upper() if region else "NACIONAL"

    # Datos del mapa
    markers = []
    heat    = []
    for n in noticias:
        coords = get_coords(n.get('region',''))
        cat    = n.get('categoria','otro')
        nivel  = n.get('nivel','BAJO')
        w_heat = {'CRITICO':1.0,'ALTO':0.75,'MEDIO':0.5,'BAJO':0.25}.get(nivel, 0.3)
        heat.append([coords[0], coords[1], w_heat])
        markers.append({
            'lat':    coords[0],
            'lng':    coords[1],
            'cat':    cat,
            'nivel':  nivel,
            'titulo': n.get('titulo','')[:80],
            'resumen':n.get('resumen','')[:120],
            'fuente': n.get('fuente',''),
            'link':   n.get('link','#')
        })

    # Construir secciones HTML
    tarjetas        = construir_tarjetas(noticias)
    resumen_tac     = construir_resumen_tactico(analisis.get('resumen_tactico',[]))
    distribucion    = construir_distribucion(analisis.get('distribucion',[]))
    corredores_html = construir_corredores(analisis.get('corredores',[]))
    recomend_html   = construir_recomendaciones(analisis.get('recomendaciones',[]))
    logo_tag        = get_logo_tag()

    # Reemplazar placeholders en la plantilla
    html = plantilla
    replacements = {
        '{{FECHA}}':          fecha_str,
        '{{AÑO}}':            anio_str,
        '{{TOTAL_EVENTOS}}':  str(total),
        '{{TOTAL}}':          str(total),
        '{{CRITICOS}}':       str(criticos),
        '{{ALTOS}}':          str(altos),
        '{{MEDIOS}}':         str(medios),
        '{{FUENTES}}':        str(fuentes),
        '{{ENFOQUE}}':        enfoque,
        '{{NOTICIAS_HTML}}':  tarjetas,
        '{{RESUMEN_TACTICO}}':resumen_tac,
        '{{DISTRIBUCION}}':   distribucion,
        '{{CORREDORES}}':     corredores_html,
        '{{RECOMENDACIONES}}':recomend_html,
        '{{LOGO_TAG}}':       logo_tag,
        '{{HEAT_DATA}}':      json.dumps(heat),
        '{{MARKERS_DATA}}':   json.dumps(markers),
    }
    for k, v in replacements.items():
        html = html.replace(k, v)

    return html

# ─── PUNTO DE ENTRADA ─────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='VISE · Radar Estratégico Colombia v2')
    parser.add_argument('--real',      action='store_true', help='Usar RSS reales + Gemini')
    parser.add_argument('--publicar',  action='store_true', help='Publicar en GitHub Pages')
    parser.add_argument('--region',    default='',          help='Enfoque regional (ej: bogota)')
    parser.add_argument('--demo',      action='store_true', help='Solo datos demo (sin internet)')
    parser.add_argument('--salida',    default='',          help='Nombre del archivo de salida')
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  🇨🇴  VISE · RADAR ESTRATÉGICO v2.0")
    print("="*60)

    # Definir salida
    salida = Path(args.salida) if args.salida else SALIDA_PATH

    # 1. Obtener noticias
    if args.real and not args.demo:
        print("\n📡 PASO 1: Obteniendo noticias de RSS...")
        raw = obtener_noticias_reales()
        print(f"  ✓ {len(raw)} noticias obtenidas de {len(FUENTES_RSS)} fuentes")

        print("\n🤖 PASO 2: Clasificando con Gemini...")
        noticias = clasificar_noticias(raw)
        print(f"  ✓ {len(noticias)} noticias clasificadas")
    else:
        print("\n📋 Usando datos de demostración...")
        noticias = DEMO_NOTICIAS
        print(f"  ✓ {len(noticias)} eventos de ejemplo")

    # Filtrar por región si se especifica
    region = args.region.lower().strip() if args.region else ''
    if region:
        filtradas = [n for n in noticias if region in n.get('region','').lower() or n.get('region','').lower() in region]
        if len(filtradas) >= 3:
            noticias = filtradas + [n for n in noticias if n not in filtradas]
            print(f"  📍 Enfoque en: {region.upper()} ({len(filtradas)} eventos específicos)")

    # 2. Análisis IA
    print("\n🧠 PASO 3: Generando análisis estratégico...")
    analisis = generar_analisis_ia(noticias, region or None)
    print("  ✓ Análisis generado")

    # 3. Generar HTML
    print("\n🎨 PASO 4: Construyendo infografía...")
    html = generar_html(noticias, analisis, region)
    salida.write_text(html, encoding='utf-8')
    size_kb = salida.stat().st_size // 1024
    print(f"  ✓ Guardado: {salida} ({size_kb} KB)")

    # 4. Publicar en GitHub Pages
    if args.publicar:
        print("\n🚀 PASO 5: Publicando en GitHub Pages...")
        try:
            pub_script = Path(__file__).parent / 'publicar_github.py'
            result = subprocess.run(
                [sys.executable, str(pub_script), '--archivo', salida.name],
                capture_output=True, text=True
            )
            print(result.stdout)
            if result.returncode != 0:
                print(f"  ⚠ Error al publicar: {result.stderr[:200]}")
        except Exception as e:
            print(f"  ⚠ Error al publicar: {e}")

    print("\n" + "="*60)
    print(f"  ✅ REPORTE GENERADO EXITOSAMENTE")
    print(f"  📄 Archivo: {salida.name}")
    print(f"  📊 Eventos: {len(noticias)} | Críticos: {sum(1 for n in noticias if n.get('nivel')=='CRITICO')}")
    print(f"  🕐 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")

    # Abrir en el navegador automáticamente
    if '--no-open' not in sys.argv:
        try:
            import webbrowser
            webbrowser.open(salida.resolve().as_uri())
            print("  🌐 Abierto en el navegador")
        except: pass

if __name__ == '__main__':
    main()
