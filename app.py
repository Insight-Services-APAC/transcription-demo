import os
from dotenv import load_dotenv
from app import create_app

# Load environment variables from .env file
load_dotenv()

# Get application environment from environment variable
env = os.environ.get('FLASK_ENV', 'development')

# Create Flask app
app = create_app(env)

if __name__ == '__main__':
    # Run development server
    app.run(host='0.0.0.0', port=5000, debug=(env == 'development'))