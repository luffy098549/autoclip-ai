# AutoClip AI — MVP en desarrollo

Automatización de edición de videos cortos **con material propio o autorizado**.

[![Python checks](https://github.com/luffy098549/autoclip-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/luffy098549/autoclip-ai/actions)

## Implementado

- Panel web responsive: Dashboard, Streamers, Clips, Publicaciones, Analíticas y Configuración
- Inicio de sesión del propietario (contraseña con hash), sesiones y protección CSRF
- Registro de canales de Kick/YouTube **sin descargar videos automáticamente**
- Carga de videos propios/autorizados y registro de fuentes en PostgreSQL
- Solicitudes de recorte y renderizado vertical 1080×1920 con FFmpeg
- Cola Celery/Redis para procesamiento opcional
- Análisis opcional con faster-whisper (transcripción local)
- Selector preliminar de fragmentos a partir de transcripciones; **es heurístico, no predictor de viralidad**
- Generación de subtítulos SRT como archivo adjunto y comando opcional para incrustarlos en video
- Límite de planificación: al menos 120 minutos entre publicaciones y máximo 5 por red/día
- Pruebas automatizadas con GitHub Actions

## NO implementado todavía

- Descarga de directos de terceros, monitoreo en vivo de Kick o YouTube
- Permisos de acceso/OAuth a cuentas de YouTube, TikTok o Instagram
- Publicación real de videos o monetización
- Reencuadre de rostros mediante IA, subtítulos incrustados en video, narración original automática
- Análisis de rendimiento con métricas de cuentas conectadas
- Motor de publicaciones transaccional, migraciones de producción y seguridad de despliegue público

**Ningún video se publica automáticamente en redes en esta versión.**

## Desarrollo local

1. Copia `.env.example` a `.env`. Sustituye SECRET_KEY por una cadena aleatoria.
2. Ejecuta `python -m scripts.hash_password` en un entorno con las dependencias instaladas. Copia el hash generado a `ADMIN_PASSWORD_HASH` en `.env` (no publiques la contraseña).
3. Ejecuta `docker compose up --build -d`.
4. Crea las tablas: `docker compose exec web python -m scripts.init_db`.
5. Abre `http://localhost:8000/login` e inicia sesión.
6. En **Streamers**, registra el canal; en **Clips**, carga un video autorizado.
7. Elige inicio/final y crea la tarea. Procesa manualmente con `docker compose exec web python -m scripts.process_clip ID` si no activaste workers.
8. Los videos exportados se guardan en `storage/clips/`.

Más detalles en [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

### Análisis con IA opcional

Para pruebas locales, instala `requirements-ai.txt` que incluye `faster-whisper` y sigue las instrucciones de Docker:

```bash
docker compose exec web python -m scripts.analyze_source SOURCE_ID --model small --max-clips 5 --render
docker compose exec web python -m scripts.export_subtitles CLIP_ID
```

Usa `INSTALL_AI=true` antes de construir Docker si quieres incluir Whisper y `AI_ENABLED=true` solo después de instalar correctamente los modelos.

La transcripción puede consumir memoria/CPU considerable, y la primera ejecución del modelo puede requerir una descarga. Los subtítulos se generan como archivos SRT. Para crear un nuevo MP4 subtitulado, utiliza `docker compose exec web python -m scripts.burn_clip_subtitles CLIP_ID`. Requiere el filtro `subtitles` de FFmpeg. No se aplica automáticamente a cada clip.

## Reglas comerciales y derechos

El proyecto busca construir canales propios de Shorts, Reels y TikTok, no ofrecer un servicio a terceros. La publicación y monetización dependen de permisos de reutilización, contenido original y normas vigentes de cada plataforma. Declarar derechos en un formulario **no constituye una verificación legal independiente**.

## Seguridad

El repositorio es público: nunca subas `.env`, contraseñas, OAuth tokens, videos privados ni claves. Docker expone el panel solo en `127.0.0.1` para desarrollo. Antes de desplegar públicamente se necesitan HTTPS, gestión de secretos, límites de intentos, autenticación reforzada y migraciones de base de datos.
