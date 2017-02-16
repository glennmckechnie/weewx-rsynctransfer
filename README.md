# weewx-rsyncbackup
A starting point for an rsync based backup service for weewx.

These files are modified copies of the existing weewwx files.

They are a critical part of weewx and won't survive an upgrade.

Neither are they meant to permanently replace the original files, nor introduce headaches to the core weewx team. 

They are starting point for me to learn python, and incoporate the features I feel a need for (itch, scratch, done).  They may be rolled into a separate user skin in the very near future, or if deemed suitable rolled back into weewx. My crystal ball is fogged at the moment; when it clears I'll know, and then you will. :-)

It was born out of the need for a simple way to reliably backup the [weewx](http://weewx.com) database - constantly or as near to constantly as paranoia dictates, in particular for the [rorpi project hosted here](https://github.com/glennmckechnie/rorpi-raspberrypi). That backup method uses the hidden 'feature' of  the existing weewx RSYNC skin and is outlined at [Using weewx's RSYNC skin as a backup solution](https://github.com/glennmckechnie/rorpi-raspberrypi/wiki/rorpi-Using-weewx's-RSYNC-skin-as-a-backup-solution)

Of note: weewx's StdReport runs after records are archived. The RSYNC skin runs under the StdReport service. This goes a long way towards ensuring a usable file, ie: database transactions should be null, the copy should be as good as the original.

* This adds the ability to save to deeper than one level  (missing in the original which forced 'single depth' only) as required for its original purpose of syncing report data with a webserver. ie: paths can now end with a slash '/'

* It adds the ability to specify recursive directories - you can save the full path to the remote location.

* It adds the ability to specify dated directories to allow snapshots, <pre> /remote_path/2017/02/16/rsync'd files </pre>

* It adds the ability to save to the localhost eg:- a writable thumbdrive. This is definitely needed for rorpi as that can be configured to have the database in RAM (tmpfs) - which makes it a little fragile without some sort of backup and (retrival process)

* It also does some added sanity checks, with complexity comes an increase in the chance of misconfiguration, although a few of the checks should help regardless of what RSYNC is used for ( it checks for remote permissions, missing routes, misconfigured local paths...

* For full flexibilty, use this in conjunction with weewx's **report_timing option**. See the section on [Customizing the report generation time](http://www.weewx.com/docs/customizing.htm#customizing_gen_time)

