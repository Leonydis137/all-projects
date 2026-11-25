"""Contract tests that keep the tenant API namespace authenticated by default."""

from fastapi.routing import APIRoute

from omnis import api


def _dependency_calls(dependant):
    for dependency in dependant.dependencies:
        yield dependency.call
        yield from _dependency_calls(dependency)


def test_every_tenant_api_route_depends_on_tenant_identity():
    """New tenant endpoints must not accidentally become public or legacy-token routes."""
    protected = [
        route
        for route in api.app.routes
        if isinstance(route, APIRoute)
        and (route.path == "/v1/identity/me" or route.path.startswith("/v1/tenant/"))
    ]

    assert protected, "the tenant API route contract unexpectedly contains no routes"

    unprotected = [
        f"{','.join(sorted(route.methods or []))} {route.path}"
        for route in protected
        if api.tenant_identity not in set(_dependency_calls(route.dependant))
    ]

    assert not unprotected, (
        "Every identity and tenant route must depend on tenant_identity; "
        "missing dependency: " + "; ".join(unprotected)
    )
