#! /usr/bin/env python3
 
import os
import pprint

from pyairtable import Api

api = Api(os.environ['AIRTABLE_API_KEY'])


QUOTE_BASE_ID='appprdUNzFPO9avLd'
RESOURCE_ENTRY_TABLE_ID='tbl5fX9qzivwgMnD2'
RESOURCE_PRICING_TABLE_ID='tblr5evoP1pKGcUxl'
RESOURCE_SUMMARY_TABLE_ID='tblCj7JYRsYlqtruU'

resource_prices = api.table(QUOTE_BASE_ID, RESOURCE_PRICING_TABLE_ID)

price_dict = {}
for rp in resource_prices.all(fields=['Name']):
	price_dict[rp['fields']['Name']] = (rp['id'])


pprint.pp(price_dict)

resource_summaries = api.table(QUOTE_BASE_ID, RESOURCE_SUMMARY_TABLE_ID)
pprint.pp(resource_summaries)

for records in resource_summaries.iterate(page_size=100, max_records=1000):
    print(records)