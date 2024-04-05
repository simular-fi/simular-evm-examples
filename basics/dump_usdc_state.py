"""
Load state from on-chain USDC contract.
"""

import os
import json
from simular import (
    PyEvm,
    create_many_accounts,
    contract_from_inline_abi,
)

# USDC master minters address on chain
MM = "0xe982615d461dd5cd06575bbea87624fda4e3de17"

# https://etherscan.io/address/0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

ABI = [
    "function masterMinter() (address)",
    "function configureMinter(address, uint256) (bool)",
    "function isMinter(address) (bool)",
    "function minterAllowance(address) (uint256)",
    "function totalSupply() (uint256)",
    "function mint(address, uint256) (bool)",
    "function burn(uint256)",
]


def fetch_state_from_fork() -> str:
    # using my secret Alchemy API key (shhhh...) to call a remote node
    evm = PyEvm.from_fork(url=os.environ["ALCHEMY"])
    usdc = contract_from_inline_abi(evm, ABI)
    usdc.at(USDC)
    assert MM == usdc.masterMinter.call()

    return evm.create_snapshot()


def load_and_dump():
    snapshot = fetch_state_from_fork()
    evm = PyEvm.from_snapshot(snapshot)

    [m1, m2, m3] = create_many_accounts(evm, 3)

    # Since we're randomly generating user addresses
    # we need to save for future use...
    addresses = {"m1": m1, "m2": m2, "m3": m3}
    with open("./usdc_addresses.json", "w") as f:
        f.write(json.dumps(addresses, indent=" "))

    usdc = contract_from_inline_abi(evm, ABI)
    usdc.at(USDC)

    usdc.configureMinter.transact(m1, 10000000, caller=MM)
    usdc.configureMinter.transact(m2, 10000000, caller=MM)
    usdc.configureMinter.transact(m3, 10000000, caller=MM)

    assert 10000000 == usdc.minterAllowance.call(m1)
    assert 10000000 == usdc.minterAllowance.call(m2)
    assert 10000000 == usdc.minterAllowance.call(m3)

    final_state = evm.create_snapshot()

    with open("./usdc_cache.json", "w") as f:
        f.write(final_state)

    print("... done! ...")


if __name__ == "__main__":
    load_and_dump()
