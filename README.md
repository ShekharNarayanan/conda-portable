# conda-portable 🧳🐍

Port your environment.yml across platforms. From any platform.


## 🚀 Why did I make this?

Conda environment files built on Windows machines break on MacOS. Often. There is always [conda-lock](https://github.com/conda/conda-lock), but it requires a clean specification file to start with. This repository gives you that file. 💨


conda-portable a platform-specific environment.yml and generates:

✅ a cleaned environment.portable.yml

✅ a multi-platform conda-lock.yml (Linux, macOS, Windows)

**So your environment can be reproduced anywhere. But there is a catch (read: many catches 👻)**

## ❌ What it doesn't do
1. Right now the tool just uses a fixed list of OS-specific packages, my point here is to keep this list as minimal as possible- so no dependencies are skipped.

2. I don’t actually solve dependencies myself — I leave that to conda-lock, which will still blow up if the environment can’t be solved.

3. Pip packages can be tagged per platform, but conda packages can’t, so those just get dropped instead of being conditionally included.

## 👎 If conda-lock fails for your use-case:

1. Some package that is indeed specific to a platform and is very common is not in the list. I am happy to add it 🎁
2. Some packages are not developed from cross-platform use. Unfortunately, I cannot do much about that but break your code to tell you this 😁

If there is anything else, please feel free to open an issue. 


## ✨ Features

1. Strip platform runtimes (vc14_runtime, ucrt, libwinpthread, llvm-openmp, libgcc-ng, …)

2. Tag OS-specific pip deps with markers (e.g. pywin32 ; platform_system == "Windows")

3. Verify with conda-lock automatically → generates lockfile for win-64, osx-arm64, and linux-64.

## 🔧 Installation

Clone the repo and install locally:
```bash
git clone https://github.com/ShekharNarayanan/conda-portable
cd conda-portable
pip install -e .
```

Make sure you also have conda-lock available:
```bash
pip install conda-lock
```

## 🖥️ Usage
Convert and verify in one go:
```bash
cd project/with/environment/file

conda-portable --env environment.yml --from_platform Windows
```

This will:

1. Write environment.portable.yml next to your input file

2. Run conda-lock for win-64, osx-arm64, and linux-64

Produce conda-lock.yml

Other platforms

If the env file was exported on Linux or macOS:

```bash
conda-portable --env environment.yml --from_platform Linux
conda-portable --env environment.yml --from_platform MacOS
```

## 📦 Example

Input environment.yml (exported on Windows):

name: demo
channels:
  - conda-forge
dependencies:
  - python=3.12
  - numpy
  - vc14_runtime
  - pip:
    - requests
    - pywin32


Output environment.portable.yml:

name: demo
channels:
  - conda-forge
dependencies:
  - python=3.12
  - numpy
  - pip:
    - requests
    - pywin32 ; platform_system == "Windows"


Lockfile conda-lock.yml will contain exact solves for win-64, osx-arm64, linux-64.


🧑‍💻 Contributing

PRs and issues welcome! If you run into an env that doesn’t port cleanly, open an issue with your environment.yml so we can extend the rules in common_packages.yaml
