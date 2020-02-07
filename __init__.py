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

# First program by AdamAmott
# A fork of the Mycroft Spotify skill

import time
from os.path import abspath, dirname, join
from .song_database_manager import SongDatabase

import re
from mycroft.skills.core import intent_handler
from mycroft.util.parse import match_one, fuzzy_match
from mycroft.messagebus import Message
from adapt.intent import IntentBuilder

#extras
import sys
import os
import psutil
from traceback import print_exc


import random

from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.skills.audioservice import AudioService

from enum import Enum

class PlaylistNotFoundError(Exception):
    pass


# Return value definition indication nothing was found
# (confidence None, data None)
NOTHING_FOUND = (None, 0.0)

# Confidence levels for generic play handling
DIRECT_RESPONSE_CONFIDENCE = 0.8

MATCH_CONFIDENCE = 0.5


def best_result(results):
    """Return best result from a list of result tuples.
    Arguments:
        results (list): list of music result tuples
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
        title: title name from music search
        query: query from user
    Returns:
        (float) best condidence
    """
    best = title.lower()
    best_stripped = re.sub(r'(\(.+\)|-.+)$', '', best).strip()
    return max(fuzzy_match(best, query),
               fuzzy_match(best_stripped, query))

def status_info():
    """Return track, artist, album tuple from spotify status.

    Arguments:
        status (dict): Spotify status info

    Returns:
        tuple (track, artist, album)
     """
    return "I don't think this should be here"


