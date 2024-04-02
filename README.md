# weewx-rsynctransfer

This service is basically the weewx RSYNC report, ripped out and adjusted to accept further options / configuration.

It was born out of the need for a simple way to reliably backup the [weewx](http://weewx.com) sqlite database - constantly or as near to constantly as paranoia dictates, for the [rorpi project hosted here](https://github.com/glennmckechnie/rorpi-raspberrypi). 
This backup method uses the hidden 'feature' of  the existing weewx RSYNC skin and is outlined at [Using weewx's RSYNC skin as a backup solution](https://github.com/glennmckechnie/rorpi-raspberrypi/wiki/rorpi-Using-weewx's-RSYNC-skin-as-a-backup-solution)

Of note: weewx's StdReport runs after records are archived. The RSYNC skin runs under the StdReport service. This goes a long way towards ensuring a usable file, ie: database transactions should be null, the copy should be as good as the original.

This rejig of RSYNC is so that...

* the added ability to save to deeper than one level which was missing in the original, it forced 'single depth' only.  This is required for the purpose of syncing report data with a webserver. ie: paths can now end with***out*** a slash '/'

* It adds the ability to specify recursive directories - you can save the full path to the remote location.

* It adds the ability to specify dated directories to allow snapshots, <pre> /remote_path/2017/02/16/rsync'd files </pre>

* It adds the ability to save to the localhost eg:- a writable thumbdrive. This is definitely needed for rorpi as that can be configured to have the database in RAM (tmpfs) - which makes it a little fragile without some sort of backup and (retrival process).

* It also performs some added sanity checks. With complexity comes an increase in the chance of misconfiguration, although a few of the checks should help regardless of what RSYNC is used for ( it checks for remote permissions, missing routes, misconfigured local paths, builds remote trees, something else and...

* For full flexibilty, use this in conjunction with weewx's **report_timing option**. See the section on [Customizing the report generation time](http://www.weewx.com/docs/customizing.htm#customizing_gen_time)

***Instructions:***

1. Download the skin to your weewx machine.

    <pre>wget -O weewx-rsynctransfer.zip https://github.com/glennmckechnie/weewx-rsynctransfer/archive/master.zip</pre>

2. Change to that directory and run the weewx extension installer

   for the newer 5.x weewx versions it is now...

   <pre>sudo weectl extension install weewx-rsynctransfer.zip</pre>
   
   or for the older 4.x weewx versions it remains...

   <pre>sudo wee_extension --install weewx-rsynctransfer.zip</pre>

4. Restart weewx

   <pre>
   sudo /etc/init.d/weewx stop

   sudo /etc/init.d/weewx start
   </pre>

