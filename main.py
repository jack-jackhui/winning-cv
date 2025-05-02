import argparse
import logging
import os

from config.settings import Config
from job_processing.core import JobProcessor
from utils.logger import setup_logger
from utils.notifications import notify_all


class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)

def main(config_data: dict):
    # ----------------------------------------------------------------------
    # Set up Logging in a "logs" folder
    # ----------------------------------------------------------------------
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", "job_monitor.log")
    setup_logger(log_file=log_path, level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logging.info("Initializing SINGLE-RUN Job Monitor Application")

    # ----------------------------------------------------------------------
    # Initialize Application Components
    # ----------------------------------------------------------------------
    # Use passed config or load default
    config = Struct(**config_data)

    # ----------------------------------------------------------------------
    # Main Execution (Single Run, No Scheduler)
    # ----------------------------------------------------------------------
    try:
        processor = JobProcessor(config)
        results = processor.process_jobs()
        notify_all(len(results), results, config.airtable_ui_url)

        return results
    except Exception as e:
        logger.error(f"Main execution failed: {str(e)}")
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run job search and CV tailoring")
    parser.add_argument("--user-email", type=str, required=True, help="User email for job search session")
    args = parser.parse_args()
    config_data = {k.lower(): v for k, v in Config.__dict__.items() if not k.startswith("_")}
    config_data["user_email"] = args.user_email
    main(config_data)
