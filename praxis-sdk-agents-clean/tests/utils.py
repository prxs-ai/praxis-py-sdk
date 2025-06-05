from libp2p.host.basic_host import (
    BasicHost,
)
from collections.abc import (
    AsyncIterator,
)
from contextlib import (
    AsyncExitStack,
    asynccontextmanager,
)
from typing import (
    Any,
    Callable,
    cast,
)

import factory

from libp2p import (
    generate_new_rsa_identity,
    generate_peer_id_from,
)
from libp2p.abc import (
    ISecureTransport,
)
from libp2p.crypto.ed25519 import create_new_key_pair as create_ed25519_key_pair
from libp2p.crypto.keys import (
    KeyPair,
    PrivateKey,
)
from libp2p.crypto.secp256k1 import create_new_key_pair as create_secp256k1_key_pair
from libp2p.custom_types import (
    TMuxerOptions,
    TProtocol,
    TSecurityOptions,
)
from libp2p.network.swarm import (
    Swarm,
)
from libp2p.peer.id import (
    ID,
)
from libp2p.peer.peerstore import (
    PeerStore,
)
from libp2p.security.insecure.transport import (
    PLAINTEXT_PROTOCOL_ID,
    InsecureTransport,
)
from libp2p.security.noise.messages import (
    NoiseHandshakePayload,
    make_handshake_payload_sig,
)
from libp2p.security.noise.transport import PROTOCOL_ID as NOISE_PROTOCOL_ID
from libp2p.security.noise.transport import Transport as NoiseTransport
import libp2p.security.secio.transport as secio
from libp2p.stream_muxer.yamux.yamux import (
    Yamux,
)
from libp2p.tools.async_service.trio_service import (
    background_trio_service,
)
from libp2p.tools.constants import (
    LISTEN_MADDR,
)
from libp2p.transport.tcp.tcp import (
    TCP,
)
from libp2p.transport.upgrader import (
    TransportUpgrader,
)


DEFAULT_SECURITY_PROTOCOL_ID = PLAINTEXT_PROTOCOL_ID


def default_key_pair_factory() -> KeyPair:
    return generate_new_rsa_identity()


def yamux_transport_factory() -> TMuxerOptions:
    return {cast(TProtocol, "/yamux/1.0.0"): Yamux}


def default_muxer_transport_factory() -> TMuxerOptions:
    return yamux_transport_factory()


def initialize_peerstore_with_our_keypair(self_id: ID, key_pair: KeyPair) -> PeerStore:
    peer_store = PeerStore()
    peer_store.add_key_pair(self_id, key_pair)
    return peer_store


def noise_static_key_factory() -> PrivateKey:
    return create_ed25519_key_pair().private_key


def noise_handshake_payload_factory() -> NoiseHandshakePayload:
    libp2p_keypair = create_secp256k1_key_pair()
    noise_static_privkey = noise_static_key_factory()
    return NoiseHandshakePayload(
        libp2p_keypair.public_key,
        make_handshake_payload_sig(
            libp2p_keypair.private_key, noise_static_privkey.get_public_key()
        ),
    )


def plaintext_transport_factory(key_pair: KeyPair) -> ISecureTransport:
    return InsecureTransport(key_pair)


def secio_transport_factory(key_pair: KeyPair) -> ISecureTransport:
    return secio.Transport(key_pair)


def noise_transport_factory(key_pair: KeyPair) -> ISecureTransport:
    return NoiseTransport(
        libp2p_keypair=key_pair,
        noise_privkey=noise_static_key_factory(),
        with_noise_pipes=False,
    )


