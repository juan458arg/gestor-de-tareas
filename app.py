import os
from flask import Flask, render_template, request, redirect
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

def get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)

def init_db():
    con = get_db()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tareas (
            id          SERIAL PRIMARY KEY,
            texto       TEXT NOT NULL,
            hecho       BOOLEAN DEFAULT FALSE,
            categoria   TEXT DEFAULT 'otros',
            recordatorio TIMESTAMP,
            orden       INTEGER DEFAULT 0
        )
    """)
    con.commit()
    cur.close()
    con.close()

init_db()


# ── Rutas ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    categoria  = request.args.get('categoria', 'todas')
    estado     = request.args.get('estado', 'todas')

    con = get_db()
    cur = con.cursor()

    query  = "SELECT * FROM tareas WHERE 1=1"
    params = []

    if categoria != 'todas':
        query += " AND categoria = %s"
        params.append(categoria)
    if estado == 'pendientes':
        query += " AND hecho = FALSE"
    elif estado == 'completadas':
        query += " AND hecho = TRUE"

    query += " ORDER BY orden ASC"
    cur.execute(query, params)
    tareas = cur.fetchall()
    cur.close()
    con.close()

    ahora = datetime.now()
    return render_template('index.html', tareas=tareas, ahora=ahora,
                           categoria=categoria, estado=estado)


@app.route('/agregar', methods=['POST'])
def agregar():
    texto     = request.form.get('texto_tarea', '').strip()
    categoria = request.form.get('categoria', 'otros')
    rec_str   = request.form.get('recordatorio', '')

    recordatorio = None
    if rec_str:
        try:
            recordatorio = datetime.fromisoformat(rec_str)
        except ValueError:
            pass

    if texto:
        con = get_db()
        cur = con.cursor()
        cur.execute("SELECT COALESCE(MAX(orden), -1) + 1 FROM tareas")
        orden = cur.fetchone()['coalesce']
        cur.execute(
            "INSERT INTO tareas (texto, categoria, recordatorio, orden) VALUES (%s, %s, %s, %s)",
            (texto, categoria, recordatorio, orden)
        )
        con.commit()
        cur.close()
        con.close()

    return redirect('/')


@app.route('/completar/<int:id>')
def completar(id):
    con = get_db()
    cur = con.cursor()
    cur.execute("UPDATE tareas SET hecho = TRUE WHERE id = %s", (id,))
    con.commit()
    cur.close()
    con.close()
    return redirect('/')


@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM tareas WHERE id = %s", (id,))
    con.commit()
    cur.close()
    con.close()
    return redirect('/')


@app.route('/reordenar', methods=['POST'])
def reordenar():
    from flask import jsonify
    data = request.get_json(silent=True)
    if not data or 'orden' not in data:
        return jsonify({'error': 'payload inválido'}), 400

    con = get_db()
    cur = con.cursor()
    for i, id_ in enumerate(data['orden']):
        cur.execute("UPDATE tareas SET orden = %s WHERE id = %s", (i, id_))
    con.commit()
    cur.close()
    con.close()
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))