#from this package
from labsync import checksum as cs
from labsync import settings

#generic imports
import os
import sys
import ntpath
import posixpath
import glob
import re
import fnmatch
import re
import random
import datetime as dt
import errno
import configparser
import pkg_resources

__version__ = pkg_resources.require("labsync")[0].version
__email__ = 'j.c.vanelst@uu.nl'
__authors__ = ['Jacco van Elst'] 
__doc__= """ Test I/O + storage related + generic module util functions.

What you can find here
-----------------------

- Helpers that can generate checksums/files.  
- Tool to simulate YODA index_file generation behavior of YODA (intake/vault/iRods 
    commands) based upon local sqlite database contents.  
- Tools to generate valid WEPV strings (Wave, Experiment, Pseudocode + Version)  
- Tools to generate random byte (bytesize) files given experiment settings.  
- Combinations thereof for test purposes.  
- File and files size specification.  

Settings
--------

Settings with dicts and lists come from settings.py  

"""
myos = os.name
#some regexpressions that check for wepv standards
#see https://regex101.com/r/nR1hF2/1 the only difference is caps/nocaps
one = "^[ab](\d{5})_(\d{0,16})^[yb]_([a-z]{5,10})(_)([0-9]{4})(1[0-2]|0[1-9])"
two = "(3[01]|0[1-9]|[12][0-9])(_)([01]?[0-9]|2[0-3])[0-5][0-9]\w"
mega = one + two
WEPV = re.compile(mega, re.IGNORECASE)
"""
Compiled regular expression for WEPV format.
"""

def run_wepv_test(testlist=None):
    """ 
    Checks for WEPV (simple test routine).
    
    **Parameters**
    --------------
    testlist: list  
        *A list (that comes from e.g. settings.py).*  
    """
    for f in testlist:
        hit = re.match(WEPV, f) 
        if hit:
            print (f, ' OK-wepv')
        else:
            print (f, ' Bad-wepv')

def yodasim_indexfile(to_md5_list=None, to_sha_list=None, outpath=None):
    """
    Simulate an index file in Yoda format
    
    Input list(s) must be full pathnames to existing files.
    
    **Parameters**
    ---------------
    to_md5_list: list  
        *List with files to checksum with md5 algo.*  
    to_sha_list: list  
        *List with files to checksum with sha256 algo.*  
    outpath: str  
        *If not none, write the output info to this filepath.*  
    
    **Returns**
    -----------
    save: list  
        A list (and/or a file) in YODA indexfile format.  
    """
    skip1 = False
    save = []
    for f in to_md5_list:
        try:
            md5hash = cs.chunk_md5(f, blocksize=4096)
        except OSError as e:
            skip1 = True
        if not skip1:
            size1 = str(os.stat(f).st_size)
            line1 = 'md5 ' + md5hash + ' ' + size1 + ' ' + f + ' \n'
            save.append(line1)
    #second list, not very pythonic, no
    skip2 = False
    for f in to_sha_list:
        try:
            shahash = cs.chunk_sha256(f, blocksize=4096)
        except OSError as e:
            skip2 = True
        if not skip2:
            size2 = str(os.stat(f).st_size)
            to_fix_sha = str(shahash)
            fix_sha = to_fix_sha[2:-1]
            line2 = 'sha2 ' + fix_sha + ' ' + size2 + ' ' + f + ' \n'
            save.append(line2)
    if outpath:
        with open(outpath, "w") as checkfile:
            checkfile.writelines(save)
    return save
    
