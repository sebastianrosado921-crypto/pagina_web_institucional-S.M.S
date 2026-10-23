import os
import re
import secrets
import uuid
import hashlib
import hmac
from functools import wraps
from pathlib import Path
from math import ceil
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from psycopg2.extras import RealDictCursor
from werkzeug.utils import secure_filename

from db import get_connection


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "sms-entrega9-cambiar-en-produccion")

app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

UPLOAD_ROOT = Path(app.root_path) / "static" / "uploads"
UPLOAD_PERSONAL = UPLOAD_ROOT / "personal"
UPLOAD_GALERIA = UPLOAD_ROOT / "galeria"
UPLOAD_NOTICIAS = UPLOAD_ROOT / "noticias"
UPLOAD_VIDEOS = UPLOAD_ROOT / "videos"
UPLOAD_PERSONAL.mkdir(parents=True, exist_ok=True)
UPLOAD_GALERIA.mkdir(parents=True, exist_ok=True)
UPLOAD_NOTICIAS.mkdir(parents=True, exist_ok=True)
UPLOAD_VIDEOS.mkdir(parents=True, exist_ok=True)

EXTENSIONES_IMAGEN = {"png", "jpg", "jpeg", "webp"}
EXTENSIONES_VIDEO = {"mp4", "webm"}

PERMISOS_ROL = {
    "SUPERADMIN": {"*"},
    "RECTORIA": {"general", "personal", "secciones", "noticias", "logros", "galerias", "redes", "mensajes"},
    "EDITOR": {"personal", "secciones", "noticias", "logros", "galerias", "redes"},
    "COMUNICACIONES": {"noticias", "logros", "galerias", "redes", "mensajes"},
}

ROLES_PUBLICADORES = {"SUPERADMIN", "RECTORIA"}
ROLES_EDITORES = {"SUPERADMIN", "RECTORIA", "EDITOR", "COMUNICACIONES"}



NOMBRE_INSTITUCION = "Institución Educativa Distrital Santa Magdalena Sofía"


def obtener_institucion(cur):
    """Obtiene la institución principal, priorizando el nombre configurado."""
    cur.execute("""
        SELECT id_institucion, nombre, mision, vision, descripcion_general
        FROM institucion
        ORDER BY CASE WHEN nombre = %s THEN 0 ELSE 1 END, id_institucion
        LIMIT 1
    """, (NOMBRE_INSTITUCION,))
    return cur.fetchone()



def obtener_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def validar_correo(correo):
    patron = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return bool(re.match(patron, correo or ""))


def crear_hash_clave(clave, salt=None, iteraciones=260000):
    salt = salt or secrets.token_hex(16)
    derivada = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), salt.encode("utf-8"), iteraciones)
    return f"pbkdf2_sha256${iteraciones}${salt}${derivada.hex()}"


def verificar_hash_clave(hash_guardado, clave):
    try:
        algoritmo, iteraciones, salt, esperado = hash_guardado.split("$", 3)
        if algoritmo != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            clave.encode("utf-8"),
            salt.encode("utf-8"),
            int(iteraciones),
        ).hex()
        return hmac.compare_digest(actual, esperado)
    except (ValueError, TypeError, AttributeError):
        return False


def validar_csrf_post():
    token = request.form.get("csrf_token", "")
    return bool(token and token == session.get("csrf_token"))


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Inicia sesión para acceder al panel administrativo.", "danger")
            return redirect(url_for("admin_login", next=request.path))
        return func(*args, **kwargs)
    return wrapper


def permiso_required(permiso):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not session.get("admin_id"):
                return redirect(url_for("admin_login"))
            permisos = PERMISOS_ROL.get(session.get("admin_rol", ""), set())
            if "*" not in permisos and permiso not in permisos:
                flash("Tu rol no tiene permiso para esta acción.", "danger")
                return redirect(url_for("admin_dashboard"))
            return func(*args, **kwargs)
        return wrapper
    return decorator


def extension_imagen_valida(nombre):
    return "." in nombre and nombre.rsplit(".", 1)[1].lower() in EXTENSIONES_IMAGEN


def firma_imagen_valida(archivo):
    posicion = archivo.stream.tell()
    cabecera = archivo.stream.read(16)
    archivo.stream.seek(posicion)
    if cabecera.startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
        return True
    if cabecera.startswith(b"\\xff\\xd8\\xff"):
        return True
    if cabecera.startswith(b"RIFF") and len(cabecera) >= 12 and cabecera[8:12] == b"WEBP":
        return True
    return False


def guardar_imagen(archivo, subcarpeta):
    if not archivo or not archivo.filename:
        return None
    nombre_seguro = secure_filename(archivo.filename)
    if not extension_imagen_valida(nombre_seguro) or not firma_imagen_valida(archivo):
        raise ValueError("Solo se permiten imágenes PNG, JPG, JPEG o WEBP válidas.")
    extension = nombre_seguro.rsplit(".", 1)[1].lower()
    nuevo_nombre = f"{uuid.uuid4().hex}.{extension}"
    destino_dir = UPLOAD_PERSONAL if subcarpeta == "personal" else UPLOAD_GALERIA
    destino_dir.mkdir(parents=True, exist_ok=True)
    archivo.save(destino_dir / nuevo_nombre)
    return f"/static/uploads/{subcarpeta}/{nuevo_nombre}"



def extension_video_valida(nombre):
    return "." in nombre and nombre.rsplit(".", 1)[1].lower() in EXTENSIONES_VIDEO


def firma_video_valida(archivo):
    posicion = archivo.stream.tell()
    cabecera = archivo.stream.read(16)
    archivo.stream.seek(posicion)
    # MP4: box ftyp a partir del byte 4. WEBM: EBML.
    if len(cabecera) >= 12 and cabecera[4:8] == b"ftyp":
        return True
    if cabecera.startswith(b"\x1a\x45\xdf\xa3"):
        return True
    return False


def guardar_video(archivo):
    if not archivo or not archivo.filename:
        return None
    nombre_seguro = secure_filename(archivo.filename)
    if not extension_video_valida(nombre_seguro) or not firma_video_valida(archivo):
        raise ValueError("Solo se permiten videos MP4 o WEBM válidos.")
    extension = nombre_seguro.rsplit(".", 1)[1].lower()
    nuevo_nombre = f"{uuid.uuid4().hex}.{extension}"
    UPLOAD_VIDEOS.mkdir(parents=True, exist_ok=True)
    archivo.save(UPLOAD_VIDEOS / nuevo_nombre)
    return f"/static/uploads/videos/{nuevo_nombre}"


def guardar_imagen_noticia(archivo):
    if not archivo or not archivo.filename:
        return None
    nombre_seguro = secure_filename(archivo.filename)
    if not extension_imagen_valida(nombre_seguro) or not firma_imagen_valida(archivo):
        raise ValueError("Solo se permiten imágenes PNG, JPG, JPEG o WEBP válidas.")
    extension = nombre_seguro.rsplit(".", 1)[1].lower()
    nuevo_nombre = f"{uuid.uuid4().hex}.{extension}"
    UPLOAD_NOTICIAS.mkdir(parents=True, exist_ok=True)
    archivo.save(UPLOAD_NOTICIAS / nuevo_nombre)
    return f"/static/uploads/noticias/{nuevo_nombre}"


def puede_publicar():
    return session.get("admin_rol") in ROLES_PUBLICADORES


def eliminar_archivo_local(url):
    if not url or not url.startswith("/static/uploads/"):
        return
    ruta = Path(app.root_path) / url.lstrip("/")
    try:
        if ruta.exists() and ruta.is_file():
            ruta.unlink()
    except OSError:
        pass


def obtener_institucion_id():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        return institucion["id_institucion"] if institucion else None
    finally:
        cur.close()
        conn.close()



@app.context_processor
def inyectar_csrf():
    def tiene_permiso(permiso):
        rol = session.get("admin_rol", "")
        permisos = PERMISOS_ROL.get(rol, set())
        return "*" in permisos or permiso in permisos

    return {
        "csrf_token": obtener_csrf_token(),
        "tiene_permiso": tiene_permiso,
        "puede_publicar_contenido": puede_publicar(),
    }


def cargar_contexto_publico():
    datos = {
        "institucion_nav": None,
        "contacto_nav": None,
        "nav_secciones": [],
        "redes_nav": [],
    }

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        institucion = obtener_institucion(cur)
        datos["institucion_nav"] = institucion

        if not institucion:
            return datos

        institucion_id = institucion["id_institucion"]

        cur.execute("""
            SELECT telefono, correo, direccion, horario_atencion
            FROM contacto_institucional
            WHERE id_institucion = %s
            LIMIT 1
        """, (institucion_id,))
        datos["contacto_nav"] = cur.fetchone()

        cur.execute("""
            SELECT id_seccion, nombre, descripcion, orden_menu
            FROM seccion
            WHERE id_institucion = %s
              AND visible = TRUE
            ORDER BY orden_menu, nombre
            LIMIT 8
        """, (institucion_id,))
        datos["nav_secciones"] = cur.fetchall()

        cur.execute("""
            SELECT id_red, plataforma, url_enlace, icono
            FROM red_social
            WHERE id_institucion = %s
            ORDER BY id_red
            LIMIT 6
        """, (institucion_id,))
        datos["redes_nav"] = cur.fetchall()

        return datos
    finally:
        cur.close()
        conn.close()


@app.context_processor
def inyectar_contexto_publico():
    try:
        return cargar_contexto_publico()
    except Exception:
        return {
            "institucion_nav": None,
            "contacto_nav": None,
            "nav_secciones": [],
            "redes_nav": [],
        }


def cargar_inicio():
    datos = {
        "institucion": None,
        "contacto": None,
        "secciones": [],
        "noticias": [],
        "destacadas": [],
        "videos_destacados": [],
        "logros": [],
        "carrusel": [],
        "galerias_destacadas": [],
        "metricas": {"noticias": 0, "logros": 0, "galerias": 0, "personal": 0, "secciones": 0, "videos": 0},
    }

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        datos["institucion"] = institucion
        if not institucion:
            return datos

        iid = institucion["id_institucion"]

        cur.execute("""
            SELECT telefono, correo, direccion, horario_atencion
            FROM contacto_institucional WHERE id_institucion=%s LIMIT 1
        """, (iid,))
        datos["contacto"] = cur.fetchone()

        cur.execute("""
            SELECT id_seccion,nombre,descripcion,orden_menu
            FROM seccion
            WHERE id_institucion=%s AND visible=TRUE
            ORDER BY orden_menu,id_seccion
            LIMIT 6
        """, (iid,))
        datos["secciones"] = cur.fetchall()

        cur.execute("""
            SELECT id_noticia,titulo,resumen,contenido,fecha_publicacion,estado,
                   tipo_contenido,imagen_url,video_url,destacada,orden_destacado
            FROM noticia
            WHERE id_institucion=%s AND estado='PUBLICADA'
            ORDER BY fecha_publicacion DESC,id_noticia DESC
            LIMIT 6
        """, (iid,))
        datos["noticias"] = cur.fetchall()

        cur.execute("""
            SELECT id_noticia,titulo,resumen,contenido,fecha_publicacion,estado,
                   tipo_contenido,imagen_url,video_url,destacada,orden_destacado
            FROM noticia
            WHERE id_institucion=%s AND estado='PUBLICADA' AND COALESCE(destacada,FALSE)=TRUE
            ORDER BY COALESCE(orden_destacado,999),fecha_publicacion DESC,id_noticia DESC
            LIMIT 4
        """, (iid,))
        destacadas = cur.fetchall()
        if not destacadas:
            destacadas = datos["noticias"][:4]
        datos["destacadas"] = destacadas

        cur.execute("""
            SELECT id_noticia,titulo,resumen,fecha_publicacion,tipo_contenido,
                   imagen_url,video_url
            FROM noticia
            WHERE id_institucion=%s AND estado='PUBLICADA' AND video_url IS NOT NULL
            ORDER BY COALESCE(destacada,FALSE) DESC,fecha_publicacion DESC,id_noticia DESC
            LIMIT 3
        """, (iid,))
        datos["videos_destacados"] = cur.fetchall()

        cur.execute("""
            SELECT id_logro,titulo,descripcion,fecha_logro,categoria
            FROM logro WHERE id_institucion=%s
            ORDER BY fecha_logro DESC NULLS LAST,id_logro DESC LIMIT 3
        """, (iid,))
        datos["logros"] = cur.fetchall()

        cur.execute("""
            SELECT ig.id_imagen,ig.url_imagen,ig.pie_foto,ig.fecha_carga,
                   g.id_galeria,g.nombre AS galeria_nombre,g.descripcion AS galeria_descripcion,g.tipo AS galeria_tipo
            FROM imagen_galeria ig
            JOIN galeria g ON g.id_galeria=ig.id_galeria
            WHERE g.id_institucion=%s
            ORDER BY ig.fecha_carga DESC,ig.id_imagen DESC
            LIMIT 4
        """, (iid,))
        datos["carrusel"] = cur.fetchall()

        cur.execute("""
            SELECT g.id_galeria,g.nombre,g.descripcion,g.tipo,
                   COUNT(ig.id_imagen) AS total_imagenes,MIN(ig.url_imagen) AS portada
            FROM galeria g
            LEFT JOIN imagen_galeria ig ON ig.id_galeria=g.id_galeria
            WHERE g.id_institucion=%s
            GROUP BY g.id_galeria,g.nombre,g.descripcion,g.tipo
            ORDER BY g.id_galeria DESC LIMIT 3
        """, (iid,))
        datos["galerias_destacadas"] = cur.fetchall()

        cur.execute("SELECT COUNT(*) total FROM noticia WHERE id_institucion=%s AND estado='PUBLICADA'", (iid,))
        datos["metricas"]["noticias"] = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) total FROM logro WHERE id_institucion=%s", (iid,))
        datos["metricas"]["logros"] = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) total FROM galeria WHERE id_institucion=%s", (iid,))
        datos["metricas"]["galerias"] = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) total FROM seccion WHERE id_institucion=%s AND visible=TRUE", (iid,))
        datos["metricas"]["secciones"] = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) total FROM noticia WHERE id_institucion=%s AND estado='PUBLICADA' AND video_url IS NOT NULL", (iid,))
        datos["metricas"]["videos"] = cur.fetchone()["total"]
        cur.execute("""
            SELECT (SELECT COUNT(*) FROM docente WHERE id_institucion=%s AND COALESCE(visible,TRUE)=TRUE)
                 + (SELECT COUNT(*) FROM administrativo WHERE id_institucion=%s AND COALESCE(visible,TRUE)=TRUE) AS total
        """, (iid, iid))
        datos["metricas"]["personal"] = cur.fetchone()["total"]
        return datos
    finally:
        cur.close()
        conn.close()


