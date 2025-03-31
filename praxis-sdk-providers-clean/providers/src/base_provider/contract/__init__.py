from base_provider.abc import AbstractDataContract
from base_provider.const import EntrypointGroup
from base_provider.utils import get_entrypoint


def contract_builder(*args, **kwargs) -> AbstractDataContract:
    try:
        return get_entrypoint(EntrypointGroup.DATA_CONTRACT_ENTRYPOINT).load()(*args, **kwargs)
    except Exception:
        from base_provider.contract.base import get_data_contract as get_default_data_contract

        return get_default_data_contract(*args, **kwargs)
