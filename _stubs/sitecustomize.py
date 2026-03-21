"""Runtime compatibility shims for the training venv.

This file is auto-imported by Python (via `sitecustomize`) when it is present on
`sys.path`. We include `_stubs/` on `PYTHONPATH` in `scripts/train_python.sh`, so
these shims apply ONLY to the training stack and do not affect the Wave 1
generation venv.

Currently:
- `transformers>=4.5x` may call `torch.utils._pytree.register_pytree_node`, which
  exists in newer PyTorch. PyTorch 2.1.x exposes `_register_pytree_node`.
  We add a small alias so imports work while keeping torch pinned to 2.1.2.

- DeepSpeed may probe `CUDA_HOME` / `nvcc` at *import time* via
    `deepspeed.ops.op_builder.builder.installed_cuda_version()`. On this machine we
    rely on PyTorch's CUDA runtime from pip wheels and do NOT compile DeepSpeed
    CUDA ops, so import-time probing must not hard-fail when CUDA toolkit headers
    are absent.
"""

from __future__ import annotations


def _patch_torch_pytree() -> None:
    try:
        import torch  # noqa: WPS433
        import inspect

        pytree = getattr(torch.utils, "_pytree", None)
        if pytree is None:
            return

        if not hasattr(pytree, "register_pytree_node") and hasattr(pytree, "_register_pytree_node"):
            base = pytree._register_pytree_node  # type: ignore[attr-defined]

            base_sig = None
            try:
                base_sig = inspect.signature(base)
            except Exception:
                base_sig = None

            def register_pytree_node(*args, **kwargs):  # type: ignore[no-redef]
                # Newer Transformers passes extra kwargs (e.g. serialized_type_name)
                # which older PyTorch versions don't accept.
                if base_sig is not None:
                    allowed = set(base_sig.parameters.keys())
                    kwargs = {k: v for k, v in kwargs.items() if k in allowed}
                else:
                    # Fallback: drop the known new kwargs.
                    kwargs.pop("serialized_type_name", None)
                    kwargs.pop("to_dumpable_context", None)
                    kwargs.pop("from_dumpable_context", None)
                return base(*args, **kwargs)

            pytree.register_pytree_node = register_pytree_node
    except Exception:
        # Never fail the interpreter for a shim.
        return


_patch_torch_pytree()


