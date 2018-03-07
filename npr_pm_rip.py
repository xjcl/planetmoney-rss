# TODO: ncaa ep (after 801) missing

# TODO: use something like 'planetmoney-rss/feed.xml' instead of an url containing 'test' (ew!)
# TODO: This American Life ?

# assembles a podcast feed (rss/xml) containing all planet money episodes
#   (their official feed only includes the most recent episodes)
# by downloading the human-interfacing HTML (which does contain all episodes, surprisingly),
#   parsing it into python datatypes (PlanetMoneyHTMLParser), and emitting an xml rss feed

import re
import sys
import html
import math
import json
import time
import pytz
import base64
import pickle
import datetime
import itertools
import html.parser
import email.utils
import collections
import urllib.request
import dateutil.parser

# input:   "npr planet money" html website corresponding to a month+year-date
# output:  stored in self.feed_entries which is a list of entries
#               each entry corresponds to a podcast episode
#               each entry is a dictionary with info, eg
#                   { 'title': 'Episode ###: Bla',  'link': 'https://...',  ...} etc
class PlanetMoneyHTMLParser(html.parser.HTMLParser):

    def __init__(self):
        self.prev = None
        self.next_attr = ''

        self.subpage = None

        # stack tags (sneaking in before content) we want to ignore in handle_data
        # eg   <want> <time="12"> irrelevant data! </time> data we want </want>
        # so here we would ignore 'time'
        self.tag_stack = []

        self.feed_entry = {}
        self.feed_entries = []

        self.tagattrs = collections.namedtuple('tagattrs', ['tag', 'attrs'])

        super().__init__()

    def handle_starttag(self, tag, attrs):

        attrs = dict(attrs)

        if self.next_attr:
            self.tag_stack.append(tag)

        if tag == 'a' and self.prev.tag == 'h2' and self.prev.attrs.get('class') == 'title':  # on episode list page
            self.subpage = attrs['href']
            self.next_attr = 'title'
        if attrs.get('class') == 'audio-module-title':  # on episode's own page (= subpage)
            self.next_attr = 'title'

        if tag == 'a' and self.prev.tag == 'p' and self.prev.attrs.get('class') == 'teaser':
            self.next_attr = 'description'
        if tag == 'meta' and attrs.get('name') == 'description':
            self.feed_entry['description'] = attrs['content']

        if tag == 'time':
            # TODO: remove non-iTunes-duration ?  also some are missing duration, eg #366  (DL?)
            if attrs.get('class') == 'audio-module-duration':
                self.next_attr = 'itunes:duration'
            elif self.prev.attrs.get('class') == 'dateblock' or 'href' in self.prev.attrs:
                self.feed_entry['pubDate'] = attrs['datetime']

        # don't use download link for download but instead stream-link as some DL links are missing ! eg #702
        if attrs.get('class') == 'audio-module-controls-wrap' and self.prev.attrs.get('class') == 'audio-module-title' and 'data-audio' in attrs:
            self.feed_entry['link'] = json.loads(attrs['data-audio'])['audioUrl']   # ondemand.npr.org
            if not self.feed_entry['link'].startswith('https://'):
                self.feed_entry['link'] = base64.b64decode(self.feed_entry['link']).decode('UTF-8')
            self.feed_entry['guid'] = self.feed_entry['link']

        self.prev = self.tagattrs(tag, attrs)

    # re-use scraping code on an indiviual episode's page (= subpage), this requires some trickery
    #   (combining all fake feed_entries of the subpage on top of the current dict)
    def add_subpage_info(self, url):

        req = urllib.request.Request(url)

        with urllib.request.urlopen(req) as response:
            the_page = str(response.read(), 'utf-8')

        parser = PlanetMoneyHTMLParser()
        parser.feed(the_page)
        if 'audio-module-controls-wrap' not in the_page:
            print('No download link on page: ' + url, file=sys.stderr)
            # dl_missing = True
        parser.close()

        for e in parser.feed_entries:
            self.feed_entry.update(e)

    def handle_endtag(self, tag):
        if self.tag_stack:
            self.tag_stack.pop()

        if tag == 'article' and self.feed_entry:
            # since 2017 stories lack audio modules now, you have to go on the episode pages themselves for the links =(
            #   and also for full release date timestamps (overview pages only have the date, not the time)

            if self.subpage:
                # print('DL-ing ' + self.subpage)
                self.add_subpage_info(self.subpage)

                # OMG they straight up forgot an episode in their feed. this intern needs to be fired xD
                if self.subpage == 'https://www.npr.org/sections/money/2016/07/22/487069271/episode-576-when-women-stopped-coding':

                    self.feed_entries.append(self.feed_entry)
                    self.feed_entry = {}

                    self.add_subpage_info('https://www.npr.org/sections/money/2016/07/20/486785422/episode-713-paying-for-the-crime')

                self.subpage = None

            # is unindented to sneakily handle a subpage's pseduo-feed also
            self.feed_entries.append(self.feed_entry)
            self.feed_entry = {}


    def handle_data(self, data):
        if not self.next_attr:
            return

        if self.tag_stack:
            return

        # o god pls stop with the inconsistencies =/  affects #824 #657 #618 and others
        if self.next_attr == 'title' and data == 'Listen ':
            self.next_attr = ''
            return

        # some missing initial '#'s...
        if self.next_attr == 'title' and re.match('[0-9]+:', data):
            self.feed_entry['title'] = '#' + data
            self.next_attr = ''
            return

        self.feed_entry[self.next_attr] = data
        self.next_attr = ''


