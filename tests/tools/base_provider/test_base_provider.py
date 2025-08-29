import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from fastapi.security import HTTPAuthorizationCredentials

from base_provider.contract.config import BaseDataContractConfig
from base_provider.ray_entrypoint import (
    BaseProvider,
    provider_builder,
    get_provider_config,
    AbstractDataProvider
)
from base_provider.config import BaseProviderConfig
from base_provider.contract.base import BaseDataContract, get_data_contract
from base_provider.sinks.config import KafkaDataSinkConfig
from base_provider.stream.base import BaseDataStream
from base_provider.runner.base import BaseDataRunner
from base_provider.sinks.base import BaseDataSink
from base_provider.sinks.kafka import KafkaDataSink
from base_provider.sources.base import BaseDataSource
from base_provider.processors.base import BaseDataProcessor
from base_provider.triggers.base import BaseDataTrigger
from base_provider.exceptions import (
    AsyncNotSupportedException,
    SyncNotSupportedException
)


@pytest.fixture
def mock_config():
    return BaseProviderConfig(
        title="Test",
        description="Test",
        domain="test",
        version="v1",
        kafka_bootstrap_uri="mock://kafka",
        sinks='{"kafka": {"bootstrap_uri": "mock://kafka"}}'
    )


@pytest.fixture(autouse=True)
def kafka_config():
    return KafkaDataSinkConfig(kafka_bootstrap_uri="mock://kafka")


@pytest.fixture
def mock_contract():
    contract = BaseDataContract(MagicMock())
    contract._spec = {"test": "spec"}
    contract.supported_modes = {"SYNC", "ASYNC"}
    return contract


@pytest.fixture
def mock_stream():
    stream = BaseDataStream(MagicMock())
    stream.sources = {"test": AsyncMock()}
    stream.processors = {"test": AsyncMock()}
    stream.sinks = {"test": AsyncMock()}
    stream.fetch_batch = AsyncMock(return_value={"test": ["data"]})
    stream.process_batch = AsyncMock(return_value={"processed": "data"})
    return stream


@pytest.fixture
def mock_runner():
    runner = BaseDataRunner(MagicMock())
    runner.run_once = AsyncMock(return_value="result")
    runner.run = AsyncMock()
    return runner


@pytest.fixture
def provider(mock_config):
    provider = BaseProvider(mock_config)
    provider._contract = BaseDataContract(BaseDataContractConfig())
    provider._contract._spec = {"test": "spec"}
    return provider


def test_contract_initialization(mock_config):
    contract = BaseDataContract(mock_config)
    assert contract.config == mock_config
    assert contract.supported_modes is not None


def test_contract_build_spec(mock_config):
    contract = BaseDataContract(mock_config)
    assert hasattr(contract, '_spec')


def test_contract_spec_property(mock_contract):
    assert mock_contract.spec == {"test": "spec"}


def test_contract_mode_support():
    contract = BaseDataContract(BaseDataContractConfig())
    contract.supported_modes = {"SYNC", "ASYNC"}
    assert contract.supports_sync is True
    assert contract.supports_async is True


@pytest.mark.asyncio
async def test_provider_query(provider):
    provider.runner.run_once = AsyncMock(return_value="result")
    result = await provider.query({"filter": "test"})
    assert result == "result"


@pytest.mark.asyncio
async def test_provider_query_sync_not_supported(provider):
    provider._contract.supported_modes = {"ASYNC"}
    with pytest.raises(SyncNotSupportedException):
        await provider.query({"filter": "test"})


@pytest.mark.asyncio
async def test_provider_subscribe(provider):
    topic = await provider.subscribe({"filter": "test"})
    assert topic.startswith("test.v1.")
    provider.runner.run.assert_called_once()


@pytest.mark.asyncio
async def test_provider_subscribe_async_not_supported(provider):
    provider._contract.supported_modes = {"SYNC"}
    with pytest.raises(AsyncNotSupportedException):
        await provider.subscribe({"filter": "test"})


def test_provider_generate_run_hash(provider):
    filters = {"param": "value"}
    hash_str = provider._generate_run_hash(filters)
    assert len(hash_str) == 7

    assert hash_str == provider._generate_run_hash(filters)


@pytest.mark.asyncio
async def test_stream_processing(mock_stream):
    result = await mock_stream.process_batch({"test": ["data"]}, {})
    assert result == {"processed": "data"}


@pytest.mark.asyncio
async def test_stream_fetch_batch(mock_stream):
    result = await mock_stream.fetch_batch()
    assert result == {"test": ["data"]}


@pytest.mark.asyncio
async def test_runner_execution(mock_runner, mock_stream):
    await mock_runner.run_once(mock_stream, filters={})
    mock_runner.run_once.assert_called_once()


@pytest.mark.asyncio
async def test_full_flow(provider):
    result = await provider.query({"test": "filter"})
    assert result == "result"

    topic = await provider.subscribe({"test": "filter"})
    assert isinstance(topic, str)


@pytest.mark.asyncio
async def test_authentication(provider):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    result = await provider.authenticate(credentials)
    assert result is True


def test_config_loading():
    with patch.dict('os.environ', {
        'TITLE': 'Test',
        'DESCRIPTION': 'Desc',
        'DOMAIN': 'test',
        'VERSION': 'v1',
        'KAFKA_BOOTSTRAP_URI': 'kafka://test'
    }):
        config = get_provider_config()
        assert config.domain == "test"


def test_provider_builder():
    with patch('base_provider.ray_entrypoint.BaseProvider') as mock_provider:
        builder = provider_builder({})
        assert builder is not None


@pytest.mark.asyncio
async def test_stream_error_handling():
    bad_stream = BaseDataStream(MagicMock())
    bad_source = AsyncMock()
    bad_source.fetch.side_effect = Exception("Failed")
    bad_stream.sources = {"test": bad_source}

    with pytest.raises(Exception, match="Failed"):
        await bad_stream.fetch_batch()


