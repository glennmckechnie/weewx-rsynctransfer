# rsyncthread.py
#
# A weeWX service able to transfer files by rsync as required.
#
# Copyright (C) 2017 Gary Roderick                  gjroderick<at>gmail.com
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see http://www.gnu.org/licenses/.
#
# Version: 0.1                                        Date: 15 February 2017
#
# Revision History
#  15 February 2017     v0.1.0  - initial release
#
"""A weeWX service able to transfer files by rsync as required.

An rsync capable thread monitors a queue and rsync transfers file that appear
in the queue.

Based on a previous service rsyncloop that rsync transferred a given file on
every loop packet.

##############################################################################
[RsyncThread]

    # RsyncThread is a service that controls a thread that can upload discrete
    # files to a remote system via rsync. The service is based on the
    # underlying code of the weeWX rsync skin (rsyncupload.py). Unlike the
    # rsync skin which only executes every report cycle, RsyncThread runs in a
    # thread and utilises a Queue object to allow it to accept and process
    # rsync transfers at any time.

    # run this service? True to enable, False to disable. Default is False
    enable = True

    # Remote path
    remote_path = replace_me

    # Server address
    server = replace_me

    # User name
    user = replace_me

    # Port number. Default is rsync default of 873
    port =

    # Delete file on remote server if file is deleted on local server?
    # Default is False
    delete =

    # ssh timeout in seconds. Period after which an unsuccessful ssh connection
    # will be terminated. Default is to use system default TCP timeout setting.
    # Refer ssh documentation.
    ssh_timeout = 2

    # rsync timeout in seconds. Period after which an unsuccessful rsync
    # session will be terminated. Default is no timeout.
    rsync_timeout = 2

##############################################################################
"""

# python imports
import Queue
import os.path
import subprocess
import syslog
import threading
import time

# weeWX imports
import weewx
import weeutil.weeutil
from weewx.engine import StdService

# version number of this script
RSYNC_THREAD = '0.1'


def logmsg(level, msg):
    syslog.syslog(level, msg)


def logcrit(id, msg):
    logmsg(syslog.LOG_CRIT, '%s: %s' % (id, msg))


def logdbg(id, msg):
    logmsg(syslog.LOG_DEBUG, '%s: %s' % (id, msg))


def logdbg2(id, msg):
    if weewx.debug >= 2:
        logmsg(syslog.LOG_DEBUG, '%s: %s' % (id, msg))


def loginf(id, msg):
    logmsg(syslog.LOG_INFO, '%s: %s' % (id, msg))


def logerr(id, msg):
    logmsg(syslog.LOG_ERR, '%s: %s' % (id, msg))


# ============================================================================
#                                class Rsync
# ============================================================================


class Rsync(StdService):
    """Service that rsync transfers files as required."""

    def __init__(self, engine, config_dict):
        # initialize my superclass
        super(Rsync, self).__init__(engine, config_dict)

        engine.rsync_queue = Queue.Queue()
        self.rsync_queue = engine.rsync_queue

        self.rsync_thread = RsyncThread(self.rsync_queue, config_dict)
        self.rsync_thread.start()

    def shutDown(self):
        """Shut down any threads."""

        if hasattr(self, 'rsync_queue') and hasattr(self, 'rsync_thread'):
            if self.rsync_queue and self.rsync_thread.isAlive():
                # Put a None in the queue to signal the thread to shutdown
                self.rsync_queue.put(None)
                # Wait up to 20 seconds for the thread to exit:
                self.rsync_thread.join(20.0)
                if self.rsync_thread.isAlive():
                    logerr("rsyncthread",
                           "Unable to shut down %s thread" % self.rsync_thread.name)
                else:
                    logdbg("rsyncthread",
                           "Shut down %s thread." % self.rsync_thread.name)


# ============================================================================
#                             class RsyncThread
# ============================================================================


