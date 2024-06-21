========
Overview
========

Design
------

One of the major design principles of the Jacquard is that model specification errors occur often, and ought to be produced in a format which is as readable as possible. Instead of getting the standard `NoneType has no attribute 'iterations'` or `KeyError: scenario`, Jacquard gives graceful messages like `Item 'iterations' is missing from jacquard <model.traffic_assignment>`. As a result, code which calls a Jacquard becomes self-validating. Jacquards are always ordered, and allow comments in C-style starting with `//` (these are stripped out during parsing).

Jacquard replaces:

.. code-block:: python

   from json import load

   fp = r"path/to/example.json"

   with open(fp) as reader:
       d = load(reader)

   assert "traffic_assignment" in d, "File '%s' is missing a traffic assignment section" % fp
   assert "iterations" in d['traffic_assignment'], "File '%s'.traffic_assignment is missing 'iterations" % fp
   n_iterations = int(d['traffic_assignment']['iterations'])

with

.. code-block:: python

   from jacquard import Jacquard

   config = Jacquard.from_file(r"path/to/example.json")

   n_iterations = config.traffic_assignment.iterations.as_int()

Usage
-----

The primary class in the package is the `Jacquard` object. Jacquards can be obtained through several class methods:

- `Jacquard.from_file(fp: Path-like)` reads from a JSON file. Raises `JacquardParseError` if it encounters an error while parsing.
- `Jacquard.from_string(s: str, **kwargs)` creates from an in-memory string (via `json.loads`).
- `Jacquard.from_dict(dict_, **kwargs)` creates from an in-memory dict. Dict keys are auto-converted to strings.

It is **strongly recommended** that JSON key names *follow Python variable naming conventions* and *do not duplicate reserved keywords*. All keys that follow the rules for Python identifiers become *attributes of the returned Jacquard object*.

Using a Jacquard to self-validate a file is best shown by example:

.. code-block:: json

   // example.json
   {
       "traffic_assignment": {
           "iterations": 100,  // Set to 0 to do a shortest-path assignment
           "best_relative_gap": 0.001,
           "demand_matrix": "Projects\\TTS Demand\\auto_demand.mdf",
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

.. code-block:: python

   from jacquard import Jacquard

   config = Jacquard.from_file(r"path/to/example.json")

   print('Name is:', config.name)
   print('Parent is: ', config.parent)
   # >> Name is: example
   # >> Parent is: <root>

Each attribute returns either a child `Jacquard` object (one which has sub-attributes) or a `JacquardValue` object at the end of the tree.

.. code-block:: python

   ...

   assignment_config = config.traffic_assignment
   print("Assignment sub-type", type(assignment_config))
   print("Assignment namespace", assignment_config.namespace)

   seed_config = config.world.random_seed
   print("Random seed sub-type", type(seed_config))
   print("Random seed namespace", seed_config.namespace)

   # >> Assignment sub-type type<Jacquard>
   # >> Assignment namespace example.traffic_assignment
   # >> Random seed sub-type type<JacquardValue>
   # >> Random seed namespace example.world.random_seed

`JacquardValue` objects expose several primitive conversion methods which handle proper type-checking:

.. code-block:: python

   ...

   n_iterations = assignment_config.iterations.as_int()
   br_gap = assignment_config.best_relative_gap.as_float()
   demand_matrix = assignment_jsd.demand_matrix.as_path()
   bg_traffic_flag = assignment_config.consider_background_traffic.as_bool()
