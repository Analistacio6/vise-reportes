#!/usr/bin/env python3
"""
=================================================================
VISE · PUBLICADOR GITHUB PAGES
Sube el reporte HTML generado a GitHub Pages automáticamente
=================================================================
Uso:
  python publicar_github.py                    # Sube el último reporte
  python publicar_github.py --archivo mi.html  # Sube un archivo específico
=================================================================
"""

import os, sys, json, base64, datetime, argparse
import urllib.request, urllib.parse, urllib.error
from pathlib import Path

# ── Cargar .env si existe ─────────────────────────────────────
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO  = os.environ.get('GITHUB_REPO', '')   # ej: juanvise/vise-reportes
GITHUB_BRANCH = os.environ.get('GITHUB_BRANCH', 'main')

# ─────────────────────────────────────────────────────────────

def subir_archivo_github(ruta_local: Path, nombre_remoto: str) -> str:
    """Sube un archivo a GitHub y retorna la URL de GitHub Pages."""
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN no configurado en .env")
        sys.exit(1)
    if not GITHUB_REPO:
        print("❌ GITHUB_REPO no configurado en .env (ej: juanvise/vise-reportes)")
        sys.exit(1)

    contenido = ruta_local.read_bytes()
    contenido_b64 = base64.b64encode(contenido).decode('utf-8')

    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{nombre_remoto}"
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Content-Type': 'application/json',
        'User-Agent': 'VISE-Bot/1.0'
    }

    # Verificar si el archivo ya existe (para obtener su SHA y actualizarlo)
    sha = None
    try:
        req_get = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req_get, timeout=15) as r:
            data = json.loads(r.read())
            sha = data.get('sha')
            print(f"  📝 Archivo existente encontrado, actualizando...")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  🆕 Creando archivo nuevo en GitHub...")
        else:
            print(f"  ⚠ Error verificando archivo: {e.code}")

    # Preparar payload
    fecha = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    payload = {
        "message": f"🇨🇴 VISE Radar Estratégico · {fecha}",
        "content": contenido_b64,
        "branch": GITHUB_BRANCH
    }
    if sha:
        payload["sha"] = sha

    # Subir archivo
    payload_bytes = json.dumps(payload).encode('utf-8')
    req_put = urllib.request.Request(api_url, data=payload_bytes, headers=headers, method='PUT')

    try:
        with urllib.request.urlopen(req_put, timeout=30) as r:
            resp = json.loads(r.read())
            usuario = GITHUB_REPO.split('/')[0]
            repo    = GITHUB_REPO.split('/')[1]
            url_pages = f"https://{usuario}.github.io/{repo}/{nombre_remoto}"
            return url_pages
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"❌ Error GitHub API {e.code}: {body[:300]}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='VISE · Publicador GitHub Pages')
    parser.add_argument('--archivo', default='reporte_vise.html',
                        help='Archivo HTML local a subir (default: reporte_vise.html)')
    parser.add_argument('--nombre', default='',
                        help='Nombre del archivo en GitHub (default: igual al local)')
    args = parser.parse_args()

    # Buscar el archivo a subir
    ruta = Path(__file__).parent / args.archivo
    if not ruta.exists():
        # Intentar también con el nombre de demo
        ruta_demo = Path(__file__).parent / 'reporte_vise_demo.html'
        if ruta_demo.exists():
            ruta = ruta_demo
            print(f"  ℹ Usando reporte demo: {ruta.name}")
        else:
            print(f"❌ No se encontró el archivo: {ruta}")
            print(f"   Ejecuta primero: python generar_reporte_vise.py --real")
            sys.exit(1)

    nombre_remoto = args.nombre or ruta.name
    # Siempre publicar también como "reporte_vise.html" para URL fija
    nombres_a_subir = [nombre_remoto]
    if nombre_remoto != 'reporte_vise.html':
        nombres_a_subir.append('reporte_vise.html')

    print(f"\n🚀 VISE · Publicando en GitHub Pages")
    print(f"   Repo:    {GITHUB_REPO}")
    print(f"   Archivo: {ruta.name} ({ruta.stat().st_size // 1024} KB)")

    url_final = None
    for nombre in nombres_a_subir:
        print(f"\n  ⬆ Subiendo como: {nombre}")
        url = subir_archivo_github(ruta, nombre)
        if nombre == 'reporte_vise.html':
            url_final = url
        print(f"  ✅ Disponible en: {url}")

    print(f"\n{'='*60}")
    print(f"✅ PUBLICACIÓN EXITOSA")
    print(f"🔗 URL FIJA DEL REPORTE:")
    print(f"   {url_final}")
    print(f"\n📱 Envía esta URL por Telegram o configúrala en n8n")
    print(f"⏳ GitHub Pages puede tardar 1-2 min en actualizar")
    print(f"{'='*60}\n")

    # Guardar la URL en un archivo para que n8n la use
    url_file = Path(__file__).parent / 'ultima_url.txt'
    url_file.write_text(url_final, encoding='utf-8')
    print(f"💾 URL guardada en: ultima_url.txt")


if __name__ == '__main__':
    main()
