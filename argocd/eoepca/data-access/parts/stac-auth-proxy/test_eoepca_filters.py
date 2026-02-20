import pytest
from cql2 import Expr

from eoepca_filters import CollectionsFilter, ItemsFilter, is_write_request

# Reusable request context fragments
_READ_REQ = {"method": "GET", "path": "/collections"}
_WRITE_REQ = {"method": "POST", "path": "/collections"}


def cql2_matches(cql2_json: dict, item: dict) -> bool:
    """Parse a CQL2-JSON expression and test it against an item dict."""
    expr = Expr(cql2_json)
    expr.validate()
    return expr.matches(item)


class TestIsWriteRequest:
    """is_write_request classifies HTTP requests as read or write."""

    @pytest.mark.parametrize(
        "method",
        [
            pytest.param("GET", id="GET"),
            pytest.param("HEAD", id="HEAD"),
            pytest.param("OPTIONS", id="OPTIONS"),
        ],
    )
    def test_safe_methods_are_reads(self, method):
        """GET, HEAD, and OPTIONS are always read operations."""
        assert not is_write_request({"method": method, "path": "/collections"})

    @pytest.mark.parametrize(
        "path",
        [
            pytest.param("/search", id="search"),
            pytest.param("/search/", id="search-trailing-slash"),
        ],
    )
    def test_post_to_search_is_read(self, path):
        """POST to /search (with or without trailing slash) is a read."""
        assert not is_write_request({"method": "POST", "path": path})

    @pytest.mark.parametrize(
        "method",
        [
            pytest.param("POST", id="POST"),
            pytest.param("PUT", id="PUT"),
            pytest.param("PATCH", id="PATCH"),
            pytest.param("DELETE", id="DELETE"),
        ],
    )
    def test_mutating_methods_are_writes(self, method):
        """POST (non-search), PUT, PATCH, and DELETE are write operations."""
        assert is_write_request({"method": method, "path": "/collections"})

    def test_post_to_items_endpoint_is_write(self):
        """POST to an items endpoint (creating an item) is a write."""
        assert is_write_request({"method": "POST", "path": "/collections/my-col/items"})

    def test_case_insensitive_method(self):
        """HTTP methods are matched case-insensitively."""
        assert not is_write_request({"method": "get", "path": "/collections"})
        assert is_write_request({"method": "post", "path": "/collections"})


