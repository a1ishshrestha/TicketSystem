from app import create_app, db

app = create_app()

with app.app_context():
    db.drop_all()  # Drops all tables
    db.create_all()  # Recreates tables from the models
    print("Database has been reset!")
    