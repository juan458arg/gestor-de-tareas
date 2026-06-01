import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave-secreta-local-dev")

# ── Flask-Login ────────────────────────────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id, username):
        self.id       = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT id, username FROM usuarios WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close(); con.close()
    if row:
        return User(row["id"], row["username"])
    return None


# ── DB helpers ─────────────────────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)

def init_db():
    con = get_db()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id       SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tareas (
            id           SERIAL PRIMARY KEY,
            user_id      INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
            texto        TEXT NOT NULL,
            hecho        BOOLEAN DEFAULT FALSE,
            categoria    TEXT DEFAULT 'otros',
            recordatorio TIMESTAMP,
            orden        INTEGER DEFAULT 0
        )
    """)
    con.commit()
    cur.close(); con.close()

init_db()


# ── Auth ───────────────────────────────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            error = "Completá ambos campos."
        else:
            try:
                con = get_db()
                cur = con.cursor()
                cur.execute(
                    "INSERT INTO usuarios (username, password) VALUES (%s, %s)",
                    (username, generate_password_hash(password))
                )
                con.commit()
                cur.close(); con.close()
                return redirect(url_for("login"))
            except psycopg2.errors.UniqueViolation:
                error = "Ese nombre de usuario ya existe."
    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        con = get_db()
        cur = con.cursor()
        cur.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
        user_row = cur.fetchone()
        cur.close(); con.close()
        if user_row and check_password_hash(user_row["password"], password):
            login_user(User(user_row["id"], user_row["username"]))
            return redirect(url_for("index"))
        error = "Usuario o contraseña incorrectos."
    return render_template("login.html", error=error)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ── Tareas ─────────────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    categoria = request.args.get("categoria", "todas")
    estado    = request.args.get("estado", "todas")

    con = get_db()
    cur = con.cursor()

    query  = "SELECT * FROM tareas WHERE user_id = %s"
    params = [current_user.id]

    if categoria != "todas":
        query += " AND categoria = %s"
        params.append(categoria)
    if estado == "pendientes":
        query += " AND hecho = FALSE"
    elif estado == "completadas":
        query += " AND hecho = TRUE"

    query += " ORDER BY orden ASC"
    cur.execute(query, params)
    tareas = cur.fetchall()
    cur.close(); con.close()

    ahora = datetime.now()
    return render_template("index.html", tareas=tareas, ahora=ahora,
                           categoria=categoria, estado=estado)


@app.route("/agregar", methods=["POST"])
@login_required
def agregar():
    texto     = request.form.get("texto_tarea", "").strip()
    categoria = request.form.get("categoria", "otros")
    rec_str   = request.form.get("recordatorio", "")

    recordatorio = None
    if rec_str:
        try:
            recordatorio = datetime.fromisoformat(rec_str)
        except ValueError:
            pass

    if texto:
        con = get_db()
        cur = con.cursor()
        cur.execute("SELECT COALESCE(MAX(orden), -1) + 1 AS orden FROM tareas WHERE user_id = %s", (current_user.id,))
        orden = cur.fetchone()["orden"]
        cur.execute(
            "INSERT INTO tareas (user_id, texto, categoria, recordatorio, orden) VALUES (%s, %s, %s, %s, %s)",
            (current_user.id, texto, categoria, recordatorio, orden)
        )
        con.commit()
        cur.close(); con.close()

    return redirect("/")


@app.route("/completar/<int:id>")
@login_required
def completar(id):
    con = get_db()
    cur = con.cursor()
    cur.execute("UPDATE tareas SET hecho = TRUE WHERE id = %s AND user_id = %s", (id, current_user.id))
    con.commit()
    cur.close(); con.close()
    return redirect("/")


@app.route("/eliminar/<int:id>", methods=["POST"])
@login_required
def eliminar(id):
    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM tareas WHERE id = %s AND user_id = %s", (id, current_user.id))
    con.commit()
    cur.close(); con.close()
    return redirect("/")


@app.route("/reordenar", methods=["POST"])
@login_required
def reordenar():
    data = request.get_json(silent=True)
    if not data or "orden" not in data:
        return jsonify({"error": "payload inválido"}), 400
    con = get_db()
    cur = con.cursor()
    for i, id_ in enumerate(data["orden"]):
        cur.execute("UPDATE tareas SET orden = %s WHERE id = %s AND user_id = %s",
                    (i, id_, current_user.id))
    con.commit()
    cur.close(); con.close()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)