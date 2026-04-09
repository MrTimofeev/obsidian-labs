from sqlalchemy import Column, Integer, String, Float, Boolean, Date, Text, DateTime, UniqueConstraint, Table, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone, date

Base = declarative_base()


class DailyMetric(Base):
    """
    Гибкая таблица метрик (EAV).
    Позволяет добавлять новые привычки без изменения структуры БД.
    """
    __tablename__ = 'daily_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_date = Column(Date, nullable=False, index=True)
    metric_name = Column(String, nullable=False, index=True)

    # Разделение по типам
    value_num = Column(Float, default=None)   # Для чисел
    value_bool = Column(Boolean, default=None)  # Для да/нет (0/1)
    value_text = Column(Text, default=None)    # Для комментариев

    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    # Уникальность: одна метрика одного типа за один день
    __table_args__ = (UniqueConstraint(
        'log_date', 'metric_name', name='uix_date_metric'),)

    def __repr__(self):
        return f"<Metric(date={self.log_date}, name={self.metric_name}, val={self.value_num or self.value_bool})>"


class DailyNote(Base):
    """
    Хранит текст заметок и пути к файлам.
    Связана с метриками по дате.
    """
    __tablename__ = 'daily_notes'

    log_date = Column(Date, primary_key=True)  # Дата как ключ
    file_name = Column(String, nullable=True)
    relative_path = Column(String, nullable=True)
    content_text = Column(Text, nullable=True)  # Полный текст заметки
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Note(date={self.log_date}, file={self.file_name})>"


# ---------------------------
card_tags = Table(
    'card_tags', Base.metadata,
    Column('card_id', Integer, ForeignKey('srs_cards.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('srs_tags.id'), primary_key=True)
)


class SrsTag(Base):
    __tablename__ = 'srs_tags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)

    cards = relationship("SrsCard", secondary=card_tags, back_populates="tags")

    def __repr__(self):
        return f"<Tag(name='{self.name}')>"


class SrsCard(Base):
    __tablename__ = 'srs_cards'

    id = Column(Integer, primary_key=True, autoincrement=True)
    card_hash = Column(String, unique=True, nullable=False, index=True)

    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

    source_file = Column(String, nullable=True)  # Путь к файлу
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    is_archived = Column(Boolean, default=False)  # Если карточка удалена из MD

    # Параметры алгоритма SM-2
    interval = Column(Integer, default=0)       # Интервал в днях
    # Кол-во успешных повторений подряд
    repetitions = Column(Integer, default=0)
    # Коэффициент легкости (начальный 2.5)
    ease_factor = Column(Float, default=2.5)
    last_reviewed = Column(Date, nullable=True)  # Дата последнего повторения

    # Связь с тегами
    tags = relationship("SrsTag", secondary=card_tags, back_populates="cards")

    def __repr__(self):
        return f"<Card(hash='{self.card_hash[:8]}...', q='{self.question[:20]}...')>"


class SrsReviewLog(Base):
    __tablename__ = 'srs_review_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    card_hash = Column(String, nullable=False,
                       index=True)  # Ссылка на карточку

    review_date = Column(Date, nullable=False, default=date.today)
    quality = Column(Integer, nullable=False)  # Оценка 0-5

    was_correct = Column(Boolean, nullable=False)  # True если quality >= 3

    def __repr__(self):
        return f"<Log(card='{self.card_hash[:8]}...', q={self.quality})>"
