import asyncio
import logging
import subprocess
from datetime import datetime, timedelta, timezone
import time


class GitUpdater:
    def __init__(self) -> None:
        self.date_format: str = "%d/%m/%Y %H:%M:%S"
        logging.basicConfig()
        self.logger = logging.getLogger("gitupdater")
        self.logger.level = logging.INFO
        self.logger.info(f"Last Git Update: {self.get_last_git_update()}")
        self.is_generator_enabled: bool = True
        self.loop: asyncio.AbstractEventLoop | None = None

    def get_last_git_update(self) -> datetime | None:
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "-1",
                    "--format=%cd",
                    f"--date=format:'{self.date_format}'",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            last_update = result.stdout.strip()
            # Convert to Moscow time (UTC+3)
            utc_time = datetime.strptime(
                last_update, f"'{self.date_format}'"
            ).astimezone(timezone(timedelta(hours=3)))
            return utc_time
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Error while checking last Git update: {e}")
            return None

    @property
    def is_latest_version(self) -> bool:
        try:
            subprocess.run(["git", "fetch"], check=True)
            local_head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

            remote_head = subprocess.run(
                ["git", "rev-parse", "@{u}"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

            return local_head == remote_head
        except subprocess.CalledProcessError as e:
            self.logger.warning(
                f"Error while checking if the latest version is installed: {e}"
            )
            return False

    def update(self):
        try:
            subprocess.run(["git", "pull"], check=True)
            self.logger.info("Repository successfully updated to the latest version.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error while updating the repository: {e}")

    async def generator_enter(self):
        self.logger.info(self.is_generator_enabled)

        while self.is_generator_enabled:
            if not self.is_latest_version:
                self.update()
                self.restart_application()
            self.logger.info(self.get_last_git_update())
            await asyncio.sleep(20)

    def restart_application(self):
        try:
            self.logger.info("Restarting application...")
            subprocess.run(["poetry", "run", "run"], check=True)
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error while restarting the application: {e}")
        finally:
            exit()
    def __enter__(self):
        self.logger.info("Entering context manager.")
        if not self.loop:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.create_task(self.generator_enter())
            self.loop.run_in_executor(None, self.loop.run_forever)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        self.logger.info("Exiting context manager.")
        self.is_generator_enabled = False
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)


updater = GitUpdater()
if __name__ == "__main__":
    with updater:
        while True:
            time.sleep(1)