PLANET_MONEY_EPOCH = dateutil.parser.parse('2008-09-09T16:45:00-04:00')  # datetime of 1st episode
FEED_PICKLE_FILE = 'npr_pm_feed.pickle'
URL_STEM = 'http://www.npr.org/sections/money/127413729/podcast/archive'

# try to load cached results from a previous run of this script
def load_feed_entries():
    try:
        with open(FEED_PICKLE_FILE, 'rb') as f:
            # i think we have to store the rss feed "newest-first"
            #     (everyone else does it, looks dum in firefox if "oldest-first")
            old_feed_entries = pickle.load(f)
        epoch = dateutil.parser.parse(old_feed_entries[0]['pubDate']) - datetime.timedelta(days=1)

    except:
        old_feed_entries = []
        epoch = PLANET_MONEY_EPOCH

    return (old_feed_entries, epoch)


def parse_site_into_feed(old_feed_entries, epoch):

    now = datetime.datetime.now(pytz.utc)
    print('making ~' + str(math.ceil((now - epoch).days / 40)) + ' requests to gather urls, please be patient...')
    req_nr = 0

    new_feed_entries = []

    # we have to iteratre from present to the past because we need to know the last date to make the next request
    curdate = now
    while curdate > epoch:

        req_nr += 1
        print('Request number', req_nr, 'for date', curdate.strftime('%Y-%m-%d'), end='\r')

        full_url = URL_STEM + curdate.strftime('?date=%m-%d-%Y')  # site uses yankeedates !! lmao
        req = urllib.request.Request(full_url)

        with urllib.request.urlopen(req) as response:
            the_page = str(response.read(), 'utf-8')

        # print('init DL-ing ' + full_url)
        parser = PlanetMoneyHTMLParser()
        parser.feed(the_page)
        parser.close()

        for e in parser.feed_entries:
            # exclude space overview page with 4 episode links
            if not 'link' in e or e['title'] == 'Episode 4':
                continue
            # curdate = datetime.datetime.strptime(e['pubDate'], '%Y-%m-%d')
            # curdate = datetime.datetime(*time.strptime(e['pubDate'], "%Y-%m-%dT%H:%M:%S")[:6])
            curdate = dateutil.parser.parse(e['pubDate'])
            if all(f['link'] != e['link'] for f in old_feed_entries) and \
               all(f['link'] != e['link'] for f in new_feed_entries):  # prevent duplicates
                new_feed_entries.append(e)

    return new_feed_entries


