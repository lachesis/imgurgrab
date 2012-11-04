#!/usr/bin/python2.7
import argparse
import nethandler
import urllib
import json
import logging
import re,urlparse
import subprocess
import os
import demjson
import sys
import Queue,threading

def sizeof_fmt(num):
    for x in ['bytes','KB','MB','GB']:
        if num < 1024.0 and num > -1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')

def get_imgur_album(url,title=None):
    net = nethandler.NetHandler(fast=True,cookies=True)
    # first, get the main page
    try:
        txt = net.get(url)
    except nethandler.Error404:
        logging.error( "Unable to fetch album (404) - {0}".format(url) )
        return
    
    # now find the ImgurAlbum JS object
    try:
        iajs = demjson.decode(re.search(r'(?mis)album = Imgur.Album.getInstance\((\{.*?\})\)',txt).group(1))
    except:
        iajs = demjson.decode(re.search(r'(?mis)album = new ImgurAlbum\((\{.*?\})\)',txt).group(1))
    
    # and the post title
    if not title:
        m = re.search(r'(?mis)<meta\s*name="twitter:title"\s*value="(.*?)"\s*/>',txt)
        title = m.group(1) if m else None
        if not title:
            m = re.search(r'(?mis)<title>\s*(.*?)\s*-\s*Imgur\s*</title>',txt)
            title = m.group(1) if m else 'Unknown Title'
    
    if not 'images' in iajs or not iajs['images'] or not 'items' in iajs['images'] or not iajs['images']['items'] or len(iajs['images']['items']) == 0:
        print "Warning: album at {0} is broken somehow!!".format(url)
        return None

    # make up the filename
    filename = '{0} ({1})'.format(title.replace('/','.'),iajs['id'])

    #printj(iajs)
    
    # create the directory
    try: os.mkdir(filename)
    except: pass
    os.chdir(filename)

    # log
    print "Downloading album \"{0}\" with {1} pictures (est. size: {2})".format(
        filename,
        len(iajs['images']['items']),
        sizeof_fmt(sum([t['size'] for t in iajs['images']['items']]))
    )

    inqueue = Queue.Queue()
    class IGThread(threading.Thread):
        def run(self):
            mnet = nethandler.NetHandler(fast=True,cookies=False)
            while True:
                url = inqueue.get()
                try:
                    if not url: return
                    mnet.saveURL(url,skip_if_exists=True)
                    sys.stdout.write('.')
                    sys.stdout.flush()
                finally: inqueue.task_done()
                
    # queue all the images
    for image in iajs['images']['items']:
        inqueue.put('http://i.imgur.com/' + image['hash'] + image['ext'])

    # create right number of threads
    threadcnt = 8
    threads = [IGThread() for t in xrange(threadcnt)]

    # start downloading!
    for t in threads: inqueue.put(None)
    for t in threads: t.start()
    for t in threads: t.join()
    print
    sys.stdout.flush()

    # change back up
    os.chdir('..')

if __name__ == '__main__':
    get_imgur_album(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
