""" Scrape quote using pyppeteer"""

import asyncio
from pyppeteer import launch
from pyquery import PyQuery as pq


async def main():
    browser = await launch(headless=True,
                           args=['--disable-infobars'],
                           executable_path=None)
    page = await browser.newPage()
    response = await page.goto('http://quotes.toscrape.com/js/')
    # async with response:
    page_text = await response.text()
    doc = pq(await page.content())
    print(doc)
    print('Quotes:', doc('.quote').text())
    await page.close()
    await browser.close()

asyncio.get_event_loop().run_until_complete(main())
