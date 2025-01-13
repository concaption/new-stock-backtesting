Aggregates (Bars)
get
/v2/aggs/ticker/{stocksTicker}/range/{multiplier}/{timespan}/{from}/{to}
Get aggregate bars for a stock over a given date range in custom time window sizes.

For example, if timespan = ‘minute’ and multiplier = ‘5’ then 5-minute bars will be returned.

Parameters
stocksTicker
*
AAPL
Specify a case-sensitive ticker symbol. For example, AAPL represents Apple Inc.

multiplier
*
1
The size of the timespan multiplier.

timespan
*

day
The size of the time window.

from
*
2023-01-09
The start of the aggregate time window. Either a date with the format YYYY-MM-DD or a millisecond timestamp.

to
*
2023-02-10
The end of the aggregate time window. Either a date with the format YYYY-MM-DD or a millisecond timestamp.

adjusted

true
Whether or not the results are adjusted for splits. By default, results are adjusted. Set this to false to get results that are NOT adjusted for splits.

sort

asc
Sort the results by timestamp. asc will return results in ascending order (oldest at the top), desc will return results in descending order (newest at the top).

limit
Limits the number of base aggregates queried to create the aggregate results. Max 50000 and Default 5000. Read more about how limit is used to calculate aggregate results in our article on Aggregate Data API Improvements.

https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2023-01-09/2023-02-10?adjusted=true&sort=asc&apiKey=*

Copy

JSON

Run Query
Response Attributes
ticker*string
The exchange symbol that this item is traded under.

adjusted*boolean
Whether or not this response was adjusted for splits.

queryCount*integer
The number of aggregates (minute or day) used to generate the response.

request_id*string
A request id assigned by the server.

resultsCount*integer
The total number of results for this request.

status*string
The status of this request's response.

resultsarray
c*number
The close price for the symbol in the given time period.

h*number
The highest price for the symbol in the given time period.

l*number
The lowest price for the symbol in the given time period.

ninteger
The number of transactions in the aggregate window.

o*number
The open price for the symbol in the given time period.

otcboolean
Whether or not this aggregate is for an OTC ticker. This field will be left off if false.

t*integer
The Unix Msec timestamp for the start of the aggregate window.

v*number
The trading volume of the symbol in the given time period.

vwnumber
The volume weighted average price.

next_urlstring
If present, this value can be used to fetch the next page of data.

Was this helpful?
Help us improve

Yes

