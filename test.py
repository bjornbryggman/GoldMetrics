import json
import base64
import zlib
from pathlib import Path
from collections.abc import Iterator
import polars as pl
from structlog import stdlib

from slpp import slpp as lua

log = stdlib.get_logger(__name__)

def test(something) -> dict:
    """
    test `docs`

    Args:
        - 1: something
				- 2: something else

    Raises:
        - 1: something
				- 2: something else
    """
    try:
        log.info("This is a test message.")
    except Exception as error:
        log.exception(f"⚠️ {type(error).__name__}): {error}")
        return None



</example_function>
could be turned into:
<example_output_tables>
<Fact_Module>

</Fact_Module>
<Fact_Function>
id: primaryKey
module_id: foreignKey
header_id: int
docstring_id: int
logic_id: int
</Fact_Function>
<Dimension_Function_Header>
id: primaryKey
function_id: foreignKey(Facts_Function)
function_name: str
function_arguments: list
function_return: dict
</Dimension_Function_Header>
<Dimension_Function_Docstring>
id: primaryKey
function_id: foreignKey(Facts_Function)
docstring: str
</Dimension_Function_Docstring>
<Dimension_Function_Logic>
id: primaryKey
function_id: foreignKey(Facts_Function)
line_position:
</Dimension_Function_Logic>
</Module>
</example_output_tables>