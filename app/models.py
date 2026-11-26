from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('resident', 'master', 'dispatcher', 'admin')",
            name="ck_users_role",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    resident: Mapped["Resident | None"] = relationship(back_populates="user")
    master: Mapped["Master | None"] = relationship(back_populates="user")

class House(Base):
    __tablename__ = "houses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    entrances_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    apartments: Mapped[list["Apartment"]] = relationship(back_populates="house")

class Apartment(Base):
    __tablename__ = "apartments"
    __table_args__ = (
        UniqueConstraint("house_id", "number", name="uq_apartment_house_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    house_id: Mapped[int] = mapped_column(
        ForeignKey("houses.id"), nullable=False
    )
    number: Mapped[str] = mapped_column(String(20), nullable=False)
    floor: Mapped[int | None] = mapped_column(Integer)
    area: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))

    house: Mapped["House"] = relationship(back_populates="apartments")
    residents: Mapped[list["Resident"]] = relationship(back_populates="apartment")
    requests: Mapped[list["Request"]] = relationship(back_populates="apartment")

class Resident(Base):
    __tablename__ = "residents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), unique=True, nullable=False
    )
    apartment_id: Mapped[int] = mapped_column(
        ForeignKey("apartments.id"), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="resident")
    apartment: Mapped["Apartment"] = relationship(back_populates="residents")
    requests: Mapped[list["Request"]] = relationship(back_populates="resident")

class Master(Base):
    __tablename__ = "masters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), unique=True, nullable=False
    )
    specialization: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="master")
    requests: Mapped[list["Request"]] = relationship(back_populates="master")

class Request(Base):
    __tablename__ = "requests"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'normal', 'high')",
            name="ck_requests_priority",
        ),
        CheckConstraint(
            "status IN ('new', 'assigned', 'in_progress', 'completed', 'cancelled')",
            name="ck_requests_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    apartment_id: Mapped[int] = mapped_column(
        ForeignKey("apartments.id"), nullable=False
    )
    resident_id: Mapped[int] = mapped_column(
        ForeignKey("residents.id"), nullable=False
    )
    master_id: Mapped[int | None] =mapped_column(ForeignKey("masters.id"))
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    apartment: Mapped["Apartment"] = relationship(back_populates="requests")
    resident: Mapped["Resident"] = relationship(back_populates="requests")
    master: Mapped["Master | None"] = relationship(back_populates="requests")
    history: Mapped[list["RequestStatusHistory"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
    )

class RequestStatusHistory(Base):
    __tablename__ = "request_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id"), nullable=False
    )
    changed_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    old_status: Mapped[str | None] = mapped_column(String(20))
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    request: Mapped["Request"] = relationship(back_populates="history")
