SET client_encoding = 'UTF8';
SET TIME ZONE 'America/Bogota';

BEGIN;

-- ============================================================================
-- 1. LIMPIEZA DE LA BASE AVANZADA
--    Se incluyen las 25 tablas detectadas en el respaldo avanzado.
-- ============================================================================
DROP TABLE IF EXISTS asistente_mensaje CASCADE;
DROP TABLE IF EXISTS asistente_conversacion CASCADE;
DROP TABLE IF EXISTS faq_institucional CASCADE;
DROP TABLE IF EXISTS ejecucion_automatizacion CASCADE;
DROP TABLE IF EXISTS ia_interaccion CASCADE;
DROP TABLE IF EXISTS analitica_evento CASCADE;
DROP TABLE IF EXISTS automatizacion CASCADE;
DROP TABLE IF EXISTS auditoria_admin CASCADE;
DROP TABLE IF EXISTS acceso_portal CASCADE;
DROP TABLE IF EXISTS documento_institucional CASCADE;
DROP TABLE IF EXISTS evento_calendario CASCADE;
DROP TABLE IF EXISTS video_galeria CASCADE;
DROP TABLE IF EXISTS resultado_saber11 CASCADE;
DROP TABLE IF EXISTS promocion_grado11 CASCADE;

DROP TABLE IF EXISTS imagen_galeria CASCADE;
DROP TABLE IF EXISTS galeria CASCADE;
DROP TABLE IF EXISTS noticia CASCADE;
DROP TABLE IF EXISTS mensaje_contacto CASCADE;
DROP TABLE IF EXISTS docente CASCADE;
DROP TABLE IF EXISTS administrativo CASCADE;
DROP TABLE IF EXISTS red_social CASCADE;
DROP TABLE IF EXISTS logro CASCADE;
DROP TABLE IF EXISTS seccion CASCADE;
DROP TABLE IF EXISTS contacto_institucional CASCADE;
DROP TABLE IF EXISTS institucion CASCADE;

-- ============================================================================
-- 2. ESQUEMA EXACTO ACUMULADO HASTA E9 · 11 TABLAS
-- ============================================================================

-- TABLA 1: INSTITUCION
CREATE TABLE institucion (
    id_institucion INTEGER GENERATED ALWAYS AS IDENTITY,
    nombre VARCHAR(150) NOT NULL,
    mision TEXT NOT NULL,
    vision TEXT NOT NULL,
    descripcion_general TEXT,
    CONSTRAINT pk_institucion PRIMARY KEY (id_institucion)
);

-- TABLA 2: CONTACTO_INSTITUCIONAL
CREATE TABLE contacto_institucional (
    id_contacto_inst INTEGER GENERATED ALWAYS AS IDENTITY,
    id_institucion INTEGER NOT NULL,
    telefono VARCHAR(30) NOT NULL,
    correo VARCHAR(150) NOT NULL,
    direccion VARCHAR(200) NOT NULL,
    horario_atencion VARCHAR(150),
    CONSTRAINT pk_contacto_institucional PRIMARY KEY (id_contacto_inst),
    CONSTRAINT fk_contacto_institucion FOREIGN KEY (id_institucion)
        REFERENCES institucion(id_institucion) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT uq_contacto_institucion UNIQUE (id_institucion),
    CONSTRAINT uq_contacto_correo UNIQUE (correo)
);

-- TABLA 3: SECCION
CREATE TABLE seccion (
    id_seccion INTEGER GENERATED ALWAYS AS IDENTITY,
    id_institucion INTEGER NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    orden_menu INTEGER NOT NULL,
    visible BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_seccion PRIMARY KEY (id_seccion),
    CONSTRAINT fk_seccion_institucion FOREIGN KEY (id_institucion)
        REFERENCES institucion(id_institucion) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT ck_seccion_orden CHECK (orden_menu > 0)
);

-- TABLA 4: NOTICIA · esquema E9
CREATE TABLE noticia (
    id_noticia INTEGER GENERATED ALWAYS AS IDENTITY,
    id_institucion INTEGER NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    resumen TEXT NOT NULL,
    fecha_publicacion DATE NOT NULL DEFAULT CURRENT_DATE,
    estado VARCHAR(20) NOT NULL DEFAULT 'PUBLICADA',
    contenido TEXT,
    tipo_contenido VARCHAR(20) DEFAULT 'NOTICIA',
    imagen_url VARCHAR(500),
    video_url VARCHAR(500),
    destacada BOOLEAN DEFAULT FALSE,
    orden_destacado INTEGER DEFAULT 999,
    creado_por_id INTEGER,
    ultimo_editor_id INTEGER,
    aprobado_por_id INTEGER,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_aprobacion TIMESTAMP,
    CONSTRAINT pk_noticia PRIMARY KEY (id_noticia),
    CONSTRAINT fk_noticia_institucion FOREIGN KEY (id_institucion)
        REFERENCES institucion(id_institucion) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT chk_noticia_estado_editorial
        CHECK (estado IN ('BORRADOR','REVISION','PUBLICADA','ARCHIVADA'))
);

-- TABLA 5: LOGRO
CREATE TABLE logro (
    id_logro INTEGER GENERATED ALWAYS AS IDENTITY,
    id_institucion INTEGER NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT NOT NULL,
    fecha_logro DATE,
    categoria VARCHAR(100),
    CONSTRAINT pk_logro PRIMARY KEY (id_logro),
    CONSTRAINT fk_logro_institucion FOREIGN KEY (id_institucion)
        REFERENCES institucion(id_institucion) ON UPDATE CASCADE ON DELETE CASCADE
);

-- TABLA 6: RED_SOCIAL
CREATE TABLE red_social (
    id_red INTEGER GENERATED ALWAYS AS IDENTITY,
    id_institucion INTEGER NOT NULL,
    plataforma VARCHAR(60) NOT NULL,
    url_enlace VARCHAR(500) NOT NULL,
    icono VARCHAR(150),
    CONSTRAINT pk_red_social PRIMARY KEY (id_red),
    CONSTRAINT fk_red_social_institucion FOREIGN KEY (id_institucion)
        REFERENCES institucion(id_institucion) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT uq_red_social UNIQUE (id_institucion, plataforma)
);

-- TABLA 7: GALERIA
CREATE TABLE galeria (
    id_galeria INTEGER GENERATED ALWAYS AS IDENTITY,
    id_institucion INTEGER NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT,
    tipo VARCHAR(80),
    CONSTRAINT pk_galeria PRIMARY KEY (id_galeria),
    CONSTRAINT fk_galeria_institucion FOREIGN KEY (id_institucion)
        REFERENCES institucion(id_institucion) ON UPDATE CASCADE ON DELETE CASCADE
);

