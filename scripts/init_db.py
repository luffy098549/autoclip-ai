"""Run once after database service is healthy: python -m scripts.init_db"""
from app import create_app
from app.models import db

app = create_app()
with app.app_context():
    db.create_all()
print("Created initial development tables. Use Alembic for future schema migrations.")
