import sqlite3
import os
import numpy
import logging
import datetime as dt
import numpy as np
from collections import OrderedDict
import pkg_resources  # part of setuptools

__version__ = pkg_resources.require("labsync")[0].version
__email__ = 'j.c.vanelst@uu.nl'
__authors__ = ['Jacco van Elst'] 
__doc__ = """A class for interacting with an sqlite3 database for synchronising data.

How to start using it (from some other module):

**Example**
-----------

    #import this module
    import database as db 
    #if it does not exist yet, create the sqlite db like this:
    db.build_db(name='mac3db.sqlite')
    
    #initialize the class as object, eg. named 'mydb'
    mydb = db.dbManager('mydatabase.sqlite', debug=True) #make sure it exists!
    #perform some nifty query:  
    upinfo = mydb.get_table_rows_where(table='upload', columns=['id','upload_full_path', 
                'upload_count'], condition="WHERE upload_count >= 1")
"""

#i'm logging it
mylogger = logging.getLogger("Labdata_cleanup.database")

#used by the script to create the db 
db_creation = """CREATE TABLE sync_run(
id      INTEGER PRIMARY KEY AUTOINCREMENT, 
timestamp_start      TEXT,
timestamp_ready      TEXT,
computer_id     TEXT,
script_version      TEXT,
uploads_done        INTEGER,
trashes_done        INTEGER,
FOREIGN KEY(id) REFERENCES upload(id),
FOREIGN KEY(id) REFERENCES trash(id)
);
CREATE TABLE upload(
id      INTEGER PRIMARY KEY AUTOINCREMENT,
upload_full_path        TEXT,
upload_rela_path        TEXT,
upload_timestamp        TEXT,
upload_checksum     TEXT,
upload_checksum_type        TEXT,
upload_count        INTEGER

);
CREATE TABLE trash(
id      INTEGER PRIMARY KEY AUTOINCREMENT,
trash_timestamp_entrance     TEXT,
trash_timestamp_exit     TEXT,
trash_checksum      TEXT,
trash_checksum_type     TEXT,
trash_fname     TEXT,
trash_oripath       TEXT,
trash_os        TEXT,
trash_box_id        TEXT,
trash_trashed_bool      INTEGER

);
"""
"""
Custom code to create the database.
"""
#make sure all types are ok (in the numpy result arrays)
db_types = {'sync_run': {'id': '<i4', 
                            'timestamp_start': 'U26',
                            'timestamp_ready': 'U26',
                            'computer_id' : 'U30', 
                            'script_version': 'U4',
                            'uploads_done' : '<i10',
                            'trashes_done': '<i10',
                            },
            'upload': {'id': '<i4',
                         'upload_full_path': 'U1024',
                         'upload_rela_path': 'U1024',
                         'upload_timestamp': 'U26',
                         'upload_checksum': 'U50',
                         'upload_checksum_type': 'U5',
                         'upload_count' : '<i4',
                         },
            'trash': {'id': '<i4',
                        'trash_timestamp_entrance': 'U26',
                        'trash_timestamp_exit': 'U26',
                        'trash_checksum': 'U50',
                        'trash_checksum_type': 'U5',
                        'trash_fname':'U1024',
                        'trash_oripath':'U1024',
                        'trash_os':'U10',
                        'trash_box_id':'U24',
                        'trash_trashed_bool':'<i1',
                        }
            }
"""
Custom structured array specification for the database dtypes.
"""

