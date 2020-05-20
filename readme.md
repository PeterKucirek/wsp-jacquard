# Jacquard: JSON-based configuration for models

Historically, a [Jacquard machine is a programmable loom controlled by a chain of cards](https://en.wikipedia.org/wiki/Jacquard_machine); the term "jacquard" refers to the card (or set of cards) used to configure the machine. The `jacquard` library is designed to facilitate application of models, where the a model's configuration (locations of data, options, parameters) are stored in a human-readable JSON file. One of the major design principles of the Jacquard is that model specification errors occur often, and ought to be produced in a format which is as readable as possible. Instead of getting the standard `NoneType has no attribute 'iterations'` or `KeyError: scenario`, Jacquard gives graceful messages like `Item 'iterations' is missing from jacquard <model.traffic_assignment>`. As a result, code which calls a Jacquard becomes self-validating. Jacquards are always ordered, and allow comments in C-style starting with `//` (these are stripped out during parsing).

Jacquard replaces:

```python
from json import load

fp = r"path/to/example.json"

with open(fp) as reader:
    d = load(reader)

assert "traffic_assignment" in d, "File '%s' is missing a traffic assignment section" % fp
assert "iterations" in d['traffic_assignment'], "File '%s'.traffic_assignment is missing 'iterations" % fp
n_iterations = int(d['traffic_assignment']['iterations'])
```

with 

```python
from jacquard import Jacquard

jacquard = Jacquard.from_file(r"path/to/example.json")
n_iterations = jacquard.traffic_assignment.iterations.as_int()
```

(c) WSP Canada

## Installation

The easiest way is to install using `pip`:

`pip install git+http://github.com/wsp-sag/jacquard.git`

## Usage

The primary class in the package is the `Jacquard` object. Jacquards can be obtained through several class methods:

- `Jacquard.from_file(fp: Path-like)` reads from a JSON file. Raises `JacquardParseError` if it encounters an error while parsing.
- `Jacquard.from_string(s: str, **kwargs)` creates from an in-memory string (via `json.loads`).
- `Jacquard.from_dict(dict_, **kwargs)` creates from an in-memory dict. Dict keys are auto-converted to strings.

It is **strongly recommended** that JSON key names _follow Python variable naming conventions_ and _do not duplicate reserved keywords_. All keys that follow the rules for Python identifiers become _attributes of the returned Jacquard object_. 

Using a Jacquard to self-validate a file is best shown by example:

```javascript
// example.json
{
  "traffic_assignment": {
    "iterations": 100,  // Set to 0 to do a shortest-path assignment
    "best_relative_gap": 0.001,
    "demand_matrix": "Projects\\Mississauga\\auto_demand.mdf",
    "consider_background_traffic": true
  },
  "world": {
    "scenario_name": "2016 Base",
    "scenario_number": 501,
    "transit_modes": [
      "b",
      "r",
      "w"
    ],
  "random_seed": null
  }
}
```

```python
from jacquard import Jacquard
jcd = Jacquard.from_file(r"path/to/example.json")

print('Name is:', jcd.name)
print('Parent is: ', jcd.parent)
#>> Name is: example
#>> Parent is: <root>
```

 Each attribute returns either a child `Jacquard` object (one which has sub-attributes) or a `JacquardValue` object at the end of the tree. 
 
 ```python
...
assignment_jcd = jcd.traffic_assignment
print("Assignment sub-type", type(assignment_jcd))
print("Assignment namespace", assignment_jcd.namespace)

seed_jcd = jcd.random_seed
print("Random seed sub-type", type(seed_jcd))
print("Random seed namespace", seed_jcd.namespace)

# >> Assignment sub-type type<Jacquard>
# >> Assignment namespace example.traffic_assignment
# >> Random seed sub-type type<JacquardValue>
# >> Random seed namespace example.random_seed
```

`JacquardValue` objects expose several primitive conversion methods which handle proper type-checking:

```python
...
n_iterations = assignment_jcd.iterations.as_int()
br_gap = assignment_jcd.best_relative_gap.as_float()
demand_matrix = assignment_jsd.demand_matrix.as_path()
bg_traffic_flag = assignment_jcd.consider_background_traffic.as_bool()

```
