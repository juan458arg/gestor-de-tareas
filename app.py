from flask import Flask, render_template, request, redirect

app = Flask(__name__)

# Base de datos temporal
tareas = []
siguiente_id = 1

def agregar_tarea(texto):
    global siguiente_id
    tareas.append({'id': siguiente_id, 'texto': texto, 'hecho': False})
    siguiente_id += 1

def completar_tarea(id_tarea):
    for tarea in tareas:
        if tarea['id'] == id_tarea:
            tarea['hecho'] = True
            break

@app.route('/')
def index():
    # Ordenar: Las no hechas arriba
    tareas_ordenadas = sorted(tareas, key=lambda t: t['hecho'])
    return render_template('index.html', tareas=tareas_ordenadas)

@app.route('/agregar', methods=['POST'])
def agregar():
    texto = request.form.get('texto_tarea')
    if texto:
        agregar_tarea(texto)
    return redirect('/')

@app.route('/completar/<int:id>')
def completar(id):
    completar_tarea(id)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)