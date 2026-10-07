import cPickle


def load_session(db, session_id):
    row = db.execute("SELECT data FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return cPickle.loads(row[0]) if row else {}


def load_session_file(fh):
    return cPickle.load(fh)
