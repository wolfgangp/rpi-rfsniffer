import numpy as np

from collections import namedtuple
from pathlib import Path
import shelve

Protocol = namedtuple('Protocol',
                      ['pulselength',
                       'sync_high', 'sync_low',
                       'zero_high', 'zero_low',
                       'one_high', 'one_low'])

PROTOCOLS = (None,
             Protocol(350, 1, 31, 1, 3, 3, 1),
             Protocol(650, 1, 10, 1, 2, 2, 1),
             Protocol(100, 30, 71, 4, 11, 9, 6),
             Protocol(380, 1, 6, 1, 3, 3, 1),
             Protocol(500, 6, 14, 1, 2, 2, 1),
             Protocol(200, 1, 10, 1, 5, 1, 1),
             Protocol(150, 2, 62, 1, 6, 6, 1))

def get_db(path=None):
    return shelve.open(path or Path.home() / "buttons.db", writeback=True)

def condense_protocol3(stream):
    """ this assumes microseconds (us) """
    synch_signals = np.where((stream > 2900) & (stream < 7000))[0]
    # synch_signals = np.where(stream > 6900)[0]
    last_full_signal_end_idx = synch_signals[-1]
    last_full_signal_start_idx = synch_signals[-2]
    return last_full_signal_start_idx, last_full_signal_end_idx

def make_short(button_name):
    db = get_db(str(Path(__file__).parent / "buttons.db"))
    raw = np.asarray(db[button_name])
    timings = (raw[:,0] * 1e6).astype(np.int)  # s to us
    toggle = raw[:,1].astype(np.int)
    start, end = condense_protocol3(timings)
    float_timings = timings.astype(np.float) / 1e6
    short = list(zip(float_timings[start: end].tolist(), toggle[start: end].tolist()))
    print(f"Bits in signal (including synch): {len(short) / 2}")
    db[button_name + ".short"] = short * 3  # repeat 3 times
    db.close()


make_short("OBIRemote2.C.on2")
