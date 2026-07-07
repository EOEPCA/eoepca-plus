package stac.cql2.common

import data.stac.patterns.allowed

filter_for_property(prop) := out if {
	pats := allowed(input.operation, effective_roles)
	out := patterns_to_or_filter(prop, pats)
}

effective_roles := object.get(input, "roles", [])

patterns_to_or_filter(prop, pats) := {"op": "=", "args": [1, 0]} if count(pats) == 0

patterns_to_or_filter(prop, pats) := preds[0] if {
	preds := [pattern_to_pred(prop, pats[_])]
	count(preds) == 1
}

patterns_to_or_filter(prop, pats) := {"op": "or", "args": preds} if {
	preds := [pattern_to_pred(prop, pats[_])]
	count(preds) > 1
}

pattern_to_pred(prop, p) := {"op": "=", "args": [{"property": prop}, p]} if {
	not contains(p, "*")
	not contains(p, "?")
}

# wildcard: '*' => LIKE
pattern_to_pred(prop, p) := {"op": "like", "args": [{"property": prop}, glob_to_like(p)]} if {
	contains(p, "*")
}

# wildcard: '?' => LIKE
pattern_to_pred(prop, p) := {"op": "like", "args": [{"property": prop}, glob_to_like(p)]} if {
	contains(p, "?")
}

glob_to_like(p) := replace(replace(p, "*", "%"), "?", "_")
