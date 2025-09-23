# SECURITY WARNING: don't run with debug turned on in production!
from FundFlow.settings.settings import *


DEBUG = False
ALLOWED_HOSTS = ['djangoarticle.herokuapp.com', '127.0.0.1']


INSTALLED_APPS += [

]

MIDDLEWARE += [
    'whitenoise.middleware.WhiteNoiseMiddleware',    
]

TIMEOUT = 7 * 24 * 3600

import ssl
CELERY_BROKER_URL = 'rediss://:p31597f53c1a12263faad1db77cd4d0b6a20b35c04d66121d01d7b11efc4a944c@ec2-3-213-255-205.compute-1.amazonaws.com:16570'
CELERY_RESULT_BACKEND = 'rediss://:p31597f53c1a12263faad1db77cd4d0b6a20b35c04d66121d01d7b11efc4a944c@ec2-3-213-255-205.compute-1.amazonaws.com:16570'
# CELERY_BROKER_URL = 'redis://localhost:6379'
# CELERY_RESULT_BACKEND = 'redis://localhost:6379'
# CELERY_ACCEPT_CONTENT = ['application/json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = 'UTC'
BROKER_USE_SSL={'ssl_cert_reqs': ssl.CERT_NONE}
CELERY_REDIS_BACKEND_USE_SSL={'ssl_cert_reqs': ssl.CERT_NONE}

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

import dj_database_url 
prod_db  =  dj_database_url.config(conn_max_age=500)
DATABASES['default'].update(prod_db)