class TestCollectionsFilter:
    """CollectionsFilter generates CQL2 filters matching on the 'id' property."""

    # --- Unauthenticated access ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "collection_id,expected",
        [
            pytest.param("sentinel-2", True, id="public-allowed"),
            pytest.param("alice.my-data", False, id="prefixed-denied"),
            pytest.param("org.dept.data", False, id="deep-prefix-denied"),
        ],
    )
    async def test_unauthenticated_read_access(self, collection_id, expected):
        """Unauthenticated reads allow public collections but deny prefixed ones."""
        filt = await CollectionsFilter()({"payload": None, "req": _READ_REQ})
        assert cql2_matches(filt, {"id": collection_id}) == expected

    @pytest.mark.asyncio
    async def test_unauthenticated_write_denies_all(self):
        """Unauthenticated users cannot write to any collection."""
        filt = await CollectionsFilter()({"payload": None, "req": _WRITE_REQ})
        assert not cql2_matches(
            filt, {"id": "public"}
        ), "unauthenticated write should deny public collections"
        assert not cql2_matches(
            filt, {"id": "alice.data"}
        ), "unauthenticated write should deny prefixed collections"

    @pytest.mark.asyncio
    async def test_missing_payload_treated_as_unauthenticated(self):
        """A context dict without a 'payload' key is treated as unauthenticated."""
        filt = await CollectionsFilter()({"req": _READ_REQ})
        assert cql2_matches(
            filt, {"id": "public"}
        ), "public collection should be visible when payload key is missing"
        assert not cql2_matches(
            filt, {"id": "alice.data"}
        ), "prefixed collection should not be visible when payload key is missing"

    # --- Authenticated user access (own prefix, other users, public) ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "req",
        [
            pytest.param(_READ_REQ, id="read"),
            pytest.param(_WRITE_REQ, id="write"),
        ],
    )
    async def test_authenticated_user_accesses_own_prefix(self, req):
        """Users can access their own prefixed collections for both read and write."""
        token = {"preferred_username": "alice"}
        filt = await CollectionsFilter()({"payload": token, "req": req})
        assert cql2_matches(
            filt, {"id": "alice.my-data"}
        ), "user 'alice' should access her own prefixed collection"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "req",
        [
            pytest.param(_READ_REQ, id="read"),
            pytest.param(_WRITE_REQ, id="write"),
        ],
    )
    async def test_authenticated_user_denied_other_users_prefix(self, req):
        """A user cannot access collections prefixed with another user's name."""
        token = {"preferred_username": "alice"}
        filt = await CollectionsFilter()({"payload": token, "req": req})
        assert not cql2_matches(
            filt, {"id": "bob.my-data"}
        ), "user 'alice' should not access 'bob.my-data'"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "req,expected",
        [
            pytest.param(_READ_REQ, True, id="read-allows-public"),
            pytest.param(_WRITE_REQ, False, id="write-denies-public"),
        ],
    )
    async def test_authenticated_public_collection_access(self, req, expected):
        """Authenticated reads see public collections; writes do not."""
        token = {"preferred_username": "alice"}
        filt = await CollectionsFilter()({"payload": token, "req": req})
        assert cql2_matches(filt, {"id": "sentinel-2"}) == expected

    # --- Token without username ---

    @pytest.mark.asyncio
    async def test_token_without_username_only_gets_public_access(self):
        """If preferred_username is missing, only public collections are visible on read."""
        token: dict = {}
        filt = await CollectionsFilter()({"payload": token, "req": _READ_REQ})
        assert cql2_matches(
            filt, {"id": "public"}
        ), "public collection should be visible even without preferred_username"
        assert not cql2_matches(
            filt, {"id": "alice.data"}
        ), "prefixed collection should not be visible without preferred_username"

    @pytest.mark.asyncio
    async def test_write_token_without_username_gets_no_access(self):
        """A token without preferred_username gets no write access at all."""
        token: dict = {}
        filt = await CollectionsFilter()({"payload": token, "req": _WRITE_REQ})
        assert not cql2_matches(
            filt, {"id": "public"}
        ), "write without username should deny public collections"
        assert not cql2_matches(
            filt, {"id": "alice.data"}
        ), "write without username should deny prefixed collections"

    # --- Group-based access ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "req",
        [
            pytest.param(_READ_REQ, id="read"),
            pytest.param(_WRITE_REQ, id="write"),
        ],
    )
    async def test_rw_group_grants_access(self, req):
        """A /dss/{prefix} group grants both read and write access."""
        token = {"preferred_username": "alice", "groups": ["/dss/org-dss-team"]}
        filt = await CollectionsFilter()({"payload": token, "req": req})
        assert cql2_matches(
            filt, {"id": "org-dss-team.dataset"}
        ), "rw group should grant access to 'org-dss-team.dataset'"

    @pytest.mark.asyncio
    async def test_rw_group_does_not_grant_access_to_other_prefixes(self):
        """A group only grants access to its own prefix, not unrelated prefixes."""
        token = {"preferred_username": "alice", "groups": ["/dss/org-dss-team"]}
        filt = await CollectionsFilter()({"payload": token, "req": _READ_REQ})
        assert not cql2_matches(
            filt, {"id": "other-dss-org.dataset"}
        ), "group '/dss/org-dss-team' should not grant access to 'other-dss-org.dataset'"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "req,expected",
        [
            pytest.param(_READ_REQ, True, id="read-grants"),
            pytest.param(_WRITE_REQ, False, id="write-denies"),
        ],
    )
    async def test_ro_group_access_depends_on_mode(self, req, expected):
        """A -ro group grants read access but not write access."""
        token = {"preferred_username": "alice", "groups": ["/dss/org-dss-shared-ro"]}
        filt = await CollectionsFilter()({"payload": token, "req": req})
        assert cql2_matches(filt, {"id": "org-dss-shared.dataset"}) == expected

    @pytest.mark.asyncio
    async def test_ro_group_public_still_visible(self):
        """Public collections remain visible alongside read-only group access."""
        token = {"preferred_username": "alice", "groups": ["/dss/org-dss-shared-ro"]}
        filt = await CollectionsFilter()({"payload": token, "req": _READ_REQ})
        assert cql2_matches(
            filt, {"id": "public-data"}
        ), "public collection 'public-data' should remain visible with ro group membership"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "req,rw_expected,ro_expected",
        [
            pytest.param(_READ_REQ, True, True, id="read-both-grant"),
            pytest.param(_WRITE_REQ, True, False, id="write-only-rw"),
        ],
    )
    async def test_mixed_rw_and_ro_groups(self, req, rw_expected, ro_expected):
        """Both group types contribute on read; only rw contributes on write."""
        token = {
            "preferred_username": "alice",
            "groups": ["/dss/proj-dss-alpha", "/dss/proj-dss-beta-ro"],
        }
        filt = await CollectionsFilter()({"payload": token, "req": req})
        assert cql2_matches(filt, {"id": "proj-dss-alpha.data"}) == rw_expected
        assert cql2_matches(filt, {"id": "proj-dss-beta.data"}) == ro_expected

    @pytest.mark.asyncio
    async def test_write_user_retains_own_prefix_with_ro_group(self):
        """User can still write to own prefix even when only holding -ro groups."""
        token = {
            "preferred_username": "alice",
            "groups": ["/dss/org-dss-shared-ro"],
        }
        filt = await CollectionsFilter()({"payload": token, "req": _WRITE_REQ})
        assert cql2_matches(
            filt, {"id": "alice.data"}
        ), "user should retain write access to own prefix despite only having ro groups"
        assert not cql2_matches(
            filt, {"id": "org-dss-shared.dataset"}
        ), "ro group should not grant write access"

    # --- Invalid / malformed group handling ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "group",
        [
            pytest.param("/other/org-dss-team", id="wrong-prefix"),
            pytest.param("/dss/org-team", id="missing-dss-infix"),
            pytest.param("/dss/org-dss-team-mgr", id="manager-group"),
            pytest.param("org-dss-team", id="no-leading-slash"),
        ],
    )
    async def test_invalid_group_format_grants_no_extra_access(self, group):
        """Groups that don't match '/dss/{name-with-dss-infix}' are silently ignored."""
        token = {"preferred_username": "alice", "groups": [group]}
        filt = await CollectionsFilter()({"payload": token, "req": _READ_REQ})
        assert not cql2_matches(
            filt, {"id": "org-dss-team.data"}
        ), f"invalid group '{group}' should not grant access to 'org-dss-team.data'"
        assert cql2_matches(
            filt, {"id": "alice.data"}
        ), "username-based access should still work despite invalid group"
        assert cql2_matches(
            filt, {"id": "public"}
        ), "public access should still work despite invalid group"

    @pytest.mark.asyncio
    async def test_groups_claim_not_a_list_is_ignored(self):
        """If the 'groups' claim is a string instead of a list, it is ignored gracefully."""
        token = {"preferred_username": "alice", "groups": "not-a-list"}
        filt = await CollectionsFilter()({"payload": token, "req": _READ_REQ})
        assert cql2_matches(
            filt, {"id": "public"}
        ), "public access should work when groups claim is malformed"
        assert cql2_matches(
            filt, {"id": "alice.data"}
        ), "username-based access should work when groups claim is malformed"
        assert not cql2_matches(
            filt, {"id": "not-a-list.data"}
        ), "malformed groups string should not be treated as a collection prefix"

    @pytest.mark.asyncio
    async def test_no_groups_claim_still_allows_username_access(self):
        """A token without a 'groups' claim still grants username-based access."""
        token = {"preferred_username": "bob"}
        filt = await CollectionsFilter()({"payload": token, "req": _READ_REQ})
        assert cql2_matches(
            filt, {"id": "bob.data"}
        ), "user 'bob' should access 'bob.data' even without any groups claim"
        assert cql2_matches(
            filt, {"id": "public"}
        ), "public access should work without groups claim"

    @pytest.mark.asyncio
    async def test_empty_groups_list_grants_no_group_access(self):
        """An empty groups list contributes no extra collection prefixes."""
        token = {"preferred_username": "alice", "groups": []}
        filt = await CollectionsFilter()({"payload": token, "req": _READ_REQ})
        assert cql2_matches(
            filt, {"id": "public"}
        ), "public access should work with empty groups list"
        assert cql2_matches(
            filt, {"id": "alice.data"}
        ), "username-based access should work with empty groups list"
        assert not cql2_matches(
            filt, {"id": "org-dss-team.data"}
        ), "empty groups list should not grant access to any group-prefixed collection"

    # --- Input sanitization ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "username",
        [
            pytest.param("' OR 1=1 --", id="sql-injection-style"),
            pytest.param("alice'bob", id="embedded-single-quote"),
            pytest.param("alice.bob", id="dot-in-username"),
            pytest.param("alice bob", id="space-in-username"),
        ],
    )
    async def test_unsafe_username_is_rejected(self, username):
        """Usernames with unsafe characters must not be interpolated into CQL2."""
        token = {"preferred_username": username}
        filt = await CollectionsFilter()({"payload": token, "req": _READ_REQ})
        assert cql2_matches(
            filt, {"id": "public"}
        ), "public access should still work with unsafe username"
        assert not cql2_matches(
            filt, {"id": f"{username}.data"}
        ), f"unsafe username {username!r} should not produce a filter granting access"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "group,derived_prefix",
        [
            pytest.param("/dss/org-dss-t'eam", "org-dss-t'eam", id="single-quote"),
            pytest.param("/dss/org-dss-t eam", "org-dss-t eam", id="space"),
            pytest.param(
                "/dss/' OR 1=1-dss- --",
                "' OR 1=1-dss- --",
                id="cql2-injection",
            ),
        ],
    )
    async def test_unsafe_group_prefix_is_rejected(self, group, derived_prefix):
        """Group names that yield unsafe prefixes must not be interpolated into CQL2."""
        token = {"preferred_username": "alice", "groups": [group]}
        filt = await CollectionsFilter()({"payload": token, "req": _READ_REQ})
        assert not cql2_matches(
            filt, {"id": f"{derived_prefix}.data"}
        ), f"unsafe group {group!r} should not produce a filter granting access"
        assert cql2_matches(
            filt, {"id": "alice.data"}
        ), "username-based access should still work despite unsafe group"


