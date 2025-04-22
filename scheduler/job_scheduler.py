from apscheduler.schedulers.background import BackgroundScheduler
import logging

class JobScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.logger = logging.getLogger(__name__)

    def add_job(self, func, interval_minutes, name=None):
        self.scheduler.add_job(
            func,
            'interval',
            minutes=interval_minutes,
            max_instances=1,
            name=name
        )
        self.logger.info(f"Added scheduled job to run every {interval_minutes} minutes")

    def start(self):
        try:
            self.scheduler.start()
            self.logger.info("Scheduler started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {str(e)}")

    def block(self):
        """Block the main thread so the script keeps running."""
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def shutdown(self):
        self.logger.info("Shutting down scheduler...")
        self.scheduler.shutdown()
        self.logger.info("Scheduler shut down successfully")