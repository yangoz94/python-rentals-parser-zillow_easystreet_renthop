from __future__ import print_function
from dotenv import load_dotenv

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class SheetsAPI:
    def __init__(self):
        self.creds = None
        self.spreadsheet_id = os.environ['SAMPLE_SPREADSHEET_ID']
        self.range_name = os.environ['SAMPLE_RANGE_NAME']

    def authenticate(self):
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

    def getAllRows(self):
        try:
            service = build('sheets', 'v4', credentials=self.creds)

            # Call the Sheets API
            sheet = service.spreadsheets()
            result = sheet.values().get(spreadsheetId=self.spreadsheet_id, range=self.range_name).execute()
            values = result.get('values', [])

            if not values:
                print('No data found.')
                return values

            return values

        except HttpError as err:
            print(err)
            return []

    def addNewRow(self, new_row):
        try:
            service = build('sheets', 'v4', credentials=self.creds)

            # Call the Sheets API
            sheet = service.spreadsheets()
            result = sheet.values().get(spreadsheetId=self.spreadsheet_id, range=self.range_name).execute()
            existing_rows = result.get('values', [])

            if existing_rows:
                for row in existing_rows:
                    if row == new_row:
                        print('Row already exists.')
                        return

            value_input_option = 'RAW'
            insert_data_option = 'INSERT_ROWS'
            body = {
                'values': [new_row]
            }

            result = sheet.values().append(
                spreadsheetId=self.spreadsheet_id,
                range=self.range_name,
                valueInputOption=value_input_option,
                insertDataOption=insert_data_option,
                body=body
            ).execute()

            print('Row added successfully.')

        except HttpError as err:
            print(err)


sheets_api = SheetsAPI()
sheets_api.authenticate()

#TO-BE-REFACTORED AND MOVED TO A SEPERATE ENDPOINT
# Add a new row (TEST-
new_row = ['John', 'Doe2', 'john.doe@example.com']
sheets_api.addNewRow(new_row)