-- TABLA 8: IMAGEN_GALERIA
CREATE TABLE imagen_galeria (
    id_imagen INTEGER GENERATED ALWAYS AS IDENTITY,
    id_galeria INTEGER NOT NULL,
    url_imagen VARCHAR(500) NOT NULL,
    pie_foto VARCHAR(250),
    fecha_carga TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_imagen_galeria PRIMARY KEY (id_imagen),
    CONSTRAINT fk_imagen_galeria FOREIGN KEY (id_galeria)
        REFERENCES galeria(id_galeria) ON UPDATE CASCADE ON DELETE CASCADE
);

-- TABLA 9: MENSAJE_CONTACTO
CREATE TABLE mensaje_contacto (
    id_mensaje INTEGER GENERATED ALWAYS AS IDENTITY,
    id_institucion INTEGER NOT NULL,
    nombre_remitente VARCHAR(150) NOT NULL,
    correo_remitente VARCHAR(150) NOT NULL,
    asunto VARCHAR(200) NOT NULL,
    mensaje TEXT NOT NULL,
    fecha_envio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(25) NOT NULL DEFAULT 'PENDIENTE',
    CONSTRAINT pk_mensaje_contacto PRIMARY KEY (id_mensaje),
    CONSTRAINT fk_mensaje_institucion FOREIGN KEY (id_institucion)
        REFERENCES institucion(id_institucion) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT ck_mensaje_estado CHECK (estado IN ('PENDIENTE','LEIDO','RESPONDIDO','ARCHIVADO'))
);

-- TABLA 10: DOCENTE · ampliada en E8
CREATE TABLE docente (
    id_docente INTEGER GENERATED ALWAYS AS IDENTITY,
    id_institucion INTEGER NOT NULL,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    cargo VARCHAR(120) NOT NULL,
    correo VARCHAR(150),
    area VARCHAR(120),
    foto_url VARCHAR(500),
    biografia TEXT,
    formacion VARCHAR(300),
    anios_experiencia INTEGER,
    orden_visual INTEGER DEFAULT 100,
    visible BOOLEAN DEFAULT TRUE,
    CONSTRAINT pk_docente PRIMARY KEY (id_docente),
    CONSTRAINT fk_docente_institucion FOREIGN KEY (id_institucion)
        REFERENCES institucion(id_institucion) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT uq_docente_correo UNIQUE (correo)
);

-- TABLA 11: ADMINISTRATIVO · ampliada en E8
CREATE TABLE administrativo (
    id_administrativo INTEGER GENERATED ALWAYS AS IDENTITY,
    id_institucion INTEGER NOT NULL,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    cargo VARCHAR(120) NOT NULL,
    correo VARCHAR(150),
    dependencia VARCHAR(120),
    foto_url VARCHAR(500),
    biografia TEXT,
    formacion VARCHAR(300),
    orden_visual INTEGER DEFAULT 100,
    visible BOOLEAN DEFAULT TRUE,
    usuario_web VARCHAR(80),
    password_hash VARCHAR(300),
    rol_web VARCHAR(40) DEFAULT 'EDITOR',
    activo_web BOOLEAN DEFAULT FALSE,
    CONSTRAINT pk_administrativo PRIMARY KEY (id_administrativo),
    CONSTRAINT fk_administrativo_institucion FOREIGN KEY (id_institucion)
        REFERENCES institucion(id_institucion) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT uq_administrativo_correo UNIQUE (correo)
);

-- Relaciones editoriales añadidas en E9
ALTER TABLE noticia
    ADD CONSTRAINT noticia_creado_por_id_fkey
    FOREIGN KEY (creado_por_id) REFERENCES administrativo(id_administrativo) ON DELETE SET NULL;
ALTER TABLE noticia
    ADD CONSTRAINT noticia_ultimo_editor_id_fkey
    FOREIGN KEY (ultimo_editor_id) REFERENCES administrativo(id_administrativo) ON DELETE SET NULL;
ALTER TABLE noticia
    ADD CONSTRAINT noticia_aprobado_por_id_fkey
    FOREIGN KEY (aprobado_por_id) REFERENCES administrativo(id_administrativo) ON DELETE SET NULL;

-- Índices acumulados E1-E9
CREATE INDEX idx_seccion_institucion ON seccion(id_institucion);
CREATE INDEX idx_noticia_institucion ON noticia(id_institucion);
CREATE INDEX idx_noticia_fecha ON noticia(fecha_publicacion);
CREATE INDEX idx_logro_institucion ON logro(id_institucion);
CREATE INDEX idx_red_social_institucion ON red_social(id_institucion);
CREATE INDEX idx_galeria_institucion ON galeria(id_institucion);
CREATE INDEX idx_imagen_galeria ON imagen_galeria(id_galeria);
CREATE INDEX idx_mensaje_institucion ON mensaje_contacto(id_institucion);
CREATE INDEX idx_mensaje_estado ON mensaje_contacto(estado);
CREATE INDEX idx_docente_institucion ON docente(id_institucion);
CREATE INDEX idx_administrativo_institucion ON administrativo(id_institucion);
CREATE UNIQUE INDEX uq_administrativo_usuario_web
    ON administrativo (LOWER(usuario_web))
    WHERE usuario_web IS NOT NULL;

-- ============================================================================
-- 3. DATOS ACUMULADOS HASTA E9
--    Se conservan los identificadores y valores del respaldo suministrado.
-- ============================================================================

-- INSTITUCION · 1 registro(s)
INSERT INTO institucion (id_institucion, nombre, mision, vision, descripcion_general) OVERRIDING SYSTEM VALUE VALUES (1, 'Institución Educativa Distrital Santa Magdalena Sofía', 'Formar estudiantes íntegros, autónomos y comprometidos con su entorno, fortaleciendo sus capacidades académicas, humanas, ciudadanas y tecnológicas mediante experiencias de aprendizaje pertinentes y una convivencia basada en el respeto.', 'Consolidarnos como una institución educativa distrital reconocida en Barranquilla por la calidad de sus procesos formativos, la innovación, la participación de la comunidad y la preparación de estudiantes capaces de aportar positivamente a la sociedad.', 'La Institución Educativa Distrital Santa Magdalena Sofía, ubicada en Barranquilla, orienta su labor a una formación integral y a una comunicación cercana con estudiantes, familias, docentes y comunidad.');

-- CONTACTO_INSTITUCIONAL · 1 registro(s)
INSERT INTO contacto_institucional (id_contacto_inst, id_institucion, telefono, correo, direccion, horario_atencion) OVERRIDING SYSTEM VALUE VALUES (1, 1, '(605) 000 0000', 'contacto@santamagdalenasofia.edu.co', 'Calle 84B #76-82, Barranquilla, Atlántico', 'Lunes a viernes · 7:00 a. m. - 4:00 p. m.');

