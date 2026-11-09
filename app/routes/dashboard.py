"""Read-only initial dashboard. State-changing actions will require authentication."""
from flask import Blueprint, render_template

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
    return render_template(template, title=title)


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
