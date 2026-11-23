"""Public informational pages; no authentication or database access required."""
import os
import re

from flask import Blueprint, abort, make_response, render_template

public_bp = Blueprint("public", __name__)
_VERIFICATION_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\.txt$")
_VERIFICATION_VALUE = re.compile(r"^[A-Za-z0-9_.=-]{1,512}$")


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


@public_bp.get("/<filename>")
def tiktok_domain_verification(filename):
    """Serve only an exact, operator-configured TikTok domain verification file.

    The filename and file contents must be copied from TikTok Developer Portal.
    This route is disabled unless both values are configured; no filesystem access.
    """
    configured_name = os.getenv("TIKTOK_VERIFICATION_FILENAME", "")
    configured_value = os.getenv("TIKTOK_VERIFICATION_CONTENT", "")
    if not (_VERIFICATION_FILENAME.fullmatch(configured_name)
            and _VERIFICATION_VALUE.fullmatch(configured_value)
            and filename == configured_name):
        abort(404)
    response = make_response(configured_value + "\n")
    response.mimetype = "text/plain"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