-- SECCION · 14 registro(s)
INSERT INTO seccion (id_seccion, id_institucion, nombre, descripcion, orden_menu, visible) OVERRIDING SYSTEM VALUE VALUES (1, 1, 'Calendario Institucional', 'Consulta actividades, jornadas, encuentros y fechas relevantes del colegio.', 2, true);
INSERT INTO seccion (id_seccion, id_institucion, nombre, descripcion, orden_menu, visible) OVERRIDING SYSTEM VALUE VALUES (2, 1, 'Proyectos e Innovación', 'Espacio para visibilizar iniciativas pedagógicas, tecnológicas, culturales y ambientales.', 3, true);
INSERT INTO seccion (id_seccion, id_institucion, nombre, descripcion, orden_menu, visible) OVERRIDING SYSTEM VALUE VALUES (3, 1, 'Nuestra Institución', 'Conoce la identidad, principios y propósito de la comunidad educativa.', 1, true);
INSERT INTO seccion (id_seccion, id_institucion, nombre, descripcion, orden_menu, visible) OVERRIDING SYSTEM VALUE VALUES (4, 1, 'Comunidad Educativa', 'Información de interés para estudiantes, familias, docentes y personal institucional.', 4, true);
INSERT INTO seccion (id_seccion, id_institucion, nombre, descripcion, orden_menu, visible) OVERRIDING SYSTEM VALUE VALUES (5, 1, 'Gobierno escolar', 'Descripción de los espacios de participación y representación de estudiantes, familias, docentes y directivos.', 10, true);
INSERT INTO seccion (id_seccion, id_institucion, nombre, descripcion, orden_menu, visible) OVERRIDING SYSTEM VALUE VALUES (6, 1, 'Participación de las familias', 'Orientaciones y espacios para fortalecer el vínculo entre la institución, madres, padres, acudientes y cuidadores.', 14, true);
INSERT INTO seccion (id_seccion, id_institucion, nombre, descripcion, orden_menu, visible) OVERRIDING SYSTEM VALUE VALUES (7, 1, 'Convivencia escolar', 'Información de orientación sobre convivencia, participación, acuerdos institucionales y construcción de ambientes respetuosos.', 9, true);
INSERT INTO seccion (id_seccion, id_institucion, nombre, descripcion, orden_menu, visible) OVERRIDING SYSTEM VALUE VALUES (8, 1, 'Horizonte institucional', 'Principios, valores, objetivos y referentes que orientan las decisiones pedagógicas y la vida institucional.', 7, true);
INSERT INTO seccion (id_seccion, id_institucion, nombre, descripcion, orden_menu, visible) OVERRIDING SYSTEM VALUE VALUES (9, 1, 'Proyecto Educativo Institucional', 'Presentación general del PEI y de los componentes que orientan la propuesta formativa y el mejoramiento institucional.', 8, true);
INSERT INTO seccion (id_seccion, id_institucion, nombre, descripcion, orden_menu, visible) OVERRIDING SYSTEM VALUE VALUES (10, 1, 'Historia y trayectoria', 'Recorrido por los principales momentos, procesos y transformaciones que han construido la identidad de la institución en Barranquilla.', 5, true);
INSERT INTO seccion (id_seccion, id_institucion, nombre, descripcion, orden_menu, visible) OVERRIDING SYSTEM VALUE VALUES (11, 1, 'Servicios a la comunidad', 'Acceso organizado a información útil, trámites, canales y servicios institucionales de interés para estudiantes y familias.', 12, true);
INSERT INTO seccion (id_seccion, id_institucion, nombre, descripcion, orden_menu, visible) OVERRIDING SYSTEM VALUE VALUES (12, 1, 'Bienestar y orientación', 'Información sobre acciones de acompañamiento, bienestar, orientación y apoyo disponibles para la comunidad educativa.', 11, true);
INSERT INTO seccion (id_seccion, id_institucion, nombre, descripcion, orden_menu, visible) OVERRIDING SYSTEM VALUE VALUES (13, 1, 'Proyectos pedagógicos', 'Visibilización de iniciativas académicas, culturales, ambientales, ciudadanas, tecnológicas y de innovación desarrolladas en la institución.', 13, true);
INSERT INTO seccion (id_seccion, id_institucion, nombre, descripcion, orden_menu, visible) OVERRIDING SYSTEM VALUE VALUES (14, 1, 'Símbolos institucionales', 'Espacio para presentar emblema, colores, lema y demás elementos que fortalecen el sentido de pertenencia de la comunidad educativa.', 6, true);

