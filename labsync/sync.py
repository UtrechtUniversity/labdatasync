"""
Synchronize lab workstation data with a grid storage server (YODA).

# Definitions

- *WEPV* : Wave + Experiment + Pseudocode + Version file naming and type identification 
    standard.
- *YODA* : Grid based storage server.
- *VAULT*: Part of YODA where data resides when approved and checked by Data manager.
- *INTAKE*: Web interface to YODA where files/sets are being approved or not.

# Flow
1. Download file with paths and checksums of data in the 'vault'  
2. Compare local (lab data) files with checksums from vault.  
3. If any local files are found with checksums not in the list:  
    + Upload file to YODA intake area.  
    + Update local (sqlite3) database with upload info.  
4. If any local files are found that are already at vault location:  
    + Update local (sqlite3) database with 'trashed' info.  
    + Delete the files once they've been in the trash for long enough.  
5. If local files are found that are not new, they are are uploaded again just as 
    long as they are not in the vault list they will reside in limbo and their upload 
    counts and dates are updated. 
6. Don't delete data sets for which holds that on or more of the files in 
    it's WEPV directory are 'known' by remote server, (i.e. their checksum and local
    database checksum are known) but which one or more file names doen not match in
    the database.  
7. Log everything  

# Package creation
The package is made like this:

    $ cd path-to-labdatasync #git repos
    $ pip3 install --upgrade .
        
# Documentation generation
Create the whole package's documentation like so:

    $ pdoc --html --html-dir docs --only-pypath --external-links --overwrite ./labsync 
    
"""

import configparser
import datetime as dt
import getpass
import logging
import logging.handlers  # for rotating logs
import ntpath
import os
import posixpath
import random
import re
import shutil
import socket
import sys
import threading
import time

import easywebdav as dav
import numpy as np
# RC1 edits: central package version comes in db
import pkg_resources  # part of setuptools
from labsync import checksum as cs
from labsync import database as db
# our own modules
from labsync import settings
from labsync import yoda_helpers as yh

__version__ = pkg_resources.require("labsync")[0].version
__email__ = 'j.c.vanelst@uu.nl'
__authors__ = ['Jacco van Elst', 'Julia Brehm']

# want to exclude e.g. the settings documentation?, (un)comment lines below
__pdoc__ = {}
__pdoc__['settings'] = None


def getConfigFile():
    """
    Find configuration file, return a filename.
    
    **Notes**  
    ---------- 
    For our specific setup we often require either 
    dell<1-6>.cfg or mac<1-9>.cfg as file names.  
    
    **Returns**
    -----------
    config_filename: str  
        *Name of config file.*    
    """
    config_files = []
    for file in os.listdir():
        if file.endswith('.cfg'):
            if 'dell' in file or 'mac' in file or 'lenovo' in file or 'hp' in file:
                config_files.append(file)
    if not config_files:
        print('Configuration file missing! Either "dell<1-9>.cfg" or "mac<1-9>.cfg"')
        print('Needs to be in this folder: ' + os.getcwd())
        sys.exit()
    elif len(config_files) > 1:
        print('Specify the file you want to use for config by typing a file name: ')
        for name in config_files:
            print(name)
        config_filename = input()
        while config_filename not in config_files:
            print('Oops something went wrong! Typo? Try again:')
            config_filename = input()
    else:
        config_filename = config_files
    return config_filename


############ Compile the important regex for WEPV ########################################
# aa = "^[ab](\d{5})_(\d{1,2})[ym]_([a-z]{5,10})(_)([0-9]{4})(1[0-2]|0[1-9])"
# bb = "(3[01]|0[1-9]|[12][0-9])(_)([01]?[0-9]|[0-9])[0-5][0-9].+"
# mega = aa + bb
# WEPV = re.compile(mega, re.IGNORECASE)
# A WEP(V) format in the form like "B12345_3Y_experiment_".
WEPV = re.compile(r'[AB]\d{5}_\d{1,2}[YM]_[a-z]{2,15}_', re.IGNORECASE)
"""
WEPV regular expression in compiled form.
"""

############ Set up logging ##############################################################
logger = logging.getLogger('Labdata_cleanup')
"""
Logging.
"""
logger.setLevel(logging.INFO)
fh = logging.handlers.TimedRotatingFileHandler("Labdata_cleanup.log",
                                               when="w0", interval=1, backupCount=0)
logger.addHandler(fh)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

############ Global debug settings #######################################################

DEBUG = True
MAIL = True
DEBUGDB = False  # database queries in logger, we don't want it all the time

"""
General debug setting, print some extra stuff when True.
"""

############  Figure out OS, settings and ID's ##########################################
myos = os.name
gconf = configparser.ConfigParser()

confname = getConfigFile()
gconf.read(confname)
gconf.sections()

# parse gconf for hostname etc, figure out some stuff about the system
full_hostname = socket.gethostname()
if myos == 'posix':
    stuff = full_hostname.split('.')
    hostname = stuff[0]
    network = ".".join(stuff[1:]).lower()
    mac = True
else:
    hostname = full_hostname  # win: no splits
    network = None
    mac = False

if mac:
    # some extra checks on hostnames: should be .local or .soliscom.uu.nl on macs
    if network != 'local' or network != 'soliscom.uu.nl':
        logger.warning("Hostname is not 'local' or 'soliscom', but: " + str(network))

# Get box_id from configuration file.
box_id = gconf["LocalID"]["box_id"]

# Compare box_id to hostname. They have to be equal.
if not box_id.lower() == hostname.lower():
    message = "Host name '" + hostname + "' not equal to box-id '" + box_id + "'."
    print(message)
    logger.error(message)
    raise ValueError(message)

if DEBUG:
    print("Official workstation ID:", box_id)
    print("Current 'labsync' package version:", __version__)

############### Set up test directories for datasets and delete-folder #################

t1 = gconf['TEST_DATA_DIR']['test_data_dir']
t2 = gconf['TEST_DATA_DIR']['test_fake_trash']

if myos == 'nt':
    if not ntpath.exists(t1):
        try:
            os.mkdir(ntpath.normpath(t1))
        except:
            print("Could not create directory: ", t1)
            raise OSError("Could not create directory: ", t1)
    if not ntpath.exists(t2):
        try:
            os.mkdir(ntpath.normpath(t2))
        except:
            print("Could not create directory: ", t2)
            raise OSError("Could not create directory: ", t2)

