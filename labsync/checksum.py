import os
import hashlib
import base64
import random
import numpy as np
import logging
import pkg_resources  # part of setuptools

__version__ = pkg_resources.require("labsync")[0].version
__email__ = 'j.c.vanelst@uu.nl'
__authors__ = ['Jacco van Elst'] 
__doc__= """Generating checksums. """

logger = logging.getLogger("Labdata_cleanup.checksum")

#print (hashlib.algorithms_available)

def chunk_md5(fname, blocksize=4096):
    """
    Checksums a file in chunks of `blocksize` bytes.
    
    **Parameters**
    ---------------
    fname: str  
        *File name.*  
    blocksize: int  
        *Block size in Bytes.*  
    
    **Returns**
    ------------
    str   
        *An MD5 hash string for the file.*
    """
    myhash = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(blocksize), b""):
            myhash.update(chunk)
    return myhash.hexdigest()

def chunk_sha256(fname, blocksize=4096):
    """
    Checksums a file in chunks of `blocksize` bytes.
    
    **Parameters**
    ---------------
    fname: str  
        *File name.*  
    blocksize: int  
        *Block size in Bytes.*  
    
    **Returns**
    ------------
    str   
        *An SHA256 hash string for the file.*
    """
    myhash = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(blocksize), b""):
            myhash.update(chunk)
    return base64.b64encode(myhash.digest())

def make_hash_string(fname, algoID):
    """
    Checksum file with filename and return it's hash according to algoID.
    
    **Parameters**
    ---------------
    fname: str  
        *File name.*  
    algoID: str  
        *String indicating hashing algorithm, either['SHA256', 'MD5]*  
    
    **Returns**
    ------------
    str  
        *String containing: algoID hash bytesize*
    """
    if not os.path.exists(fname):
        logger.critical("The file " + fname + " does not exist.") 
        raise ValueError("The file " + fname + " does not exist.") 
    info = os.stat(fname)
    byte_s = str(info.st_size)
    if 'SHA' in algoID:
        hasj = chunk_sha256(fname).decode('utf-8')
        algoID = 'SHA256'
    elif 'MD' in algoID:
        hasj = chunk_md5(fname)
        algoID = 'MD5'
    else:
        logger.critical("A non-implemented or wrong algoID was given.") 
        raise ValueError("A non-implemented or wrong algoID was given.") 
    return algoID + ' ' + hasj + ' ' + byte_s

def compare(hash1, hash2):
    """
    Compare two hashes.
    
    **Parameters**
    -------------- 
    hash1: str  
        *Hash 1.*  
    hash2: str  
        *Hash 2.*  
        
    **Returns**
    -----------
    bool  
        *True or False*  
    """
    return hash1==hash2

def simulate_list(n=2000, randsize=100, bytesize=30, algoID='MD5-SHA256'):
    """
    Make a random list of (algo + hash + bytesize) strings.
    
    This is a hack basically, since it generates the hash based
    upon some random string, instead of actual file contents.
    
    **Parameters**
    ---------------
    n: int  
        *The number of hashes to simulate.*  
    randsize: int  
         *A value like '100' yields about 28 integers.*  
    bytesize: int  
         *A value like '30' yields about 9 integers (<Gigabyte).*
         
    **Returns**
    -----------
    bitlist: list  
        * A list like yoda_indexfile with `n` items.    
    """
    random.seed()
    bitlist = []
    for i in range(n):
        bits = str(random.getrandbits(randsize))
        bitsok = bits.encode('utf-8')
        hasj = hashlib.md5(bitsok).hexdigest()
        byte = str(random.getrandbits(bytesize))
        select = random.randint(1, len(byte))
        samplebyte = ''.join(random.sample(byte, select))
        bitlist.append(algoID + ' ' + hasj + ' ' + samplebyte)
    return bitlist

def h_string(mystring=b'geef poot', algo='sha256', encoding='base64'):
    #message = mystring.encode('base64')
    hash = hashlib.sha256(mystring).digest()
    encoded = base64.b64encode(hash)
    print (hash)
    print (encoded)
    return hash, encoded
#     print (encoded)
#     return encoded

def testcase():
    """
    Test/simulate some scenario's.
    """
    yodalist = simulate_list(n=120000)#on yoda, say 120 thousand files
    locallist = simulate_list(n=600)#on workstation (new, so to upload)
    extralist = random.sample(yodalist, 300)#still on workstation, on yoda
    locallist = locallist + extralist
    #arrays tend to be faster
    remote = np.asarray(yodalist)
    local = np.asarray(locallist)
    remote.sort()
    local.sort()
    #but without looping?...
    totrash = []
    for f in local:
        hitbool = f == remote
        if np.any(hitbool):# should there be duplicates somehow on yoda
            totrash.append(f)
    return remote, local, totrash
    