-- LOGRO · 12 registro(s)
INSERT INTO logro (id_logro, id_institucion, titulo, descripcion, fecha_logro, categoria) OVERRIDING SYSTEM VALUE VALUES (1, 1, 'Fortalecimiento de la identidad institucional', 'Logro de prueba relacionado con acciones que promueven participación, pertenencia y convivencia escolar.', '2026-07-04', 'Institucional');
INSERT INTO logro (id_logro, id_institucion, titulo, descripcion, fecha_logro, categoria) OVERRIDING SYSTEM VALUE VALUES (2, 1, 'Participación destacada en proyectos de innovación', 'Reconocimiento de prueba para visibilizar el trabajo colaborativo y creativo desarrollado por estudiantes.', '2026-07-29', 'Innovación');
INSERT INTO logro (id_logro, id_institucion, titulo, descripcion, fecha_logro, categoria) OVERRIDING SYSTEM VALUE VALUES (3, 1, 'Reconocimiento a proyectos de innovación escolar', 'Experiencias desarrolladas por estudiantes fueron destacadas por integrar creatividad, pensamiento tecnológico y solución de situaciones del contexto educativo.', '2026-08-16', 'Innovación y Tecnología');
INSERT INTO logro (id_logro, id_institucion, titulo, descripcion, fecha_logro, categoria) OVERRIDING SYSTEM VALUE VALUES (4, 1, 'Experiencia significativa en pensamiento computacional', 'Actividades de lógica, programación y creación digital permitieron fortalecer habilidades para resolver problemas mediante herramientas tecnológicas.', '2026-07-06', 'Innovación y Tecnología');
INSERT INTO logro (id_logro, id_institucion, titulo, descripcion, fecha_logro, categoria) OVERRIDING SYSTEM VALUE VALUES (5, 1, 'Participación sobresaliente en jornada deportiva escolar', 'Los equipos estudiantiles representaron a la institución con disciplina, trabajo colectivo, juego limpio y sentido de pertenencia.', '2026-07-12', 'Deportivo');
INSERT INTO logro (id_logro, id_institucion, titulo, descripcion, fecha_logro, categoria) OVERRIDING SYSTEM VALUE VALUES (6, 1, 'Reconocimiento por prácticas de convivencia escolar', 'La comunidad educativa fue destacada por desarrollar acciones pedagógicas orientadas al respeto, el diálogo y la construcción de ambientes protectores.', '2026-07-30', 'Convivencia');
INSERT INTO logro (id_logro, id_institucion, titulo, descripcion, fecha_logro, categoria) OVERRIDING SYSTEM VALUE VALUES (7, 1, 'Destacada participación en encuentro de lectura', 'Estudiantes representaron a la institución en actividades de lectura, oralidad y producción textual, fortaleciendo sus competencias comunicativas.', '2026-08-10', 'Académico');
INSERT INTO logro (id_logro, id_institucion, titulo, descripcion, fecha_logro, categoria) OVERRIDING SYSTEM VALUE VALUES (8, 1, 'Avances en liderazgo y participación estudiantil', 'Las iniciativas promovidas por representantes estudiantiles fortalecieron la participación democrática, la comunicación y el sentido de pertenencia.', '2026-08-05', 'Liderazgo');
INSERT INTO logro (id_logro, id_institucion, titulo, descripcion, fecha_logro, categoria) OVERRIDING SYSTEM VALUE VALUES (9, 1, 'Reconocimiento al compromiso académico y la constancia', 'Estudiantes con procesos de mejora sostenida fueron reconocidos por su responsabilidad, perseverancia y disposición para aprender.', '2026-06-28', 'Académico');
INSERT INTO logro (id_logro, id_institucion, titulo, descripcion, fecha_logro, categoria) OVERRIDING SYSTEM VALUE VALUES (10, 1, 'Fortalecimiento del vínculo entre familias y escuela', 'La participación activa de las familias en jornadas de acompañamiento y orientación fue reconocida como un aporte al bienestar y permanencia escolar.', '2026-06-20', 'Comunidad');
INSERT INTO logro (id_logro, id_institucion, titulo, descripcion, fecha_logro, categoria) OVERRIDING SYSTEM VALUE VALUES (11, 1, 'Talento artístico destacado en muestra institucional', 'Estudiantes demostraron creatividad y compromiso en presentaciones de música, artes visuales y expresión corporal realizadas para la comunidad.', '2026-07-18', 'Cultura y Arte');
INSERT INTO logro (id_logro, id_institucion, titulo, descripcion, fecha_logro, categoria) OVERRIDING SYSTEM VALUE VALUES (12, 1, 'Proyecto ambiental escolar con impacto comunitario', 'Una iniciativa de cuidado ambiental promovió separación de residuos, recuperación de espacios y sensibilización sobre hábitos sostenibles.', '2026-07-24', 'Ambiental');

-- RED_SOCIAL · 5 registro(s)
INSERT INTO red_social (id_red, id_institucion, plataforma, url_enlace, icono) OVERRIDING SYSTEM VALUE VALUES (1, 1, 'Sitio Web Institucional', 'https://iedsantamagdalenasofia.edu.co/', 'bi-globe2');
INSERT INTO red_social (id_red, id_institucion, plataforma, url_enlace, icono) OVERRIDING SYSTEM VALUE VALUES (2, 1, 'Google Maps', 'https://www.google.com/maps/search/?api=1&query=Instituci%C3%B3n+Educativa+Distrital+Santa+Magdalena+Sof%C3%ADa%2C+Calle+84B+76-82%2C+Barranquilla', 'bi-geo-alt-fill');
INSERT INTO red_social (id_red, id_institucion, plataforma, url_enlace, icono) OVERRIDING SYSTEM VALUE VALUES (3, 1, 'Waze', 'https://www.waze.com/live-map/directions/co/atlantico/barranquilla/educational-institution-santa-magdalena-sofia?to=place.ChIJH1ENhsAt9I4R6mCS3Il4YBE', 'bi-signpost-2-fill');
INSERT INTO red_social (id_red, id_institucion, plataforma, url_enlace, icono) OVERRIDING SYSTEM VALUE VALUES (4, 1, 'Instagram Institucional', 'https://www.instagram.com/iedsantamagdalenas/', 'bi-instagram');
INSERT INTO red_social (id_red, id_institucion, plataforma, url_enlace, icono) OVERRIDING SYSTEM VALUE VALUES (5, 1, 'Facebook Institucional', 'https://www.facebook.com/cdsantamagdalenasofiab/', 'bi-facebook');

-- GALERIA · 2 registro(s)
INSERT INTO galeria (id_galeria, id_institucion, nombre, descripcion, tipo) OVERRIDING SYSTEM VALUE VALUES (1, 1, 'Comunidad, arte y bienestar', 'Imágenes de actividades culturales, deportivas y de participación de las familias que fortalecen la convivencia y el sentido de pertenencia.', 'Comunidad');
INSERT INTO galeria (id_galeria, id_institucion, nombre, descripcion, tipo) OVERRIDING SYSTEM VALUE VALUES (2, 1, 'Experiencias que nos inspiran', 'Una colección de momentos académicos, tecnológicos, ambientales y de liderazgo que reflejan el aprendizaje activo de nuestros estudiantes.', 'Académica');

-- IMAGEN_GALERIA · 8 registro(s)
INSERT INTO imagen_galeria (id_imagen, id_galeria, url_imagen, pie_foto, fecha_carga) OVERRIDING SYSTEM VALUE VALUES (1, 1, '/static/img/galeria/liderazgo.svg', 'Liderazgo estudiantil: voces que participan y construyen comunidad.', '2026-08-11 09:40:00');
INSERT INTO imagen_galeria (id_imagen, id_galeria, url_imagen, pie_foto, fecha_carga) OVERRIDING SYSTEM VALUE VALUES (2, 1, '/static/img/galeria/familias.svg', 'Familias y escuela: acompañamiento que fortalece los procesos educativos.', '2026-08-12 16:10:00');
INSERT INTO imagen_galeria (id_imagen, id_galeria, url_imagen, pie_foto, fecha_carga) OVERRIDING SYSTEM VALUE VALUES (3, 1, '/static/img/galeria/deporte.svg', 'Deporte y bienestar: disciplina, trabajo en equipo y sana convivencia.', '2026-08-13 15:20:00');
INSERT INTO imagen_galeria (id_imagen, id_galeria, url_imagen, pie_foto, fecha_carga) OVERRIDING SYSTEM VALUE VALUES (4, 1, '/static/img/galeria/arte.svg', 'Arte y cultura: talento, creatividad y expresión estudiantil.', '2026-08-14 14:00:00');
INSERT INTO imagen_galeria (id_imagen, id_galeria, url_imagen, pie_foto, fecha_carga) OVERRIDING SYSTEM VALUE VALUES (5, 2, '/static/img/galeria/tecnologia.svg', 'Tecnología y pensamiento computacional para aprender creando.', '2026-08-15 11:15:00');
INSERT INTO imagen_galeria (id_imagen, id_galeria, url_imagen, pie_foto, fecha_carga) OVERRIDING SYSTEM VALUE VALUES (6, 2, '/static/img/galeria/ambiente.svg', 'Ambiente escolar: acciones para cuidar los espacios que compartimos.', '2026-08-16 08:45:00');
INSERT INTO imagen_galeria (id_imagen, id_galeria, url_imagen, pie_foto, fecha_carga) OVERRIDING SYSTEM VALUE VALUES (7, 2, '/static/img/galeria/lectura.svg', 'Lectura y expresión: palabras que conectan a nuestra comunidad.', '2026-08-17 10:30:00');
INSERT INTO imagen_galeria (id_imagen, id_galeria, url_imagen, pie_foto, fecha_carga) OVERRIDING SYSTEM VALUE VALUES (8, 2, '/static/img/galeria/ciencia.svg', 'Ciencia e innovación: aprender investigando y creando soluciones.', '2026-08-18 09:00:00');

