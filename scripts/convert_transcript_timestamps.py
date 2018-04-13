#!/usr/bin/env python
import re
from datetime import timedelta
import sys
import click

OUT_TRANSCRIPT_LINE_TEMPLATE = '{ts} {author}: {msg}\n'
IN_TRANSCRIPT_START_MARKER = 'START'

@click.command()
@click.argument('input-file', type=click.File('rb'))
@click.option('--output-file', help='The file to write. Default: stdout', default='-', type=click.File('wb'))
@click.option('--context-offset', help='The number of seconds to shift timestamps forward for message context. Default: 5', default=5)
@click.option('--start-timestamp', help='The timestamp to manually set as the start. Default: auto-detects START message')

def process(input_file, output_file, context_offset, start_timestamp):
    """This script takes a transcript TXT from Zoom and converts it to a
    transcript for posting to YouTube."""

    transcript_data = parse_transcript(input_file, context_offset)
    for line in transcript_data:
        updated_line = OUT_TRANSCRIPT_LINE_TEMPLATE.format(ts =line['ts_transposed'],
                author=line['author'],
                msg=line['msg'])
        output_file.write(updated_line.encode('utf8'))

def parse_transcript(input_file, context_offset):
    data = [{'raw': x.decode('utf8')} for x in input_file.readlines()]
    line_re = re.compile('^(?P<timestamp>.+?)\s+(?P<author>.+?):\s+(?P<message>.+)')

    for i, line in enumerate(data):
        result = re.match(line_re, line['raw'])
        data[i].update({'ts': result.group('timestamp')})
        data[i].update({'author': result.group('author')})
        data[i].update({'msg': result.group('message')})

    is_start = lambda x: x['msg'].startswith(IN_TRANSCRIPT_START_MARKER)
    recording_starts = list(filter(is_start, data))
    start_delta = parse_ts_delta(recording_starts[0]['ts'])

    for i, line in enumerate(data):
        ts_transposed = parse_ts_delta(line['ts']) - start_delta
        context_shift = timedelta(seconds=context_offset)
        if ts_transposed > context_shift:
            ts_transposed = ts_transposed - context_shift
        ts_transposed = '0' + str(ts_transposed)
        data[i].update({'ts_transposed': ts_transposed})

    return data

def parse_ts_delta(timestamp):
    hh, mm, ss = [int(x) for x in timestamp.split(':')]
    return timedelta(hours=hh, minutes=mm, seconds=ss)

if __name__ == '__main__':
    process()
