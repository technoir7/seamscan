import os
import sys


def count_lines(path):
    return int(os.popen("wc -l < {}".format(path)).read().strip())


if __name__ == "__main__":
    print(count_lines(sys.argv[1]))
