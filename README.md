![icon](https://raw.githubusercontent.com/UtrechtUniversity/Labdata_cleanup/RC1/icons/win_incon.ico) 

# Labdata_cleanup (package *labsync*)

Python code to synchronise/clean up lab data after check that all data resides on server.

------------------------------------------------------------------------------------------------------
# Upload data unknown in vault

Get (new) data from lab computers to server using WebDAV protocol.

# Delete data known in vault

Using checksums, figure out which data is already present at remote location and then delete data from workstation.
See the packages, especially *sync.py* for more specifics, like time delta's for reuploads and deletions.

Safekeeping of the algorithm/flow suggested by Ton Smeele:

# Basic algorithm for workstation labsync code
1. Walk tree of directories
  * for file in tree:
     * calculate checksum of file
  * list CHECKSUM_FILEPATH
  * sort list on checksum
  
2. Download checksum file from Remote location
  * sort list in the same way
  
3. Compare lists --> find items that can be deleted)
4. (Prompt user to) Delete lab data files. 
5. Prompt user to warn when there were any errors (Wally ascii art.)

# Implementation conventions for names/files
Hashtype: MD5 ('md5') or SHA256 ('sha2') [checksums](https://en.wikipedia.org/wiki/Hash-based_message_authentication_code)  

Format becomes: HASHTYPE HASHKEY (optional filename) FILESIZE

Thus, for example a line looks like this:

> 'md5 xf7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8 IM_optional.file 42424242'

See also: Yoda_indexfile_format.txt

# Dependencies

- Python3 (Py > 3.3) Tested with 3.5.1 (OSX 10.9.2) and older parts with 3.4.3 (Ubuntu 14.04 LTS) 
- numpy (for numpy record array database results)
- easywebdav (use [Julia's Fork](https://github.com/JuliaPython/easywebdav))
- sqlite3 (Not always correctly installed by default python installation, check it!)

# Soft dependencies
These modules are recommended, but not very important for main functionality 
- pdoc (for nice documentation generation) 
- ipython (for nice interactive shell)

## Setting up a Mac in the lab 

For Mac lab computers (AKA Workstations) there are some things to take into account:
- Some sort of python is by default installed and used on OSX, whatever you do, don't mess with that python version. It's best to setup a completely isolated Python environment. I chose to install Homebrew (http://brew.sh) and set up Python 3 from there, there are of course alternatives.  

For setting up homebrew I followed this instruction (http://coolestguidesontheplanet.com/setting-up-os-x-mavericks-and-homebrew/)

Other requirements then are:

- Xcode + command line tools (App store, annoying by the way)
- Homebrew 

Setting up the basic stuff could then be as easy as:

```
    brew install python3  
    pip3 install ipython
    pip3 install numpy    
    pip3 install git+git://github.com/JuliaPython/easywebdav
    pip3 install pdoc
```

## Setting up a Windows box in the lab

Set up a completely *new python 3.5.1*, Download the executable installer from [here](https://www.python.org/downloads/release/python-351/) and take care of the following:

If you want to plug a new PC in the lab, you do *not* want a default installation in \<your_user\> AppData, select the custom installation and proceed:

- In the first window (Optional Features), check **all** boxes.
- In the second window (Advanced Options), make sure that the following items are checked:
    - Install for all users
    - Associate files with python
    - Add Python to environment variables
    - Precompile standard library.
 - Check that the location for installation is like here:
         
   > C:\Program Files\Python35
   
 Then continue installing it.
 
A restart might be wise now, next, I suggest installing this [Git for windows](https://git-for-windows.github.io/), so you can use pip from the bash shell, too. Otherwise, you need to install the dependencies manually, which can may be sort of a drag for the fork of easywebdav.

Install Git for windows with all defaults suggested, they are fine.

Now, for win versions newer than win 7, you need some additional steps to make things easy: find the Git folder in your all apps list, select the GIT bash app, right click and pin it to your start menu. 

Then, when you want to use the bash shell for installations of the dependencies, you need to run it as administrator, else you will get into permission errors. So, right click GIT bash from your fresh shortcut block, then select 'more' and select "Run as Administrator".

The bash shell pops up. You can now:  

```
    pip3 install ipython
    pip3 install numpy
    pip3 install git+git://github.com/JuliaPython/easywebdav
    pip3 install pdoc
```


Installing package *labsync*
----------------------------

You can check out the release candidate [RC1 branch from github](https://github.com/UtrechtUniversity/Labdata_cleanup/tree/RC1). You can do  it manually, download the zip etc via Github, or via terminal (mac) or via the bash shell (windows) using this command:

```
    git clone https://github.com/UtrechtUniversity/Labdata_cleanup.git -b RC1
```

Then continue like so:

```
    cd /path/to/Labddata_cleanup  #where you cloned the git repos
    cd labsync
    pip3 install --upgrade .
```

The **structure** of Labdata_cleanup (branch RC1) is:

```
    Labdata_cleanup/
        .gitignore
        example_config.cfg.txt ---------- *
        README.md
        Yoda_indexfile_format.txt
        labsync/
            checksums.txt <-------------- **
            Labdata_cleanup.log <-------- **
            mac7.cfg <------------------- ***
            mac7db.sqlite <-------------- ***
            setup.py
            docs/ <---------------------- Documentation
                labsync/ 
                    checksum.m.html
                    database.m.html
                    index.html
                    settings.m.html
                    tps.m.html
                    yoda_helpers.m.html
            labsync/ <------------------- Code package
                __init__.py
                __main__.py
                checksum.py
                database.py
                settings.py
                sync.py 
                tps.py
                yoda_helpers.py           
     
     
     Notes:
     ------
                
     *   You have to hand edit this one, save as .cfg and put it in the first labsync folder
     **  This file only appears after all is in use and correctly installed.
     *** These files you are about to create to make it all work   
 ```
 
# Creating the package using setup.py

The package can be installed like this:

```
	cd path-to-Labdata_cleanup #git repos
	cd labsync
	pip3 install --upgrade .
``` 

Note that it is now installed in your site-packages folder. Any changes in the code will not have any effect once you've installed it this way, you will need to install it again. Usually after any new major edits, I will update the version number in setup.py, so you can easlily check that.  
 
# Extra git help: accept all changes
 
In the process of testing this software, It might be best to accept changes I make after the tester found issues. GIT is not a centralised version management system, so it does not automatically overwrite any of your local files under revision, while this is usually what a tester (who is not necesarily a developer) wants. 

I've found the following info [here](https://stackoverflow.com/questions/1125968/how-do-i-force-git-pull-to-overwrite-local-files). In order to accept my latest pushed edits, issue the following commands:

```
	cd path-to-Labdata_cleanup #git repos
	git fetch --all
	git reset --hard origin/RC1
``` 

------------------
##### Note! After accepting all recent edits from GitHub, you must also install the package again. See info above.
------------------ 

# Documentation generation
Create the whole package's documentation (from the same location as the package creation directory)like so:
```
	pdoc --html --html-dir docs --only-pypath --external-links --overwrite ./labsync
```
 
             
Creating configuration file and database
----------------------------------------
Copy the file example_config.cfg.txt from Labdata_cleanup.
Edit the name to reflect your workstation ID, e.g. mac7.cfg, dell3,cfg and *make sure the.txt extension is removed* from the filename. 
Assuming your name is 'Wil de Bras', here is an example given 'Mac 7' as ID and the YODA *acceptance* domain:

```
    [Connection]
    domain: acc.youth.data.uu.nl
    username: Wil
    name: Wil de Bras
    email: W.I.L.deBras@uu.nl 
    pass: geheimpaswoordaanvragwenviayoda #need this
    port: 443
    proto: https
    usessl: true
    path: /
    
    [LocalFolders]
    data_dir:/Users/cid/Documents/YOUth/kkc_tasks/trunk/DATA/ #usual location for mac
    
    [LocalID]
    box_id: mac7 #edit, all small
    
    [RemoteFolders]
    list_dir: /grp-datamanager-youth
    put_dir: /grp-intake-youth
    
    [LocalDataBase]
    database: mac7db.sqlite
    
    [CHECKSUM_PATH]
    checksum_file = /grp-datamanager-youth/checksums.txt
    
    # New other "fixed" settings for data & types, do not edit values below here
    
    [TEST_DATA_DIR]
    test_fake_trash = TEST_FAKE_TRASH
    test_data_dir = TEST
```

Now save it to the (first) labsync folder, the one where setup.py resides.   
**Note**: Inside is another folder called labsync, that is the package itself, don't touch it!
Next, build the database.

You need a sqlite database to connect to and keep sync results in. Proceed using **python/ipython** shell from the(first) 'labsync' folder in the location where you installed the package and do:

```
    import labsync.database  
    labsync.database.build_db('mac7db.sqlite')  
```
And make sure that it give no error messages, but returns: 

```
    The database ma7db.sqlite was created
```

Now, if all went well, you can start using the package!
Start a **(I)python** test sync run like this (same location: in folder labsync where setup.py resides):

```
    import labsync.sync
    labsync.sync.main(testing=True)
``` 

Code documentation
------------------
For now, this resides only in docs as html files (download them to view), soon online through a VM.

You might as well create it yourself using pdoc:

```
    pdoc --html --html-dir docs --only-pypath --external-links --overwrite ./labsync 
```

Mailing 
-------

From RC1 version 0.24review and onwards, a UU-specific mailing system is implemented. This is a higly UU-specific method, using telnet. The interaction within telnet is automated using the 'pexpect' module. If this code should at some point be implemented at UMCU, we'd need to think up a different system, or so it seems. Within the UU 'ethernet' (aka 'Wired') network, this should always work, elsewhere this mailing system will fail.

You need a telnet client, which is not by default configured on windows, follow [this](https://www.rootusers.com/how-to-enable-the-telnet-client-in-windows-10/) link for some instructions, at least under win10.  


Quick example for testing WebDav connection:
--------------------------------------------

```
	wolk:Labdata_cleanup jacco$ ipython
	iPython 3.5.1 (default, Feb 16 2016, 12:04:52) 
	Type "copyright", "credits" or "license" for more information.

	IPython 4.1.1 -- An enhanced Interactive Python.
	?         -> Introduction and overview of IPython's features.
	%quickref -> Quick reference.
	help      -> Python's own help system.
	object?   -> Details about 'object', use 'object??' for extra details.
	
	In [1]: import easywebdav
	In [2]: webdav = easywebdav.connect('acc.youth.data.uu.nl', username='i.nitial@uu.nl', password='secret', path='/', protocol='https')
	In [3]: webdav.ls()
	Out[3]: 
	[File(name='', size=0, mtime='Sun, 28 Jan 2007 16:00:00 GMT', ctime='Sun, 28 Jan 2007 16:00:00 GMT', contenttype='httpd/unix-directory', contentlength=None, is_dir=True),
 	File(name='/grp-datamanager-youth', size=0, mtime='Mon, 02 May 2016 15:29:33 GMT', ctime='Mon, 29 Feb 2016 08:57:35 GMT', contenttype='', contentlength=None, is_dir=True),
 	File(name='/grp-intake-youth', size=0, mtime='Wed, 30 Mar 2016 13:29:30 GMT', ctime='Mon, 29 Feb 2016 08:56:57 GMT', contenttype='', contentlength=None, is_dir=True),
 	File(name='/grp-vault-youth', size=0, mtime='Mon, 29 Feb 2016 08:57:23 GMT', ctime='Mon, 29 Feb 2016 08:57:23 GMT', contenttype='', contentlength=None, is_dir=True),
 	File(name='/j.c.vanelst@uu.nl', size=0, mtime='Thu, 18 Aug 2016 13:32:10 GMT', ctime='Thu, 18 Aug 2016 13:32:10 GMT', contenttype='text/plain', contentlength=None, is_dir=True),
 	File(name='/public', size=0, mtime='Sun, 28 Jan 2007 16:00:00 GMT', ctime='Sun, 28 Jan 2007 16:00:00 GMT', contenttype='', contentlength=None, is_dir=True)]
```

Extra's on windows and mac: Icons.
---------------------------------

Create a new shortcut that executes the sync routine, add this to the name:
```
	C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -command cd C:\Users\<your-user-name>\Documents\YOUth\Labdata_cleanup\labsync\; python labsync
```
And woops, it is an executable shortcut.

On a mac, i really enjoyed answer 5 (no upvotes, but very nice) from [here](http://stackoverflow.com/questions/281372/executing-shell-scripts-from-the-os-x-dock) to have a nice icon with sync stuff.

Shell commands should be like this:
```
	#! /bin/bash
	cd /Users/<you>/Documents/YOUth/Labdata_cleanup/labsync 
	/usr/local/bin/python3 labsync
```

Now, if you want to make thingss really fancy, look in the 'icons' folder for nice shortcut images to the script. Sorry about that.

Notes
-----

Before, not specifying the protocol (https/http) was not an issue, since recent (2016_09_21), you need to specify this explicitly in order to connect/upload/download.

*Ipython* is a development environment. Under windows, the getpass() function, when run from ipython does not behave as is should: it actually displays the characters of your password. In production, the software will be run using either windows Powershell or the regular windows command prompt, so this will not be an issue anymore. 


Running Tests (tps)
-------------------

There are some test functions in **tps.py**, but, they are aimed at Test Procedure Specification Purposes only, and are in the scope of the entire system (sync utils + Yoda portal + Yoda disk, etc,) You'd need the TPS document to make sense of it, and require credentials for the Yoda acceptance environment.

Without proper config files and a sqlite database and such, you will not get very far with this code,

JvE on 2017-08-03T10:55

 
