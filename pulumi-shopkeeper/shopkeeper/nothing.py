import logging
from dataclasses import dataclass
from typing import Optional

from pulumi import ComponentResource, Input, ResourceOptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass()
class NothingArgs:
    something: Input[str]


class Nothing(ComponentResource):
    def __init__(
        self, name: str, args: NothingArgs, opts: Optional[ResourceOptions] = None
    ):
        super().__init__(
            t="pulumi-shopkeeper:index:Nothing",
            name=name,
            props={},
            opts=opts,
        )
        # No outputs or properties to register
        logger.info(f"Initialized {self.__class__.__name__} with name {name}")
        self.register_outputs({})
