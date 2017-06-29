#generics
import os
import random
import shutil
import pkg_resources  # part of setuptools

#import the main sync module separately
from labsync import sync
#some function shortcuts
from labsync import yoda_helpers as yh

__version__ = pkg_resources.require("labsync")[0].version
__email__ = 'j.c.vanelst@uu.nl'
__authors__ = ['Jacco van Elst'] 
__doc__ = """Test Specification Protocol for labsync.

Purpose
--------

Check/validate all scenarios before we start implementing the labsync package with real
data. The docstrings describe what should be done in each test. The code itself is very
simple in most cases. This module can serve as a TPS document + code shortcuts to manual 
work all in one, although a regular TPS document exists, too.

Important Codes
---------------
- **H** : A **human** --> checks/validates.  
- **C** : A piece of **code** --> generates or creates.  

"""

def test_0():
    """
    Dry run test after sqlite database and config files have been created.
    
    **Scenario:** 
    
    Create new data in TEST. Set is not uploaded yet and unknown in vault.
        
    **Done here:**
    
    1. H: Check if TEST and TEST_FAKE_TRASH directories are created.
    2. H: Check if TEST and TEST_FAKE_TRASH dirs are not overwritten.
    3. H: Check if TEST dir is empty: if not: delete all file in it manually.
    4. C: Generates a (fake) dataset in TEST dir.
    5. H: Check if the fake data set is created and has the right WEPV/amount of
         files in it
    6. C: Run main with testing = True
    7. H: Verify if uploads succeeded. Use Cyberduck and check intake.
    8. H: Verify that files that are part of a WEPV directory are in the same 
        directory/structure using Cyberduck.
    9. H: After uploads have been verified: log in @intake. Scan for new files.
    10. H: Check that uploads are in folder named after Lab computer.
    11. H: Check that uploads are in right WEPV folder and set is complete.
    12. H: If all is ok, lock the files (go to vault).
    13. H: Read the Labdata_cleanup.log and check if all has been logged
    """
    sync.gen_multi_fake_data()#default is only one randomly selected data set
    sync.main(testing=True)

def test_01():
    """
    Test 1: Verify deletion preparation after test_0 has been run.
    
    **Scenario:** 
    
    Dataset in vault, dataset in TEST.
    
    **Done here:**
    
    1. C: Perform a sync run (after checksum data from Yoda should be in remote 
        checksum file).
    2. H: Verify wether uploaded and locked files are indeed in checksums.txt.
    3. H: Verify that files from the dataset that was uploaded in test_0 are marked 
        for deletion.
    4. H: Also, verify that those datasets are not yet moved to TEST_FAKE_TRASH 
        directly in testing mode, the files wil need to be in the database for 
        longer than 5 minutes an 33 seconds.
    5. H: verify in the local db that files are in the trash table with the
         'trashed' boolean on 0 (waiting for next sync run + deletion 
         timedelelta to be removed).
    """ 
    sync.main(testing=True)

def test_02():
    """
    Test 2: Check actual deletion after another sync run.
    
    **Scenario:** 
    
    The time has passed that files can be *actually* removed, they have been 
    known in the database long enough. This is 5 minutes and 33 seconds while testing.

    **Done here:**
    
    1. C: Run main sync without any new files in TEST directory.
    2. H: Verify that files/datasets from TEST are moved to TEST_FAKE_TRASH
    3. H: Check that, if files are contained in a WEPV directory, this structure 
        is the same in the trash (TEST_FAKE_TRASH).
    4. H: Related: verify that there are no empty WEPV directories left in the test
        directory (TEST).
    5. H: Verify that the files that were marked in the db trash table now have the 
        "trash_trashed" boolean values on '1'
    """
    sync.main(testing=True)
    
def test_03():
    """
    Test 3: Check re-upload flow.
    
    Verify that files are not being re-uploaded if within the time delta specified for
    reuploading. In production, this would be, say, 8-24 hours, for testing, it is 
    three minutes.
    
    **Scenario:** 
    
    New files to upload in sync run 1, sync run 2 follows directly 
    after run 1.
    
    1. New files should be uploaded in run 1
    2. Files should not be re-uploaded in run 2
    3. Information in the interface + log file gives feedback about this.
    
    **Done here:**
    
    1. C: Generate new dataset
    2. C: Start sync run
    3. C: Start second sync run directly after
    4. H: Verify program's feedback an logging about skipping reuploads within 
        time delta.
    5. H: Log in to intake and lock the new dataset, which we need in test_4.
    6. H: Wait until it's checksums are expected to be available... 
    """
    sync.gen_multi_fake_data()
    sync.main(testing=True)  
    sync.main(testing=True)  

