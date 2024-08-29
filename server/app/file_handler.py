import os
import re
import zipfile
import shutil
import logging


class FileHandler:
    def __init__(self, filename, queue_manager):
        self.filename = filename
        self.queue_manager = queue_manager
        self.logger = logging.getLogger(__name__)

    def handle_file(self):
        pattern = r"SearchBot_results_for_.*\.zip"
        if re.match(pattern, self.filename):
            self._process_matching_file()
        else:
            self._save_to_downloads()

    def _process_matching_file(self):
        try:
            with zipfile.ZipFile(self.filename, "r") as zip_ref:
                file_list = zip_ref.namelist()
                if len(file_list) != 1 or not file_list[0].endswith(".txt"):
                    raise ValueError(
                        "Expected exactly one .txt file in the zip archive"
                    )

                txt_file_name = file_list[0]
                with zip_ref.open(txt_file_name) as txt_file:
                    txt_contents = txt_file.read().decode("utf-8")
                    self.queue_manager.send_to_queue(txt_contents)
                    self.logger.info(f"Sent contents of {txt_file_name} to queue")

            os.remove(self.filename)
            self.logger.info(f"Processed and deleted the file: {self.filename}")
        except Exception as e:
            self.logger.error(f"Error processing {self.filename}: {str(e)}")
            self._save_to_downloads()  # Fallback to saving the file if processing fails

    def _save_to_downloads(self):
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True)

        base, extension = os.path.splitext(self.filename)
        counter = 1
        destination = os.path.join(downloads_dir, self.filename)

        while os.path.exists(destination):
            new_filename = f"{base}_{counter}{extension}"
            destination = os.path.join(downloads_dir, new_filename)
            counter += 1

        shutil.move(self.filename, destination)
        self.logger.info(
            f"File {self.filename} didn't match the pattern. Moved to {destination}"
        )
