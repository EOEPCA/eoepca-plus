package stac.cql2.items

import rego.v1
import data.stac.cql2.common.filter_for_property

# For Item Search: filter on the STAC Item field "collection"
filter := filter_for_property("collection")
