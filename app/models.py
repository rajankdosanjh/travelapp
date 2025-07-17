from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_login import UserMixin
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
from dataclasses import dataclass
import datetime

@dataclass
class Location(db.Model):
    class Location:
        def __init__(self, name: str, latitude: float, longitude: float, description: str = "",
                     tiktok_review_score: float = 0.0):
            self.name = name
            self.latitude = latitude
            self.longitude = longitude
            self.description = description




class Route(db.Model):