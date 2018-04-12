#!/usr/bin/env python
#
# Description:
#
#      This script takes a transcript TXT from Zoom and converts it to a
#      transcript for posting to YouTube.
#
# Usage:
#
#      python scripts/convert_transcript_timestamps.py <input transript txt> [ <relative start timestamp> ]
#
# Environment Variables:
#
#     None.
#
# Configuration:
#
#     None.

import re
from datetime import timedelta
import sys

arg_names = ['command', 'file', 'start_ts']
args = dict(zip(arg_names, sys.argv))
# TODO: start_ts not implemented

# Number of seconds to shift the timestamps forward to ensure the context of
# each comment is captured.
SEC_TIMESHIFTED = 5

def process(transcript_file):
    with open(transcript_file) as f:
        content = f.readlines()
    for line in content:
        line_re = re.compile('^(?P<timestamp>.+?)\s+(?P<author>.+?): (?P<message>.+)')
        result = re.match(line_re, line)
        data = {}
        data.update({'ts': result.group('timestamp')})
        data.update({'author': result.group('author')})
        data.update({'msg': result.group('message')})

        yield data

is_start = lambda x: x.startswith('START')

transcript = list(process(args['file']))

def parse_ts_delta(timecode):
    hh, mm, ss = [int(x) for x in timecode.split(':')]
    return timedelta(hours=hh, minutes=mm, seconds=ss)

recording_starts = [x for x in transcript if is_start(x['msg'])]
start_delta = parse_ts_delta(recording_starts[0]['ts'])

for line in transcript:
    transposed_ts = parse_ts_delta(line['ts']) - start_delta
    context_shift = timedelta(seconds=SEC_TIMESHIFTED)
    if transposed_ts > context_shift:
        transposed_ts = transposed_ts - context_shift
    print('0{} {}: {}'.format(transposed_ts, line['author'], line['msg']))
