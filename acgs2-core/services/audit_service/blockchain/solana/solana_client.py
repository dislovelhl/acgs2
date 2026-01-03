"""Constitutional Hash: cdd01ef066bc6cf2
Solana 区块链客户端 (Production Ready)
用于审计日志哈希的去中心化锚定

支持的网络：
- Devnet (默认)
- Testnet
- Mainnet-beta
"""

import asyncio
import functools
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

# Handle httpx 0.25.x vs 0.26.x incompatibility in solana-py 0.36.9
import httpx

try:
    if httpx.__version__ < "0.26.0":
        import functools

        _original_async_client_init = httpx.AsyncClient.__init__

        @functools.wraps(_original_async_client_init)
        def _patched_async_client_init(self, *args, **kwargs):
            if "proxy" in kwargs:
                kwargs["proxies"] = kwargs.pop("proxy")
            return _original_async_client_init(self, *args, **kwargs)

        httpx.AsyncClient.__init__ = _patched_async_client_init
except Exception:  # nosec B110 - Monkey patching for httpx compatibility
    pass

# Solana & Solders Primitives
try:
    from solana.rpc.async_api import AsyncClient
    from solana.rpc.commitment import Confirmed
    from solders.instruction import Instruction
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.signature import Signature
    from solders.transaction import Transaction

    try:
        from solders.compute_budget import set_compute_unit_price
    except ImportError:
        set_compute_unit_price = None
    HAS_SOLANA = True
