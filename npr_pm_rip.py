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


def npr_HTML_request(url):
    req = urllib.request.Request(url)
    req.add_header('Cookie', 'trackingChoice=true; dateOfChoice=1528282943947; choiceVersion=1')  # GDPR cookie

    with urllib.request.urlopen(req) as response:
        return str(response.read(), 'utf-8')


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
            # TODO: some are missing duration, eg #366  (DL?)
            if attrs.get('class') == 'audio-module-duration':
                self.next_attr = 'itunes:duration'
            elif self.prev.attrs.get('class') == 'dateblock' or 'href' in self.prev.attrs:
                self.feed_entry['pubDate'] = attrs['datetime']

        # don't use download link for download but instead stream-link as some DL links are missing ! eg #702
        if attrs.get('class') == 'audio-module-controls-wrap' and self.prev.attrs.get('class') == 'audio-module-title' and 'data-audio' in attrs:
            self.feed_entry['link'] = json.loads(attrs['data-audio'])['audioUrl']   # ondemand.npr.org
            if not self.feed_entry['link'].startswith('https://'):
                self.feed_entry['link'] = base64.b64decode(self.feed_entry['link']).decode('UTF-8')  # WTF???

        # download links deleted..
        if self.feed_entry.get('title') == 'Hear: They Know You':
            self.feed_entry['link'] = 'http://podcastdownload.npr.org/anon.npr-podcasts/podcast/510289/104203194/npr_104203194.mp3'
        if self.feed_entry.get('title') == 'Secrets Of The Watchmen':
            self.feed_entry['link'] = 'http://podcastdownload.npr.org/anon.npr-podcasts/podcast/510289/105020259/npr_105020259.mp3'
        # download links missing..
        if self.feed_entry.get('title') == 'Episode 830: XXX-XX-XXXX':
            self.feed_entry['link'] = 'https://20963.mc.tritondigital.com/NPR_510289/media-session/0d8e5b34-3266-4faf-8068-7a7b414b2be2/anon.npr-podcasts/podcast/npr/pmoney/2018/03/20180314_pmoney_pmpod830-2d1cb700-1ad5-4fd4-89a7-3c51f6d31b39.mp3?orgId=1&d=1243&p=510289&story=593603674&t=podcast&e=593603674&siteplayer=true&dl=1'

        self.prev = self.tagattrs(tag, attrs)

    # re-use scraping code on an indiviual episode's page (= subpage), this requires some trickery
    #   (combining all fake feed_entries of the subpage on top of the current dict)
    def add_subpage_info(self, url):
        the_page = npr_HTML_request(url)

        parser = PlanetMoneyHTMLParser()
        parser.feed(the_page)
        if 'audio-module-controls-wrap' not in the_page or '<b class="audio-availability-message">Audio for this story is unavailable.</b>' in the_page:
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
                # manually add previous episode for the 3 eps missing in the feed
                if self.subpage == 'https://www.npr.org/sections/money/2016/07/22/487069271/episode-576-when-women-stopped-coding':
                    self.feed_entries.append(self.feed_entry)
                    self.feed_entry = {}
                    self.add_subpage_info('https://www.npr.org/sections/money/2016/07/20/486785422/episode-713-paying-for-the-crime')

                if self.subpage == 'https://www.npr.org/sections/money/2010/08/03/128960709/the-tuesday-podcast':
                    self.feed_entries.append(self.feed_entry)
                    self.feed_entry = {}
                    self.add_subpage_info('https://www.npr.org/sections/money/2010/07/30/128880374/the-friday-podcast-tallying-up-the-pelican-bill')

                if self.subpage == 'https://www.npr.org/sections/money/2018/08/29/643072388/episode-783-new-jersey-bails-out':
                    self.feed_entries.append(self.feed_entry)
                    self.feed_entry = {}
                    print('prev')
                    self.add_subpage_info('https://www.npr.org/sections/money/2018/08/24/641739640/episode-861-food-scare-squad')

                self.subpage = None

            # is unindented to sneakily handle a subpage's pseduo-feed also
            self.feed_entries.append(self.feed_entry)
            self.feed_entry = {}


    def handle_data(self, data):
        if not self.next_attr:
            return

        if self.tag_stack:
            return

        # o god pls stop with the inconsistencies =/  affects #824 #657 #618 and others  -> 'Listen ' 'Listen to Podcast' 'Listen to Mark's Story' etc
        if self.next_attr == 'title' and data.startswith('Listen ') and not data.startswith('Listen Up'):
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
URL_STEM = 'https://www.npr.org/sections/money/127413729/planet-money/archive'


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
    print('Going through ~' + str(math.ceil((now - epoch).days / 40)) + ' pages of episodes, please be patient...')
    req_nr = 0

    new_feed_entries = []

    # we have to iteratre from present to the past because we need to know the last date to make the next request
    curdate = now
    while curdate > epoch:

        req_nr += 1
        print('On page #' + str(req_nr) + ' for date ' + curdate.strftime('%Y-%m-%d'), end='\r')

        full_url = URL_STEM + curdate.strftime('?date=%m-%d-%Y')  # site uses yankeedates !! lmao

        # print('init DL-ing ' + full_url)
        parser = PlanetMoneyHTMLParser()
        parser.feed(npr_HTML_request(full_url))
        parser.close()

        for e in parser.feed_entries:
            # exclude space overview page with 4 episode links
            if not 'link' in e or e['title'] == 'Episode 4':
                continue
            curdate = dateutil.parser.parse(e['pubDate'])
            # prevent duplicates -- nb PM sometimes changes links =/// (version 2's etc) -> podcatcher thinks it's a SEPERATE ep
            if all(f['link'] != e['link'] for f in old_feed_entries) and \
               all(f['link'] != e['link'] for f in new_feed_entries) and \
               all(f['pubDate'] != e['pubDate'] for f in old_feed_entries) and \
               all(f['pubDate'] != e['pubDate'] for f in new_feed_entries):
                new_feed_entries.append(e)

    return new_feed_entries


