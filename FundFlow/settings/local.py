# SECURITY WARNING: don't run with debug turned on in production!
from FundFlow.settings.settings import *


DEBUG = True
ALLOWED_HOSTS = []


INSTALLED_APPS += [

]

MIDDLEWARE += [
]

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

MEDIA_URL = '/media/'  # URL to access media files
MEDIA_ROOT = BASE_DIR.parent / 'media'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.example.com'  # Your SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your_email@example.com'
EMAIL_HOST_PASSWORD = 'your_email_password'
DEFAULT_FROM_EMAIL = 'your_email@example.com'


# # CELERY SETTINGS
# CELERY_BROKER_URL = env.str('BROKER_URL')
# CELERY_RESULT_BACKEND = env.str('BROKER_URL')
# # CELERY_BROKER_URL = env.str('BROKER_URL_2')
# # CELERY_RESULT_BACKEND = env.str('BROKER_URL_2')
# CELERY_ACCEPT_CONTENT = ['application/json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = 'UTC'

# CELERY_IMPORTS = (
#     'posts.tasks'
# )

# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# import dj_database_url 
# prod_db  =  dj_database_url.config(conn_max_age=500)
# DATABASES['default'].update(prod_db)