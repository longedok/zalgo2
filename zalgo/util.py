import time
import random

class Util():
    @staticmethod
    def generateId():
        unix_time = str(int(time.time() * 1000))
        random_postfix = ''.join([chr(random.randint(ord('a'), ord('z'))) for _ in xrange(4)])
        return unix_time + random_postfix

if __name__ == '__main__':
    for i in xrange(1, 10):
        print Util.generateId()
