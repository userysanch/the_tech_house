"""Servidor temporal para descargar rootCA.pem e instalar en el celular."""
import http.server, os

PORT = 5001
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DIR, **kw)
    def log_message(self, fmt, *a):
        print(f"  {a[0]}")

print(f"\n  Servidor de descarga: http://192.168.0.10:{PORT}")
print(f"  Abre esto en tu celular para descargar el certificado CA.\n")
http.server.HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
