import yaml
import importlib.resources as resources
import subprocess
import pathlib

def base_name(spec: str) -> str:
    """Extract the base name from a package specification.

    Args:
        spec (str): Package specification string, e.g. "numpy>=1.18.0; python_version >= '3.6'"

    Returns:
        str:    Base name of the package, lowercased and stripped of version and platform info.
    """
    spec = spec.split(";", 1)[0].strip()
    spec = spec.split("[", 1)[0]
    for sep in ("===", "==", ">=", "<=", "!=", "~=", "=", ">", "<"):
        if sep in spec:
            spec = spec.split(sep, 1)[0]
            break
    return spec.strip().lower()

def _strip_mkl_and_pin_openblas(dep_list: list) -> list:
    """
    Remove MKL/OpenMP deps and enforce OpenBLAS for portability.
    Drops: {"mkl", "mkl-service", "intel-openmp", "openmp"}.
    Ensures 'libblas=*=*openblas' is present.
    """
    drop_names = {"mkl", "mkl-service", "intel-openmp", "openmp"} # Windows specific packages for math/ linear algebra
    # -> these are not needed on Linux/MacOS and can cause issues
    kept, has_openblas = [], False

    for d in dep_list:
        if isinstance(d, str):
            name = base_name(d) # collect base name of the dependency
            if name in drop_names: # -> check if it is a package to drop
                continue
            if name == "libblas" and "*openblas" in d: # -> check the dependency list it already has OpenBLAS as a dependency
                has_openblas = True
        kept.append(d) # -> keep the dependency if not a string (like the pip section) 
    # -> if OpenBLAS is not in the list, add it to the top -> this makes conda opt for OpenBLAS instead of MKL which helps with portability on Linux/MacOS
    if not has_openblas: 
        kept.insert(0, "libblas=*=*openblas")
    return kept

def _load_common_packages() -> dict:
    """Load common packages configuration from the common_packages YAML file.

    Returns:
        dict: A dictionary containing common packages for different platforms.
    """
    with resources.files("conda_portable").joinpath("common_packages.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def _print_box(msg: str):
    """
    Print a message in a box format for better visibility.

    Args:
        msg (str): The message to print inside the box.
    """
    border = "*" * (len(msg) + 4)
    print(border)
    print(f"* {msg} *")
    print(border)

def _tag_pip_packages(dependency_dict:dict, drop_platform_specific_pip: set, from_platform: str) -> str:
    """ Drop platform-specific pip packages and tag them with the platform.

    Args:
        dependency_dict (dict): All dependencies from the environment file.
        drop_platform_specific_pip (set): pip dependencies to drop based on the platform.
        from_platform (str): platform from which the environment was exported.

    Returns:
        str: pip package name with the platform tag.
    """
    tagged_packages = []
    for p in dependency_dict.get("pip") or []: # -> get the pip dict or fall back to empty list
                # ->1. check if package is string, 2. base_name is contained common pip packages and 3. is not already marked"
                if isinstance(p, str) and base_name(p) in drop_platform_specific_pip and ";" not in p: 
                    p = f'{p} ; platform_system == "{from_platform}"' # mark pip packages with platform tag 
                tagged_packages.append(p) # -> append the package to the list
                
    return tagged_packages
    

def make_portable(inp: pathlib.Path, outp: pathlib.Path, from_platform: str = "Windows") -> None:
    """
    Convert a conda environment file to a portable format by adjusting dependencies
    based on the specified platform. For ex, specifying "Windows" will
    remove Windows-specific packages and tag pip packages accordingly, making them usable
    on macosx and linux based platforms.

    Args:
        inp (Path): Path to the input environment file.
        outp (Path):   Path to the output environment now portable) file.
        from_platform (str, optional): The platform from which the base environment is made. Defaults to "Windows".


    """
    # display status of pipeline
    _print_box("Making environment portable")

    # load yaml file containig packages
    data = yaml.safe_load(inp.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "dependencies" not in data:
        raise SystemExit("ERROR: no 'dependencies' in environment file")

    # remove channel_priority and prefix if they exist
    data.pop("channel_priority", None)
    data.pop("prefix", None)

    # load common packages 
    packages_all_platforms = _load_common_packages()
    # filter according to the platform
    package_specific_platform = packages_all_platforms.get(from_platform, {"conda": [], "pip": []})

    # define sets for conda and pip packages to drop according to the platform
    drop_platform_specific_conda = set(x.lower() for x in package_specific_platform.get("conda", []))
    drop_platform_specific_pip   = set(x.lower() for x in package_specific_platform.get("pip", []))

    # get all dependencies from the environment file
    deps = data.get("dependencies", [])
    new_deps, pip_section = [], None

    for item in deps:
        if isinstance(item, dict) and "pip" in item: # -> look for pip dictionary inside the dependency list
            tagged_packages = _tag_pip_packages(item, drop_platform_specific_pip, from_platform)
            pip_section = {"pip": tagged_packages}
            continue
        if isinstance(item, str):  # -> go through str entries in the conda dependency list before pip
            if base_name(item) in drop_platform_specific_conda:  # -> ignore conda packages that are platform specific
                continue
            new_deps.append(item)  # -> keep valid conda dependency
        else:
            # -> any other structure (rare in practice), just preserve as-is
            new_deps.append(item)

    if pip_section:
        new_deps.append(pip_section)

    # ensure OpenBLAS is used and MKL/OpenMP packages are removed
    new_deps = _strip_mkl_and_pin_openblas(new_deps)

    # write the modified environment file
    data["dependencies"] = new_deps
    outp.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    print(f"✅ wrote {outp} (from {from_platform})")

def run_conda_lock(env_file: pathlib.Path, *, platforms=None) -> None:
    """Create a multi-platform conda-lock.yml from env_file."""
    if platforms is None:
        platforms = ["win-64", "osx-arm64", "linux-64"]

    # ensure conda-lock is available
    try:
        subprocess.run(["conda-lock", "--version"], check=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        raise SystemExit("ERROR: conda-lock not found. Install with: pip install conda-lock")

    _print_box("Verifying portable environment with conda-lock")
    cmd = ["conda-lock", "lock", "--mamba", "--file", str(env_file)]
    for p in platforms:
        cmd += ["--platform", p]
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print("✅ wrote conda-lock.yml")
