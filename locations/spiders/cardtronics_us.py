# -*- coding: utf-8 -*-

import csv
import re

import scrapy
from scrapy.selector import Selector

from locations.items import GeojsonPointItem


class CardtronicsUSSpider(scrapy.Spider):
    name = "cardtronics_us"

    def start_requests(self):
        for point in csv.DictReader(
            open("./locations/searchable_points/us_centroids_10mile_radius.csv")
        ):
            yield scrapy.FormRequest(
                "https://catm.locatorsearch.com/GetItems.aspx",
                formdata={
                    "lat": point["latitude"],
                    "lng": point["longitude"],
                    "searchby": "USATM|CATMPOL|",
                },
            )

    def parse(self, response):
        # Response is mislabeled as text/html, and this causes the CDATA
        # to disappear.
        response = response.replace(cls=scrapy.http.response.xml.XmlResponse)
        for marker in response.xpath("marker"):
            yield self.parse_marker(marker)

    def parse_marker(self, marker):
        props = {}
        props["lat"] = lat = marker.attrib["lat"]
        props["lon"] = lon = marker.attrib["lng"]
        props["name"] = marker.xpath("*/title/text()").get()
        props["ref"] = f"{lat}|{lon}"
        props["addr_full"] = marker.xpath("*/add1/text()").get()
        add2 = marker.xpath("*/add2/text()").get()
        props["city"], props["state"], props["postcode"] = re.fullmatch(
            "(.*), (.*) (.*)", add2
        ).groups()

        contents = Selector(text=marker.xpath("*/contents/text()").get())
        descriptions = contents.xpath("*/div[not(@class)]//text()").getall()

        if "- Allpoint Network" in descriptions:
            props["brand"] = "Allpoint"

        return GeojsonPointItem(**props)
