# P4PCore

P4PCore is an asynchronous Python library for peer-to-peer networking.

It is built around awaitable lifecycle methods and async message handling. Components such as the runner, network layers, event manager, and secure communication stack are designed to operate with Python's async model rather than blocking I/O.

The main structure is centered on a runner object that initializes the underlying network, attaches handler-based routing, and exposes separate layers for plain user traffic, encrypted traffic, and reachability checks. The project is intended for applications that need asynchronous communication, event-driven processing, and optional secure peer-to-peer messaging.

## Get Started

In pyproject.toml:

```toml
[project]
dependencies = [
    "P4PCore @ git+https://github.com/stsaria/P4PCore.git@<tag(version)-or-commit>"
]
```

For example:

```toml
[project]
dependencies = [
    "P4PCore @ git+https://github.com/stsaria/P4PCore.git@0.1.7"
]
```

In requirements.txt:

```txt
git+https://github.com/stsaria/P4PCore.git@<tag-or-commit>
```

After installation, import it as:

```python
from P4PCore.P4PRunner import P4PRunner
```
