package stac.patterns

import rego.v1

baseline(op) := object.get(data.authz.baseline, op, [])

role_patterns(op, roles) := [p |
  some r in roles
  pats := object.get(object.get(data.authz.roles, r, {}), op, [])
  p := pats[_]
]

allowed(op, roles) := array.concat(baseline(op), role_patterns(op, roles))
