# installer for wxobs
# Copyright 2016 Matthew Wall
# Co-opted by Glenn McKechnie 2017-2024
# Distributed under the terms of the GNU Public License (GPLv3)
"""
    #-O, --omit-dir-times        omit directories from --times
    #-z, --compress              compress file data during the transfer
    #-v, --verbose               increase verbosity)
    # rsync_options = -rlptgoD
    # -D                          same as --devices --specials
    #  rsync_options = -rlptgoD
    # -o, --owner                 preserve owner (super-user only)
    #r sync_options = -rltg
    #-g, --group                 preserve group
    #rs ync_options = -rlt
    #-t, --times                 preserve modification times
    #rsy nc_options = -rl
    #-l, --links                 copy symlinks as symlinks
    #-r, --recursive             recurse into directories
    #rsyn c_options = -tOJrlenerators
    # -t, --times                 preserve modification times
    # -O, --omit-dir-times        omit directories from --times
    # -J, --omit-link-times       omit symlinks from --times
"""
from setup import ExtensionInstaller

def loader():
    return rsynctransferInstaller()

class rsynctransferInstaller(ExtensionInstaller):
    def __init__(self):
        super(rsynctransferInstaller, self).__init__(
            version="0.7.0",
            name='rsynctransfer',
            description='Transfer weewx files to where-ever, local, remote...',
            author="Glenn McKechnie",
            author_email="glenn.mckechnie@gmail.com",
            config={
                'StdReport': {
                    'RsyncTransfer': {
                        'skin': 'rsynctransfer'
                   }}},
            files=[('bin/user',
                    ['bin/user/rsynctransfer.py']),
                   ('skins/rsynctransfer',
                    ['skins/rsynctransfer/skin.conf']),
                  ]
        )
