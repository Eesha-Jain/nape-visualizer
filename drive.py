import os
import uuid
from flask import Flask, render_template, request
from google.oauth2 import service_account
import google.auth.transport.requests as google_auth_transport
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload, MediaIoBaseDownload
import io
from werkzeug.datastructures import FileStorage

# Google OAuth2 credentials
SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_KEY_FILE = 'token.json'
PARENT_FOLDER_ID = '1oj_F0Auv6qvwPp7dPAZzWnv6as44_7Hc'

def create_drive_service():
    # Create a service account credentials object
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY_FILE, scopes=SCOPES)

    # Obtain an authorized session
    auth_req = google_auth_transport.Request()
    creds.refresh(auth_req)

    # Build the Google Drive service using the credentials
    drive_service = build('drive', 'v3', credentials=creds)

    return drive_service

def upload(files):
    # Get the credentials and create a Google Drive client
    drive_service = create_drive_service()

    # Upload each file to Google Drive
    folder_id = create_folder()

    # Upload each file to Google Drive
    uploaded_files = []
    for file in files:
        # Ensure the file is not empty
        if file.filename == '':
            return "Error: Please select a file to upload."

        # Prepare the file metadata
        file_metadata = {'name': file.filename, 'parents': [folder_id]}

        # Get the file's binary data
        file_content = file.read()

        # Upload the file to Google Drive using MediaInMemoryUpload
        media = MediaInMemoryUpload(file_content, mimetype=file.mimetype, resumable=True)
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        uploaded_files.append(uploaded_file.get("id"))

    return uploaded_files

def create_folder():
    # Get the folder name from the HTML form
    folder_name = str(uuid.uuid1())

    drive_service = create_drive_service()

    # Create the folder in Google Drive
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [PARENT_FOLDER_ID]
    }
    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()

    # Convert the UUID object to a string
    folder_id_str = str(folder.get("id"))

    return folder_id_str

def get_file_by_id(file_id):
    drive_service = create_drive_service()

    # Get file metadata
    file_metadata = drive_service.files().get(fileId=file_id).execute()

    # Check if it's a regular file
    if file_metadata['mimeType'] != 'application/vnd.google-apps.folder':
        # Download the file content
        request = drive_service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        done = False
        while done is False:
            _, done = downloader.next_chunk()

        # Create a FileStorage object with the file content
        filename = file_metadata['name']
        mimetype = file_metadata['mimeType']
        file_storage = FileStorage(stream=file_stream, filename=filename, content_type=mimetype)

        return file_storage

    return None