class PlayLocallySkill(CommonPlaySkill):
    """But now we're making it play locally with Amarok or something"""

    def __init__(self):
        super(PlayLocallySkill, self).__init__()
        self.song_database = SongDatabase()
        self.idle_count = 0
        self.ducking = False
        self.mouth_text = None

        enclosure_config = self.config_core.get('enclosure')
        self.platform = enclosure_config.get('platform', 'unknown')
        self.DEFAULT_VOLUME = 80 if self.platform == 'mycroft_mark_1' else 100
        self._playlists = self.song_database.playlists
        self.regexes = {}
        self.last_played_type = None  # The last dir type that was started
        self.is_playing = False
        self.use_ducking = self.settings.get('use_ducking', False) #check that this line works

        self.repeat = False #TODO: Make this changeable
        self.shuffle = False #TODO: implement shuffle
        self.queue = {} # involved in shuffle

        


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

    def initialize(self):
        super().initialize()

        # Setup handlers for playback control messages
        self.add_event('mycroft.audio.service.next', self.next_track)
        self.add_event('mycroft.audio.service.prev', self.prev_track)
        self.add_event('mycroft.audio.service.pause', self.pause)
        self.add_event('mycroft.audio.service.resume', self.resume)
        
        # Set up music service stuff
        self.audio_service = AudioService(self.bus)
        self.song_database.load_database()
        self.preferred_service = 'vlc' # TODO-- Hopefully we can figure out how to implement this. more music file types



        #info for use later. Will be removed later on
        self.log.info("#####################backends:"+ str(self.audio_service.available_backends()))


    ######################################################################
    # Handle auto ducking when listener is started.

    def handle_listener_started(self, message):
        """Handle auto ducking when listener is started.

        The ducking is enabled/disabled using the skill settings on home.
        """
        if self.is_playing and self.use_ducking:
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
        status = self.status()

        if not status:
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

    def status(self):
        if self.audio_service:
            return self.audio_service.track_info()
        else:
            return None


    def CPS_send_status(self, artist='', track='', album='', image=''):
        data = {'skill': self.name,
                'artist': artist,
                'track': track,
                'album': album,
                'image': image,
                'status': None
                }
        self.bus.emit(Message('play:status', data))

    def CPS_match_query_phrase(self, phrase):
        """Handler for common play framework Query."""

        offline_specified = 'offline' in phrase or 'locally' in phrase
        bonus = 0.1 if offline_specified else 0.0
        phrase = re.sub(self.translate_regex('offline'), '', phrase)

        #search for the song. Check to see if locally or offline mentioned,
        # search specific phrase, then search generically
        confidence, data = self.continue_playback(phrase, bonus) #'play offline'
        if not data:
            confidence, data = self.specific_query(phrase, bonus) #'play x'
            if not data:
                confidence, data = self.generic_query(phrase, bonus) #'play y'

        if data:
            self.log.info('Offline Player confidence: {}'.format(confidence))
            self.log.info('              data: {}'.format(data))


            if data.get('type') in ['saved_tracks', 'album', 'artist', 'track', 'playlist']:
            #a query matched with enough confidence
                if offline_specified:
                    # " play great song offline/locally'
                    level = CPSMatchLevel.EXACT
                else:
                    if confidence > 0.9:
                        level = CPSMatchLevel.MULTI_KEY
                    elif confidence < 0.5:
                        level = CPSMatchLevel.GENERIC
                    else:
                        level = CPSMatchLevel.TITLE
                    phrase += ' locally'
            elif data.get('type') == 'continue':
            # Just keep playing whatever we played last
                if offline_specified:
                    # "resume playback offline"
                    level = CPSMatchLevel.EXACT
                else:
                    # "resume playback"
                    level = CPSMatchLevel.GENERIC
                    phrase += ' offline' #put 'offline' back since we cut it off for processing
            else: #Just roll with it and play something random if no matches and CPS returns to us
                self.log.warning('Unexpected Offline Player type: '
                                 '{}'.format(data.get('type')))
                level = CPSMatchLevel.GENERIC

            #DEBUGGING
            self.log.info("Phrase: " + str(phrase) + "-- Level:" + str(level) + "-- Data: " + str(data))
            return phrase, level, data

        else:
            #none of the queries had a high enough confidence match
            self.log.debug('Couldn\'t find anything to play')

    def continue_playback(self, phrase, bonus):
        #user says, "Play offline"
        phrase = phrase.strip()
        if phrase == 'offline' or phrase == 'locally' or phrase == "offline music" or phrase == "local music":
            return (1.0,
                    {
                        'data': None,
                        'name': None,
                        'type': 'continue'
                    })
        else:
            return NOTHING_FOUND

    #Implement search feature here for songs
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
         #gets "saved songs" from the phrase if it is there.
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
            if match:
                bonus += 0.1

        # Check artist
        match = re.match(self.translate_regex('artist'), phrase)
        if match:
            artist = match.groupdict()['artist']
            return self.query_artist(artist, bonus)

        # Check track
        match = re.match(self.translate_regex('song'), phrase)
        if match:
            song = match.groupdict()['track']
            return self.query_song(song, bonus)
        return NOTHING_FOUND

    def generic_query(self, phrase, bonus = 0.0):
        """Check for a generic query, not asking for any special feature.
        Fall back to this when none of the regexes in generic query could help

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

        # Check for playlist
        self.log.info('Checking users playlists')
        playlist, conf = self.song_database.search_playlists(phrase)
        if playlist:
            dir = self.song_database.playlists[playlist]
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

        return best_result(results)

    def query_artist(self, artist, bonus=0.0):
        """Try to find an artist.

        Arguments:
            artist (str): Artist to search for
            bonus (float): Any bonus to apply to the confidence

        Returns: Tuple with confidence and data or NOTHING_FOUND
        """
        data, confidence = self.song_database.search_artists(artist.lower())

        if data:
            confidence = min(confidence, 1.0)
            return (confidence,
                    {
                        'data': data,
                        'name': None,
                        'type': 'artist'
                    })
        else:
            return NOTHING_FOUND

    def query_album(self, album, bonus=0.0):
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
            album_search = album
            artist_search = artist
        else:
            album_search = album
            artist_search = "any_artist"

        data, confidence = self.song_database.search_albums(album_search, artist_search)
        
        if data:
            first_song_info = self.song_database.get_song_info(data)
            if first_song_info:
                album_title = first_song_info['album']
            else:
                album_title = 'no title'

            better_confidence = best_confidence(album_title, album_search)
            # ^ see if confidence improves when parentheses removed
            # "'Hello Nasty ( Deluxe Version/Remastered 2009" as "Hello Nasty")
            if better_confidence > confidence:
                confidence = better_confidence
            confidence = min(confidence + bonus, 1.0)
            self.log.info(("Album:", data, "\nConfidence: ", confidence))

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
        result, conf = self.song_database.search_playlists(playlist)
        if result and conf > 0.5:
            dir = self.song_database.playlists[result]
            return (conf, {'data': dir,
                           'name': playlist,
                           'type': 'playlist'})

    def query_song(self, song, bonus):
        """Try to find a song.

        Searches for song and artist if provided.

        Arguments:
            song (str): Song to search for
            bonus (float): Any bonus to apply to the confidence

        Returns: Tuple with confidence and data or NOTHING_FOUND
        """
        data = None
        by_word = ' {} '.format(self.translate('by'))
        if len(song.split(by_word)) > 1:
            song, artist = song.split(by_word)
            song_search = song
            artist_search = artist
        else:
            song_search = song
            artist_search = "any_artist"

        data, confidence = self.song_database.search_tracks(song_search, artist_search)
        if data: # and len(data['tracks']) > 0:
            self.log.debug("Matched {} with {}% confidence.".format(data, confidence * 100))
            return (confidence,
                    {'data': data, 'name': None, 'type': 'track'})
        else:
            return NOTHING_FOUND

    def CPS_start(self, phrase, data):
        """Handler for common play framework start playback request."""
        try:
            if data['type'] == 'continue':
                self.acknowledge()
                self.resume()
            elif data['type'] == 'playlist':
                self.start_playlist_playback(data['name'],
                                             data['data'])
            else:  # artist, album track
                self.log.info('playing {}'.format(data['type']))
                song_data = data['data']
                data_type = data['type']
                self.play(song_data, data_type)
            self.enable_playing_intents()
            if data.get('type') and data['type'] != 'continue':
                self.last_played_type = data['type']
            self.is_playing = True

        except PlaylistNotFoundError:
            self.speak_dialog('PlaybackFailed',
                              {'reason': self.translate('PlaylistNotFound')})
        # DEBUGGING """
        #try:
        #    self.audio_service.play(self.song_database.get_random_song(), self.preferred_service, self.repeat)
        except Exception as e:
            self.log.exception(str(e))
            self.speak_dialog('PlaybackFailed', {'reason': str(e)})

    def create_intents(self):
        """Setup the spotify intents."""
        intent = IntentBuilder('').require('OfflinePlayer').require('Search').require('For')
        self.register_intent(intent, self.search_music)
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
        return self.song_database.playlists

    #come back
    def offline_player_play(self, files=None):
        """Start playback and log any exceptions."""
        try:
            self.log.info(u'Offline_play')
            if files != None:
                self.audio_service.play(files, self.preferred_service, self.repeat)
            """else:
                self.resume()"""
            self.start_monitor()

        except Exception as e:
            self.log.exception(e)
            raise

    def start_playlist_playback(self, name, dir):
        name = name.replace('|', ':')
        if dir:
            self.log.info(u'playing {}'.format(name))
            self.speak_dialog('ListeningToPlaylist',
                              data={'playlist': name})
            time.sleep(2)
            self.offline_player_play(dir)
        else:
            self.log.info('No playlist found')
            raise PlaylistNotFoundError

    def play(self, song_list, data_type='track', genre_name=None):
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
            song_list (list):        Data returned by self.song_database.search. 
                                A list of song files
            data_type (str):    The type of data contained in the passed-in
                                object. 'saved_tracks', 'track', 'album',
                                or 'genre' are currently supported.
            genre_name (str):   If type is 'genre', also include the genre's
                                name here, for output purposes. default None
        """
        try:
            if data_type == 'saved_tracks':
                items = self.song_database.saved_tracks
                self.speak_dialog('ListeningToSavedSongs')
                time.sleep(2)
                self.offline_player_play(items)

            elif data_type == 'track':
                song_info = self.song_database.get_song_info(song_list)
                if song_info:
                    song = song_info['title']
                    artist = song_info['artist']
                    dir = song_info['dir']

                else: #If no specific choice, play something random
                    song = "random"
                    artist = "random"
                    dir = self.song_database.get_random_song_list()
                self.speak_dialog('ListeningToSongBy',
                                  data={'tracks': song,
                                        'artist': artist})
                time.sleep(2)
                self.offline_player_play(song_list)

            elif data_type == 'artist':
                (artist, song_list) = self.song_database.get_artist_info(song_list)
                self.speak_dialog('ListeningToArtist',
                                  data={'artist': artist})
                time.sleep(2)
                self.offline_player_play(song_list)

            elif data_type == 'album':
                #pass the first song
                song_info = self.song_database.get_song_info(song_list[0])
                self.speak_dialog('ListeningToAlbumBy',
                                  data={'album': song_info.get('album'),
                                        'artist': song_info.get('artist')})
                time.sleep(2)
                self.offline_player_play(song_list)

            elif data_type == 'genre':
                genre_name = self.song_database.get_genre_name(song_list)
                self.log.info("Shuffling songs in ", genre_name)
                random.shuffle(song_list)
                self.speak_dialog('ListeningToGenre', genre_name)
                time.sleep(2)
                self.offline_player_play(song_list)

            else:
                self.log.error('wrong data_type')
                raise ValueError("Invalid type")
        except Exception as e:
            self.log.error("Unable to obtain the name, artist, "
                           "and/or dir information while asked to play "
                           "something. " + str(e))
            raise

    #not needed
    def search(self, query, search_type):
        """ Search for an album, playlist or artist.
        Arguments:
            query:       search query (album title, artist, etc.)
            search_type: whether to search for an 'album', 'artist',
                         'playlist', 'track', or 'genre'
        """
        res = None
        if search_type == 'album' and len(query.split('by')) > 1:
            title, artist = query.split('by')
            result = self.song_database.search(title, type=search_type)
        else:
            result = self.song_database.search(query, type=search_type)

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
    #not needed
    def search_music(self, message):
        """ Intent handler for "search spotify for X". """

        try:
            utterance = message.data['utterance']
            if len(utterance.split(self.translate('ForAlbum'))) == 2:
                query = utterance.split(self.translate('ForAlbum'))[1].strip()
                data = self.song_database.search(query, type='album')
                self.play(data=data, data_type='album')
            elif len(utterance.split(self.translate('ForArtist'))) == 2:
                query = utterance.split(self.translate('ForArtist'))[1].strip()
                data = self.song_database.search(query, type='artist')
                self.play(data=data, data_type='artist')
            elif len(utterance.split(self.translate('ForGenre'))) == 2:
                query = utterance.split(self.translate('ForGenre'))[1].strip()
                data = self.song_database.search(query, type='genre')
                self.play(data=data, data_type='genre')
            else:
                for_word = ' ' + self.translate('For')
                query = for_word.join(utterance.split(for_word)[1:]).strip()
                data = self.song_database.search(query, type='track')
                self.play(data=data, data_type='track')
        except PlaylistNotFoundError:
            self.speak_dialog(
                'PlaybackFailed',
                {'reason': self.translate('PlaylistNotFound')})
        except Exception as e:
            self.speak_dialog('PlaybackFailed', {'reason': str(e)})

    def shuffle_on(self):
        """ Turn on shuffling """
        self.shuffle = True
        if self.queue > 1:
            random.shuffle(self.queue)

    def shuffle_off(self):
        """ Turn off shuffling """
        self.shuffle = False

    def song_info(self, message):
        """ Speak song info. """
        status = self.audio_service.track_info()
        self.speak_dialog('CurrentSong', {'song': status['title'], 'artist': status['artist']})

    def album_info(self, message):
        """ Speak album info. """
        status = self.audio_service.track_info()
        if self.last_played_type == 'album':
            self.speak_dialog('CurrentAlbum', {'album': status['album']})
        else:
            self.speak_dialog('OnAlbum', {'album': status['album']})

    def artist_info(self, message):
        """ Speak artist info. """
        status = self.audio_service.track_info()
        self.speak_dialog('CurrentArtist', {'artist': status['artist']})

    def __pause(self):
        # if playback was started by the skill
        if self.audio_service:
            self.log.info('Pausing Music Player...')

    def pause(self, message=None):
        """ Handler for playback control pause. """
        self.ducking = False
        self.__pause()

    def resume(self, message=None):
        """ Handler for playback control resume. """
        # if playback was started by the skill
        if self.audio_service:
            self.log.info('Resuming Music Player')

    def next_track(self, message):
        """ Handler for playback control next. """
        # if playback was started by the skill
        if self.audio_service:
            self.log.info('Next track')
            self.start_monitor()
            return True
            
        else:
            return False

    def prev_track(self, message):
        """ Handler for playback control prev. """
        # if playback was started by the skill
        if self.audio_service:
            self.log.info('Previous track')
            self.start_monitor()
            return True
        else:
            return False

    def handle_stop(self, message):
        self.bus.emit(Message('mycroft.stop'))

    def do_stop(self):
        try:
            self.pause(None)
            audio_service = None
        except Exception as e:
            self.log.error('Pause failed: {}'.format(repr(e)))
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
# play locally
# search locally for the album nighthawks at the diner
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