def _patch_deepspeed_cuda_probe() -> None:
    """Make `import deepspeed` (and the `deepspeed` CLI) work without CUDA_HOME."""

    try:
        import importlib.abc
        import importlib.machinery
        import sys

        import torch  # noqa: WPS433

        builder_mod_name = "deepspeed.ops.op_builder.builder"
        accel_mod_name = "deepspeed.accelerator.cuda_accelerator"

        def _patch_builder_module(mod) -> None:
            MissingCUDAException = getattr(mod, "MissingCUDAException", Exception)

            def _installed_cuda_version(name: str = "") -> tuple[int, int]:
                if not getattr(torch.version, "cuda", None):
                    raise MissingCUDAException("torch.version.cuda is None")
                major, minor = torch.version.cuda.split(".")[:2]
                return int(major), int(minor)

            setattr(mod, "installed_cuda_version", _installed_cuda_version)

            # DeepSpeed's TorchCPUOpBuilder may attempt to JIT-compile CPU ops with
            # CUDA link flags whenever torch.cuda.is_available() is True. On nodes
            # without a CUDA toolkit (CUDA_HOME is None), this can crash while
            # constructing those flags (e.g., CPUAdamBuilder). Patch the builder to
            # degrade gracefully and build CPU-only in that scenario.
            try:
                import os

                TorchCPUOpBuilder = getattr(mod, "TorchCPUOpBuilder", None)
                if TorchCPUOpBuilder is not None and not getattr(TorchCPUOpBuilder, "_ship_patched_cuda_home", False):
                    orig_get_cuda_lib64_path = TorchCPUOpBuilder.get_cuda_lib64_path
                    orig_cxx_args = TorchCPUOpBuilder.cxx_args
                    orig_extra_ldflags = TorchCPUOpBuilder.extra_ldflags

                    def _safe_cuda_home() -> str | None:
                        try:
                            from torch.utils import cpp_extension

                            return getattr(cpp_extension, "CUDA_HOME", None)
                        except Exception:
                            return None

                    def get_cuda_lib64_path(self):  # noqa: ANN001
                        cuda_home = _safe_cuda_home()
                        if cuda_home is None:
                            # Fall back to torch's bundled CUDA libs (wheels).
                            try:
                                import torch as _torch

                                torch_pkg = os.path.dirname(_torch.__file__)
                                lib_dir = os.path.join(torch_pkg, "lib")
                                return lib_dir
                            except Exception:
                                return ""
                        return orig_get_cuda_lib64_path(self)

                    def cxx_args(self):  # noqa: ANN001
                        cuda_home = _safe_cuda_home()
                        if cuda_home is None:
                            old = getattr(self, "build_for_cpu", False)
                            try:
                                # Force CPU-only flags (no CUDA linker paths).
                                self.build_for_cpu = True
                                return orig_cxx_args(self)
                            finally:
                                self.build_for_cpu = old
                        return orig_cxx_args(self)

                    def extra_ldflags(self):  # noqa: ANN001
                        cuda_home = _safe_cuda_home()
                        if cuda_home is None:
                            old = getattr(self, "build_for_cpu", False)
                            try:
                                self.build_for_cpu = True
                                return orig_extra_ldflags(self)
                            finally:
                                self.build_for_cpu = old
                        return orig_extra_ldflags(self)

                    TorchCPUOpBuilder.get_cuda_lib64_path = get_cuda_lib64_path
                    TorchCPUOpBuilder.cxx_args = cxx_args
                    TorchCPUOpBuilder.extra_ldflags = extra_ldflags
                    TorchCPUOpBuilder._ship_patched_cuda_home = True
            except Exception:
                # Best-effort: never prevent interpreter startup.
                pass

        def _patch_cuda_accelerator_module(mod) -> None:
            """Relax fp16 support checks for older GPUs.

            DeepSpeed disallows fp16 unless compute capability >= 7.0 (or 6.x with
            DS_ALLOW_DEPRECATED_FP16). K80s (3.7) can still run fp16 kernels in
            practice for many workloads (albeit slower), and our training plan
            requires fp16.
            """

            try:
                CUDA_Accelerator = getattr(mod, "CUDA_Accelerator", None)
                if CUDA_Accelerator is None:
                    return
                if getattr(CUDA_Accelerator, "_ship_patched_fp16_supported", False):
                    return

                def is_fp16_supported(self):  # noqa: ANN001
                    return True

                CUDA_Accelerator.is_fp16_supported = is_fp16_supported  # type: ignore[assignment]
                CUDA_Accelerator._ship_patched_fp16_supported = True
            except Exception:
                return

        class _DSBuilderPatchLoader(importlib.abc.Loader):
            def __init__(self, base_loader: importlib.abc.Loader) -> None:
                self._base_loader = base_loader

            def create_module(self, spec):  # noqa: ANN001
                if hasattr(self._base_loader, "create_module"):
                    return self._base_loader.create_module(spec)  # type: ignore[misc]
                return None

            def exec_module(self, module) -> None:  # type: ignore[override]
                self._base_loader.exec_module(module)  # type: ignore[misc]
                _patch_builder_module(module)

        class _DSBuilderPatchFinder(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path, target=None):  # noqa: ANN001
                if fullname != builder_mod_name:
                    return None
                spec = importlib.machinery.PathFinder.find_spec(fullname, path)
                if spec is None or spec.loader is None:
                    return spec
                if not isinstance(spec.loader, _DSBuilderPatchLoader):
                    spec.loader = _DSBuilderPatchLoader(spec.loader)  # type: ignore[assignment]
                return spec

        if not any(isinstance(f, _DSBuilderPatchFinder) for f in sys.meta_path):
            sys.meta_path.insert(0, _DSBuilderPatchFinder())

        # Patch CUDA accelerator module on import.
        class _DSAccelPatchLoader(importlib.abc.Loader):
            def __init__(self, base_loader: importlib.abc.Loader) -> None:
                self._base_loader = base_loader

            def create_module(self, spec):  # noqa: ANN001
                if hasattr(self._base_loader, "create_module"):
                    return self._base_loader.create_module(spec)  # type: ignore[misc]
                return None

            def exec_module(self, module) -> None:  # type: ignore[override]
                self._base_loader.exec_module(module)  # type: ignore[misc]
                _patch_cuda_accelerator_module(module)

        class _DSAccelPatchFinder(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path, target=None):  # noqa: ANN001
                if fullname != accel_mod_name:
                    return None
                spec = importlib.machinery.PathFinder.find_spec(fullname, path)
                if spec is None or spec.loader is None:
                    return spec
                if not isinstance(spec.loader, _DSAccelPatchLoader):
                    spec.loader = _DSAccelPatchLoader(spec.loader)  # type: ignore[assignment]
                return spec

        if not any(isinstance(f, _DSAccelPatchFinder) for f in sys.meta_path):
            sys.meta_path.insert(0, _DSAccelPatchFinder())

        existing = sys.modules.get(builder_mod_name)
        if existing is not None:
            _patch_builder_module(existing)

        existing_accel = sys.modules.get(accel_mod_name)
        if existing_accel is not None:
            _patch_cuda_accelerator_module(existing_accel)
    except Exception:
        return


_patch_deepspeed_cuda_probe()