elif myos == 'posix':
    if not posixpath.exists(t1):
        try:
            os.mkdir(posixpath.normpath(t1))
        except:
            print("Could not create directory: ", t1)
            raise OSError("Could not create directory: ", t1)
    if not posixpath.exists(t2):
        try:
            os.mkdir(posixpath.normpath(t2))
        except:
            print("could not create directory: ", t2)
            raise OSError("Could not create directory: ", t2)


############## End of settings and specifics at startup ################################

# class cSpinner(threading.Thread):
#     """
#     Present a spinner while waiting.
#     """
#
#     def run(self):
#         self.stop = False
#         self.kill = False
#         print('Please wait...   ', end=' ')
#         sys.stdout.flush()
#         i = 0
#         while not self.stop:
#             if (i % 4) == 0:
#                 sys.stdout.write('\b/')
#             elif (i % 4) == 1:
#                 sys.stdout.write('\b-')
#             elif (i % 4) == 2:
#                 sys.stdout.write('\b\\')
#             elif (i % 4) == 3:
#                 sys.stdout.write('\b|')
#             sys.stdout.flush()
#             time.sleep(0.1)
#             i += 1


############### Errors/Exceptions tryout ################################################

class ConnectionError(Exception):
    """ Basic connection error."""


class MaxRetriesError(ConnectionError):
    """ You entered the wrong credentials more than 3 times"""


class MailingError(Exception):
    """ Mailing system seems broken."""


############### GUI/Feedback ############################################################
# if all goes well
reward_banner = r"""

          _
         /(|                        /
        (  :                       /
       __\  \  ___________________/
     (____)  `|
    (____)|   |  ALL IS AWESOME!
     (____).__|
      (___)__.|_____________________/


"""
"""
Thumb up ASCII art when all is well.
"""

# if any stuff went wrong or needs attention
hell_banner = r"""


      .----.
     /___.--'-.     shit hit the fan
     C   '----'
     |       )   .-----.
     |     .|   /_     /
     '''----'  /  )   /
     /       \/'..'__/
    /        /   /
   /            /
               /\~~)__________
                 \(___________)


"""
"""
Wally ASCII art when errors are encountered.
"""


#########################################################################################

def connect(config):
    """
    Connect to server based on config file parameters and/or user input.
    
    **Parameters**
    ---------------
    config: object  
        *Configparser object.*  
    
    **Returns**
    -----------
    wbdv: object  
        *Webdav connection object.*  
    """
    # connect to server
    success = False
    max_retries = 3
    retries = 0
    messages = []
    users_tries = []
    while retries < max_retries and not success:
        domain = config.get('Connection', 'domain')
        print("Logging in at " + domain)
        # user = config.get('Connection', 'username')
        user = input("Solis-id (e-mail address): ")  # prod
        # pword = config.get('Connection', 'pass')
        pword = getpass.getpass('Password: ')  # prod
        proto = config.get('Connection', 'proto')  # @new, MUST now be specified!
        dest_path = config.get('Connection', 'path')
        box_id = config.get('LocalID', 'box_id')
        port = 443  # we must use this one too, or the ls() method fails
        wbdv = dav.connect(domain, username=user, password=pword,
                           protocol=proto, port=port, path=dest_path)
        try:
            wbdv.ls()
            success = True
        except Exception as e:
            success = False
            print('Cannot connect, please try again...')
            print("This was attempt:", retries + 1)
            messages.append(e)
            users_tries.append(user)
            time.sleep(0.3)
        retries += 1
    if not success:
        logger.info("Webdav connection failed ... these were the errors.")
        for m in messages:
            logger.info(m)
        logger.info("This is the list of users that tried to connect:")
        for u in users_tries:
            logger.info(u)
        if retries >= max_retries:
            try:
                raise MaxRetriesError("Login failed too many times.")
            finally:
                print("Please try again later")
                time.sleep(2.0)
                sys.exit()
        else:
            try:
                raise ConnectionError("Cannot connect...")
            finally:
                print("Please try running the program again. Quitting")
                time.sleep(2.0)
                sys.exit()
    else:
        print("Connected to " + domain)
        logger.info("Webdav connection established from local computer " + box_id +
                    " to " + domain + ", instantiated with credentials of lab user " +
                    user)
        return wbdv


def download_hash_list(config, config_filename, server):
    """
    Download file with indexes of files found in vault and return lists.
    
    **Parameters**
    --------------
    config: Object  
        *Configparser object.*  
    config_filename: str  
        *Path to config file.*  
    server: Object  
        *Easywebdav instantiated class object.*  
    
    **Returns**
    -----------
    download_list: list  
        *A list of vault files/indices as downloaded from YODA.*  
    md5_list: list  
        *Sub list from the index files that have been checksummed with 
        MD5 algorithm.*  
    sha256_list list: list  
        *Sub list from the index files that have been checksummed with 
        SHA256 algorithm.*  
    """
    config.read(config_filename)
    save_loc = '.'
    checksum_file = config.get('CHECKSUM_PATH', 'checksum_file')
    # remote pathnames always posix.
    remote_checksumfile = checksum_file
    local_checksumfile = os.path.join(save_loc, 'checksums.txt')
    # local can be 'nt' or 'posix', let's normalise stuff
    if myos == 'nt':
        local_checksumfile = ntpath.normpath(local_checksumfile)
    server.download(remote_checksumfile, local_checksumfile)
    with open(local_checksumfile, 'r') as curr_file:
        download_list = curr_file.readlines()
    download_list = [i.split() for i in download_list if not i[0] == '#']
    md5_list = [i for i in download_list if 'md' in i[0]]
    sha256_list = [i for i in download_list if 'sha' in i[0]]
    return download_list, md5_list, sha256_list


