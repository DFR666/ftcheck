# ftcheck

Check whether importing an installed Python distribution re-enables the Global Interpreter Lock (GIL) on a free-threaded CPython build.

A wheel built for the free-threaded ABI (`cp313t`, `cp314t`) does not guarantee that a package runs without the GIL. Every extension module must also declare that it is safe without the GIL; otherwise CPython turns the GIL back on for the whole process when the module is imported. `ftcheck` imports a distribution in a fresh interpreter and reports any module that re-enables the GIL.

## Usage

Run it with a free-threaded interpreter, in an environment where the distributions are installed:

```
python3.14t -m pip install numpy lxml
python3.14t ftcheck.py numpy lxml
```

Every module of each distribution is imported by default; `--top-level` imports only top-level modules and `--json` prints machine-readable results. The exit code is 1 if any distribution re-enables the GIL or fails to import. Because CPython reports only the first module that turns the GIL on, run the check after fixing a reported module to find the next one.

## Use in continuous integration

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.14t"
- run: pip install .
- run: python ftcheck.py your-distribution-name
```

## Declaring GIL independence

| Technology | Declaration |
| --- | --- |
| Cython (3.1 or later) | `# cython: freethreading_compatible = True` |
| pybind11 | `PYBIND11_MODULE(name, m, py::mod_gil_not_used())` |
| nanobind | `FREE_THREADED` option of `nanobind_add_module` |
| PyO3 | version 0.28 or later declares by default; earlier versions need `#[pymodule(gil_used = false)]` |
| C API | `Py_mod_gil` slot set to `Py_MOD_GIL_NOT_USED`, or `PyUnstable_Module_SetGIL()` |

Declare a module only after checking that it is thread-safe without the GIL.

## Licence

MIT
