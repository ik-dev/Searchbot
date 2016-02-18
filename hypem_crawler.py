import time
import urllib2
import argparse
from bs4 import BeautifulSoup


def get_args():
    parser = argparse.ArgumentParser(description='Hype Machine crawler')
    parser.add_argument('-g', '--genre',
                        action='store',
                        type=str,
                        default='popular',
                        help='Genre type to search for.')
    parser.add_argument('-p', '--pages',
                        action='store',
                        type=int,
                        default=1,
                        help='Number of pages to list.')
    return parser.parse_args()


args = get_args()

genre = '+'.join(args.genre.lower().split())

pages = args.pages or 1

ts = int(time.time())

if 'popular' in genre:
    base_url = 'http://hypem.com/%s' % genre
else:
    base_url = 'http://hypem.com/tags/%s' % genre

for page in xrange(1, pages + 1):
    url = base_url + '/%d/?ax=1&ts=%d' % (page, ts)
    source = urllib2.urlopen(url).read()
    tree = BeautifulSoup(source, 'html.parser')
    for track in tree.findAll('h3', {'class': 'track_name'}):
        track_artist = track.find('a', {'class': 'artist'}).text.title()
        track_name = track.find('a', {'class': 'track'}).text.title()
        print '%s %s' % (track_artist.strip(), track_name.strip())
