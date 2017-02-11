# assembles a podcast feed (rss/xml) containing all planet money episodes
#   (their official feed only includes the most recent episodes)
# by downloading the human-interfacing HTML (which does contain all episodes, surprisingly),
#   parsing it into python datatypes (PlanetMoneyHTMLParser), and emitting an xml rss feed

# TODO: cache websites?

from html.parser import HTMLParser
from html.entities import name2codepoint
from html import escape

import datetime
import urllib.request


class PlanetMoneyHTMLParser(HTMLParser):

    def __init__(self):
        self.prev = None
        self.next_attr = ''
        # stack tags (sneaking in before content) wa want to ignore in handle_data
        # eg   <want> <time="12"> irrelevant data! </time> data we want </want>
        # so here we would ignore 'time'
        self.tag_stack = []

        self.feed_entry = {}
        self.feed_entries = []
        super().__init__()

    def handle_starttag(self, tag, attrs):

        if self.next_attr:
            self.tag_stack.append(tag)

        if tag == 'a' and self.prev[0] == 'h2' and ('class', 'title') in self.prev[1]:
            self.next_attr = 'title'

        if tag == 'a' and self.prev[0] == 'p' and ('class', 'teaser') in self.prev[1]:
            self.next_attr = 'description'

        if tag == 'a' and self.prev[0] == 'li' and ('class', 'audio-tool audio-tool-download') in self.prev[1]:
            self.feed_entry['link'] = attrs[0][1]
            self.feed_entry['guid'] = attrs[0][1]

        if tag == 'time':
            if ('class', 'audio-module-duration') in attrs:
                self.next_attr = 'itunes:duration'
            else:
                self.feed_entry['pubDate'] = attrs[0][1]

        self.prev = (tag, attrs)
        # XXX check tag,attrs instead of doing [0][1]

    def handle_endtag(self, tag):
        if self.tag_stack:
            self.tag_stack.pop()

        if tag == 'article' and self.feed_entry:
            if 'link' in self.feed_entry:
                self.feed_entries.append(self.feed_entry)
            self.feed_entry = {}

    def handle_data(self, data):
        if not self.next_attr:
            return

        if self.tag_stack:
            return

        self.feed_entry[self.next_attr] = data
        self.next_attr = ''


URL_STEM = 'http://www.npr.org/sections/money/127413729/podcast/archive'
USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
HDR = {'User-Agent': USER_AGENT, 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
PLANET_MONEY_EPOCH = 2008

yr_now = datetime.datetime.now().year
print('making ' + str(12 * (yr_now - PLANET_MONEY_EPOCH-1)) + ' requests to gather urls, please be patient...')
req_nr = 0
all_feed_entries = []

for year in range(yr_now, PLANET_MONEY_EPOCH-1, -1):
    for month in range(12, 0, -1):

        req_nr += 1
        print('Request number ' + str(req_nr), end='\r')

        # every side goes about 2 months back, so we check every month
        full_url = URL_STEM + '?date=' + str(month) + '-31-' + str(year)
        req = urllib.request.Request(full_url, headers=HDR)

        with urllib.request.urlopen(req) as response:
            the_page = str(response.read(), 'utf-8')

            parser = PlanetMoneyHTMLParser()
            parser.feed(the_page)
            for e in parser.feed_entries:
                if all(f['link'] != e['link'] for f in all_feed_entries):  # prevent dupes
                    all_feed_entries.append(e)

with open('/home/jan/Dropbox/py/planetmoney-rss/npr_pm_test.xml', 'w') as f:
    f.write('''<?xml version="1.0" encoding="utf-8"?>
        <rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
        <channel>
        <title>Planet Money but it's all episodes</title>
        <link>https://github.com/xjcl/planetmoney-rss/tree/gh-pages</link>
        <image><url>http://nationalpublicmedia.com/wp-content/uploads/2014/06/planetmoney.png</url></image>
        <description>pls don't sue</description>\n''')

    for e in all_feed_entries:
        f.write('<item>')
        for k,v in e.items():
            f.write('<' + k + '>' + escape(v) + '</' + k + '>')
        f.write('</item>\n')

    f.write('</channel></rss>')

