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

__all__ = [
    'BasePlaybook', 'SMCRules',
    'BTCPlaybook', 'ETHPlaybook', 'SOLPlaybook', 'BNBPlaybook',
    'DOGEPlaybook', 'XRPPlaybook', 'LTCPlaybook'
]