def security_options_factory_factory(
    protocol_id: TProtocol | None = None,
) -> Callable[[KeyPair], TSecurityOptions]:
    if protocol_id is None:
        protocol_id = DEFAULT_SECURITY_PROTOCOL_ID

    def security_options_factory(key_pair: KeyPair) -> TSecurityOptions:
        transport_factory: Callable[[KeyPair], ISecureTransport]
        if protocol_id == PLAINTEXT_PROTOCOL_ID:
            transport_factory = plaintext_transport_factory
        elif protocol_id == secio.ID:
            transport_factory = secio_transport_factory
        elif protocol_id == NOISE_PROTOCOL_ID:
            transport_factory = noise_transport_factory
        else:
            raise Exception(f"security transport {protocol_id} is not supported")
        return {protocol_id: transport_factory(key_pair)}

    return security_options_factory


class SwarmFactory(factory.Factory):
    class Meta:
        model = Swarm

    class Params:
        key_pair = factory.LazyFunction(default_key_pair_factory)
        security_protocol = DEFAULT_SECURITY_PROTOCOL_ID
        muxer_opt = factory.LazyFunction(default_muxer_transport_factory)

    peer_id = factory.LazyAttribute(lambda o: generate_peer_id_from(o.key_pair))
    peerstore = factory.LazyAttribute(
        lambda o: initialize_peerstore_with_our_keypair(o.peer_id, o.key_pair)
    )
    upgrader = factory.LazyAttribute(
        lambda o: TransportUpgrader(
            (security_options_factory_factory(o.security_protocol))(o.key_pair),
            o.muxer_opt,
        )
    )
    transport = factory.LazyFunction(TCP)

    @classmethod
    @asynccontextmanager
    async def create_and_listen(
        cls,
        key_pair: KeyPair | None = None,
        security_protocol: TProtocol | None = None,
        muxer_opt: TMuxerOptions | None = None,
    ) -> AsyncIterator[Swarm]:
        # `factory.Factory.__init__` does *not* prepare a *default value* if we pass
        # an argument explicitly with `None`. If an argument is `None`, we don't pass it
        # to `factory.Factory.__init__`, in order to let the function initialize it.
        optional_kwargs: dict[str, Any] = {}
        if key_pair is not None:
            optional_kwargs["key_pair"] = key_pair
        if security_protocol is not None:
            optional_kwargs["security_protocol"] = security_protocol
        if muxer_opt is not None:
            optional_kwargs["muxer_opt"] = muxer_opt
        swarm = cls(**optional_kwargs)
        async with background_trio_service(swarm):  # type: ignore
            await swarm.listen(LISTEN_MADDR)  # type: ignore
            yield swarm  # type: ignore

    @classmethod
    @asynccontextmanager
    async def create_batch_and_listen(
        cls,
        number: int,
        security_protocol: TProtocol | None = None,
        muxer_opt: TMuxerOptions | None = None,
    ) -> AsyncIterator[tuple[Swarm, ...]]:
        async with AsyncExitStack() as stack:
            ctx_mgrs = [
                await stack.enter_async_context(
                    cls.create_and_listen(
                        security_protocol=security_protocol, muxer_opt=muxer_opt
                    )
                )
                for _ in range(number)
            ]
            yield tuple(ctx_mgrs)


class HostFactory(factory.Factory):
    class Meta:
        model = BasicHost

    class Params:
        key_pair = factory.LazyFunction(default_key_pair_factory)
        security_protocol: TProtocol | None = None
        muxer_opt = factory.LazyFunction(default_muxer_transport_factory)

    network = factory.LazyAttribute(
        lambda o: SwarmFactory(
            security_protocol=o.security_protocol, # type: ignore
            muxer_opt=o.muxer_opt,  # type: ignore
        )
    )

    @classmethod
    @asynccontextmanager
    async def create_batch_and_listen(
        cls,
        number: int,
        security_protocol: TProtocol | None = None,
        muxer_opt: TMuxerOptions | None = None,
    ) -> AsyncIterator[tuple[BasicHost, ...]]:
        async with SwarmFactory.create_batch_and_listen(
            number, security_protocol=security_protocol, muxer_opt=muxer_opt
        ) as swarms:
            hosts = tuple(BasicHost(swarm) for swarm in swarms)
            yield hosts
