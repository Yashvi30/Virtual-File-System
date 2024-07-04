import logging
import os
import stat
import time
import errno
import io
from fuse import FUSE, FuseOSError, Operations
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[
                        logging.StreamHandler(),
                        logging.FileHandler('google_drive_fs.log')
                    ])

# Constants
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive'
]
SERVICE_ACCOUNT_FILE = '/Users/tarandeepsinghkohli/Desktop/JIO_Cloud/service_credential_final.json'  # Update with the correct path


class GoogleDriveFS(Operations):
    def __init__(self):
        self.credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        self.service = build('drive', 'v3', credentials=self.credentials)
        self.path_to_file_id = {}
        self.file_id_to_path = {}
        self.open_files = {}

        # Initialize mapping from Google Drive
        self._initialize_file_mapping()

    def _initialize_file_mapping(self):
        logging.debug("Initializing file mapping from Google Drive (My Drive)...")
        try:
            root_files = self.service.files().list(
                q=f"'1dkfbfyQYLnckre8Xz9NB8WjDcLXOAxrC' in parents and trashed=false",
                fields="files(id, name, size)").execute().get('files', [])

            logging.debug(f"Fetched {len(root_files)} files from My Drive")

            for file in root_files:
                file_path = '/' + file['name']
                self.path_to_file_id[file_path] = file['id']
                self.file_id_to_path[file['id']] = file_path
                logging.debug(f"Mapping file {file_path} to ID {file['id']}")

        except HttpError as e:
            logging.error(f"Failed to fetch file list from Google Drive: {e}")
            raise FuseOSError(errno.EIO)
        logging.debug("File mapping initialization completed.")

    def _get_file_id(self, path):
        logging.debug(f"Retrieving file ID for path: {path}")
        normalized_path = os.path.normpath(path)
        return self.path_to_file_id.get(normalized_path, None)

    def getattr(self, path, fh=None):
        logging.debug(f"getattr called for path: {path}")

        if path == '/':
            attrs = {
                'st_mode': stat.S_IFDIR | 0o755,
                'st_nlink': 2,
                'st_ctime': time.time(),
                'st_mtime': time.time(),
                'st_atime': time.time()
            }
            return attrs

        if path.startswith('/.'):
            raise FuseOSError(errno.ENOENT)

        file_id = self._get_file_id(path)
        logging.debug(f"File ID for path {path}: {file_id}")

        if file_id is None:
            logging.error(f"File not found for path: {path}")
            raise FuseOSError(errno.ENOENT)

        try:
            file_metadata = self.service.files().get(fileId=file_id, fields='size').execute()
            logging.debug(f"File metadata for {path}: {file_metadata}")

            attrs = {
                'st_mode': stat.S_IFREG | 0o644,
                'st_size': int(file_metadata.get('size', 0)),
                'st_ctime': time.time(),
                'st_mtime': time.time(),
                'st_atime': time.time()
            }
            return attrs

        except HttpError as e:
            logging.error(f"Google Drive API error: {e}")
            raise FuseOSError(errno.EIO)

        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            raise FuseOSError(errno.EIO)

    def readdir(self, path, fh):
        logging.debug(f"readdir called for path: {path}")
        normalized_path = os.path.normpath(path)

        if normalized_path == '/':
            try:
                files = self.service.files().list(
                    q=f"'1dkfbfyQYLnckre8Xz9NB8WjDcLXOAxrC' in parents and trashed=false",
                    fields="files(id, name)").execute().get('files', [])

                entries = ['.', '..']
                for file in files:
                    entries.append(file['name'])

                return entries

            except HttpError as e:
                logging.error(f"Failed to list directory contents: {e}")
                raise FuseOSError(errno.EIO)

        else:
            file_id = self._get_file_id(normalized_path)
            try:
                files = self.service.files().list(
                    q=f"'{file_id}' in parents and trashed=false",
                    fields="files(id, name)").execute().get('files', [])

                entries = ['.', '..']
                for file in files:
                    entries.append(file['name'])

                return entries

            except HttpError as e:
                logging.error(f"Failed to list directory contents: {e}")
                raise FuseOSError(errno.EIO)

    def open(self, path, flags):
        logging.debug(f"open called for path: {path} with flags: {flags}")
        file_id = self._get_file_id(path)
        if file_id is None:
            logging.error(f"File not found for path: {path}")
            raise FuseOSError(errno.ENOENT)

        self.open_files[path] = {'file_id': file_id, 'content': None, 'size': 0, 'downloader': None}
        logging.debug(f"File opened for path: {path}, file_id: {file_id}")
        return 0

    def read(self, path, size, offset, fh):
        logging.debug(f"read called for path: {path} with size: {size} and offset: {offset}")
        file_info = self.open_files.get(path)
        if file_info is None:
            logging.error(f"File not opened: {path}")
            raise FuseOSError(errno.ENOENT)

        if file_info['content'] is None:
            request = self.service.files().get_media(fileId=file_info['file_id'])
            file_info['content'] = io.BytesIO()
            file_info['downloader'] = MediaIoBaseDownload(file_info['content'], request)
            logging.debug(f"Downloader initialized for file_id: {file_info['file_id']}")

        while file_info['size'] < offset + size:
            status, done = file_info['downloader'].next_chunk()
            if status:
                logging.debug(f"Download progress for {path}: {int(status.progress() * 100)}%")
            if done:
                logging.debug(f"Download completed for {path}")
                break

        file_info['size'] = file_info['content'].tell()
        file_info['content'].seek(0)
        data = file_info['content'].read(offset + size)[offset:]
        logging.debug(f"Returning {len(data)} bytes for read request on path: {path}")
        return data

    def getxattr(self, path, name, position=0):
        raise FuseOSError(errno.ENOTSUP)

    def listxattr(self, path):
        return []

    def debug_file_mapping(self):
        logging.debug("Current file path to ID mapping:")
        for path, file_id in self.path_to_file_id.items():
            logging.debug(f"Path: {path} -> File ID: {file_id}")


def main(mountpoint):
    fs = GoogleDriveFS()
    fs.debug_file_mapping()
    FUSE(fs, mountpoint, nothreads=True, foreground=True)


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python gdrivefs.py <mountpoint>")
        sys.exit(1)
    main(sys.argv[1])