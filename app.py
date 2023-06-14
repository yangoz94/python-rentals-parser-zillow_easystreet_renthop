import asyncio
from flask import Flask, request, jsonify, Response
from models.ListingParser.ListingParser import ListingParser
from models.SheetsAPI.SheetsAPI import SheetsAPI

app = Flask(__name__)


@app.route('/api/parse-listing', methods=['POST'])
def parse_listing():
    try:
        if request.method != 'POST':
            raise ValueError('Method not allowed')

        data = request.get_json()
        if not data or 'url' not in data:
            raise ValueError('No URL provided')

        url = data['url'].strip()
        listing_parser = ListingParser(url)
        if not listing_parser.is_supported_url():
            raise ValueError('Unsupported URL provided. Supported URLs: {}'.format(listing_parser.SUPPORTED_URLS))

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        listing_data = loop.run_until_complete(listing_parser.fetch_listing_data())
        attributes = listing_parser.extract_attributes(listing_data)

        new_row_to_append = [
            url,
            attributes['address'],
            attributes['neighborhood'],
            attributes['number_of_rooms'],
            attributes['price'],
            attributes['available_on'],
            "",  # placeholder for notes column in google sheets that I want to leave blank
            attributes['description'],
        ]

        # add newly parsed data to google sheets
        sheets_api = SheetsAPI()
        is_row_added = sheets_api.add_new_row(new_row_to_append)
        if not is_row_added:
            raise ValueError('Error: likely because the listing URL already exists in the sheet.')

        return jsonify(attributes)

    except ValueError as ve:
        return Response(status=400, response="{}".format(ve))

    except Exception as e:
        return Response(status=500, response='Internal Server Error: {}'.format(str(e)))


if __name__ == '__main__':
    print("Starting the flask server...")
    app.run()
