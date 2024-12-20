from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from wsp_jacquard import Jacquard

config_dict = {
    "traffic_assignment": {
        "iterations": 100,
        "best_relative_gap": 0.001,
        "demand_matrix": (Path("..").resolve() / 'demand.mdf').as_posix(),
        "consider_background_traffic": True
    },
    "world": {
        "scenario_name": "2016 Base",
        "scenario_number": 501,
        "transit_modes": [
            "b",
            "r",
            "w"
        ],
        "random_seed": None
    },
    "vdf": {
        "10": "fd1",
        "11": "fd2"
    }
}


def test_loading():
    from_dict = Jacquard.from_dict(config_dict).serialize()
    from_str = Jacquard.from_string(json.dumps(config_dict)).serialize()
    with TemporaryDirectory() as tempdir:
        fp = Path(tempdir) / 'config.json'
        with open(fp, mode='w') as f:
            json.dump(config_dict, f)
        from_file = Jacquard.from_file(fp).serialize()
    assert json.dumps(from_dict) == json.dumps(from_str)
    assert json.dumps(from_dict) == json.dumps(from_file)


def test_as_dict():
    config = Jacquard.from_dict(config_dict)
    assert json.dumps(config.vdf.as_dict(value_type=str)) == json.dumps(config_dict['vdf'])


def test_as_bool():
    config = Jacquard.from_dict(config_dict)
    assert config.traffic_assignment.consider_background_traffic.as_bool() == config_dict['traffic_assignment']['consider_background_traffic']


def test_as_int():
    config = Jacquard.from_dict(config_dict)
    assert config.traffic_assignment.iterations.as_int() == config_dict['traffic_assignment']['iterations']


def test_as_float():
    config = Jacquard.from_dict(config_dict)
    assert config.traffic_assignment.best_relative_gap.as_float() == config_dict['traffic_assignment']['best_relative_gap']


def test_as_str():
    config = Jacquard.from_dict(config_dict)
    assert config.world.scenario_name.as_str() == config_dict['world']['scenario_name']


def test_as_list():
    config = Jacquard.from_dict(config_dict)
    assert json.dumps(config.world.transit_modes.as_list(sub_type=str)) == json.dumps(config_dict['world']['transit_modes'])


def test_as_path():
    config = Jacquard.from_dict(config_dict)
    assert config.traffic_assignment.demand_matrix.as_path().as_posix() == config_dict['traffic_assignment']['demand_matrix']


def test_as_set():
    config = Jacquard.from_dict(config_dict)
    assert set(config.world.transit_modes.as_list(sub_type=str)) == set(config_dict['world']['transit_modes'])
