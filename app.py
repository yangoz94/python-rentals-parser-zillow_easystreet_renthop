import asyncio
from flask import Flask, request, jsonify, Response
from model import ListingParser

app = Flask(__name__)



@app.route('/')
def hello_world():
    return 'Hello, World!'


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
            raise ValueError('Unsupported URL provided. Supported URLs: {}'.format(SUPPORTED_URLS))

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        listing_data = loop.run_until_complete(listing_parser.fetch_listing_data())
        attributes = listing_parser.extract_attributes(listing_data)

        response = {
            'url': url,
            'address': attributes[0],
            'neighborhood': attributes[1],
            'number_of_rooms': attributes[2],
            'price': attributes[3],
            'description': attributes[4],
            'available_on': attributes[5]
        }

        return jsonify(response)

    except ValueError as ve:
        return Response(status=400, response=str(ve))

    except Exception as e:
        return Response(status=500, response='Internal Server Error: {}'.format(str(e)))


if __name__ == '__main__':
    app.run()
