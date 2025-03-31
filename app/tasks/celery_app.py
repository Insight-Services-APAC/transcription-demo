from celery import Celery

def make_celery(app):
    celery = Celery(app.import_name, backend=app.config.get('result_backend') or app.config.get('CELERY_RESULT_BACKEND'), broker=app.config.get('broker_url') or app.config.get('CELERY_BROKER_URL'))
    celery.conf.update(app.config)
    celery.conf.broker_connection_retry_on_startup = True

    class ContextTask(celery.Task):

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery.Task = ContextTask
    return celery