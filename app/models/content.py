"""Kontent ierarxiyasi: kurs → bo'lim → mavzu → kichik mavzu → dars bloklari."""
from sqlalchemy import (BigInteger, Boolean, CheckConstraint, ForeignKey, Index, Integer, SmallInteger,
                        String, Text, true)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from ._base import JSONB, PK, Timestamps, one_of, pk

BLOCK_KINDS = ("text", "code", "image", "table", "mermaid", "formula", "video", "callout", "example", "quiz")


class Course(Timestamps, db.Model):
    __tablename__ = "courses"

    id: Mapped[int] = pk()
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    sections: Mapped[list["Section"]] = relationship(back_populates="course", order_by="Section.position")


class Section(Timestamps, db.Model):
    __tablename__ = "sections"

    id: Mapped[int] = pk()
    course_id: Mapped[int] = mapped_column(PK, ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")

    course: Mapped[Course] = relationship(back_populates="sections")
    topics: Mapped[list["Topic"]] = relationship(back_populates="section", order_by="Topic.position")


class Topic(Timestamps, db.Model):
    __tablename__ = "topics"

    id: Mapped[int] = pk()
    section_id: Mapped[int] = mapped_column(PK, ForeignKey("sections.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    est_minutes: Mapped[int | None] = mapped_column(SmallInteger)         # rejadagi taxminiy vaqt
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    section: Mapped[Section] = relationship(back_populates="topics")
    subtopics: Mapped[list["Subtopic"]] = relationship(back_populates="topic", order_by="Subtopic.position")
    prerequisites: Mapped[list["Topic"]] = relationship(
        secondary="topic_prerequisites",
        primaryjoin="Topic.id == TopicPrerequisite.topic_id",
        secondaryjoin="Topic.id == TopicPrerequisite.prerequisite_id",
        viewonly=True,
    )


class Subtopic(Timestamps, db.Model):
    __tablename__ = "subtopics"
    __table_args__ = (CheckConstraint("weight >= 0", name="weight_nonneg"),)

    id: Mapped[int] = pk()
    topic_id: Mapped[int] = mapped_column(PK, ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    weight: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")  # testdagi savollar soni

    topic: Mapped[Topic] = relationship(back_populates="subtopics")


class TopicPrerequisite(db.Model):
    __tablename__ = "topic_prerequisites"
    __table_args__ = (CheckConstraint("topic_id <> prerequisite_id", name="not_self"),)

    topic_id: Mapped[int] = mapped_column(PK, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
    prerequisite_id: Mapped[int] = mapped_column(PK, ForeignKey("topics.id", ondelete="CASCADE"),
                                                 primary_key=True, index=True)


class ContentBlock(Timestamps, db.Model):
    """Dars bloki. Mavzu uchun bir marta saqlanadi (har foydalanuvchiga emas).
    Sxemalar rasm emas, `kind='mermaid'` va `data.code` sifatida saqlanadi."""
    __tablename__ = "content_blocks"
    __table_args__ = (
        one_of("kind", BLOCK_KINDS),
        Index("ix_content_blocks_subtopic_position", "subtopic_id", "position"),
    )

    id: Mapped[int] = pk()
    subtopic_id: Mapped[int] = mapped_column(PK, ForeignKey("subtopics.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(12))
    position: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    audio_text: Mapped[str | None] = mapped_column(Text)                  # ovozli o'qish uchun matn
    method: Mapped[str | None] = mapped_column(String(40))                # tushuntirish usuli (10.3, method_stats)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    content_hash: Mapped[str] = mapped_column(String(64), index=True)     # sha256: audio/AI kesh kaliti
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    author_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))

    subtopic: Mapped[Subtopic] = relationship()
