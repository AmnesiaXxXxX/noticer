import subprocess
from datetime import datetime
import logging


class GitUpdater:
    def __init__(self) -> None:
        self.date_format: str = "%d/%m/%Y %H:%M:%S"
        self.logger = logging.getLogger("gitupdater")
        self.get_last_git_update()

    def get_last_git_update(self) -> datetime | None:
        try:
            # Get the date of the last commit
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
            return datetime.strptime(last_update, self.date_format)
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Error while checking last Git update: {e}")
            return None

    @property
    def is_latest_version(self) -> bool:
        try:
            # Fetch the latest changes from the remote repository
            subprocess.run(["git", "fetch"], check=True)

            # Compare the local HEAD with the remote HEAD
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
