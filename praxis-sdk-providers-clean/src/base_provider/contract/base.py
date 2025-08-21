from typing import Any

from base_provider.abc import AbstractDataContract, DataMode
from base_provider.contract.config import BaseDataContractConfig, get_data_contract_config
from base_provider.contract.models import ContractSpecification, DataModel, Policy, Role, ServerSpec, ServiceLevel
from fast_depends import Depends, inject


class BaseDataContract(AbstractDataContract):
    """Base implementation of data contract."""

    def __init__(self, config: BaseDataContractConfig):
        self.config = config
        self._spec = None
        self.supported_modes = DataMode.all()

    def build_spec(
        self,
        domain: str,
        version: str,
        title: str,
        description: str,
        models: dict[str, Any],
        servers: dict[str, Any],
        service_levels: dict[str, Any],
        supported_modes: set[DataMode] = None,
    ):
        if supported_modes is None:
            supported_modes = DataMode.all()
        self.supported_modes = supported_modes

        self._spec = ContractSpecification(
            data_contract_specification=self.config.data_contract_version,
            id=self.config.data_contract_uid_template.format(domain=domain, version=version),
            info=self._build_info(title, version, description),
            servers={server_name: ServerSpec(**server) for server_name, server in servers.items()},
            roles=self._build_roles(),
            terms=self._build_terms(),
            policies=self._build_policies(),
            models={model_name: DataModel(**model) for model_name, model in models.items()},
            service_levels=ServiceLevel(**service_levels),
            tags=[],
            supported_modes=supported_modes,
        )

    @staticmethod
    def _build_info(title, version, description):
        return {
            "title": title,
            "version": version,
            "description": description,
        }

    @staticmethod
    def _build_roles():
        return [Role(name="consumer", description="read-only access")]

    @staticmethod
    def _build_terms():
        return {
            "usage": "Data usage terms go here",
            "limitations": "Data limitations go here",
        }

    @staticmethod
    def _build_policies():
        return [Policy(name="privacy-policy", url="https://example.com/privacy-policy")]

    @property
    def spec(self) -> dict[str, Any]:
        if self._spec is None:
            raise ValueError("Contract specification has not been built yet.")
        return self._spec.model_dump()

    @property
    def supports_sync(self) -> bool:
        return DataMode.SYNC in self.supported_modes

    @property
    def supports_async(self) -> bool:
        return DataMode.ASYNC in self.supported_modes


@inject
def get_data_contract(config: BaseDataContractConfig = Depends(get_data_contract_config)) -> BaseDataContract:
    return BaseDataContract(config)
