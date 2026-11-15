"""Public informational pages; no authentication or database access required."""
from flask import Blueprint, render_template, make_response

public_bp = Blueprint("public", __name__)


@public_bp.get("/about")
def about():
    return render_template("public/about.html")


def legal_draft(template):
    # Prevent unfinished legal text from being indexed or cached as final policy.
    response = make_response(render_template(template))
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["Cache-Control"] = "no-store"
    return response


@public_bp.get("/terms")
def terms():
    return legal_draft("public/terms.html")


@public_bp.get("/privacy")
def privacy():
    return legal_draft("public/privacy.html")
