import sqlalchemy as sa
import sqlalchemy.orm as so
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db

saved_route_locations = sa.Table('saved_route_locations', db.metadata,
    sa.Column('saved_route_id', sa.Integer, sa.ForeignKey('saved_routes.id'), primary_key=True),
    sa.Column('location_id', sa.Integer, sa.ForeignKey('locations.id'), primary_key=True)
)

class Location(db.Model):
    __tablename__ = 'locations'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(100), index=True, unique=True)
    latitude: so.Mapped[float] = so.mapped_column(sa.Float)
    longitude: so.Mapped[float] = so.mapped_column(sa.Float)
    category_id: so.Mapped[int] = so.mapped_column(sa.Integer, nullable=False)  # 1=Food, 2=History, etc.
    reviews:so.Mapped[list["Review"]] = so.relationship(back_populates="location")

    @property
    def avg_sentiment(self):
        if not self.reviews:
            return 0
        return sum(r.sentiment for r in self.reviews) / len(self.reviews)

    def __repr__(self):
        return (f'Location(id={self.id}, name={self.name}, latitude={self.latitude}, longitude={self.longitude},'
                f'category_id={self.category}, reviews={self.reviews})')


class Review(db.Model):
    __tablename__ ='reviews'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    text: so.Mapped[str] = so.mapped_column(sa.String(500))
    sentiment: so.Mapped[float] = so.mapped_column(sa.Float)
    location_id: so.Mapped[int]= so.mapped_column(sa.ForeignKey('locations.id'))
    location: so.Mapped[Location] = so.relationship(back_populates="reviews")
    username: so.Mapped[str] = so.mapped_column(sa.String(100))

    def __repr__(self):
        return (f'Review for {self.location.name}: {self.text}')


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(100))
    username: so.Mapped[str] = so.mapped_column(sa.String(100), index=True, unique=True)
    password_hash: so.Mapped[str] = so.mapped_column(sa.String(128))
    saved_routes: so.Mapped[list["SavedRoute"]] = so.relationship(back_populates="user", cascade="all, delete-orphan")


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class SavedRoute(db.Model):
    __tablename__ = 'saved_routes'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    distance: so.Mapped[float] = so.mapped_column(sa.Float)
    satisfaction: so.Mapped[float] = so.mapped_column(sa.Float)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('users.id'), index=True)

    user: so.Mapped[User] = so.relationship(back_populates="saved_routes")
    locations: so.Mapped[list[Location]] = so.relationship(secondary=saved_route_locations)

    def __repr__(self):
        return f'<SavedRoute {self.id} by User {self.user.username}>'