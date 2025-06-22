from flask import Blueprint, render_template
from app.services import InstrumentoService

bp = Blueprint('instrumentos', __name__)

@bp.route('/')
def listar_instrumentos():
    service = InstrumentoService()
    instrumentos = service.obtener_todos()
    return render_template('instrumentos/list.html', instrumentos=instrumentos)