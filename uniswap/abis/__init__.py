from simular import PyAbi, Contract
from pathlib import Path

AGENT = "0xcfda354f04e741f2c902b86da7292ce9ef517039"
DAI = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
DAI_ADMIN = "0x9759A6Ac90977b93B58547b4A71c78317f391A28"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
UNISWAP_FACTORY = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
SWAP_ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564"

PATH = Path(__file__).parent


def uniswap_factory_contract(evm):
    with open(f"{PATH}/UniswapV3Factory.abi") as f:
        abi = f.read()
    abi = PyAbi.from_abi_bytecode(abi, None)
    return Contract(evm, abi).at(UNISWAP_FACTORY)


def uniswap_router_contract(evm):
    with open(f"{PATH}/SwapRouter.abi") as f:
        abi = f.read()
    abi = PyAbi.from_abi_bytecode(abi, None)
    return Contract(evm, abi).at(SWAP_ROUTER)


def uniswap_pool_contract(evm, pool_address):
    with open(f"{PATH}/UniswapV3Pool.abi") as f:
        abi = f.read()
    abi = PyAbi.from_abi_bytecode(abi, None)
    return Contract(evm, abi).at(pool_address)


def weth_contract(evm):
    with open(f"{PATH}/weth.abi") as f:
        abi = f.read()
    abi = PyAbi.from_abi_bytecode(abi, None)
    return Contract(evm, abi).at(WETH)


def dai_contract(evm):
    with open(f"{PATH}/dai.abi") as f:
        abi = f.read()
    abi = PyAbi.from_abi_bytecode(abi, None)
    return Contract(evm, abi).at(DAI)
