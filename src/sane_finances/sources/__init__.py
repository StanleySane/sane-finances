""" All available sources for export instruments history data.
"""

from . import msci
from . import solactive
from . import moex
from . import cbr
from . import yahoo

# when new source appears, add it here in the same way

__all__ = ['msci', 'solactive', 'moex', 'cbr', 'yahoo']
