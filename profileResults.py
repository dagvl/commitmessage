#!/usr/bin/python

import hotshot
import hotshot.stats
import os
import sys

i = 0
while 1:
    f = 'commitmessage%s.profile' % i
    if not os.path.exists(f): break

    s = hotshot.stats.load(f)
    s.strip_dirs()
    s.sort_stats('time', 'calls')
    s.print_stats(20)

    os.remove(f)

    i += 1