# TODO: use feed generator instead of manually writing text
def save_feed_entries(all_feed_entries):

    print('All requests done! Now saving to file(s).')

    with open(FEED_PICKLE_FILE, 'wb') as f:
        pickle.dump(all_feed_entries, f)

    found_episodes = []

    with open('npr_pm_feed.xml', 'w') as f:
        f.write('''<?xml version="1.0" encoding="utf-8"?>
            <rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
            <channel>
            <title>Planet Money but it's all episodes</title>
            <link>https://github.com/xjcl/planetmoney-rss/tree/gh-pages</link>
            <image><url>http://nationalpublicmedia.com/wp-content/uploads/2014/06/planetmoney.png</url></image>
            <description>NPR's Planet Money. The economy, explained. Collated into a full-history feed by some d00d.</description>\n''')

        for e in all_feed_entries:
            f.write('<item>\n')
            for k,v in sorted(e.items()):
                if k == 'pubDate':
                    v = email.utils.format_datetime(dateutil.parser.parse(v))
                if k == 'title':
                    if v.startswith(' Episode '):   # affected: #428 #567
                        # oh my god the intern deserves an ass-whooping xDDD
                        v = v[1:]
                    if v.startswith('Episode '):
                        v = '#' + v[8:]
                    if v.startswith('#'):
                        found_episodes.append(int(v[1:v.find(':')]))
                if k == 'link':
                    f.write('<enclosure url="' + html.escape(v) + '" type="audio/mpeg"/>')
                f.write('<' + k + '>' + html.escape(v) + '</' + k + '>\n')
            f.write('</item>\n\n')

        f.write('</channel></rss>\n')

    found_episodes.reverse()

    # test if our scraping missed any episodes  (won't detect missing re-runs)
    last_nr = 376
    print('Checking integrity of new episodes (excludes re-runs) after #' + str(last_nr) + '...', file=sys.stderr)
    # print(found_episodes, file=sys.stderr)
    for ep_nr in found_episodes:
        # print(ep_nr, file=sys.stderr)
        if ep_nr < last_nr:  # re-run  => okay
            pass
        elif ep_nr == last_nr:
            print('double entry! ep ' + str(ep_nr), file=sys.stderr)
        elif ep_nr == last_nr + 1:  # subsequent episodes  => okay
            last_nr = ep_nr
        elif ep_nr > last_nr + 1:
            # hardcode episodes that are NOT missing but just with titles missing number :>
            #   either by mistake or in the "Oil #X" (716-720) and "SPACE X" (808-811) series
            if (last_nr, ep_nr) in [(537, 539), (675, 677), (715, 721), (807, 812)]:
                last_nr = ep_nr
                continue
            if last_nr+1 == ep_nr-1:
                print('missing ep ' + str(last_nr+1) + '!', file=sys.stderr)
            else:
                print('missing eps ' + str(last_nr+1) + ' to ' + str(ep_nr-1) + '!', file=sys.stderr)
            last_nr = ep_nr


# pop n most recent episodes from history  -> used for debugging
def pop_from_history(n):

    feed = []
    with open(FEED_PICKLE_FILE, 'rb') as f:
        feed = pickle.load(f)

    feed = feed[n:]

    with open(FEED_PICKLE_FILE, 'wb') as f:
        pickle.dump(feed, f)



if __name__ == '__main__':
    old_feed_entries, epoch = load_feed_entries()
    new_feed_entries = parse_site_into_feed(old_feed_entries, epoch)
    save_feed_entries(new_feed_entries + old_feed_entries)

# TODO: quality control, e.g. list of episode numbers from feed, and compare to reference using a test case ?
# TODO: fix new eps addition bug
# TODO: automate new eps addition (server?)
# TODO: why do some episodes have info on mm:ss length and some don't ?
# TODO: okay to remove 0 bytes length ? or calculate ?

# TODO: with parser as !!
