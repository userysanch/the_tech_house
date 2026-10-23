from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from models import Producto
import re

buscador_bp = Blueprint('buscador', __name__)

def buscar_productos(query, limit=30):
    """Busca productos separando la consulta en palabras individuales."""
    if not query or not query.strip():
        return []

    palabras = query.strip().split()
    filtros = []
    for palabra in palabras:
        patron = f'%{palabra}%'
        filtros.append(
            (Producto.codigo.ilike(patron)) |
            (Producto.nombre.ilike(patron))
        )

    from sqlalchemy import and_
    productos = Producto.query.filter(and_(*filtros)).limit(limit).all()
    return productos

def resaltar(texto, query):
    """Resalta las palabras de la consulta en el texto."""
    if not query or not texto:
        return texto
    palabras = query.strip().split()
    for palabra in palabras:
        patron = re.compile(re.escape(palabra), re.IGNORECASE)
        texto = patron.sub(lambda m: f'<mark>{m.group()}</mark>', texto)
    return texto

@buscador_bp.route('/', methods=['GET'])
@login_required
def buscador_view():
    query = request.args.get('q', '').strip()
    productos = buscar_productos(query)
    resultados = []
    for p in productos:
        resultados.append({
            'id': p.id,
            'codigo': p.codigo,
            'codigo_barras': p.codigo_barras or '',
            'nombre': p.nombre,
            'nombre_resaltado': resaltar(p.nombre, query),
            'codigo_resaltado': resaltar(p.codigo, query),
            'precio': float(p.precio),
            'stock': p.stock
        })
    return render_template('buscador.html', productos=resultados, query=query)

@buscador_bp.route('/api/buscar', methods=['GET'])
@login_required
def api_buscar():
    query = request.args.get('q', '').strip()
    if len(query) < 1:
        return jsonify([])

    productos = buscar_productos(query, limit=20)
    resultados = []
    for p in productos:
        resultados.append({
            'id': p.id,
            'codigo': p.codigo,
            'codigo_barras': p.codigo_barras or '',
            'codigo_resaltado': resaltar(p.codigo, query),
            'nombre': p.nombre,
            'nombre_resaltado': resaltar(p.nombre, query),
            'precio': float(p.precio),
            'precio_fmt': f'Q{p.precio:.2f}',
            'stock': p.stock,
            'stock_texto': str(p.stock) if p.stock > 0 else 'Agotado',
            'stock_clase': 'success' if p.stock > 5 else ('warning' if p.stock > 0 else 'danger')
        })
    return jsonify(resultados)
