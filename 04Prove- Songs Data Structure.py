from collections import deque

class Song:
    def __init__(self):
        self.title = "unknown"
        self.artist = "unknown"

    def prompt(self):
        self.title = input("Enter a song title: ")
        if self.title == "quit":
            return False

        self.artist = input("Enter a song artist: ")
        return True

    def display(self):
        print(self.title, "by", self.artist)

def display_menu():
    print("Options:")
    print("1. Add a new song to the end of the playlist")
    print("2. Insert a new song to the beginning of the playlist")
    print("3. Play the next song")
    print("4. Quit")

def main():
    songs = deque()

    selection = 0
    while selection != 4:
        display_menu()
        selection = int(input("Enter selection: "))
        print()

        if selection == 1:
            song = Song()
            song.prompt()
            songs.append(song)
        elif selection == 2:
            song = Song()
            song.prompt()
            songs.appendleft(song)
        elif selection == 3:
            if songs:
                print("Playing song:")
                songs.popleft().display()
            else:
                print("The playlist is currently empty.")
        print()

    print("Goodbye")

if __name__ == "__main__":
    main()