def test_04():
    """
    Test 4: Check re-upload flow approach 2.
    
    Falsification approach of test 2: with data generated in test_3.
    Verify that files will not be thrown away if triggered with new sync run within
    timedelta specified (5:33 minutes)
    
    **Scenario:**   
    
    1. Data set is known in vault and still resides in TEST.
    2. A new sync run (1) marks the files as ready to trash.
    3. Now directly after this sync run, another sync run is started.
    4. Thus, sync run 2 is initiated before the data may actually be removed
    5. Thus, the data should not yet be thrown away.
    
    **Done here:**
    
    1. H: Note start time.
    2. C: Start sync run 1
    3. C: Start sync run 2 immediately after 1 has been run.
    4. H: Verify that dataset is still in TEST directory.
    5. H: Verify that database values in trash table for new dataset files still 
        end with '0'
    """
    sync.main(testing=True)
    sync.main(testing=True)
    
def test_05():
    """
    Test 5: Test deletion flow including warings.
    
    Verify that files known in vault that are known as deleted according to DB are
    identified as previously deleted by the sync run and are deleted again. Also,
    verify that this triggers a warning in the log.
    
    **Scenario:** 
    
    Data set from TEST_FAKE_TRASH is moved back into TEST directory.
    Sync run identifies the set as previously deleted and deletes it again.
    The incident get logged with WARNING status.

    **Done here:**
    
    1. H: Copy or move a dataset from TEST_FAKE_TRASH to TEST (manually)
    2. C: Start a sync run.
    3. H: Verify that the dataset is trashed again.
    4. H: Verify that warnings are printed in the log
    """
    input("Select a data set from TEST_FAKE_TRASH and put it in TEST " + 
        " and press enter to continue...")
    sync.main(testing=True)
            
def test_06():
    """
    Test 6: Check that a non-WEPV file gets uploaded by the sync run.
    
    **Scenario:** 
    
    A file (or set) with a name not according to WEPV specification is in (test) data
    directory. It gets uploaded and ends up in the upload table, but is detected as an 
    unidentified or unscanned file (or set) by YODA.
    
    **Done here:** 
    
    1. C: Generate a non wepv file.
    2. C: Perform a sync run.
    3. H: Log in at YODA intake, scan for files  and verify that the file is marked 
        as "unrecognised" (or unscanned).
    4. H: Delete the file manually after verification.
    """
    yh.fake_file(outpath=sync.gconf.get('TEST_DATA_DIR', 'test_data_dir') + os.sep + 
                        'test_06_non_wepv_file.file', bytesize=424242)
    sync.main(testing=True)
 
def test_07():
    """
    Test 7: Check warnings on name change.
    
    Check that files with a known checksum, but *different filename than in he db*,
    trigger warnings and log messages.
    
    **Scenario:**
    
    Data set from vault has been renamed, but still in WEPV format and put (back) in 
    (test) upload data directory. Checksums will be identical, so the files should: 
    1. not be uploaded again
    2. not be deleted
    3. (so) warnings should be given and data manager/lab tech should resolve the 
        issue. 
    4. The user should be prompted to report this incident.

    **Done here:**
    
    1. H: Verify that TEST_FAKE_TRASH is not empty and that there are some 
        sets/files in it.
    2. H: Verify that all sets in TEST_FAKE_TRASH have actually been synced and 
        locked in earlier test steps. Remove any files or sets for which this
        does not hold.
    3. C: Create the rename file/set by randomly choosing a set from 
        TEST_FAKE_TRASH.
    4. H: Verify that one of the sets or files  in TEST_FAKE_TRASH ends up in 
        TEST_DATA_DIR and that it's structure (i.e. set within WEPV directory 
        or file itself) is represented in TEST_DATA_DIR, and that directories 
        have the '_test_3_newdirname' in the name and/or that the file or files 
        within have '_test_3_newfilename' in their name.
    5. H: Verify that the duplicate set is NOT moved to TEST_FAKE_TRASH.
    6. H: Verify that all these renamed files are not be uploaded to YODA, since 
        they are in the vault and their checksums are known in DB.
    7. H: Verify that a warning is printed in the UI about the renamed file(s).
    8. H: Verify that a warnings are printed in the log file.
    9. H: Delete the dataset with edited names manually.
    """
    tocreate = os.getcwd() + os.sep + sync.gconf.get('TEST_DATA_DIR','test_data_dir')
    list_trash = sync.gconf.get('TEST_DATA_DIR','test_fake_trash')
    sets = []
    p = os.path.join(os.getcwd(), list_trash)
    #check for files at the entry level, they  are not a set, but a separate file
    for f in os.listdir(p):
        if os.path.isfile(os.path.join(p, f)) and not f.startswith('.DS_'):
            sets.append(os.path.join(p,f))
    #now for sets
    for dirpath, dirnames, files in os.walk(p):
        dirnames = [dn for dn in dirnames if not dn.startswith('.DS_')]
        files = [f for f in files if not f.startswith('.DS_')]
        if files:
            if not dirpath == p:
                sets.append(dirpath)
        if not files:
            continue
    torename = random.choice(sets)
    if os.path.isdir(torename):
        newdirname = os.path.basename(torename) + '_test_7_newdirname'
        newdir = tocreate + os.sep + newdirname
        try:
            os.mkdir(newdir)
        except FileExistsError as e:
            print ('Directory ', newdir, ' already exists...please check.')
            pass
        for f in os.listdir(torename):
            full_f = os.path.join(os.getcwd() + os.sep + list_trash + 
                                    os.sep + os.path.basename(torename) + os.sep + f)
            opath, ext = os.path.splitext(f)
            basen = os.path.basename(f)
            nfilename = basen + '_test_7_newfilename' + ext
            shutil.copy(full_f, newdir + os.sep + nfilename)
    else:
        full_f = os.path.join(os.getcwd() + os.sep + list_trash + torename) 
        opath, ext = os.path.splitext(torename)
        basen = os.path.basename(torename)
        nfilename = basen + '_test_7_newfilename' + ext
        shutil.copy(full_f, tocreate + os.sep + nfilename)
    sync.main(testing=True)
    return sets

