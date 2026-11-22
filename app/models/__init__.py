"""Ma'lumotlar modeli (TZ 23-bo'lim). Tafsilotlar: docs/tz-23-malumotlar-modeli.md"""
from .ai import EMBED_DIM, AICache, AIUsage, AudioAsset, RagChunk, RagSource
from .community import Certificate, Discussion, Note, Objection
from .content import ContentBlock, Course, Section, Subtopic, Topic, TopicPrerequisite
from .progress import ErrorItem, MethodStat, ReviewSchedule, UserTopicProgress
from .questions import Question, QuestionVersion
from .system import AuditLog, Setting
from .testing import AttemptItem, TestAttempt
from .users import User

__all__ = [
    "EMBED_DIM", "AICache", "AIUsage", "AttemptItem", "AudioAsset", "AuditLog", "Certificate", "ContentBlock",
    "Course", "Discussion", "ErrorItem", "MethodStat", "Note", "Objection", "Question", "QuestionVersion",
    "RagChunk", "RagSource", "ReviewSchedule", "Section", "Setting", "Subtopic", "TestAttempt", "Topic",
    "TopicPrerequisite", "User", "UserTopicProgress",
]
