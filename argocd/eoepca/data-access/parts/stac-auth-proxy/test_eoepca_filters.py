import pytest
from cql2 import Expr

from eoepca_filters import CollectionsFilter, ItemsFilter


def cql2_matches(cql2_text: str, item: dict) -> bool:
    """Parse a CQL2-text expression and test it against an item dict."""
    expr = Expr(cql2_text)
    expr.validate()
    return expr.matches(item)


class TestCollectionsFilter:
    """CollectionsFilter generates CQL2 filters matching on the 'id' property."""

    @pytest.mark.asyncio
    async def test_unauthenticated_allows_public_collections(self):
        """A collection without a '.' in the ID is public and visible without authentication."""
        filt = await CollectionsFilter()({"payload": None})
        assert cql2_matches(
            filt, {"id": "sentinel-2"}
        ), "public collection 'sentinel-2' should be visible without authentication"

    @pytest.mark.asyncio
    async def test_unauthenticated_denies_prefixed_collections(self):
        """A collection with a '.' prefix (e.g. 'alice.data') requires authentication."""
        filt = await CollectionsFilter()({"payload": None})
        assert not cql2_matches(
            filt, {"id": "alice.my-data"}
        ), "prefixed collection 'alice.my-data' should not be visible without authentication"

    @pytest.mark.asyncio
    async def test_unauthenticated_denies_deeply_prefixed_collections(self):
        """A collection with multiple '.' separators (e.g. 'org.dept.data') is also denied."""
        filt = await CollectionsFilter()({"payload": None})
        assert not cql2_matches(
            filt, {"id": "org.dept.data"}
        ), "deeply prefixed collection 'org.dept.data' should not be visible without authentication"

    @pytest.mark.asyncio
    async def test_missing_payload_treated_as_unauthenticated(self):
        """A context dict without a 'payload' key is treated as unauthenticated."""
        filt = await CollectionsFilter()({})
        assert cql2_matches(
            filt, {"id": "public"}
        ), "public collection should be visible when payload key is missing"
        assert not cql2_matches(
            filt, {"id": "alice.data"}
        ), "prefixed collection should not be visible when payload key is missing"

    @pytest.mark.asyncio
    async def test_authenticated_user_can_access_own_prefixed_collections(self):
        """The preferred_username claim grants access to '{username}.*' collections."""
        token = {"preferred_username": "alice"}
        filt = await CollectionsFilter()({"payload": token})
        assert cql2_matches(
            filt, {"id": "alice.my-data"}
        ), "user 'alice' should be able to access her own prefixed collection 'alice.my-data'"

    @pytest.mark.asyncio
    async def test_authenticated_user_cannot_access_other_users_collections(self):
        """A user cannot access collections prefixed with another user's name."""
        token = {"preferred_username": "alice"}
        filt = await CollectionsFilter()({"payload": token})
        assert not cql2_matches(
            filt, {"id": "bob.my-data"}
        ), "user 'alice' should not be able to access 'bob.my-data'"

    @pytest.mark.asyncio
    async def test_authenticated_user_retains_public_access(self):
        """Authentication does not revoke access to public collections."""
        token = {"preferred_username": "alice"}
        filt = await CollectionsFilter()({"payload": token})
        assert cql2_matches(
            filt, {"id": "sentinel-2"}
        ), "authenticated user should still see public collection 'sentinel-2'"

    @pytest.mark.asyncio
    async def test_token_without_username_only_gets_public_access(self):
        """If preferred_username is missing, only public collections are visible."""
        token: dict = {}
        filt = await CollectionsFilter()({"payload": token})
        assert cql2_matches(
            filt, {"id": "public"}
        ), "public collection should be visible even without preferred_username"
        assert not cql2_matches(
            filt, {"id": "alice.data"}
        ), "prefixed collection should not be visible without preferred_username"

    @pytest.mark.asyncio
    async def test_rw_group_grants_read_access_to_group_prefix(self):
        """A /dss/{prefix} group grants read access to '{prefix}.*' collections."""
        token = {"preferred_username": "alice", "groups": ["/dss/org-dss-team"]}
        filt = await CollectionsFilter()({"payload": token})
        assert cql2_matches(
            filt, {"id": "org-dss-team.dataset"}
        ), "rw group '/dss/org-dss-team' should grant access to 'org-dss-team.dataset'"

    @pytest.mark.asyncio
    async def test_rw_group_does_not_grant_access_to_other_prefixes(self):
        """A group only grants access to its own prefix, not unrelated prefixes."""
        token = {"preferred_username": "alice", "groups": ["/dss/org-dss-team"]}
        filt = await CollectionsFilter()({"payload": token})
        assert not cql2_matches(
            filt, {"id": "other-dss-org.dataset"}
        ), "group '/dss/org-dss-team' should not grant access to 'other-dss-org.dataset'"

    @pytest.mark.asyncio
    async def test_ro_group_grants_read_access(self):
        """A /dss/{prefix}-ro group grants read access to '{prefix}.*' collections."""
        token = {"preferred_username": "alice", "groups": ["/dss/org-dss-shared-ro"]}
        filt = await CollectionsFilter()({"payload": token})
        assert cql2_matches(
            filt, {"id": "org-dss-shared.dataset"}
        ), "ro group '/dss/org-dss-shared-ro' should grant read access to 'org-dss-shared.dataset'"

    @pytest.mark.asyncio
    async def test_ro_group_public_still_visible(self):
        """Public collections remain visible alongside read-only group access."""
        token = {"preferred_username": "alice", "groups": ["/dss/org-dss-shared-ro"]}
        filt = await CollectionsFilter()({"payload": token})
        assert cql2_matches(
            filt, {"id": "public-data"}
        ), "public collection 'public-data' should remain visible with ro group membership"

    @pytest.mark.asyncio
    async def test_mixed_rw_and_ro_groups_both_grant_read_access(self):
        """Both rw and ro groups contribute collection prefixes during read access."""
        token = {
            "preferred_username": "alice",
            "groups": ["/dss/proj-dss-alpha", "/dss/proj-dss-beta-ro"],
        }
        filt = await CollectionsFilter()({"payload": token})
        assert cql2_matches(
            filt, {"id": "proj-dss-alpha.data"}
        ), "rw group should grant read access to 'proj-dss-alpha.data'"
        assert cql2_matches(
            filt, {"id": "proj-dss-beta.data"}
        ), "ro group should also grant read access to 'proj-dss-beta.data'"

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
        filt = await CollectionsFilter()({"payload": token})
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
        filt = await CollectionsFilter()({"payload": token})
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
        filt = await CollectionsFilter()({"payload": token})
        assert cql2_matches(
            filt, {"id": "bob.data"}
        ), "user 'bob' should access 'bob.data' even without any groups claim"
        assert cql2_matches(
            filt, {"id": "public"}
        ), "public access should work without groups claim"

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
        filt = await CollectionsFilter()({"payload": token})
        # Should only contain the public-collection policy, no user prefix
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
        filt = await CollectionsFilter()({"payload": token})
        assert not cql2_matches(
            filt, {"id": f"{derived_prefix}.data"}
        ), f"unsafe group {group!r} should not produce a filter granting access"
        assert cql2_matches(
            filt, {"id": "alice.data"}
        ), "username-based access should still work despite unsafe group"

    @pytest.mark.asyncio
    async def test_empty_groups_list_grants_no_group_access(self):
        """An empty groups list contributes no extra collection prefixes."""
        token = {"preferred_username": "alice", "groups": []}
        filt = await CollectionsFilter()({"payload": token})
        assert cql2_matches(
            filt, {"id": "public"}
        ), "public access should work with empty groups list"
        assert cql2_matches(
            filt, {"id": "alice.data"}
        ), "username-based access should work with empty groups list"
        assert not cql2_matches(
            filt, {"id": "org-dss-team.data"}
        ), "empty groups list should not grant access to any group-prefixed collection"


class TestItemsFilter:
    """ItemsFilter generates CQL2 filters matching on the 'collection' property."""

    @pytest.mark.asyncio
    async def test_unauthenticated_allows_items_in_public_collections(self):
        """Items in public collections (no '.' in collection name) are visible without auth."""
        filt = await ItemsFilter()({"payload": None})
        assert cql2_matches(
            filt, {"collection": "sentinel-2"}
        ), "item in public collection 'sentinel-2' should be visible without authentication"

    @pytest.mark.asyncio
    async def test_unauthenticated_denies_items_in_prefixed_collections(self):
        """Items in prefixed collections require authentication."""
        filt = await ItemsFilter()({"payload": None})
        assert not cql2_matches(
            filt, {"collection": "alice.my-data"}
        ), "item in prefixed collection 'alice.my-data' should not be visible without authentication"

    @pytest.mark.asyncio
    async def test_authenticated_user_can_access_own_and_group_items(self):
        """Authenticated users can access items in username-prefixed and group collections."""
        token = {
            "preferred_username": "alice",
            "groups": ["/dss/org-dss-shared"],
        }
        filt = await ItemsFilter()({"payload": token})
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
