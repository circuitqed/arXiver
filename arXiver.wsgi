#!/home/dave/venvs/arxiver36/python
activate_this = '/home/dave/venvs/arxiver36/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

import sys
import logging

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/home/dave/venvs/arxiver36/lib/python3.6/site-packages")
sys.path.insert(0,"/home/dave/arXiver")

from arxiver import app as application
