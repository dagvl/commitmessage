#!/usr/bin/python

import hotshot
import hotshot.stats
import sys

# Setup commitmessage by importing and munging the argv
import main
sys.argv[1:] = ['-c', '/home/svn/conf/commitmessage/wiki', '/home/svn/repos/wiki', '720']

prof = hotshot.Profile('cm.prof')
prof.runcall(main.main)
prof.close()

s = hotshot.stats.load('cm.prof')
s.strip_dirs()
s.sort_stats('time', 'calls')
s.print_stats(20)

