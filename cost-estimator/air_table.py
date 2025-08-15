#! /usr/bin/env python3
 
import os
import pprint

from pyairtable import Api

api = Api(os.environ['AIRTABLE_API_KEY'])


QUOTE_BASE_ID='appprdUNzFPO9avLd'
RESOURCE_ENTRY_TABLE_ID='tbl5fX9qzivwgMnD2'
RESOURCE_PRICING_TABLE_ID='tblr5evoP1pKGcUxl'

resource_prices = api.table(QUOTE_BASE_ID, RESOURCE_PRICING_TABLE_ID)

price_dict = {}
for rp in resource_prices.all(fields=['Name']):
	print(rp['id'])
	print(rp['fields']['Name'])