@app.route("/")
def inicio():
    try:
        datos = cargar_inicio()
        return render_template("index.html", db_error=False, **datos)
    except Exception as exc:
        return render_template(
            "index.html",
            db_error=True,
            error_tecnico=str(exc),
            institucion=None,
            contacto=None,
            secciones=[],
            noticias=[],
            destacadas=[],
            videos_destacados=[],
            logros=[],
            carrusel=[],
            galerias_destacadas=[],
            metricas={"noticias":0,"logros":0,"galerias":0,"personal":0,"secciones":0,"videos":0},
        ), 503

@app.route("/calendario")
def calendario():
    """Muestra el calendario escolar con filtros por tipo y mes."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        if not institucion:
            return render_template("calendario.html", institucion=None, eventos=[], tipos=[], filtro_tipo=None, mes_seleccionado=None)

        iid = institucion["id_institucion"]

        # Filtros por URL
        filtro_tipo = request.args.get("tipo", "").strip().upper() or None
        filtro_mes = request.args.get("mes", "").strip() or None

        # Tipos disponibles para el filtro
        cur.execute("""
            SELECT DISTINCT tipo_evento FROM evento_calendario
            WHERE id_institucion = %s AND visible_publico = TRUE
            ORDER BY tipo_evento
        """, (iid,))
        tipos_disponibles = [r["tipo_evento"] for r in cur.fetchall()]

        # Construir consulta base
        sql = """
            SELECT id_evento, titulo, descripcion, fecha_inicio, fecha_fin,
                   hora_inicio, hora_fin, tipo_evento, ubicacion, responsable,
                   es_dia_no_laboral, color_etiqueta
            FROM evento_calendario
            WHERE id_institucion = %s AND visible_publico = TRUE
        """
        params = [iid]

        if filtro_tipo and filtro_tipo in tipos_disponibles:
            sql += " AND tipo_evento = %s"
            params.append(filtro_tipo)

        if filtro_mes:
            try:
                anio, mes = filtro_mes.split("-")
                sql += " AND EXTRACT(YEAR FROM fecha_inicio) = %s AND EXTRACT(MONTH FROM fecha_inicio) = %s"
                params.extend([int(anio), int(mes)])
            except ValueError:
                filtro_mes = None

        sql += " ORDER BY fecha_inicio ASC, hora_inicio ASC NULLS LAST"

        cur.execute(sql, params)
        eventos = cur.fetchall()

        # Mes actual por defecto para el selector
        hoy = date.today()
        mes_actual = f"{hoy.year}-{hoy.month:02d}"

        return render_template(
            "calendario.html",
            institucion=institucion,
            eventos=eventos,
            tipos=tipos_disponibles,
            filtro_tipo=filtro_tipo,
            mes_seleccionado=filtro_mes or mes_actual,
            mes_actual=mes_actual,
        )
    finally:
        cur.close()
        conn.close()


# ----------------------------------------------------------------------------
# PREGUNTAS FRECUENTES (FAQ) · ruta pública
# ----------------------------------------------------------------------------
@app.route("/faq")
def faq():
    """Muestra preguntas frecuentes organizadas por categoría."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        if not institucion:
            return render_template("faq.html", institucion=None, categorias={}, total=0)

        iid = institucion["id_institucion"]

        cur.execute("""
            SELECT id_faq, categoria, pregunta, respuesta, orden_visual
            FROM faq_institucional
            WHERE id_institucion = %s AND visible = TRUE
            ORDER BY categoria, orden_visual, id_faq
        """, (iid,))
        filas = cur.fetchall()

        # Agrupar por categoría
        categorias = {}
        for f in filas:
            cat = f["categoria"]
            if cat not in categorias:
                categorias[cat] = []
            categorias[cat].append(f)

        return render_template(
            "faq.html",
            institucion=institucion,
            categorias=categorias,
            total=len(filas),
        )
    finally:
        cur.close()
        conn.close()


# ============================================================================
# FIN DEL BLOQUE PARA AGREGAR EN app.py
# ============================================================================

def cargar_pagina_institucional():
    datos = {
        "institucion": None,
        "contacto": None,
        "secciones_institucionales": [],
        "secciones_por_nombre": {},
        "metricas": {
            "secciones": 0,
            "noticias": 0,
            "logros": 0,
            "galerias": 0,
        },
    }

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        institucion = obtener_institucion(cur)
        datos["institucion"] = institucion

        if not institucion:
            return datos

        institucion_id = institucion["id_institucion"]

        cur.execute("""
            SELECT telefono, correo, direccion, horario_atencion
            FROM contacto_institucional
            WHERE id_institucion = %s
            LIMIT 1
        """, (institucion_id,))
        datos["contacto"] = cur.fetchone()

        cur.execute("""
            SELECT id_seccion, nombre, descripcion, orden_menu
            FROM seccion
            WHERE id_institucion = %s
              AND visible = TRUE
            ORDER BY orden_menu, nombre
        """, (institucion_id,))
        secciones = cur.fetchall()
        datos["secciones_institucionales"] = secciones
        datos["secciones_por_nombre"] = {
            item["nombre"]: item for item in secciones
        }

        consultas = {
            "secciones": """
                SELECT COUNT(*) AS total
                FROM seccion
                WHERE id_institucion = %s AND visible = TRUE
            """,
            "noticias": """
                SELECT COUNT(*) AS total
                FROM noticia
                WHERE id_institucion = %s AND estado = 'PUBLICADA'
            """,
            "logros": """
                SELECT COUNT(*) AS total
                FROM logro
                WHERE id_institucion = %s
            """,
            "galerias": """
                SELECT COUNT(*) AS total
                FROM galeria
                WHERE id_institucion = %s
            """,
        }

        for clave, sql in consultas.items():
            cur.execute(sql, (institucion_id,))
            datos["metricas"][clave] = cur.fetchone()["total"]

        return datos
    finally:
        cur.close()
        conn.close()


@app.route("/institucion")
def institucion():
    try:
        datos = cargar_pagina_institucional()
        return render_template(
            "institucion.html",
            db_error=False,
            **datos,
        )
    except Exception as exc:
        return render_template(
            "institucion.html",
            db_error=True,
            error_tecnico=str(exc),
            institucion=None,
            contacto=None,
            secciones_institucionales=[],
            secciones_por_nombre={},
            metricas={
                "secciones": 0,
                "noticias": 0,
                "logros": 0,
                "galerias": 0,
            },
        ), 503


@app.route("/secciones")
def secciones():
    termino = request.args.get("q", "").strip()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        institucion = obtener_institucion(cur)

        if not institucion:
            return render_template(
                "secciones.html",
                institucion=None,
                secciones=[],
                termino=termino,
                total=0,
            )

        params = [institucion["id_institucion"]]
        filtro = ""

        if termino:
            filtro = """
                AND (
                    nombre ILIKE %s
                    OR COALESCE(descripcion, '') ILIKE %s
                )
            """
            patron = f"%{termino}%"
            params.extend([patron, patron])

        cur.execute(f"""
            SELECT id_seccion, nombre, descripcion, orden_menu, visible
            FROM seccion
            WHERE id_institucion = %s
              AND visible = TRUE
              {filtro}
            ORDER BY orden_menu, nombre
        """, params)

        registros = cur.fetchall()

        return render_template(
            "secciones.html",
            institucion=institucion,
            secciones=registros,
            termino=termino,
            total=len(registros),
        )
    finally:
        cur.close()
        conn.close()


@app.route("/seccion/<int:id_seccion>")
def detalle_seccion(id_seccion):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        institucion = obtener_institucion(cur)

        if not institucion:
            return render_template("404.html"), 404

        institucion_id = institucion["id_institucion"]

        cur.execute("""
            SELECT id_seccion, nombre, descripcion, orden_menu
            FROM seccion
            WHERE id_seccion = %s
              AND id_institucion = %s
              AND visible = TRUE
        """, (id_seccion, institucion_id))
        seccion = cur.fetchone()

        if not seccion:
            return render_template("404.html"), 404

        cur.execute("""
            SELECT id_seccion, nombre, descripcion, orden_menu
            FROM seccion
            WHERE id_institucion = %s
              AND visible = TRUE
            ORDER BY orden_menu, id_seccion
        """, (institucion_id,))
        todas = cur.fetchall()

        anterior = None
        siguiente = None

        for indice, item in enumerate(todas):
            if item["id_seccion"] == id_seccion:
                if indice > 0:
                    anterior = todas[indice - 1]

                if indice < len(todas) - 1:
                    siguiente = todas[indice + 1]

                break

        return render_template(
            "seccion_detalle.html",
            institucion=institucion,
            seccion=seccion,
            todas=todas,
            anterior=anterior,
            siguiente=siguiente,
        )
    finally:
        cur.close()
        conn.close()


@app.route("/noticias")
def noticias():
    termino = request.args.get("q", "").strip()
    tipo = request.args.get("tipo", "").strip().upper()
    pagina = max(request.args.get("page", 1, type=int), 1)
    por_pagina = 9

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        if not institucion:
            return render_template("noticias.html", institucion=None, noticias=[], destacada=None,
                                   termino=termino, tipo=tipo, pagina=1, paginas=0, total=0)

        iid = institucion["id_institucion"]
        filtros = ["id_institucion=%s", "estado='PUBLICADA'"]
        params = [iid]

        if termino:
            patron = f"%{termino}%"
            filtros.append("(titulo ILIKE %s OR resumen ILIKE %s OR COALESCE(contenido,'') ILIKE %s)")
            params.extend([patron, patron, patron])
        if tipo in {"NOTICIA", "EVENTO", "COMUNICADO"}:
            filtros.append("tipo_contenido=%s")
            params.append(tipo)

        where = " AND ".join(filtros)
        cur.execute(f"SELECT COUNT(*) AS total FROM noticia WHERE {where}", params)
        total = cur.fetchone()["total"]
        paginas = ceil(total / por_pagina) if total else 0
        if paginas and pagina > paginas:
            pagina = paginas
        offset = (pagina - 1) * por_pagina

        cur.execute(f"""
            SELECT id_noticia,titulo,resumen,contenido,fecha_publicacion,estado,
                   tipo_contenido,imagen_url,video_url,destacada
            FROM noticia WHERE {where}
            ORDER BY COALESCE(destacada,FALSE) DESC,fecha_publicacion DESC,id_noticia DESC
            LIMIT %s OFFSET %s
        """, params + [por_pagina, offset])
        registros = cur.fetchall()

        cur.execute("""
            SELECT id_noticia,titulo,resumen,contenido,fecha_publicacion,
                   tipo_contenido,imagen_url,video_url,destacada
            FROM noticia
            WHERE id_institucion=%s AND estado='PUBLICADA'
            ORDER BY COALESCE(destacada,FALSE) DESC,COALESCE(orden_destacado,999),fecha_publicacion DESC,id_noticia DESC
            LIMIT 1
        """, (iid,))
        destacada = cur.fetchone()

        return render_template("noticias.html", institucion=institucion, noticias=registros,
                               destacada=destacada, termino=termino, tipo=tipo,
                               pagina=pagina, paginas=paginas, total=total)
    finally:
        cur.close()
        conn.close()


