# Entrega 9 — Página Web Institucional
## IED Santa Magdalena Sofía · Barranquilla

Esta versión es **acumulativa** y conserva todo lo construido desde la Entrega 1.

## Objetivo de la Entrega 9

La Entrega 9 convierte el portal en una plataforma editorial institucional más madura:

- portada completamente renovada;
- carrusel de alto impacto basado en contenido real de PostgreSQL;
- noticias, eventos y comunicados;
- carga y publicación de videos;
- flujo editorial por roles;
- revisión antes de publicar;
- cambio de contraseña desde el panel;
- tarjetas más pequeñas, modernas y consistentes;
- eliminación de textos técnicos/por entrega en el pie público.

## 1. Nuevo inicio

Ruta:

`http://127.0.0.1:5000/`

Se reemplazó el carrusel anterior por una portada más cinematográfica:

- imagen o video a pantalla amplia;
- degradado para asegurar legibilidad;
- títulos de gran impacto;
- tipo de contenido;
- fecha;
- botones de acción;
- navegación numerada;
- accesos rápidos flotantes;
- métricas animadas;
- publicaciones recientes;
- sección de videos;
- misión/visión compactas;
- secciones institucionales;
- logros y contacto.

El contenido del carrusel ya no está “quemado” en la plantilla: se obtiene de publicaciones marcadas como **Destacadas** en PostgreSQL.

## 2. Ajustes visuales globales

Se redujo el tamaño y el peso visual de tarjetas en:

- Equipo institucional.
- Noticias.
- Galerías.
- Logros.
- Institución.
- Secciones.
- Contacto.
- Mapa del sitio.
- Administración.

El objetivo es mostrar más información con menos sensación de bloques gigantes.

## 3. Corrección del pie de página

Se retiraron completamente del sitio público textos como:

- `Entrega 8 · Equipo Institucional y Administración`
- `Flask + PostgreSQL + Bootstrap 5`

El visitante ya no ve información técnica ni números de entrega.

## 4. Videos institucionales

Nueva ruta pública:

`http://127.0.0.1:5000/videos`

Los videos se administran desde una publicación de tipo:

- NOTICIA
- EVENTO
- COMUNICADO

Formatos permitidos:

- MP4
- WEBM

Límite general de solicitud:

- 80 MB

Los archivos se guardan en:

`static/uploads/videos/`

PostgreSQL almacena la ruta, no el archivo binario.

## 5. Administración de noticias, eventos y videos

Ruta:

`http://127.0.0.1:5000/admin/noticias`

Cada publicación permite:

- título;
- resumen;
- contenido completo;
- tipo;
- fecha;
- imagen de portada;
- video;
- destacar en inicio;
- ordenar destacados;
- estado editorial.

También se puede:

- reemplazar imagen;
- eliminar imagen;
- reemplazar video;
- eliminar video;
- archivar;
- enviar a revisión;
- aprobar y publicar según rol.

## 6. Flujo editorial

Estados:

`BORRADOR → REVISION → PUBLICADA → ARCHIVADA`

### SUPERADMIN
Control total.

### RECTRIA / RECTORIA
Puede revisar, aprobar y publicar.

### EDITOR
Puede preparar y editar contenido, pero la publicación final pasa a revisión.

### COMUNICACIONES
Puede crear noticias, eventos, comunicados, imágenes y videos; la publicación final queda sujeta a revisión institucional.

## 7. Credenciales demo

### Superadmin
- Usuario: `admin.sms`
- Clave: `SmsPortal2026!`

### Rectoría
- Usuario: `rectoria.sms`
- Clave: `RectoriaSMS2026!`

### Editor
- Usuario: `editor.sms`
- Clave: `EditorSMS2026!`

### Comunicaciones
- Usuario: `comunica.sms`
- Clave: `ComunicaSMS2026!`

Cambiar todas las contraseñas antes de publicar el sistema en Internet.

## 8. Mi cuenta

Nueva ruta:

`/admin/cuenta`

Un usuario autenticado puede cambiar su contraseña desde la interfaz.

La contraseña sigue almacenándose mediante PBKDF2-SHA256 con salt.

## 9. Base de datos

Se conservan las **11 tablas originales**.

No se agrega una tabla nueva. La Entrega 9 amplía `noticia` con:

- `contenido`
- `tipo_contenido`
- `imagen_url`
- `video_url`
- `destacada`
- `orden_destacado`
- `creado_por_id`
- `ultimo_editor_id`
- `aprobado_por_id`
- `fecha_actualizacion`
- `fecha_aprobacion`

Esto mantiene el MER original y le aporta funcionalidad editorial real.

