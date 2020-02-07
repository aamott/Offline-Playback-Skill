from mycroft.util.parse import match_one, fuzzy_match
from pathlib import Path
import os.path
from tinytag import TinyTag
import random

class SongDatabase:
    def __init__(self, music_directory = str(Path.home()) + "/Music"):
        self.playlists = {}
        self.artists = {}
        self.albums = {}
        self.tracks = {}
        self.genres = {}
        self.previous_tracks = {}
        self.saved_tracks = {} #TODO - make a way to load and save saved tracks

    def get_random_song(self):
    #returns a single random song directory as a string
        return random.choice(list(self.tracks.values()))

    def get_random_song_list(self):
    #returns a list of random song file directories
        num_songs = len(self.tracks.values())
        if num_songs > 400:
            return random.sample(list(self.tracks.values()), 400)
        return random.sample(list(self.tracks.values()), num_songs)


    def get_artists(self, song_files):
    #receives a list of song files
    #returns a list of artists who wrote songs
        artists = []
        for song in song_files:
            tag = TinyTag(song)
            artists.append(tag.artist)
        return artists

    def get_playlists(self):
        return self.playlists

    def get_song_info(self, song=None):
        """returns the name of the artist of a known song
        input: song title
        return: dict of song info
        """
        data_type = type(song)
        if data_type is list or data_type is tuple: #If it is a list of songs, get the info from the first song
            return self.get_song_info(song[0])
        if data_type is dict:
            return self.get_song_info(song.values()[0])
        else:
            if song in self.tracks:
                track_dir = self.tracks[song]
                tag = TinyTag.get(track_dir)
                info = {
                'title': tag.title,
                'artist': tag.artist,
                'album': tag.album,
                'album artist': tag.albumartist,
                'genre': tag.genre,
                'year': tag.year,
                'dir': self.tracks[song]
                }
                return info
            else:
                #try: #try to open it as a filepath
                tag = TinyTag.get(song)
                info = {
                'title': tag.title,
                'artist': tag.artist,
                'album': tag.album,
                'album artist': tag.albumartist,
                'genre': tag.genre,
                'year': tag.year,
                'dir': song
                }
                return info
                """except:
                    info = {
                    'title': 'unknown',
                    'artist': 'unknown',
                    'album': 'unknown',
                    'album artist': 'unknown',
                    'genre': 'unknown',
                    'year': 'unknown',
                    'dir': 'unknown'
                    }
                    return info"""

    def get_artist_info(self, artist):
        #returns a tuple with artist name and
        #list of all the songs written by an artist
        return artist, self.artists[artist]

    def get_album_info(self, song_list):
        #takes a list of song files (presumably an album)
        if song_list is list:
            song_tags = TinyTag.get(song_list[0])
            album = song_tags.album
            artist = song_tags.albumartist

        return album, artists, album

    def get_genre_name(self, song_list):
        if genre is list:
            song_tags = TinyTag.get(song_list[0])
            genre_names = song_tags.genre

        return genre_name

    def search(self, query, type):
        if type == 'album':
            return search_albums(query)
        elif type == 'artist':
            return search_artists(query)
        elif type == 'genre':
            return search_genres(query)
        elif type == 'track':
            return search_tracks(query)

    def search_genres(self, query):
        match, confidence = match_one(query, self.genres)

        return match, confidence

    def search_playlists(self, query):
        if self.playlists:
            match, confidence = match_one(query, self.playlists)
            return match, confidence
        else:
            return None, 0.0

    def search_artists(self, query):
        match, confidence = match_one(query, self.artists)
        return match, confidence

    def search_albums(self, album_name, artist = "any_artist"):
        #fuzzy match the album name
        match, confidence = match_one(album_name, self.albums)

        #The rest of this code is for matching the artist (if available)
        if artist != "any_artist":
            confidences = []
            for song in self.albums[match]:
                tag = TinyTag.get(match)
                artist_confidence = fuzzy_match(tag.artist, artist)
                confidences.append(artist_confidence)

            #Choose the best artist from the songs and add a bonus
            max_artist_confidence = max(confidences)
            if max_artist_confidence > 0.5:
                confidence += max_artist_confidence / 2
            else:
                #search again, but this time with "by {}".format(artist)
                # Fixes problems with "by" in song name.
                # Ex. "Cake by the ocean floor"
                possible_match, possible_confidence = match_one(poss_album_name + " by " + artist, self.albums)

                if possible_confidence > confidence:
                    match = possible_match
                    confidence = possible_confidence

            if confidence > 1.0:
                confidence = 1.0

        return match, confidence

    def search_tracks(self, track_name, artist = "any_artist"):
        match, confidence = match_one(track_name, self.tracks)

        #The rest of this code is to check artists
        if artist != "any_artist":
            tag = TinyTag.get(self.tracks[match])
            artist_confidence = fuzzy_match(tag.artist, artist)
            if artist_confidence > 0.5:
                confidence += artist_confidence / 2
            else:
            #search again, but this time with "by {}".format(artist)
            # Fixes problems with "by" in song name. Ex. "Cake by the ocean floor"
                possible_match, possible_confidence = match_one(poss_album_name + " by " + artist, self.albums)
                if possible_confidence > confidence:
                    match = possible_match
                    confidence = possible_confidence

        if confidence > 1.0:
            confidence = 1.0

        return [match], confidence

    def add_to_queue(self, location):
        success = False
        return success #TODO - make it. It's empty

    def to_standard_title(self, title):
        title = title.replace('-', ' ')
        return Path(title).stem

    def load_database(self, directory= str(Path.home()) + "/Music", music_extension=(
            '.mp3', '.aac', '.cda', '.flac', '.ogg', '.opus', '.wma', '.zab'),
        playlist_extension=('.asx', '.xspf', '.b4s', '.m3u', 'm3u8')):

        for root, subfolder, files in os.walk(directory):
            for item in files:
                # check for music files
                if music_extension and item.lower().endswith(music_extension):
                    file_path = os.path.join(root, item)
                    tag = TinyTag.get(file_path)
                    #adds song name and its path to tracks Dict.
                    if tag.title:
                        self.tracks[tag.title] = file_path
                    else:
                        self.tracks[self.to_standard_title(item)] = file_path

                    #ARTIST: creates a list of tracks under each artist
                    if tag.artist in self.artists:
                        self.artists[tag.artist].append(file_path)
                    else:
                        self.artists[tag.artist] = [file_path]

                    #ALBUM: adds a list of tracks to each album
                    if tag.album in self.albums:
                        self.albums[tag.album].append(file_path)
                    else:
                        self.albums[tag.album] = [file_path]

                    #GENRE: adds a list of tracks to each genre
                    if tag.genre in self.genres:
                        self.genres[tag.genre].append(file_path)
                    else:
                        self.genres[tag.genre] = [file_path]

                # check for playlist files
                elif playlist_extension and item.lower().endswith(playlist_extension):
                    file_path = os.path.join(root, item)
                    self.playlists[self.to_standard_title(item)] = file_path

        if self.albums[None]:
            self.albums['_unknown'] = self.albums[None]
            del self.albums[None]
        if self.genres[None]:
            self.genres['_unknown'] = self.genres[None]
            del self.genres[None]        
        if self.artists[None]:
            self.artists['_unknown'] = self.artists[None]
            del self.artists[None]


        #Debugging
        #for album in self.albums:
        #    print(album)

def main():
    player = SongDatabase()
    player.load_database()
    #match, confidence = player.search_albums("Come Thou")
    #print('matches: {}\nConfidence: {}'.format(match, confidence))

if __name__ == "__main__":
    main()
