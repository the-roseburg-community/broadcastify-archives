import os
from flask import Flask, render_template, request, redirect, url_for
from flask_caching import Cache  # Import Flask-Caching
import requests
import calendar
from datetime import datetime, timedelta
import redis
import pytz

# Define the Pacific Time (Los Angeles) timezone
pacific = pytz.timezone('America/Los_Angeles')

USERNAME = os.getenv('BROADCASTIFY_USERNAME')
PASSWORD = os.getenv('BROADCASTIFY_PASSWORD')
FEEDID = os.getenv('FEED_ID')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

# Configure Flask-Caching to use Redis
cache = Cache(config = {
    "DEBUG": True,
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 180,
    "CACHE_REDIS_HOST": 'redis',
    "CACHE_REDIS_PORT": 6379,
    "CACHE_REDIS_PASSWORD": REDIS_PASSWORD
})

app = Flask(__name__, template_folder='./templates')

# Define the base API endpoint URL
BASE_API_URL = f"https://api.broadcastify.com/owner/?a=archives&feedId={FEEDID}&u={USERNAME}&p={PASSWORD}&type=json&day="

@app.route('/')
def index():
  today = datetime.now().date()
  three_months_ago = today - timedelta(days=45)
  return redirect(url_for('calendar_picker', year=today.year, month=today.month, day=today.day, start_year=three_months_ago.year, start_month=three_months_ago.month))

@app.route('/calendar/<int:year>/<int:month>/<int:day>/<int:start_year>/<int:start_month>')
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
def archives(date):
  # Construct the API URL for the specified date
  api_url = f"{BASE_API_URL}{date}"

  # Fetch data from the API
  response = requests.get(api_url)
  data = response.json()

  # Extract the archives from the API response
  archives = data.get("archives", [])

  # Render the template and pass the archives and date to it
  return render_template('archives.html', archives=archives, date=date)

cache.init_app(app)  # Initialize the cache with your Flask app  # Move this line here

if __name__ == '__main__':
  app.run(host='0.0.0.0', debug=True)