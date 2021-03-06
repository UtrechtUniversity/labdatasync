from setuptools import setup

setup(name='labsync',
      version='1.1',
      description='Lab data synchronisation package for Utrecht University',
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: UNLICENSE License',
        'Programming Language :: Python :: 3.5',
        'Topic :: Data synchronisation :: WebDav :: Grid based Storage',
      ],
      keywords='Data synchronisation, WebDav, Grid based Storage',
      url='https://github.com/UtrechtUniversity/Labdata_cleanup',
      author='Jacco van Elst & Julia Brehm',
      author_email='j.c.vanelst@uu.nl',
      license='UNLICENSE',
      packages=['labsync'],
      include_package_data=True,
      zip_safe=False)
