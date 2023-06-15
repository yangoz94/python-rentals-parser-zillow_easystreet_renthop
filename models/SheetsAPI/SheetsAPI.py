import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()


class SheetsAPI:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    def __init__(self):
        self.creds = None
        self.spreadsheet_id = os.environ['SPREADSHEET_ID']
        self.range_name = os.environ['RANGE_NAME']
        self.authenticate()

    def authenticate(self):
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

    def get_all_rows(self) -> list:
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

    def add_new_row(self, new_row: list) -> bool:
        try:
            service = build('sheets', 'v4', credentials=self.creds)

            # Call the Sheets API
            sheet = service.spreadsheets()
            result = sheet.values().get(spreadsheetId=self.spreadsheet_id, range=self.range_name).execute()
            existing_rows = result.get('values', [])

            if existing_rows:
                for row in existing_rows:
                    if row[0] == new_row[0]: # row[0] is the url as the unique identifier
                        raise ValueError('Row already exists.')

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

            return True

        except ValueError as err:
            print(err)
            return False

        except HttpError as err:
            print(err)
            return False
        except Exception as e:
            print(e)
            return False