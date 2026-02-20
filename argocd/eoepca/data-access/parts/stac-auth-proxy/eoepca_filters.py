from typing import Any, Literal, Optional
import dataclasses
import logging

logger = logging.getLogger(__name__)


def get_cql2_filters(
    *,
    collection_prop: Literal["id", "collection"],
    is_write: bool,
    token: Optional[dict],
) -> dict:
    """
    Build a CQL2-JSON filter expression based on a user's token claims.

    Returns a CQL2-JSON dict (not CQL2-text) so that user-supplied values are
    always in the value position of a structured expression, avoiding any
    possibility of CQL2 injection.

    :param collection_prop: The property name to filter on (e.g., "id" for collections, "collection" for items).
    :param is_write: Whether to generate filters for write access (True) or read access (False).
    :param token: The user's authentication token containing claims. None for unauthenticated users.

    :return: A CQL2-JSON filter dict that restricts access based on the user's claims.
    """
    policies: list[dict] = []

    # Public Collections: Any collection without a prefix (ie no '.' in the ID) is considered "public"
    if not is_write:
        policies.append(
            {
                "op": "not",
                "args": [
                    {"op": "like", "args": [{"property": collection_prop}, "%.%"]}
                ],
            }
        )

    # Private Collections: Authenticated users can access collections based on their username and group memberships
    if token:
        allowed_prefixes = set()

        # Users can read/write any collection prefixed with their username
        if user_id := token.get("preferred_username"):
            allowed_prefixes.add(user_id)
        else:
            logger.warning("No 'preferred_username' claim found in token")

        if group_names := token.get("groups"):
            # Groups are expected in one of the following formats:
            # - /dss/{group_id}          — grants read and write access
            # - /dss/{group_id}-ro       — grants read-only access (ignored during write checks)
            if not isinstance(group_names, list):
                logger.warning(
                    "Expected 'groups' claim to be a list, got %s", type(group_names)
                )
            else:
                for name in group_names:
                    # We expect group names in the format of '/dss/{group_prefix}(-ro)?'
                    if not name.startswith("/dss/"):
                        logger.debug("Ignoring group '%s': missing /dss/ prefix", name)
                        continue

                    # Strip the '/dss/' prefix, then validate the remainder
                    group_id = name[len("/dss/") :]

                    if "-dss-" not in group_id:
                        logger.debug("Ignoring group '%s': missing -dss- infix", name)
                        continue

                    if group_id.endswith("-mgr"):
                        logger.debug("Ignoring group '%s': manager group", name)
                        continue

                    if group_id.endswith("-ro"):
                        if not is_write:
                            allowed_prefixes.add(group_id[: -len("-ro")])
                        # else: skip — read-only groups grant no write access
                    else:
                        allowed_prefixes.add(group_id)
        else:
            logger.warning("No 'groups' claim found in token")

        for prefix in sorted(allowed_prefixes):
            policies.append(
                {"op": "like", "args": [{"property": collection_prop}, f"{prefix}.%"]}
            )

    # Combine policies with OR, as any policy being true should allow access
    # If no policies, return a filter that denies all access
    if not policies:
        return {"op": "=", "args": [1, 0]}
    if len(policies) == 1:
        return policies[0]
    return {"op": "or", "args": policies}


def is_write_request(req: dict) -> bool:
    """
    Determine if the incoming request is a write operation based on its method and path.

    Read operations:
    - GET, HEAD, OPTIONS — always reads
    - POST to /search — this is a read (STAC uses POST for complex search queries)

    Write operations:
    - POST (to non-search endpoints, e.g. creating items/collections)
    - PUT, PATCH, DELETE
    """
    method = req["method"].upper()
    path = req["path"]

    if method in ("GET", "HEAD", "OPTIONS"):
        return False
    if method == "POST" and path.rstrip("/").endswith("/search"):
        return False
    return True  # POST (non-search), PUT, PATCH, DELETE


@dataclasses.dataclass
class CollectionsFilter:

    async def __call__(self, context: dict) -> dict:
        token = context.get("payload")
        if not token:
            logger.debug("No token found in context, unauthenticated access")
        return get_cql2_filters(
            collection_prop="id",
            is_write=is_write_request(context["req"]),
            token=token,
        )


@dataclasses.dataclass
class ItemsFilter:

    async def __call__(self, context: dict) -> dict:
        token = context.get("payload")
        if not token:
            logger.debug("No token found in context, unauthenticated access")
        return get_cql2_filters(
            collection_prop="collection",
            is_write=is_write_request(context["req"]),
            token=token,
        )
