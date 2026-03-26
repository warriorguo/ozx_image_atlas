import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, LargeBinary, ForeignKey, Text, text
import uuid

# Convert postgres:// to postgresql+asyncpg://
raw_url = os.environ.get("DATABASE_URL", "postgres://liuli@192.168.0.151:5432/ozx_atlas")
if raw_url.startswith("postgres://"):
    DATABASE_URL = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = raw_url


engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    params: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    export_filename: Mapped[str] = mapped_column(String(255), default="atlas.png")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkspaceImage(Base):
    __tablename__ = "workspace_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # "sprite", "shadow", "background"
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


async def ensure_database():
    """Create the ozx_atlas database if it doesn't exist, then create tables."""
    # Connect to default 'postgres' database to create our database
    admin_url = raw_url.rsplit("/", 1)[0] + "/postgres"
    if admin_url.startswith("postgres://"):
        admin_url = admin_url.replace("postgres://", "postgresql+asyncpg://", 1)
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'ozx_atlas'"))
            if not result.scalar():
                await conn.execute(text("CREATE DATABASE ozx_atlas"))
    finally:
        await admin_engine.dispose()

    # Now create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
