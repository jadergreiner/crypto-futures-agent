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

__all__ = [
    'BasePlaybook', 'SMCRules',
    'BTCPlaybook', 'ETHPlaybook', 'SOLPlaybook', 'BNBPlaybook',
    'DOGEPlaybook', 'XRPPlaybook', 'LTCPlaybook',
    'ZeroGPlaybook', 'KAIAPlaybook', 'AXLPlaybook', 'NILPlaybook', 'FOGOPlaybook'
]
