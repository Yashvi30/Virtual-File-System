import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Define the scope for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']

# Path to the service account credentials JSON file
SERVICE_ACCOUNT_FILE = '/Users/tarandeepsinghkohli/Desktop/JIO_Cloud/service_credential_final.json'

# Function to authenticate and get the service object
def authenticate():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)
    return service

# Function to upload a file to Google Drive root directory
def upload_file(service, file_name, file_path):
    file_metadata = {
        'name': file_name,
        'parents': ['root']  # This specifies that the file should be added to the root directory
    }
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f'File ID: {file.get("id")}')
    print(f'File "{file_name}" uploaded successfully.')

# Main function to run the script
def main():
    # Authenticate and get the service object
    service = authenticate()

    # Example file to upload (change these paths to your actual file paths)
    file_name = 'Capstone_Report_Final.docx'
    file_path = '/Users/tarandeepsinghkohli/Downloads/Capstone_Report_Final.docx'

    # Upload the file to Google Drive root directory
    upload_file(service, file_name, file_path)

if __name__ == '__main__':
    main()