import os
from datetime import datetime
import aiohttp
import asyncio
import re
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
SUPPORTED_URLS = {'streeteasy.com', 'zillow.com', 'renthop.com'}


def extract_base_url(url):
    pattern = r"(?:https?://)?(?:www\.)?([^/]+\.com)"
    match = re.match(pattern, url)
    if match:
        base_url = match.group(1)
        return base_url
    return None


def is_supported_url(url):
    base_url = extract_base_url(url)
    if base_url is not None:
        for supported_url in SUPPORTED_URLS:
            if supported_url in base_url:
                return True
    return False


def get_listing_url():
    data = request.get_json()
    if not data or 'url' not in data:
        raise ValueError('No URL provided')
    listing_url = data['url'].strip()
    if not is_supported_url(listing_url):
        raise ValueError('Unsupported URL provided. Supported URLs: {}'.format(SUPPORTED_URLS))
    return listing_url

async def get_neighborhood_from_address(address, api_key):
    url = f'https://api.opencagedata.com/geocode/v1/json?q={address}&key={os.getenv("GOOGLE_V3_API_KEY")}'

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()

            if 'results' in data and len(data['results']) > 0:
                components = data['results'][0]['components']
                neighborhood = components.get('neighbourhood')
                return neighborhood

            return None


async def fetch_listing_data(listing_url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(listing_url, headers=headers) as response:
                response.raise_for_status()  # Raise an exception if the request was unsuccessful
                return await response.text()
    except aiohttp.ClientError as e:
        raise Exception('Error fetching listing data: {}'.format(str(e)))


def extract_attributes(html_text, listing_url: str):
    address = None
    neighborhood = None
    number_of_rooms = None
    price = None
    description = None
    available_on = None
    try:
        soup = BeautifulSoup(html_text, 'html.parser')
        # Getting the necessary data from the listing
        if "streeteasy.com" in listing_url:
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
                available_on = datetime.strptime(available_on_element.text.strip(), "%m/%d/%Y").strftime("%a %b %d %Y")

        elif "zillow.com" in listing_url:
            summary_container = soup.find('div', {'class': 'summary-container'})
            address_raw = summary_container.find_all('h1')[0].text.strip()
            address = re.sub(r',([^,]+,[^,]+)$', '', address_raw) if address_raw else None

            number_of_rooms_elements = summary_container.find_all('strong')
            if number_of_rooms_elements:
                number_of_rooms = number_of_rooms_elements[0].text.strip()

            price_element = summary_container.find('span')
            if price_element:
                price_raw = price_element.text.strip()
                price = re.sub(r'\$|/mo', '', price_raw)

            data_view_container = soup.find('div', {'class': 'data-view-container'})
            description_overview = data_view_container.find('h4', string='Overview')
            if description_overview:
                description_raw = description_overview.find_next_sibling('div').text.strip()
                # Remove the sentence starting with "Show more"
                description = re.sub(r"Show more.*$", "", description_raw, flags=re.MULTILINE)\
                    .replace('\n', ' ')\
                    .replace("Hide", "").strip()

            available_on_element = data_view_container.find('span', string="Date available")
            if available_on_element:
                available_on = available_on_element.find_next_sibling('span').text.strip()
            else:
                available_on = "Not specified"

        elif "renthop.com" in listing_url:
            pass

        return address, neighborhood, number_of_rooms, price, description, available_on

    except Exception as e:
        raise Exception('Error parsing with BeautifulSoup: {}'.format(str(e)))




@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/api/parse-listing', methods=['POST'])
def parse_listing():
    try:
        # Check the method as a backup to the route config above
        if request.method != 'POST':
            raise ValueError('Method not allowed')

        # Get the listing URL from the request
        listing_url = get_listing_url()

        # Fetch the listing data
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        listing_data = loop.run_until_complete(fetch_listing_data(listing_url))

        # Extract attributes from the HTML
        address, neighborhood, number_of_rooms, price, description, available_on = extract_attributes(listing_data, listing_url)

        # Return response as JSON
        return jsonify({
            'url': listing_url,
            'address': address,
            'neighborhood': neighborhood,
            'number_of_rooms': number_of_rooms,
            'price': price,
            'description': description,
            'available_on': available_on
        })

    except ValueError as ve:
        return Response(status=400, response=str(ve))

    except Exception as e:
        return Response(status=500, response='Internal Server Error: {}'.format(str(e)))


if __name__ == '__main__':
    app.run()