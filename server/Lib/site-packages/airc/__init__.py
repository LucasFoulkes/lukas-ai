"""
    Asynchronous IRC module. Provides ways to handle individual servers, multiple servers,
    and a built in client and bot framework. Handles twitch and general IRC protocol
    'out of the box'.

    :copyright: (c) 2018 CraftSpider
    :license: MIT, see LICENSE for details.
"""

from .events import Event
from .enums import *
from .errors import *
from .server import Server, DefaultServer
from .client import DefaultClient
from .bot import *

__title__ = "airc"
__author__ = "CraftSpider"
__license__ = "MIT"
__copyright__ = "Copyright 2019 CraftSpider"
__version__ = "0.0.2"

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())