def sense(start_path=None, dic=None):
    """
    Recursive data set check on completeness, file size and WEPV structure check.
    
    # Important assumption   
    There are no subfolders containing other WEPV data *folders* in the "DATA" folder, 
    i.e. all is at the exact DATA dir as configured with the <mac or dell ID>.cfg.  
    
    **Parameters**
    --------------
    start_path: str  
        - The DATA folder where new data sets end up.  
    dic: dictionary  
        - The settings dictionary for checking datasets, amounts of files per experiment
        type  
    
    **Returns**
    ------------
    Three dictionaries, key, value pairs are:  
        - Files that do no match, message.  
        - Directories that contain files that don't match, message.
        - Files/folders with complete sets.
    """
    #list the experiment names
    exnames = list(dic.keys())
    #find the glob patterns for filenames, * stands for "anything" at location
    includes = ["*" + exname + "*" for exname in exnames]# glob patterns for filenames
    # transform glob patterns to regular expressions
    includes = r'|'.join([fnmatch.translate(x) for x in includes])
    out = {}
    weirdfiles = {}
    weird_dirs = {}
    for (dirpath, dirnames, filenames) in os.walk(start_path):
        dirname = dirpath.split(os.path.sep)[-1] # get dirname
        # exclude/include files
        filenames = [f for f in filenames if not f[0] == '.']
        dirnames[:] = [d for d in dirnames if not d[0] == '.']
        filenames = [os.path.join(dirpath, f) for f in filenames]
        filenames = [f for f in filenames if re.match(includes, f)]
        c = 0
        subd = {} # dict for specific matches of files
        memlist = [] # in this we keep files and sizes until the subdir is checked
        tmp = {} # tmp dict for all type of files associated with exp
        order = []
        for file in filenames:  
            ft = os.path.basename(file)
            memlist.append((file,  os.path.getsize(file))) #file + size to memory
            hit = re.match(includes, ft) #if file corresponds to any of the exp dicts 
            if hit:
                g = hit.group()
            else:
                #tag file/dir with info
                weirdfiles[file] = 'File not in inclusion naming specs' # skip file
                weird_dirs[dirname] = 'Files within here not in inclusion naming specs'
            # now make sure the right values for files for each type of exp are loaded
            for exname in exnames: #loop over all experiments we've configured
                if not exname in out:
                    out[exname] = {} #create a new sub dict in out if key does not exist
                p = re.compile(exname)
                match = p.search(g)
                if match:
                    ex = exname
                    break
            # now we're pretty sure the file belongs of a specific type 
            # (facehouse/coherence etc.)
            # continue to check which filetypes should be matched within    
            subs = dic[exname] # matching patterns for files
            tmp[subs] = subs # we check excactly what how many they should be
            includes_sub = [subname for subname in subs]
            for sub in subs:
                if not sub in out[exname]:
                    out[exname][sub] = [] # set a sub dict for the out data (type)
            includes_sub = r'|'.join([fnmatch.translate(x) for x in includes_sub])
            # check if the file is in any of the settings for files
            hit2 = re.match(includes_sub, ft)
            if hit2:
                g2 = hit2.group()
            else: 
                weirdfiles[file] = ('One or more of the file name patterns is not' + 
                                    'recognised')
                weird_dirs[dirname] = ('One or more of the filename patterns not' + 
                                    'recognised')
            #CHECK IF *ALL* OF THE FILE SETTINGS patterns are found     
            for sub in subs:
                subcheck = r'|'.join([fnmatch.translate(sub)])
                p = re.compile(subcheck)
                match = p.search(ft)
                if match:
                    subd[sub] = match.group()
                    order.append(sub)
                    break
            c+=1
        print (c, "files found in ", dirname)
        if not is_empty(subd):
            if not len(list(subd.keys())) == len(list(tmp.keys())[0]):
                print (dirname)
                print ("================ NO! :-( incomplete!==========\n\n")
                for file_and_size in memlist:
                    weirdfiles[file_and_size] = "file from incomplete set"
                    weird_dirs[dirname] = "incomplete set"
            else:
                print (dirname)
                print ("**************** COMPLETE! *******************\n\n")
                for i in range(len(memlist)):
                    out[exname][order[i]].append(memlist[i])
    return weirdfiles, weird_dirs, out

def make_outfiles(d):
    """
    Create human readable csv files from specific dictionaries.
    
    Parses the out dictionary from sense() with experiment values to human readable 
    files. Dotcomma seperated '.csv' files for each experiment type that is 'complete' 
    according to settings files.
    
    **Parameters**
    ---------------
    d: dictionary   
        * Dictionary originating from the sense() function.  
    
    **See Also**
    ------------
    `labsync.yoda_helpers.sense`, `labsync.yoda_helpers.sense_main`
    """
    experiments = list(d.keys())
    for exp in experiments:
        expdata = d[exp]
        expdata_filekeys = d[exp].keys()
        #print (exp, " with ", expdata_filekeys)    
        with open(exp + '.csv', 'w') as f:
            f.write('file ; bytes \n')
            for k in expdata_filekeys:
                for file, size in expdata[k]:
                    f.write(file + ';' + str(size) + '\n')

