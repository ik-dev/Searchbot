import os
import urllib2
import argparse
import logging

from pprint import pprint
from bs4 import BeautifulSoup


LOG = logging.getLogger('ScrapeBot')
ch = logging.StreamHandler()
LOG.addHandler(ch)
LOG.setLevel(logging.INFO)


class FailedToFind(Exception):
    message = 'Failed to find.'
    def __init__(self, **kwargs):
        message = self.message % kwargs
        super(FailedToFind, self).__init__(message)


class FailedToFindAlbum(FailedToFind):
    message = "Failed to find '%(album)s' album."


class FailedToFindSingle(FailedToFind):
    message = "Failed to find '%(single)s' single."


class FailedToFindDownloadLink(FailedToFind):
    message = "Failed to find download link for '%(link)s'."


class FailedToFindZipLink(FailedToFind):
    message = "Failed to find single link for '%(url)s'."


class FailedToFindIndividualLink(FailedToFind):
    message = "Failed to find individual songs link for '%(url)s'."


class NotReleasedOrRemoved(FailedToFind):
    message = "Not released yet or link removed for '%(link)s'"


class TunesCrawler(object):
    def __init__(self, proxy=None):
        self.base = 'https://9xtunes.com'
        self.proxy = proxy

    def get_tree(self, url):
        url = self.base + url
        LOG.debug('Reading %s' % url)
        source = urllib2.urlopen(url).read()
        return BeautifulSoup(source, 'html.parser')

    def get_search_string(self, query):
        return '/search?q=' + '+'.join(query.split())

    def search_for_album(self, album):
        LOG.info('Searching for album %s', album)
        search_url = self.get_search_string(album)
        tree = self.get_tree(search_url)
        target_href = None
        for div in tree.findAll('div', {'class': 'info'}):
            anchor = div.find('h4').find('a', text=album.title())
            if anchor:
                href = anchor['href']
                if href.startswith('/album'):
                    target_href = href
                    break
        if not target_href:
            raise FailedToFindAlbum(album=album)
        return target_href

    def search_for_single(self, name):
        LOG.info('Searching for single %s' % name)
        search_url = self.get_search_string(name)
        tree = self.get_tree(search_url)
        target_href = None
        for div in tree.findAll('div', {'class': 'info'}):
            anchor = div.find('h4').find('a', text=name.title())
            if anchor:
                href = anchor['href']
                if href.startswith('/single'):
                    target_href = href
                    break
        if not target_href:
            raise FailedToFindSingle(single=name)
        return target_href

    def search_for_latest(self, singles=False):
        if singles:
            LOG.info('Scraping for latest single links')
            latest_url = '/category/bollywood-singles'
        else:
            LOG.info('Scraping for latest album link')
            latest_url = '/category/bollywood-albums'
        tree = self.get_tree(latest_url)
        for div in tree.findAll('div', {'class': 'info'}):
            anchor = div.find('h4').find('a')
            yield anchor.text, anchor['href']

    def download_file(self, url):
        ph = urllib2.ProxyHandler({'http': self.proxy, 'https': self.proxy})
        opener = urllib2.build_opener(ph)
        urllib2.install_opener(opener)
        url_obj = urllib2.urlopen(url)
        filename = os.path.basename(url_obj.geturl())
        
    def get_download_link(self, link, box):
        divs = box.findAll('div', {'class': 'left-col'})
        anchors = [div.find('a')['href'] for div in divs]
        try:
            return anchors[-1]
        except IndexError:
            raise NotReleasedOrRemoved(link=link)

    def get_single_song_link(self, song_link):
        _tree = self.get_tree(song_link)
        song_box = _tree.find('div', {'class': 'song-link-box'})
        if not song_box:
            raise FailedToFindDownloadLink(link=song_link)
        return self.get_download_link(song_link, song_box)

    def get_album_zip_link(self, zip_link):
        _tree = self.get_tree(zip_link)
        zip_box = _tree.find('div', {'class': 'album-zip-box'})
        if not zip_box:
            raise FailedToFindDownloadLink(link=zip_link)
        return self.get_download_link(zip_link, zip_box)

    def get_entire_album(self, album_url):
        tree = self.get_tree(album_url)
        LOG.info('Searching single link for full album')
        zip_link = tree.find('div', {'class': 'album-zip-link'})
        if not zip_link:
            raise FailedToFindDownladLink(url=album_url)
        zip_link = zip_link.find('a')['href']
        if zip_link and zip_link.startswith('/zip'):
            return self.get_album_zip_link(zip_link)
        else:
            raise FailedToFindZipLink(url=album_url)

    def get_album_songs(self, album_url):
        tree = self.get_tree(album_url)
        LOG.info('Searching links for individual songs')
        songs_list = tree.findAll('li', {'class': 'album-song-items'})
        songs_link = []
        for song in songs_list:
            song_link = song.find('div', {'class': 'song-name'})
            if song_link:
                song_link = song_link.find('a')['href']
                if song_link and song_link.startswith('/single'):
                    try:
                        final_link = self.get_single_song_link(song_link)
                    except NotReleasedOrRemoved as e:
                        LOG.error(str(e))
                    else:
                        if final_link:
                            songs_link.append(final_link)
        if not len(songs_link):
            raise FailedToFindIndividualLink(url=album_url)
        return songs_link

    def get_latest(self, singles=False):
        latest_links = self.search_for_latest(singles)
        for name, link in latest_links:
            print "%-40s %s" % (name, link)

    def get_album(self, album, individual_link=False):
        album_url = self.search_for_album(album)
        if not individual_link:
            download_url = self.get_entire_album(album_url)
        else:
            download_url = self.get_album_songs(album_url)
        pprint(download_url)

    def get_single(self, name):
        single_url = self.search_for_single(name)
        download_url = self.get_single_song_link(single_url)
        pprint(download_url)

    def get_from_uri(self, uri):
        if uri.startswith('/single'):
            download_url = self.get_single_song_link(uri)
        elif uri.startswith('/album'):
            download_url = self.get_entire_album(uri)
        else:
            raise ValueError("Invalid uri '%s'")
        pprint(download_url)


def get_args():
    parser = argparse.ArgumentParser(description='Scrapes 9xtunes for album link')
    parser.add_argument('-a', '--album',
                        required=False,
                        action='store',
                        type=str,
                        help='Name of album to search for.')
    parser.add_argument('-s', '--single',
                        required=False,
                        action='store',
                        type=str,
                        help='Name of song to search for.')
    parser.add_argument('-u', '--uri',
                        required=False,
                        action='store',
                        help='URI for the song/album')
    parser.add_argument('-i', '--individual',
                        required=False,
                        action='store_true',
                        default=False,
                        help='Individual songs link.')
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

    if args.album:
        c.get_album(args.album, args.individual)
    elif args.single:
        c.get_single(args.single)
    elif args.uri:
        c.get_from_uri(args.uri)
    else:
        c.get_latest(args.individual)
