# businessglossary

> A research plan for building and managing a business glossary.

## Overview

`businessglossary` is a Python library designed to help organizations define, manage, and share a consistent business glossary — a centralized repository of business terms, definitions, and metadata that promotes shared understanding across teams.

This project is built with [nbdev](https://nbdev.fast.ai/), meaning the source notebooks serve as both the documentation and the library source.

## Install

```
pip install businessglossary
```

## How to use

```python
from businessglossary.core import say_hello

say_hello("World")
# 'Hello World!'
```

## Development

This project uses [nbdev](https://nbdev.fast.ai/) for literate programming. To contribute:

1. Clone the repository:
   ```
   git clone https://github.com/{user}/businessglossary.git
   cd businessglossary
   ```

2. Install the development dependencies and set up hooks:
   ```
   pip install nbdev
   nbdev_install_git_hooks
   ```

3. Edit the notebooks (e.g. `00_core.ipynb`) and run:
   ```
   nbdev_build_lib
   ```

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## License

Copyright 2024 janru.muller

Licensed under the [Apache License 2.0](LICENSE).