## 10. SQL incremental

Ejecutar únicamente después de las Entregas 1 a 8:

`SQL/entrega9_roles_editorial_video.sql`

El script:

- no recrea la base;
- no borra información existente;
- amplía `noticia`;
- ajusta el estado editorial para incluir `REVISION`;
- configura cuentas demo por rol;
- inserta **exactamente 10 nuevos contenidos de prueba**;
- incluye publicaciones destacadas, eventos, borradores, revisión y archivo.

## 11. Videos demo incluidos

La entrega incluye dos videos ligeros de demostración generados a partir de recursos gráficos propios del proyecto:

- `static/uploads/videos/demo_feria_innovacion.mp4`
- `static/uploads/videos/demo_cultura.mp4`

Permiten probar inmediatamente el carrusel y la sección `/videos`.

## 12. Seguridad

Se mantiene y amplía:

- sesiones Flask;
- HttpOnly;
- SameSite Lax;
- token CSRF;
- consultas parametrizadas;
- hash PBKDF2-SHA256;
- permisos por rol;
- validación de imagen;
- validación básica de firma MP4/WEBM;
- nombres aleatorios de archivos;
- aprobación restringida a Rectoría/Superadmin;
- formulario separado del portal público.

## 13. Datos de conexión

`db.py` continúa exactamente con:

- host: `localhost`
- database: `paginaWeb_SMS`
- user: `postgres`
- password: `1968Deruve2025`
- port: `5432`

## 14. Cómo probar

1. Ejecuta:
   `SQL/entrega9_roles_editorial_video.sql`
2. Inicia Flask:
   `python app.py`
3. Revisa la nueva portada:
   `http://127.0.0.1:5000/`
4. Revisa videos:
   `http://127.0.0.1:5000/videos`
5. Ingresa al panel:
   `http://127.0.0.1:5000/admin/login`
6. Prueba primero con `editor.sms` creando una publicación y enviándola a revisión.
7. Cierra sesión e ingresa con `rectoria.sms` para aprobarla.
8. Comprueba que aparezca públicamente.

## Evolución posterior

Si el proyecto se extiende más allá de las 9 entregas, las siguientes mejoras naturales serían:

- historial/auditoría completa de acciones;
- permisos todavía más finos;
- recuperación de contraseña;
- programación de publicación por fecha/hora;
- biblioteca multimedia reutilizable;
- SEO técnico y metadatos sociales;
- estadísticas de visitas y contenidos;
- copias de seguridad y exportación;
- despliegue productivo con HTTPS y servidor WSGI.

---

# Ajuste visual y de acceso — Entrega 9

Esta versión corregida incorpora los cambios solicitados después de revisar la interfaz en ejecución.

## Navegación pública

- Se eliminó el dropdown **Explorar** del centro del navbar.
- **Explorar** ahora es un botón hamburguesa ubicado en el extremo derecho.
- El botón abre un panel lateral moderno con:
  - accesos principales;
  - buscador;
  - secciones institucionales;
  - videos;
  - Conecta;
  - mapa del sitio;
  - acceso administrativo.
- En el navbar de escritorio ahora aparecen directamente:
  - **Ingresar**;
  - **Registro**.

## Registro administrativo

Nueva ruta pública:

`http://127.0.0.1:5000/admin/registro`

El registro funciona como **solicitud de acceso**, no como alta automática. Por seguridad:

1. el usuario diligencia sus datos;
2. la cuenta se almacena con `activo_web = FALSE`;
3. el rol inicial es `EDITOR`;
4. Rectoría o un `SUPERADMIN` revisa la solicitud desde Personal;
5. el responsable puede ajustar rol y activar la cuenta.

Si una persona intenta iniciar sesión antes de la aprobación, el sistema informa que su solicitud está pendiente.

## Secciones

Las tarjetas de `/secciones` fueron reemplazadas por cards más compactas y visuales:

- icono contextual;
- acento de color diferente;
- número editorial de fondo;
- indicador de sección pública;
- animación hover;
- menor altura;
- mejor adaptación a celulares y tabletas.

## Conecta

- Los iconos sociales del footer tienen nuevo estilo con profundidad, gradientes y hover.
- La página `/redes` también utiliza nuevas tarjetas digitales con iconos protagonistas y mejor jerarquía visual.

## Base de datos

**Este ajuste no requiere cambios adicionales de estructura.**

Si ya ejecutaste `SQL/entrega9_roles_editorial_video.sql`, no debes ejecutar otro SQL para aplicar este ajuste.

El registro administrativo reutiliza las columnas incorporadas en las Entregas 8 y 9.
