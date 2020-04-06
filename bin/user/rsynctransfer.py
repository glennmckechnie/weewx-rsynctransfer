#
#    Copyright (c) 2012 Will Page <compenguy@gmail.com>
#    Derivative of ftpupload.py, credit to Tom Keffer <tkeffer@gmail.com>
#
#    Modified to allow multiple source directories to be transferred in the one
#    session, rsync to localhost, addition of dated dir structure on remote,
#    include an rsync_option, skin name for logging
#    (c) 2017 Glenn McKechnie <glenn.mckechnie@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
#    $Id: rsyncupload.py 2766 2014-12-02 02:45:36Z tkeffer $
#
"""For uploading files to a remove server via Rsync"""

import os
import errno
import sys
import subprocess
import syslog
import time
import configobj

import weewx
import weewx.engine
import weewx.manager
import weewx.units
from weewx.engine import StdService
from weeutil.weeutil import to_int, to_bool
from weewx.cheetahgenerator import SearchList

rsynct_version = "0.0.1"

def logmsg(level, msg):
    syslog.syslog(level,'rsynctransfer: %s' % msg)

def loginf(msg):
    logmsg(syslog.LOG_INFO, msg)

def logerr(msg):
    logmsg(syslog.LOG_ERR, msg)

def logdbg(msg):
    logmsg(syslog.LOG_DEBUG, msg)



class Rsynct(SearchList):
    """
    Uploads a directory and all its descendants to a remote server.

    Its default behaviour is to keep track of what files have changed,
    and only updates changed files, eg: /var/www/html/weewx transfers
    for the web server.
    
    Now modified to allow recursive behaviour, as well as additional
    directories at the remote end.
    """
    

    def __init__(self, generator):
    
        SearchList.__init__(self, generator)
        """Initialize an instance of RsyncUpload.

        After initializing, call method run() to perform the upload.

        HTML_ROOT: The default value for remote_root as read from weewx.conf.
        To use another destination, specify it as HTML_ROOT = /path/to/files
        in weewx.conf

        All other config variables - stanzas. Can exist in either weewx.conf or
        in an appropriately named skin file. They are...

        local_root: path of directory to be transferred. Multiple paths can
        be added as a space separated list - the only time spaces can be added
        to a config variable.

        server: The remote server to which the files are to be uploaded. DNS
        qualified name or IP address. Use localhost if copying locally.
        localhost can't write to / Any attempts will be redirected to
        /tmp/localhost

        user: The user name that is to be used. [Optional, maybe] If
        server = localhost is specified, user becomes ''

        dated_dir: Optional structure for remote tree eg: 2017/02/02 rolling
        over as required. this end builds those directories as required.

        rsync_option: Added to allow addition of -R, ( --relative use relative
        path name. Others may be included but that's untested. No spaces allowed

        report_timing: See the weewx documentation for the full description on
        this addition. There are many options eg:-
        @daily, @weekly, @monthly, etc

        delete: delete remote files that don't match with local files. Use
        with caution.  [Optional.  Default is False.]

        self_report_name: always defaults to the [[section]] name used in
        weewx.conf
                #local_root=local_root,
                #remote_root=self.skin_dict['path'],
                #server=self.skin_dict['server'],
                #user=self.skin_dict.get('user'),
                #port=self.skin_dict.get('port'),
                # Glenn McKechnie
                #rsync_opt=self.skin_dict.get('rsync_options'),
                #ssh_options=self.skin_dict.get('ssh_options'),
                compress=to_bool(self.skin_dict.get('compress', False)),
                delete=to_bool(self.skin_dict.get('delete', False)),

        server=None
        dated_dir=None
        user=None
        delete=False
        date_dir=False
        port=None
        rsync_opt=None
        ssh_options=None
        compress=False
        log_success=True
        """

        self.rsynct_version = rsynct_version
        # get our rsynctransfer config dictionary
        #syslog.syslog(syslog.LOG_INFO, "RSYNCTRANSFER: sys.argv[2] - %s" % sys.argv[1])
        #config_dict = configobj.ConfigObj(file_error=True, encoding='utf-8')
        #rsync_config_dict = config_dict.get('rsynctransfer', {})


        # are we enabled?
        #self.enable = rsync_config_dict.get('enable', True)

        #self.local_root  = os.path.normpath(local_root)
        #self.local_root  = rsync_config_dict.get('localroot')

        self.local_root  = self.generator.config_dict['StdReport'].get('HTML_ROOT')
