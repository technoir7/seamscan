import cPickle as pickle

from worker.queue import pop


def handle_next():
    body = pop("jobs")
    job = pickle.loads(body)
    job.run()
