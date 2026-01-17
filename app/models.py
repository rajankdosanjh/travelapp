import sqlalchemy as sa
import sqlalchemy.orm as so
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db
from datetime import datetime

CATEGORY_NAMES = {
    1: 'Food and Drink',
    2: 'History',
    3: 'Shopping',
    4: 'Nature',
    5: 'Art and Culture',
    6: 'Nightlife',
}

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
    feedbacks: so.Mapped[list["LocationFeedback"]] = so.relationship(
        back_populates="location", cascade="all, delete-orphan"
    )
    address: so.Mapped[str | None] = so.mapped_column(sa.String(200), nullable=True)

    @property
    def avg_sentiment(self):
        if not self.reviews:
            return 0
        return sum(r.sentiment for r in self.reviews) / len(self.reviews)

    @property
    def category_name(self):
        return CATEGORY_NAMES.get(self.category_id, 'Other')

    image: so.Mapped[str | None] = so.mapped_column(
        sa.String(200),
        nullable=True
    )

    def __repr__(self):
        return (f'Location(id={self.id}, name={self.name}, latitude={self.latitude}, longitude={self.longitude},'
                f'category_id={self.category_id}, address={self.address}, reviews={self.reviews}, image={self.image})')


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

    saved_routes: so.Mapped[list["SavedRoute"]] = so.relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    saved_places: so.Mapped[list["SavedPlace"]] = so.relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    location_feedbacks: so.Mapped[list["LocationFeedback"]] = so.relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    route_feedbacks: so.Mapped[list["RouteFeedback"]] = so.relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username}>"

class SavedRoute(db.Model):
    __tablename__ = 'saved_routes'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    distance: so.Mapped[float] = so.mapped_column(sa.Float)
    satisfaction: so.Mapped[float] = so.mapped_column(sa.Float)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('users.id'), index=True)
    travel_mode: so.Mapped[str] = so.mapped_column(sa.String(50), default="walking")  # 👈 NEW
    is_public: so.Mapped[bool] = so.mapped_column(sa.Boolean, default=False)

    user: so.Mapped[User] = so.relationship(back_populates="saved_routes")
    locations: so.Mapped[list[Location]] = so.relationship(secondary=saved_route_locations)
    feedbacks: so.Mapped[list["RouteFeedback"]] = so.relationship(
        back_populates="route", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f'<SavedRoute {self.id} by User {self.user.username}>'
    
class SavedPlace(db.Model):
    __tablename__ = 'saved_places'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    timestamp: so.Mapped[datetime] = so.mapped_column(sa.DateTime, default=datetime.utcnow)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('users.id'), index=True)
    location_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('locations.id'))
    photo_filename: so.Mapped[str | None] = so.mapped_column(sa.String(200), nullable=True)

    user: so.Mapped["User"] = so.relationship(back_populates="saved_places")
    location: so.Mapped["Location"] = so.relationship()


class LocationFeedback(db.Model):
    __tablename__ = 'location_feedback'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(500))
    rating: so.Mapped[float] = so.mapped_column(sa.Float)
    timestamp: so.Mapped[datetime] = so.mapped_column(sa.DateTime, default=datetime.utcnow)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('users.id'), index=True)
    location_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('locations.id'), index=True)

    user: so.Mapped["User"] = so.relationship(back_populates="location_feedbacks")
    location: so.Mapped["Location"] = so.relationship(back_populates="feedbacks")


class RouteFeedback(db.Model):
    __tablename__ = 'route_feedback'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(500))
    rating: so.Mapped[int] = so.mapped_column(sa.Integer)
    timestamp: so.Mapped[datetime] = so.mapped_column(sa.DateTime, default=datetime.utcnow)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('users.id'), index=True)
    route_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('saved_routes.id'), index=True)

    user: so.Mapped["User"] = so.relationship(back_populates="route_feedbacks")
    route: so.Mapped["SavedRoute"] = so.relationship(back_populates="feedbacks")