#        self.local_root  = self.generator.skin_dict.get('localroot')

        #loginf("RSYNCTRANSFER: localroot %s" % (self.local_root))
        ##self.remote_root = os.path.normpath(remote_root)
        self.remote_root = self.local_root,
        #self.server      = rsync_config_dict.get('server')
        self.server      = self.generator.skin_dict.get('server'),
        #self.user        = rsync_config_dict.get('user')
        self.user        = self.generator.skin_dict.get('user'),
        #loginf("USER = %s" % self.user)
        print("USER = %s" % self.user)
        #self.dated_dir   = rsync_config_dict.get('dated_dir')
        dated_dir   = to_bool(self.generator.skin_dict.get('date_dir', 'False')),
        print (self.generator.skin_dict.get('dated_dir', False)),
        print("dated _dir = %s : type(dated dir) = %s" % (dated_dir, type(dated_dir)))
        # rsyncupload.py - dated_dir=to_bool(self.skin_dict.get('dated_dir', False)),
        #self.port        = rsync_config_dict.get('port')
        self.port        = self.generator.skin_dict.get('port',22),
        print("PORT = %s" % self.port)
        #self.rsync_opt   = rsync_config_dict.get('rsync_opt')
        self.rsync_opt   = self.generator.skin_dict.get('rsync_options','-a'),
        print("RSYNC OPT = %s" % self.rsync_opt)
        #self.ssh_options = rsync_config_dict.get('ssh_options')
        self.ssh_options = self.generator.skin_dict.get('ssh_options', " "),
        print("ssh_options %s" % self.ssh_options)
        #self.compress    = to_bool(rsync_config_dict.get('compress', False)),
        self.compress    = to_bool(self.generator.skin_dict.get('compress', False)),
        #self.delete      = rsync_config_dict.get('delete')
        #self.delete      = rsync_config_dict.get('delete')
        #delete           = to_bool(rsync_config_dict.get('delete', False)),
        self.delete           = to_bool(self.generator.skin_dict.get('delete', False)),
        #self.log_success = rsync_config_dict.get('log_success')
        self.log_success = self.generator.skin_dict.get('log_success'),
        wdebug = 1,
        syslog.syslog(syslog.LOG_INFO, "RSYNCTRANSFER: user- %s, debug is at %s" % (self.user, wdebug))
        #return 


        """
        Perform the actual upload.

        Check for rsync error codes and log the obvious ones
        """

        wdebug = 2
        t1 = time.time()
        # With multiple configs available, prefix with the skin or label name
        # for log clarity
        # Do we have spaces in this string? If so we'll have multiple directories
        # Set up for later tests
        src_dir = self.local_root.split()
        src_len = len(src_dir)
        syslog.syslog(syslog.LOG_DEBUG, "rsynct WEEWX.DEBUG: %s" % wdebug)
        if wdebug >= 2:
            syslog.syslog(syslog.LOG_DEBUG, "rsynct:local root string length: %s" % src_len)

        # If true, create the remote directory with a date structure
        # eg: <path to backup directory>/2017/02/12/var/lib/weewx...
        if dated_dir:
            print("true")
            date_dir_str = time.strftime("/%Y/%m/%d/")
            date_dir_str = ''
        else:
            print("none")
            date_dir_str = ''
        if wdebug >= 2:
            syslog.syslog(syslog.LOG_INFO, "rsynct:timestamp used for rsyncremotespec  - %s" % date_dir_str)

        # allow local transfers
        if self.server == 'localhost':
            rsyncremotespec = "%s%s" % (self.remote_root, date_dir_str)
            rsync_rem_dir = "%s%s" % (self.remote_root, date_dir_str)
            self.user = ''
            if wdebug >= 2:
                syslog.syslog(syslog.LOG_DEBUG, "rsynct:self.remote_root is %s and rsync_rem_dir is %s" %  (self.remote_root, rsync_rem_dir))
            # and attempt to prevent disasters!
            if self.remote_root == '/':
                rsyncremotespec = '/tmp/%s/' % (self.server)
                err_mes = "rsynct:rsyncupload:  ERR Attempting to write files to %s redirecting to %s ! FIXME !" %  (self.remote_root, rsyncremotespec)
                syslog.syslog(syslog.LOG_ERR, "%s" %  (err_mes))

        else:
            # construct string for remote ssh
            if self.user is not None and len(self.user) > 0:
                #loginf("%s@%s:%s%s" % (self.user[0], self.server[0], self.remote_root[0], date_dir_str))
                print("as tuples:", self.user,self.server,self.remote_root, date_dir_str)
                print("as strings:", self.user[0],self.server[0],self.remote_root[0], date_dir_str)
                rsyncremotespec = "%s@%s:%s%s" % (self.user[0], self.server[0], self.remote_root[0], date_dir_str)
                #loginf("%s@%s:%s%s" % (self.user[0], self.server[0], self.remote_root[0], date_dir_str))
                rsync_rem_dir = "%s%s" % (self.remote_root, date_dir_str)
            else:
                # ?? same account (user) as weewx
                rsyncremotespec = "%s:%s%s" % (self.server, self.remote_root, date_dir_str)
                rsync_rem_dir = "%s%s" % (self.remote_root, date_dir_str)
        # A chance to add rsync options eg -R (no spaces allowed)
        if self.rsync_opt is not None and len(self.rsync_opt) > 0:
            rsyncoptstring = "%s" % (self.rsync_opt)
        else:
            rsyncoptstring = ""
        # haven't used nor tested this (-p 222) ???
        if self.port is not None and len(self.port) > 0:
            rsyncsshstring = "ssh -p %s" % (self.port)
        else:
            rsyncsshstring = "ssh"

        # nor tested this ???
        if self.ssh_options is not None and len(self.ssh_options) > 0:
            print(self.ssh_options)
            # TypeError: Can't convert 'tuple' object to str implicitly
            # rsyncsshstring = rsyncsshstring + " " + self.ssh_options

        # construct the command argument
        cmd = ['rsync']
        # -a archive means:
        #   recursive, copy symlinks as symlinks, preserve perm's, preserve
        #   modification times, preserve group and owner, preserve device
        #   files and special files, but not ACLs, no hardlinks, and no
        #   extended attributes
        cmd.extend(["-a"])

        # add any others as required, but add them now (before ssh str)
        if self.rsync_opt:
            cmd.extend(["%s" % rsyncoptstring])

        # provide some stats on the transfer
        cmd.extend(["--stats"])

        # Remove files remotely when they're removed locally
        if self.delete:
            cmd.extend(["--delete"])
        if self.compress:
            cmd.extend(["--compress"])

        # Are we operating locally? If so tweak the cmd
        if self.server != 'localhost':
            cmd.extend(["-e %s" % rsyncsshstring])

        # If src_lentest shows we have multiple, space separated local
        # directories, seperate them out and add them back as individual stanzas
        # If we don't do this, rsync will complain about non existant files
        if src_len > 1:
            if wdebug >= 2:
                syslog.syslog(syslog.LOG_DEBUG, "rsynct:original local root string: %s" % self.local_root)
                syslog.syslog(syslog.LOG_DEBUG, "rsynct:local root string length: %s" % src_len)
                syslog.syslog(syslog.LOG_DEBUG, "rsynct:src_dir: %s" % src_dir)
            for step in range(src_len):
                # we don't want to force os.sep if we have multiple dirs use them as entered
                #if src_dir[step].endswith(os.sep):
                multi_loc = src_dir[step]
                if wdebug >= 2:
                    syslog.syslog(syslog.LOG_DEBUG, "rsynct:multi_loc = %s" % multi_loc)
                cmd.extend([multi_loc])
        else:
            # Keep original 'transfer to remote web server' behaviour - append
            # a slash to ensure only directories contents are copied.
            # If the source path ends with a slash, rsync interprets that as a
            # request to copy all the directory's *contents*, whereas if it
            # doesn't, it copies the entire directory.
            # For a single directory copy, we want the former (backwards
            # compatabile); so make it end  with a slash.
            #
            # of note : self.local_root  = os.path.normpath(local_root)
            # stanza used at the start (above) strips the last slash off ?????
            # seems redundant when we reinsert it anyway?
            # tested without and seems to make no difference - assuming no major
            # typos by user - we'll give them the benefit.
            # Removing this to allow multi path to work - original +os.sep
            # makes it redundant 2017/02/15 Glenn.McKechnie
            if self.local_root.endswith(os.sep):
                rsynclocalspec = self.local_root
                cmd.extend([rsynclocalspec])
                if wdebug >= 2:
                    syslog.syslog(syslog.LOG_DEBUG, "rsynct:rsynclocalspec ends with %s" % rsynclocalspec)
            else:
                rsynclocalspec = self.local_root + os.sep
                cmd.extend([rsynclocalspec])
                if wdebug >= 2:
                    syslog.syslog(syslog.LOG_DEBUG, "rsynct:rsynclocalspec + os.sep %s" % rsynclocalspec)
        cmd.extend([rsyncremotespec])

        try:
            # perform the actual rsync transfer...
            if wdebug >= 2:
                syslog.syslog(syslog.LOG_DEBUG, "rsynct:rsync cmd is ... %s" % (cmd))
            rsynccmd = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            print ("cmd = ", cmd[0],cmd[1],cmd[2],cmd[3],cmd[4],cmd[5],cmd[6],cmd[7],cmd[8],)
            loginf("cmdd = %s %s %s %s %s %s %s %s %s" % (cmd[0],cmd[1],cmd[2],cmd[3],cmd[4],cmd[5],cmd[6],cmd[7],cmd[8]))
            stdout = rsynccmd.communicate()[0]
            stroutput = stdout.decode("utf-8").strip()
            print("stroutput is %s", stroutput)
        except OSError as e:
            #print "EXCEPTION"
            if e.errno == errno.ENOENT:
                syslog.syslog(syslog.LOG_ERR, "rsynct:rsyncupload: rsync does not appear to be installed on this system. (errno %d, \"%s\")" % (e.errno, e.strerror))
            raise

        # we have some output from rsync so generate an appropriate message
        if stroutput.find('rsync error:') < 0:
            # no rsync error message so parse rsync --stats results
            rsyncinfo = {}
            for line in iter(stroutput.splitlines()):
                if line.find(':') >= 0:
                    (n, v) = line.split(':', 1)
                    rsyncinfo[n.strip()] = v.strip()
            # get number of files and bytes transferred and produce an
            # appropriate message
            try:
                if 'Number of regular files transferred' in rsyncinfo:
                    N = rsyncinfo['Number of regular files transferred']
                else:
                    N = rsyncinfo['Number of files transferred']

                Nbytes = rsyncinfo['Total transferred file size']
                if N is not None and Nbytes is not None:
                    rsync_message = "rsynct:rsync'd %s files (%s) in %%0.2f seconds" % (N, Nbytes)
                else:
                    rsync_message = "rsynct:rsync executed in %0.2f seconds"
            except:
                rsync_message = "rsynct:rsync :exception raised: executed in %0.2f seconds"
        else:
            # suspect we have an rsync error so tidy stroutput
            # and display a message
            stroutput = stroutput.replace("\n", ". ")
            stroutput = stroutput.replace("\r", "")
            # Attempt to catch a few errors that may occur and deal with them
            # see man rsync for EXIT VALUES
            rsync_message = "rsynct:rsync command failed after %0.2f seconds (set 'wdebug = 1'),"
            if "code 1)" in stroutput:
                if wdebug >= 1:
                    syslog.syslog(syslog.LOG_DEBUG, "rsynct:rsyncupload: rsync code 1 - %s" % stroutput)
                rsync_message = "rsynct:syntax error in rsync command - set debug = 1 - ! FIX ME !"
                syslog.syslog(syslog.LOG_INFO, "rsynct:rsyncupload:  ERR %s " % (rsync_message))
                rsync_message = "rsynct:code 1, syntax error, failed rsync executed in %0.2f seconds"

            elif ("code 23" and "Read-only file system") in stroutput:
                # read-only file system
                # sadly, won't be detected until after first succesful transfer
                # but it's useful then!
                if wdebug >= 1:
                    syslog.syslog(syslog.LOG_DEBUG, "rsynct:rsyncupload: rsync code 23 - %s" % stroutput)
                syslog.syslog(syslog.LOG_INFO, "rsynct:  ERR Read only file system ! FIX ME !")
                rsync_message = "rsynct:code 23, read-only, rsync failed executed in %0.2f seconds"
            elif ("code 23" and "link_stat") in stroutput:
                # likely to be that a local path doesn't exist - possible typo?
                if wdebug >= 1:
                    syslog.syslog(syslog.LOG_DEBUG, "rsynct:rsyncupload: rsync code 23 found %s" % stroutput)
                rsync_message = "rsynct:rsync code 23 : is %s correct? ! FIXME !" % (rsynclocalspec)
                syslog.syslog(syslog.LOG_INFO, "rsyncupload:  ERR %s " % rsync_message)
                rsync_message = "rsynct:code 23, link_stat, rsync failed executed in %0.2f seconds"

            elif "code 11" in stroutput:
                # directory structure at remote end is missing - needs creating
                # on this pass. Should be Ok on next pass.
                if wdebug >= 1:
                    syslog.syslog(syslog.LOG_DEBUG, "rsynct:rsyncupload: rsync code 11 - %s" % stroutput)
                rsync_message = "rsynct:rsync code 11 found Creating %s as a fix?" % (rsync_rem_dir)
                syslog.syslog(syslog.LOG_INFO, "rsyncupload: %s"  % rsync_message)
                # laborious but apparently necessary, the only way the command will run!?
                # build the ssh command - n.b:  spaces cause wobblies!
                if self.server == 'localhost':
                    cmd = ['mkdir']
                    cmd.extend(['-p'])
                    cmd.extend(["%s" % rsyncremotespec])
                    if wdebug >= 2:
                        syslog.syslog(syslog.LOG_DEBUG, "mkdircmd %s" % cmd)
                    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    rsync_message = "rsynct:code 11, rsync mkdir cmd executed in % 0.2f seconds"
                else:
                    cmd = ['ssh']
                    cmd.extend(["%s@%s" % (self.user, self.server)])
                    mkdirstr = "mkdir -p"
                    cmd.extend([mkdirstr])
                    cmd.extend([rsync_rem_dir])
                    if wdebug >= 2:
                        syslog.syslog(syslog.LOG_DEBUG, "sshcmd %s" % cmd)
                    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    rsyncremotespec = rsync_rem_dir
                    rsync_message = "rsynct:code 11, rsync mkdir cmd executed in % 0.2f seconds"
                rsync_message = "rsynct:rsync executed in %0.2f seconds, built destination (remote) directories"
            elif ("code 12") and ("Permission denied") in stroutput:
                if wdebug >= 1:
                    syslog.syslog(syslog.LOG_DEBUG, "rsynct:rsyncupload: rsync code 12 - %s" % stroutput)
                rsync_message = "rsynct:Permission error in rsync command, probably remote authentication ! FIX ME !"
                syslog.syslog(syslog.LOG_INFO, "rsynct:rsyncupload:  ERR %s " % (rsync_message))
                rsync_message = "rsynct:code 12, rsync failed, executed in % 0.2f seconds"
            elif ("code 12") and ("No route to host") in stroutput:
                if wdebug >= 1:
                    syslog.syslog(syslog.LOG_DEBUG, "rsynct:rsyncupload: rsync code 12 - %s" % stroutput)
                rsync_message = "rsynct:No route to host error in rsync command ! FIX ME !"
                syslog.syslog(syslog.LOG_INFO, "rsynct:rsyncupload:  ERR %s " % (rsync_message))
                rsync_message = "rsynct:code 12, rsync failed, executed in % 0.2f seconds"
            else:
                syslog.syslog(syslog.LOG_ERR, "rsynct:ERROR: rsyncupload: [%s] reported this error: %s" % (cmd, stroutput))

        if self.log_success:
            if wdebug == 0:
                to = ''
                rsyncremotespec = ''
            else:
                to = ' to '
            t2= time.time()
            syslog.syslog(syslog.LOG_INFO, "rsyncupload: %s" % rsync_message % (t2-t1) + to + rsyncremotespec)


