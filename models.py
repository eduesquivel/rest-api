import os

from dotenv import load_dotenv
from sqlalchemy import ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL", ""
)
engine = create_engine(DATABASE_URL)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r})"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    user: Mapped["User | None"] = relationship(back_populates="tickets")

    def __repr__(self) -> str:
        return f"Ticket(id={self.id!r}, user_id={self.user_id!r})"
