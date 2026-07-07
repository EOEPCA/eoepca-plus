package stac.collections.list

import rego.v1

import data.stac.patterns.allowed

default patterns := []

patterns := pats if {
  op := input.operation
  roles := object.get(input, "roles", [])
  pats := allowed(op, roles)
}