def fake_pseudo(ptype='B'):
    """ 
    Generate a (fake) pseudocode for ptype. 
    """
    intcode = random.randint(9999, 99999) #not the full range btw.
    niceint = '{0:05d}'.format(intcode)
    pseudo = str(ptype) + str(niceint)
    return pseudo
    
def fake_id(ids=None):
    """ 
    Random select one ID from the workstaton ID list.
    """
    return random.choice(ids)
    
def fake_time(date_time=dt.datetime.now()):
    """ 
    Generate YODA-compatible date/time strings based upon a datetime object.
    """
    datestring = dt.datetime.strftime(date_time, "%Y%m%d")
    timestring = dt.datetime.strftime(date_time, "%H%M")
    return datestring, timestring   
    
def fake_wave(dic=None, experiment='chantigap'):
    """ 
    Random select one of the waves belonging to the experiment type.
    """
    choices = dic[experiment]
    return random.choice(choices) 
    
def fake_file(outpath=None, bytesize=1024):
    """
    Generate file with name outpath made up from random bytes given bytesize.
    
    **Notes**
    ---------
    Use with care!  
    
    **Parameters**
    --------------
    outpath: str  
        *File path/name to save the file.*  
    bytesize: int  
        *The bytes size to count with.*  
    """
    if outpath:
        with open(outpath, 'wb') as fout:
            fout.write(os.urandom(bytesize))
    
def gen_webv_fake_data(expdic=None, type_exp='chantigap', pseudotype_dic=None, 
                        id='MAC07', wave_dic=None, outpath='TEST', iswin=False):
    """ 
    Generate test files in a WEPV folder that are made up of random bytes.
    
    Files are generated according to dictionaries in settings.py.
    
    **Parameters**
    ---------------
    expdic: dictionary  
        *A settings dictionary for creation (names/types/file sizes).*  
    type_exp: str  
        *Some experiment name.*  
    pseudotype_dic: dictionary  
        *The dictionary that holds the pseudo prefix codes implemented
        for the experiment types, as specified in settings.py.*
    id: str  
        *The ID of a lab workstation.*  
    wave_dic: dictionary  
        *A settings.py dictionary for experiments and their implemented waves.*  
    outpath: str  
        *A base path specifying where to put WEPV folder w/ files.*  
    iswin: bool  
        *A boolean, True if on windows, else, will create posix paths.
        (probably not really needed, since all is run on one OS, so os.path.normpath 
        should be fine, @todo)*    
    """
    # generate time and date strings (based upon dt.datetime.now()
    datestr, timestr = fake_time()
    # check what kind of pseudo we need (B or A)
    pseudo_pre = pseudotype_dic[type_exp]
    pseudo = fake_pseudo(ptype=pseudo_pre)
    twave = fake_wave(dic=wave_dic, experiment=type_exp)
    wepvstring = (pseudo + '_' + twave + '_' + type_exp + '_' + datestr + '_' 
                    + timestr + '_' + id)
    #now let's create that dir, first simple
    if iswin:
        ntpath.normpath(outpath)
    else:
        posixpath.normpath(outpath)
    if not os.path.exists(outpath + os.path.sep + wepvstring):
        try:
            os.mkdir(outpath + os.path.sep + wepvstring)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise exc
        pass
        print (outpath + os.path.sep + wepvstring + " was created")
    else:
        print (outpath + os.path.sep + wepvstring + " already exists")
    subd = expdic[type_exp]
    for k, v in subd.items():
        fake_file(outpath + os.path.sep + wepvstring + os.path.sep + wepvstring 
                 + '_' + k, bytesize=v)

def sense_main(path=None):
    """ 
    Shortcut to checking all correct data in DATA dir qua amount/size of files.
    
    Also saves them as dotcomma-separated human readable files in the working directory.
    
    **Parameters**
    -------------  
    path: str  
        *The main path in which experiment data resides on a lab computer.*  
    
    **Returns**
    ------------
    gooddict: dictionary  
        *A dictionary containg the ok/complete date sets/files.*
    """
    badfiles, baddirs, gooddict = sense(start_path=path)
    make_outfiles(gooddict)
    return gooddict
