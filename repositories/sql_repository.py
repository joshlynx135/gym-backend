import uuid
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import Select, delete, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from domain.models import ClassDetails, Member, Trainer, WorkoutClass, build_member
from repositories.orm import BookingRow, ClassRow, MemberRow, TrainerRow

class SqlGymRepository:
    """PostgreSQL repository, following the same contract as the in-memory one.

    One instance wraps one SQLAlchemy Session, and one Session serves one request.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Transactions ------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator[None]:
        try:
            yield  # the body of the "with" block runs here
            self._session.commit()
        except BaseException:
            self._session.rollback()
            raise

    # --- Helpers -----------------------------------------------------------
    @staticmethod
    def _locked(statement: Select, for_update: bool) -> Select:
        if not for_update:
            return statement
        # FOR UPDATE locks the row; populate_existing refreshes any copy the session holds
        return statement.with_for_update().execution_options(populate_existing=True)

    @staticmethod
    def _to_member(row: MemberRow) -> Member:
        return build_member(row.id, row.name, row.type)

    @staticmethod
    def _to_class(row: ClassRow, member_ids: list[str]) -> WorkoutClass:
        return WorkoutClass(
            row.id, row.name, row.max_capacity,
            enrolled_member_ids=member_ids, trainer_id=row.trainer_id,
        )

    def _new_id(self, prefix: str, row_type: type) -> str:
        # Loop until we find an id that no row uses
        while True:
            candidate = f"{prefix}-{uuid.uuid4().hex[:8]}"
            if self._session.get(row_type, candidate) is None:
                return candidate

    def next_member_id(self) -> str:
        return self._new_id("m", MemberRow)

    def next_class_id(self) -> str:
        return self._new_id("c", ClassRow)

    # --- Members -----------------------------------------------------------
    def save_member(self, member: Member) -> None:
        row = self._session.get(MemberRow, member.id)
        if row is None:
            self._session.add(MemberRow(id=member.id, name=member.name, type=member.type_name))
        else:
            row.name = member.name
            row.type = member.type_name
        self._session.flush()  # send the SQL now, so a constraint violation surfaces here

    def get_member(self, member_id: str, *, for_update: bool = False) -> Optional[Member]:
        statement = self._locked(select(MemberRow).where(MemberRow.id == member_id), for_update)
        row = self._session.execute(statement).scalar_one_or_none()
        return self._to_member(row) if row is not None else None

    def list_members(self) -> list[Member]:
        rows = self._session.execute(select(MemberRow).order_by(MemberRow.id)).scalars().all()
        return [self._to_member(row) for row in rows]

    def delete_member(self, member_id: str) -> None:
        # The database removes this member's bookings itself (ON DELETE CASCADE)
        self._session.execute(delete(MemberRow).where(MemberRow.id == member_id))

    # --- Classes -----------------------------------------------------------
    def save_class(self, workout_class: WorkoutClass) -> None:
        row = self._session.get(ClassRow, workout_class.id)
        if row is None:
            self._session.add(
                ClassRow(
                    id=workout_class.id,
                    name=workout_class.name,
                    max_capacity=workout_class.max_capacity,
                    trainer_id=workout_class.trainer_id,
                )
            )
        else:
            row.name = workout_class.name
            row.max_capacity = workout_class.max_capacity
            row.trainer_id = workout_class.trainer_id 
        self._session.flush()  # the class row must exist before bookings can reference it
        self._sync_bookings(workout_class.id, set(workout_class.enrolled_members_ids))

    def get_class(self, class_id: str, *, for_update: bool = False) -> Optional[WorkoutClass]:
        statement = self._locked(select(ClassRow).where(ClassRow.id == class_id), for_update)
        row = self._session.execute(statement).scalar_one_or_none()
        if row is None:
            return None
        member_ids = (
            self._session.execute(
                select(BookingRow.member_id).where(BookingRow.class_id == class_id).order_by(BookingRow.member_id)
            )
            .scalars()
            .all()
        )
        return self._to_class(row, list(member_ids))

    def list_classes(self) -> list[WorkoutClass]:
        rows = self._session.execute(select(ClassRow).order_by(ClassRow.id)).scalars().all()

        # ONE query for every booking, grouped in Python: the number of queries
        # does not grow with the number of classes
        rosters: dict[str, list[str]] = defaultdict(list)
        booking_pairs = self._session.execute(
            select(BookingRow.class_id, BookingRow.member_id).order_by(BookingRow.member_id)
        )
        for class_id, member_id in booking_pairs:
            rosters[class_id].append(member_id)

        return [self._to_class(row, rosters[row.id]) for row in rows]

    def list_class_details(self) -> list[ClassDetails]:
        statement = (
            select(ClassRow)
            .options(joinedload(ClassRow.trainer), selectinload(ClassRow.members))
            .order_by(ClassRow.id)
        )
        rows = self._session.execute(statement).scalars().all()

        details = []
        for row in rows:
            members = tuple(self._to_member(member_row) for member_row in row.members)
            trainer = Trainer(row.trainer.id, row.trainer.name) if row.trainer is not None else None
            details.append(
                ClassDetails(
                    workout_class=self._to_class(row, [member.id for member in members]),
                    trainer=trainer,
                    members=members,
                )
            )
        return details

    def delete_class(self, class_id: str) -> None:
        # The database removes this class's bookings itself (ON DELETE CASCADE)
        self._session.execute(delete(ClassRow).where(ClassRow.id == class_id))

    # --- Bookings ----------------------------------------------------------
    def count_bookings_of_member(self, member_id: str) -> int:
        statement = select(func.count()).select_from(BookingRow).where(BookingRow.member_id == member_id)
        return self._session.execute(statement).scalar_one()

    def _sync_bookings(self, class_id: str, desired_member_ids: set[str]) -> None:
        """Make the bookings table match the roster of the class object."""
        stored = set(
            self._session.execute(select(BookingRow.member_id).where(BookingRow.class_id == class_id)).scalars()
        )
        for member_id in sorted(desired_member_ids - stored):
            self._session.add(BookingRow(member_id=member_id, class_id=class_id))

        removed = stored - desired_member_ids
        if removed:
            self._session.execute(
                delete(BookingRow).where(BookingRow.class_id == class_id, BookingRow.member_id.in_(removed))
            )
        self._session.flush()

    # --- Trainers ----------------------------------------------------------
    def next_trainer_id(self) -> str:
        return self._new_id("t", TrainerRow)

    def save_trainer(self, trainer: Trainer) -> None:
        row = self._session.get(TrainerRow, trainer.id)
        if row is None:
            self._session.add(TrainerRow(id=trainer.id, name=trainer.name))
        else:
            row.name = trainer.name
        self._session.flush()

    def get_trainer(self, trainer_id: str, *, for_update: bool = False) -> Optional[Trainer]:
        statement = self._locked(select(TrainerRow).where(TrainerRow.id == trainer_id), for_update)
        row = self._session.execute(statement).scalar_one_or_none()
        return Trainer(row.id, row.name) if row is not None else None

    def list_trainers(self) -> list[Trainer]:
        rows = self._session.execute(select(TrainerRow).order_by(TrainerRow.id)).scalars().all()
        return [Trainer(row.id, row.name) for row in rows]

    def delete_trainer(self, trainer_id: str) -> None:
        # The database refuses this while a class still references the trainer (RESTRICT)
        self._session.execute(delete(TrainerRow).where(TrainerRow.id == trainer_id))

    def count_classes_of_trainer(self, trainer_id: str) -> int:
        statement = select(func.count()).select_from(ClassRow).where(ClassRow.trainer_id == trainer_id)
        return self._session.execute(statement).scalar_one()