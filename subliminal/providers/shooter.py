# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import logging
import json

from babelfish import Language
from requests import Session

from . import Provider
from .. import __short_version__
from ..subtitle import Subtitle, fix_line_ending
from ..video import Episode, Movie

logger = logging.getLogger(__name__)


class ShooterSubtitle(Subtitle):
    provider_name = 'shooter'

    def __init__(self, language, hash, download_link):
        super(ShooterSubtitle, self).__init__(language)
        self.hash = hash
        self.download_link = download_link

    def get_matches(self, video):
        matches = set()
        # hash
        if 'shooter' in video.hashes and video.hashes['shooter'] == self.hash:
            matches.add('hash')
        return matches


class ShooterProvider(Provider):
    languages = {Language(l) for l in [
        'eng', 'zho'
    ]}
    required_hash = 'shooter'
    video_types = (Episode, Movie)
    server = 'https://www.shooter.cn/api/subapi.php'

    def initialize(self):
        self.session = Session()
        self.session.headers['User-Agent'] = 'Subliminal/%s' % __short_version__

    def terminate(self):
        self.session.close()

    def query(self, language, filename, hash=None):
        params = {
            'filehash': hash,
            'pathinfo': os.path.realpath(filename),
            'format': 'json',
            'lang': language.shooter,
        }
        logger.debug('Searching subtitles %r', params)
        r = self.session.post(self.server, verify=False, params=params, timeout=10)
        r.raise_for_status()

        if r.content == b'\xff':
            logger.debug('No subtitle found')
            return []
        raw_json = json.loads(r.text)
        subtitles = [ShooterSubtitle(language, hash, t['Link']) for s in raw_json for t in s['Files']]
        return subtitles

    def list_subtitles(self, video, languages):
        return [s for l in languages for s in self.query(l, video.name, video.hashes['shooter'])]

    def download_subtitle(self, subtitle):
        logger.info('Downloading subtitle %r', subtitle)
        r = self.session.get(subtitle.download_link)
        r.raise_for_status()

        subtitle.content = fix_line_ending(r.content)
