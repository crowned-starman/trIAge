# backend/app/blockchain/logger.py

import httpx
from app.core.config import settings


async def log_hash_to_chain(event_hash: str) -> bool:
    """
    Envía el hash a Monad (EVM) o lo simula localmente.
    Nunca bloquea — se llama siempre como BackgroundTask.
    Retorna True si el log fue exitoso, False si falló.
    """
    if not settings.BLOCKCHAIN_ENABLED:
        return await _simulate_log(event_hash)

    return await _log_to_monad(event_hash)


async def _simulate_log(event_hash: str) -> bool:
    """
    Modo demo: imprime el hash como si fuera una tx on-chain.
    Útil para el hackathon sin necesidad de wallet ni RPC.
    """
    from datetime import datetime
    print(
        f"[BLOCKCHAIN SIMULATED] "
        f"hash={event_hash[:16]}... "
        f"ts={datetime.utcnow().isoformat()}"
    )
    return True


async def _log_to_monad(event_hash: str) -> bool:
    """
    Llama al contrato TriageLogger.sol en Monad testnet via JSON-RPC.
    Requiere MONAD_PRIVATE_KEY y MONAD_CONTRACT_ADDR en .env
    """
    if not settings.MONAD_PRIVATE_KEY or not settings.MONAD_CONTRACT_ADDR:
        return False

    try:
        from web3 import AsyncWeb3
        from web3.middleware import async_geth_poa_middleware

        w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(settings.MONAD_RPC_URL))
        w3.middleware_onion.inject(async_geth_poa_middleware, layer=0)

        account = w3.eth.account.from_key(settings.MONAD_PRIVATE_KEY)

        # ABI mínimo — solo la función logEvent
        abi = [{
            "inputs": [{"internalType": "bytes32", "name": "eventHash", "type": "bytes32"}],
            "name": "logEvent",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        }]

        contract = w3.eth.contract(
            address=settings.MONAD_CONTRACT_ADDR,
            abi=abi,
        )

        # Convierte hex string a bytes32
        hash_bytes = bytes.fromhex(event_hash)

        tx = await contract.functions.logEvent(hash_bytes).build_transaction({
            "from":  account.address,
            "nonce": await w3.eth.get_transaction_count(account.address),
            "gas":   100_000,
        })

        signed = account.sign_transaction(tx)
        tx_hash = await w3.eth.send_raw_transaction(signed.rawTransaction)

        print(f"[BLOCKCHAIN OK] tx={tx_hash.hex()} hash={event_hash[:16]}...")
        return True

    except Exception as e:
        print(f"[BLOCKCHAIN ERROR] {e}")
        return False