def comp2localchecksum(config, config_filename, md_list, sha_list, testing):
    """
    Creates indexfile list of local files.
    
    **Parameters**
    ----------
    config: Object  
        *Configparser object.*  
    config_filename: str  
        *Path to config file.*  
    md_list: list  
        *List with md5 checksums.*   
    sha_list: list  
        *List with sha256 checksums.*  
    
    **Returns**
    -------
    files2delete: list  
        *List of files to upload.*  
    files2upload: list  
        *List of files marked for deletion.*  
    
    **See Also**  
    ------------
    `labsync.checksum.make_hash_string`
    """
    files2upload = []
    files2delete = []
    md_checksums = [i[1] for i in md_list]
    sha_checksums = [i[1] for i in sha_list]
    config.read(config_filename)
    source_path = config.get('LocalFolders', 'data_dir')
    if testing:
        source_path = config.get('TEST_DATA_DIR', 'test_data_dir')
    upload_db = config.get('LocalDataBase', 'database')
    hash_list = []
    for (dirpath, dirnames, filenames) in os.walk(source_path):
        if myos == 'nt':
            filenames = [f for f in filenames if not f[0] == '.' and not
            str(f) == ntpath.basename(upload_db)]
        elif myos == 'posix':
            filenames = [f for f in filenames if not f[0] == '.' and not
            str(f) == posixpath.basename(upload_db)]
        else:
            print("What OS are you on?, this support windows, MacOSX and Linux/Unix")
            raise OSError
        dirnames[:] = [d for d in dirnames if not d[0] == '.']  # skip hidden .DS_Store etc.
        for file in filenames:
            if myos == 'nt':
                file_path = ntpath.join(dirpath, file)
            elif myos == 'posix':
                file_path = posixpath.join(dirpath, file)
            else:
                print("What OS are you on?, support for windows, MacOSX and Linux/Unix")
                raise OSError
            if os.path.isfile(file_path) and not file_path.endswith('~'):
                hash_str1 = cs.make_hash_string(file_path, 'SHA256')
                hash_str1 = hash_str1.split()
                if hash_str1[1] in sha_checksums:
                    files2delete.append((file_path, hash_str1[1], 'sha2'))
                else:
                    hash_str2 = cs.make_hash_string(file_path, 'MD5')
                    hash_str2 = hash_str2.split()
                    if hash_str2[1] in md_checksums:
                        files2delete.append((file_path, hash_str2[1], 'md5'))
                    else:
                        files2upload.append((file_path, hash_str1[1], 'sha2'))
    return files2upload, files2delete


def sort_list(hash_list):
    """
    Sort list made from index files based upon hash keys.
    
    **Parameters**
    --------------
    hash_list: list  
        *Indexfile as list.*  
    
    **Returns**
    -----------
    hash_list  
        *The **sorted** list*  
    """
    hash_list.sort(key=lambda x: x[1])  # sort list based on hashkeys (at pos 1)
    return hash_list


def compare(local_list, vault_list):
    """
    Compare two lists based on hash keys.
    
    **Parameters**
    --------------
    local_list: list  
        *List of files from workstation (local).*  
    vault_list: list  
        *List of files from vault (remote)*  
    
    **Returns**
    -----------
    files2delete: list  
        *List with files marked for deletion from local workstation (lab computer).*  
    files2upload: list      
        *List with files marked for uploading to intake.*  
    """
    temp_vault_list = vault_list
    temp_local_list = local_list
    files2upload = []
    files2delete = []
    for local_file in temp_local_list:
        local_hash = local_file[1]
        if temp_vault_list:
            for remote_file in temp_vault_list:
                remote_hash = remote_file[1]
                if local_hash == remote_hash:
                    files2delete.append(local_file[3])
                    del temp_vault_list[0]
                    break
                elif local_hash > remote_hash:
                    for counter, remote_file in enumerate(temp_vault_list):
                        remote_hash = remote_file[1]
                        if local_hash == remote_hash:
                            files2delete.append(local_file[3])
                            del temp_vault_list[0:counter + 1]
                            break
                        elif local_hash < remote_hash:
                            files2upload.append(local_file[3])
                            del temp_vault_list[0:counter]
                            break
                    break
                elif local_hash < remote_hash:
                    files2upload.append(local_file[3])
                    break
        else:
            files2upload.append(local_file[3])
    return files2delete, files2upload


def bytesto(bytes_in, to, bsize=1024):
    """
    Convert bytes to megabytes, gigabytes, etc.
    
    **Parameters**
    -------------
    bytes: int  
        *Byte size.*  
    to: str  
        *This: 'k/m/g/t/p/e' (representing kilo, mega, giga, terra, peta, exa).*  
    bsize: int  
        *Number of bytes, defaults to 1024*  
    
    **Returns**
    -----------
    r: float  
        *The converted value.*  
    """
    a = {'k': 1, 'm': 2, 'g': 3, 't': 4, 'p': 5, 'e': 6}
    r = float(bytes_in)
    for i in range(a[to]):
        r = r / bsize
    return r


def isotime_to_obj(iso_string):
    """
    Convert isoformat string of type '2016-09-22T15:37:20.931850' to datetime object.
    
    **Parameters**
    --------------
    iso_string : str  
        *ISO (8601) formatted time string.*  
    
    **Returns**  
    -----------
    object  
        *A datetime.datetime object.*  
    """
    return dt.datetime.strptime(iso_string, '%Y-%m-%dT%H:%M:%S.%f')


def strfdelta(tdelta, fmt):
    """ 
    Helps formatting timedelta objects.
    
    **Parameters**
    --------------
    tdelta: object  
        *A datetime delta object.*  
    fmt: dictionary  
        *A format dictionary specification.*  
    
    **Returns**
    -----------
    fmt.format(**d): str
        *A string format for the timedelta object.*  
    """
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