class RsyncThread(threading.Thread):
    """Thread that rsync transfers files."""

    def __init__(self, queue, config_dict):
        # Initialize my superclass:
        threading.Thread.__init__(self)

        self.setDaemon(True)
        self.queue = queue

        # get our RsyncThread config dictionary
        rsync_config_dict = config_dict.get('RsyncThread', {})

        # are we enabled?
        self.enable = rsync_config_dict.get('enable', False)

        # Get the rest our our rsync parameters
        self.remote_path  = os.path.normpath(rsync_config_dict.get('remote_path'))
        self.server       = rsync_config_dict.get('server')
        self.user         = rsync_config_dict.get('user')
        self.delete       = rsync_config_dict.get('delete', False)
        self.port         = rsync_config_dict.get('port')
        self.sshtimeout   = rsync_config_dict.get('ssh_timeout')
        self.rsynctimeout = rsync_config_dict.get('rsync_timeout')


    def run(self):
        """Monitor the queue and rsync files as required."""

        # run a continuous loop, waiting for jobs to appear in the queue then
        # process them
        while True:
            while True:
                _file_spec = self.queue.get()
                # a None record is our signal to exit
                if _file_spec is None:
                    return
                elif not os.path.isfile(_file_spec):
                    logdbg2("rsyncthread", "file spec '%s' skipped" % (_file_spec, ))
                    continue
                # if packets have backed up in the queue, trim it until it's no
                # bigger than the max allowed backlog
                if self.queue.qsize() <= 5:
                    break

            # we now have a file to rsync, if we are enabled wrap in a
            # try..except so we can catch any errors
            if self.enable:
                try:
                    logdbg2("rsyncthread", "rsyncing file: %s" % (_file_spec, ))
                    self.rsync(_file_spec)
                    logdbg2("rsyncthread", "rsyncing file: %s" % (_file_spec, ))
                except (IOError), e:
                    (cl, unused_ob, unused_tr) = sys.exc_info()
                    logcrit("rsyncthread",
                            "Caught exception %s in RsyncThread; %s." % (cl, e))
                    logcrit("rsyncthread", "Thread exiting.")
                    return

    def rsync(self, file_spec):
        """Perform the rsync."""

        t1 = time.time()
        # create the rsync command string elements
        # the remote login spec
        if self.user is not None and len(self.user.strip()) > 0:
            rsyncremotespec = "%s@%s:%s" % (self.user,
                                            self.server,
                                            self.remote_path)
        else:
            rsyncremotespec = "%s:%s" % (self.server, self.remote_path)

        # the port
        if self.port is not None and len(self.port.strip()) > 0:
            rsyncsshstring = "ssh -p %s" % (self.port,)
        else:
            rsyncsshstring = "ssh"

        #  the ssh string
        if self.sshtimeout is not None and len(self.sshtimeout.strip()) > 0:
            rsyncsshstring += " -o ConnectTimeout=%s" % (self.sshtimeout,)

        # the timeout string
        if self.rsynctimeout is not None and len(self.rsynctimeout.strip()) > 0:
            rsynctimeoutstring = "--timeout=%s" % (self.rsynctimeout,)
        else:
            # rsync default --timeout setting
            rsynctimeoutstring = "--timeout=0"

        # now built the command list
        # the base
        cmd = ['rsync']
        # --archive means:
        #    recursive, copy symlinks as symlinks, preserve permissions,
        #    preserve modification times, preserve group and owner,
        #    preserve device files and special files, but not ACLs,
        #    no hardlinks, and no extended attributes
        cmd.extend(["--archive"])
        # Remove files remotely when they're removed locally
        if self.delete:
            cmd.extend(["--delete"])
        # since we are 'setting and forgetting' set timeout so process will
        # automatically close if there is a problem
        cmd.extend([rsynctimeoutstring])
        # add ssh settings
        cmd.extend(["-e %s" % rsyncsshstring])
        # add our local file spec and remote spec
        cmd.extend([file_spec])
        cmd.extend([rsyncremotespec])
        # do the rsync as a subprocess, wrap in a try..except to catch what
        # errors we can
        try:
            rsynccmd = subprocess.Popen(cmd,stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,bufsize=1)
            for line in iter(rsynccmd.stdout.readline, b''):
                loginf("rsyncthread", "%s" % line)
            rsynccmd.stdout.close()
        except OSError, e:
            if e.errno == errno.ENOENT:
                logerr("rsyncthread",
                       "rsync does not appear to be installed on this system. (errno %d, \"%s\")" % (e.errno,
                                                                                                     e.strerror))
            raise
        t2 = time.time()
        # Implement some sort of reporting/logging. Since we are cutting the
        # process loose the best we can do is report what we tried to send!
        logdbg("rsyncthread",
               "rsync executed in %0.3f seconds, attempted to transfer 1 file" % (t2-t1))