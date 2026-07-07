package stac.collections.authorize

import rego.v1

import data.stac.patterns.allowed

default allow := false

# Input contract expected:
# input.collection_id: string
# input.operation: "discover" | "search" | "download"
# input.roles: [string] (already verified & extracted by the proxy; [] for anonymous)

allow if {
  cid := input.collection_id
  op := input.operation
  roles := object.get(input, "roles", [])

  pats := allowed(op, roles)

  some p in pats
  glob.match(p, ["/"], cid)
}
