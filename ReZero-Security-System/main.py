from threading import Thread
from cv2_detection import run_program
from cv2_bot.bot import run_bot

from tests.test1 import abc
from tests.test2 import abc2

def run_rezero_security_system():
    Thread(target=run_program).start()
    Thread(target=run_bot).start()

if __name__ == "__main__":
    run_rezero_security_system()