import os
import os.path
import typing

import matplotlib.pyplot as plt
from eth_utils import is_address
from simular import PyEvm, create_account

import abis

FEE = 3000
NUM_RUNS = 500
CACHE_FILE = "diaweth.json"


q96 = 2**96
DEPOSIT = int(1e24)  # 1_000_000 eth


def sqrtp_to_price(sqrtp):
    return (sqrtp / q96) ** 2


def token0_price(sqrtp):
    sp = sqrtp_to_price(sqrtp)
    return sp


def token1_price(sqrtp):
    t0 = token0_price(sqrtp)
    return 1 / t0


def fetch_price_without_saving():
    evm = PyEvm.from_fork(url=os.environ["ALCHEMY"])
    factory_contract = abis.uniswap_factory_contract(evm)

    # get the pool address
    pool_address = factory_contract.getPool.call(abis.WETH, abis.DAI, FEE)
    assert is_address(pool_address)
    pool_contract = abis.uniswap_pool_contract(evm, pool_address)

    sqrtp = pool_contract.slot0.call()[0]
    print(f"pool address : {pool_address}")
    print(f"sqrtp        : {sqrtp}")
    dai_price = token1_price(sqrtp)
    print(f"dai for 1 eth: {dai_price}")


def fork_and_snapshot():
    evm = PyEvm.from_fork(url=os.environ["ALCHEMY"])

    # load contracts
    dai_contract = abis.dai_contract(evm)
    weth_contract = abis.weth_contract(evm)
    router_contract = abis.uniswap_router_contract(evm)
    factory_contract = abis.uniswap_factory_contract(evm)

    # create accounts for agent and dia admin
    create_account(evm, address=abis.AGENT, value=DEPOSIT)
    create_account(evm, address=abis.DAI_ADMIN, value=DEPOSIT)

    # get the pool address
    pool_address = factory_contract.getPool.call(abis.WETH, abis.DAI, FEE)
    assert is_address(pool_address)
    pool_contract = abis.uniswap_pool_contract(evm, pool_address)

    # get token info
    token0 = pool_contract.token0.call()
    token1 = pool_contract.token1.call()
    pool_contract.slot0.call()

    # fund and approve weth
    weth_contract.deposit.transact(caller=abis.AGENT, value=DEPOSIT)
    weth_contract.approve.transact(abis.SWAP_ROUTER, DEPOSIT, caller=abis.AGENT)

    # mint and approve dai
    dai_contract.mint.transact(abis.AGENT, DEPOSIT, caller=abis.DAI_ADMIN)
    dai_contract.approve.transact(abis.SWAP_ROUTER, DEPOSIT, caller=abis.AGENT)

    # confirm balances
    wbal = weth_contract.balanceOf.call(abis.AGENT)
    dbal = dai_contract.balanceOf.call(abis.AGENT)
    assert wbal == DEPOSIT
    assert dbal == DEPOSIT

    # verify allowance for uniswap router
    daia = dai_contract.allowance.call(abis.AGENT, abis.SWAP_ROUTER)
    wetha = weth_contract.allowance.call(abis.AGENT, abis.SWAP_ROUTER)
    assert wetha == DEPOSIT
    assert daia == DEPOSIT

    # make a single swap
    swapped = router_contract.exactInputSingle.transact(
        (
            token1,
            token0,
            FEE,
            abis.AGENT,
            int(1e32),
            int(1e18),
            0,
            0,
        ),
        caller=abis.AGENT,
    )

    print(f"received: {swapped/1e18} DAI for 1 Ether")
    snap = evm.create_snapshot()

    with open(CACHE_FILE, "w") as f:
        f.write(snap)


def run_transactions() -> typing.List[float]:
    with open(CACHE_FILE) as f:
        raw = f.read()
    evm = PyEvm.from_snapshot(raw)

    # load contracts
    router_contract = abis.uniswap_router_contract(evm)
    factory_contract = abis.uniswap_factory_contract(evm)

    # get pool info
    pool_address = factory_contract.getPool.call(abis.WETH, abis.DAI, FEE)
    pool_contract = abis.uniswap_pool_contract(evm, pool_address)

    # get token info
    token0 = pool_contract.token0.call()
    token1 = pool_contract.token1.call()

    # do a bunch of swaps. WETH for DAI
    data = []
    for _i in range(NUM_RUNS):
        swapped = router_contract.exactInputSingle.transact(
            (
                token1,
                token0,
                FEE,
                abis.AGENT,
                int(1e32),
                int(1e18),
                0,
                0,
            ),
            caller=abis.AGENT,
        )
        amount = swapped / 1e18
        data.append(amount)

    return data


def plot_data(data):
    plt.style.use("_mpl-gallery")

    x = [i for i in range(0, NUM_RUNS)]
    y = data

    # plot
    fig, ax = plt.subplots(figsize=(5, 5), layout="constrained")
    ax.set_xlabel("SWAPS")
    ax.set_ylabel("DAI")
    fig.suptitle("DAI for 1 Ether")
    ax.plot(x, y, linewidth=2.0)

    plt.show()


if __name__ == "__main__":
    # fork_and_snapshot()
    # fetch_price_without_saving()
    data = run_transactions()
    plot_data(data)
