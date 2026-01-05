import json
import re

import numpy as np

from ns_shiny_hunter import util

ENCOUNTER_RE = re.compile(r'^.*run:54 - Encounter took (.*)s$')

if __name__ == '__main__':
    with open('ramanas_park.logs', 'r') as f:
        content = f.read()
    encounter_times = []
    lines = content.splitlines()
    for line in content.splitlines():
        result = ENCOUNTER_RE.match(line)
        if not result:
            continue
        group = result.group(1)
        encounter_time = float(result.group(1))
        print(f'Found encounter time: "{encounter_time}" from groups "{result.groups()}"')
        encounter_times.append(encounter_time)
    with open('baseline.json', 'w') as f:
        json.dump(encounter_times, f)

    # with open('baseline.json', 'r') as f:
    #     encounter_times = json.load(f)
    #
    # arr = np.array(encounter_times, dtype=float)
    # arr = arr[~np.isnan(arr)]
    # n = arr.size
    # if n == 0:
    #     raise ValueError("No valid encounter times found.")
    #
    # mean = float(np.mean(arr))
    # median = float(np.median(arr))
    # # sample standard deviation (ddof=1) if possible, else 0.0
    # stdev = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    # p90 = float(np.percentile(arr, 90))
    # p95 = float(np.percentile(arr, 95))
    # p99 = float(np.percentile(arr, 99))
    # print({
    #     'count': n,
    #     'min': float(np.min(arr)),
    #     'max': float(np.max(arr)),
    #     'mean': mean,
    #     'median': median,
    #     'stdev': stdev,
    #     '90th_percentile': p90,
    #     '95th_percentile': p95,
    #     '99th_percentile': p99,
    # })
    # util.is_outlier(3.0, encounter_times)


