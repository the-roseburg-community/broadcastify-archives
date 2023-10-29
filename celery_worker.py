import os
from celery import Celery
from app import cache, get_data_for_date

REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

celery = Celery(__name__, broker='redis://default:' + REDIS_PASSWORD + '@redis:6379/0')

celery.conf.update(
  CACHE_TYPE='RedisCache',
  CACHE_DEFAULT_TIMEOUT=1800,
  CACHE_REDIS_HOST='redis',
  CACHE_REDIS_PORT=6379,
  CACHE_REDIS_PASSWORD=REDIS_PASSWORD,
)

@celery.task
def update_cache(date):
  # Fetch data and update the cache here
  data = get_data_for_date(date)
  if data is not None:
    cache.set(date, data, timeout=1800)

if __name__ == '__main__':
  celery.start()