from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean, JSON, Numeric, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.core.database import Base

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc)

class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Owned(Identity):
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)

class User(Identity, Base):
    __tablename__ = 'users'
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(Text)

class RefreshToken(Owned, Base):
    __tablename__ = 'refresh_tokens'
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

class Conversation(Owned, Base):
    __tablename__ = 'conversations'
    title: Mapped[str] = mapped_column(String(200), default='Yangi suhbat')

class Message(Identity, Base):
    __tablename__ = 'messages'
    conversation_id: Mapped[str] = mapped_column(ForeignKey('conversations.id', ondelete='CASCADE'), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)

class Memory(Owned, Base):
    __tablename__ = 'memories'
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), default='Uzoq muddatli xotiralar')
    tags: Mapped[list] = mapped_column(JSON, default=list)
    use_in_chat: Mapped[bool] = mapped_column(Boolean, default=True)

class MemoryEmbedding(Identity, Base):
    __tablename__ = 'memory_embeddings'
    memory_id: Mapped[str] = mapped_column(ForeignKey('memories.id', ondelete='CASCADE'), unique=True)
    model: Mapped[str] = mapped_column(String(100))
    embedding: Mapped[list] = mapped_column(Vector(768).with_variant(JSON, 'sqlite'))

class Project(Owned, Base):
    __tablename__ = 'projects'
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default='')
    technologies: Mapped[list] = mapped_column(JSON, default=list)
    repository_url: Mapped[str] = mapped_column(String(500), default='')
    status: Mapped[str] = mapped_column(String(30), default='faol')

class ProjectNote(Owned, Base):
    __tablename__ = 'project_notes'
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    content: Mapped[str] = mapped_column(Text)

class Task(Owned, Base):
    __tablename__ = 'tasks'
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default='')
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[str] = mapped_column(String(20), default='o‘rta')
    due_date: Mapped[str] = mapped_column(String(10), default='')
    category: Mapped[str] = mapped_column(String(100), default='Shaxsiy')
    project_id: Mapped[Optional[str]] = mapped_column(ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)

class Category(Owned, Base):
    __tablename__ = 'categories'
    name: Mapped[str] = mapped_column(String(100))
    __table_args__ = (UniqueConstraint('owner_id', 'name'),)

class KnowledgeDocument(Owned, Base):
    __tablename__ = 'knowledge_documents'
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(255), default='')
    category: Mapped[str] = mapped_column(String(100), default='Qaydlar')
    tags: Mapped[list] = mapped_column(JSON, default=list)
    source_url: Mapped[str] = mapped_column(String(1000), default='')
    summary: Mapped[str] = mapped_column(Text, default='')

class DocumentChunk(Identity, Base):
    __tablename__ = 'document_chunks'
    document_id: Mapped[str] = mapped_column(ForeignKey('knowledge_documents.id', ondelete='CASCADE'), index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding_model: Mapped[str] = mapped_column(String(100), default='')
    embedding: Mapped[Optional[list]] = mapped_column(Vector(768).with_variant(JSON, 'sqlite'), nullable=True)

class Integration(Owned, Base):
    __tablename__ = 'integrations'
    name: Mapped[str] = mapped_column(String(100))
    connected: Mapped[bool] = mapped_column(Boolean, default=False)

class UserSettings(Owned, Base):
    __tablename__ = 'user_settings'
    __table_args__ = (UniqueConstraint('owner_id'),)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)

class AIUsageLog(Owned, Base):
    __tablename__ = 'ai_usage_logs'
    model: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30))

class AuditLog(Owned, Base):
    __tablename__ = 'audit_logs'
    action: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(36), default='')
    detail: Mapped[dict] = mapped_column(JSON, default=dict)

class BusinessEntry(Owned, Base):
    __tablename__ = 'business_entries'
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    amount: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default='UZS')
    date: Mapped[str] = mapped_column(String(10))
    note: Mapped[str] = mapped_column(Text, default='')

Index('ix_memories_owner_category', Memory.owner_id, Memory.category)
Index('ix_tasks_owner_completed_due', Task.owner_id, Task.completed, Task.due_date)
Index('ix_memory_embeddings_cosine', MemoryEmbedding.embedding, postgresql_using='hnsw', postgresql_ops={'embedding':'vector_cosine_ops'}).ddl_if(dialect='postgresql')
Index('ix_document_chunks_cosine', DocumentChunk.embedding, postgresql_using='hnsw', postgresql_ops={'embedding':'vector_cosine_ops'}).ddl_if(dialect='postgresql')
