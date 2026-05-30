from flask import Flask, render_template, request, redirect, jsonify
from datetime import datetime

app = Flask(__name__)

tareas = [
    {'id': 1, 'texto': 'Revisar el informe trimestral', 'hecho': False, 'categoria': 'trabajo', 'recordatorio': None, 'orden': 0},
    {'id': 2, 'texto': 'Ir al gimnasio',               'hecho': False, 'categoria': 'personal', 'recordatorio': None, 'orden': 1},
    {'id': 3, 'texto': 'Enviar propuesta al cliente',  'hecho': False, 'categoria': 'urgente',  'recordatorio': None, 'orden': 2},
    {'id': 4, 'texto': 'Comprar víveres',              'hecho': True,  'categoria': 'personal', 'recordatorio': None, 'orden': 3},
]
siguiente_id = 10


def agregar_tarea(texto, categoria='otros', recordatorio=None):
    global siguiente_id
    orden_max = max((t['orden'] for t in tareas), default=-1) + 1
    tareas.append({
        'id':          siguiente_id,
        'texto':       texto,
        'hecho':       False,
        'categoria':   categoria,
        'recordatorio': recordatorio,
        'orden':       orden_max,
    })
    siguiente_id += 1


def completar_tarea(id_tarea):
    for tarea in tareas:
        if tarea['id'] == id_tarea:
            tarea['hecho'] = True
            break


# ── Rutas ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    categoria  = request.args.get('categoria', 'todas')
    solo_estado = request.args.get('estado', 'todas')   # pendientes | completadas

    filtradas = list(tareas)

    if categoria != 'todas':
        filtradas = [t for t in filtradas if t['categoria'] == categoria]

    if solo_estado == 'pendientes':
        filtradas = [t for t in filtradas if not t['hecho']]
    elif solo_estado == 'completadas':
        filtradas = [t for t in filtradas if t['hecho']]

    filtradas.sort(key=lambda t: t['orden'])

    ahora = datetime.now()
    return render_template('index.html', tareas=filtradas, ahora=ahora,
                           categoria=categoria, estado=solo_estado)


@app.route('/agregar', methods=['POST'])
def agregar():
    texto      = request.form.get('texto_tarea', '').strip()
    categoria  = request.form.get('categoria', 'otros')
    recordatorio_str = request.form.get('recordatorio', '')

    recordatorio = None
    if recordatorio_str:
        try:
            recordatorio = datetime.fromisoformat(recordatorio_str)
        except ValueError:
            pass

    if texto:
        agregar_tarea(texto, categoria, recordatorio)
    return redirect('/')


@app.route('/completar/<int:id>')
def completar(id):
    completar_tarea(id)
    return redirect('/')


@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    global tareas
    tareas = [t for t in tareas if t['id'] != id]
    return redirect('/')


@app.route('/reordenar', methods=['POST'])
def reordenar():
    """Recibe {"orden": [id1, id2, id3, ...]} y actualiza el campo orden."""
    data = request.get_json(silent=True)
    if not data or 'orden' not in data:
        return jsonify({'error': 'payload inválido'}), 400

    id_a_orden = {id_: i for i, id_ in enumerate(data['orden'])}
    for tarea in tareas:
        if tarea['id'] in id_a_orden:
            tarea['orden'] = id_a_orden[tarea['id']]

    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(debug=True)