import os
from dotenv import load_dotenv

load_dotenv()

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = 'alexandre.brief2.0@gmail.com'
BASE_URL = 'http://localhost:5000'