-- MENSAJE_CONTACTO · 15 registro(s)
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (1, 1, 'José Ricardo Torres', 'jose.torres@example.com', 'Galería institucional', 'Me gustaría consultar las actividades culturales y deportivas publicadas en la galería.', '2026-08-18 11:20:00', 'RESPONDIDO');
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (2, 1, 'Diana Martínez', 'diana.martinez@example.com', 'Actividades para familias', 'Quisiera conocer próximos espacios de participación dirigidos a padres y acudientes.', '2026-08-18 10:05:00', 'PENDIENTE');
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (3, 1, 'Laura Gómez', 'laura.gomez@example.com', 'Redes institucionales', 'Solicito confirmar cuáles son las redes oficiales de la institución para seguir las novedades.', '2026-08-18 13:40:00', 'PENDIENTE');
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (4, 1, 'Carlos Andrés Pérez', 'carlos.perez@example.com', 'Ubicación de la sede', 'Agradezco información para llegar a la sede principal desde el centro de Barranquilla.', '2026-08-18 09:15:00', 'LEIDO');
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (5, 1, 'María Fernanda López', 'maria.lopez@example.com', 'Información institucional', 'Deseo conocer los canales oficiales para consultar información y actividades del colegio.', '2026-08-18 08:30:00', 'PENDIENTE');
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (6, 1, 'Ricardo Salas', 'ricardo.salas@example.com', 'Consulta de noticias', 'Quisiera confirmar dónde puedo encontrar las noticias y novedades más recientes del colegio.', '2026-08-18 16:15:00', 'ARCHIVADO');
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (7, 1, 'Miguel Ángel Castro', 'miguel.castro@example.com', 'Información sobre proyectos pedagógicos', 'Quisiera conocer qué proyectos pedagógicos se encuentran activos y cómo participa la comunidad educativa.', '2026-08-18 14:35:00', 'LEIDO');
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (8, 1, 'Natalia Herrera', 'natalia.herrera@example.com', 'Orientación para acudientes', 'Solicito información sobre los canales de orientación disponibles para madres, padres y acudientes.', '2026-08-18 15:00:00', 'PENDIENTE');
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (9, 1, 'Andrea Rodríguez', 'andrea.rodriguez@example.com', 'Consulta sobre jornada escolar', 'Deseo conocer información general sobre los horarios y la organización de la jornada escolar.', '2026-08-18 14:10:00', 'PENDIENTE');
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (10, 1, 'Felipe Torres', 'felipe.torres@example.com', 'Reconocimientos institucionales', 'Quisiera consultar los logros y reconocimientos que han sido publicados recientemente por la institución.', '2026-08-18 17:55:00', 'PENDIENTE');
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (11, 1, 'Samuel Gómez', 'samuel.gomez@example.com', 'Ubicación y cómo llegar', 'Necesito la ubicación exacta de la institución y un enlace para calcular la ruta desde mi sector.', '2026-08-18 17:05:00', 'RESPONDIDO');
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (12, 1, 'Vanessa Díaz', 'vanessa.diaz@example.com', 'Galería institucional', 'Solicito orientación para encontrar las imágenes de actividades ambientales y académicas realizadas por estudiantes.', '2026-08-18 16:40:00', 'LEIDO');
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (13, 1, 'Jorge Luis Martínez', 'jorge.martinez@example.com', 'Actividades culturales', 'Me gustaría saber dónde consultar las próximas actividades culturales y artísticas de la institución.', '2026-08-18 15:25:00', 'RESPONDIDO');
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (14, 1, 'Carolina Pacheco', 'carolina.pacheco@example.com', 'Participación de las familias', 'Deseo conocer los espacios disponibles para que las familias participen en actividades institucionales.', '2026-08-18 17:30:00', 'PENDIENTE');
INSERT INTO mensaje_contacto (id_mensaje, id_institucion, nombre_remitente, correo_remitente, asunto, mensaje, fecha_envio, estado) OVERRIDING SYSTEM VALUE VALUES (15, 1, 'Paola Mendoza', 'paola.mendoza@example.com', 'Información de convivencia escolar', 'Deseo consultar información general sobre las estrategias institucionales de convivencia y buen trato.', '2026-08-18 15:50:00', 'PENDIENTE');

