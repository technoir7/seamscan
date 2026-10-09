import argparse

from replay_lib import Runner


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    args = ap.parse_args()
    Runner(args.log).run(debug=True)


if __name__ == "__main__":
    main()