@app.route("/noticia/<int:id_noticia>")
def detalle_noticia(id_noticia):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        if not institucion:
            return render_template("404.html"), 404
        iid = institucion["id_institucion"]

        cur.execute("""
            SELECT id_noticia,titulo,resumen,contenido,fecha_publicacion,estado,
                   tipo_contenido,imagen_url,video_url,destacada
            FROM noticia
            WHERE id_noticia=%s AND id_institucion=%s AND estado='PUBLICADA'
        """, (id_noticia, iid))
        noticia = cur.fetchone()
        if not noticia:
            return render_template("404.html"), 404

        cur.execute("""
            SELECT id_noticia,titulo,fecha_publicacion FROM noticia
            WHERE id_institucion=%s AND estado='PUBLICADA'
              AND (fecha_publicacion < %s OR (fecha_publicacion=%s AND id_noticia < %s))
            ORDER BY fecha_publicacion DESC,id_noticia DESC LIMIT 1
        """, (iid, noticia["fecha_publicacion"], noticia["fecha_publicacion"], id_noticia))
        anterior = cur.fetchone()

        cur.execute("""
            SELECT id_noticia,titulo,fecha_publicacion FROM noticia
            WHERE id_institucion=%s AND estado='PUBLICADA'
              AND (fecha_publicacion > %s OR (fecha_publicacion=%s AND id_noticia > %s))
            ORDER BY fecha_publicacion ASC,id_noticia ASC LIMIT 1
        """, (iid, noticia["fecha_publicacion"], noticia["fecha_publicacion"], id_noticia))
        siguiente = cur.fetchone()

        cur.execute("""
            SELECT id_noticia,titulo,resumen,fecha_publicacion,tipo_contenido,imagen_url,video_url
            FROM noticia
            WHERE id_institucion=%s AND estado='PUBLICADA' AND id_noticia<>%s
            ORDER BY fecha_publicacion DESC,id_noticia DESC LIMIT 3
        """, (iid, id_noticia))
        relacionadas = cur.fetchall()

        return render_template("noticia_detalle.html", institucion=institucion, noticia=noticia,
                               anterior=anterior, siguiente=siguiente, relacionadas=relacionadas)
    finally:
        cur.close()
        conn.close()


@app.route("/videos")
def videos():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        if not institucion:
            return render_template("videos.html", institucion=None, videos=[])
        cur.execute("""
            SELECT id_noticia,titulo,resumen,fecha_publicacion,tipo_contenido,imagen_url,video_url
            FROM noticia
            WHERE id_institucion=%s AND estado='PUBLICADA' AND video_url IS NOT NULL
            ORDER BY fecha_publicacion DESC,id_noticia DESC
        """, (institucion["id_institucion"],))
        return render_template("videos.html", institucion=institucion, videos=cur.fetchall())
    finally:
        cur.close()
        conn.close()


@app.route("/logros")
def logros():
    termino = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip()
    pagina = max(request.args.get("page", 1, type=int), 1)
    por_pagina = 6

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        institucion = obtener_institucion(cur)

        if not institucion:
            return render_template(
                "logros.html",
                institucion=None,
                logros=[],
                destacado=None,
                categorias=[],
                termino=termino,
                categoria=categoria,
                pagina=1,
                paginas=0,
                total=0,
            )

        institucion_id = institucion["id_institucion"]

        cur.execute("""
            SELECT DISTINCT categoria
            FROM logro
            WHERE id_institucion = %s
              AND categoria IS NOT NULL
              AND TRIM(categoria) <> ''
            ORDER BY categoria
        """, (institucion_id,))
        categorias = [fila["categoria"] for fila in cur.fetchall()]

        condiciones = ["id_institucion = %s"]
        params = [institucion_id]

        if termino:
            patron = f"%{termino}%"
            condiciones.append("(titulo ILIKE %s OR descripcion ILIKE %s OR COALESCE(categoria, '') ILIKE %s)")
            params.extend([patron, patron, patron])

        if categoria:
            condiciones.append("categoria = %s")
            params.append(categoria)

        where_sql = " AND ".join(condiciones)

        cur.execute(f"""
            SELECT COUNT(*) AS total
            FROM logro
            WHERE {where_sql}
        """, params)
        total = cur.fetchone()["total"]

        paginas = ceil(total / por_pagina) if total else 0
        if paginas and pagina > paginas:
            pagina = paginas

        offset = (pagina - 1) * por_pagina

        cur.execute(f"""
            SELECT id_logro, titulo, descripcion, fecha_logro, categoria
            FROM logro
            WHERE {where_sql}
            ORDER BY fecha_logro DESC NULLS LAST, id_logro DESC
            LIMIT %s OFFSET %s
        """, params + [por_pagina, offset])
        registros = cur.fetchall()

        cur.execute("""
            SELECT id_logro, titulo, descripcion, fecha_logro, categoria
            FROM logro
            WHERE id_institucion = %s
            ORDER BY fecha_logro DESC NULLS LAST, id_logro DESC
            LIMIT 1
        """, (institucion_id,))
        destacado = cur.fetchone()

        return render_template(
            "logros.html",
            institucion=institucion,
            logros=registros,
            destacado=destacado,
            categorias=categorias,
            termino=termino,
            categoria=categoria,
            pagina=pagina,
            paginas=paginas,
            total=total,
        )
    finally:
        cur.close()
        conn.close()


@app.route("/logro/<int:id_logro>")
def detalle_logro(id_logro):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        institucion = obtener_institucion(cur)

        if not institucion:
            return render_template("404.html"), 404

        institucion_id = institucion["id_institucion"]

        cur.execute("""
            SELECT id_logro, titulo, descripcion, fecha_logro, categoria
            FROM logro
            WHERE id_logro = %s
              AND id_institucion = %s
        """, (id_logro, institucion_id))
        logro = cur.fetchone()

        if not logro:
            return render_template("404.html"), 404

        cur.execute("""
            SELECT id_logro, titulo, descripcion, fecha_logro, categoria
            FROM logro
            WHERE id_institucion = %s
              AND id_logro <> %s
              AND (
                    categoria = %s
                    OR %s IS NULL
              )
            ORDER BY fecha_logro DESC NULLS LAST, id_logro DESC
            LIMIT 3
        """, (
            institucion_id,
            id_logro,
            logro["categoria"],
            logro["categoria"],
        ))
        relacionados = cur.fetchall()

        if len(relacionados) < 3:
            ids = [item["id_logro"] for item in relacionados] + [id_logro]
            placeholders = ",".join(["%s"] * len(ids))
            cur.execute(f"""
                SELECT id_logro, titulo, descripcion, fecha_logro, categoria
                FROM logro
                WHERE id_institucion = %s
                  AND id_logro NOT IN ({placeholders})
                ORDER BY fecha_logro DESC NULLS LAST, id_logro DESC
                LIMIT %s
            """, [institucion_id] + ids + [3 - len(relacionados)])
            relacionados.extend(cur.fetchall())

        cur.execute("""
            SELECT id_logro, titulo
            FROM logro
            WHERE id_institucion = %s
              AND id_logro < %s
            ORDER BY id_logro DESC
            LIMIT 1
        """, (institucion_id, id_logro))
        anterior = cur.fetchone()

        cur.execute("""
            SELECT id_logro, titulo
            FROM logro
            WHERE id_institucion = %s
              AND id_logro > %s
            ORDER BY id_logro ASC
            LIMIT 1
        """, (institucion_id, id_logro))
        siguiente = cur.fetchone()

        return render_template(
            "logro_detalle.html",
            institucion=institucion,
            logro=logro,
            relacionados=relacionados,
            anterior=anterior,
            siguiente=siguiente,
        )
    finally:
        cur.close()
        conn.close()




@app.route("/galerias")
def galerias():
    tipo = request.args.get("tipo", "").strip()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        institucion = obtener_institucion(cur)

        if not institucion:
            return render_template(
                "galerias.html",
                institucion=None,
                galerias=[],
                tipos=[],
                tipo=tipo,
                total=0,
            )

        institucion_id = institucion["id_institucion"]

        cur.execute("""
            SELECT DISTINCT tipo
            FROM galeria
            WHERE id_institucion = %s
              AND tipo IS NOT NULL
              AND TRIM(tipo) <> ''
            ORDER BY tipo
        """, (institucion_id,))
        tipos = [fila["tipo"] for fila in cur.fetchall()]

        params = [institucion_id]
        filtro = ""
        if tipo:
            filtro = " AND g.tipo = %s"
            params.append(tipo)

        cur.execute(f"""
            SELECT
                g.id_galeria,
                g.nombre,
                g.descripcion,
                g.tipo,
                COUNT(ig.id_imagen) AS total_imagenes,
                MIN(ig.url_imagen) AS portada,
                MAX(ig.fecha_carga) AS ultima_actualizacion
            FROM galeria g
            LEFT JOIN imagen_galeria ig ON ig.id_galeria = g.id_galeria
            WHERE g.id_institucion = %s
              {filtro}
            GROUP BY g.id_galeria, g.nombre, g.descripcion, g.tipo
            ORDER BY ultima_actualizacion DESC NULLS LAST, g.id_galeria DESC
        """, params)
        registros = cur.fetchall()

        return render_template(
            "galerias.html",
            institucion=institucion,
            galerias=registros,
            tipos=tipos,
            tipo=tipo,
            total=len(registros),
        )
    finally:
        cur.close()
        conn.close()


@app.route("/galeria/<int:id_galeria>")
def detalle_galeria(id_galeria):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        institucion = obtener_institucion(cur)

        if not institucion:
            return render_template("404.html"), 404

        institucion_id = institucion["id_institucion"]

        cur.execute("""
            SELECT id_galeria, nombre, descripcion, tipo
            FROM galeria
            WHERE id_galeria = %s
              AND id_institucion = %s
        """, (id_galeria, institucion_id))
        galeria = cur.fetchone()

        if not galeria:
            return render_template("404.html"), 404

        cur.execute("""
            SELECT id_imagen, url_imagen, pie_foto, fecha_carga
            FROM imagen_galeria
            WHERE id_galeria = %s
            ORDER BY fecha_carga DESC, id_imagen DESC
        """, (id_galeria,))
        imagenes = cur.fetchall()

        cur.execute("""
            SELECT
                g.id_galeria,
                g.nombre,
                g.tipo,
                MIN(ig.url_imagen) AS portada
            FROM galeria g
            LEFT JOIN imagen_galeria ig ON ig.id_galeria = g.id_galeria
            WHERE g.id_institucion = %s
              AND g.id_galeria <> %s
            GROUP BY g.id_galeria, g.nombre, g.tipo
            ORDER BY g.id_galeria DESC
            LIMIT 3
        """, (institucion_id, id_galeria))
        relacionadas = cur.fetchall()

        return render_template(
            "galeria_detalle.html",
            institucion=institucion,
            galeria=galeria,
            imagenes=imagenes,
            relacionadas=relacionadas,
        )
    finally:
        cur.close()
        conn.close()


@app.route("/imagen/<int:id_imagen>")
def detalle_imagen(id_imagen):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        institucion = obtener_institucion(cur)

        if not institucion:
            return render_template("404.html"), 404

        cur.execute("""
            SELECT
                ig.id_imagen,
                ig.url_imagen,
                ig.pie_foto,
                ig.fecha_carga,
                g.id_galeria,
                g.nombre AS galeria_nombre,
                g.descripcion AS galeria_descripcion,
                g.tipo AS galeria_tipo
            FROM imagen_galeria ig
            JOIN galeria g ON g.id_galeria = ig.id_galeria
            WHERE ig.id_imagen = %s
              AND g.id_institucion = %s
        """, (id_imagen, institucion["id_institucion"]))
        imagen = cur.fetchone()

        if not imagen:
            return render_template("404.html"), 404

        cur.execute("""
            SELECT id_imagen, url_imagen, pie_foto, fecha_carga
            FROM imagen_galeria
            WHERE id_galeria = %s
              AND id_imagen <> %s
            ORDER BY fecha_carga DESC, id_imagen DESC
            LIMIT 4
        """, (imagen["id_galeria"], id_imagen))
        relacionadas = cur.fetchall()

        return render_template(
            "imagen_detalle.html",
            institucion=institucion,
            imagen=imagen,
            relacionadas=relacionadas,
        )
    finally:
        cur.close()
        conn.close()








