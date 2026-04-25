import bcrypt
from sqlalchemy import (
    Boolean, Column, Float, ForeignKey, Integer, MetaData, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_convention)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), nullable=False, unique=True)
    password_hash = Column(String(256), nullable=False)

    trips = relationship("Trip", back_populates="user", lazy="dynamic")
    addresses = relationship(
        "SavedAddress", back_populates="user", lazy="select",
        order_by="SavedAddress.sort_order",
    )
    cars = relationship(
        "SavedCar", back_populates="user", lazy="select",
        order_by="SavedCar.sort_order",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hashpw(
            password.encode(), bcrypt.gensalt()
        ).decode()

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())


class SavedAddress(Base):
    __tablename__ = "saved_addresses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    label = Column(String(80), nullable=False)
    address = Column(String(512), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="addresses")

    __table_args__ = (
        UniqueConstraint("user_id", "label", name="uq_saved_addresses_user_id_label"),
    )


class SavedCar(Base):
    __tablename__ = "saved_cars"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(80), nullable=False)
    mpg = Column(Float, nullable=False)
    fuel_type = Column(String(20), nullable=False, default="gasoline")
    is_default = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="cars")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_saved_cars_user_id_name"),
    )


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True)
    date = Column(String(10), nullable=False)
    start_loc = Column(String, nullable=False)
    end_loc = Column(String, nullable=False)
    mode = Column(String(20), nullable=False)
    car_name = Column(String(50))
    miles = Column(Float, nullable=False)
    co2_kg = Column(Float, nullable=False, default=0.0)
    notes = Column(Text, default="")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    user = relationship("User", back_populates="trips")
    segments = relationship(
        "TripSegment", back_populates="trip",
        order_by="TripSegment.position",
        cascade="all, delete-orphan", lazy="select",
    )


class TripSegment(Base):
    __tablename__ = "trip_segments"

    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, index=True)
    position = Column(Integer, nullable=False, default=0)
    start_loc = Column(String, nullable=False)
    end_loc = Column(String, nullable=False)
    mode = Column(String(20), nullable=False)
    miles = Column(Float, nullable=False)

    trip = relationship("Trip", back_populates="segments")