class TestItemsFilter:
    """ItemsFilter generates CQL2 filters matching on the 'collection' property."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "collection_id,expected",
        [
            pytest.param("sentinel-2", True, id="public-allowed"),
            pytest.param("alice.my-data", False, id="prefixed-denied"),
        ],
    )
    async def test_unauthenticated_read_access(self, collection_id, expected):
        """Unauthenticated reads allow items in public collections but deny prefixed."""
        filt = await ItemsFilter()({"payload": None, "req": _READ_REQ})
        assert cql2_matches(filt, {"collection": collection_id}) == expected

    @pytest.mark.asyncio
    async def test_unauthenticated_write_denies_all(self):
        """Unauthenticated users cannot write items to any collection."""
        filt = await ItemsFilter()({"payload": None, "req": _WRITE_REQ})
        assert not cql2_matches(
            filt, {"collection": "public"}
        ), "unauthenticated write should deny items in public collections"
        assert not cql2_matches(
            filt, {"collection": "alice.data"}
        ), "unauthenticated write should deny items in prefixed collections"

    @pytest.mark.asyncio
    async def test_authenticated_read_access(self):
        """Authenticated users can read items in own, group, and public collections."""
        token = {
            "preferred_username": "alice",
            "groups": ["/dss/org-dss-shared"],
        }
        filt = await ItemsFilter()({"payload": token, "req": _READ_REQ})
        assert cql2_matches(
            filt, {"collection": "alice.data"}
        ), "user 'alice' should access items in her own collection 'alice.data'"
        assert cql2_matches(
            filt, {"collection": "org-dss-shared.data"}
        ), "group membership should grant access to items in 'org-dss-shared.data'"
        assert cql2_matches(
            filt, {"collection": "public"}
        ), "authenticated user should still access items in public collections"
        assert not cql2_matches(
            filt, {"collection": "bob.data"}
        ), "user 'alice' should not access items in 'bob.data'"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "collection_id,expected",
        [
            pytest.param("alice.data", True, id="own-prefix-allowed"),
            pytest.param("public", False, id="public-denied"),
        ],
    )
    async def test_authenticated_write_basic_access(self, collection_id, expected):
        """Write allows own prefix but denies public collections."""
        token = {"preferred_username": "alice"}
        filt = await ItemsFilter()({"payload": token, "req": _WRITE_REQ})
        assert cql2_matches(filt, {"collection": collection_id}) == expected

    @pytest.mark.asyncio
    async def test_write_ro_group_denied(self):
        """A -ro group does NOT grant write access to items."""
        token = {
            "preferred_username": "alice",
            "groups": ["/dss/org-dss-shared-ro"],
        }
        filt = await ItemsFilter()({"payload": token, "req": _WRITE_REQ})
        assert not cql2_matches(
            filt, {"collection": "org-dss-shared.data"}
        ), "ro group should not grant write access to items"

    @pytest.mark.asyncio
    async def test_write_rw_group_grants_access(self):
        """A rw group grants write access to items in that group's collections."""
        token = {
            "preferred_username": "alice",
            "groups": ["/dss/org-dss-shared"],
        }
        filt = await ItemsFilter()({"payload": token, "req": _WRITE_REQ})
        assert cql2_matches(
            filt, {"collection": "org-dss-shared.data"}
        ), "rw group should grant write access to items in 'org-dss-shared.data'"
        assert not cql2_matches(
            filt, {"collection": "bob.data"}
        ), "rw group should not grant write access to unrelated collections"
