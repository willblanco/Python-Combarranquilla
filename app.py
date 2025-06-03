from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from datetime import date, timedelta
from flask import send_file
import io
import os


app = Flask(__name__)
app.secret_key = "clave_secreta_para_flask"  # también hardcodeado

# ————————————————————————————————
# DATOS DE LA BASE DE DATOS
DB_HOST      = "mysql-c5521b4-pycombarranquilla.e.aivencloud.com"
DB_PORT      = 19817
DB_USER      = "avnadmin"
DB_PASS      = "AVNS_a6BsQw8ARsvy7IKuWIn"
DB_NAME      = "defaultdb"
SSL_CA_PATH  = os.path.join(os.path.dirname(__file__), "certs", "ca.pem")
# ————————————————————————————————

# Configuración MySQL con SSL, usando las constantes
app.config['MYSQL_HOST']     = DB_HOST
app.config['MYSQL_PORT']     = DB_PORT
app.config['MYSQL_USER']     = DB_USER
app.config['MYSQL_PASSWORD'] = DB_PASS
app.config['MYSQL_DB']       = DB_NAME
app.config['MYSQL_SSL_CA']   = SSL_CA_PATH

mysql = MySQL(app)


#LOGINN
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form['usuario']
        clave   = request.form['clave']
        if not usuario or not clave:
            flash("Completa todos los campos.", "warning")
            return redirect(url_for('login'))
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE nombre_usuario=%s AND password=%s",
                    (usuario, clave))
        if cur.fetchone():
            session['user'] = usuario
            return redirect(url_for('tareas'))
        else:
            flash("Usuario o contraseña incorrectos.", "danger")
            return redirect(url_for('login'))
    return render_template("login.html")

#MOSTRAR Y AGREGAR TAREAS
@app.route("/tareas", methods=["GET", "POST"])
def tareas():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Agregar nueva tarea
    if request.method == "POST":
        titulo  = request.form['titulo'].strip()
        desc    = request.form['descripcion'].strip()
        fecha_s = request.form['fecha']
        estado  = request.form['estado']
        # Validación fecha igual que en Tkinter
        fecha_dt = date.fromisoformat(fecha_s)
        hoy = date.today()
        if not titulo or not desc or fecha_dt < hoy or fecha_dt > hoy + timedelta(days=30):
            flash("Datos inválidos o campos vacíos.", "danger")
            return redirect(url_for('tareas'))

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO tareas (titulo, descripcion, fecha, estado) VALUES (%s,%s,%s,%s)",
            (titulo, desc, fecha_s, estado)
        )
        mysql.connection.commit()
        flash("Tarea agregada correctamente.", "success")
        return redirect(url_for('tareas'))

    # Mostrar tareas
    filtro = request.args.get("filtro", "Todos")
    cur = mysql.connection.cursor()
    if filtro == "Todos":
        cur.execute("SELECT id, titulo, descripcion, fecha, estado FROM tareas ORDER BY fecha")
    else:
        cur.execute("SELECT id, titulo, descripcion, fecha, estado FROM tareas WHERE estado=%s ORDER BY fecha",
                    (filtro,))
    filas = cur.fetchall()

    # calculamos fecha mínima y máxima como strings ISO
    min_date = date.today().isoformat()
    max_date = (date.today() + timedelta(days=30)).isoformat()

    return render_template(
        "tareas.html",
        tareas=filas,
        filtro=filtro,
        min_date=min_date,
        max_date=max_date,
        edit_tarea=None,
        edit_id=None
        )

#EDITAR
@app.route("/tareas/editar/<int:id>", methods=["POST"])
def editar(id):
    # 1 Recuperar los datos del formulario
    titulo  = request.form.get('titulo', '').strip()
    desc    = request.form.get('descripcion', '').strip()
    fecha_s = request.form.get('fecha', '')
    estado  = request.form.get('estado', '')

    # 2 Validaciones
    if not titulo or not desc or not fecha_s or not estado:
        flash("Todos los campos son obligatorios.", "warning")
        return redirect(url_for('tareas'))

    # 3 Hacer el UPDATE en la BD
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE tareas SET titulo=%s, descripcion=%s, fecha=%s, estado=%s WHERE id=%s",
        (titulo, desc, fecha_s, estado, id)
    )
    mysql.connection.commit()

    # 4 Mensaje y redirección
    flash("Tarea actualizada correctamente.", "success")
    return redirect(url_for('tareas'))

#EDITAR PRECARGAR INFO
@app.route("/tareas/editar/<int:id>", methods=["GET"])
def editar_form(id):
    cur = mysql.connection.cursor()
    
    # 1) Carga los datos de la tarea a editar
    cur.execute(
        "SELECT titulo, descripcion, fecha, estado FROM tareas WHERE id=%s",
        (id,)
    )
    tarea = cur.fetchone()

    # 2) Calcula min_date y max_date
    min_date = date.today().isoformat()
    max_date = (date.today() + timedelta(days=30)).isoformat()

    # 3) Prepara la consulta para la lista según filtro
    filtro = request.args.get("filtro", "Todos")
    if filtro == "Todos":
        sql = "SELECT id, titulo, descripcion, fecha, estado FROM tareas ORDER BY fecha ASC"
        params = ()
    else:
        sql = "SELECT id, titulo, descripcion, fecha, estado FROM tareas WHERE estado=%s ORDER BY fecha ASC"
        params = (filtro,)

    cur.execute(sql, params)
    filas = cur.fetchall()

    # 4) Renderiza el template con edit_tarea y edit_id
    return render_template(
        "tareas.html",
        tareas=filas,
        filtro=filtro,
        min_date=min_date,
        max_date=max_date,
        edit_tarea=tarea,
        edit_id=id
    )

#ELIMINAR
@app.route("/tareas/borrar/<int:id>")
def borrar(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM tareas WHERE id=%s", (id,))
    mysql.connection.commit()
    flash("Tarea eliminada.", "info")
    return redirect(url_for('tareas'))


#EXPORTAR
@app.route('/exportar')
def exportar():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, titulo, descripcion, estado, fecha FROM tareas ORDER BY fecha ASC")
    tareas = cur.fetchall()
    cur.close()
    
    # Crear el contenido del archivo
    contenido = ""
    for tarea in tareas:
        contenido += f"ID: {tarea[0]}\n"
        contenido += f"Título: {tarea[1]}\n"
        contenido += f"Descripción: {tarea[2]}\n"
        contenido += f"Estado: {tarea[3]}\n"
        contenido += f"Fecha de creación: {tarea[4]}\n"
        contenido += "-" * 40 + "\n"

    # Crear un archivo en memoria
    archivo = io.BytesIO()
    archivo.write(contenido.encode('utf-8'))
    archivo.seek(0)

    return send_file(archivo, as_attachment=True, download_name="tareas.txt", mimetype='text/plain')


#CERRAR SESION
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)