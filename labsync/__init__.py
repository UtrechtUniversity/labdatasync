import pkg_resources  # part of setuptools

__version__ = pkg_resources.require("labsync")[0].version
__email__ = 'j.c.vanelst@uu.nl'
__authors__ = ['Jacco van Elst', 'Julia Brehm'] 
__package__ = ['labsync']
# __all__ = ['sync', 'tps', 'yoda_helpers', 'database', 'checksum']
# __path__ = ['sync', 'tps', 'yoda_helpers', 'database', 'checksum']

# import labsync
