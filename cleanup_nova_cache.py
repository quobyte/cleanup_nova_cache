#!/bin/python3


import argparse
import configparser
import json
from os import walk, remove
from os.path import abspath, basename, getmtime, join, isfile
import subprocess
import sys
import time


DESCRIPTION = ("Lists and optionally removes unused and aged base images "
               "from Novas image cache on a shared file system.")
DEFAULT_MIN_AGE = 86400
DEFAULT_STATE_PATH = "/var/lib/nova"
DEFAULT_INSTANCES_SUBDIR_NAME = "instances"
DEFAULT_IMAGE_CACHE_SUBDIR_NAME = "_base"

# set up argument parser
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument('-s', '--statepath',
                    default=DEFAULT_STATE_PATH,
                    help='path of the Nova state')
parser.add_argument('-i', '--instancesname',
                    default=DEFAULT_INSTANCES_SUBDIR_NAME,
                    help='name of the instances directory')
parser.add_argument('-c', '--cachename',
                    default=DEFAULT_IMAGE_CACHE_SUBDIR_NAME,
                    help='name of the image cache directory')
parser.add_argument('-r', '--readconfig', action='count',
                    help='read path data from the nova.conf file')
parser.add_argument('-a', '--age', type=float,
                    default=DEFAULT_MIN_AGE,
                    help='minimum file age in seconds')
parser.add_argument('-v', '--verbose', action="count",
                    help='provide logging output during operation')
parser.add_argument('-d', '--delete', action="count",
                    help='explicitely delete unused images.')

args = parser.parse_args()

if not len(sys.argv) > 1:
    exit()

if args.readconfig:
    # Identify state path in Nova config
    try:
        if args.verbose:
            print("Looking for state path property in nova.conf...")
        nova_conf = configparser.ConfigParser()
        nova_conf.read("/etc/nova/nova.conf")
        if nova_conf['DEFAULT']['state_path']:
            args.statepath = nova_conf['DEFAULT']['state_path']
        if nova_conf['DEFAULT']['instances_path']:
            args.instancesname = nova_conf['DEFAULT']['state_path']
        if nova_conf['DEFAULT']['image_cache_subdirectory_name']:
            args.cachename = nova_conf['DEFAULT']['image_cache_subdirectory_name']
    except Exception as e:
        if args.verbose:
            print("Could not read all settings from nova.conf: {}".format(e))

if args.verbose:
    print("Using Nova status path '{}' with instance dir name '{}' and "
          "image cache dir name '{}'".format(args.statepath, args.instancesname,
                                           args.cachename))
    print('Deleting images who are older than {} seconds'.format(args.age))


# create list of deletion candidates
base_dir = join(args.statepath, args.instancesname, args.cachename)
_, _, filenames = next(walk(base_dir), (None, None, []))
full_filenames = [join(args.statepath, args.instancesname,
                       args.cachename, f) for f in filenames]
if args.verbose:
    print("Files stored in cache: {}".format(full_filenames))
# filter out young files from candidates list
oldfiles = [f for f in full_filenames if (time.time()- getmtime(f)) >= args.age]
if args.verbose:
    print("Files old enough for deletion: {}".format(oldfiles))


# Loop over instances and remove used backing files from deletion cand. list
instances_dir = join(args.statepath, args.instancesname)
_, dirnames, _ = next(walk(instances_dir), (None, [], None))
full_instance_dirnames = [join(args.statepath,
                               args.instancesname,
                               d) for d in dirnames]
# remove cache dir from list
full_instance_dirnames.remove(join(args.statepath, args.instancesname,
                                   args.cachename))
if args.verbose:
    print ("Directories stored in instances folder: {}"
           .format(full_instance_dirnames))
used_paths = []
for instancepath in full_instance_dirnames:
    if isfile(join(instancepath, "disk")):
        qemu_result = subprocess.check_output(['qemu-img',
                                               'info',
                                               '--output=json',
                                               join(instancepath, "disk")])
        qemu_json = json.loads(qemu_result.decode("utf-8"))
        if args.verbose:
            print("qemu-img result: {}".format(qemu_json))
        # NOTE(kaisers): Nova uses absolute paths for backing files, we rely
        # on this here!
        if "backing-filename" in qemu_json:
            b = qemu_json["backing-filename"]
            if args.verbose:
                print("{} is a backing file.".format(b))
            if b in oldfiles:
                if args.verbose:
                    print("{} is still in use, ignoring.".format(b))
                oldfiles.remove(b)
                if b not in used_paths:
                    used_paths.append(b)
            elif b not in used_paths and b not in full_filenames:
                print("ERROR! Unable to locate backing file {} !!".format(b))
                if args.delete:
                    print(
                        "Deactivating deletion flag as one or more backing files"
                        " could not be located.")
                    args.delete = False
        else:
            if args.verbose:
                print("{} has no backing file set, ignoring..."
                      .format(instancepath))

if args.verbose:
    print("Leftover deletion candidates: {}".format(oldfiles))

# list unused images and delete if -d flag is set
for image in oldfiles:
    print(image)
    if args.delete:
        remove(image)