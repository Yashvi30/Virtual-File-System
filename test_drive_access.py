from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = '/Users/tarandeepsinghkohli/Desktop/JIO_Cloud/service_credential_final.json'

# Load credentials and initialize the Google Drive service
try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)
except Exception as e:
    logging.error(f"Failed to initialize Google Drive service: {e}")
    raise

try:
    # Test listing files
    logging.info("Listing files in Google Drive...")
    results = service.files().list(fields="files(id, name, size)").execute()
    items = results.get('files', [])
    if not items:
        logging.info("No files found.")
    for item in items:
        logging.info(f"Found file: {item['name']} (ID: {item['id']}, Size: {item.get('size', 'Unknown')})")
except HttpError as e:
    logging.error(f"An error occurred: {e}")