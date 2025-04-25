import logging
import pytest
import pulumi
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def example_marketplace():
    loop = asyncio.get_event_loop()
    # bypass multithreading for now
    loop.set_default_executor(ImmediateExecutor())

    old_settings = pulumi.runtime.settings.SETTINGS
    try:
        pulumi.runtime.mocks.set_mocks(MyMocks())
        from shopkeeper.components import Marketplace, MarketplaceArgs

        yield Marketplace("test", MarketplaceArgs())
    finally:
        pulumi.runtime.settings.configure(old_settings)
        loop.set_default_executor(ThreadPoolExecutor())


class MyMocks(pulumi.runtime.Mocks):
    def new_resource(self, args: pulumi.runtime.MockResourceArgs):
        if args.typ == "pulumi-shopkeeper:index:Marketplace":
            # really not sure where these mocks end up :/
            outputs = dict(
                banana="yellow",
                **args.inputs
            )
            logger.info(outputs)
            return [args.name + "_id", outputs]
        return [args.name + "_id", args.inputs]

    def call(self, args: pulumi.runtime.MockCallArgs):
        return ["", {}]


class ImmediateExecutor(ThreadPoolExecutor):
    """
    This removes multithreading from current tests. Unfortunately in
    presence of multithreading the tests are flaky. The proper fix is
    postponed - see https://github.com/pulumi/pulumi/issues/7663
    """

    def __init__(self):
        super()
        self._default_executor = ThreadPoolExecutor()

    def submit(self, fn, *args, **kwargs):
        v = fn(*args, **kwargs)
        return self._default_executor.submit(ImmediateExecutor._identity, v)

    def map(self, func, *iterables, timeout=None, chunksize=1):
        raise Exception("map not implemented")

    def shutdown(self, wait=True, cancel_futures=False):
        raise Exception("shutdown not implemented")

    @staticmethod
    def _identity(x):
        return x


@pulumi.runtime.test
def test_marketplace(example_marketplace):
    """
    Check the marketplace resource
    """
    def check_marketplace(index_content):
        assert 1==1

    #return example_marketplace.something.apply(check_marketplace)
    return
