from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base


class Emission(Base):
    __tablename__ = "emissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#6B2EA6")
    statut_technique: Mapped[str] = mapped_column(String(50), default="normal", nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="emissions")
    podcasts: Mapped[list["Podcast"]] = relationship(back_populates="emission", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Emission id={self.id} title={self.title}>"
