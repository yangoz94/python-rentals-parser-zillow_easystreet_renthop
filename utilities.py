def extract_renthop_availability(text: str) -> str:
    try:
        separated_text = text.split(',')[1].replace('Move-In', '').strip()
        return separated_text
    except Exception as e:
        raise Exception('Error extracting availability from RentHop: {}'.format(str(e)))