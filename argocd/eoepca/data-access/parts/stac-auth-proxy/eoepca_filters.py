from typing import Any, Literal, Optional
import dataclasses
import logging
import re

logger = logging.getLogger(__name__)

_SAFE_PREFIX_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


"""
Rules:

- Public Collections: Any collection without a '.' in the ID is considered "public"

"""


def get_cql2_filters(
    *,
    collection_prop: Literal["id", "collection"],
    is_write: bool,
    token: Optional[dict[str, Any]],
) -> str:
    """
    Extract collection prefixes from a user's token claims.

    Groups are expected in one of the following formats:
    - /dss/{group_id}          — grants read and write access
    - /dss/{group_id}-ro       — grants read-only access (ignored during write checks)

    :param collection_prop: The property name to filter on (e.g., "id" for collections, "collection" for items).
    :param is_write: Whether to generate filters for write access (True) or read access (False).
    :param token: The user's authentication token containing claims. None for unauthenticated users.

    :return: A set of collection prefixes that the user has access to.
    """
    policies = set()

    # Public Collections: Any collection without a prefix (ie no '.' in the ID) is considered "public"
    policies.add(f"{collection_prop} NOT LIKE '%.%'")

    # Authenticated users can access
    if token:
        prefixes = set()

        # Users can read/write any collection prefixed with their username
        if user_id := token.get("preferred_username"):
            prefixes.add(user_id)
        else:
            logger.warning("No 'preferred_username' claim found in token")

        if group_names := token.get("groups"):
            if not isinstance(group_names, list):
                logger.warning(
                    "Expected 'groups' claim to be a list, got %s", type(group_names)
                )
            else:
                for name in group_names:
                    # We expect group names in the format of '/dss/{group_prefix}(-ro)?'
                    if any(
                        (
                            # Groups should begin with /dss/
                            not name.startswith("/dss/"),
                            # Collection IDs should contain '-dss-'
                            "-dss-" not in name,
                            # Ignore manager groups
                            name.endswith("-mgr"),
                        )
                    ):
                        logger.debug(
                            "Ignoring group name '%s' as it does not match expected format",
                            name,
                        )
                        continue

                    # Strip the '/dss/' prefix
                    name = name[len("/dss/") :]

                    if name.endswith("-ro"):
                        if not is_write:
                            prefixes.add(name[: -len("-ro")])
                        # else: skip — read-only groups grant no write access
                    else:
                        prefixes.add(name)
        else:
            logger.warning("No 'groups' claim found in token")

        for prefix in prefixes:
            if not _SAFE_PREFIX_RE.match(prefix):
                logger.warning(
                    "Ignoring prefix with unsafe characters: %r", prefix
                )
                continue
            policies.add(f"{collection_prop} LIKE '{prefix}.%'")

    # Combine policies with OR, as any policy being true should allow access
    return " OR ".join(policies)


@dataclasses.dataclass
class CollectionsFilter:

    async def __call__(self, context: dict[str, Any]) -> str:
        token = context.get("payload")
        if not token:
            logger.debug("No token found in context, unauthenticated access")
        return get_cql2_filters(
            collection_prop="id",
            is_write=False,  # TODO: Support write policies
            token=token,
        )


@dataclasses.dataclass
class ItemsFilter:
    async def __call__(self, context: dict[str, Any]) -> str:
        token = context.get("payload")
        if not token:
            logger.debug("No token found in context, unauthenticated access")
        return get_cql2_filters(
            collection_prop="collection",
            is_write=False,  # TODO: Support write policies
            token=token,
        )
