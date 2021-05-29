#! /usr/bin/env python

import sys
import os
from glob import glob

import zipfile
import md5


def check_egg(egg):
    if os.path.isdir(egg):
        return
    z = zipfile.ZipFile(egg, 'r')
    filenames = z.namelist()
    if 'EGG-INFO/not-zip-safe' in filenames:
        temp_dir = os.path.join(os.path.dirname(egg), md5.new(egg).hexdigest())
        os.mkdir(temp_dir)
        print 'Unpacking egg, this will only happen once.' 
        for filename in filenames:
            filepath = os.path.join(temp_dir, filename)
            try:
                os.makedirs(os.path.dirname(filepath))
            except OSError:
                pass
            f = open(filepath, 'wb')
            f.write(z.read(filename))
            f.close()
            print ".",
        os.remove(egg)
        os.rename(temp_dir, egg)
        print 'Done.'

try:
    __file__
except NameError:
    pass
else:
    libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'lib'))
    sys.path.insert(0, libdir)
    eggdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'eggs'))
    for egg in glob(os.path.join(eggdir, '*.egg')):
        check_egg(egg)
        sys.path.insert(0, os.path.abspath(egg))
    for egg in glob(os.path.join(eggdir, sys.platform, '*.egg')):
        check_egg(egg)
        sys.path.insert(0, os.path.abspath(egg))

import main
main.main()
