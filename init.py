"""
Covenant.AI - Constitutional Alignment Framework for Autonomous AI Systems
Enhanced Enterprise Edition
"""

__version__ = "2.0.0"
__author__ = "Covenant.AI Development Team"
__license__ = "Apache 2.0"

from covenant.core.constitutional_engine import ConstitutionalEngine
from covenant.core.quantum_optimizer import QuantumOptimizer
from covenant.agents.swarm_orchestrator import SwarmOrchestrator
from covenant.llm.llm_integration import LLMIntegration
from covenant.blockchain.audit_trail import BlockchainAuditTrail
from covenant.security.zero_trust import ZeroTrustSecurity
from covenant.monitoring.metrics import MetricsCollector

# Core components
__all__ = [
    'ConstitutionalEngine',
    'QuantumOptimizer',
    'SwarmOrchestrator',
    'LLMIntegration',
    'BlockchainAuditTrail',
    'ZeroTrustSecurity',
    'MetricsCollector',
]

# Logging configuration
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('covenant.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Covenant.AI v{__version__} initialized")
