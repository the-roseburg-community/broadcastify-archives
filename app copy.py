import os
from flask import Flask, render_template, request, redirect, url_for
import requests
import calendar
from datetime import datetime, timedelta

USERNAME = os.getenv('BROADCASTIFY_USERNAME')
PASSWORD = os.getenv('BROADCASTIFY_PASSWORD')
FEEDID = os.getenv('FEED_ID')
app = Flask(__name__, template_folder='./templates')

# Define the base API endpoint URL
BASE_API_URL = f"https://api.broadcastify.com/owner/?a=archives&feedId={FEEDID}&u={USERNAME}&p={PASSWORD}&type=json&day="

@app.route('/')
def index():
  today = datetime.now().date()
  three_months_ago = today - timedelta(days=45)
  return redirect(url_for('calendar_picker', year=today.year, month=today.month, day=today.day, start_year=three_months_ago.year, start_month=three_months_ago.month))

@app.route('/calendar/<int:year>/<int:month>/<int:day>/<int:start_year>/<int:start_month>')
def calendar_picker(year, month, day, start_year, start_month):
  # Calculate the first and last days for the calendar
  _, last_day = calendar.monthrange(year, month)
  last_date = datetime(year, month, last_day)
  start_date = datetime(start_year, start_month, 1)

  # Ensure that the selected date is within the allowed range
  selected_date = datetime(year, month, day)
  if selected_date > last_date:
    return redirect(url_for('calendar_picker', year=year, month=month, day=last_day, start_year=start_year, start_month=start_month))
  if selected_date < start_date:
    return redirect(url_for('calendar_picker', year=start_year, month=start_month, day=1, start_year=start_year, start_month=start_month))

  # Generate a list of available dates for the current month
  available_dates = []
  for d in range((last_date - start_date).days + 1):
    date = start_date + timedelta(days=d)
    date_str = date.strftime("%Y-%m-%d")
    api_url = f"{BASE_API_URL}{date_str}"
    response = requests.get(api_url)
    if response.status_code == 200:
      available_dates.append(date_str)

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

if __name__ == '__main__':
  app.run(host='0.0.0.0', debug=True)