if __name__ == '__main__':

    # To run this manually it's best to construct a minimalist, renamed
    # weewx.conf file, with (possibly) modified skin files, and run that
    # to test this script with :-
    #
    # wee_reports /etc/weewx/weewx-test.conf
    #
    # The report_timing stanza is ignored when testing with wee_reports -
    # everything else will be actioned on though.
    #
    # Running this directly returns an error
    #$ PYTHONPATH=/usr/share/weewx python /usr/share/weewx/weeutil/rsyncupload.py
    #   Traceback (most recent call last):
    #  File "/usr/share/weewx/weeutil/rsyncupload.py", line 23, in <module>
    #    import weewx.engine
    #  File "/usr/share/weewx/weewx/engine.py", line 26, in <module>
    #    import weewx.accum
    #  File "/usr/share/weewx/weewx/accum.py", line 12, in <module>
    #    from weewx.units import ListOfDicts
    #  File "/usr/share/weewx/weewx/units.py", line 15, in <module>
    #    import weeutil.weeutil
    #ImportError: No module named weeutil

    import weewx
    import configobj

    wdebug = 2
    syslog.openlog('rsyncupload', syslog.LOG_PID|syslog.LOG_CONS)
    syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_DEBUG))

    if len(sys.argv) < 2:
        #print Usage: rsyncupload.py path-to-configuration-file [path-to-be-rsync'd]
        sys.exit(weewx.CMD_ERROR)

    try:
        config_dict = configobj.ConfigObj(sys.argv[1], file_error=True)
    except IOError:
        #print "Unable to open configuration file ", sys.argv[1]
        raise

    if len(sys.argv) == 2:
        try:
            rsync_dir = os.path.join(config_dict['WEEWX_ROOT'],
                                     config_dict['StdReport']['HTML_ROOT'])
        except KeyError:
            #print "No HTML_ROOT in configuration dictionary."
            sys.exit(1)
    else:
        rsync_dir = sys.argv[2]

    rsync_transfer = Rsynct(rsync_dir, **config_dict['StdReport']['RSYNC'])
    rsynctransfer()
    
