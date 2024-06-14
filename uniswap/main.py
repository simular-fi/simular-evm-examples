import os
import os.path
import typing
import argparse

import matplotlib.pyplot as plt
from eth_utils import is_address
from simular import PyEvm, create_account

import abis

FEE = 3000
NUM_RUNS = 500
SNAPSHOT = "uniswap_snapshot.json"


DEPOSIT = int(1e24)  # 1_000_000 eth


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

    # get token info from the pool contract
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
    tx = router_contract.exactInputSingle.transact(
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

    print(f"received: {tx.output/1e18} DAI for 1 Ether")
    snap = evm.create_snapshot()

    with open(SNAPSHOT, "w") as f:
        f.write(snap)


def run_transactions(num) -> typing.List[float]:
    with open(SNAPSHOT) as f:
        raw = f.read()
    evm = PyEvm.from_snapshot(raw)

    # load contracts
    router_contract = abis.uniswap_router_contract(evm)
    factory_contract = abis.uniswap_factory_contract(evm)

    # get pool info
    pool_address = factory_contract.getPool.call(abis.WETH, abis.DAI, FEE)
    pool_contract = abis.uniswap_pool_contract(evm, pool_address)

    # get token addresses
    token0 = pool_contract.token0.call()
    token1 = pool_contract.token1.call()

    # do a bunch of swaps. WETH for DAI
    data = []
    for _i in range(num):
        tx = router_contract.exactInputSingle.transact(
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

        amount = tx.output / 1e18
        data.append(amount)

    return data


def plot_data(steps, data):
    plt.style.use("_mpl-gallery")

    x = [i for i in range(0, steps)]
    y = data

    # plot
    fig, ax = plt.subplots(figsize=(5, 5), layout="constrained")
    ax.set_xlabel("Number of Trades")
    ax.set_ylabel("DAI for 1 WETH")
    fig.suptitle("DAI/WETH")
    ax.plot(x, y, linewidth=2.0)

    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py")
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Re-create the snapshot",
    )
    parser.add_argument(
        "--steps", type=int, default=NUM_RUNS, help="Number of steps to run"
    )

    args = parser.parse_args()

    if args.snapshot:
        print("generating snapshot...")
        fork_and_snapshot()
    else:
        print(f"making {args.steps} transactions...")
        data = run_transactions(args.steps)
        plot_data(args.steps, data)
