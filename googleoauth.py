from google.oauth2 import service_account
from googleapiclient.discovery import build

# Replace with your own credentials and service account file path
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = '/Users/tarandeepsinghkohli/Desktop/JIO_Cloud/service_credential_final.json'

# Authenticate and create a service object
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=credentials)

# List files in the root directory
results = service.files().list(
    q="'root' in parents and trashed=false",
    fields="files(id, name)").execute()

files = results.get('files', [])
if not files:
    print('No files found in the root directory.')
else:
    print('Files in the root directory:')
    for file in files:
        print(f'{file["name"]} ({file["id"]})')