-- DOCENTE · 6 registro(s)
INSERT INTO docente (id_docente, id_institucion, nombres, apellidos, cargo, correo, area, foto_url, biografia, formacion, anios_experiencia, orden_visual, visible) OVERRIDING SYSTEM VALUE VALUES (1, 1, 'Ana Lucía', 'Torres Molina', 'Docente de Matemáticas', 'ana.torres.demo@santamagdalenasofia.edu.co', 'Matemáticas', '/static/img/personal/doc_matematicas.svg', 'Acompaña el desarrollo del pensamiento lógico, la resolución de problemas y la argumentación matemática mediante experiencias cercanas al contexto estudiantil.', 'Licenciatura en Matemáticas', 12, 10, true);
INSERT INTO docente (id_docente, id_institucion, nombres, apellidos, cargo, correo, area, foto_url, biografia, formacion, anios_experiencia, orden_visual, visible) OVERRIDING SYSTEM VALUE VALUES (2, 1, 'Jorge Eliécer', 'Romero Díaz', 'Docente de Ciencias Naturales', 'jorge.romero.demo@santamagdalenasofia.edu.co', 'Ciencias Naturales', '/static/img/personal/doc_ciencias.svg', 'Promueve la curiosidad científica, la observación y la comprensión del entorno mediante actividades de indagación y experimentación.', 'Licenciatura en Ciencias Naturales', 15, 20, true);
INSERT INTO docente (id_docente, id_institucion, nombres, apellidos, cargo, correo, area, foto_url, biografia, formacion, anios_experiencia, orden_visual, visible) OVERRIDING SYSTEM VALUE VALUES (3, 1, 'Marcela', 'Gómez Pacheco', 'Docente de Lengua Castellana', 'marcela.gomez.demo@santamagdalenasofia.edu.co', 'Lengua Castellana', '/static/img/personal/doc_lengua.svg', 'Fortalece lectura, escritura, oralidad y pensamiento crítico a través de experiencias comunicativas y proyectos de aula.', 'Licenciatura en Lengua Castellana', 11, 30, true);
INSERT INTO docente (id_docente, id_institucion, nombres, apellidos, cargo, correo, area, foto_url, biografia, formacion, anios_experiencia, orden_visual, visible) OVERRIDING SYSTEM VALUE VALUES (4, 1, 'Luis Fernando', 'Álvarez Peña', 'Docente de Tecnología e Informática', 'luis.alvarez.demo@santamagdalenasofia.edu.co', 'Tecnología e Informática', '/static/img/personal/doc_tecnologia.svg', 'Integra pensamiento computacional, creación digital y uso responsable de tecnología para resolver situaciones del contexto escolar.', 'Licenciatura en Informática y Tecnología', 9, 40, true);
INSERT INTO docente (id_docente, id_institucion, nombres, apellidos, cargo, correo, area, foto_url, biografia, formacion, anios_experiencia, orden_visual, visible) OVERRIDING SYSTEM VALUE VALUES (5, 1, 'Camila', 'Rodríguez Salcedo', 'Docente de Inglés', 'camila.rodriguez.demo@santamagdalenasofia.edu.co', 'Inglés', '/static/img/personal/doc_ingles.svg', 'Impulsa competencias comunicativas en lengua extranjera mediante actividades participativas y situaciones auténticas de comunicación.', 'Licenciatura en Lenguas Extranjeras', 8, 50, true);
INSERT INTO docente (id_docente, id_institucion, nombres, apellidos, cargo, correo, area, foto_url, biografia, formacion, anios_experiencia, orden_visual, visible) OVERRIDING SYSTEM VALUE VALUES (6, 1, 'Hernando', 'Pérez Castillo', 'Docente de Educación Física', 'hernando.perez.demo@santamagdalenasofia.edu.co', 'Educación Física', '/static/img/personal/doc_deporte.svg', 'Promueve hábitos saludables, trabajo en equipo, disciplina y bienestar mediante experiencias deportivas y recreativas.', 'Licenciatura en Educación Física', 14, 60, true);

-- ADMINISTRATIVO · 4 registro(s)
INSERT INTO administrativo (id_administrativo, id_institucion, nombres, apellidos, cargo, correo, dependencia, foto_url, biografia, formacion, orden_visual, visible, usuario_web, password_hash, rol_web, activo_web) OVERRIDING SYSTEM VALUE VALUES (1, 1, 'Laura Marcela', 'Ríos Mendoza', 'Rectora', 'rectoria.demo@santamagdalenasofia.edu.co', 'Rectoría', '/static/img/personal/rectoria.svg', 'Orienta la gestión institucional y promueve el trabajo articulado entre estudiantes, familias, docentes y equipos de apoyo.', 'Dirección y gestión educativa', 1, true, 'rectoria.sms', 'pbkdf2_sha256$260000$3c327de8da14d39d7a7b18a9e55ba498$a4aff5c542117b6c248345082d4991d0f16765cf4473bb7825735fddd3f759c0', 'RECTORIA', true);
INSERT INTO administrativo (id_administrativo, id_institucion, nombres, apellidos, cargo, correo, dependencia, foto_url, biografia, formacion, orden_visual, visible, usuario_web, password_hash, rol_web, activo_web) OVERRIDING SYSTEM VALUE VALUES (2, 1, 'Carlos Andrés', 'Mejía Torres', 'Coordinador Académico', 'coordinacion.academica.demo@santamagdalenasofia.edu.co', 'Coordinación Académica', '/static/img/personal/coord_academica.svg', 'Acompaña los procesos académicos, el seguimiento pedagógico y la articulación de estrategias para fortalecer los aprendizajes.', 'Gestión académica y pedagógica', 2, true, 'editor.sms', 'pbkdf2_sha256$260000$154d24935bd45ece719891f84a1e2b02$cf74d92d1ab172bf27c319decbf96b459449905352935ff8c7282c05c8422812', 'EDITOR', true);
INSERT INTO administrativo (id_administrativo, id_institucion, nombres, apellidos, cargo, correo, dependencia, foto_url, biografia, formacion, orden_visual, visible, usuario_web, password_hash, rol_web, activo_web) OVERRIDING SYSTEM VALUE VALUES (3, 1, 'Diana Patricia', 'Herrera Gómez', 'Coordinadora de Convivencia', 'convivencia.demo@santamagdalenasofia.edu.co', 'Coordinación de Convivencia', '/static/img/personal/coord_convivencia.svg', 'Promueve ambientes protectores, diálogo, participación y estrategias de convivencia para el bienestar de la comunidad educativa.', 'Convivencia y orientación escolar', 3, true, 'comunica.sms', 'pbkdf2_sha256$260000$2d4c0b285bc071759efb5a8d23b344fc$759f886ef4d6d354964ba98c6603c9db9be19614ac91baee4660d1a19d1fe34c', 'COMUNICACIONES', true);
INSERT INTO administrativo (id_administrativo, id_institucion, nombres, apellidos, cargo, correo, dependencia, foto_url, biografia, formacion, orden_visual, visible, usuario_web, password_hash, rol_web, activo_web) OVERRIDING SYSTEM VALUE VALUES (4, 1, 'Andrés Felipe', 'Navarro Ruiz', 'Responsable del Portal Institucional', 'portal.demo@santamagdalenasofia.edu.co', 'TIC y Comunicaciones', NULL, 'Perfil técnico encargado de administrar contenidos, imágenes y publicaciones del portal bajo autorización institucional.', 'Gestión TIC y comunicaciones institucionales', 90, false, 'admin.sms', 'pbkdf2_sha256$260000$8a5427a1308133aed38e4e658f8317ae$fbf04bc4671ee681349375f326e950826d5acc7b4ebae4abb35c5e0b8fc4e6ac', 'SUPERADMIN', true);

