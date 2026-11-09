# AutoClip AI — MVP en desarrollo

Automatización de edición de videos cortos **con material propio o autorizado**.

[![Python checks](https://github.com/luffy098549/autoclip-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/luffy098549/autoclip-ai/actions)

## Implementado

- Panel web responsive: Dashboard, Streamers, Clips, Publicaciones, Analíticas, Configuración e Integraciones
- Pantalla de trabajos con estados reales de la cola y actualización mientras está visible
- Estado real de PostgreSQL y módulos del backend en la página de configuración; estadísticas de negocio privadas
- Inicio de sesión del propietario (contraseña con hash), sesiones y protección CSRF
- Registro de canales de Kick/YouTube **sin descargar videos automáticamente**
- Consulta opcional de metadatos públicos de canales/videos con la API oficial de YouTube (requiere clave propia)
- PostgreSQL como base de datos principal con migraciones versionadas Alembic/Flask-Migrate y pruebas de integración en CI
- Carga de videos propios/autorizados y registro de fuentes en PostgreSQL
- Solicitudes de recorte y renderizado vertical 1080×1920 con FFmpeg
- Cola Celery/Redis para procesamiento opcional y renderizado automático posterior al análisis cuando AUTO_RENDER_ENABLED=true
- Análisis opcional con faster-whisper (transcripción local)
- Selector preliminar de fragmentos a partir de transcripciones; **es heurístico, no predictor de viralidad**
- Generación de subtítulos SRT, lector privado de transcripciones y subtítulos incrustados opcionales durante el render
- Reproductor privado de clips 9:16, con filtros por estado y descargas MP4/SRT
- Calendario privado de borradores con cancelación, límites de 120 minutos y máximo 5 por red/día; sin uploads reales
- Registro manual de métricas de clips de tus propias cuentas, gráficos por red y ranking descriptivo por visualizaciones (sin ingresos estimados)
- Integraciones oficiales condicionadas a OAuth: YouTube mediante CLI manual; Instagram Reels en dos fases; TikTok con borrador en la bandeja de entrada
- Pruebas de SDK sociales simuladas, PostgreSQL y frontend en GitHub Actions

## NO implementado todavía

- Descarga de directos de terceros, monitoreo en vivo de Kick o YouTube
- Permisos de acceso/OAuth a cuentas de YouTube, TikTok o Instagram
- Publicación autónoma de videos o monetización; integraciones manuales requieren OAuth, permisos de apps y revisión de cada cuenta
- Reencuadre inteligente de rostros y narración original automática
- Análisis de rendimiento con métricas de cuentas conectadas
- Publicación real en plataformas, auditoría de tareas avanzada y seguridad de despliegue público

**Ningún video se publica automáticamente en redes en esta versión.**

## Desarrollo local

1. Copia `.env.example` a `.env`. Sustituye SECRET_KEY por una cadena aleatoria.
2. Ejecuta `python -m scripts.hash_password` en un entorno con las dependencias instaladas. Copia el hash generado a `ADMIN_PASSWORD_HASH` en `.env` (no publiques la contraseña).
3. Ejecuta `docker compose up --build -d`.
4. Aplica las migraciones: `docker compose exec web python -m scripts.init_db`.
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

Usa `INSTALL_AI=true` antes de construir Docker si quieres incluir Whisper y `AI_ENABLED=true` solo después de instalar correctamente los modelos. Ajusta `AUTO_RENDER_ENABLED=true` para producir automáticamente los clips que el análisis seleccione; puede consumir bastante CPU/GPU.

La transcripción puede consumir memoria/CPU considerable, y la primera ejecución del modelo puede requerir una descarga. Los subtítulos se generan como archivos SRT. Puedes activar AUTO_CAPTION_ENABLED=true para incrustarlos durante el procesamiento cuando exista transcripción. Para crear un nuevo MP4 subtitulado, utiliza `docker compose exec web python -m scripts.burn_clip_subtitles CLIP_ID`. Requiere el filtro `subtitles` de FFmpeg. No se aplica automáticamente a cada clip.

## Reglas comerciales y derechos

Los borradores del calendario no provocan publicaciones en redes. El proyecto busca construir canales propios de Shorts, Reels y TikTok, no ofrecer un servicio a terceros. La publicación y monetización dependen de permisos de reutilización, contenido original y normas vigentes de cada plataforma. Declarar derechos en un formulario **no constituye una verificación legal independiente**.

## Seguridad

El repositorio es público: nunca subas `.env`, contraseñas, OAuth tokens, videos privados ni claves. Docker expone el panel solo en `127.0.0.1` para desarrollo. Antes de desplegar públicamente se necesitan HTTPS, gestión de secretos, límites de intentos, autenticación reforzada y migraciones de base de datos.
