from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    """Parent of all ORM classes. Base.metadata collects every table definition."""

class MemberRow(Base):
    __tablename__ = "members"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type:Mapped[str] = mapped_column(String(16), nullable=False)

    # The database itself refuses any type other than these two
    __table_args__ = (
        CheckConstraint("type IN ('BASIC', 'PREMIUM')", name="ck_members_type"),
    )
class TrainerRow(Base):
    __tablename__ = "trainers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class ClassRow(Base):
    __tablename__ = "classes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    trainer_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("trainers.id", ondelete="RESTRICT", name="fk_classes_trainer_id_trainers"),
        nullable=True,
        index=True,
    )
    trainer: Mapped[Optional[TrainerRow]] = relationship(viewonly=True, lazy="raise")
    members: Mapped[list[MemberRow]] = relationship(
        secondary="bookings", viewonly=True, lazy="raise", order_by=MemberRow.id
    )

    __table_args__ = (
        CheckConstraint("max_capacity > 0", name="ck_classes_max_capacity"),
    )

class BookingRow(Base):
    __tablename__ = "bookings"

    # Composite primary key: a member can be in a given class at most once
    member_id: Mapped[str] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE", name="fk_bookings_member_id_members"),
        primary_key=True,
    )
    class_id: Mapped[str] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE", name="fk_bookings_class_id_classes"),
        primary_key=True,
        index=True,
    )