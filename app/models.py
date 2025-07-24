from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db


class Location(db.Model):
    __tablename__ = 'locations'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(100), index=True, unique=True)
    latitude: so.Mapped[float] = so.mapped_column(sa.Float)
    longitude: so.Mapped[float] = so.mapped_column(sa.Float)
    category: so.Mapped[int] = so.mapped_column(sa.Integer, nullable=False)  # 1=Food, 2=History, etc.
    tiktok_rating: so.Mapped[float] = so.mapped_column(sa.Float)  # Aggregated from TikTok data

    def __repr__(self):
        return (f'Location(id={self.id}, name={self.name}, latitude={self.latitude}, longitude={self.longitude},'
                f'category={self.category}, tiktok_rating={self.tiktok_rating})')