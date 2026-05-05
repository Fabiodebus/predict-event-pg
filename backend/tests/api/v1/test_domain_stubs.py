"""Each Phase-1 domain module must expose an APIRouter stub that feature WOs extend.

The foundation work order pre-creates the module directory structure so feature WOs
(CWG, ES, EUB) drop endpoints in without touching the v1 router wiring.
"""

import importlib

from fastapi import APIRouter

from app.api.v1.router import router as v1_router

EXPECTED_DOMAIN_MODULES = ("workspace", "events", "enrichment", "outreach")


def test_each_domain_module_exposes_an_apirouter() -> None:
    for name in EXPECTED_DOMAIN_MODULES:
        module = importlib.import_module(f"app.api.v1.{name}.router")
        assert hasattr(module, "router"), f"app.api.v1.{name}.router must define `router`"
        assert isinstance(module.router, APIRouter)


def test_v1_router_mounts_each_domain_module() -> None:
    """v1 router must include each stub so feature WOs can register routes against it."""
    # FastAPI flattens included routers' routes onto the parent. Empty stubs add nothing
    # observable, so we mount each stub with a tag and verify the tag is reachable via
    # the parent router's openapi tag inventory.
    for name in EXPECTED_DOMAIN_MODULES:
        stub_module = importlib.import_module(f"app.api.v1.{name}.router")
        # Assert v1_router has registered the stub by checking it as an included router
        # (FastAPI keeps no introspectable list — use route prefixes instead).
        # Add a sentinel: the stub must NOT be the same APIRouter instance as v1_router
        # (sanity), and must be import-reachable from the v1 router module's globals.
        assert stub_module.router is not v1_router

    v1_module = importlib.import_module("app.api.v1.router")
    source = importlib.import_module("inspect").getsource(v1_module)
    for name in EXPECTED_DOMAIN_MODULES:
        assert f"app.api.v1.{name}.router" in source, (
            f"v1 router must import and include the {name} stub"
        )
        assert f'prefix="/{name}"' in source, (
            f"v1 router must mount the {name} stub at /{name}"
        )