No
Response Object
{
  "adjusted": true,
  "next_url": "https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/1578114000000/2020-01-10?cursor=bGltaXQ9MiZzb3J0PWFzYw",
  "queryCount": 2,
  "request_id": "6a7e466379af0a71039d60cc78e72282",
  "results": [
    {
      "c": 75.0875,
      "h": 75.15,
      "l": 73.7975,
      "n": 1,
      "o": 74.06,
      "t": 1577941200000,
      "v": 135647456,
      "vw": 74.6099
    },
    {
      "c": 74.3575,
      "h": 75.145,
      "l": 74.125,
      "n": 1,
      "o": 74.2875,
      "t": 1578027600000,
      "v": 146535512,
      "vw": 74.7026
    }
  ],
  "resultsCount": 2,
  "status": "OK",
  "ticker": "AAPL"


Ticker Details v3
get
/v3/reference/tickers/{ticker}
Get a single ticker supported by Polygon.io. This response will have detailed information about the ticker and the company behind it.

Parameters
ticker
*
AAPL
The ticker symbol of the asset.

date

Specify a point in time to get information about the ticker available on that date. When retrieving information from SEC filings, we compare this date with the period of report date on the SEC filing.

For example, consider an SEC filing submitted by AAPL on 2019-07-31, with a period of report date ending on 2019-06-29. That means that the filing was submitted on 2019-07-31, but the filing was created based on information from 2019-06-29. If you were to query for AAPL details on 2019-06-29, the ticker details would include information from the SEC filing.

Defaults to the most recent available date.

https://api.polygon.io/v3/reference/tickers/AAPL?apiKey=*

Copy

JSON

Run Query
Response Attributes
countinteger
The total number of results for this request.

request_idstring
A request id assigned by the server.

resultsobject
Ticker with details.

active*boolean
Whether or not the asset is actively traded. False means the asset has been delisted.

addressobject
address1string
The first line of the company's headquarters address.

address2string
The second line of the company's headquarters address, if applicable.

citystring
The city of the company's headquarters address.

postal_codestring
The postal code of the company's headquarters address.

statestring
The state of the company's headquarters address.

brandingobject
icon_urlstring
A link to this ticker's company's icon. Icon's are generally smaller, square images that represent the company at a glance. Note that you must provide an API key when accessing this URL. See the "Authentication" section at the top of this page for more details.

logo_urlstring
A link to this ticker's company's logo. Note that you must provide an API key when accessing this URL. See the "Authentication" section at the top of this page for more details.

cikstring
The CIK number for this ticker. Find more information here.

composite_figistring
The composite OpenFIGI number for this ticker. Find more information here

currency_name*string
The name of the currency that this asset is traded with.

delisted_utcstring
The last date that the asset was traded.

descriptionstring
A description of the company and what they do/offer.

homepage_urlstring
The URL of the company's website homepage.

list_datestring
The date that the symbol was first publicly listed in the format YYYY-MM-DD.

locale*enum [us, global]
The locale of the asset.

market*enum [stocks, crypto, fx, otc, indices]
The market type of the asset.

market_capnumber
The most recent close price of the ticker multiplied by weighted outstanding shares.

name*string
The name of the asset. For stocks/equities this will be the companies registered name. For crypto/fx this will be the name of the currency or coin pair.

phone_numberstring
The phone number for the company behind this ticker.

primary_exchangestring
The ISO code of the primary listing exchange for this asset.

round_lotnumber
Round lot size of this security.

share_class_figistring
The share Class OpenFIGI number for this ticker. Find more information here

share_class_shares_outstandingnumber
The recorded number of outstanding shares for this particular share class.

sic_codestring
The standard industrial classification code for this ticker. For a list of SIC Codes, see the SEC's SIC Code List.

sic_descriptionstring
A description of this ticker's SIC code.

ticker*string
The exchange symbol that this item is traded under.

ticker_rootstring
The root of a specified ticker. For example, the root of BRK.A is BRK.

ticker_suffixstring
The suffix of a specified ticker. For example, the suffix of BRK.A is A.

total_employeesnumber
The approximate number of employees for the company.

typestring
The type of the asset. Find the types that we support via our Ticker Types API.

weighted_shares_outstandingnumber
The shares outstanding calculated assuming all shares of other share classes are converted to this share class.

statusstring
The status of this request's response.

Was this helpful?
Help us improve

Yes

No
Response Object
{
  "request_id": "31d59dda-80e5-4721-8496-d0d32a654afe",
  "results": {
    "active": true,
    "address": {
      "address1": "One Apple Park Way",
      "city": "Cupertino",
      "postal_code": "95014",
      "state": "CA"
    },
    "branding": {
      "icon_url": "https://api.polygon.io/v1/reference/company-branding/d3d3LmFwcGxlLmNvbQ/images/2022-01-10_icon.png",
      "logo_url": "https://api.polygon.io/v1/reference/company-branding/d3d3LmFwcGxlLmNvbQ/images/2022-01-10_logo.svg"
    },
    "cik": "0000320193",
    "composite_figi": "BBG000B9XRY4",
    "currency_name": "usd",
    "description": "Apple designs a wide variety of consumer electronic devices, including smartphones (iPhone), tablets (iPad), PCs (Mac), smartwatches (Apple Watch), AirPods, and TV boxes (Apple TV), among others. The iPhone makes up the majority of Apple's total revenue. In addition, Apple offers its customers a variety of services such as Apple Music, iCloud, Apple Care, Apple TV+, Apple Arcade, Apple Card, and Apple Pay, among others. Apple's products run internally developed software and semiconductors, and the firm is well known for its integration of hardware, software and services. Apple's products are distributed online as well as through company-owned stores and third-party retailers. The company generates roughly 40% of its revenue from the Americas, with the remainder earned internationally.",
    "homepage_url": "https://www.apple.com",
    "list_date": "1980-12-12",
    "locale": "us",
    "market": "stocks",
    "market_cap": 2771126040150,
    "name": "Apple Inc.",
    "phone_number": "(408) 996-1010",
    "primary_exchange": "XNAS",
    "round_lot": 100,
    "share_class_figi": "BBG001S5N8V8",
    "share_class_shares_outstanding": 16406400000,
    "sic_code": "3571",
    "sic_description": "ELECTRONIC COMPUTERS",
    "ticker": "AAPL",
    "ticker_root": "AAPL",
    "total_employees": 154000,
    "type": "CS",
    "weighted_shares_outstanding": 16334371000
  },
  "status": "OK"
}
Ticker Events
get
/vX/reference/tickers/{id}/events
Get a timeline of events for the entity associated with the given ticker, CUSIP, or Composite FIGI.

This API is experimental.
Parameters
id
*
META
Identifier of an asset. This can currently be a Ticker, CUSIP, or Composite FIGI. When given a ticker, we return events for the entity currently represented by that ticker. To find events for entities previously associated with a ticker, find the relevant identifier using the Ticker Details Endpoint

types
A comma-separated list of the types of event to include. Currently ticker_change is the only supported event_type. Leave blank to return all supported event_types.

https://api.polygon.io/vX/reference/tickers/META/events?apiKey=*

Copy

Run Query
Response Attributes
request_idstring
A request id assigned by the server.

resultsobject
eventsarray [undefined]
namestring
statusstring
The status of this request's response.

Was this helpful?
Help us improve

Yes

No
Response Object
{
  "request_id": "31d59dda-80e5-4721-8496-d0d32a654afe",
  "results": {
    "events": [
      {
        "date": "2022-06-09",
        "ticker_change": {
          "ticker": "META"
        },
        "type": "ticker_change"
      },
      {
        "date": "2012-05-18",
        "ticker_change": {
          "ticker": "FB"
        },
        "type": "ticker_change"
      }
    ],
    "name": "Meta Platforms, Inc. Class A Common Stock"
  },
  "status": "OK"
}