-- NOTICIA · 21 registro(s)
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (1, 1, 'Proyectos estudiantiles que transforman el aprendizaje', 'Estudiantes fortalecen competencias mediante iniciativas de innovación, trabajo colaborativo y apropiación de herramientas tecnológicas.', '2026-08-13', 'PUBLICADA', 'Estudiantes fortalecen competencias mediante iniciativas de innovación, trabajo colaborativo y apropiación de herramientas tecnológicas.', 'NOTICIA', NULL, NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (2, 1, 'Bienvenida a nuestra nueva presencia digital', 'La comunidad educativa cuenta con un nuevo espacio web institucional para consultar información organizada, noticias y servicios.', '2026-08-18', 'PUBLICADA', 'La comunidad educativa cuenta con un nuevo espacio web institucional para consultar información organizada, noticias y servicios.', 'NOTICIA', NULL, NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (3, 1, 'Experiencias de programación y pensamiento computacional', 'Estudiantes desarrollan actividades de programación, lógica y creación digital como parte de los procesos de fortalecimiento de competencias tecnológicas.', '2026-07-25', 'PUBLICADA', 'Estudiantes desarrollan actividades de programación, lógica y creación digital como parte de los procesos de fortalecimiento de competencias tecnológicas.', 'NOTICIA', NULL, NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (4, 1, 'Encuentro de familias y acompañamiento escolar', 'La institución fortalece el vínculo con madres, padres y acudientes mediante orientaciones sobre acompañamiento académico, convivencia y bienestar estudiantil.', '2026-08-12', 'PUBLICADA', 'La institución fortalece el vínculo con madres, padres y acudientes mediante orientaciones sobre acompañamiento académico, convivencia y bienestar estudiantil.', 'NOTICIA', NULL, NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (5, 1, 'Orientación para el proyecto de vida de los estudiantes', 'Espacios de reflexión y acompañamiento fortalecen la toma de decisiones, el reconocimiento de habilidades y la construcción de metas personales y académicas.', '2026-07-29', 'PUBLICADA', 'Espacios de reflexión y acompañamiento fortalecen la toma de decisiones, el reconocimiento de habilidades y la construcción de metas personales y académicas.', 'NOTICIA', NULL, NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (6, 1, 'Proyectos ambientales que transforman nuestros espacios', 'Iniciativas estudiantiles impulsan el cuidado del entorno, el manejo responsable de residuos y acciones de sensibilización ambiental dentro de la institución.', '2026-08-06', 'PUBLICADA', 'Iniciativas estudiantiles impulsan el cuidado del entorno, el manejo responsable de residuos y acciones de sensibilización ambiental dentro de la institución.', 'NOTICIA', NULL, NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (7, 1, 'Feria institucional de ciencia, tecnología e innovación', 'Estudiantes presentan experiencias de aula, prototipos y proyectos que integran pensamiento científico, creatividad y solución de problemas del entorno escolar.', '2026-08-18', 'PUBLICADA', 'Estudiantes presentan experiencias de aula, prototipos y proyectos que integran pensamiento científico, creatividad y solución de problemas del entorno escolar.', 'NOTICIA', NULL, NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (8, 1, 'Reconocimiento a la constancia y al compromiso académico', 'La comunidad educativa destaca el esfuerzo, la responsabilidad y la mejora continua de estudiantes que avanzan de manera significativa en su proceso formativo.', '2026-07-17', 'PUBLICADA', 'La comunidad educativa destaca el esfuerzo, la responsabilidad y la mejora continua de estudiantes que avanzan de manera significativa en su proceso formativo.', 'NOTICIA', NULL, NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (9, 1, 'Semana de la lectura y la expresión oral', 'La comunidad educativa participa en jornadas de lectura, narración, producción textual y espacios de expresión para fortalecer las competencias comunicativas.', '2026-08-15', 'PUBLICADA', 'La comunidad educativa participa en jornadas de lectura, narración, producción textual y espacios de expresión para fortalecer las competencias comunicativas.', 'NOTICIA', NULL, NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (10, 1, 'Participación estudiantil y liderazgo escolar', 'Representantes estudiantiles promueven iniciativas de participación, liderazgo, comunicación y corresponsabilidad en la vida institucional.', '2026-07-21', 'PUBLICADA', 'Representantes estudiantiles promueven iniciativas de participación, liderazgo, comunicación y corresponsabilidad en la vida institucional.', 'NOTICIA', NULL, NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (11, 1, 'Talento artístico y cultural en escena', 'Muestras de música, expresión corporal, artes visuales y creación cultural permiten reconocer el talento y la participación de los estudiantes.', '2026-08-02', 'PUBLICADA', 'Muestras de música, expresión corporal, artes visuales y creación cultural permiten reconocer el talento y la participación de los estudiantes.', 'NOTICIA', NULL, NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (12, 1, 'Jornada por la convivencia y el buen trato', 'Actividades pedagógicas promueven el respeto, la escucha, la resolución pacífica de conflictos y la construcción colectiva de ambientes escolares protectores.', '2026-08-09', 'PUBLICADA', 'Actividades pedagógicas promueven el respeto, la escucha, la resolución pacífica de conflictos y la construcción colectiva de ambientes escolares protectores.', 'NOTICIA', NULL, NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (13, 1, 'Jornada de lectura y expresión oral', 'Actividades de lectura, escritura y oralidad fortalecen la comunicación y el pensamiento crítico.', '2026-08-13', 'PUBLICADA', 'Durante la jornada se desarrollan espacios de lectura compartida, escritura creativa y expresión oral. El propósito es fortalecer competencias comunicativas y generar encuentros significativos alrededor de la palabra.', 'EVENTO', '/static/img/galeria/lectura.svg', NULL, false, 20, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', '2026-08-18 22:40:36.124893');
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (14, 1, 'Feria de ciencia e innovación: ideas que se convierten en soluciones', 'Proyectos estudiantiles integran ciencia, tecnología y creatividad para responder a situaciones del entorno escolar.', '2026-08-18', 'PUBLICADA', 'La comunidad educativa participa en una jornada de socialización de proyectos de aula, experiencias STEAM, prototipos y soluciones creadas por estudiantes. La actividad fortalece la comunicación, el pensamiento crítico, el trabajo colaborativo y la apropiación responsable de la tecnología.', 'EVENTO', '/static/img/galeria/ciencia.svg', '/static/uploads/videos/demo_feria_innovacion.mp4', true, 1, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', '2026-08-18 22:40:36.124893');
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (15, 1, 'Encuentro de familias y acompañamiento institucional', 'Borrador de una publicación relacionada con participación de las familias y acompañamiento a los procesos escolares.', '2026-08-20', 'BORRADOR', 'Contenido de prueba en estado borrador para demostrar que los editores pueden preparar información sin publicarla inmediatamente. Posteriormente puede enviarse a Rectoría para revisión.', 'EVENTO', '/static/img/galeria/familias.svg', NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (16, 1, 'Actividad deportiva para fortalecer hábitos saludables', 'La práctica deportiva se integra a experiencias de bienestar, cooperación y uso positivo del tiempo escolar.', '2026-08-09', 'PUBLICADA', 'Las actividades deportivas fomentan el trabajo en equipo, el respeto por las reglas, la disciplina y el cuidado de la salud. Esta publicación registra una experiencia de participación de la comunidad educativa.', 'EVENTO', '/static/img/galeria/deporte.svg', NULL, false, 40, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', '2026-08-18 22:40:36.124893');
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (17, 1, 'Encuentro cultural: arte, expresión y convivencia', 'Una jornada para reconocer el talento, la creatividad y la participación de estudiantes en diferentes expresiones artísticas.', '2026-08-17', 'PUBLICADA', 'El encuentro cultural reúne muestras de expresión artística, lectura, música y actividades de integración que fortalecen el sentido de pertenencia y la convivencia escolar. El registro audiovisual permite conservar y compartir estos momentos con la comunidad.', 'EVENTO', '/static/img/galeria/arte.svg', '/static/uploads/videos/demo_cultura.mp4', true, 2, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', '2026-08-18 22:40:36.124893');
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (18, 1, 'Acciones ambientales para cuidar los espacios que compartimos', 'La comunidad educativa fortalece hábitos de cuidado, reciclaje y uso responsable de los espacios institucionales.', '2026-08-15', 'PUBLICADA', 'Las acciones ambientales articulan sensibilización, clasificación de residuos, cuidado de zonas comunes y participación estudiantil. Estas experiencias buscan que el aprendizaje se traduzca en decisiones responsables dentro y fuera de la institución.', 'NOTICIA', '/static/img/galeria/ambiente.svg', NULL, true, 4, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', '2026-08-18 22:40:36.124893');
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (19, 1, 'Tecnología para aprender creando', 'Estudiantes desarrollan experiencias de pensamiento computacional y producción digital dentro de proyectos pedagógicos.', '2026-08-16', 'PUBLICADA', 'Las actividades de tecnología e informática promueven el análisis de problemas, la creación de soluciones digitales y el uso responsable de herramientas tecnológicas. Los productos desarrollados se socializan como parte del aprendizaje activo.', 'NOTICIA', '/static/img/galeria/tecnologia.svg', NULL, true, 3, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', '2026-08-18 22:40:36.124893');
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (20, 1, 'Boletín institucional de cierre de periodo', 'Contenido histórico conservado como ejemplo de una publicación archivada dentro del flujo editorial.', '2026-07-19', 'ARCHIVADA', 'Este registro demuestra que una publicación puede conservarse en el sistema sin aparecer en el portal público cuando su estado es ARCHIVADA.', 'COMUNICADO', NULL, NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);
INSERT INTO noticia (id_noticia, id_institucion, titulo, resumen, fecha_publicacion, estado, contenido, tipo_contenido, imagen_url, video_url, destacada, orden_destacado, creado_por_id, ultimo_editor_id, aprobado_por_id, fecha_actualizacion, fecha_aprobacion) OVERRIDING SYSTEM VALUE VALUES (21, 1, 'Comunicado sobre actualización de canales institucionales', 'Se prepara información para orientar a las familias sobre los canales oficiales de comunicación del colegio.', '2026-08-19', 'REVISION', 'Este contenido se encuentra en revisión editorial. Antes de hacerlo público debe validarse que los datos de contacto, enlaces y horarios correspondan a la información institucional vigente.', 'COMUNICADO', NULL, NULL, false, 999, NULL, NULL, NULL, '2026-08-18 22:40:36.124893', NULL);


-- ============================================================================
-- 4. SINCRONIZACIÓN DE IDENTIDADES
-- ============================================================================
SELECT setval(pg_get_serial_sequence('institucion','id_institucion'), COALESCE(MAX(id_institucion),1), TRUE) FROM institucion;
SELECT setval(pg_get_serial_sequence('contacto_institucional','id_contacto_inst'), COALESCE(MAX(id_contacto_inst),1), TRUE) FROM contacto_institucional;
SELECT setval(pg_get_serial_sequence('seccion','id_seccion'), COALESCE(MAX(id_seccion),1), TRUE) FROM seccion;
SELECT setval(pg_get_serial_sequence('noticia','id_noticia'), COALESCE(MAX(id_noticia),1), TRUE) FROM noticia;
SELECT setval(pg_get_serial_sequence('logro','id_logro'), COALESCE(MAX(id_logro),1), TRUE) FROM logro;
SELECT setval(pg_get_serial_sequence('red_social','id_red'), COALESCE(MAX(id_red),1), TRUE) FROM red_social;
SELECT setval(pg_get_serial_sequence('galeria','id_galeria'), COALESCE(MAX(id_galeria),1), TRUE) FROM galeria;
SELECT setval(pg_get_serial_sequence('imagen_galeria','id_imagen'), COALESCE(MAX(id_imagen),1), TRUE) FROM imagen_galeria;
SELECT setval(pg_get_serial_sequence('mensaje_contacto','id_mensaje'), COALESCE(MAX(id_mensaje),1), TRUE) FROM mensaje_contacto;
SELECT setval(pg_get_serial_sequence('docente','id_docente'), COALESCE(MAX(id_docente),1), TRUE) FROM docente;
SELECT setval(pg_get_serial_sequence('administrativo','id_administrativo'), COALESCE(MAX(id_administrativo),1), TRUE) FROM administrativo;

COMMIT;

-- ============================================================================
-- 5. VERIFICACIÓN DEL CORTE E9
--    Deben aparecer exactamente 11 filas (una por tabla de la aplicación E9).
-- ============================================================================
SELECT * FROM (
    SELECT 'institucion'::text AS tabla, COUNT(*)::bigint AS registros FROM institucion
    UNION ALL SELECT 'contacto_institucional', COUNT(*) FROM contacto_institucional
    UNION ALL SELECT 'seccion', COUNT(*) FROM seccion
    UNION ALL SELECT 'noticia', COUNT(*) FROM noticia
    UNION ALL SELECT 'logro', COUNT(*) FROM logro
    UNION ALL SELECT 'red_social', COUNT(*) FROM red_social
    UNION ALL SELECT 'galeria', COUNT(*) FROM galeria
    UNION ALL SELECT 'imagen_galeria', COUNT(*) FROM imagen_galeria
    UNION ALL SELECT 'mensaje_contacto', COUNT(*) FROM mensaje_contacto
    UNION ALL SELECT 'docente', COUNT(*) FROM docente
    UNION ALL SELECT 'administrativo', COUNT(*) FROM administrativo
) AS resumen
ORDER BY tabla;

-- RESULTADOS ESPERADOS:
-- administrativo           4
-- contacto_institucional   1
-- docente                  6
-- galeria                  2
-- imagen_galeria           8
-- institucion              1
-- logro                   12
-- mensaje_contacto        15
-- noticia                 21
-- red_social               5
-- seccion                 14
--
-- TOTAL DE TABLAS DEL ESQUEMA DE LA ENTREGA 9: 11
-- ============================================================================
