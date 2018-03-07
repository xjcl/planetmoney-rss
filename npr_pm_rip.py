# TODO: ncaa ep (after 801) missing

# TODO: use something like 'planetmoney-rss/feed.xml' instead of an url containing 'test' (ew!)
# TODO: This American Life ?

# assembles a podcast feed (rss/xml) containing all planet money episodes
#   (their official feed only includes the most recent episodes)
# by downloading the human-interfacing HTML (which does contain all episodes, surprisingly),
#   parsing it into python datatypes (PlanetMoneyHTMLParser), and emitting an xml rss feed

import sys
import html
import math
import pickle
import datetime
import itertools
import html.parser
import email.utils
import collections
import urllib.request

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

        if tag == 'a' and self.prev.tag == 'h2' and self.prev.attrs.get('class') == 'title':
            self.subpage = attrs['href']
            self.next_attr = 'title'

        if tag == 'a' and self.prev.tag == 'p' and self.prev.attrs.get('class') == 'teaser':
            self.next_attr = 'description'

        if tag == 'a' and self.prev.tag == 'li' and self.prev.attrs.get('class') == 'audio-tool audio-tool-download':
            self.feed_entry['link'] = attrs['href']
            self.feed_entry['guid'] = attrs['href']

        if tag == 'time':
            # TODO: remove duration (implicit in file + ugly itunes tag) ?
            if attrs.get('class') == 'audio-module-duration':
                self.next_attr = 'itunes:duration'
            else:
                self.feed_entry['pubDate'] = attrs['datetime']

        self.prev = self.tagattrs(tag, attrs)

    def handle_endtag(self, tag):
        if self.tag_stack:
            self.tag_stack.pop()

        if tag == 'article' and self.feed_entry:

            # since 2017 stories lack audio modules now, you have to go on the episode pages themselves for the links

            # case we are on the main feed page which has subpages
            if self.subpage:
                req = urllib.request.Request(self.subpage)

                with urllib.request.urlopen(req) as response:
                    the_page = str(response.read(), 'utf-8')

                parser = PlanetMoneyHTMLParser()
                parser.feed(the_page)
                parser.close()


                for e in parser.feed_entries:
                    # ugly hack
                    old_pub_date = self.feed_entry['pubDate']

                    self.feed_entry.update(e)

                    if len(old_pub_date) == len('YYYY-MM-DD'):   # -> we DONT want the 'T22:10:00' part or a duration!
                        self.feed_entry['pubDate'] = old_pub_date   # TODO: more exact datetime (add hours and minutes)

                self.subpage = None


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


# ok not to subtract one here cos there was only a single episode that date
PLANET_MONEY_EPOCH = datetime.datetime(2008, 9, 9)
FEED_PICKLE_FILE = 'npr_pm_feed.pickle'
URL_STEM = 'http://www.npr.org/sections/money/127413729/podcast/archive'



# try to load cached results from a previous run of this script
def load_feed_entries():
    try:
        with open(FEED_PICKLE_FILE, 'rb') as f:
            # i think we have to store the rss feed "newest-first"
            #     (everyone else does it, looks dum in firefox if "oldest-first")
            old_feed_entries = pickle.load(f)
        epoch = datetime.datetime.strptime(old_feed_entries[0]['pubDate'], '%Y-%m-%d') - datetime.timedelta(days=1)

    except:
        old_feed_entries = []
        epoch = PLANET_MONEY_EPOCH

    return (old_feed_entries, epoch)



def parse_site_into_feed(old_feed_entries, epoch):

    now = datetime.datetime.now()
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

        parser = PlanetMoneyHTMLParser()
        parser.feed(the_page)
        parser.close()

        for e in parser.feed_entries:
            curdate = datetime.datetime.strptime(e['pubDate'], '%Y-%m-%d')
            if all(f['link'] != e['link'] for f in old_feed_entries) and \
               all(f['link'] != e['link'] for f in new_feed_entries):  # prevent duplicates
                new_feed_entries.append(e)

    return new_feed_entries



# TODO: use feed generator instead of manually writing text
def save_feed_entries(all_feed_entries):

    for fn in ['npr_pm_test.xml', 'npr_pm_feed.xml']:

        found_episodes = []

        with open(fn, 'w') as f:
            f.write('''<?xml version="1.0" encoding="utf-8"?>
                <rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
                <channel>
                <title>Planet Money but it's all episodes</title>
                <link>https://github.com/xjcl/planetmoney-rss/tree/gh-pages</link>
                <image><url>http://nationalpublicmedia.com/wp-content/uploads/2014/06/planetmoney.png</url></image>
                <description>pls don't sue</description>\n''')

            for e in all_feed_entries:
                f.write('<item>')
                for k,v in sorted(e.items()):
                    if k == 'pubDate':
                        v = email.utils.format_datetime(datetime.datetime.strptime(v, '%Y-%m-%d'))
                    if k == 'title':
                        if v.startswith(' Episode '):
                            # oh my god the intern deserves an ass-whooping xDDD
                            v = v[1:]
                        if v.startswith('Episode '):
                            v = '#' + v[8:]
                            found_episodes.append(int(v[1:v.find(':')]))
                    if k == 'link':
                        f.write('<enclosure url="' + html.escape(v) + '" length="0" type="audio/mpeg"/>')
                    f.write('<' + k + '>' + html.escape(v) + '</' + k + '>')
                f.write('</item>\n')

            f.write('</channel></rss>\n')

        found_episodes.reverse()

        # test if our scraping missed any episodes  (won't detect missing re-runs)
        print()
        print(found_episodes, file=sys.stderr)
        last_nr = 377
        for ep_nr in found_episodes:
            # print(ep_nr, file=sys.stderr)
            if ep_nr < last_nr:  # re-run  => okay
                pass
            elif ep_nr == last_nr:
                print('double entry!', file=sys.stderr)
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

    with open(FEED_PICKLE_FILE, 'wb') as f:
        pickle.dump(all_feed_entries, f)



if __name__ == '__main__':
    old_feed_entries, epoch = load_feed_entries()
    new_feed_entries = parse_site_into_feed(old_feed_entries, epoch)
    save_feed_entries(new_feed_entries + old_feed_entries)

# TODO: quality control, e.g. list of episode numbers from feed, and compare to reference using a test case ?
# TODO: fix new eps addition bug
# TODO: automate new eps addition (server?)