@app.route("/equipo")
def equipo():
    area = request.args.get("area", "").strip()
    q = request.args.get("q", "").strip()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        if not institucion:
            return render_template(
                "equipo.html",
                institucion=None, rectoria=[], coordinaciones=[], docentes=[],
                areas=[], area=area, q=q,
                metricas={"docentes": 0, "areas": 0, "directivos": 0},
            )

        iid = institucion["id_institucion"]

        cur.execute("""
            SELECT id_administrativo, nombres, apellidos, cargo, correo,
                   dependencia, foto_url, biografia, formacion, orden_visual
            FROM administrativo
            WHERE id_institucion = %s
              AND COALESCE(visible, TRUE) = TRUE
              AND (UPPER(cargo) LIKE '%%RECTOR%%'
                   OR UPPER(COALESCE(dependencia,'')) LIKE '%%RECTOR%%')
            ORDER BY orden_visual, id_administrativo
        """, (iid,))
        rectoria = cur.fetchall()

        cur.execute("""
            SELECT id_administrativo, nombres, apellidos, cargo, correo,
                   dependencia, foto_url, biografia, formacion, orden_visual
            FROM administrativo
            WHERE id_institucion = %s
              AND COALESCE(visible, TRUE) = TRUE
              AND (UPPER(cargo) LIKE '%%COORDIN%%'
                   OR UPPER(COALESCE(dependencia,'')) LIKE '%%COORDIN%%')
            ORDER BY orden_visual, id_administrativo
        """, (iid,))
        coordinaciones = cur.fetchall()

        filtros = ["id_institucion = %s", "COALESCE(visible, TRUE) = TRUE"]
        params = [iid]
        if area:
            filtros.append("COALESCE(area, cargo) = %s")
            params.append(area)
        if q:
            patron = f"%{q}%"
            filtros.append("""
                (nombres ILIKE %s OR apellidos ILIKE %s OR cargo ILIKE %s
                 OR COALESCE(area,'') ILIKE %s OR COALESCE(biografia,'') ILIKE %s)
            """)
            params.extend([patron, patron, patron, patron, patron])

        cur.execute(f"""
            SELECT id_docente, nombres, apellidos, cargo, correo, area,
                   foto_url, biografia, formacion, anios_experiencia, orden_visual
            FROM docente
            WHERE {" AND ".join(filtros)}
            ORDER BY orden_visual, apellidos, nombres
        """, params)
        docentes = cur.fetchall()

        cur.execute("""
            SELECT DISTINCT COALESCE(area, cargo) AS area
            FROM docente
            WHERE id_institucion = %s
              AND COALESCE(visible, TRUE)=TRUE
              AND COALESCE(area, cargo) IS NOT NULL
            ORDER BY area
        """, (iid,))
        areas = [fila["area"] for fila in cur.fetchall()]

        cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM docente WHERE id_institucion=%s AND COALESCE(visible,TRUE)=TRUE) AS docentes,
                (SELECT COUNT(DISTINCT COALESCE(area,cargo)) FROM docente WHERE id_institucion=%s AND COALESCE(visible,TRUE)=TRUE) AS areas,
                (SELECT COUNT(*) FROM administrativo
                 WHERE id_institucion=%s AND COALESCE(visible,TRUE)=TRUE
                   AND (UPPER(cargo) LIKE '%%RECTOR%%' OR UPPER(cargo) LIKE '%%COORDIN%%'
                        OR UPPER(COALESCE(dependencia,'')) LIKE '%%RECTOR%%'
                        OR UPPER(COALESCE(dependencia,'')) LIKE '%%COORDIN%%')) AS directivos
        """, (iid, iid, iid))
        metricas = cur.fetchone()

        return render_template(
            "equipo.html", institucion=institucion, rectoria=rectoria,
            coordinaciones=coordinaciones, docentes=docentes, areas=areas,
            area=area, q=q, metricas=metricas,
        )
    finally:
        cur.close()
        conn.close()


@app.route("/equipo/docente/<int:id_docente>")
def perfil_docente(id_docente):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        if not institucion:
            return render_template("404.html"), 404
        cur.execute("""
            SELECT id_docente AS id, nombres, apellidos, cargo, correo, area,
                   foto_url, biografia, formacion, anios_experiencia,
                   'DOCENTE' AS tipo
            FROM docente
            WHERE id_docente=%s AND id_institucion=%s AND COALESCE(visible,TRUE)=TRUE
        """, (id_docente, institucion["id_institucion"]))
        persona = cur.fetchone()
        if not persona:
            return render_template("404.html"), 404
        return render_template("perfil_personal.html", institucion=institucion, persona=persona)
    finally:
        cur.close()
        conn.close()


@app.route("/equipo/directivo/<int:id_administrativo>")
def perfil_directivo(id_administrativo):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        if not institucion:
            return render_template("404.html"), 404
        cur.execute("""
            SELECT id_administrativo AS id, nombres, apellidos, cargo, correo,
                   dependencia AS area, foto_url, biografia, formacion,
                   NULL::INTEGER AS anios_experiencia, 'DIRECTIVO' AS tipo
            FROM administrativo
            WHERE id_administrativo=%s AND id_institucion=%s AND COALESCE(visible,TRUE)=TRUE
        """, (id_administrativo, institucion["id_institucion"]))
        persona = cur.fetchone()
        if not persona:
            return render_template("404.html"), 404
        return render_template("perfil_personal.html", institucion=institucion, persona=persona)
    finally:
        cur.close()
        conn.close()


@app.route("/contacto", methods=["GET", "POST"])
def contacto():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        institucion = obtener_institucion(cur)

        if not institucion:
            return render_template(
                "contacto.html",
                institucion=None,
                contacto=None,
                redes=[],
            )

        institucion_id = institucion["id_institucion"]

        cur.execute("""
            SELECT telefono, correo, direccion, horario_atencion
            FROM contacto_institucional
            WHERE id_institucion = %s
            LIMIT 1
        """, (institucion_id,))
        contacto_inst = cur.fetchone()

        cur.execute("""
            SELECT id_red, plataforma, url_enlace, icono
            FROM red_social
            WHERE id_institucion = %s
            ORDER BY id_red
        """, (institucion_id,))
        redes = cur.fetchall()

        if request.method == "POST":
            token = request.form.get("csrf_token", "")
            honeypot = request.form.get("website", "")

            if honeypot:
                flash("No fue posible procesar el formulario.", "danger")
                return redirect(url_for("contacto"))

            if not token or token != session.get("csrf_token"):
                flash("La sesión del formulario expiró. Intenta nuevamente.", "danger")
                return redirect(url_for("contacto"))

            nombre = request.form.get("nombre", "").strip()
            correo = request.form.get("correo", "").strip().lower()
            asunto = request.form.get("asunto", "").strip()
            mensaje = request.form.get("mensaje", "").strip()

            errores = []

            if len(nombre) < 3 or len(nombre) > 150:
                errores.append("Ingresa un nombre válido de 3 a 150 caracteres.")

            if not validar_correo(correo) or len(correo) > 150:
                errores.append("Ingresa un correo electrónico válido.")

            if len(asunto) < 4 or len(asunto) > 200:
                errores.append("El asunto debe tener entre 4 y 200 caracteres.")

            if len(mensaje) < 10 or len(mensaje) > 3000:
                errores.append("El mensaje debe tener entre 10 y 3000 caracteres.")

            if errores:
                for error in errores:
                    flash(error, "danger")

                return render_template(
                    "contacto.html",
                    institucion=institucion,
                    contacto=contacto_inst,
                    redes=redes,
                    form_data={
                        "nombre": nombre,
                        "correo": correo,
                        "asunto": asunto,
                        "mensaje": mensaje,
                    },
                ), 400

            cur.execute("""
                INSERT INTO mensaje_contacto (
                    id_institucion,
                    nombre_remitente,
                    correo_remitente,
                    asunto,
                    mensaje,
                    fecha_envio,
                    estado
                )
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 'PENDIENTE')
            """, (
                institucion_id,
                nombre,
                correo,
                asunto,
                mensaje,
            ))
            conn.commit()

            session["csrf_token"] = secrets.token_urlsafe(32)
            flash("Tu mensaje fue enviado correctamente. Gracias por contactar a la institución.", "success")
            return redirect(url_for("contacto", enviado="1"))

        return render_template(
            "contacto.html",
            institucion=institucion,
            contacto=contacto_inst,
            redes=redes,
            form_data={},
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@app.route("/redes")
def redes():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        institucion = obtener_institucion(cur)

        if not institucion:
            return render_template(
                "redes.html",
                institucion=None,
                redes=[],
                contacto=None,
            )

        institucion_id = institucion["id_institucion"]

        cur.execute("""
            SELECT id_red, plataforma, url_enlace, icono
            FROM red_social
            WHERE id_institucion = %s
            ORDER BY id_red
        """, (institucion_id,))
        redes = cur.fetchall()

        cur.execute("""
            SELECT telefono, correo, direccion, horario_atencion
            FROM contacto_institucional
            WHERE id_institucion = %s
            LIMIT 1
        """, (institucion_id,))
        contacto = cur.fetchone()

        return render_template(
            "redes.html",
            institucion=institucion,
            redes=redes,
            contacto=contacto,
        )
    finally:
        cur.close()
        conn.close()


@app.route("/buscar")
def buscar():
    termino = request.args.get("q", "").strip()
    resultados = []

    if len(termino) < 2:
        return render_template(
            "buscar.html",
            termino=termino,
            resultados=resultados,
            mensaje="Escribe al menos 2 caracteres.",
        )

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        institucion = obtener_institucion(cur)

        if not institucion:
            return render_template(
                "buscar.html",
                termino=termino,
                resultados=[],
                mensaje="No hay información institucional cargada.",
            )

        patron = f"%{termino}%"
        institucion_id = institucion["id_institucion"]

        cur.execute("""
            SELECT
                'seccion' AS tipo,
                id_seccion AS id,
                nombre AS titulo,
                COALESCE(descripcion, '') AS descripcion,
                orden_menu AS orden
            FROM seccion
            WHERE id_institucion = %s
              AND visible = TRUE
              AND (
                    nombre ILIKE %s
                    OR COALESCE(descripcion, '') ILIKE %s
              )

            UNION ALL

            SELECT
                'noticia' AS tipo,
                id_noticia AS id,
                titulo,
                resumen AS descripcion,
                1000 AS orden
            FROM noticia
            WHERE id_institucion = %s
              AND estado = 'PUBLICADA'
              AND (
                    titulo ILIKE %s
                    OR resumen ILIKE %s
              )

            UNION ALL

            SELECT
                'logro' AS tipo,
                id_logro AS id,
                titulo,
                descripcion,
                2000 AS orden
            FROM logro
            WHERE id_institucion = %s
              AND (
                    titulo ILIKE %s
                    OR descripcion ILIKE %s
              )

            ORDER BY orden, titulo
            LIMIT 30
        """, (
            institucion_id,
            patron,
            patron,
            institucion_id,
            patron,
            patron,
            institucion_id,
            patron,
            patron,
        ))

        resultados = cur.fetchall()

        return render_template(
            "buscar.html",
            termino=termino,
            resultados=resultados,
            mensaje=None,
        )
    finally:
        cur.close()
        conn.close()


@app.route("/mapa-del-sitio")
def mapa_sitio():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        institucion = obtener_institucion(cur)
        registros = []

        if institucion:
            cur.execute("""
                SELECT id_seccion, nombre, descripcion, orden_menu
                FROM seccion
                WHERE id_institucion = %s
                  AND visible = TRUE
                ORDER BY orden_menu, nombre
            """, (institucion["id_institucion"],))
            registros = cur.fetchall()

        return render_template(
            "mapa_sitio.html",
            institucion=institucion,
            secciones=registros,
        )
    finally:
        cur.close()
        conn.close()




# ============================================================
# ADMINISTRACIÓN INSTITUCIONAL
# ============================================================

CONTENT_CONFIGS = {
    "secciones": {
        "permiso": "secciones",
        "table": "seccion",
        "pk": "id_seccion",
        "titulo": "Secciones del sitio",
        "singular": "Sección",
        "fields": [
            {"name": "nombre", "label": "Nombre", "type": "text", "required": True},
            {"name": "descripcion", "label": "Descripción", "type": "textarea"},
            {"name": "orden_menu", "label": "Orden", "type": "number", "default": 100},
            {"name": "visible", "label": "Visible", "type": "checkbox", "default": True},
        ],
        "order": "orden_menu, id_seccion",
    },
    "logros": {
        "permiso": "logros",
        "table": "logro",
        "pk": "id_logro",
        "titulo": "Logros y reconocimientos",
        "singular": "Logro",
        "fields": [
            {"name": "titulo", "label": "Título", "type": "text", "required": True},
            {"name": "descripcion", "label": "Descripción", "type": "textarea", "required": True},
            {"name": "fecha_logro", "label": "Fecha", "type": "date"},
            {"name": "categoria", "label": "Categoría", "type": "text"},
        ],
        "order": "fecha_logro DESC NULLS LAST, id_logro DESC",
    },
    "redes": {
        "permiso": "redes",
        "table": "red_social",
        "pk": "id_red",
        "titulo": "Redes y canales",
        "singular": "Canal",
        "fields": [
            {"name": "plataforma", "label": "Plataforma", "type": "text", "required": True},
            {"name": "url_enlace", "label": "URL", "type": "url", "required": True},
            {"name": "icono", "label": "Icono Bootstrap", "type": "text"},
        ],
        "order": "id_red",
    },
}


def config_contenido(tipo):
    config = CONTENT_CONFIGS.get(tipo)
    if not config:
        abort(404)
    return config


def valor_formulario(field):
    nombre = field["name"]
    if field["type"] == "checkbox":
        return request.form.get(nombre) == "on"
    if field["type"] == "number":
        raw = request.form.get(nombre, "").strip()
        return int(raw) if raw else field.get("default", 0)
    raw = request.form.get(nombre, "").strip()
    return raw if raw != "" else None


@app.route("/admin/registro", methods=["GET", "POST"])
def admin_registro():
    """Solicitud pública de una cuenta administrativa.

    Por seguridad, la cuenta se crea INACTIVA y con rol EDITOR. Un SUPERADMIN
    o Rectoría debe revisar el registro y activarlo desde Gestión de Personal.
    """
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))

    datos = {
        "nombres": "",
        "apellidos": "",
        "cargo": "",
        "correo": "",
        "usuario_web": "",
    }

    if request.method == "POST":
        if not validar_csrf_post():
            flash("La sesión del formulario expiró. Intenta nuevamente.", "danger")
            return redirect(url_for("admin_registro"))

        # Honeypot antispam: un usuario real no ve ni diligencia este campo.
        if request.form.get("website", "").strip():
            flash("No fue posible procesar la solicitud.", "danger")
            return redirect(url_for("admin_registro"))

        datos = {
            "nombres": request.form.get("nombres", "").strip(),
            "apellidos": request.form.get("apellidos", "").strip(),
            "cargo": request.form.get("cargo", "").strip(),
            "correo": request.form.get("correo", "").strip().lower(),
            "usuario_web": request.form.get("usuario_web", "").strip().lower(),
        }
        clave = request.form.get("clave", "")
        confirmar = request.form.get("confirmar_clave", "")
        acepta = request.form.get("acepta") == "on"

        errores = []
        if len(datos["nombres"]) < 2:
            errores.append("Ingresa tus nombres.")
        if len(datos["apellidos"]) < 2:
            errores.append("Ingresa tus apellidos.")
        if len(datos["cargo"]) < 3:
            errores.append("Indica tu cargo o responsabilidad institucional.")
        if not validar_correo(datos["correo"]):
            errores.append("Ingresa un correo válido.")
        if not re.fullmatch(r"[a-z0-9._-]{4,40}", datos["usuario_web"]):
            errores.append("El usuario debe tener entre 4 y 40 caracteres y usar solo letras minúsculas, números, punto, guion o guion bajo.")
        if len(clave) < 8:
            errores.append("La contraseña debe tener al menos 8 caracteres.")
        if clave != confirmar:
            errores.append("Las contraseñas no coinciden.")
        if not acepta:
            errores.append("Debes confirmar que perteneces o estás autorizado por la institución.")

        if errores:
            for error in errores:
                flash(error, "danger")
            return render_template("admin_registro.html", datos=datos), 400

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            institucion = obtener_institucion(cur)
            if not institucion:
                flash("No se encontró la institución configurada.", "danger")
                return render_template("admin_registro.html", datos=datos), 500

            cur.execute("""
                SELECT id_administrativo, usuario_web, correo, activo_web
                FROM administrativo
                WHERE id_institucion=%s
                  AND (LOWER(COALESCE(usuario_web,''))=%s OR LOWER(COALESCE(correo,''))=%s)
                LIMIT 1
            """, (institucion["id_institucion"], datos["usuario_web"], datos["correo"]))
            existente = cur.fetchone()
            if existente:
                flash("Ya existe una cuenta o solicitud con ese usuario o correo. Si está pendiente, espera la aprobación institucional.", "warning")
                return render_template("admin_registro.html", datos=datos), 409

            cur.execute("""
                INSERT INTO administrativo (
                    id_institucion, nombres, apellidos, cargo, correo,
                    dependencia, biografia, formacion, orden_visual, visible,
                    usuario_web, password_hash, rol_web, activo_web
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                institucion["id_institucion"], datos["nombres"], datos["apellidos"],
                datos["cargo"], datos["correo"], "Solicitud de acceso al portal",
                "Solicitud de cuenta administrativa pendiente de validación institucional.",
                None, 999, False, datos["usuario_web"], crear_hash_clave(clave),
                "EDITOR", False,
            ))
            conn.commit()
            flash("Solicitud registrada. Por seguridad, tu cuenta queda pendiente hasta que Rectoría o un Superadmin la revise y active.", "success")
            return redirect(url_for("admin_login"))
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    return render_template("admin_registro.html", datos=datos)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        if not validar_csrf_post():
            flash("La sesión del formulario expiró.", "danger")
            return redirect(url_for("admin_login"))

        usuario = request.form.get("usuario", "").strip().lower()
        clave = request.form.get("clave", "")

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            institucion = obtener_institucion(cur)
            if not institucion:
                flash("No se encontró la institución configurada.", "danger")
                return redirect(url_for("admin_login"))

            cur.execute("""
                SELECT id_administrativo, nombres, apellidos, cargo,
                       usuario_web, password_hash, rol_web, activo_web
                FROM administrativo
                WHERE id_institucion=%s
                  AND LOWER(usuario_web)=%s
                LIMIT 1
            """, (institucion["id_institucion"], usuario))
            admin = cur.fetchone()

            if not admin or not admin["password_hash"] or not verificar_hash_clave(admin["password_hash"], clave):
                flash("Usuario o contraseña incorrectos.", "danger")
                return render_template("admin_login.html", usuario=usuario), 401

            if not admin["activo_web"]:
                flash("Tu solicitud de acceso existe, pero aún está pendiente de aprobación por un responsable autorizado.", "warning")
                return render_template("admin_login.html", usuario=usuario), 403

            session.clear()
            session["admin_id"] = admin["id_administrativo"]
            session["admin_nombre"] = f"{admin['nombres']} {admin['apellidos']}"
            session["admin_rol"] = admin["rol_web"] or "EDITOR"
            session["csrf_token"] = secrets.token_urlsafe(32)

            siguiente = request.args.get("next")
            if siguiente and siguiente.startswith("/admin"):
                return redirect(siguiente)
            return redirect(url_for("admin_dashboard"))
        finally:
            cur.close()
            conn.close()

    return render_template("admin_login.html", usuario="")


