"""
Pacote de playbooks específicos por moeda.
"""

from .base_playbook import BasePlaybook
from .smc_rules import SMCRules
from .btc_playbook import BTCPlaybook
from .eth_playbook import ETHPlaybook
from .sol_playbook import SOLPlaybook
from .bnb_playbook import BNBPlaybook
from .doge_playbook import DOGEPlaybook
from .xrp_playbook import XRPPlaybook
from .ltc_playbook import LTCPlaybook
from .zerog_playbook import ZeroGPlaybook
from .kaia_playbook import KAIAPlaybook
from .axl_playbook import AXLPlaybook
from .nil_playbook import NILPlaybook
from .fogo_playbook import FOGOPlaybook
from .dash_playbook import DASHPlaybook
from .zk_playbook import ZKPlaybook
from .xai_playbook import XAIPlaybook
from .gtc_playbook import GTCPlaybook
from .celo_playbook import CELOPlaybook
from .hyper_playbook import HYPERPlaybook
from .mtl_playbook import MTLPlaybook
from .polyx_playbook import POLYXPlaybook
from .fil_playbook import FILPlaybook
from .grt_playbook import GRTPlaybook
from .ata_playbook import ATAPlaybook
from .pengu_playbook import PENGUPlaybook
from .gps_playbook import GPSPlaybook
from .gun_playbook import GUNPlaybook
from .power_playbook import POWERPlaybook

# Dynamic imports for modules with numeric names
import importlib
_1000why_module = importlib.import_module("playbooks.1000why_playbook")
WHYPlaybook = _1000why_module.WHYPlaybook

_1000bonk_module = importlib.import_module("playbooks.1000bonk_playbook")
BONKPlaybook = _1000bonk_module.BONKPlaybook

__all__ = [
    'BasePlaybook', 'SMCRules',
    'BTCPlaybook', 'ETHPlaybook', 'SOLPlaybook', 'BNBPlaybook',
    'DOGEPlaybook', 'XRPPlaybook', 'LTCPlaybook',
    'ZeroGPlaybook', 'KAIAPlaybook', 'AXLPlaybook', 'NILPlaybook', 'FOGOPlaybook',
    'DASHPlaybook', 'ZKPlaybook', 'WHYPlaybook', 'XAIPlaybook', 'GTCPlaybook',
    'CELOPlaybook', 'HYPERPlaybook', 'MTLPlaybook', 'POLYXPlaybook', 'BONKPlaybook',
    'FILPlaybook', 'GRTPlaybook', 'ATAPlaybook', 'PENGUPlaybook', 'GPSPlaybook',
    'GUNPlaybook', 'POWERPlaybook'
]
