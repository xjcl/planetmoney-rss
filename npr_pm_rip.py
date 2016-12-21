#!/usr/bin/python3
import urllib.request
import os
import re
import html
import datetime

URL_STEM = 'http://www.npr.org/sections/money/127413729/podcast/archive'

USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
HDR = {'User-Agent': USER_AGENT, 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}

print('making ~100 requests to gather urls, please be patient...')
media_urls = []
media_urls_rich = []
req_nr = 0

for year in range(datetime.datetime.now().year, 2007, -1):
    for month in range(12, 0, -1):
        req_nr += 1
        print('Request number ' + str(req_nr))

        # every side goes about 2 months back, so we check every month
        full_url = URL_STEM + '?date=' + str(month) + '-31-' + str(year)
        req = urllib.request.Request(full_url, headers=HDR)

        with urllib.request.urlopen(req) as response:
            the_page = str(response.read(), 'utf-8')

            findtitle = '<h2 class="title">'
            qs = [m.start()+len(findtitle) for m in re.finditer(findtitle, the_page)]

            findurl = 'audio-tool audio-tool-download"><a href="'
            js = [m.start()+len(findurl) for m in re.finditer(findurl, the_page)]

            for j,q in zip(js, qs):
                i = j; p = q
                while the_page[j] != '"':
                    j += 1
                while the_page[p] != '>':
                    p += 1; q += 1
                while the_page[q] != '<':
                    q += 1
                media_url = html.unescape(the_page[i:j])
                media_title = the_page[p+1:q]
                while the_page[p-10:p-2] != 'datetime':
                    p += 1
                media_date = the_page[p:p+10]

                # don't use set cos we want to maintain order
                # (unlike PM whose urls are veeeery inconsistent holy shit)
                if media_url not in media_urls:
                    media_urls.append(media_url)
                    media_urls_rich.append((media_url, media_title, media_date))

# can be downloaded all with  wgt -i filename.txt
with open('media_urls', 'w') as f:
    f.write('\n'.join(media_urls))

# # won't work anyway if the full command is too long
# # and if we do one wget per line they'll all happen simultaneously..
# media_urls = ["'" + s + "'" for s in media_urls]
# os.system('wget ' + ' '.join(media_urls))

with open('/home/jan/Dropbox/py/planetmoney-rss/npr_pm_test.xml', 'w') as f:
    f.write('''<?xml version="1.0" encoding="utf-8"?>
        <rss version="2.0">
        <channel>
        <title>Planet money but it's all episodes</title>
        <link>https://github.com/xjcl/planetmoney-rss/tree/gh-pages</link>
        <image><url>http://nationalpublicmedia.com/wp-content/uploads/2014/06/planetmoney.png</url><image>
        <description>pls don't sue</description>
    ''')

    for m in media_urls_rich:
        mu, mt, md = m
        mu = html.escape(mu)
        f.write('''
            <item>
            <title>''' + mt + '''</title>
            <link>''' + mu + '''</link>
            <guid>''' + mu + '''</guid>
            <pubDate>''' + md + '''</pubDate>
            <description>I might extract description in the future soz</description>
            </item>
        ''')

    f.write('''
        </channel>
        </rss>
    ''')

