from werkzeug.security import generate_password_hash
from app import create_app
from app.models import db


def test_analytics_chart_is_private():
    app=create_app({
        "TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://",
        "WTF_CSRF_ENABLED":False,"SECRET_KEY":"test-only",
        "ADMIN_PASSWORD_HASH":generate_password_hash("test-owner-password"),
    })
    with app.app_context():
        db.create_all()
    portal=app.test_client()
    assert portal.get("/api/analytics").status_code==401
    assert b'analytics-chart' not in portal.get("/analytics").data
    portal.post("/login",data={"password":"test-owner-password"})
    response=portal.get("/analytics")
    assert response.status_code==200
    assert b'analytics-chart' in response.data
    result=portal.get("/api/analytics")
    assert result.status_code==200
    assert result.json["summary"]["views"]==0
