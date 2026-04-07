import bcrypt
from flask_login import UserMixin
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


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)

    trips     = db.relationship("Trip",         back_populates="user", lazy="dynamic")
    addresses = db.relationship("SavedAddress", back_populates="user", lazy="select",
                                order_by="SavedAddress.sort_order")
    cars      = db.relationship("SavedCar",     back_populates="user", lazy="select")

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hashpw(
            password.encode(), bcrypt.gensalt()
        ).decode()

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())


class SavedAddress(db.Model):
    __tablename__ = "saved_addresses"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    label      = db.Column(db.String(80),  nullable=False)
    address    = db.Column(db.String(512), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    user = db.relationship("User", back_populates="addresses")

    __table_args__ = (
        db.UniqueConstraint("user_id", "label", name="uq_saved_addresses_user_id_label"),
    )


class SavedCar(db.Model):
    __tablename__ = "saved_cars"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name       = db.Column(db.String(80), nullable=False)
    mpg        = db.Column(db.Float, nullable=False)
    fuel_type  = db.Column(db.String(20), nullable=False, default="gasoline")
    is_default = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship("User", back_populates="cars")

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_saved_cars_user_id_name"),
    )


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
