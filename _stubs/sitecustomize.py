"""Runtime compatibility shims for the training venv.

This file is auto-imported by Python (via `sitecustomize`) when it is present on
`sys.path`. We include `_stubs/` on `PYTHONPATH` in `scripts/train_python.sh`, so
these shims apply ONLY to the training stack and do not affect the Wave 1
generation venv.

Currently:
- `transformers>=4.5x` may call `torch.utils._pytree.register_pytree_node`, which
  exists in newer PyTorch. PyTorch 2.1.x exposes `_register_pytree_node`.
  We add a small alias so imports work while keeping torch pinned to 2.1.2.
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
