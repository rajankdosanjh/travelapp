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
    category_id: so.Mapped[int] = so.mapped_column(sa.Integer, nullable=False)  # 1=Food, 2=History, etc.
    rating: so.Mapped[float] = so.mapped_column(sa.Float)  #
    reviews:so.Mapped[list["Review"]] = so.relationship(back_populates="location")


    def __repr__(self):
        return (f'Location(id={self.id}, name={self.name}, latitude={self.latitude}, longitude={self.longitude},'
                f'category_id={self.category}, rating={self.tiktok_rating}, reviews={self.reviews})')


class Review(db.Model):
    __tablename__ ='reviews'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    text: so.Mapped[str] = so.mapped_column(sa.String(500))
    sentiment: so.Mapped[float] = so.mapped_column(sa.Float)
    location_id: so.Mapped[int]= so.mapped_column(sa.ForeignKey('locations.id'))
    location: so.Mapped[Location] = so.relationship(back_populates="reviews")

    def __repr__(self):
        return (f'Review for {self.location.name}: {self.text}')


