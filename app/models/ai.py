"""AI: javoblar keshi, sarf hisobi, audio va RAG."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from ._base import JSONB, PK, created_at, pk
from ._vector import HalfVec

EMBED_DIM = 768   # gemini-embedding-2. O'zgartirilsa — yangi migratsiya va qayta indekslash


class AICache(db.Model):
    """Bir xil so'rovga (mavzu darsi, savol izohi) bir marta to'lanadi."""
    __tablename__ = "ai_cache"

    id: Mapped[int] = pk()
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)   # sha256(kind + model + normallashgan prompt)
    kind: Mapped[str] = mapped_column(String(30))                    # lesson, explain, hint, tutor, generate
    model: Mapped[str] = mapped_column(String(60))
    topic_id: Mapped[int | None] = mapped_column(PK, ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    response: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    hits: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = created_at()
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class AIUsage(db.Model):
    """Har bir AI chaqiruvi: oylik limit va admin panelidagi «AI xarajati»."""
    __tablename__ = "ai_usage"
    __table_args__ = (Index("ix_ai_usage_user_created", "user_id", "created_at"),)

    id: Mapped[int] = pk()
    user_id: Mapped[int | None] = mapped_column(PK, ForeignKey("users.id", ondelete="SET NULL"))
    provider: Mapped[str] = mapped_column(String(20))                # gemini, ... (zaxira zanjiri)
    model: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(30))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 6, asdecimal=False), default=0, server_default="0")
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    ok: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=db.func.now(), index=True)


class AudioAsset(db.Model):
    """Matn xeshi bo'yicha keshlangan ovoz: bir blok uchun bir marta yaratiladi."""
    __tablename__ = "audio_assets"

    id: Mapped[int] = pk()
    text_hash: Mapped[str] = mapped_column(String(64), unique=True)
    block_id: Mapped[int | None] = mapped_column(PK, ForeignKey("content_blocks.id", ondelete="SET NULL"), index=True)
    voice: Mapped[str] = mapped_column(String(40))
    path: Mapped[str] = mapped_column(String(300))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = created_at()


class RagSource(db.Model):
    __tablename__ = "rag_sources"

    id: Mapped[int] = pk()
    title: Mapped[str] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(20))                    # textbook, standard, lesson, faq
    uri: Mapped[str | None] = mapped_column(String(500))
    checksum: Mapped[str] = mapped_column(String(64), unique=True)
    topic_id: Mapped[int | None] = mapped_column(PK, ForeignKey("topics.id", ondelete="SET NULL"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = created_at()

    chunks: Mapped[list["RagChunk"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class RagChunk(db.Model):
    __tablename__ = "rag_chunks"
    __table_args__ = (
        Index("ix_rag_chunks_embedding", "embedding", postgresql_using="hnsw",
              postgresql_with={"m": 16, "ef_construction": 64},
              postgresql_ops={"embedding": "halfvec_cosine_ops"}),
    )

    id: Mapped[int] = pk()
    source_id: Mapped[int] = mapped_column(PK, ForeignKey("rag_sources.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(SmallInteger)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    embedding: Mapped[list[float] | None] = mapped_column(HalfVec(EMBED_DIM))

    source: Mapped[RagSource] = relationship(back_populates="chunks")
