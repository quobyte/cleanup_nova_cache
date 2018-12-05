# OpenStack Nova Image Cache Cleanup Script

This script can be run to remove old and unused images from the Nova base image 
cache. This is helpful if Nova is configured with:

    remove_unused_base_images = False

This is sometimes used if Nova ephemeral images are stored in a shared
filesystem, in order to prevent different Nova hosts from interfering with
each others base images. Usage:

    usage: cleanup_nova_cache.py [-h] [-s STATEPATH] [-i INSTANCESNAME]
                             [-c CACHENAME] [-r] [-a AGE] [-v] [-d]

    Lists and optionally removes unused and aged base images from Novas image
    cache on a shared file system.
    
    optional arguments:
      -h, --help            show this help message and exit
      -s STATEPATH, --statepath STATEPATH
                            path of the Nova state
      -i INSTANCESNAME, --instancesname INSTANCESNAME
                            name of the instances directory
      -c CACHENAME, --cachename CACHENAME
                            name of the image cache directory
      -r, --readconfig      read path data from the nova.conf file
      -a AGE, --age AGE     minimum file age in seconds
      -v, --verbose         provide logging output during operation
      -d, --delete          explicitly delete unused images.
