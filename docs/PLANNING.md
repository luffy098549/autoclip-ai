# Calendario local de AutoClip AI

La pantalla Publicaciones guarda borradores privados. No llama a APIs de YouTube, TikTok ni Instagram.

- Requiere iniciar sesión.
- Solo acepta clips terminados, con archivo existente y derechos declarados.
- Las fechas se interpretan en America/New_York.
- Máximo cinco registros activos por red y día; al menos 120 minutos entre ellos.
- Permite cancelar borradores sin borrarlos de la auditoría.
- En PostgreSQL usa un bloqueo transaccional por plataforma para evitar reservas conflictivas.
- Ningún registro pasa a estado publicado por este módulo.

Pendiente: OAuth, upload oficial, verificación de permisos editoriales, estados remotos, tasas, reintentos e idempotencia de publicación.
