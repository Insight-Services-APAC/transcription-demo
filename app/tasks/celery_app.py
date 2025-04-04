from celery import Celery


def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config.get("result_backend"),
        broker=app.config.get("broker_url")
    )
    celery.conf.update(app.config)
    celery.conf.broker_connection_retry_on_startup = True

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery