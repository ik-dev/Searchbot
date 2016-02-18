import os
import urllib2
import argparse
import logging
from bs4 import BeautifulSoup


LOG = logging.getLogger('ScrapeBot')
ch = logging.StreamHandler()
LOG.addHandler(ch)
LOG.setLevel(logging.INFO)


class TunesCrawler(object):
    def __init__(self, proxy=None):
        self.base = 'https://9xtunes.com'
        self.proxy = proxy

    def get_tree(self, url):
        LOG.debug('Scraping %s' % url)
        source = urllib2.urlopen(url).read()
        return BeautifulSoup(source, 'html.parser')

    def get_search_string(self, album):
        return '/search?q=' + '+'.join(album.split())

    def search_for_album(self, album):
        LOG.info('Searching for album %s', album)
        search_url = self.base + self.get_search_string(album)
        tree = self.get_tree(search_url)
        for div in tree.findAll('div', {'class': 'info'}):
            anchor = div.find('h4').find('a', text=album.title())
            if anchor:
                href = anchor['href']
                if href.startswith('/album'):
                    return href

    def download_file(self, url):
        ph = urllib2.ProxyHandler({'http': self.proxy, 'https': self.proxy})
        opener = urllib2.build_opener(ph)
        urllib2.install_opener(opener)
        url_obj = urllib2.urlopen(url)
        filename = os.path.basename(url_obj.geturl())

    def scrape_for_link(self, album_url, look_for_singles=False):
        def get_download_link(box):
            divs = box.findAll('div', {'class': 'left-col'})
            anchors = [div.find('a')['href'] for div in divs]
            return anchors[-1]

        def get_zip():
            LOG.info('Searching for zip link')
            zip_link = tree.find('div', {'class': 'album-zip-link'})
            if zip_link:
                zip_link = zip_link.find('a')['href']
                if zip_link and zip_link.startswith('/zip'):
                    _tree = self.get_tree(self.base + zip_link)
                    zip_box = _tree.find('div', {'class': 'album-zip-box'})
                    if zip_box:
                        return get_download_link(zip_box)

        def get_album_list():
            LOG.info('Searching for individual songs list')
            songs_link = []
            songs_list = tree.findAll('li', {'class': 'album-song-items'})
            for song in songs_list:
                song_link = song.find('div', {'class': 'song-name'})
                if song_link:
                    song_link = song_link.find('a')['href']
                    if song_link and song_link.startswith('/single'):
                        _tree = self.get_tree(self.base + song_link)
                        song_box = _tree.find('div', {'class': 'song-link-box'})
                        if song_box:
                            songs_link.append(get_download_link(song_box))
            return songs_link

        album_url = self.base + album_url
        tree = self.get_tree(album_url)

        if look_for_singles:
            album_link = get_album_list()
            if len(album_link):
                LOG.info('Found all singles link. :)')
                LOG.info('\n'.join(album_link))
            else:
                LOG.error('Failed to scrape singles link for album :|')
        else:
            album_link = get_zip()
            if album_link:
                LOG.info('Found a zip link! :D')
                LOG.info(album_link)
            else:
                LOG.error('Failed to scrape zip link for album :|')

    def search(self, album, look_for_singles=False):
        album_url = self.search_for_album(album)
        if album_url:
            self.scrape_for_link(album_url, look_for_singles)
        else:
            LOG.error('Failed to find the album :(')


def get_args():
    parser = argparse.ArgumentParser(description='Scrapes 9xtunes for album link')
    parser.add_argument('-a', '--album',
                        required=True,
                        action='store',
                        type=str,
                        help='Name of album to search for')
    parser.add_argument('-s', '--singles',
                        required=False,
                        action='store_true',
                        default=False,
                        help='List link for singles in album')
    parser.add_argument('-v', '--verbose',
                        required=False,
                        action='store_true',
                        help='Detailed info of background')
    parser.add_argument('-p', '--proxy',
                        required=False,
                        action='store',
                        help='Proxy to be used for downloading')
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()

    if args.verbose:
        fmt = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
        ch.setFormatter(fmt)
        LOG.setLevel(logging.DEBUG)

    c = TunesCrawler(args.proxy)
    c.search(args.album.strip(), args.singles)
