def merge_records(a, b):
    return a if a['ts'] > b['ts'] else b
