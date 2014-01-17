from distutils.core import setup
import py2exe

setup(console=['main.py'], 
          options = {
              "py2exe": 
                  {
                      "dll_excludes": ["MSVCP90.dll"], 
                      "includes": ["sip", "PyQt4.Qt", "PyQt4.phonon"]
                  }
              })
