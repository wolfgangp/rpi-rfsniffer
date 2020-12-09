#!/usr/bin/env python
'''
Copyright (c) 2017, Jesper Derehag
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

from __future__ import print_function
import argparse
import os
from pathlib import Path
import shelve
import sys
import time
import warnings

try:
    if 'RPi.GPIO' not in sys.modules:
        import RPi.GPIO as GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
except RuntimeError:
    # Catch here so that we can actually test on non-pi targets
    warnings.warn('This can only be executed on Raspberry Pi', RuntimeWarning)

if GPIO.getmode() == GPIO.BCM:
    defaulttxpin = 17
    defaultrxpin = 27
elif GPIO.getmode() == GPIO.BOARD:
    defaulttxpin = 11
    defaultrxpin = 13

defaulttimeout = 0.1

rfsnifferdir = Path(__file__).parent.absolute()
defaultpath = str(rfsnifferdir / "buttons")


def play(button_name, txpin=defaulttxpin, buttonsdb=defaultpath):
    # buttons = shelve.open(buttonsdb)
    GPIO.setup(txpin, GPIO.OUT, initial=GPIO.LOW)
    with shelve.open(buttonsdb) as buttons:
        for i, (timing, level) in enumerate(buttons[button_name]):
            if i is not 0:
                # Busy-sleep (gives a better time granularity than
                # sleep() but at the cost of busy looping)
                now = time.time()
                while now + timing > time.time():
                    pass
            GPIO.output(txpin, level)
    GPIO.cleanup()


def parsed_play(args):
    for button in args.button:
        play(button, args.txpin, args.buttonsdb)    


def read_timings(rxpin, timeout):
    capture = []
    start = time.time()
    now = 0
    #while True:
    while now < start + timeout:
        now = time.time()
        if GPIO.wait_for_edge(rxpin, GPIO.BOTH, timeout=1000):
            capture.append((time.time() - now, GPIO.input(rxpin)))
        elif len(capture) < 5:  # Any pattern is likely larger than 5 bits
            capture = []
        else:
            return capture
    return capture

def record(button_name, rxpin=defaultrxpin, buttonsdb=defaultpath, timeout=defaulttimeout):
    GPIO.setup(rxpin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    print('Press', button_name)
    sample = read_timings(rxpin, timeout)
    print('Recorded', len(sample), 'bit transitions')
    with shelve.open(buttonsdb) as buttons:
        buttons[button_name] = sample
    GPIO.cleanup()


def parsed_record(args):
    record(args.button, args.rxpin, args.buttonsdb, args.timeout)
    # GPIO.setup(args.rxpin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    # print('Press', args.button)
    # sample = read_timings(args.rxpin, args.timeout)
    # print('Recorded', len(sample), 'bit transitions')
    # buttons[args.button] = sample
    # GPIO.cleanup()


def dump(buttonsdb=defaultpath, verbose=False):
    # buttons = shelve.open(buttonsdb)
    with shelve.open(buttonsdb) as buttons:
        for button in sorted(buttons.keys()):
            print(button)
            if verbose:
                print("timings:")
                for timing, _ in buttons[button]:
                    print(f"{(timing * 1e6):.0f}", end=",")  # microseconds
                print("\nhigh/low:")
                for _, toggle in buttons[button]:
                    print(toggle, end=",")
                print("\n")


def parsed_dump(args):
    dump(args.buttonsdb, args.verbose)
    # for button in sorted(buttons.keys()):
    #     print(button)
    #     if args.verbose:
    #         #for timing, toggle in buttons[button]:
    #             #print('\t{0:.6f}'.format(timing), toggle)
    #         print("timings:")
    #         for timing, _ in buttons[button]:
    #             print(f"{(timing * 1e6):.0f}", end=",")
    #         print("\nhigh/low:")
    #         for _, toggle in buttons[button]:
    #             print(toggle, end=",")
    #         print("\n")



def main():
    fc = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(add_help=True, formatter_class=fc)

    subparsers = parser.add_subparsers(help='sub-command help')

    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        default=False, help='Verbose output')


    parser.add_argument('--rxpin', type=int, default=defaultrxpin,
                        help=('The RPi boardpin where the RF receiver'
                              ' is attached'))

    parser.add_argument('--txpin', type=int, default=defaulttxpin,
                        help=('The RPi boardpin where the RF transmitter'
                              ' is attached'))

    parser.add_argument('-b', '--buttonsdb', dest='buttonsdb',
                        default=defaultpath)

    # Record subcommand
    parser_record = subparsers.add_parser('record',
                                          help='Record an RF signal')
    parser_record.add_argument('button')
    parser_record.add_argument('-timeout', type=float, default=defaulttimeout,
                               help='Stop recording after x seconds')
    parser_record.set_defaults(func=parsed_record)

    # Play subcommand
    parser_play = subparsers.add_parser('play', help=('Send a previously '
                                                      'recorded RF signal'))
    parser_play.add_argument('button', nargs='*')
    parser_play.set_defaults(func=parsed_play)

    # Dump subcommand
    parser_dump = subparsers.add_parser('dump', help=('Dumps the already '
                                                      'recorded RF signals'))
    parser_dump.set_defaults(func=parsed_dump)

    args = parser.parse_args()

    # buttons = shelve.open(args.buttonsdb)
    # args.func(args, buttons)
    args.func(args)

    # buttons.close()
    # GPIO.cleanup()


if __name__ == '__main__':
    main()
