# Harbor `Application`

The deployment of `harbor` relies mostly upon the harbor helm chart.

## Admin Credentials Sealed Secret

The harbor admin credentials are provided via a `Secret` that is maintained securely in git as a `SealedSecret`.

This `SealedSecret` is defined as an element with the `parts/`, and is generated via the script `ss-harbor-auth.sh` via the `sealed-secrets-controller` that is running in the live cluster.

The `<rootUser>` and `<rootPassword>` are supplied as positional cmdline arguments (with built-in defaults).
