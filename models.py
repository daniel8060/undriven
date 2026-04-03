from sqlalchemy import MetaData
from flask_sqlalchemy import SQLAlchemy

# Explicit naming convention is required for Alembic batch operations on SQLite
# (and good practice for Postgres migrations too)
_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
db = SQLAlchemy(metadata=MetaData(naming_convention=_convention))


class User(db.Model):
    """Stub for future auth. Exists now so the FK is in place before data accumulates."""
    __tablename__ = "users"

    id    = db.Column(db.Integer, primary_key=True)
    trips = db.relationship("Trip", back_populates="user", lazy="dynamic")


class Trip(db.Model):
    __tablename__ = "trips"

    id        = db.Column(db.Integer, primary_key=True)
    date      = db.Column(db.String(10), nullable=False)
    start_loc = db.Column(db.String, nullable=False)
    end_loc   = db.Column(db.String, nullable=False)
    mode      = db.Column(db.String(20), nullable=False)
    car_name  = db.Column(db.String(50))
    miles     = db.Column(db.Float, nullable=False)
    co2_kg    = db.Column(db.Float, nullable=False, default=0.0)
    notes     = db.Column(db.Text, default="")
    user_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    user      = db.relationship("User", back_populates="trips")