# TODO: use feed generator instead of manually writing text
def save_feed_entries(all_feed_entries):

    print('All requests done! Now saving to file(s).')

    with open(FEED_PICKLE_FILE, 'wb') as f:
        pickle.dump(all_feed_entries, f)


    all_feed_entries.reverse()

    started_count = False
    ep = None

    # sanitize feed entries:  add ep #'s, san titles, ..
    for i,e in enumerate(all_feed_entries):

        print('--------')
        print(e['title'])

        e['guid'] = e['link']
        e['pubDate'] = email.utils.format_datetime(dateutil.parser.parse(e['pubDate']))

        for stripme in ('Hear: ', 'Podcast: ', 'Listen Up: ', 'The Friday Podcast: ', 'The Tuesday Podcast: '):
            if e['title'].startswith(stripme):
                e['title'] = e['title'][len(stripme):]

        if e['title'].startswith(' Episode '):  # affected: #428 #567  -> intern's ass = whooped
            e['title'] = e['title'][1:]
        if e['title'].startswith(' #'):  # affected: #833
            e['title'] = e['title'][1:]
        if e['title'].startswith('Episode '):
            e['title'] = '#' + e['title'][8:]

        if "Japan's Lost Lesson" in e['title'] and not started_count:
            started_count = True
            ep = 1

        if e['title'].startswith('Deep Read: ') or e['title'].startswith('Our First Podcast: '):
            continue

        if e['title'].startswith('SPACE ') or e['title'].startswith('Oil #'):
            ep += 1
            continue

        if any(x in e['title'] for x in ['Episode #1', "'The Souls Of China'"]):
            continue

        # some episodes have original titles different from their re-run titles  => needed for matching
        if e['title'] == 'Medieval Economics':
            e['title'] = 'Bloody, Miserable Medieval Economics'
        if e['title'] == 'The Rise And Fall Of An Internet Giant':
            e['title'] = 'MySpace Was Born Of Total Ignorance. Also Porn And Spyware'
        if e['title'] == 'Why Economists Hate Gifts':
            e['title'] = 'Making Christmas More Joyful, And More Efficient'
        if e['title'] == 'How To Kill A Currency':
            e['title'] = 'Kill The Euro, Win $400,000'


        if started_count:

            m = re.match('#[0-9]+: ', e['title'])

            if m:
                ep_nr = m.group(0)[1:-2]
                if ep == int(ep_nr):
                    ep += 1
                else:
                    # has to be a re-run, otherwise we skipped something
                    assert int(ep_nr) < ep

            else:
                # manually add numbering, either based on re-runs (for) or on counter (else)
                for f in all_feed_entries[:i]:
                    old_title = f['title']
                    m_old = re.match('#[0-9]+: ', old_title)
                    if m_old:
                        old_title = old_title[m_old.end(0):]
                    if e['title'] == old_title:
                        e['title'] = f['title']
                        break
                else:
                    e['title'] = '#' + str(ep) + ': ' + e['title']
                    ep += 1

        # missing and forever lost -- RIP
        while ep in (139,):
            ep += 1

        print(e['title'])


    all_feed_entries.reverse()

    found_episodes = []

    with open('npr_pm_feed.xml', 'w') as f:
        f.write('''<?xml version="1.0" encoding="utf-8"?>
            <rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
            <channel>
            <title>Planet Money but it's all episodes</title>
            <link>https://github.com/xjcl/planetmoney-rss/tree/gh-pages</link>
            <image><url>http://nationalpublicmedia.com/wp-content/uploads/2014/06/planetmoney.png</url></image>
            <description>NPR's Planet Money. The economy, explained. Collated into a full-history feed by /u/xjcl.</description>\n''')

        for i,e in enumerate(all_feed_entries):
            f.write('<item>\n')
            for k,v in sorted(e.items()):
                if k == 'title':
                    if v.startswith('#'):
                        found_episodes.append(int(v[1:v.find(':')]))
                if k == 'link':
                    f.write('<enclosure url="' + html.escape(v) + '" type="audio/mpeg"/>')
                f.write('<' + k + '>' + html.escape(v) + '</' + k + '>\n')
            f.write('</item>\n\n')

        f.write('</channel></rss>\n')

    found_episodes.reverse()

    # test if our scraping missed any episodes  (won't detect missing re-runs)
    last_nr = 0
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
            # hardcode episodes that are NOT missing but just with different titles:  "Oil #X" (716-720) and "SPACE X" (808-811)
            if (last_nr, ep_nr) in [(715, 721), (807, 812)]:
                last_nr = ep_nr
                continue
            if last_nr+1 == ep_nr-1:
                print('missing ep ' + str(last_nr+1) + '!', file=sys.stderr)
            else:
                print('missing eps ' + str(last_nr+1) + ' to ' + str(ep_nr-1) + '!', file=sys.stderr)
            last_nr = ep_nr


# pop n most recent episodes from history  -> used for debugging and bugfixes
def pop_from_history(n):
    with open(FEED_PICKLE_FILE, 'rb+') as f:
        feed = pickle.load(f)[n:]
        f.seek(0)
        pickle.dump(feed, f)


if __name__ == '__main__':
    old_feed_entries, epoch = load_feed_entries()
    new_feed_entries = parse_site_into_feed(old_feed_entries, epoch)   #TODO: add try..except for inet
    save_feed_entries(new_feed_entries + old_feed_entries)

# TODO: (low-prio) add pictures

# TODO: automate new eps addition (server?)
# TODO: why do some episodes have info on mm:ss length and some don't ?
# TODO: episode duration for ALL episodes, eg #407

# TODO: deprecate 'npr_pm_test.xml'
# TODO: This American Life ?
# TODO: make cps of the indicator just in case ?

# TODO: fix titles+descriptions for early episodes

# TODO: missing links from
# http://www.podcasts.com/npr_planet_money_podcast/page/2152
# TODO: check if old episodes are all there (screenshot)

# TODO: #858 has excess space in the official feed
