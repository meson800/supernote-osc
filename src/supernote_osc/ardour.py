"""
Various Ardour enums, flags, etc
"""

from dataclasses import dataclass
from enum import Enum, Flag
from typing import Dict, List


class ParameterOption(Flag):
    Enumeration = 1
    Integer = 2
    Logarithmic = 4
    SampleRateDependent = 32
    Toggled = 64
    Controllable = 128
    Hidden = 255


@dataclass
class ScalePoint:
    value: float
    name: str


@dataclass
class PluginParameter:
    param_id: int
    name: str
    options: ParameterOption
    dtype: str
    min_val: float
    max_val: float
    scale_points: List[ScalePoint]
    value: float


@dataclass
class StripPlugin:
    piid: int
    name: str
    enabled: bool
    parameters: Dict[int, PluginParameter]


class StripType(Enum):
    AudioTrack = "AT"
    MidiTrack = "MT"
    AudioBus = "B"
    MidiBus = "MB"
    FoldbackBus = "FB"
    VCA = "V"
    Master = "MA"


@dataclass
class Strip:
    name: str
    strip_type: StripType
    n_inputs: int
    n_outputs: int
    muted: bool
    soloed: bool
    ssid: int
    record_enabled: bool
    plugins: Dict[int, StripPlugin]
