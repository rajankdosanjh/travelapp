import csv
from app import app, db
from app.models import Location

def reset_db():
    with app.app_context():
        try:
            print("--- Dropping all database tables... ---")
            db.drop_all()
            print("--- Creating all database tables... ---")
            db.create_all()

            print(f"--- Reading locations from {app.config['LOCATIONS_CSV_PATH']} ---")
            with open(app.config['LOCATIONS_CSV_PATH'], mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                locations_to_add = []
                for row in reader:
                    location = Location(
                        name=row['name'],
                        latitude=float(row['latitude']),
                        longitude=float(row['longitude']),
                        category_id=int(row['category_id']),
                        rating=float(row['rating'])
                    )
                    locations_to_add.append(location)

                print(f"--- Adding {len(locations_to_add)} new locations to the session... ---")
                db.session.bulk_save_objects(locations_to_add)

            print("--- Committing the session to the database... ---")
            db.session.commit()
            print("--- Database reset and population complete. ---")

        except FileNotFoundError:
            print(f"Error: The file {app.config['LOCATIONS_CSV_PATH']} was not found.")
        except Exception as e:
            print(f"An error occurred during database reset: {e}")
            db.session.rollback()