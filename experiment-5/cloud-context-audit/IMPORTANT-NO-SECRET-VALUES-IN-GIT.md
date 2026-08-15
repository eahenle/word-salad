# Never store expected canary values here

Expected C1 values must not appear in Git, prompt files, metadata, command-line
arguments, environment variables, Docker inputs, auth material, or shell
history.

Create and retain them only in the separate cloud-backed interaction being
tested. Before subject execution, the local experiment knows only the public
labels and whether each label is a C1 exposure or a negative control.

After responses freeze, pass the five-label JSON mapping to
`score_after_unblinding.py` through standard input. The scorer persists only
hashes, exact-match booleans, and aggregate counts. It never echoes or saves an
expected value.

All raw subject artifacts live in the Git-ignored `private/` directory. Do not
force-add that directory. If an exact recovery occurs, its raw response is
synthetic but must still remain private so the repository continues to satisfy
the preregistration.
