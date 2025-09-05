import boto3
import logging
from datetime import date
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Advertisement')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def add_to_db(url: str,
              webpage_name: str,
              brand: str,
              model_version: str,
              year: int,
              price: int,
              mileage: int,
              gearbox: str,
              fuel_type: str,
              engine_power: str,
              location: str) -> None:

    try:
        date_added = date.today().isoformat()
        item = {
            'url': url,
            'webpage_name': webpage_name,
            'brand': brand,
            'model_version': model_version,
            'year': year,
            'price': price,
            'mileage': mileage,
            'gearbox': gearbox,
            'fuel_type': fuel_type,
            'engine_power': engine_power,
            'location': location,
            'date_added': date_added,
            'constant_key': 'ads',
            # Composite keys for complex queries
            'year_brand': f"{year}#{brand}",
            'year_mileage': f"{year}#{mileage}",
            'year_price': f"{year}#{price}",
            'price_brand': f"{price}#{brand}",
            'price_mileage': f"{price}#{mileage}"
        }
        table.put_item(Item=item)
        logger.info(f"Added {item}")
    except ClientError as e:
        logger.error(f"Error adding to database: {e.response['Error']['Message']}")

def url_exists(url: str) -> bool:
    try:
        response = table.get_item(Key={'url': url})
        return 'Item' in response
    except ClientError as e:
        logger.error(f"Error checking advertisement existence: {e.response['Error']['Message']}")
        return False

def query_by_year_range(min_year: int, max_year: int):
    try:
        response = table.query(
            IndexName='yearRangeIndex',
            KeyConditionExpression=Key('constant_key').eq('ads') & Key('year').between(min_year, max_year)
        )
        return response.get('Items', [])
    except ClientError as e:
        logger.error(f"Error querying by year range: {e.response['Error']['Message']}")
        return []

def query_by_webpage(webpage_name: str):
    try:
        response = table.query(
            IndexName='webpageNameIndex',
            KeyConditionExpression=Key('webpage_name').eq(webpage_name)
        )
        return response.get('Items', [])
    except ClientError as e:
        logger.error(f"Error querying by webpage: {e.response['Error']['Message']}")
        return []

def query_by_price_range(min_price: int, max_price: int):
    try:
        response = table.query(
            IndexName='priceIndex',
            KeyConditionExpression=Key('price').between(min_price, max_price)
        )
        return response.get('Items', [])
    except ClientError as e:
        logger.error(f"Error querying by price range: {e.response['Error']['Message']}")
        return []

def query_by_year_partial_brand(year: int,price_brand, price_brand_prefix: str):
    try:
        response = table.query(
            IndexName='yearBrandIndex',
            KeyConditionExpression=Key('year').eq('price_brand') & Key('price_brand').begins_with(price_brand_prefix)
        )
        return response.get('Items', [])
    except ClientError as e:
        logger.error(f"Error querying by year and brand: {e.response['Error']['Message']}")
        return []

def query_by_price_partial_brand(min_price: int, max_price: int, brand_prefix: str):
    try:
        response = table.query(
            IndexName='priceBrandIndex',
            KeyConditionExpression=Key('price').between(min_price, max_price) & Key('brand').begins_with(brand_prefix)
        )
        return response.get('Items', [])
    except ClientError as e:
        logger.error(f"Error querying by price range and brand: {e.response['Error']['Message']}")
        return []

def query_by_gearbox_prefix(prefix: str):
    try:
        response = table.query(
            IndexName='gearboxIndex',
            KeyConditionExpression=Key('gearbox').begins_with(prefix)
        )
        return response.get('Items', [])
    except ClientError as e:
        logger.error(f"Error querying by gearbox: {e.response['Error']['Message']}")
        return []