def test_08():
    """
    Test 8: Check that warnings are triggered on name change within folder.
    
    Verify that a dataset that has one hand-edited new name in its WEPV folder will
    raise a warning and that the entire WEPV folder is not deleted in this case.
    
    **Scenario:** 
    
    A set has been locked to the vault and still resides in sync directory.
    From that set, one or multiple files have been renamed since the data were
    locked. All checksums are known, but some file names differ. All files from the 
    set should: 
    
    1. not be uploaded again
    2. not be deleted
    3. warnings should be given that data manager should resolve the issue. 
    4. The user should be prompted to report the incident.

    **Done here:**
    
    1. H: Verify that TEST_FAKE_TRASH is not empty and that there are some 
        sets/files in it.
    2. H: Verify that all sets in TEST_FAKE_TRASH have actually been synced and 
        locked in earlier test steps. Remove any files or sets for which this
        does not hold.
    3. H: Manually copy a (the) data set from TEST_FAKE_TRASH and put it in the 
        TEST directory.
    4. H: Edit ONE of the files by changing its name only. E.g. append 
        "_edited_test_8" to its base name.
    5. H: Run test_8() and press enter when ready to continue after prompts.
    6. H: Verify that the entire set is NOT moved to TEST_FAKE_TRASH.
    7. H: Verify that none of the files in the set are uploaded to YODA, since
         they are in the vault and their checksums are known in DB.
    8. H: Verify that a warning is printed in the UI about the renamed file(s)
    9. H: Verify that warnings are written in the log.
    """
    input("Select a data set from TEST_FAKE_TRASH and put it in TEST " + 
        " Now edit ONE file's name manually, eg. append 'edited_' to the file name." + 
        " Press enter to continue and start a sync run...")
    sync.main(testing=True)
    
def test_09():
    """
    Test 9: Check that additional files in WEPV folder trigger warnings.
    
    Verify that a dataset that has one extra (not known in vault) file in its WEPV 
    folder will raise a warning and that the entire WEPV folder is not deleted in 
    this case.
    
    **Scenario:** 
    
    A set has been locked to the vault and still resides in sync directory.
    Within that set, one file has been added manually (or, in real life, by running 
    a repair program of some kind). Almost all checksums are known, except the one 
    that has been added. In this case the entire set should:
    1. Not be uploaded again.  
    2. Not be deleted.  
    3. Warnings should be given that data manager should resolve the issue.   
    4. The user should be prompted to report the incident.  

    **Done here:**  
    
    1. H: Verify that TEST_FAKE_TRASH is not empty and that there are some 
        sets/files in it.
    2. H: Verify that all sets in TEST_FAKE_TRASH have actually been synced and 
        locked in earlier test steps. Remove any files or sets for which this
        does not hold.
    3. H: Manually copy a (the) data set from TEST_FAKE_TRASH and put it in the 
        TEST directory.
    4. H: Add ONE extra file in the WEPV set. This may be any file on the machine, 
        and may or may not be in WEPV naming format, just make sure that it is not
        a file known in the vault.
    5. H: Run test_9() and press enter when ready to continue after prompts.
    6. H: Verify that the entire set is NOT moved to TEST_FAKE_TRASH
    7. H: Verify that none of the files in the set are uploaded to YODA, since they 
        are in the vault and their checksums are known in DB.
    8. H: Verify that a warning is printed in the UI about the extra file(s)
    9. H: Verify that warnings are written in the log.
    """
    input("Select a data set from TEST_FAKE_TRASH and put it in TEST " + 
        " Now copy some random file (eg from desktop) into that WEPV set." + 
        " You could rename it to match the other files WEPV structure, but you don't" +
        " need to." +
        " Press enter to continue and start a sync run...")
    sync.main(testing=True)

def test_10():
    """
    Test 10: Check max upload times warnings.
    
    Verify that warnings are printed about files that have been uploaded 5 or more
    times.
    
    **Scenario:**  
    
    A new set is uploaded and is not put in the vault.
    Then 5 or more sync runs are started, one after the other.
    """
    for i in range(5):
        sync.main(testing=True)
    return ("Check if it works...")