def sync(server, config, files2upload, files2delete, reupload_delta,
         wait_until_delete_delta, testing=False, implement_test=True):
    """ 
    Database synchronisation routine.
    
    The database sync script that does most of the integrating work, i.e. connecting, 
    logging, interacting with the database, checking, comparing local with
    remote checksums and eventually deleting local files that are known to be in the 
    vault. Also, some basic feedback/UI aspects happen here.
    
    **Parameters**
    --------------
    server: object  
        *Easywebdav instantiated class/object.*  
    config: object  
        *Configparser object.*  
    files2upload: list  
        *A list of files that are not found in the vault.*  
    files2delete: list  
        *A list of files that are found in the vault.*  
    reupload_delta: object  
        *Datetime delta object that controls when to reupload locally 
        'know files' or not.*  
    wait_until_delete_delta: object  
        *Datetime delta object that controls when to actually 
        delete data from the local lab computer or not.*  
    testing: boolean  
        *If True, use only TEST and TEST_FAKE_TRASH instead of real data
        locations for sync tests.*  
    implement_test : boolean
        *If True, use TEST_FAKE_TRASH to move data to instead of deleting,
        but do use the regularly specified data path as configured in cfg.*
        
    
    **Notes** 
    ---------
    Possibly confusing: the lists 'files2delete' and 'files2upload' are checked
    here against much stricter requirements, see the main script for the more 
    general I/O flow. Actual deletion of files does not happen from within here.  
    
    
    **See Also**
    ------------
    `labsync.main`  
    
    **Returns**
    -----------
    upped: list  
        *Uploaded files.*  
    totrashlist: list  
        *Files to trash for the first time.*  
    toretrashlist: list  
        *Files to trash again (if someone has put them back from trash).*  
    warnlist: list  
        *Warnings(type 1)*  
    warnlist2: list  
        *Warnings(type 2)*  
    dberror: boolean  
        *If any db errors were encounterd: True, else: False.*  
    """
    sql_codes = []
    logger = logging.getLogger("Labdata_cleanup.sync")
    # parse for local db info
    upload_db = config.get('LocalDataBase', 'database')
    box_id = config.get('LocalID', 'box_id')
    lab_id = config.get('LocalID', 'lab_id')
    # initiate the database class like so:
    mydb = db.dbManager(upload_db, debug=DEBUGDB)
    local_data_prefix = config.get('LocalFolders', 'data_dir')
    if testing:
        local_data_prefix = config.get('TEST_DATA_DIR', 'test_data_dir')
    remote_data_dir = config.get('RemoteFolders', 'put_dir')
    # path normalisations, extra verbose
    if myos == 'nt':
        local_data_prefix = ntpath.normpath(local_data_prefix)
    if myos == 'posix':
        local_data_prefix = posixpath.normpath(local_data_prefix)
    # check if the subfolder in remote 'put_dir' exists according to plan
    check_it = posixpath.normpath(posixpath.join(remote_data_dir, lab_id))
    test = server.exists(check_it)
    if not test:
        logger.info("The remote directory " + check_it +
                    ' does not yet exist, creating it... ')
        server.mkdir(check_it)
    remote_data_dir = check_it  # overwriting the configured dir here
    now = str(dt.datetime.now().isoformat())  # iso time for the upload_run
    logger.info("Starting actual upload part from sync")
    # db checks for files that are in limbo between intake and vault, trigger warning
    upload_info = mydb.get_table_rows_simple(table='upload',
                                             columns=['id', 'upload_full_path', 'upload_count'])
    uploaded_before_info = mydb.get_table_rows_where(table='upload',
                                                     columns=['id', 'upload_full_path', 'upload_rela_path',
                                                              'upload_count'],
                                                     condition="WHERE upload_count >= 1")
    uploaded_before_file = uploaded_before_info['upload_full_path']
    uploaded = upload_info['upload_full_path']
    uploaded_many_info = mydb.get_table_rows_where(table='upload',
                                                   columns=['id', 'upload_full_path', 'upload_count'],
                                                   condition="WHERE upload_count >= 5")
    if len(uploaded_many_info) >= 1:
        print("------------------------------------------------------------------------")
        print("""ALERT: the file(s) below has/have been uploaded often but somehow never 
made it to the vault....Please check what's going on; notify datamanager
or lab technician.""")
        print("------------------------------------------------------------------------")
        print(uploaded_many_info['upload_full_path'])
        print("------------------------------------------------------------------------")
        print("""ALERT: the file(s) above has/have been uploaded often but somehow never 
made it to the vault....Please check what's going on; notify datamanager
or lab technician.""")
        print("------------------------------------------------------------------------")
        input("press enter to continue...")
        # log files that need attention, too
        for f in uploaded_many_info:
            logger.info('The file ' + f['upload_full_path'] + ' needs attention, ' +
                        ' it has been uploaded ' + str(f['upload_count']) + ' times...')
    # now before we add fresh files we want to check the latest upload timestamps
    # this is how you get the actual freshest timestamp, so latest re-upload
    latest_uploadchangeinfo = mydb.get_table_rows_where(table='upload',
                                                        columns=['id', 'upload_rela_path', 'upload_timestamp'],
                                                        condition=" ORDER BY upload_timestamp DESC LIMIT 1 ")
    try:
        latest_upload_ts = latest_uploadchangeinfo['upload_timestamp'][0]
        # print(latest_upload_ts)
    except IndexError:
        # print('This is probably a fresh, empty database...')
        # should always "reupload" in case of empty db
        # so fake this upload time: my own epoch onset
        latest_upload_ts = '1979-07-22T00:31:41.592653'
    upped = []  # list for all "fresh" uploads in this run (including reuploads)
    # fancy spinner
    # spin1 = cSpinner()
    # spin1.stop = False
    # spin1.kill = False
    # spin1.start()
    c = 0
    bs = []
    done_before = []
    # check each file first time
    try:
        for file, checksum, checksumtype in files2upload:
            if myos == 'nt':
                file = ntpath.normpath(file)
            if myos == 'posix':
                file = posixpath.normpath(file)
            nothing_much, remote_path = file.split(local_data_prefix)
            if myos == 'nt':
                remote_path, filename = ntpath.split(remote_path)
            if myos == 'posix':
                remote_path, filename = posixpath.split(remote_path)
            if myos == 'nt':
                remote_path = remote_path.replace('\\', '/')
            remote_path = posixpath.normpath(remote_path)
            # now last check to make everything join nicely
            if remote_path[0] == '/':
                remote_path = remote_path[1:]
            remote_data_dir = posixpath.normpath(remote_data_dir)
            rel_path = posixpath.normpath(posixpath.join(remote_path, filename))
            if not file in uploaded:
                logger.info("New file to upload: " + file + " of " +
                            str(os.stat(file).st_size) + " bytes")
                server.mkdirs(posixpath.normpath(posixpath.join(remote_data_dir,
                                                                remote_path)))
                server.upload(file, posixpath.normpath(posixpath.join(remote_data_dir,
                                                                      remote_path, filename)))
                nu = str(dt.datetime.now().isoformat())
                cmd = ("INSERT INTO upload VALUES (NULL, " +
                       "'{0}','{1}','{2}','{3}','{4}', {5});".format(file, rel_path,
                                                                     nu, checksum, checksumtype,
                                                                     int(1)))  # so, is this int(1) necesarry? #V0.24
                res, code = mydb.execute(cmd)
                sql_codes.append(code)
                mydb.commit()
                upped.append(file)
                bs.append(os.stat(file).st_size)
                c += 1
            else:
                logger.info("Known in local DB as uploaded, skipping: " + file)
                done_before.append((file, checksum, checksumtype))
        # spin1.stop = True
        # spin1.kill = True
    except KeyboardInterrupt or EOFError:
        pass
        # spin1.kill = True
        # spin1.stop = True
    first_bytes = sum(bs)
    logger.info("Uploaded " + str(c) + " files for the first time, " +
                str(bytesto(first_bytes, 'm')) + " megabytes in total")
    current_ts = str(dt.datetime.now().isoformat())
    then = isotime_to_obj(latest_upload_ts)
    newnow = isotime_to_obj(current_ts)
    delta = newnow - then
    # counter and empty list for files (and sizes) that have been uploaded before
    c2 = 0
    bs2 = []
    # and the next group of spinners
    # spin2 = cSpinner()
    # spin2.stop = False
    # spin2.kill = False
    # spin2.start()
    nice_delta = strfdelta(delta, " {days} days {hours} hours {minutes} minutes " +
                           "{seconds} seconds")
    nice_orig = strfdelta(reupload_delta, " {days} days {hours} hours " +
                          "{minutes} minutes {seconds} seconds")
    if delta < reupload_delta:
        print("The latest upload time of previously uploaded files to intake was " +
              nice_delta + " ago , skipping reupload until " + nice_orig +
              " time has passed.")
        logger.info('Suppressing reupload loop due to reupload timedelta specification.')
    else:
        # second loop for uploads that have happened before, we do them again
        print("\nRe-uploading " + str(len(done_before)) + " files")
        logger.info("Re-uploading " + str(len(done_before)) + " files and " +
                    "updating their local upload counts.")
        try:
            for file, checksum, checksumtype in done_before:  # second batch, updating runs
                nothing_much, remote_path = file.split(local_data_prefix)
                if myos == 'nt':
                    remote_path, filename = ntpath.split(remote_path)
                if myos == 'posix':
                    remote_path, filename = posixpath.split(remote_path)
                    # we have to get NT, or in fact *any* remote paths in posix style
                if myos == 'nt':
                    remote_path = remote_path.replace('\\', '/')
                remote_path = posixpath.normpath(remote_path)
                remote_data_dir = posixpath.normpath(remote_data_dir)
                # now last check to make everything join nicely
                if remote_path[0] == '/':  # todo, check it!
                    remote_path = remote_path[1:]
                remote_data_dir = posixpath.normpath(remote_data_dir)
                rel_path = posixpath.normpath(posixpath.join(remote_path, filename))
                if file in uploaded_before_file:
                    logger.info("File to re-upload: " + file +
                                " of " + str(os.stat(file).st_size) + " bytes")
                    server.mkdirs(posixpath.normpath(posixpath.join(remote_data_dir,
                                                                    remote_path)))
                    server.upload(file, posixpath.normpath(posixpath.join(remote_data_dir,
                                                                          remote_path, filename)))
                    # find the DB id of the file by an actually smart query (checksums)
                    # >>>>>>>>>but what if it is a duplicate?: extension:
                    # we also look for the exact same rela_path (posixpath)
                    find_by_checksum = mydb.get_table_rows_where(table='upload',
                                                                 columns=['id', 'upload_rela_path',
                                                                          'upload_timestamp', 'upload_checksum'],
                                                                 condition=
                                                                 " WHERE upload_rela_path = '{0}' AND upload_checksum = '{1}' ".format(
                                                                     posixpath.join(remote_path, filename), checksum))
                    this_one = find_by_checksum['id'][0]
                    nuweer = str(dt.datetime.now().isoformat())
                    cmd1 = ("UPDATE upload SET upload_count = upload_count + 1 WHERE id = {0}".format(this_one))
                    cmd2 = ("UPDATE upload SET upload_timestamp = '{0}' WHERE id = {1}".format(nuweer, this_one))
                    res, code = mydb.execute(cmd1)
                    sql_codes.append(code)
                    res2, code2 = mydb.execute(cmd2)
                    sql_codes.append(code2)
                    mydb.commit()
                    upped.append(file)
                    bs2.append(os.stat(file).st_size)
                    c2 += 1
            # spin2.stop = True
            # spin2.kill = True
        except KeyboardInterrupt or EOFError:
            pass
            # spin2.kill = True
            # spin2.stop = True
    second_bytes = sum(bs2)
    logger.info("Uploaded " + str(c2) + " files that were already uploaded before, " +
                str(bytesto(second_bytes, 'm')) + " megabytes in total")
    # now for some deletions, preparing
    trash_info = mydb.get_table_rows_simple(table='trash',
                                            columns=['id', 'trash_timestamp_entrance', 'trash_timestamp_exit',
                                                     'trash_checksum', 'trash_checksum_type', 'trash_oripath',
                                                     'trash_fname',
                                                     'trash_box_id', 'trash_trashed_bool'])
    # whatever is already in the trash table of the db should be found like this
    trash_checksum = trash_info['trash_checksum']
    trash_oripath = trash_info['trash_oripath']
    # if there *were* results in the trash table, we check for more specifics 
    # we then want to get the latest timestamp of a file that was 
    # 'actually trashed' i.e. trash_trashed_bool = 1;
    # if this gives no results, we need to just add stuff to this table, for files 
    # are still in limbo/waiting for trash time to be ok
    latest_trashinfo = mydb.get_table_rows_where(table='trash',
                                                 columns=['id', 'trash_timestamp_entrance', 'trash_timestamp_exit',
                                                          'trash_checksum', 'trash_checksum_type', 'trash_oripath',
                                                          'trash_fname',
                                                          'trash_box_id', 'trash_trashed_bool'],
                                                 condition=" WHERE trash_trashed_bool=1 ORDER BY " +
                                                           "trash_timestamp_entrance DESC LIMIT 1 ")
    totrashlist = []
    toretrashlist = []
    preptrashlist = []
    warnlist = []
    warnlist2 = []
    delete_check = {}
    for filedel, checksumdel, checksumtypedel in files2delete:
        # If only some files in a WEPV directory are ready for deletion,
        # we don't want to throw away the entire set
        # figure out if it's a set in a wepv dir or not...
        thepath, thefile = os.path.split(filedel)
        boring, yay = os.path.split(thepath)
        wepvcheck_dir = re.match(WEPV, yay)
        if wepvcheck_dir:
            if thepath not in list(delete_check.keys()):
                delete_check[thepath] = []
                delete_check[thepath].append(filedel)
            elif thepath in list(delete_check.keys()):
                delete_check[thepath].append(filedel)
        if myos == 'nt':
            filedel = ntpath.normpath(filedel)  # sanitize path
            normfile = ntpath.normpath(filedel)
            normfile.replace('\\', '/')  # one type of name/path seems best for fname
        if myos == 'posix':
            filedel = posixpath.normpath(filedel)  # sanity
            normfile = posixpath.normpath(filedel)
        if checksumdel not in trash_checksum:  # it is a new file to trash, saving it
            nu = str(dt.datetime.now().isoformat())
            cmd = ("INSERT INTO trash VALUES(NULL, " +
                   "'{0}', NULL, '{1}','{2}', '{3}','{4}','{5}','{6}',{7});".format(nu,
                                                                                    checksumdel, checksumtypedel,
                                                                                    normfile,
                                                                                    filedel, myos, box_id,
                                                                                    int(0)))  # V0.24
            res, code = mydb.execute(cmd)
            sql_codes.append(code)
            mydb.commit()
            logger.info("Added " + filedel + " to trash table with trashed=0," +
                        " waiting to be deleted once delta has been been exceeded.")
            preptrashlist.append(filedel)
        else:
            dbfilename = mydb.get_table_rows_where(table='trash',
                                                   columns=['id', 'trash_timestamp_entrance', 'trash_timestamp_exit',
                                                            'trash_checksum', 'trash_checksum_type', 'trash_oripath',
                                                            'trash_fname', 'trash_box_id', 'trash_trashed_bool'],
                                                   condition=" WHERE trash_checksum = '{0}';".format(
                                                       checksumdel))
            if not filedel == str(dbfilename['trash_oripath'][0]):
                warnlist.append(filedel)
                logger.warn("This file is known in the DB under checksum " +
                            checksumdel + " with original filename " +
                            str(dbfilename['trash_oripath'][0]) + " but is now uploaded" +
                            " under the name " + filedel +
                            " Please check what is going on!")
            else:
                logger.info("Checksum already known in the deleted db, skipping to add " +
                            filedel + " to the db again, time for deletion will come...")
    # spin2.stop = True
    # spin2.kill = True
    # get the timestamp for which holds that files older are ready for actual trashing:
    current_ts_iso = str(dt.datetime.now().isoformat())
    current_ts = dt.datetime.now()
    old_ts = current_ts - wait_until_delete_delta
    old_ts_iso = str(old_ts.isoformat())
    # now we query the trashed db again and see if we can find files ready to be
    # actually deleted, the ones just arrived in the trash table will be skipped
    # so: find files known in trash table with a timestamp (older) than the time
    # calculated from now() - timedelta and that have not been *really* deleted
    # (trashed_bool=0)
    memory_trash = []
    logger.info('Trashables should be older than :' + old_ts_iso)
    find_trashables = mydb.get_table_rows_where(table='trash',
                                                columns=['id', 'trash_timestamp_entrance', 'trash_timestamp_exit',
                                                         'trash_checksum', 'trash_checksum_type', 'trash_oripath',
                                                         'trash_fname', 'trash_box_id', 'trash_trashed_bool'],
                                                condition=" WHERE datetime(trash_timestamp_entrance) < datetime('{0}') and trash_trashed_bool = 0 ORDER BY trash_timestamp_entrance;".format(
                                                    old_ts_iso)
                                                )
    for t in find_trashables:
        logger.info(t)
        memory_trash.append(t['id'])
    t_count = 0
    if find_trashables.size != 0:
        logger.info("The following files have been in the db long enough to be " +
                    "actually be deleted: ")
        for trashable in find_trashables:
            the_id = trashable['id']
            nudan = str(dt.datetime.now().isoformat())
            # update boolean
            cmd1 = "UPDATE trash SET trash_trashed_bool = 1 where id = %(id)d" % {"id": the_id}
            logger.info('\t' + trashable['trash_oripath'])
            res, code = mydb.execute(cmd1)
            sql_codes.append(code)
            # update actual trash time, although it is a bit earlier than actual
            # deletion time (see main)
            cmd2 = "UPDATE trash SET trash_timestamp_exit ='{0}' WHERE id = {1}".format(nudan, int(the_id))  # V0.24
            logger.info('\t' + trashable['trash_oripath'])
            res2, code2 = mydb.execute(cmd2)
            sql_codes.append(code2)
            mydb.commit()
            totrashlist.append(trashable['trash_oripath'])
            t_count += 1
    else:
        logger.info('No fresh trashables were found...')
    # we may still have files in toretrashlist: with files found that are
    # known at yoda and db when it comes to checksums, but that have somehow not been
    # actually removed or have been put back (testing purposes).
    check_trashed = mydb.get_table_rows_where(table='trash',
                                              columns=['id', 'trash_timestamp_entrance', 'trash_timestamp_exit',
                                                       'trash_checksum', 'trash_checksum_type', 'trash_oripath',
                                                       'trash_fname', 'trash_box_id', 'trash_trashed_bool'],
                                              condition=" WHERE trash_trashed_bool = 1 " +
                                                        "ORDER BY trash_timestamp_entrance ;")
    for fun in check_trashed:
        the_id = fun['id']
        the_path = fun['trash_oripath']
        if os.path.exists(the_path) and not the_id in memory_trash:
            logger.warn('This file ' + the_path + " should have been deleted , but" +
                        " is still or once again found! ")
            toretrashlist.append(the_path)
        elif os.path.exists(the_path) and the_id in memory_trash:
            logger.info('This file ' + the_path + ' has just been recognised as trashable')
        # if files are retrashed, shall we update anything or not BTW?
        # for now, not updating the trash time
    number = (c + c2)
    syncrunnow = str(dt.datetime.now().isoformat())
    cmd = ("INSERT INTO sync_run VALUES (NULL, " +
           "'{0}','{1}','{2}','{3}',{4},{5});".format(now, syncrunnow,
                                                      full_hostname, __version__, int(number), int(t_count)))  # V0.24
    res, code = mydb.execute(cmd)
    sql_codes.append(code)
    mydb.commit()
    logger.info("Marked " + str(t_count) + " files as deleted in local database.")
    # now we run the pre_delete, making it so that entire sets can be deleted
    # we use the delete_check dict first and check if the amount of files given by
    # checksum flow corresponds with the amount of files found within WEPV folders
    double_check = pre_delete(totrashlist + toretrashlist)
    double_check[:] = [i for i in double_check if os.path.isdir(i) and not i[0] == '.']
    incomplete = []
    for dc in double_check:
        osfiles = os.listdir(dc)
        osfiles[:] = [files for files in osfiles if not files[0] == '.']

        if not len(osfiles) == len(delete_check[dc]):
            for item in delete_check[dc]:
                print('-------------------------->', item)
                warnlist2.append(item)
    actually_delete_list = pre_delete(totrashlist + toretrashlist)
    skipitems1 = check_warnlist(warnlist)
    for item in skipitems1:
        logger.warning("File: " + item + " is not deleted because one or more files" +
                       " from its WEPV directory has a known checksum, but was saved " +
                       " under a different name.")
    skipitems2 = check_warnlist(warnlist2)

    for item in skipitems2:
        logger.warning("File: " + item + " is not deleted because one or more files" +
                       " from its WEPV directory is not identified as a known checksum." +
                       " It looks like one or more extra files were later added to a WEPV" +
                       " directory that has before been put in the vault with a different" +
                       " amount of files. Not deleting this directory, notify data manager" +
                       " or lab tech.")
    skipitems = skipitems1 + skipitems2
    skip_strings = []
    for i in skipitems:
        pad, kikker = os.path.split(i)
        baaspad = os.path.basename(pad)
        skip_strings.append(baaspad)
    skip = np.unique(skip_strings)
    exclude_deletion_count = 0
    for dont_delete in skip:
        for maybe_delete in actually_delete_list:
            if dont_delete in maybe_delete:
                actually_delete_list.remove(maybe_delete)
                kickout = os.listdir(maybe_delete)
                kickout[:] = [files for files in kickout if not files[0] == '.']
                amount = len(kickout)
                exclude_deletion_count += amount
                # so all files from a set in which one or more files has a different name than
    # what is known in the db are NOT deleted, warnings about the files causing this
    # are in the log
    if testing or implement_test:
        fake_delete(actually_delete_list, fake_trash=config.get('TEST_DATA_DIR',
                                                                'test_fake_trash'))
        logger.info("Inspectable (test_fake_trash) deletion of " + str(len(actually_delete_list)) +
                    " data set(s).")
    else:
        delete(actually_delete_list)
        logger.info("Deleting " + str(len(actually_delete_list)) + " data set(s).")
    l_upped = len(upped)
    l_trashed = len(totrashlist) + len(toretrashlist) - exclude_deletion_count
    l_prepped = len(preptrashlist)
    if len(warnlist) > 0:
        print("\n!!!!!!!!!!!!!!!!!!!WARNINGS 1 !!!!!!!!!!!!!!!!!!!!!!!!!!")
        for w in warnlist:
            print("This file is known in the DB under its checksum " +
                  "but with another name: please check -------> " + w)
    if len(warnlist2) > 0:
        print("\n!!!!!!!!!!!!!!!!!!!WARNINGS 2 !!!!!!!!!!!!!!!!!!!!!!!!!!")
        for w in warnlist2:
            print("This file is not deleted because not all checksums of it's " +
                  "fellow files in its WEPV dir are known: please check -------> " + w)
    sql_errors = sum(sql_codes)
    if sql_errors > 0:
        dberror = True
        print("\n!!!!!!!!!!!!!!!!!!!WARNINGS 3 !!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("Database errors were encountered, please notify lab tech!")
    else:
        dberror = False
    if not warnlist and not warnlist2 and not sql_errors > 0:
        print('\n-------------------------------------------')
        print(reward_banner)
        print('Files uploaded: ' + str(l_upped) + '\n' +
              'Files deleted: ' + str(l_trashed) + '\n' +
              'Files marked for deletion: ' + str(l_prepped) + '\n')
        print('-------------------------------------------\n')
    else:
        print('\n-------------------------------------------')
        print(hell_banner)
        print("Notify your Lab tech!, specify computer ID and current time.")
    logger.info("Sync run finished.")
    return upped, totrashlist, toretrashlist, warnlist, warnlist2, dberror


def check_warnlist(warnlist):
    """
    Search for any other files that may exist within WEPV sets as known according to DB
    and make sure they get added to the list of files not to delete.
    
    In the situation in which *one or just some files* from a data set is already
    known in DB given it's checksum, but it has a different name than before, or there 
    are more files now, identify these to exclude the whole set from the deletion flow 
    in the main sync routine. Also, it ends up in the log.
    
    **Parameters**
    --------------
    warnlist: list  
        *A list with warnings originating from labsync.sync().*  
    
    **Returns**
    -----------
    extra: list  
        *A list of files to exclude from deletion.*  
    
    **See Also**
    ------------
    `labsync.sync`
    """
    extra = []
    dirmem = []
    # first loop: collect all unique WEPV directories
    for f in warnlist:
        path, file = os.path.split(f)
        shortpath, maybe_wepvdir = os.path.split(path)
        if re.match(WEPV, maybe_wepvdir):
            if not path in dirmem:
                dirmem.append(path)
    # second loop over wepv dirs, check if there are any other files not in warnlist
    for dir in dirmem:
        otherfiles = os.listdir(dir)
        if otherfiles:
            for otherfile in otherfiles:
                if not os.path.join(dir, otherfile) in warnlist:
                    extra.append(os.path.join(dir, otherfile))
    return warnlist + extra


def pre_delete(files2delete):
    """
    Find out wether the files to delete are in a WEPV directory.
    
    **Notes**
    ---------
    1. Checks only the first underlying directory.  
    2. Input should be a list of files only, not (empty) directories.  
    
    **Parameters**
    --------------
    files2delete: list  
        *A list of files marked to be deleted.*  
         
    **Returns**
    -----------
    out: list  
        *A sorted list of folders and files that can be deleted **recursively**.*
    """
    wepvfile = []
    wepvfolder = []
    c = 0
    for thing in files2delete:
        is_dir = os.path.isdir(thing)
        is_file = os.path.isfile(thing)
        if is_dir:
            logger.critical(thing + " is an empty directory")
            raise ValueError(' empty directory in list')
        if is_file:
            # continue
            patje, file = os.path.split(thing)
            boring, yay = os.path.split(patje)
            wepvcheck_dir = re.match(WEPV, yay)
            wepvcheck_file = re.match(WEPV, file)
            if wepvcheck_dir and wepvcheck_file:
                # we don't append the file because we will delete it's folder
                wepvfolder.append(patje)
            elif wepvcheck_dir and not wepvcheck_file:
                continue
            elif not wepvcheck_dir and wepvcheck_file:
                wepvfile.append(thing)
            elif not wepvcheck_dir and not wepvcheck_file:
                continue
            else:
                continue
    nice = wepvfile + wepvfolder
    nice.sort()
    u = np.unique(nice)
    out = list(u)
    return out


def fake_delete(files2delete, fake_trash):
    """
    Simulate actual deletion by moving files/folders.
    
    When running tests, actual deletion is often not the best way to inspect if things
    work as intended. This helps with eyeball inspection in those cases.
        
    **Parameters**
    --------------
    files2delete: list  
        *A list of files/folders ready for 'deletion'.*  
    fake_trash: str  
        *An existing path to which files/folder are moved.*  
    """
    for file in files2delete:
        shutil.move(file, fake_trash + os.path.sep)


def delete(files_dirs):
    """
    Untested yet. Actual deletion.  
    todo before production implementation  
    """
    # for thing in files_dirs:
    #    shutil.rmtree(dest, ignore_errors=True)


def gen_multi_fake_data(select_one=True):
    """
    Create WEPV folder(s) with fake data according to settings. 
    
    **Parameters**
    --------------
    select_one: bool  
        *If True: randomly select one of the available types to generate,
        if False, generate all types.*
    
    **See also**
    ------------- 
    `labsync.yoda_helpers.gen_webv_fake_data`, `labsync.settings`
    """
    # no huge paramater values in the docs please, overloading inputs
    expdic = settings.CREATE_D
    types = list(settings.CREATE_D.keys())
    pseudotype_dic = settings.PSEUDO_D
    wave_dic = settings.WAVE_D
    outpath = gconf.get('TEST_DATA_DIR', 'test_data_dir')
    myos = os.name
    if myos == 'nt':
        iswin = True
        outpath = ntpath.normpath(outpath)
    if myos == 'posix':
        iswin = False
        outpath = posixpath.normpath(outpath)
    if not os.path.exists(outpath):
        print("creating ", outpath)
        os.mkdir(outpath)
    if select_one:
        types = random.choice(types)
        types = [types]
    print("ALERT! Generating data(sets) in ", outpath, " for these types: ", types)
    for i in types:
        yh.gen_webv_fake_data(expdic=expdic, type_exp=i, pseudotype_dic=pseudotype_dic,
                              wave_dic=wave_dic, outpath=outpath, iswin=iswin)


def abs_paths(directory):
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            yield os.path.abspath(os.path.join(dirpath, f))


def main(testing=False, implement_test=True):
    """
    Main sync function. 
    
    **Parameters**
    --------------
    testing: bool  
        *If True, uses the test_data_dir and fake_trash as specified in 
        configuration file.*  
        
    **Returns**
    -----------
    upped: list  
        *List of files uploaded to intake.*  
    trashlist: list  
        *List of files deleted (or moved in case of testing=True)*  
    retrashlist: list  
        *List of files deleted (once again)*  
    warnlist: list  
        *List of files with warnings of type 1.*  
    warnlist2: list  
        *List of files with warnings of type 2.*  
    err: bool  
        *True if any database related errors occurred during a sync run.*  
        
    **See also**
    -------------
    `labsync.sync`  
    """
    # Time delta's in 'sync'.
    UPLOAD_DELTA = dt.timedelta(days=18, hours=0, minutes=0, seconds=0, microseconds=0)
    DELETE_DELTA = dt.timedelta(days=30, hours=0, seconds=0, minutes=0, microseconds=0)

    logger.info("=============== Started main sync script. ===============")
    # get configuration object
    config = configparser.RawConfigParser()
    # get configuration file name
    config_filename = getConfigFile()
    logger.info(config_filename)
    config.read(config_filename)


    # If the database file is not found, create it.
    database_filename = config["LocalDataBase"]["database"]

    if not os.path.isfile(database_filename):
        db.build_db(database_filename)


    # connect to server
    wbdv = connect(config)
    logger.info("Connected to server using webdav.")

    print("Downloading list of checksums from vault ...", end=" ")
    vault_list, md_vault_list, sha_vault_list = download_hash_list(config,
                                                                   config_filename, wbdv)
    print("Done.")
    logger.info("Downloaded list with vault files and checksums.")

    md_vault_list = sort_list(md_vault_list)
    sha_vault_list = sort_list(sha_vault_list)
    print("Comparing to local checksums ...", end=" ")
    uploadlist, deletelist = comp2localchecksum(config, config_filename,
                                                md_vault_list, sha_vault_list, testing=testing)
    print("Done.")
    logger.info("Checksummed local files and comparing with list.")

    (upped, trashlist,
     retrashlist, warnlist,
     warnlist2, err) = sync(wbdv, config,
                            uploadlist,
                            deletelist,
                            UPLOAD_DELTA,
                            DELETE_DELTA,
                            testing=testing,
                            implement_test=implement_test)
    if not warnlist and not warnlist2 and not err:
        logger.info("===== Ran main sync script without critical errors/warnings =======")
    else:
        logger.info("===== Ran main sync script, WARNINGS/ERRORS were encountered! =====")
        # simple format some output...later we'll think about what is best
        if MAIL:
            ppwarnlist1 = '\n'.join(warnlist)
            ppwarnlist2 = '\n'.join(warnlist2)
            ppdberr = '\nDatabaser errors too?: ' + str(err)
            mess = ('WARNINGS TYPE 1 (File known under different name):\n\n' + ppwarnlist1 + '\n\n------------\n\n' +
                    'WARNINGS TYPE 2 (Not all fellow checksums in WEPV folder are known):\n\n' + ppwarnlist2 +
                    '\n\n------------\n\n' + ppdberr + '\n\n' + hell_banner + '\n')

            if config.has_option("Datamanagers", "email"):
                datamanagers = config["Datamanagers"]["email"]
            else:
                datamanagers = ''

            try:
                yh.mail(server='smtp.uu.nl', Subject='SYNC Errors encountered on: ' +
                                                     str(dt.datetime.now().isoformat()),
                        To=datamanagers,
                        From=box_id.lower() + '@' + 'soliscom.uu.nl',
                        Message=mess)
            except:
                print("Mailing error: ", sys.exc_info()[0])
    input("Press Enter to quit.")
    return upped, trashlist, retrashlist, warnlist, warnlist2, err
