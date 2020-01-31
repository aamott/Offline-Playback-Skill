# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
INTRO:
Spotify is a little different than some music services.  The APIs encourage
a sort of network of music players.  So this skill will act as a remote
controller when another Spotify player is already running and it is invoked.
Otherwise it begins playing the music locally using the Mycroft-controlled
hardware.  (Which, depending on the audio setup, might not be the main
speaker on the equipment.)
"""

# Adam Amott notes:
# Replaced all instances of 'uri' with 'dir'
#
import re
from mycroft.skills.core import intent_handler
from mycroft.util.parse import match_one, fuzzy_match
from mycroft.api import DeviceApi
from mycroft.messagebus import Message
from adapt.intent import IntentBuilder

import time
from os.path import abspath, dirname, join
from subprocess import call, Popen, DEVNULL
import signal
from socket import gethostname

#For Amarok
import sys
import dbus
import glib
import os
import psutil
from traceback import print_exc
from mycroft.skills.audioservice import AudioService

#not needed
"""
#import spotipy
from .spotify import (MycroftSpotifyCredentials, SpotifyConnect,
                      get_album_info, get_artist_info, get_song_info)
"""
import random

from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel

from enum import Enum

#not needed
"""
class DeviceType(Enum):
    MYCROFT = 1
    DEFAULT = 2
    DESKTOP = 3
    FIRSTBEST = 4
    NOTFOUND = 5


class SpotifyPlaybackError(Exception):
    pass


class NoSpotifyDevicesError(Exception):
    pass

"""
class PlaylistNotFoundError(Exception):
    pass

#not needed
"""
class SpotifyNotAuthorizedError(Exception):
    pass

# Platforms for which the skill should start the spotify player
MANAGED_PLATFORMS = ['mycroft_mark_1', 'mycroft_mark_2pi']
"""
# Return value definition indication nothing was found
# (confidence None, data None)
NOTHING_FOUND = (None, 0.0)

# Confidence levels for generic play handling
DIRECT_RESPONSE_CONFIDENCE = 0.8

MATCH_CONFIDENCE = 0.5


def best_result(results):
    """Return best result from a list of result tuples.

    Arguments:
        results (list): list of spotify result tuples

    Returns:
        Best match in list
    """
    if len(results) == 0:
        return NOTHING_FOUND
    else:
        results.reverse()
        return sorted(results, key=lambda x: x[0])[-1]

#important
def best_confidence(title, query):
    """Find best match for a title against a query.

    Some titles include ( Remastered 2016 ) and similar info. This method
    will test the raw title and a version that has been parsed to remove
    such information.

    Arguments:
        title: title name from spotify search
        query: query from user

    Returns:
        (float) best condidence
    """
    best = title.lower()
    best_stripped = re.sub(r'(\(.+\)|-.+)$', '', best).strip()
    return max(fuzzy_match(best, query),
               fuzzy_match(best_stripped, query))

"""
#not needed
def update_librespot():
    try:
        call(["bash", join(dirname(abspath(__file__)), "requirements.sh")])
    except Exception as e:
        print('Librespot Update failed, {}'.format(repr(e)))