except ImportError:
    HAS_SOLANA = False

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class SolanaClient:
    """Solana 区块链客户端 - 支持 Mock 和 Live 模式"""

    # 支持的网络配置
    NETWORKS = {
        "devnet": {
            "name": "Solana Devnet",
            "rpc_url": "https://api.devnet.solana.com",
            "explorer": "https://explorer.solana.com/?cluster=devnet",
        },
        "testnet": {
            "name": "Solana Testnet",
            "rpc_url": "https://api.testnet.solana.com",
            "explorer": "https://explorer.solana.com/?cluster=testnet",
        },
        "mainnet-beta": {
            "name": "Solana Mainnet Beta",
            "rpc_url": "https://api.mainnet-beta.solana.com",
            "explorer": "https://explorer.solana.com",
        },
    }

    # SPL Memo Program ID
    MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"

    def __init__(self, config: Dict[str, Any]):
        """
        初始化Solana客户端

        Args:
            config: 配置字典，包含：
                - network: 使用的网络 ('devnet', 'testnet', 'mainnet-beta')
                - rpc_url: RPC 节点 URL (可选)
                - commitment: 确认级别 (默认: 'confirmed')
                - wallet_path: 钱包文件路径 (默认: ~/.config/solana/id.json)
                - live: 是否启动真实网络提交 (默认: True)
                - retry_count: RPC 重试次数 (默认: 3)
                - retry_delay: 基础重试延迟 (默认: 1.0s)
                - compute_unit_price: 优先级费用 (默认: 1000 micro-lamports)
        """
        self.network = config.get("network", "devnet")
        self.network_config = self.NETWORKS.get(
            self.network, {"name": "Custom", "rpc_url": config.get("rpc_url"), "explorer": ""}
        )
        self.config = config
        self.connected = False
        self.commitment = config.get("commitment", "confirmed")
        self.live = config.get("live", True)

        # 生产硬化配置
        self.retry_count = config.get("retry_count", 3)
        self.retry_delay = config.get("retry_delay", 1.0)
        self.compute_unit_price = config.get("compute_unit_price", 1000)

        self.rpc_urls = config.get("rpc_urls", [])
        if not self.rpc_urls and config.get("rpc_url"):
            self.rpc_urls = [config.get("rpc_url")]
        if not self.rpc_urls:
            self.rpc_urls = [self.network_config.get("rpc_url", "https://api.devnet.solana.com")]

        self.rpc_clients: List[AsyncClient] = []
        self.current_rpc_index = 0
        self.failover_count = 0
        self._keypair: Optional[Keypair] = None

        if not HAS_SOLANA and self.live:
            logger.warning(
                f"[{CONSTITUTIONAL_HASH}] solana-py not found, falling back to mock mode"
            )
            self.live = False

        if self.live:
            logger.info(
                f"[{CONSTITUTIONAL_HASH}] Initializing Solana client in LIVE "
                f"mode for {self.network}"
            )
        else:
            logger.info(
                f"[{CONSTITUTIONAL_HASH}] Initializing Solana client in MOCK "
                f"mode for {self.network}"
            )

    async def _load_wallet(self) -> bool:
        """加载本地钱包 (支持环境变量或文件路径)"""
        if self._keypair:
            return True

        # 1. 优先尝试从环境变量加载
        env_key = os.environ.get("SOLANA_PRIVATE_KEY")
        if env_key:
            try:
                secret = json.loads(env_key)
                if isinstance(secret, list):
                    self._keypair = Keypair.from_bytes(bytes(secret))
                    logger.info(f"[{CONSTITUTIONAL_HASH}] Wallet loaded from environment variable")
                    return True
            except Exception as e:
                logger.debug(f"Failed to load wallet from env: {e}")

        # 2. 从文件加载
        wallet_path = self.config.get("wallet_path")
        if not wallet_path:
            wallet_path = os.path.expanduser("~/.config/solana/id.json")

        if not os.path.exists(wallet_path):
            logger.error(f"[{CONSTITUTIONAL_HASH}] Wallet not found at {wallet_path}")
            return False

        try:
            with open(wallet_path, "r") as f:
                secret = json.load(f)

            if isinstance(secret, list):
                secret = bytes(secret)

            self._keypair = Keypair.from_bytes(secret)
            logger.info(
                f"[{CONSTITUTIONAL_HASH}] Wallet loaded from file: {self._keypair.pubkey()}"
            )
            return True
        except Exception as e:
            logger.error(f"[{CONSTITUTIONAL_HASH}] Failed to load wallet from {wallet_path}: {e}")
            return False

    async def _with_retry(self, func_name: str, *args, **kwargs) -> Any:
        """通用的异步重试包装器 (支持跨多 RPC 节点 Failover)"""
        last_exception = None

        for i in range(self.retry_count + 1):
            try:
                # 获取当前活跃的 RPC 客户端
                client = self.rpc_clients[self.current_rpc_index]
                func = getattr(client, func_name)
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # 如果有多个 RPC 节点，尝试 Failover
                if len(self.rpc_clients) > 1:
                    self.current_rpc_index = (self.current_rpc_index + 1) % len(self.rpc_clients)
                    self.failover_count += 1
                    current_url = self.rpc_urls[self.current_rpc_index]
                    logger.warning(
                        f"[{CONSTITUTIONAL_HASH}] RPC Failover: Switching to {current_url} "
                        f"due to error: {e}"
                    )

                if i < self.retry_count:
                    wait_time = self.retry_delay * (2**i)
                    logger.warning(
                        f"[{CONSTITUTIONAL_HASH}] Solana RPC call '{func_name}' "
                        f"failed (attempt {i + 1}): {e}. Retrying in {wait_time:.1f}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"[{CONSTITUTIONAL_HASH}] Solana RPC call '{func_name}' "
                        f"failed after {self.retry_count} retries: {e}"
                    )

        raise last_exception if last_exception else Exception("Unknown RPC error")

    async def connect(self) -> bool:
        """连接到Solana网络"""
        if not self.live:
            await asyncio.sleep(0.05)
            self.connected = True
            return True

        try:
            self.rpc_clients = [AsyncClient(url, commitment=Confirmed) for url in self.rpc_urls]
            self.current_rpc_index = 0

            # 测试第一个连接
            version_resp = await self._with_retry("get_version")
            if version_resp and version_resp.value:
                logger.info(
                    f"[{CONSTITUTIONAL_HASH}] Connected to Solana {self.network} "
                    f"via {self.rpc_urls[0]} (Node: {version_resp.value.solana_core})"
                )

                if self.live:
                    await self._load_wallet()

                self.connected = True
                return True
            return False

        except Exception as e:
            logger.error(f"[{CONSTITUTIONAL_HASH}] Failed to connect to any Solana RPC: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        """断开连接"""
        for client in self.rpc_clients:
            await client.close()
        self.rpc_clients = []
        self.connected = False
        logger.info(f"[{CONSTITUTIONAL_HASH}] Disconnected from Solana {self.network}")

    async def submit_audit_batch(self, batch_data: Dict[str, Any]) -> Optional[str]:
        """提交审计批次到Solana区块链 (Memo Program)"""
        if not self.connected:
            if not await self.connect():
                return None

        if not self.live:
            await asyncio.sleep(0.1)
            tx_signature = f"sol_mock_sig_{int(time.time())}_{batch_data['batch_id']}"
            logger.info(
                f"[{CONSTITUTIONAL_HASH}] MOCK: Submitted audit batch "
                f"{batch_data['batch_id']} to Solana"
            )
            return tx_signature

        try:
            if not await self._load_wallet():
                logger.error(f"[{CONSTITUTIONAL_HASH}] Wallet load failed during submission")
                return None

            memo_dict = {
                "batch_id": batch_data["batch_id"],
                "root_hash": batch_data["root_hash"],
                "constitutional_hash": CONSTITUTIONAL_HASH,
                "v": "2.0",
            }
            memo_bytes = json.dumps(memo_dict, sort_keys=True).encode("utf-8")

            # 1. 准备指令
            instructions = []

            # 优先级费用
            if set_compute_unit_price:
                instructions.append(set_compute_unit_price(self.compute_unit_price))

            # Memo 指令
            instructions.append(
                Instruction(
                    program_id=Pubkey.from_string(self.MEMO_PROGRAM_ID),
                    data=memo_bytes,
                    accounts=[],
                )
            )

            # 2. 获取 Blockhash (支持重试和多 RPC)
            bh_resp = await self._with_retry("get_latest_blockhash")
            recent_blockhash = bh_resp.value.blockhash

            # 3. 构建交易
            tx = Transaction.new_signed_with_payer(
                instructions, self._keypair.pubkey(), [self._keypair], recent_blockhash
            )

            # 4. 发送交易 (支持重试和多 RPC)
            resp = await self._with_retry("send_transaction", tx)
            if resp and resp.value:
                tx_sig = str(resp.value)
                logger.info(
                    f"[{CONSTITUTIONAL_HASH}] Transaction sent for batch "
                    f"{batch_data['batch_id']}. SIG: {tx_sig}"
                )

                # 5. 等待确认 (Phase 5)
                if self.config.get("wait_for_confirmation", True):
                    confirmed = await self.confirm_transaction(tx_sig)
                    if not confirmed:
                        logger.error(
                            f"[{CONSTITUTIONAL_HASH}] Transaction failed to confirm: {tx_sig}"
                        )
                        return None

                logger.info(
                    f"[{CONSTITUTIONAL_HASH}] Audit batch {batch_data['batch_id']} "
                    f"confirmed on Solana {self.network}."
                )
                return tx_sig

            return None

        except Exception as e:
            logger.error(f"[{CONSTITUTIONAL_HASH}] Live Solana submission failed: {e}")
            return None

    async def get_transaction_memo(self, signature: str) -> Optional[Dict[str, Any]]:
        """从 Solana 交易签名中获取 Memo 内容 (支持重试)"""
        if not self.connected:
            if not await self.connect():
                return None

        if not self.live:
            return {"mock": "data", "status": "mock"}

        try:
            sig = Signature.from_string(signature)
            resp = await self._with_retry(
                "get_transaction", sig, encoding="jsonParsed", max_supported_transaction_version=0
            )

            if not resp or not resp.value:
                return None

            transaction = resp.value.transaction.transaction
            for ix in transaction.message.instructions:
                if str(ix.program_id) == self.MEMO_PROGRAM_ID:
                    if hasattr(ix, "parsed") and ix.parsed:
                        try:
                            if isinstance(ix.parsed, str):
                                return json.loads(ix.parsed)
                            return ix.parsed
                        except (json.JSONDecodeError, TypeError, ValueError) as e:
                            logger.warning(f"Failed to parse memo data: {e}")
                            return {"raw_memo": ix.parsed}
            return None
        except Exception as e:
            logger.error(f"[{CONSTITUTIONAL_HASH}] Failed to retrieve memo for {signature}: {e}")
            return None

    async def verify_batch_on_chain(
        self, batch_id: str, signature: str, expected_root_hash: str
    ) -> bool:
        """物理验证批次是否在链上且匹配"""
        memo = await self.get_transaction_memo(signature)
        if not memo:
            return False

        on_chain_root = memo.get("root_hash")
        on_chain_batch = memo.get("batch_id")

        if on_chain_root == expected_root_hash and on_chain_batch == batch_id:
            logger.info(
                f"[{CONSTITUTIONAL_HASH}] On-chain verification SUCCESS for batch {batch_id}"
            )
            return True

        return False

    async def confirm_transaction(
        self, signature: str, max_retries: int = 30, delay: float = 2.0
    ) -> bool:
        """等待交易确认 (Polling)"""
        sig = Signature.from_string(signature)
        logger.info(f"[{CONSTITUTIONAL_HASH}] Waiting for confirmation of {signature}...")

        for i in range(max_retries):
            try:
                # 使用当前 RPC 客户端检查状态
                resp = await self._with_retry("get_signature_statuses", [sig])
                if resp and resp.value and resp.value[0]:
                    status = resp.value[0]
                    if status.confirmations is not None or status.confirmation_status is not None:
                        confirmation_status = (
                            str(status.confirmation_status)
                            if status.confirmation_status
                            else "unknown"
                        )
                        logger.info(
                            f"[{CONSTITUTIONAL_HASH}] Transaction {signature} confirmation status: "
                            f"{confirmation_status} ({status.confirmations} confirmations)"
                        )
                        # 如果达到所要求的确认级别 (默认 confirmed)
                        if confirmation_status in ("confirmed", "finalized"):
                            return True

                await asyncio.sleep(delay)
            except Exception as e:
                logger.warning(
                    f"[{CONSTITUTIONAL_HASH}] Error checking signature status "
                    f"(attempt {i + 1}): {e}"
                )
                await asyncio.sleep(delay)

        logger.error(
            f"[{CONSTITUTIONAL_HASH}] Transaction {signature} timed out after {max_retries} checks"
        )
        return False

    async def get_network_stats(self) -> Dict[str, Any]:
        """获取网络统计信息 (增强版 - Phase 5)"""
        stats = {
            "blockchain_type": "solana",
            "network_name": self.network_config["name"],
            "rpc_pool_size": len(self.rpc_urls),
            "current_rpc_url": self.rpc_urls[self.current_rpc_index] if self.rpc_urls else None,
            "failover_count": self.failover_count,
            "connected": self.connected,
            "live_mode": self.live,
            "retry_config": {"count": self.retry_count, "delay": self.retry_delay},
            "compute_unit_price": self.compute_unit_price,
            "wallet_pubkey": str(self._keypair.pubkey()) if self._keypair else None,
        }

        if self.live and self.connected and self._keypair:
            try:
                # 获取余额时，使用其中一个客户端
                balance_resp = await self._with_retry("get_balance", self._keypair.pubkey())
                if balance_resp:
                    stats["wallet_balance_sol"] = balance_resp.value / 10**9
            except Exception as e:
                logger.warning(f"Failed to get wallet balance: {e}")
                stats["wallet_balance_sol"] = "error"

        return stats

    def is_connected(self) -> bool:
        return self.connected
