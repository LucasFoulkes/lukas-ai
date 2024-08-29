import os
import re
import zipfile
import logging
import shutil

logger = logging.getLogger(__name__)

DOWNLOADS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "downloads")
)


def handle_file(filename, message_queue):
    pattern = r"SearchBot_results_for_.*\.zip"
    if re.match(pattern, filename):
        _process_matching_file(filename, message_queue)
    else:
        _save_to_downloads(filename)


def _process_matching_file(filename, message_queue):
    try:
        with zipfile.ZipFile(filename, "r") as zip_ref:
            zip_ref.extractall(path=".")

        os.remove(filename)
        logger.info(f"Unzipped and deleted the file: {filename}")

        extracted_files = zip_ref.namelist()
        txt_files = [f for f in extracted_files if f.endswith(".txt")]

        if txt_files:
            txt_file_path = txt_files[0]  # Assuming there's only one .txt file
            with open(txt_file_path, "r") as txt_file:
                txt_contents = f"::::DATA::::\n{txt_file.read()}"
                logger.info(f"Extracted contents of {txt_contents}")
                _send_to_queue(txt_contents, message_queue)
                logger.info(f"Sent contents of {txt_file_path} to queue")

            # Delete the extracted txt file after sending its contents
            os.remove(txt_file_path)
            logger.info(f"Deleted extracted file: {txt_file_path}")
        else:
            logger.warning(
                f"No .txt files found in the extracted contents of {filename}"
            )

    except Exception as e:
        logger.error(f"Error processing {filename}: {str(e)}")
        _save_to_downloads(filename)


def _save_to_downloads(filename):
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    source_path = os.path.abspath(filename)
    destination_path = os.path.join(DOWNLOADS_DIR, os.path.basename(filename))

    # Ensure we don't overwrite existing files
    counter = 1
    while os.path.exists(destination_path):
        name, ext = os.path.splitext(os.path.basename(filename))
        new_filename = f"{name}_{counter}{ext}"
        destination_path = os.path.join(DOWNLOADS_DIR, new_filename)
        counter += 1

    shutil.move(source_path, destination_path)
    logger.info(f"File {filename} moved to {destination_path}")


def _send_to_queue(message, message_queue):
    message_queue.put(message)
    logger.info(f"Queued message: {message}")
