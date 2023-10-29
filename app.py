import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_caching import Cache  # Import Flask-Caching
import requests
import calendar
from datetime import datetime, timedelta
import redis
import pytz
from functools import wraps

# Define the Pacific Time (Los Angeles) timezone
pacific = pytz.timezone('America/Los_Angeles')

USERNAME = os.getenv('BROADCASTIFY_USERNAME')
PASSWORD = os.getenv('BROADCASTIFY_PASSWORD')
FEEDID = os.getenv('FEED_ID')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
WEB_LOGIN_USERNAME = os.getenv('WEB_LOGIN_USERNAME')
WEB_LOGIN_PASSWORD = os.getenv('WEB_LOGIN_PASSWORD')
APP_SECRET_KEY = os.getenv('APP_SECRET_KEY')

# Configure Flask-Caching to use Redis
cache = Cache(config = {
    "DEBUG": True,
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 180,
    "CACHE_REDIS_HOST": 'redis',
    "CACHE_REDIS_PORT": 6379,
    "CACHE_REDIS_PASSWORD": REDIS_PASSWORD,
    "CACHE_REDIS_OPTIONS": {
      "socket_timeout": 5,
      "socket_connect_timeout": 5,
    }
})

app = Flask(__name__, template_folder='./templates')
app.secret_key = APP_SECRET_KEY
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
  # Define how to retrieve the user from your data source (e.g., a database)
  # Return the User object or None if the user does not exist
  # Example: user = User.query.get(user_id)
  return User(id=user_id)

@app.route('/protected')
@login_required
def protected():
  return "This is a protected route."

def login_required(view):
  @wraps(view)
  def wrapped_view(*args, **kwargs):
    if not current_user.is_authenticated:
      return redirect(url_for('login'))
    return view(*args, **kwargs)
  return wrapped_view

def is_valid_login(username, password):
  # Check if the provided username and password are valid
  valid_username = WEB_LOGIN_USERNAME
  valid_password = WEB_LOGIN_PASSWORD
  
  return username == valid_username and password == valid_password

# Define the base API endpoint URL
BASE_API_URL = f"https://api.broadcastify.com/owner/?a=archives&feedId={FEEDID}&u={USERNAME}&p={PASSWORD}&type=json&day="

@app.route('/')
@login_required
def index():
  today = datetime.now().date()
  three_months_ago = today - timedelta(days=45)
  return redirect(url_for('calendar_picker', year=today.year, month=today.month, day=today.day, start_year=three_months_ago.year, start_month=three_months_ago.month))

@app.route('/calendar/<int:year>/<int:month>/<int:day>/<int:start_year>/<int:start_month>')
@login_required
@cache.cached(timeout=3600)
def calendar_picker(year, month, day, start_year, start_month):
  # Calculate the first and last days for the calendar
  today = datetime.now().date()
  last_day = today - timedelta(days=1)  # Yesterday is the last selectable day
  last_date = today
  start_date = today - timedelta(days=45)

  # Ensure that the selected date is within the allowed range
  selected_date = datetime(year, month, day).date()
  if selected_date > last_date:
    return redirect(url_for('calendar_picker', year=last_date.year, month=last_date.month, day=last_date.day, start_year=start_year, start_month=start_month))
  if selected_date < start_date:
    return redirect(url_for('calendar_picker', year=start_date.year, month=start_date.month, day=start_date.day, start_year=start_year, start_month=start_month))

  # Generate a list of available dates for the current month
  available_dates = []
  while start_date <= last_date:
    date_str = start_date.strftime("%Y-%m-%d")
    api_url = f"{BASE_API_URL}{date_str}"
    response = requests.get(api_url)
    if response.status_code == 200:
      available_dates.append(date_str)
    start_date += timedelta(days=1)

  return render_template('calendar_picker.html', year=year, month=month, day=day, start_year=start_year, start_month=start_month, available_dates=available_dates)

@app.route('/archives/<date>')
@login_required
def archives(date):
  # Fetch data using the get_data_for_date function
  data = get_data_for_date(date)

  if data is None:
    # Handle the case when data is not available or an error occurs
    return render_template('error.html')

  # Extract the archives from the API response
  archives = data.get("archives", [])

  # Render the template and pass the archives and date to it
  return render_template('archives.html', archives=archives, date=date)

@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']

    if is_valid_login(username, password):
      user = User(id=username)
      login_user(user)
      flash('Logged in successfully!', 'success')
      return redirect(url_for('index'))
    else:
      flash('Invalid username or password', 'error')
      return redirect(url_for('login'))
  else:
    return render_template('login.html')

@cache.memoize(timeout=3600)
def get_data_for_date(date_str):
  api_url = f"{BASE_API_URL}{date_str}"
  response = requests.get(api_url)
  if response.status_code == 200:
    return response.json()
  return None

class User(UserMixin):
  def __init__(self, id):
    self.id = id

cache.init_app(app)  # Initialize the cache with your Flask app

if __name__ == '__main__':
  app.run(host='0.0.0.0', debug=True)