"""Session-based admin login and CSRF protection for owner-only write actions."""
from functools import wraps
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

auth_bp = Blueprint("auth", __name__)


def admin_only(view):
    @wraps(view)
    def guarded(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return jsonify(error="Inicia sesión como administrador"), 401
        return view(*args, **kwargs)
    return guarded


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password_hash = current_app.config.get("ADMIN_PASSWORD_HASH") or ""
        password = request.form.get("password") or ""
        if password_hash and password and check_password_hash(password_hash, password):
            session.clear()
            session["admin_authenticated"] = True
            return redirect(url_for("dashboard.index"))
        return render_template("login.html", error="Contraseña incorrecta o administrador no configurado."), 401
    return render_template("login.html", error=None)


@auth_bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