def test_contract_without_build_spec(mock_config):
    contract = BaseDataContract(mock_config)
    with pytest.raises(ValueError):
        _ = contract.spec


def test_contract_build_roles(mock_config):
    contract = BaseDataContract(mock_config)
    roles = contract._build_roles()
    assert len(roles) == 1
    assert roles[0].name == "consumer"


def test_contract_build_terms(mock_config):
    contract = BaseDataContract(mock_config)
    terms = contract._build_terms()
    assert "usage" in terms
    assert "limitations" in terms


@pytest.mark.asyncio
async def test_provider_with_invalid_contract(provider):
    provider._contract = None
    with pytest.raises(AttributeError):
        await provider.query({"test": "filter"})


@pytest.mark.asyncio
async def test_provider_get_topic_name(provider):
    topic = provider._get_topic_name("events", "abc1234")
    assert topic == "test.v1.events.abc1234"


@pytest.mark.asyncio
async def test_stream_process_item(mock_stream):
    mock_stream.processors["test"].process.return_value = "processed"
    result = await mock_stream.process_item("data", {})
    assert result == "processed"


@pytest.mark.asyncio
async def test_stream_write_batch(mock_stream):
    mock_stream.sinks["test"].write = AsyncMock()
    await mock_stream.write_batch({"test": ["data"]})
    mock_stream.sinks["test"].write.assert_called()


@pytest.mark.asyncio
async def test_base_sink_write():
    sink = BaseDataSink(MagicMock())
    result = await sink.write("data")
    assert result == "data"


@pytest.mark.asyncio
async def test_kafka_sink_connect():
    mock_broker = AsyncMock()
    sink = KafkaDataSink(MagicMock(), mock_broker)
    await sink.connect()
    assert sink.is_connected is True


@pytest.mark.asyncio
async def test_base_source_fetch():
    source = BaseDataSource(MagicMock())
    result = await source.fetch()
    assert result == []


@pytest.mark.asyncio
async def test_base_processor_process():
    processor = BaseDataProcessor(MagicMock())
    result = await processor.process("data")
    assert result == "data"


@pytest.mark.asyncio
async def test_base_trigger_raises():
    trigger = BaseDataTrigger(MagicMock())
    with pytest.raises(NotImplementedError):
        await trigger.trigger()


def test_config_default_values():
    config = BaseProviderConfig(
        title="Test",
        description="Test",
        domain="test",
        version="v1",
        kafka_bootstrap_uri="test"
    )
    assert config.kafka_topic_template == "{domain}.{version}.{data_type}.{topic_spec_hash}"
    assert config.kafka_message_format == "msgpack"


def test_get_data_contract_singleton():
    import base_provider.contract
    base_provider.contract.get_data_contract.cache_clear()

    contract1 = get_data_contract()
    contract2 = get_data_contract()
    assert contract1 is contract2


@pytest.mark.asyncio
async def test_stream_with_empty_components():
    empty_stream = BaseDataStream(MagicMock())
    with pytest.raises(AttributeError):
        await empty_stream.fetch_batch()


@pytest.mark.asyncio
async def test_provider_invalid_authentication(provider):
    provider.authenticate = AsyncMock(return_value=False)
    with pytest.raises(PermissionError):
        await provider.query({"test": "filter"})


def test_provider_properties(provider):
    assert provider.domain == "test"
    assert provider.version == "v1"


@pytest.mark.asyncio
async def test_provider_empty_filters(provider):
    result = await provider.query({})
    assert result == "result"


@pytest.mark.asyncio
async def test_stream_empty_batch_processing(mock_stream):
    result = await mock_stream.process_batch({}, {})
    assert result == {"processed": "data"}


@pytest.mark.asyncio
async def test_complex_runner_execution():
    mock_stream = MagicMock()
    mock_stream.fetch_batch = AsyncMock(return_value={"src": [1, 2, 3]})
    mock_stream.process_batch = AsyncMock(return_value={"processed": [1, 2, 3]})

    runner = BaseDataRunner(MagicMock())
    await runner.run_once(mock_stream, filters={"test": "filter"})

    mock_stream.fetch_batch.assert_called_once()
    mock_stream.process_batch.assert_called_once()


@pytest.mark.asyncio
async def test_kafka_sink_state():
    with patch('faststream.kafka.KafkaBroker'):
        sink = KafkaDataSink(AsyncMock(), AsyncMock())
        assert sink.is_connected is False
        await sink.connect()
        assert sink.is_connected is True
        await sink.write("data", topic="test")
        assert sink.is_connected is True


def test_contract_spec_types(mock_contract):
    spec = mock_contract.spec
    assert isinstance(spec, dict)
    assert "test" in spec


@pytest.mark.asyncio
async def test_stream_parallel_processing(mock_stream):
    import time
    start = time.time()
    mock_stream.process_batch = AsyncMock(side_effect=lambda x, _: {k: [v * 2 for v in vs] for k, vs in x.items()})

    batch = {f"src_{i}": list(range(100)) for i in range(10)}
    await mock_stream.process_batch(batch, {})

    elapsed = time.time() - start
    assert elapsed < 1.0


def test_config_serialization(mock_config):
    json_str = mock_config.model_dump_json()
    assert "domain" in json_str
    assert "kafka_bootstrap_uri" in json_str


@pytest.mark.asyncio
async def test_kafka_sink_operations(kafka_config):
    mock_broker = AsyncMock()
    sink = KafkaDataSink(kafka_config, mock_broker)

    await sink.connect()
    assert sink.is_connected is True

    await sink.write("data", topic="test")
    mock_broker.publish.assert_called_once()
