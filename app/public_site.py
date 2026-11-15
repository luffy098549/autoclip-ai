"""Public informational pages; no authentication or database access required."""
from flask import Blueprint, render_template

public_bp = Blueprint("public", __name__)

@public_bp.get("/about")
def about():
    return render_template("public/about.html")

@public_bp.get("/terms")
def terms():
    return render_template("public/terms.html")

@public_bp.get("/privacy")
def privacy():
    return render_template("public/privacy.html")
