from app import db
from app.models import Location

def reset_db():
    db.drop_all()
    db.create_all()

    locations = [
        # Food & Drink (Category 1)
        {'name': 'Dishoom Covent Garden', 'latitude': 51.5126, 'longitude': -0.1243, 'category': 1,
         'tiktok_rating': 4.8},
        {'name': 'Borough Market', 'latitude': 51.5056, 'longitude': -0.0913, 'category': 1, 'tiktok_rating': 4.7},
        {'name': 'The Wolseley', 'latitude': 51.5079, 'longitude': -0.1426, 'category': 1, 'tiktok_rating': 4.5},
        {'name': 'Flat Iron Square', 'latitude': 51.5025, 'longitude': -0.0876, 'category': 1, 'tiktok_rating': 4.3},

        # Historical Sites (Category 2)
        {'name': 'Tower of London', 'latitude': 51.5081, 'longitude': -0.0759, 'category': 2, 'tiktok_rating': 4.9},
        {'name': 'Westminster Abbey', 'latitude': 51.4994, 'longitude': -0.1273, 'category': 2, 'tiktok_rating': 4.8},
        {'name': 'St. Paul\'s Cathedral', 'latitude': 51.5138, 'longitude': -0.0983, 'category': 2,
         'tiktok_rating': 4.7},


        # Shopping (Category 3)
        {'name': 'Harrods', 'latitude': 51.4996, 'longitude': -0.1634, 'category': 3, 'tiktok_rating': 4.7},
        {'name': 'Oxford Street', 'latitude': 51.5154, 'longitude': -0.1412, 'category': 3, 'tiktok_rating': 4.5},
        {'name': 'Covent Garden Market', 'latitude': 51.5129, 'longitude': -0.1223, 'category': 3,
         'tiktok_rating': 4.4},
        {'name': 'Liberty London', 'latitude': 51.5139, 'longitude': -0.1448, 'category': 3, 'tiktok_rating': 4.3},

        # Nature/Parks (Category 4)
        {'name': 'Hyde Park', 'latitude': 51.5073, 'longitude': -0.1657, 'category': 4, 'tiktok_rating': 4.8},
        {'name': 'Regent\'s Park', 'latitude': 51.5310, 'longitude': -0.1593, 'category': 4, 'tiktok_rating': 4.6},


        # Art & Culture (Category 5)
        {'name': 'British Museum', 'latitude': 51.5194, 'longitude': -0.1269, 'category': 5, 'tiktok_rating': 4.9},
        {'name': 'Tate Modern', 'latitude': 51.5076, 'longitude': -0.0994, 'category': 5, 'tiktok_rating': 4.8},
        {'name': 'National Gallery', 'latitude': 51.5089, 'longitude': -0.1283, 'category': 5, 'tiktok_rating': 4.7},
        {'name': 'Victoria and Albert Museum', 'latitude': 51.4966, 'longitude': -0.1722, 'category': 5,
         'tiktok_rating': 4.6},

        # Nightlife (Category 6)
        {'name': 'Fabric Nightclub', 'latitude': 51.5203, 'longitude': -0.1048, 'category': 6, 'tiktok_rating': 4.5},
        {'name': 'Ministry of Sound', 'latitude': 51.4975, 'longitude': -0.0997, 'category': 6, 'tiktok_rating': 4.4},
        {'name': 'The Roxy', 'latitude': 51.5132, 'longitude': -0.1313, 'category': 6, 'tiktok_rating': 4.3},
        {'name': 'Cirque le Soir', 'latitude': 51.5135, 'longitude': -0.1358, 'category': 6, 'tiktok_rating': 4.2}
    ]

    for loc in locations:
        db.session.add(Location(**loc))

    db.session.commit()
