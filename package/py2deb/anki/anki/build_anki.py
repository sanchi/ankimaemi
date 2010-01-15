#!/usr/bin/python2.5
# -*- coding: utf-8 -*-
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published
## by the Free Software Foundation; version 2 only.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
import py2deb
import os

if __name__ == "__main__":
     try:
         os.chdir(os.path.dirname(sys.argv[0]))
     except:
         pass
     print
     p=py2deb.Py2deb("anki")   #This is the package name and MUST be in lowercase! (using e.g. "mClock" fails miserably...)

     p.description="Friendly, intelligent flashcards (base library).\n" \
     ".\n"\
     "Anki is a spaced repetition system (SRS). It helps you remember\n" \
     "things by intelligently scheduling flashcards, so that you can learn\n" \
     "a lot of information with the minimum amount of effort.\n" \
     ".\n"\
     "Features:\n"\
     ".\n"\
     "  * Review anywhere. Anki lets you study on your own computer,\n"\
     "     online, on your cell phone or other portable devices like an\n"\
     "     iPod touch or Zaurus.\n"\
     "  * Synchronization features let you keep your information across\n"\
     "     multiple computers.\n"\
     "  * Shared decks allow you to divide work between friends, and let\n"\
     "     teachers push material to many students at once.\n"\
     "  * Intelligent scheduler based on the SuperMemo SM2 algorithm.\n"\
     "  * Flexible fact/card model that allows you to generate multiple\n"\
     "     views of information, and input information in the format you\n"\
     "     wish. You're not limited to predefined styles.\n"\
     "  * Audio and images are fully supported\n"\
     "  * Fully extensible, with a large number of plugins already\n"\
     "     available\n"\
     "  * Optimized for speed, and will handle reviewing decks of 100,000+\n"\
     "     cards with no problems\n"\
     "  * Clean, user-friendly interface\n"\
     "  * Free and Open Source\n"\
     ".\n"\
     "Homepage: http://ichi2.net/anki"
     p.author="Stefan Sayer"
     p.mail="sayer@cs.tu-berlin.de"
     p.depends = "python2.5, python-sqlalchemy (<< 0.5.0), python-simplejson (>= 2.0.6), python2.5-xml"
     p.build_depends = "less"
     p.section="other"
#     p.icon = "/home/user/MyDocs/mclock/mClock.png"
     p.arch="all"                #should be all for python, any for all arch
     p.urgency="low"             #not used in maemo onl for deb os
     p.distribution="diablo"
     p.repository="extras-devel"
     version = "0.9.9.8.5"           #Version of your software, e.g. "1.2.0" or "0.8.2"
     build = "2"                 #Build number, e.g. "1" for the first build of this version of your software. Increment for later re-builds of the same version of your software.
                                 #Text with changelog information to be displayed in the package "Details" tab of the Maemo Application Manager
     changeloginformation = "many many improvements. see http://ichi2.net/anki/download/index.html"
    
     dir_name = "src"            #Name of the subfolder containing your package source files (e.g. usr\share\icons\hicolor\scalable\myappicon.svg, usr\lib\myapp\somelib.py). We suggest to leave it named src in all projects and will refer to that in the wiki article on maemo.org
     #Thanks to DareTheHair from ITT for this snippet that recursively builds the file list 
     for root, dirs, files in os.walk(dir_name):
         real_dir = root[len(dir_name):]
         fake_file = []
         for f in files:
             fake_file.append(root + os.sep + f + "|" + f)
         if len(fake_file) > 0:
             p[real_dir] = fake_file

     print p
     r = p.generate(version,build,changelog=changeloginformation,tar=True,dsc=True,changes=True,build=False,src=True)
