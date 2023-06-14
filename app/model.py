from __future__ import print_function
from datetime import datetime
import aiohttp
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()


class ListingParser:
    SUPPORTED_URLS = {'streeteasy.com', 'zillow.com', 'renthop.com'}

    def __init__(self, url):
        self.url = url

    async def fetch_listing_data(self) -> str:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, headers=headers) as response:
                    response.raise_for_status()
                    return await response.text()

        except aiohttp.ClientError as e:
            raise Exception('Error fetching listing data: {}'.format(str(e)))

    def extract_base_url(self) -> str or None:
        pattern = r"(?:https?://)?(?:www\.)?([^/]+\.com)"
        match = re.match(pattern, self.url)
        if match:
            return match.group(1)
        return None

    def is_supported_url(self) -> bool:
        base_url = self.extract_base_url()
        if base_url and any(supported_url in base_url for supported_url in self.SUPPORTED_URLS):
            return True
        return False

    def extract_attributes(self, html_text: str) -> dict:
        address = None
        neighborhood = None
        number_of_rooms = None
        price = None
        description = None
        available_on = None

        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            if "streeteasy.com" in self.url:
                address_element = soup.find('h1', {'class': 'building-title'})
                if address_element:
                    address = address_element.text.strip()

                number_of_rooms_elements = soup.findAll('li', {'class': 'detail_cell'})
                if len(number_of_rooms_elements) >= 2:
                    number_of_rooms = number_of_rooms_elements[1].text.strip()[0] + 'BR'

                price_element = soup.find('div', {'class': 'price'})
                if price_element:
                    price_text = price_element.text.strip()
                    price_pattern = r"\$(\d{1,3}(?:,\d{3})*)(?:\.\d{2})?"
                    match = re.search(price_pattern, price_text)
                    price = match.group(1) if match else None

                description_element = soup.find('div', {'id': 'full-content'})
                if description_element:
                    description = description_element.text.strip().replace('\n', ' ')

                neighborhood_elements = soup.find('ul', {'class': 'Breadcrumb Breadcrumb--detailsPage'}).find_all('li')
                if len(neighborhood_elements) >= 3:
                    neighborhood = neighborhood_elements[2].text.strip()

                available_on_element = soup.find('div', {'class': 'Vitals-data'})
                if available_on_element:
                    if available_on_element.text.strip() == "Available Now":
                        available_on = "Available Immediately"
                    else:

                        available_on = datetime.strptime(
                            available_on_element.text.strip(), "%m/%d/%Y"
                        ).strftime("%a %b %d %Y")

            elif "zillow.com" in self.url:
                summary_container = soup.find('div', {'class': 'summary-container'})
                if summary_container:
                    address_raw = summary_container.find_all('h1')[0].text.strip()
                    address = re.sub(r',([^,]+,[^,]+)$', '', address_raw) if address_raw else None
                    number_of_rooms_elements = summary_container.find_all('strong')
                    number_of_rooms = number_of_rooms_elements[0].text.strip() if number_of_rooms_elements else None

                    price_element = summary_container.find('span')
                    price_raw = price_element.text.strip() if price_element else None
                    price = re.sub(r'\$|/mo', '', price_raw) if price_raw else None

                data_view_container = soup.find('div', {'class': 'data-view-container'})

                if data_view_container:
                    description_overview = data_view_container.find('h4', string='Overview')

                    if description_overview:
                        description_raw = description_overview.find_next_sibling('div').text.strip()

                        description = re.sub(

                            r"Show more.*$", "", description_raw, flags=re.MULTILINE

                        ).replace('\n', ' ').replace("Hide", "").strip()

                    available_on_element = data_view_container.find('span', string="Date available")
                    if available_on_element:
                        available_on = available_on_element.find_next_sibling('span').text.strip()
                    else:
                        available_on = "Not specified"

            elif "renthop.com" in self.url:
                address_element = soup.find('h1', {'class': 'font-size-16 b overflow-ellipsis'})
                if address_element:
                    address = address_element.find('a').text.strip() if address_element.find('a') else None

                number_of_rooms_element = soup.find('div', {'style': 'margin-left: 4px;'})
                if number_of_rooms_element is not None:
                    number_of_rooms = number_of_rooms_element.text.strip().replace(' Bed', 'BR').replace('\n',"") if number_of_rooms_element.text.strip() else None

                price_element = soup.find('span', {'class': 'listing-details-price b'})
                if price_element is not None:
                    price = price_element.text.strip().replace('$', '') if price_element.text.strip() else None

                description_element = soup.find('div', {'class': 'b font-size-12'})
                if description_element is not None:
                    description = description_element \
                        .findNextSibling('div') \
                        .findNextSibling('div') \
                        .text.strip().replace('\n', ' ')

                neighborhood_element = soup.find('div', {'class': 'overflow-ellipsis font-size-9'})
                if neighborhood_element is not None:
                    neighborhood = neighborhood_element.text.strip().split(',')[0]

                available_on_raw = soup.find('div', {'class': 'font-size-9', 'style': 'margin-top: 5px;'})
                if available_on_raw is not None:
                    available_on = self.extract_renthop_availability(available_on_raw.text.strip())

            return {
                'address': address,
                'neighborhood': neighborhood,
                'number_of_rooms': number_of_rooms,
                'price': price,
                'description': description,
                'available_on': available_on
            }

        except Exception as e:
            raise Exception('Error parsing with BeautifulSoup: {}'.format(str(e)))

    @staticmethod
    def extract_renthop_availability(text: str) -> str:
        try:
            separated_text = text.split(',')[1].replace('Move-In', '').strip()
            return separated_text
        except Exception as e:
            raise Exception('Error extracting availability from RentHop: {}'.format(str(e)))


class SheetsAPI:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    def __init__(self):
        self.creds = None
        self.spreadsheet_id = os.environ['SPREADSHEET_ID']
        self.range_name = os.environ['RANGE_NAME']
        self.authenticate()

    def authenticate(self):
        if os.path.exists('creds/token.json'):
            self.creds = Credentials.from_authorized_user_file('creds/token.json', self.SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('creds/credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open('creds/token.json', 'w') as token:
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
