from threading import Thread

from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from time import sleep

class MediaPlayer(Thread):
    def __init__(self, musicPath):
        super(MediaPlayer, self).__init__()
        self.musicPath = musicPath
        self.player = QMediaPlayer()
        
    def run(self) -> None:
        url = QUrl.fromLocalFile(self.musicPath)
        content = QMediaContent(url)
        self.player.setMedia(content)
        self.player.play()
        sleep(2)