class dbManager(object):
    """
    Manages the local data I/O and counts using sqlite database.
    """
    def __init__(self, database, debug):
        """
        Startup the class.
        
        **Parameters**
        ---------------
        database: str  
            *A database name/location, eg. 'mac7db.sqlite'.*  
        debug: bool  
            *Wether to debug/print queries in the logfile (verbose).*  
        """
        logger = logging.getLogger("Labdata_cleanup.database.dbManager.__init__")
        self.database = database
        self.debug = debug
        self.connection = sqlite3.connect(database)
        self.cursor = self.connection.cursor()
        cmd = 'SELECT SQLITE_VERSION()'
        if self.debug:
            logger.debug(cmd)
        self.cursor.execute(cmd)
        version = self.cursor.fetchone()
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        if self.debug:
            logger.debug("Using SQLite version " + str(version[0]))
            logger.debug(self.cursor.fetchall())

    def execute(self, cmd):
        """
        Execute commands.
        
        **Parameters**
        ---------------
        cmd: str  
            *A command, e.g. 'SELECT * from upload;'*  
        """
        code = 0
        logger = logging.getLogger("Labdata_cleanup.database.dbManager.execute")
        if self.debug:
            logger.info(cmd)
        try:
            self.cursor.execute(cmd)
        except:
            logger.critical('Execution failed, command was: "%s"'%(cmd))
            code = 1
        res = self.cursor.fetchall()
        return res, code
        
    def commit(self):
        """
        Commit cursor, needed for actual update/change action(s).
        """
        self.connection.commit()
    
    def get_table_infos(self, table):
        """
        Describe table info.
        
        **Parameters**
        --------------
        table: str  
            *The table of interest.*
        
        **Returns**
        -----------
        description: str  
            *Description (of columns in table)*    
        """
        logger = logging.getLogger("Labdata_cleanup.database.dbManager.get_table_infos")
        cmd = "SELECT * from '%s';" %(table)
        if self.debug:
            logger.info(cmd)
        self.cursor.execute(cmd)
        names = [description[0] for description in self.cursor.description]
        return names
    
    def get_table_rows_simple(self, table, columns):
        """
        Formats SELECT < > FROM kind of query results into nice structured numpy arrays.
        
        **Parameters**
        ---------------
        
        table: str   
            *Table of interest.*  
        columns: List  
            *List with one or more columns to give info on.*
            
        **Returns**
        -----------
        arres: array-like  
             A numpy record array with results.  
        """
        logger = logging.getLogger("Labdata_cleanup.database.dbManager.get_table_rows_simple")
        if columns == None:
            cmd = """SELECT * from %s """ %(table)
            if self.debug:
                logger.info(cmd)
        else:
            try: 
                cols = ",".join(columns)
            except TypeError:
                logger.debug("Table join error")
                raise NotImplementedError
        cmd = """SELECT %s FROM %s""" %(cols, table)
        if self.debug:
            logger.info(cmd)
        #run it without a fetchall()
        res = self.cursor.execute(cmd)
        numrows = int(self.cursor.rowcount)
        #check dtypes etc to format array
        table_oi = db_types[table]
        dtypes = [table_oi[column] for column in columns]
        myzip = list(zip(columns, dtypes))
        spec = [zipvalue for zipvalue in myzip]
        arres = np.fromiter(self.cursor.fetchall(), count=numrows, dtype=spec)
        return arres
        
    def get_table_rows_where(self, table, columns, condition):
        """
        Formats "SELECT < > FROM WHERE..." query results into structured numpy arrays.
        
        **Parameters**
        ---------------
        
        table: str  
            *Table of interest.*  
        columns: list  
            *A list with one or more columns to give info on.*  
        condition: str  
            *Some extra options for conditions.*  
        
        **Example**
        -----------
        (SELECT id, upload_full_path, upload_rela_path, upload_timestamp, 
        upload_checksum, upload_count FROM upload WHERE upload_count>3)
        
        **Returns**
        ------------
        arres: array-like  
            *A numpy record array with results.*
        """
        logger = logging.getLogger("Labdata_cleanup.database.dbManager.get_table_rows_where")
        try: 
            cols = ",".join(columns)
        except TypeError:
            logger.debug("table join error")
            raise NotImplementedError
        cmdleft = """SELECT %s FROM %s """ %(cols, table)
        cmdright = condition
        cmd = cmdleft + cmdright
        if self.debug:
            logger.info(cmd)
        #run it without a fetchall()
        res = self.cursor.execute(cmd)
        numrows = int(self.cursor.rowcount)
        #check dtypes etc to format array
        table_oi = db_types[table]
        dtypes = [table_oi[column] for column in columns]
        myzip = list(zip(columns, dtypes))
        spec = [zipvalue for zipvalue in myzip]
        arres = np.fromiter(self.cursor.fetchall(), count=numrows, dtype=spec)
        return arres
        
    def get_max_id(self, table):
        """
        Return max ID for table.
        """
        logger = logging.getLogger("Labdata_cleanup.database.dbManager.get_max_id")
        self.cursor.execute("""SELECT max(id) FROM %s """ %(table))
        max_id = self.cursor.fetchone()[0]
        return max_id
        
def test(name='mac3db.sqlite'):
    """
    Quick and simple testing of some queries on some database (that must exist).
    """
    mydb = dbManager(name, debug=True)
    now = str(dt.datetime.now().isoformat())
    cmd = "INSERT INTO upload_run(upload_run_timestamp) VALUES ('%s');" %(now)
    print (cmd)
    res = mydb.execute(cmd)
    print (res)
    commit = mydb.commit()
    cmd = "SELECT upload_run_timestamp from upload_run;"
    res = mydb.execute(cmd)
    print (res)
    commit = mydb.commit()
    names = mydb.get_table_infos('upload')
    print (names)
    
def build_db(name='mac3db.sqlite'):
    """
    Build the empty database on a new workstation.
    
    **Parameters**
    --------------
    name: str  
        *A name for the the DB.*  
    """
    if not os.path.isfile(name):
        conn = sqlite3.connect(name, detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        c.executescript(db_creation)
        rows = c.execute('pragma foreign_keys')
        # for row in rows:
        #     print (row)
        conn.commit()
        print ('The database', name, 'was created.')
    else:
        print ('The database', name, 'already exists. Please remove it and retry... ')
