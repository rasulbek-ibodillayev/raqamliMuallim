"""pgvector halfvec turi (2 bayt/o'lcham). pgvector.sqlalchemy o'rniga: u numpy'ni yuklaydi (har worker'da +7,5 MB RAM)."""
from sqlalchemy.dialects.postgresql.base import ischema_names
from sqlalchemy.types import UserDefinedType


class HalfVec(UserDefinedType):
    cache_ok = True

    def __init__(self, dim: int | None = None):
        self.dim = int(dim) if dim else None

    def get_col_spec(self, **kw):
        return f"HALFVEC({self.dim})" if self.dim else "HALFVEC"

    def bind_processor(self, dialect):
        return lambda v: None if v is None else "[" + ",".join(map(repr, map(float, v))) + "]"

    def result_processor(self, dialect, coltype):
        return lambda v: None if v is None else [float(x) for x in v.strip("[]").split(",")]


ischema_names["halfvec"] = HalfVec          # Alembic solishtirishi uchun
