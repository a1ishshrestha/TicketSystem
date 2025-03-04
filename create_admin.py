from app import create_app, db  # Import create_app and db from your app package
from app.models import User  # Import the User model
from werkzeug.security import generate_password_hash

app = create_app()  # Initialize the app

with app.app_context():  # Use the app context for database operations
    # Check if the admin user already exists
    admin = User.query.filter_by(username='admin').first()

    if not admin:
        # Create the admin user if it doesn't exist
        hashed_password = generate_password_hash('Thapa1234!')  # Replace with a secure password
        admin = User(username='admin', password=hashed_password, role='admin')
        
        # Add admin to the database
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")
    else:
        print("Admin user already exists.")