"""

def status_info(status):
    """Return track, artist, album tuple from spotify status.

    Arguments:
        status (dict): Spotify status info

    Returns:
        tuple (track, artist, album)
     """
    try:
        artist = status['item']['artists'][0]['name']
    except Exception:
        artist = 'unknown'
    try:
        track = status['item']['name']
    except Exception:
        track = 'unknown'
    try:
        album = status['item']['album']['name']
    except Exception:
        album = 'unknown'
    return track, artist, album


class PlayLocallySkill(CommonPlaySkill):
    """Spotify control through the Spotify Connect API."""
    """But now we're making it play locally with Amarok or something"""

    def __init__(self):
        super(PlayLocallySkill, self).__init__()
        self.audio_service = AudioService(self.bus)
        self.index = 0
        self.offline_player = None
        self.process = None
        self.device_name = None
        self.dev_id = None
        self.idle_count = 0
        self.ducking = False
        self.is_player_remote = False   # when dev is remote control instance
        self.mouth_text = None
        self.music_player_starting = False
        self.music_player_failed = False
        # ^ My code ^

        self.__device_list = None
        self.__devices_fetched = 0
        self.OAUTH_ID = 1
        enclosure_config = self.config_core.get('enclosure')
        self.platform = enclosure_config.get('platform', 'unknown')
        self.DEFAULT_VOLUME = 80 if self.platform == 'mycroft_mark_1' else 100
        self._playlists = None
        self.saved_tracks = None
        self.regexes = {}
        self.last_played_type = None  # The last dir type that was started
        self.is_playing = False

    def translate_regex(self, regex):
        """If the regex is not already in regexes,
         look for regex files and put them in self.regexes """
        if regex not in self.regexes:
            path = self.find_resource(regex + '.regex')
            if path:
                with open(path) as f:
                    string = f.read().strip()
                self.regexes[regex] = string
        return self.regexes[regex]

    #My own module
    def get_path():
        """find the path for the specified player"""
        """Right now, just return, "amarok", but allow for more later"""
        return amarok

    """#not needed
    def launch_librespot(self):
    """ #replaced with below line
    def launch_player(self):
        """Launch the librespot binary for the Mark-1."""
        """Launch the player binary for the Mark-1"""
        self.music_player_starting = True
        #path = self.settings.get('librespot_path', None)
        path = get_path() #Instead of that ^, let's do this

        """ #not needed
        if (path and self.device_name and
                'user' in self.settings and 'password' in self.settings):
        """
        #if path in self.settings: #instead of that ^, this line. We need no passwd
            # Disable librespot logging if not specifically requested
            log_level = self.config_core.get('log_level', '')
            if 'offline_music_player_log' in self.settings or log_level == 'DEBUG':
                outs = None
            else:
                outs = DEVNULL

            """
            self.process = Popen([path, '-n', self.device_name,
                                  '-u', self.settings['user'],
                                  '-p', self.settings['password']],
                                 stdout=outs, stderr=outs)
            """
            #do this instead of that ^
            self.process = Popen([path, '-n'],
                                 stdout=outs, stderr=outs)

            time.sleep(3)  # give libreSpot time to start-up
            if self.process and self.process.poll() is not None:
                self.log.error(path, 'failed to start.')
                self.music_player_failed = True
                self.process = None
                self.music_player_starting = False
                return

            # Lower the volume since max volume sounds terrible on the Mark-1
            dev = self.device_by_name(self.device_name)
            if dev:
                self.offline_player.volume(dev['id'], self.DEFAULT_VOLUME)
        self.music_player_starting = False

    def initialize(self):
        # Make sure the spotify login scheduled event is shutdown
        super().initialize()
        #not needed
        #self.cancel_scheduled_event('SpotifyLogin')

        # Setup handlers for playback control messages
        self.add_event('mycroft.audio.service.next', self.next_track)
        self.add_event('mycroft.audio.service.prev', self.prev_track)
        self.add_event('mycroft.audio.service.pause', self.pause)
        self.add_event('mycroft.audio.service.resume', self.resume)

        #This ain't needed. not needed
        """
        # Check and then monitor for credential changes
        self.settings.set_changed_callback(self.on_websettings_changed)
        # Retry in 5 minutes
        self.schedule_repeating_event(self.on_websettings_changed,
                                      None, 5 * 60, name='SpotifyLogin')

        if self.platform in MANAGED_PLATFORMS:
            update_librespot()
        self.on_websettings_changed()
        """ #and we toasted that setting right up there. The module in gone
    #not needed. Not an online web service
    """
    def on_websettings_changed(self):
        # Only attempt to load credentials if the username has been set
        # will limit the accesses to the api.
        if not self.spotify and self.settings.get('user', None):
            try:
                self.load_credentials()
            except Exception as e:
                self.log.debug('Credentials could not be fetched. '
                               '({})'.format(repr(e)))

        if self.spotify:
            self.cancel_scheduled_event('SpotifyLogin')
            if 'user' in self.settings and 'password' in self.settings:
                if self.process:
                    self.stop_librespot()
                self.launch_player()

            # Refresh saved tracks
            # We can't get this list when the user asks because it takes too long
            # and causes mycroft-playback-control.mycroftai:PlayQueryTimeout
            self.refresh_saved_tracks()
    """

    #not needed. No credentials needed for an offline program
    """
    def load_credentials(self):
        ""Retrieve credentials from the backend and connect to Spotify.""
        try:
            creds = MycroftSpotifyCredentials(self.OAUTH_ID)
            self.spotify = SpotifyConnect(client_credentials_manager=creds)
        except HTTPError:
            self.log.info('Couldn\'t fetch credentials')
            self.spotify = None

        if self.spotify:
            # Spotfy connection worked, prepare for usage
            # TODO: Repeat occasionally on failures?
            # If not able to authorize, the method will be repeated after 60
            # seconds
            self.create_intents()
            # Should be safe to set device_name here since home has already
            # been connected
            self.device_name = DeviceApi().get().get('name')
    """

    #not needed. No failed authorizations in offline module
    """
    def failed_auth(self):
        if 'user' not in self.settings:
            self.log.error('Settings hasn\'t been received yet')
            self.speak_dialog('NoSettingsReceived')
        elif not self.settings.get("user"):
            self.log.error('User info has not been set.')
            # Assume this is initial setup
            self.speak_dialog('NotConfigured')
        else:
            # Assume password changed or there is a typo
            self.log.error('User info has been set but Auth failed.')
            self.speak_dialog('NotAuthorized')
    """
    ######################################################################
    # Handle auto ducking when listener is started.

    def handle_listener_started(self, message):
        """Handle auto ducking when listener is started.

        The ducking is enabled/disabled using the skill settings on home.

        TODO: Evaluate the Idle check logic
        """
        if (self.offline_player.is_playing() and #self.is_player_remote and #It's not a player remote anymore
                self.settings.get('use_ducking', False)):
            self.__pause()
            self.ducking = True

            # Start idle check
            self.idle_count = 0
            self.cancel_scheduled_event('IdleCheck')
            self.schedule_repeating_event(self.check_for_idle, None,
                                          1, name='IdleCheck')

    def check_for_idle(self):
        """Repeating event checking for end of auto ducking."""
        if not self.ducking:
            self.cancel_scheduled_event('IdleCheck')
            return

        active = self.enclosure.display_manager.get_active()
        if not active == '' or active == 'PlayLocallySkill':
            # No activity, start to fall asleep
            self.idle_count += 1

            if self.idle_count >= 5:
                # Resume playback after 5 seconds of being idle
                self.cancel_scheduled_event('IdleCheck')
                self.ducking = False
                self.audio_service.resume()
        else:
            self.idle_count = 0

    ######################################################################
    # Mycroft display handling

    def start_monitor(self):
        """Monitoring and current song display."""
        # Clear any existing event
        self.stop_monitor()

        # Schedule a new one every 5 seconds to monitor/update display
        self.schedule_repeating_event(self._update_display,
                                      None, 5,
                                      name='MonitorOfflinePlayer')
        self.add_event('recognizer_loop:record_begin',
                       self.handle_listener_started)

    def stop_monitor(self):
        # Clear any existing event
        self.cancel_scheduled_event('MonitorOfflinePlayer')

    def _update_display(self, message):
        # Checks once a second for feedback
        status = self.offline_player.status() if self.offline_player else {}
        self.is_playing = self.offline_player.is_playing()

        if not status or not status.get('is_playing'):
            self.stop_monitor()
            self.mouth_text = None
            self.enclosure.mouth_reset()
            self.disable_playing_intents()
            return

        # Get the current track info
        try:
            artist = status['item']['artists'][0]['name']
        except Exception:
            artist = ''
        try:
            track = status['item']['name']
        except Exception:
            track = ''
        try:
            image = status['item']['album']['images'][0]['url']
        except Exception:
            image = ''

        self.CPS_send_status(artist=artist, track=track, image=image)

        # Mark-1
        if artist and track:
            text = '{}: {}'.format(artist, track)
        else:
            text = ''

        # Update the "Now Playing" display if needed
        if text != self.mouth_text:
            self.mouth_text = text
            self.enclosure.mouth_text(text)

    def CPS_send_status(self, artist='', track='', image=''):
        data = {'skill': self.name,
                'artist': artist,
                'track': track,
                'image': image,
                'status': None  # TODO Add status system
                }
        self.bus.emit(Message('play:status', data))

    def CPS_match_query_phrase(self, phrase):
        """Handler for common play framework Query."""
        # Not ready to play
        if not self.playback_prerequisits_ok():
            self.log.debug('Offline Player is not available to play')
            if 'offline' in phrase:
                return phrase, CPSMatchLevel.GENERIC
            elif 'locally' in phrase:
                return phrase, CPSMatchLevel.GENERIC
            else:
                return None

        offline_specified = 'offline' in phrase or 'locally' in phrase
        bonus = 0.1 if offline_specified else 0.0
        phrase = re.sub(self.translate_regex('offline'), '', phrase) #used to translate, "spotify"

        confidence, data = self.continue_playback(phrase, bonus)
        if not data:
            confidence, data = self.specific_query(phrase, bonus)
            if not data:
                confidence, data = self.generic_query(phrase, bonus)

        if data:
            self.log.info('Offline Player confidence: {}'.format(confidence))
            self.log.info('              data: {}'.format(data))

            if data.get('type') in ['saved_tracks', 'album', 'artist', 'track', 'playlist']:
                if offline_specified:
                    # " play great song on spotify'
                    level = CPSMatchLevel.EXACT
                else:
                    if confidence > 0.9:
                        # TODO: After 19.02 scoring change
                        # level = CPSMatchLevel.MULTI_KEY
                        level = CPSMatchLevel.TITLE
                    elif confidence < 0.5:
                        level = CPSMatchLevel.GENERIC
                    else:
                        level = CPSMatchLevel.TITLE
                    phrase += ' on spotify'
            elif data.get('type') == 'continue':
                if offline_specified > 0:
                    # "resume playback on spotify"
                    level = CPSMatchLevel.EXACT
                else:
                    # "resume playback"
                    level = CPSMatchLevel.GENERIC
                    phrase += ' on spotify'
            else:
                self.log.warning('Unexpected Offline Player type: '
                                 '{}'.format(data.get('type')))
                level = CPSMatchLevel.GENERIC

            return phrase, level, data
        else:
            self.log.debug('Couldn\'t find anything to play on Offline Player')

    def continue_playback(self, phrase, bonus):
        if phrase.strip() == 'offline' or phrase.strip() == 'locally':
            return (1.0,
                    {
                        'data': None,
                        'name': None,
                        'type': 'continue'
                    })
        else:
            return NOTHING_FOUND

    def specific_query(self, phrase, bonus):
        """
        Check if the phrase can be matched against a specific offline request.

        This includes asking for saved items, playlists, albums, artists or songs.

        Arguments:
            phrase (str): Text to match against
            bonus (float): Any existing match bonus

        Returns: Tuple with confidence and data or NOTHING_FOUND
        """
        # Check if saved
        match = re.match(self.translate_regex('saved_songs'), phrase)
        if match and self.saved_tracks:
            return (1.0, {'data': None,
                          'type': 'saved_tracks'})

        # Check if playlist
        match = re.match(self.translate_regex('playlist'), phrase)
        if match:
            return self.query_playlist(match.groupdict()['playlist'])

        # Check album
        match = re.match(self.translate_regex('album'), phrase)
        if match:
            bonus += 0.1
            album = match.groupdict()['album']
            return self.query_album(album, bonus)

        # Check artist
        match = re.match(self.translate_regex('artist'), phrase)
        if match:
            artist = match.groupdict()['artist']
            return self.query_artist(artist, bonus)
        match = re.match(self.translate_regex('song'), phrase)
        if match:
            song = match.groupdict()['track']
            return self.query_song(song, bonus)
        return NOTHING_FOUND

    def generic_query(self, phrase, bonus):
        """Check for a generic query, not asking for any special feature.

        This will try to parse the entire phrase in the following order
        - As a user playlist
        - As an album
        - As a track
        - As a public playlist

        Arguments:
            phrase (str): Text to match against
            bonus (float): Any existing match bonus

        Returns: Tuple with confidence and data or NOTHING_FOUND
        """
        self.log.info('Handling "{}" as a genric query...'.format(phrase))
        results = []

        self.log.info('Checking users playlists')
        playlist, conf = self.get_best_user_playlist(phrase)
        if playlist:
            dir = self.playlists[playlist]
            data = {
                        'data': dir,
                        'name': playlist,
                        'type': 'playlist'
                   }
        if conf and conf > DIRECT_RESPONSE_CONFIDENCE:
            return (conf, data)
        elif conf and conf > MATCH_CONFIDENCE:
            results.append((conf, data))

        # Check for artist
        self.log.info('Checking artists')
        conf, data = self.query_artist(phrase, bonus)
        if conf and conf > DIRECT_RESPONSE_CONFIDENCE:
            return conf, data
        elif conf and conf > MATCH_CONFIDENCE:
            results.append((conf, data))

        # Check for track
        self.log.info('Checking tracks')
        conf, data = self.query_song(phrase, bonus)
        if conf and conf > DIRECT_RESPONSE_CONFIDENCE:
            return conf, data
        elif conf and conf > MATCH_CONFIDENCE:
            results.append((conf, data))

        # Check for album
        self.log.info('Checking albums')
        conf, data = self.query_album(phrase, bonus)
        if conf and conf > DIRECT_RESPONSE_CONFIDENCE:
            return conf, data
        elif conf and conf > MATCH_CONFIDENCE:
            results.append((conf, data))

        # Check for public playlist
        self.log.info('Checking tracks')
        conf, data = self.get_best_public_playlist(phrase)
        if conf and conf > DIRECT_RESPONSE_CONFIDENCE:
            return conf, data
        elif conf and conf > MATCH_CONFIDENCE:
            results.append((conf, data))

        return best_result(results)

    def query_artist(self, artist, bonus=0.0):
        """Try to find an artist.

        Arguments:
            artist (str): Artist to search for
            bonus (float): Any bonus to apply to the confidence

        Returns: Tuple with confidence and data or NOTHING_FOUND
        """
        bonus += 0.1
        data = self.offline_player.search(artist, type='artist')
        if data and data['artists']['items']:
            best = data['artists']['items'][0]['name']
            confidence = fuzzy_match(best, artist.lower()) + bonus
            confidence = min(confidence, 1.0)
            return (confidence,
                    {
                        'data': data,
                        'name': None,
                        'type': 'artist'
                    })
        else:
            return NOTHING_FOUND

    def query_album(self, album, bonus):
        """Try to find an album.

        Searches Offline Player by album and artist if available.

        Arguments:
            album (str): Album to search for
            bonus (float): Any bonus to apply to the confidence

        Returns: Tuple with confidence and data or NOTHING_FOUND
        """
        data = None
        by_word = ' {} '.format(self.translate('by'))
        if len(album.split(by_word)) > 1:
            album, artist = album.split(by_word)
            album_search = '*{}* artist:{}'.format(album, artist)
            bonus += 0.1
        else:
            album_search = album
        data = self.offline_player.search(album_search, type='album')
        if data and data['albums']['items']:
            best = data['albums']['items'][0]['name'].lower()
            confidence = best_confidence(best, album)
            # Also check with parentheses removed for example
            # "'Hello Nasty ( Deluxe Version/Remastered 2009" as "Hello Nasty")
            confidence = min(confidence + bonus, 1.0)
            self.log.info((album, best, confidence))
            return (confidence,
                    {
                        'data': data,
                        'name': None,
                        'type': 'album'
                    })
        return NOTHING_FOUND

    def query_playlist(self, playlist):
        """Try to find a playlist.

        First searches the users playlists, then tries to find a public
        one.

        Arguments:
            playlist (str): Playlist to search for

        Returns: Tuple with confidence and data or NOTHING_FOUND
        """
        result, conf = self.get_best_user_playlist(playlist)
        if playlist and conf > 0.5:
            dir = self.playlists[result]
            return (conf, {'data': dir,
                           'name': playlist,
                           'type': 'playlist'})
        else:
            return self.get_best_public_playlist(playlist)

    def query_song(self, song, bonus):
        """Try to find a song.

        Searches Spotify for song and artist if provided.

        Arguments:
            song (str): Song to search for
            bonus (float): Any bonus to apply to the confidence

        Returns: Tuple with confidence and data or NOTHING_FOUND
        """
        data = None
        by_word = ' {} '.format(self.translate('by'))
        if len(song.split(by_word)) > 1:
            song, artist = song.split(by_word)
            song_search = '*{}* artist:{}'.format(song, artist)
        else:
            song_search = song

        data = self.offline_player.search(song_search, type='track')
        if data and len(data['tracks']['items']) > 0:
            tracks = [(best_confidence(d['name'], song), d)
                      for d in data['tracks']['items']]
            tracks.sort(key=lambda x: x[0])
            tracks.reverse()  # Place best matches first
            # Find pretty similar tracks to the best match
            tracks = [t for t in tracks if t[0] > tracks[0][0] - 0.1]
            # Sort remaining tracks by popularity
            tracks.sort(key=lambda x: x[1]['popularity'])
            self.log.debug([(t[0], t[1]['name'], t[1]['artists'][0]['name'])
                            for t in tracks])
            data['tracks']['items'] = [tracks[-1][1]]
            return (tracks[-1][0] + bonus,
                    {'data': data, 'name': None, 'type': 'track'})
        else:
            return NOTHING_FOUND

    def CPS_start(self, phrase, data):
        """Handler for common play framework start playback request."""
        try:
            # Wait for librespot to start
            if self.music_player_starting:
                self.log.info('Restarting offline player...')
                for i in range(10):
                    time.sleep(0.5)
                    if not self.music_player_starting:
                        break
                else:
                    self.log.error('OFFLINE PLAYER NOT STARTED')

            #dev = self.get_default_device()
            #Sorry joe. Can't do that. Just one device here

            if data['type'] == 'continue':
                self.acknowledge()
                self.continue_current_playlist()
            elif data['type'] == 'playlist':
                self.start_playlist_playback( data['name'],
                                             data['data'])
            else:  # artist, album track
                self.log.info('playing {}'.format(data['type']))
                self.play(data=data['data'], data_type=data['type'])
            self.enable_playing_intents()
            if data.get('type') and data['type'] != 'continue':
                self.last_played_type = data['type']
            self.is_playing = True

        except PlaylistNotFoundError:
            self.speak_dialog('PlaybackFailed',
                              {'reason': self.translate('PlaylistNotFound')})
        except Exception as e:
            self.log.exception(str(e))
            self.speak_dialog('PlaybackFailed', {'reason': str(e)})

    def create_intents(self):
        """Setup the spotify intents."""
        intent = IntentBuilder('').require('OfflinePlayer').require('Search') \ #Said .require('Spotify')
                                  .require('For')
        self.register_intent(intent, self.search_spotify)
        self.register_intent_file('ShuffleOn.intent', self.shuffle_on)
        self.register_intent_file('ShuffleOff.intent', self.shuffle_off)
        self.register_intent_file('WhatSong.intent', self.song_info)
        self.register_intent_file('WhatAlbum.intent', self.album_info)
        self.register_intent_file('WhatArtist.intent', self.artist_info)
        self.register_intent_file('StopMusic.intent', self.handle_stop)
        time.sleep(0.5)
        self.disable_playing_intents()

    def enable_playing_intents(self):
        self.enable_intent('WhatSong.intent')
        self.enable_intent('WhatAlbum.intent')
        self.enable_intent('WhatArtist.intent')
        self.enable_intent('StopMusic.intent')

    def disable_playing_intents(self):
        self.disable_intent('WhatSong.intent')
        self.disable_intent('WhatAlbum.intent')
        self.disable_intent('WhatArtist.intent')
        self.disable_intent('StopMusic.intent')

    @property
    def playlists(self):
        """Playlists, cached for 5 minutes."""
        if not self.offline_player: #Come back and see if this line is necessary
            return []  # No connection, no playlists
        now = time.time()
        if not self._playlists or (now - self.__playlists_fetched > 5 * 60):
            self._playlists = {}
            playlists = self.offline_player.current_user_playlists().get('items', [])
            for p in playlists:
                self._playlists[p['name'].lower()] = p
            self.__playlists_fetched = now
        return self._playlists

    def refresh_saved_tracks(self):
        """Saved tracks are cached for 4 hours."""
        if not self.offline_player: #Come back and see if this line is necessary
            return []
        now = time.time()
        """
        if not self.saved_tracks or (now - self.__saved_tracks_fetched > 4 * 60 * 60):
            saved_tracks = []
            offset = 0
            while True:
                batch = self.offline_player.current_user_saved_tracks(50, offset)
                for item in batch.get('items', []):
                    saved_tracks.append(item['track'])
                offset += 50
                if not batch['next']:
                    break

            self.saved_tracks = saved_tracks
            self.__saved_tracks_fetched = now
        """

    #Not needed
    """
    @property
    def devices(self):
        #Devices, cached for 60 seconds.""
        if not self.offline_player:
            return []  # No connection, no devices
        now = time.time()
        if not self.__device_list or (now - self.__devices_fetched > 60):
            self.__device_list = self.offline_player.get_devices()
            self.__devices_fetched = now
        return self.__device_list

    def device_by_name(self, name):
        "Get a Spotify devices from the API.

        Arguments:
            name (str): The device name (fuzzy matches)
        Returns:
            (dict) None or the matching device's description
        "
        devices = self.devices
        if devices and len(devices) > 0:
            # Otherwise get a device with the selected name
            devices_by_name = {d['name']: d for d in devices}
            key, confidence = match_one(name, list(devices_by_name.keys()))
            if confidence > 0.5:
                return devices_by_name[key]
        return None

    #not needed
    def get_default_device(self):
        ""Get preferred playback device. But don't really.
        if self.offline_player:
            # When there is an active Spotify device somewhere, use it
            if (self.devices and len(self.devices) > 0 and
                    self.offline_player.is_playing()):
                for dev in self.devices:
                    if dev['is_active']:
                        self.log.info('Playing on an active device '
                                      '[{}]'.format(dev['name']))
                        return dev  # Use this device

            # No playing device found, use the default Spotify device
            default_device = self.settings.get('default_device', '')
            dev = None
            device_type = DeviceType.NOTFOUND
            if default_device:
                dev = self.device_by_name(default_device)
                device_type = DeviceType.DEFAULT
            # if not set or missing try playing on this device
            if not dev:
                dev = self.device_by_name(self.device_name)
                device_type = DeviceType.MYCROFT
            # if not check if a desktop spotify client is playing
            if not dev:
                dev = self.device_by_name(gethostname())
                device_type = DeviceType.DESKTOP

            # use first best device if none of the prioritized works
            if not dev and len(self.devices) > 0:
                dev = self.devices[0]
                device_type = DeviceType.FIRSTBEST

            if dev and not dev['is_active']:
                self.offline_player.transfer_playback(dev['id'], False)
            self.log.info('Device detected: {}'.format(device_type))
            return dev

        return None
        """

    def get_best_user_playlist(self, playlist):
        """Get best playlist matching the provided name

        Arguments:
            playlist (str): Playlist name

        Returns: ((str)best match, (float)confidence)
        """
        playlists = list(self.playlists.keys())
        if len(playlists) > 0:
            # Only check if the user has playlists
            key, confidence = match_one(playlist.lower(), playlists)
            if confidence > 0.7:
                return key, confidence
        return NOTHING_FOUND

    def get_best_public_playlist(self, playlist):
        data = self.offline_player.search(playlist, type='playlist')
        if data and data['playlists']['items']:
            best = data['playlists']['items'][0]
            confidence = fuzzy_match(best['name'].lower(), playlist)
            if confidence > 0.7:
                return (confidence, {'data': best,
                                     'name': best['name'],
                                     'type': 'playlist'})
        return NOTHING_FOUND

    def continue_current_playlist(self, dev):
        """Send the play command to the selected device."""
        time.sleep(2)
        self.offline_player_play() #Not multiple devices to choose from dev['id'])

    def playback_prerequisits_ok(self):
        """Check that playback is possible, launch client if neccessary."""
        if self.offline_player is None:
            return False

        #not needed
        """
        devs = [d['name'] for d in self.devices]
        if self.process and self.device_name not in devs:
            self.log.info('Librespot not responding, restarting...')
            self.stop_librespot()
            self.__devices_fetched = 0  # Make sure devices are fetched again
        """
        if not self.process:
            self.schedule_event(self.launch_player, 0,
                                name='launch_player')
        return True

    #come back
    def offline_player_play(self, files=None, context_dir=None): #dev_id, dirs=None, context_dir=None):
        """Start playback and log any exceptions."""
        try:
            self.log.info(u'Offline_play')
            if files != None:
                self.audio_service.play(files)#dev_id, dirs, context_dir)
            else:
                self.audio_service.resume()
            self.start_monitor()
        except Exception as e:
            self.log.exception(e)
            raise

    def start_playlist_playback(self, dev, name, dir):
        name = name.replace('|', ':')
        if dir:
            self.log.info(u'playing {}'.format(name))
            self.speak_dialog('ListeningToPlaylist',
                              data={'playlist': name})
            time.sleep(2)
            self.offline_player_play(context_dir=dir['dir'])
        else:
            self.log.info('No playlist found')
            raise PlaylistNotFoundError

    def play(self, data, data_type='track', genre_name=None):#dev, data, data_type='track', genre_name=None):
        """
        Plays the provided data in the manner appropriate for 'data_type'
        If the type is 'genre' then genre_name should be specified to populate
        the output dialog.

        A 'track' is played as just an individual track.
        An 'album' queues up all the tracks contained in that album and starts
        with the first track.
        A 'genre' expects data returned from self.offline_player.search, and will use
        that genre to play a selection similar to it.

        Args:
            data (dict):        Data returned by self.spotify.search (but now self.offline_player.search)
            data_type (str):    The type of data contained in the passed-in
                                object. 'saved_tracks', 'track', 'album',
                                or 'genre' are currently supported.
            genre_name (str):   If type is 'genre', also include the genre's
                                name here, for output purposes. default None
        """
        try:
            if data_type == 'saved_tracks':
                # Grab 200 random songs
                # Spotify doesn't like it when we send thousands of songs
                items = random.sample(self.saved_tracks, 200)
                files = []
                for item in items:
                    files.append(item['dir'])
                self.speak_dialog('ListeningToSavedSongs')
                time.sleep(2)
                self.offline_player_play(files=files)
            elif data_type == 'track':
                (song, artists, dir) = get_song_info(data)
                self.speak_dialog('ListeningToSongBy',
                                  data={'tracks': song,
                                        'artist': artists[0]})
                time.sleep(2)
                self.offline_player_play(files=[dir])
            elif data_type == 'artist':
                (artist, dir) = get_artist_info(data)
                self.speak_dialog('ListeningToArtist',
                                  data={'artist': artist})
                time.sleep(2)
                self.offline_player_play(context_dir=dir)
            elif data_type == 'album':
                (album, artists, dir) = get_album_info(data)
                self.speak_dialog('ListeningToAlbumBy',
                                  data={'album': album,
                                        'artist': artists[0]})
                time.sleep(2)
                self.offline_player_play(context_dir=dir)
            elif data_type == 'genre':
                items = data['tracks']['items']
                random.shuffle(items)
                files = []
                for item in items:
                    files.append(item['dir'])
                data = {'genre': genre_name, 'track': items[0]['name'],
                        'artist': items[0]['artists'][0]['name']}
                self.speak_dialog('ListeningToGenre', data)
                time.sleep(2)
                self.offline_player_play(files=files)
            else:
                self.log.error('wrong data_type')
                raise ValueError("Invalid type")
        except Exception as e:
            self.log.error("Unable to obtain the name, artist, "
                           "and/or dir information while asked to play "
                           "something. " + str(e))
            raise

    def search(self, query, search_type):
        """ Search for an album, playlist or artist.
        Arguments:
            query:       search query (album title, artist, etc.)
            search_type: whether to search for an 'album', 'artist',
                         'playlist', 'track', or 'genre'

            TODO: improve results of albums by checking artist
        """
        res = None
        if search_type == 'album' and len(query.split('by')) > 1:
            title, artist = query.split('by')
            result = self.offline_player.search(title, type=search_type)
        else:
            result = self.offline_player.search(query, type=search_type)

        if search_type == 'album':
            if len(result['albums']['items']) > 0:
                album = result['albums']['items'][0]
                self.log.info(album)
                res = album
        elif search_type == 'artist':
            self.log.info(result['artists'])
            if len(result['artists']['items']) > 0:
                artist = result['artists']['items'][0]
                self.log.info(artist)
                res = artist
        elif search_type == 'genre':
            self.log.debug("TODO! Genre")
        else:
            self.log.error('Search type {} not supported'.format(search_type))
            return

        return res

    def search_spotify(self, message):
        """ Intent handler for "search spotify for X". """

        try:
            utterance = message.data['utterance']
            if len(utterance.split(self.translate('ForAlbum'))) == 2:
                query = utterance.split(self.translate('ForAlbum'))[1].strip()
                data = self.offline_player.search(query, type='album')
                self.play(data=data, data_type='album')
            elif len(utterance.split(self.translate('ForArtist'))) == 2:
                query = utterance.split(self.translate('ForArtist'))[1].strip()
                data = self.offline_player.search(query, type='artist')
                self.play(data=data, data_type='artist')
            else:
                for_word = ' ' + self.translate('For')
                query = for_word.join(utterance.split(for_word)[1:]).strip()
                data = self.offline_player.search(query, type='track')
                self.play(data=data, data_type='track')
        except PlaylistNotFoundError:
            self.speak_dialog(
                'PlaybackFailed',
                {'reason': self.translate('PlaylistNotFound')})
        except Exception as e:
            self.speak_dialog('PlaybackFailed', {'reason': str(e)})

    def shuffle_on(self):
        """ Turn on shuffling """
        if self.offline_player:
            self.offline_player.shuffle(True)
        else:
            self.failed_auth()

    def shuffle_off(self):
        """ Turn off shuffling """
        if self.offline_player:
            self.offline_player.shuffle(False)
        else:
            self.failed_auth()

    #Come back to these. AudioService may have a way to return status.
    def song_info(self, message):
        """ Speak song info. """
        status = self.offline_player.status() if self.offline_player else None
        song, artist, _ = status_info(status)
        self.speak_dialog('CurrentSong', {'song': song, 'artist': artist})

    def album_info(self, message):
        """ Speak album info. """
        status = self.offline_player.status() if self.offline_player else None
        _, _, album = status_info(status)
        if self.last_played_type == 'album':
            self.speak_dialog('CurrentAlbum', {'album': album})
        else:
            self.speak_dialog('OnAlbum', {'album': album})

    def artist_info(self, message):
        """ Speak artist info. """
        status = self.offline_player.status() if self.offline_player else None
        if status:
            _, artist, _ = status_info(status)
            self.speak_dialog('CurrentArtist', {'artist': artist})

    def __pause(self):
        # if authorized and playback was started by the skill
        if self.audio_service:
            self.log.info('Pausing Music Player...')
            self.audio_service.pause()

    def pause(self, message=None):
        """ Handler for playback control pause. """
        self.ducking = False
        self.__pause()

    def resume(self, message=None):
        """ Handler for playback control resume. """
        # if authorized and playback was started by the skill
        if self.audio_service:
            self.log.info('Resume Music Player')
            self.audio_service.resume()

    def next_track(self, message):
        """ Handler for playback control next. """
        # if authorized and playback was started by the skill
        if self.audio_service:
            self.log.info('Next track')
            self.audio_service.next()
            self.start_monitor()
            return True
        return False

    def prev_track(self, message):
        """ Handler for playback control prev. """
        # if authorized and playback was started by the skill
        if self.audio_service:
            self.log.info('Previous Spotify track')
            self.audio_service.prev()
            self.start_monitor()

    def handle_stop(self, message):
        self.bus.emit(Message('mycroft.stop'))

    def do_stop(self):
        try:
            self.pause(None)
        except Exception as e:
            self.log.error('Pause failed: {}'.format(repr(e)))
            dev = self.get_default_device()
            if dev:
                self.log.info('Retrying')
                self.pause(None)
        return True

    def stop(self):
        """ Stop playback. """
        if self.audio_service and self.is_playing:
            self.schedule_event(self.do_stop, 0, name='StopOfflinePlayer')
            return True
        else:
            return False

    def shutdown(self):
        """ Remove the monitor at shutdown. """
        self.stop_monitor()

        # Do normal shutdown procedure
        super(PlayLocallySkill, self).shutdown()


def create_skill():
    return PlayLocallySkill()

# WORKING COMMANDS:
# play spotify
# search spotify for the album nighthawks at the diner
# list spotify devices
# skip track
# next track
# pause
# resume
# pause music
# resume music
#
# FAILING COMMANDS:
# play tom waits on spotify
# search spotify for nighthawks at the diner
