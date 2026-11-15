"""Read-only initial dashboard. State-changing actions will require authentication."""
from pathlib import Path
from flask import Blueprint, current_app, render_template, session

dashboard_bp = Blueprint("dashboard", __name__)

PAGES = {
    "/": ("index.html", "Dashboard"),
    "/streamers": ("streamers.html", "Streamers"),
    "/clips": ("clips.html", "Clips"),
    "/publications": ("publications.html", "Publicaciones"),
    "/analytics": ("analytics.html", "Analíticas"),
    "/settings": ("settings.html", "Configuración"),
}


def render_page(template, title):
    youtube_token_present = False
    if session.get("admin_authenticated"):
        token = Path(current_app.config["MEDIA_ROOT"]) / "private" / "youtube-token.json"
        youtube_token_present = token.is_file() and token.stat().st_size > 0
    return render_template(template, title=title, youtube_token_present=youtube_token_present)


@dashboard_bp.get("/")
def index():
    return render_page(*PAGES["/"])


@dashboard_bp.get("/streamers")
def streamers():
    return render_page(*PAGES["/streamers"])


@dashboard_bp.get("/clips")
def clips():
    return render_page(*PAGES["/clips"])


@dashboard_bp.get("/publications")
def publications():
    return render_page(*PAGES["/publications"])


@dashboard_bp.get("/analytics")
def analytics():
    return render_page(*PAGES["/analytics"])


@dashboard_bp.get("/settings")
def settings():
    return render_page(*PAGES["/settings"])


@dashboard_bp.get("/jobs")
def jobs():
    return render_page("jobs.html", "Trabajos")


@dashboard_bp.get("/integrations")
def integrations():
    return render_page("integrations.html", "Integraciones")
