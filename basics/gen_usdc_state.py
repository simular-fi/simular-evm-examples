"""
Load state from on-chain USDC contract.
"""

import os
from simular import (
    PyEvm,
    create_account,
    contract_from_inline_abi,
)

# USDC master minters address on chain
MM = "0xe982615d461dd5cd06575bbea87624fda4e3de17"

# The minter we'll create
MINTER = "0x7ac8a704a0dafcc12fc54679b940fc17de02950a"

# minter allowance (how much USDC they're allowed to mint)
# Remember USDC has 6 decimal places. So, 1e10 is 10,000 USDC
MINTER_ALLOWANCE = int(1e10)

# https://etherscan.io/address/0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"


# Define the abi we'll be using vs. loading abi from file
ABI = [
    "function masterMinter() (address)",
    "function configureMinter(address, uint256) (bool)",
    "function isMinter(address) (bool)",
    "function minterAllowance(address) (uint256)",
    "function totalSupply() (uint256)",
    "function mint(address, uint256) (bool)",
    "function burn(uint256)",
    "function balanceOf(address) (uint256)",
]


def fetch_state_from_fork() -> str:
    """
    This will load minimal state from the live USDC contract on Ethereum main we'll
    use for a snapshot.  By touching the contract, it'll pull down the bytecode. Calling
    any method on the contract will pull in the associated state. We can then take a snapshot
    and save this to reload later.

    Note:
    You need access to remote Ethereum RPC node or service to read on-chain data.
    For this example, I'm using my secret Alchemy API key (shhhh...) to call a remote node
    """

    # Setup the EVM to pull information from a remote node
    evm = PyEvm.from_fork(url=os.environ["ALCHEMY"])
    # load the contract from the ABI.
    usdc = contract_from_inline_abi(evm, ABI)
    # set the contract address to the deployed contract address
    usdc.at(USDC)

    # check the remote minter matches the address we looked up on etherscan
    # this will also store the state in the contract.
    assert MM == usdc.masterMinter.call()

    # take a snapshot of the state
    return evm.create_snapshot()


def load_and_dump():
    """
    Here we'll load pull the snapshot from 1 EVM and the load into a local
    in-memory EVM. We'll interact with the contract to make some initial state
    then save it as a new snapshot to use in the `forks` notebook
    """
    snapshot = fetch_state_from_fork()

    # load an evm from the snapshot
    evm = PyEvm.from_snapshot(snapshot)

    # Create an account in the EVM for the minter we'll use.
    # note: we create a account based on an address
    # we generated separately to be able to re-use it in the notebook
    create_account(evm, address=MINTER)

    # create an instance of the contract
    # we don't need to deploy it, because we already saved it
    # with our snapshot
    usdc = contract_from_inline_abi(evm, ABI)
    usdc.at(USDC)

    # Master minter allows MINTER to mint 10,000 USDC
    usdc.configureMinter.transact(MINTER, MINTER_ALLOWANCE, caller=MM)

    # Confirm allowance
    assert int(1e10) == usdc.minterAllowance.call(MINTER)

    # create and save the new snapshot
    final_state = evm.create_snapshot()
    with open("./usdc_snapshot.json", "w") as f:
        f.write(final_state)

    print("... done! ...")


if __name__ == "__main__":
    load_and_dump()