@app.post("/admin/logout")
@admin_required
def admin_logout():
    if not validar_csrf_post():
        abort(400)
    session.clear()
    flash("Sesión administrativa cerrada.", "success")
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        iid = institucion["id_institucion"]

        cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM seccion WHERE id_institucion=%s) AS secciones,
                (SELECT COUNT(*) FROM noticia WHERE id_institucion=%s) AS noticias,
                (SELECT COUNT(*) FROM logro WHERE id_institucion=%s) AS logros,
                (SELECT COUNT(*) FROM galeria WHERE id_institucion=%s) AS galerias,
                (SELECT COUNT(*) FROM imagen_galeria ig JOIN galeria g ON g.id_galeria=ig.id_galeria WHERE g.id_institucion=%s) AS imagenes,
                (SELECT COUNT(*) FROM docente WHERE id_institucion=%s) AS docentes,
                (SELECT COUNT(*) FROM administrativo WHERE id_institucion=%s) AS administrativos,
                (SELECT COUNT(*) FROM mensaje_contacto WHERE id_institucion=%s AND estado='PENDIENTE') AS pendientes,
                (SELECT COUNT(*) FROM noticia WHERE id_institucion=%s AND estado='REVISION') AS revision,
                (SELECT COUNT(*) FROM noticia WHERE id_institucion=%s AND estado='PUBLICADA' AND video_url IS NOT NULL) AS videos,
                (SELECT COUNT(*) FROM administrativo WHERE id_institucion=%s AND usuario_web IS NOT NULL AND COALESCE(activo_web,FALSE)=FALSE) AS solicitudes_acceso
        """, (iid, iid, iid, iid, iid, iid, iid, iid, iid, iid, iid))
        metricas = cur.fetchone()

        cur.execute("""
            SELECT id_mensaje,nombre_remitente,asunto,fecha_envio,estado
            FROM mensaje_contacto
            WHERE id_institucion=%s
            ORDER BY fecha_envio DESC,id_mensaje DESC
            LIMIT 5
        """, (iid,))
        mensajes = cur.fetchall()

        cur.execute("""
            SELECT id_noticia,titulo,tipo_contenido,estado,fecha_actualizacion,
                   imagen_url,video_url
            FROM noticia
            WHERE id_institucion=%s
            ORDER BY COALESCE(fecha_actualizacion,fecha_publicacion::timestamp) DESC,id_noticia DESC
            LIMIT 6
        """, (iid,))
        actividad_editorial = cur.fetchall()

        return render_template(
            "admin_dashboard.html",
            institucion=institucion,
            metricas=metricas,
            mensajes=mensajes,
            actividad_editorial=actividad_editorial,
        )
    finally:
        cur.close()
        conn.close()


@app.route("/admin/general", methods=["GET", "POST"])
@admin_required
@permiso_required("general")
def admin_general():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        iid = institucion["id_institucion"]

        cur.execute("""
            SELECT telefono,correo,direccion,horario_atencion
            FROM contacto_institucional
            WHERE id_institucion=%s LIMIT 1
        """, (iid,))
        contacto_inst = cur.fetchone()

        if request.method == "POST":
            if not validar_csrf_post():
                abort(400)

            nombre = request.form.get("nombre", "").strip()
            if not nombre:
                flash("El nombre de la institución es obligatorio.", "danger")
            else:
                cur.execute("""
                    UPDATE institucion
                    SET nombre=%s,mision=%s,vision=%s,descripcion_general=%s
                    WHERE id_institucion=%s
                """, (
                    nombre,
                    request.form.get("mision", "").strip() or None,
                    request.form.get("vision", "").strip() or None,
                    request.form.get("descripcion_general", "").strip() or None,
                    iid,
                ))
                cur.execute("""
                    UPDATE contacto_institucional
                    SET telefono=%s,correo=%s,direccion=%s,horario_atencion=%s
                    WHERE id_institucion=%s
                """, (
                    request.form.get("telefono", "").strip() or None,
                    request.form.get("correo", "").strip() or None,
                    request.form.get("direccion", "").strip() or None,
                    request.form.get("horario_atencion", "").strip() or None,
                    iid,
                ))
                conn.commit()
                flash("Información institucional actualizada.", "success")
                return redirect(url_for("admin_general"))

        return render_template("admin_general.html", institucion=institucion, contacto=contacto_inst)
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@app.route("/admin/contenido/<tipo>")
@admin_required
def admin_contenido_lista(tipo):
    config = config_contenido(tipo)
    permisos = PERMISOS_ROL.get(session.get("admin_rol", ""), set())
    if "*" not in permisos and config["permiso"] not in permisos:
        flash("No tienes permiso para este módulo.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        cur.execute(f"""
            SELECT * FROM {config['table']}
            WHERE id_institucion=%s
            ORDER BY {config['order']}
        """, (iid,))
        registros = cur.fetchall()
        return render_template("admin_content_list.html", config=config, tipo=tipo, registros=registros)
    finally:
        cur.close()
        conn.close()


@app.route("/admin/contenido/<tipo>/nuevo", methods=["GET", "POST"])
@app.route("/admin/contenido/<tipo>/<int:item_id>/editar", methods=["GET", "POST"])
@admin_required
def admin_contenido_form(tipo, item_id=None):
    config = config_contenido(tipo)
    permisos = PERMISOS_ROL.get(session.get("admin_rol", ""), set())
    if "*" not in permisos and config["permiso"] not in permisos:
        flash("No tienes permiso para este módulo.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        registro = None

        if item_id:
            cur.execute(f"SELECT * FROM {config['table']} WHERE {config['pk']}=%s AND id_institucion=%s", (item_id, iid))
            registro = cur.fetchone()
            if not registro:
                abort(404)

        if request.method == "POST":
            if not validar_csrf_post():
                abort(400)

            valores = {}
            errores = []
            for field in config["fields"]:
                valor = valor_formulario(field)
                if field.get("required") and (valor is None or valor == ""):
                    errores.append(f"{field['label']} es obligatorio.")
                valores[field["name"]] = valor

            if errores:
                for error in errores:
                    flash(error, "danger")
                registro = valores
            else:
                columnas = [f["name"] for f in config["fields"]]
                params = [valores[col] for col in columnas]
                if item_id:
                    set_sql = ", ".join([f"{col}=%s" for col in columnas])
                    cur.execute(
                        f"UPDATE {config['table']} SET {set_sql} WHERE {config['pk']}=%s AND id_institucion=%s",
                        params + [item_id, iid],
                    )
                else:
                    columnas_sql = ", ".join(["id_institucion"] + columnas)
                    placeholders = ", ".join(["%s"] * (len(columnas) + 1))
                    cur.execute(
                        f"INSERT INTO {config['table']} ({columnas_sql}) VALUES ({placeholders})",
                        [iid] + params,
                    )
                conn.commit()
                flash(f"{config['singular']} guardada correctamente.", "success")
                return redirect(url_for("admin_contenido_lista", tipo=tipo))

        return render_template(
            "admin_content_form.html",
            config=config,tipo=tipo,registro=registro or {},item_id=item_id,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@app.post("/admin/contenido/<tipo>/<int:item_id>/eliminar")
@admin_required
def admin_contenido_eliminar(tipo, item_id):
    config = config_contenido(tipo)
    permisos = PERMISOS_ROL.get(session.get("admin_rol", ""), set())
    if "*" not in permisos and config["permiso"] not in permisos:
        abort(403)
    if not validar_csrf_post():
        abort(400)

    conn = get_connection()
    cur = conn.cursor()
    try:
        iid = obtener_institucion_id()
        cur.execute(f"DELETE FROM {config['table']} WHERE {config['pk']}=%s AND id_institucion=%s", (item_id, iid))
        conn.commit()
        flash(f"{config['singular']} eliminada.", "success")
        return redirect(url_for("admin_contenido_lista", tipo=tipo))
    finally:
        cur.close()
        conn.close()






@app.route("/admin/noticias")
@admin_required
@permiso_required("noticias")
def admin_noticias():
    estado = request.args.get("estado", "").strip().upper()
    tipo = request.args.get("tipo", "").strip().upper()
    q = request.args.get("q", "").strip()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        filtros = ["n.id_institucion=%s"]
        params = [iid]
        if estado in {"BORRADOR", "REVISION", "PUBLICADA", "ARCHIVADA"}:
            filtros.append("n.estado=%s")
            params.append(estado)
        if tipo in {"NOTICIA", "EVENTO", "COMUNICADO"}:
            filtros.append("n.tipo_contenido=%s")
            params.append(tipo)
        if q:
            patron = f"%{q}%"
            filtros.append("(n.titulo ILIKE %s OR n.resumen ILIKE %s)")
            params.extend([patron, patron])

        cur.execute(f"""
            SELECT n.id_noticia,n.titulo,n.resumen,n.fecha_publicacion,n.estado,
                   n.tipo_contenido,n.imagen_url,n.video_url,n.destacada,
                   n.fecha_actualizacion,
                   CONCAT(COALESCE(a.nombres,''),' ',COALESCE(a.apellidos,'')) AS editor
            FROM noticia n
            LEFT JOIN administrativo a ON a.id_administrativo=n.ultimo_editor_id
            WHERE {' AND '.join(filtros)}
            ORDER BY COALESCE(n.fecha_actualizacion,n.fecha_publicacion::timestamp) DESC,n.id_noticia DESC
        """, params)
        registros = cur.fetchall()

        cur.execute("""
            SELECT estado,COUNT(*) total
            FROM noticia WHERE id_institucion=%s
            GROUP BY estado
        """, (iid,))
        conteos = {r["estado"]: r["total"] for r in cur.fetchall()}

        return render_template(
            "admin_noticias.html",
            noticias=registros, estado=estado, tipo=tipo, q=q,
            conteos=conteos, puede_publicar=puede_publicar(),
        )
    finally:
        cur.close()
        conn.close()


@app.route("/admin/noticias/nueva", methods=["GET", "POST"])
@app.route("/admin/noticias/<int:id_noticia>/editar", methods=["GET", "POST"])
@admin_required
@permiso_required("noticias")
def admin_noticia_form(id_noticia=None):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        noticia = {}
        if id_noticia:
            cur.execute("SELECT * FROM noticia WHERE id_noticia=%s AND id_institucion=%s", (id_noticia, iid))
            noticia = cur.fetchone()
            if not noticia:
                abort(404)

        if request.method == "POST":
            if not validar_csrf_post():
                abort(400)

            titulo = request.form.get("titulo", "").strip()
            resumen = request.form.get("resumen", "").strip()
            contenido = request.form.get("contenido", "").strip() or None
            fecha_publicacion = request.form.get("fecha_publicacion", "").strip() or None
            tipo_contenido = request.form.get("tipo_contenido", "NOTICIA").strip().upper()
            estado = request.form.get("estado", "BORRADOR").strip().upper()
            destacada = request.form.get("destacada") == "on"
            orden_raw = request.form.get("orden_destacado", "999").strip()
            try:
                orden_destacado = max(1, int(orden_raw))
            except ValueError:
                orden_destacado = 999

            if tipo_contenido not in {"NOTICIA", "EVENTO", "COMUNICADO"}:
                tipo_contenido = "NOTICIA"
            if estado not in {"BORRADOR", "REVISION", "PUBLICADA", "ARCHIVADA"}:
                estado = "BORRADOR"
            if not puede_publicar() and estado in {"PUBLICADA", "ARCHIVADA"}:
                estado = "REVISION"
            if id_noticia and noticia and noticia.get("estado") == "PUBLICADA" and not puede_publicar():
                estado = "REVISION"

            errores = []
            if len(titulo) < 5:
                errores.append("El título debe tener al menos 5 caracteres.")
            if len(resumen) < 10:
                errores.append("El resumen debe tener al menos 10 caracteres.")
            if not fecha_publicacion:
                errores.append("La fecha de publicación es obligatoria.")

            imagen_url = noticia.get("imagen_url") if noticia else None
            video_url = noticia.get("video_url") if noticia else None

            if request.form.get("eliminar_imagen") == "1":
                eliminar_archivo_local(imagen_url)
                imagen_url = None
            if request.form.get("eliminar_video") == "1":
                eliminar_archivo_local(video_url)
                video_url = None

            try:
                imagen = request.files.get("imagen")
                if imagen and imagen.filename:
                    nueva_imagen = guardar_imagen_noticia(imagen)
                    eliminar_archivo_local(imagen_url)
                    imagen_url = nueva_imagen

                video = request.files.get("video")
                if video and video.filename:
                    nuevo_video = guardar_video(video)
                    eliminar_archivo_local(video_url)
                    video_url = nuevo_video
            except ValueError as exc:
                errores.append(str(exc))

            if errores:
                for error in errores:
                    flash(error, "danger")
                noticia = request.form.to_dict()
                noticia.update({"imagen_url": imagen_url, "video_url": video_url})
            else:
                admin_id = session.get("admin_id")
                aprobador = admin_id if estado == "PUBLICADA" and puede_publicar() else None

                if id_noticia:
                    cur.execute("""
                        UPDATE noticia
                        SET titulo=%s,resumen=%s,contenido=%s,fecha_publicacion=%s,
                            estado=%s,tipo_contenido=%s,imagen_url=%s,video_url=%s,
                            destacada=%s,orden_destacado=%s,ultimo_editor_id=%s,
                            fecha_actualizacion=CURRENT_TIMESTAMP,
                            aprobado_por_id=CASE WHEN %s IS NOT NULL THEN %s ELSE aprobado_por_id END,
                            fecha_aprobacion=CASE WHEN %s IS NOT NULL THEN CURRENT_TIMESTAMP ELSE fecha_aprobacion END
                        WHERE id_noticia=%s AND id_institucion=%s
                    """, (
                        titulo,resumen,contenido,fecha_publicacion,estado,tipo_contenido,
                        imagen_url,video_url,destacada,orden_destacado,admin_id,
                        aprobador,aprobador,aprobador,id_noticia,iid,
                    ))
                else:
                    cur.execute("""
                        INSERT INTO noticia (
                            id_institucion,titulo,resumen,contenido,fecha_publicacion,estado,
                            tipo_contenido,imagen_url,video_url,destacada,orden_destacado,
                            creado_por_id,ultimo_editor_id,aprobado_por_id,
                            fecha_actualizacion,fecha_aprobacion
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP,
                                  CASE WHEN %s IS NOT NULL THEN CURRENT_TIMESTAMP ELSE NULL END)
                    """, (
                        iid,titulo,resumen,contenido,fecha_publicacion,estado,tipo_contenido,
                        imagen_url,video_url,destacada,orden_destacado,admin_id,admin_id,
                        aprobador,aprobador,
                    ))

                conn.commit()
                flash("Contenido editorial guardado correctamente.", "success")
                return redirect(url_for("admin_noticias"))

        return render_template(
            "admin_noticia_form.html",
            noticia=noticia or {}, id_noticia=id_noticia,
            puede_publicar=puede_publicar(),
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@app.post("/admin/noticias/<int:id_noticia>/estado")
@admin_required
@permiso_required("noticias")
def admin_noticia_estado(id_noticia):
    if not validar_csrf_post():
        abort(400)
    nuevo = request.form.get("estado", "").strip().upper()
    if nuevo not in {"BORRADOR", "REVISION", "PUBLICADA", "ARCHIVADA"}:
        abort(400)
    if nuevo in {"PUBLICADA", "ARCHIVADA"} and not puede_publicar():
        flash("Solo Rectoría o Superadmin pueden publicar o archivar contenido público.", "danger")
        return redirect(url_for("admin_noticias"))

    conn = get_connection()
    cur = conn.cursor()
    try:
        iid = obtener_institucion_id()
        admin_id = session.get("admin_id")
        cur.execute("""
            UPDATE noticia
            SET estado=%s,ultimo_editor_id=%s,fecha_actualizacion=CURRENT_TIMESTAMP,
                aprobado_por_id=CASE WHEN %s='PUBLICADA' THEN %s ELSE aprobado_por_id END,
                fecha_aprobacion=CASE WHEN %s='PUBLICADA' THEN CURRENT_TIMESTAMP ELSE fecha_aprobacion END
            WHERE id_noticia=%s AND id_institucion=%s
        """, (nuevo,admin_id,nuevo,admin_id,nuevo,id_noticia,iid))
        conn.commit()
        flash("Estado editorial actualizado.", "success")
        return redirect(url_for("admin_noticias"))
    finally:
        cur.close()
        conn.close()


@app.post("/admin/noticias/<int:id_noticia>/eliminar")
@admin_required
@permiso_required("noticias")
def admin_noticia_eliminar(id_noticia):
    if not validar_csrf_post():
        abort(400)
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        cur.execute("SELECT imagen_url,video_url,estado FROM noticia WHERE id_noticia=%s AND id_institucion=%s", (id_noticia,iid))
        registro = cur.fetchone()
        if registro:
            if registro.get("estado") == "PUBLICADA" and not puede_publicar():
                flash("Solo Rectoría o Superadmin pueden eliminar una publicación pública.", "danger")
                return redirect(url_for("admin_noticias"))
            eliminar_archivo_local(registro.get("imagen_url"))
            eliminar_archivo_local(registro.get("video_url"))
        cur.execute("DELETE FROM noticia WHERE id_noticia=%s AND id_institucion=%s", (id_noticia,iid))
        conn.commit()
        flash("Contenido eliminado.", "success")
        return redirect(url_for("admin_noticias"))
    finally:
        cur.close()
        conn.close()


@app.route("/admin/cuenta", methods=["GET", "POST"])
@admin_required
def admin_cuenta():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        cur.execute("""
            SELECT id_administrativo,nombres,apellidos,cargo,correo,usuario_web,
                   rol_web,password_hash
            FROM administrativo
            WHERE id_administrativo=%s AND id_institucion=%s
        """, (session.get("admin_id"),iid))
        cuenta = cur.fetchone()
        if not cuenta:
            abort(404)

        if request.method == "POST":
            if not validar_csrf_post():
                abort(400)
            actual = request.form.get("clave_actual", "")
            nueva = request.form.get("clave_nueva", "")
            confirmar = request.form.get("confirmar_clave", "")
            errores = []
            if not verificar_hash_clave(cuenta.get("password_hash"), actual):
                errores.append("La contraseña actual no es correcta.")
            if len(nueva) < 10:
                errores.append("La nueva contraseña debe tener al menos 10 caracteres.")
            if nueva != confirmar:
                errores.append("La confirmación no coincide.")
            if errores:
                for error in errores:
                    flash(error, "danger")
            else:
                cur.execute("""
                    UPDATE administrativo SET password_hash=%s
                    WHERE id_administrativo=%s AND id_institucion=%s
                """, (crear_hash_clave(nueva),session.get("admin_id"),iid))
                conn.commit()
                flash("Contraseña actualizada correctamente.", "success")
                return redirect(url_for("admin_cuenta"))

        return render_template("admin_cuenta.html", cuenta=cuenta)
    finally:
        cur.close()
        conn.close()


@app.route("/admin/personal")
@admin_required
@permiso_required("personal")
def admin_personal():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        cur.execute("""
            SELECT id_docente AS id,nombres,apellidos,cargo,correo,area,
                   foto_url,visible,orden_visual,'docente' AS tipo
            FROM docente WHERE id_institucion=%s
            ORDER BY orden_visual,apellidos,nombres
        """, (iid,))
        docentes = cur.fetchall()

        cur.execute("""
            SELECT id_administrativo AS id,nombres,apellidos,cargo,correo,
                   dependencia AS area,foto_url,visible,orden_visual,
                   usuario_web,rol_web,activo_web,'administrativo' AS tipo
            FROM administrativo WHERE id_institucion=%s
            ORDER BY orden_visual,apellidos,nombres
        """, (iid,))
        administrativos = cur.fetchall()

        return render_template(
            "admin_personal.html",
            docentes=docentes,
            administrativos=administrativos,
        )
    finally:
        cur.close()
        conn.close()


@app.route("/admin/personal/<tipo>/nuevo", methods=["GET", "POST"])
@app.route("/admin/personal/<tipo>/<int:persona_id>/editar", methods=["GET", "POST"])
@admin_required
@permiso_required("personal")
def admin_persona_form(tipo, persona_id=None):
    if tipo not in {"docente", "administrativo"}:
        abort(404)

    tabla = "docente" if tipo == "docente" else "administrativo"
    pk = "id_docente" if tipo == "docente" else "id_administrativo"

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        persona = {}

        if persona_id:
            cur.execute(
                f"SELECT * FROM {tabla} WHERE {pk}=%s AND id_institucion=%s",
                (persona_id, iid),
            )
            persona = cur.fetchone()
            if not persona:
                abort(404)

        if request.method == "POST":
            if not validar_csrf_post():
                abort(400)

            nombres = request.form.get("nombres", "").strip()
            apellidos = request.form.get("apellidos", "").strip()
            cargo = request.form.get("cargo", "").strip()
            correo = request.form.get("correo", "").strip().lower() or None
            biografia = request.form.get("biografia", "").strip() or None
            formacion = request.form.get("formacion", "").strip() or None
            visible = request.form.get("visible") == "on"

            orden_raw = request.form.get("orden_visual", "100").strip()
            try:
                orden = max(1, int(orden_raw))
            except ValueError:
                orden = 100

            if not nombres or not apellidos or not cargo:
                flash("Nombres, apellidos y cargo son obligatorios.", "danger")
                persona = request.form.to_dict()
            elif correo and not validar_correo(correo):
                flash("El correo no tiene un formato válido.", "danger")
                persona = request.form.to_dict()
            else:
                foto_actual = persona.get("foto_url") if persona else None
                foto_url = foto_actual
                archivo = request.files.get("foto")
                if archivo and archivo.filename:
                    nueva = guardar_imagen(archivo, "personal")
                    eliminar_archivo_local(foto_actual)
                    foto_url = nueva

                if tipo == "docente":
                    area = request.form.get("area", "").strip() or cargo
                    exp_raw = request.form.get("anios_experiencia", "").strip()
                    experiencia = None
                    if exp_raw:
                        try:
                            experiencia = max(0, min(60, int(exp_raw)))
                        except ValueError:
                            experiencia = None

                    if persona_id:
                        cur.execute("""
                            UPDATE docente
                            SET nombres=%s,apellidos=%s,cargo=%s,correo=%s,
                                area=%s,foto_url=%s,biografia=%s,formacion=%s,
                                anios_experiencia=%s,orden_visual=%s,visible=%s
                            WHERE id_docente=%s AND id_institucion=%s
                        """, (
                            nombres,apellidos,cargo,correo,area,foto_url,biografia,
                            formacion,experiencia,orden,visible,persona_id,iid,
                        ))
                    else:
                        cur.execute("""
                            INSERT INTO docente (
                                id_institucion,nombres,apellidos,cargo,correo,
                                area,foto_url,biografia,formacion,anios_experiencia,
                                orden_visual,visible
                            )
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (
                            iid,nombres,apellidos,cargo,correo,area,foto_url,
                            biografia,formacion,experiencia,orden,visible,
                        ))
                else:
                    dependencia = request.form.get("dependencia", "").strip() or cargo
                    usuario_web = request.form.get("usuario_web", "").strip().lower() or None
                    rol_web = request.form.get("rol_web", "EDITOR").strip() or "EDITOR"
                    activo_web = request.form.get("activo_web") == "on"
                    clave = request.form.get("clave", "")

                    if rol_web not in PERMISOS_ROL:
                        rol_web = "EDITOR"

                    password_hash = persona.get("password_hash") if persona else None
                    if clave:
                        if len(clave) < 8:
                            flash("La contraseña debe tener al menos 8 caracteres.", "danger")
                            return render_template(
                                "admin_persona_form.html",
                                tipo=tipo,
                                persona=request.form.to_dict(),
                                persona_id=persona_id,
                                roles=list(PERMISOS_ROL.keys()),
                            ), 400
                        password_hash = crear_hash_clave(clave)

                    if persona_id:
                        cur.execute("""
                            UPDATE administrativo
                            SET nombres=%s,apellidos=%s,cargo=%s,correo=%s,
                                dependencia=%s,foto_url=%s,biografia=%s,formacion=%s,
                                orden_visual=%s,visible=%s,usuario_web=%s,
                                password_hash=%s,rol_web=%s,activo_web=%s
                            WHERE id_administrativo=%s AND id_institucion=%s
                        """, (
                            nombres,apellidos,cargo,correo,dependencia,foto_url,
                            biografia,formacion,orden,visible,usuario_web,
                            password_hash,rol_web,activo_web,persona_id,iid,
                        ))
                    else:
                        cur.execute("""
                            INSERT INTO administrativo (
                                id_institucion,nombres,apellidos,cargo,correo,
                                dependencia,foto_url,biografia,formacion,orden_visual,
                                visible,usuario_web,password_hash,rol_web,activo_web
                            )
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (
                            iid,nombres,apellidos,cargo,correo,dependencia,foto_url,
                            biografia,formacion,orden,visible,usuario_web,password_hash,
                            rol_web,activo_web,
                        ))

                conn.commit()
                flash("Registro de personal guardado correctamente.", "success")
                return redirect(url_for("admin_personal"))

        return render_template(
            "admin_persona_form.html",
            tipo=tipo,
            persona=persona or {},
            persona_id=persona_id,
            roles=list(PERMISOS_ROL.keys()),
        )
    except ValueError as exc:
        conn.rollback()
        flash(str(exc), "danger")
        return render_template(
            "admin_persona_form.html",
            tipo=tipo,
            persona=request.form.to_dict(),
            persona_id=persona_id,
            roles=list(PERMISOS_ROL.keys()),
        ), 400
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@app.post("/admin/personal/<tipo>/<int:persona_id>/eliminar")
@admin_required
@permiso_required("personal")
def admin_persona_eliminar(tipo, persona_id):
    if tipo not in {"docente", "administrativo"}:
        abort(404)
    if not validar_csrf_post():
        abort(400)
    if tipo == "administrativo" and persona_id == session.get("admin_id"):
        flash("No puedes eliminar tu propio usuario con la sesión abierta.", "danger")
        return redirect(url_for("admin_personal"))

    tabla = "docente" if tipo == "docente" else "administrativo"
    pk = "id_docente" if tipo == "docente" else "id_administrativo"

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        cur.execute(
            f"SELECT foto_url FROM {tabla} WHERE {pk}=%s AND id_institucion=%s",
            (persona_id, iid),
        )
        actual = cur.fetchone()
        if actual:
            eliminar_archivo_local(actual.get("foto_url"))
        cur.execute(
            f"DELETE FROM {tabla} WHERE {pk}=%s AND id_institucion=%s",
            (persona_id, iid),
        )
        conn.commit()
        flash("Registro eliminado.", "success")
        return redirect(url_for("admin_personal"))
    finally:
        cur.close()
        conn.close()




@app.route("/admin/galerias")
@admin_required
@permiso_required("galerias")
def admin_galerias():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        cur.execute("""
            SELECT g.id_galeria,g.nombre,g.descripcion,g.tipo,
                   COUNT(ig.id_imagen) AS total_imagenes
            FROM galeria g
            LEFT JOIN imagen_galeria ig ON ig.id_galeria=g.id_galeria
            WHERE g.id_institucion=%s
            GROUP BY g.id_galeria,g.nombre,g.descripcion,g.tipo
            ORDER BY g.id_galeria DESC
        """, (iid,))
        galerias = cur.fetchall()
        return render_template("admin_galerias.html", galerias=galerias)
    finally:
        cur.close()
        conn.close()


@app.route("/admin/galerias/nueva", methods=["GET", "POST"])
@app.route("/admin/galerias/<int:id_galeria>/editar", methods=["GET", "POST"])
@admin_required
@permiso_required("galerias")
def admin_galeria_form(id_galeria=None):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        galeria = {}
        if id_galeria:
            cur.execute(
                "SELECT * FROM galeria WHERE id_galeria=%s AND id_institucion=%s",
                (id_galeria, iid),
            )
            galeria = cur.fetchone()
            if not galeria:
                abort(404)

        if request.method == "POST":
            if not validar_csrf_post():
                abort(400)

            nombre = request.form.get("nombre", "").strip()
            descripcion = request.form.get("descripcion", "").strip() or None
            tipo = request.form.get("tipo", "").strip() or None

            if not nombre:
                flash("El nombre de la galería es obligatorio.", "danger")
            else:
                if id_galeria:
                    cur.execute("""
                        UPDATE galeria SET nombre=%s,descripcion=%s,tipo=%s
                        WHERE id_galeria=%s AND id_institucion=%s
                    """, (nombre, descripcion, tipo, id_galeria, iid))
                else:
                    cur.execute("""
                        INSERT INTO galeria (id_institucion,nombre,descripcion,tipo)
                        VALUES (%s,%s,%s,%s)
                    """, (iid, nombre, descripcion, tipo))
                conn.commit()
                flash("Galería guardada.", "success")
                return redirect(url_for("admin_galerias"))

        return render_template(
            "admin_galeria_form.html",
            galeria=galeria or {},
            id_galeria=id_galeria,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@app.post("/admin/galerias/<int:id_galeria>/eliminar")
@admin_required
@permiso_required("galerias")
def admin_galeria_eliminar(id_galeria):
    if not validar_csrf_post():
        abort(400)

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        cur.execute("""
            SELECT ig.url_imagen
            FROM imagen_galeria ig
            JOIN galeria g ON g.id_galeria=ig.id_galeria
            WHERE g.id_galeria=%s AND g.id_institucion=%s
        """, (id_galeria, iid))
        for fila in cur.fetchall():
            eliminar_archivo_local(fila["url_imagen"])

        cur.execute(
            "DELETE FROM galeria WHERE id_galeria=%s AND id_institucion=%s",
            (id_galeria, iid),
        )
        conn.commit()
        flash("Galería e imágenes asociadas eliminadas.", "success")
        return redirect(url_for("admin_galerias"))
    finally:
        cur.close()
        conn.close()


@app.route("/admin/galerias/<int:id_galeria>/imagenes", methods=["GET", "POST"])
@admin_required
@permiso_required("galerias")
def admin_imagenes(id_galeria):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        cur.execute(
            "SELECT * FROM galeria WHERE id_galeria=%s AND id_institucion=%s",
            (id_galeria, iid),
        )
        galeria = cur.fetchone()
        if not galeria:
            abort(404)

        if request.method == "POST":
            if not validar_csrf_post():
                abort(400)

            archivo = request.files.get("imagen")
            pie = request.form.get("pie_foto", "").strip() or None
            try:
                url_imagen = guardar_imagen(archivo, "galeria")
            except ValueError as exc:
                flash(str(exc), "danger")
                return redirect(url_for("admin_imagenes", id_galeria=id_galeria))

            if not url_imagen:
                flash("Selecciona una imagen.", "danger")
            else:
                cur.execute("""
                    INSERT INTO imagen_galeria (id_galeria,url_imagen,pie_foto,fecha_carga)
                    VALUES (%s,%s,%s,CURRENT_TIMESTAMP)
                """, (id_galeria, url_imagen, pie))
                conn.commit()
                flash("Imagen cargada correctamente.", "success")

            return redirect(url_for("admin_imagenes", id_galeria=id_galeria))

        cur.execute("""
            SELECT id_imagen,url_imagen,pie_foto,fecha_carga
            FROM imagen_galeria
            WHERE id_galeria=%s
            ORDER BY fecha_carga DESC,id_imagen DESC
        """, (id_galeria,))
        imagenes = cur.fetchall()

        return render_template(
            "admin_imagenes.html",
            galeria=galeria,
            imagenes=imagenes,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@app.post("/admin/imagen/<int:id_imagen>/actualizar")
@admin_required
@permiso_required("galerias")
def admin_imagen_actualizar(id_imagen):
    if not validar_csrf_post():
        abort(400)

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        cur.execute("""
            SELECT ig.*,g.id_institucion
            FROM imagen_galeria ig
            JOIN galeria g ON g.id_galeria=ig.id_galeria
            WHERE ig.id_imagen=%s AND g.id_institucion=%s
        """, (id_imagen, iid))
        imagen = cur.fetchone()
        if not imagen:
            abort(404)

        pie = request.form.get("pie_foto", "").strip() or None
        nueva = request.files.get("imagen")
        url = imagen["url_imagen"]

        if nueva and nueva.filename:
            try:
                nueva_url = guardar_imagen(nueva, "galeria")
            except ValueError as exc:
                flash(str(exc), "danger")
                return redirect(url_for("admin_imagenes", id_galeria=imagen["id_galeria"]))
            eliminar_archivo_local(url)
            url = nueva_url

        cur.execute("""
            UPDATE imagen_galeria
            SET pie_foto=%s,url_imagen=%s
            WHERE id_imagen=%s
        """, (pie, url, id_imagen))
        conn.commit()
        flash("Imagen actualizada.", "success")
        return redirect(url_for("admin_imagenes", id_galeria=imagen["id_galeria"]))
    finally:
        cur.close()
        conn.close()


@app.post("/admin/imagen/<int:id_imagen>/eliminar")
@admin_required
@permiso_required("galerias")
def admin_imagen_eliminar(id_imagen):
    if not validar_csrf_post():
        abort(400)

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        cur.execute("""
            SELECT ig.id_galeria,ig.url_imagen
            FROM imagen_galeria ig
            JOIN galeria g ON g.id_galeria=ig.id_galeria
            WHERE ig.id_imagen=%s AND g.id_institucion=%s
        """, (id_imagen, iid))
        imagen = cur.fetchone()
        if not imagen:
            abort(404)

        eliminar_archivo_local(imagen["url_imagen"])
        cur.execute("DELETE FROM imagen_galeria WHERE id_imagen=%s", (id_imagen,))
        conn.commit()
        flash("Imagen eliminada.", "success")
        return redirect(url_for("admin_imagenes", id_galeria=imagen["id_galeria"]))
    finally:
        cur.close()
        conn.close()


@app.route("/admin/mensajes")
@admin_required
@permiso_required("mensajes")
def admin_mensajes():
    estado = request.args.get("estado", "").strip()
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        iid = obtener_institucion_id()
        params = [iid]
        filtro = ""
        if estado in {"PENDIENTE", "LEIDO", "RESPONDIDO", "ARCHIVADO"}:
            filtro = " AND estado=%s"
            params.append(estado)

        cur.execute(f"""
            SELECT *
            FROM mensaje_contacto
            WHERE id_institucion=%s {filtro}
            ORDER BY fecha_envio DESC,id_mensaje DESC
        """, params)
        mensajes = cur.fetchall()
        return render_template("admin_mensajes.html", mensajes=mensajes, estado=estado)
    finally:
        cur.close()
        conn.close()


@app.post("/admin/mensajes/<int:id_mensaje>/estado")
@admin_required
@permiso_required("mensajes")
def admin_mensaje_estado(id_mensaje):
    if not validar_csrf_post():
        abort(400)

    nuevo = request.form.get("estado", "")
    if nuevo not in {"PENDIENTE", "LEIDO", "RESPONDIDO", "ARCHIVADO"}:
        abort(400)

    conn = get_connection()
    cur = conn.cursor()
    try:
        iid = obtener_institucion_id()
        cur.execute("""
            UPDATE mensaje_contacto
            SET estado=%s
            WHERE id_mensaje=%s AND id_institucion=%s
        """, (nuevo, id_mensaje, iid))
        conn.commit()
        flash("Estado actualizado.", "success")
        return redirect(url_for("admin_mensajes"))
    finally:
        cur.close()
        conn.close()


@app.post("/admin/mensajes/<int:id_mensaje>/eliminar")
@admin_required
@permiso_required("mensajes")
def admin_mensaje_eliminar(id_mensaje):
    if not validar_csrf_post():
        abort(400)

    conn = get_connection()
    cur = conn.cursor()
    try:
        iid = obtener_institucion_id()
        cur.execute(
            "DELETE FROM mensaje_contacto WHERE id_mensaje=%s AND id_institucion=%s",
            (id_mensaje, iid),
        )
        conn.commit()
        flash("Mensaje eliminado.", "success")
        return redirect(url_for("admin_mensajes"))
    finally:
        cur.close()
        conn.close()


@app.errorhandler(413)
def archivo_demasiado_grande(error):
    flash("El archivo supera el límite permitido de 80 MB.", "danger")
    if request.path.startswith("/admin"):
        return redirect(request.referrer or url_for("admin_dashboard"))
    return redirect(request.referrer or url_for("inicio"))


@app.errorhandler(404)
def pagina_no_encontrada(error):
    return render_template("404.html"), 404



# ============================================================================
# FASE 2 · PANEL ADMINISTRATIVO COMPLETO
# ============================================================================
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            flash("🔒 Debes iniciar sesión como administrador", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

# ========== CALENDARIO ADMIN ==========
@app.route("/admin/calendario")
@admin_required
def admin_calendario():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        if not institucion:
            flash("No se encontró la institución", "danger")
            return redirect(url_for("inicio"))
        iid = institucion["id_institucion"]
        cur.execute("SELECT * FROM evento_calendario WHERE id_institucion = %s ORDER BY fecha_inicio DESC", (iid,))
        eventos = cur.fetchall()
        return render_template("admin_calendario.html", eventos=eventos, institucion=institucion)
    finally:
        cur.close()
        conn.close()

@app.route("/admin/calendario/nuevo", methods=["GET", "POST"])
@admin_required
def calendario_nuevo():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        iid = institucion["id_institucion"]
        admin_id = session.get("admin_id")
        if request.method == "POST":
            cur.execute("""
                INSERT INTO evento_calendario
                (id_institucion, titulo, descripcion, fecha_inicio, fecha_fin,
                 hora_inicio, hora_fin, tipo_evento, ubicacion, responsable,
                 es_dia_no_laboral, color_etiqueta, visible_publico, id_administrativo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (iid, request.form["titulo"], request.form["descripcion"],
                  request.form["fecha_inicio"], request.form["fecha_fin"] or None,
                  request.form["hora_inicio"] or None, request.form["hora_fin"] or None,
                  request.form["tipo_evento"], request.form["ubicacion"], request.form["responsable"],
                  "es_dia_no_laboral" in request.form, request.form["color_etiqueta"],
                  "visible_publico" in request.form, admin_id))
            conn.commit()
            flash("✅ Evento creado", "success")
            return redirect(url_for("admin_calendario"))
        return render_template("calendario_form.html", evento=None)
    finally:
        cur.close()
        conn.close()

@app.route("/admin/calendario/editar/<int:id_e>", methods=["GET", "POST"])
@admin_required
def calendario_editar(id_e):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        iid = institucion["id_institucion"]
        admin_id = session.get("admin_id")
        if request.method == "POST":
            cur.execute("""
                UPDATE evento_calendario SET
                    titulo=%s, descripcion=%s, fecha_inicio=%s, fecha_fin=%s,
                    hora_inicio=%s, hora_fin=%s, tipo_evento=%s, ubicacion=%s,
                    responsable=%s, es_dia_no_laboral=%s, color_etiqueta=%s,
                    visible_publico=%s, id_administrativo=%s
                WHERE id_evento=%s AND id_institucion=%s
            """, (request.form["titulo"], request.form["descripcion"],
                  request.form["fecha_inicio"], request.form["fecha_fin"] or None,
                  request.form["hora_inicio"] or None, request.form["hora_fin"] or None,
                  request.form["tipo_evento"], request.form["ubicacion"], request.form["responsable"],
                  "es_dia_no_laboral" in request.form, request.form["color_etiqueta"],
                  "visible_publico" in request.form, admin_id, id_e, iid))
            conn.commit()
            flash("✅ Evento actualizado", "success")
            return redirect(url_for("admin_calendario"))
        cur.execute("SELECT * FROM evento_calendario WHERE id_evento=%s AND id_institucion=%s", (id_e, iid))
        evento = cur.fetchone()
        return render_template("calendario_form.html", evento=evento)
    finally:
        cur.close()
        conn.close()

@app.route("/admin/calendario/eliminar/<int:id_e>", methods=["POST"])
@admin_required
def calendario_eliminar(id_e):
    conn = get_connection()
    cur = conn.cursor()
    try:
        institucion = obtener_institucion(cur)
        iid = institucion["id_institucion"]
        cur.execute("DELETE FROM evento_calendario WHERE id_evento=%s AND id_institucion=%s", (id_e, iid))
        conn.commit()
        flash("🗑️ Evento eliminado", "info")
        return redirect(url_for("admin_calendario"))
    finally:
        cur.close()
        conn.close()

# ========== FAQ ADMIN ==========
@app.route("/admin/faq")
@admin_required
def admin_faq():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        if not institucion:
            flash("No se encontró la institución", "danger")
            return redirect(url_for("inicio"))
        iid = institucion["id_institucion"]
        cur.execute("SELECT * FROM faq_institucional WHERE id_institucion = %s ORDER BY categoria, orden_visual, id_faq", (iid,))
        preguntas = cur.fetchall()
        return render_template("admin_faq.html", preguntas=preguntas, institucion=institucion)
    finally:
        cur.close()
        conn.close()

@app.route("/admin/faq/nuevo", methods=["GET", "POST"])
@admin_required
def faq_nuevo():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        iid = institucion["id_institucion"]
        admin_id = session.get("admin_id")
        if request.method == "POST":
            cur.execute("""
                INSERT INTO faq_institucional
                (id_institucion, categoria, pregunta, respuesta, orden_visual, visible, id_administrativo)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (iid, request.form["categoria"], request.form["pregunta"],
                  request.form["respuesta"], int(request.form["orden_visual"]),
                  "visible" in request.form, admin_id))
            conn.commit()
            flash("✅ Pregunta creada", "success")
            return redirect(url_for("admin_faq"))
        return render_template("faq_form.html", pregunta=None)
    finally:
        cur.close()
        conn.close()

@app.route("/admin/faq/editar/<int:id_p>", methods=["GET", "POST"])
@admin_required
def faq_editar(id_p):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        iid = institucion["id_institucion"]
        admin_id = session.get("admin_id")
        if request.method == "POST":
            cur.execute("""
                UPDATE faq_institucional SET
                    categoria=%s, pregunta=%s, respuesta=%s, orden_visual=%s,
                    visible=%s, id_administrativo=%s
                WHERE id_faq=%s AND id_institucion=%s
            """, (request.form["categoria"], request.form["pregunta"], request.form["respuesta"],
                  int(request.form["orden_visual"]), "visible" in request.form, admin_id, id_p, iid))
            conn.commit()
            flash("✅ Pregunta actualizada", "success")
            return redirect(url_for("admin_faq"))
        cur.execute("SELECT * FROM faq_institucional WHERE id_faq=%s AND id_institucion=%s", (id_p, iid))
        pregunta = cur.fetchone()
        return render_template("faq_form.html", pregunta=pregunta)
    finally:
        cur.close()
        conn.close()

@app.route("/admin/faq/eliminar/<int:id_p>", methods=["POST"])
@admin_required
def faq_eliminar(id_p):
    conn = get_connection()
    cur = conn.cursor()
    try:
        institucion = obtener_institucion(cur)
        iid = institucion["id_institucion"]
        cur.execute("DELETE FROM faq_institucional WHERE id_faq=%s AND id_institucion=%s", (id_p, iid))
        conn.commit()
        flash("🗑️ Pregunta eliminada", "info")
        return redirect(url_for("admin_faq"))
    finally:
        cur.close()
        conn.close()

# ========== FAQ PÚBLICO (lo ven TODOS sin iniciar sesión) ==========
@app.route("/preguntas-frecuentes")
def preguntas_frecuentes():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        iid = institucion["id_institucion"]
        cur.execute("SELECT * FROM faq_institucional WHERE id_institucion = %s AND visible = TRUE ORDER BY categoria, orden_visual, id_faq", (iid,))
        preguntas = cur.fetchall()
        # Agrupamos por categorías para que se vean organizadas
        categorias = {}
        for p in preguntas:
            cat = p["categoria"] or "GENERAL"
            if cat not in categorias:
                categorias[cat] = []
            categorias[cat].append(p)
        return render_template("faq.html", categorias=categorias, institucion=institucion)
    finally:
        cur.close()
        conn.close()
# ========== PÁGINA SIAN ==========
@app.route("/sian")
def sian():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        institucion = obtener_institucion(cur)
        return render_template("sian.html", institucion=institucion)
    finally:
        cur.close()
        conn.close()
if __name__ == "__main__":
    app.run(debug=True)