__author__ = 'yangchenxing'

import time


def clean_expired_data(user_data, interval=90*86400):
    now = int(time.time())
    done_jobs = [job for job in user_data.done_jobs if now - job.timestamp >= interval]
    if done_jobs:
        for job in done_jobs:
            user_data.done_jobs.remove(job)
        return True
    else:
        return False
