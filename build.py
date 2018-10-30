#! /usr/bin/python3

import argparse
import subprocess as sp
import os
import sys
import fcntl

LOCKFILE = '/home/pi/.build_lock'

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build a hss-app image from a Dockerfile.")
    ap.add_argument('-i', dest="dockerfilepath", help='The input dockerfile')
    ap.add_argument('-o', dest='outpath', help='The output path for saving the image as .tar container')
    ap.add_argument('-r', dest='repo', help='The repository to upload the image to')
    ap.add_argument('-p', dest='password', help='The password to login to the repository')
    ap.add_argument('-u', dest='username', help='The username to login to the repository')
    args = ap.parse_args()

    inpath = os.path.abspath(args.dockerfilepath)
    lastslash = inpath.rfind('/')
    username = inpath[inpath[:lastslash].rfind('/'):lastslash]

    print('Username: ' + username)

    if os.path.exists(LOCKFILE):
        print("Build in progress, please wait until the current build is finished!")
        sys.exit(1)

    else:
        hold_lock = False
        with open(LOCKFILE, 'rw') as fd:
            try:
                fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                builduser = fd.read().rstrip()
                if (builduser == ''):
                    fd.write(username + '\n')
                    builduser = username
                if (builduser == username):
                    hold_lock = True
                    fcntl.flock(fd, fcntl.LOCK_UN)
                else:
                    print("Build in progress, please wait until the current build is finished!")
                    fcntl.flock(fd, fcntl.LOCK_UN)
                    sys.exit(1)
            except IOError:
                print("Build in progress, please wait until the current build is finished!")
                sys.exit(1)

        if(hold_lock):
            status = sp.call(['balena', 'build', inpath, '--tag', 'hss-app-' + username])
            if status == 0:
                status = sp.call(['balena', 'tag', 'hss-app-' + username, 'hss-app'])
                if status == 0:
                    if args.outpath:
                        if not args.outpath.endswith('.tar'):
                            args.outpath += '.tar'
                        status = sp.call(['balena', 'save', 'hss-app', '-o', args.outpath])
                        if status == 0:
                            print('Successfully saved image to ' + args.outpath)

                    if args.repo:
                        try:
                            status = sp.call(['balena', 'login', args.repo, '-p', args.password, '-u', args.username])
                            if status == 0:
                                status = sp.call(['balena', 'push', 'hss-app'])
                        except Exception as ex:
                            print("Uploading image to " + args.repo + " failed")
                            sys.exit(1)

            with open(LOCKFILE, 'rw') as fd:
                try:
                    fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
                    os.unlink(LOCKFILE)
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except IOError:
                    print("Could not delete lock file, please delete " + LOCKFILE + " manually!")
                    sys.exit(1)
