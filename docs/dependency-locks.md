# Dependency locks and tested images

`requirements.in` selects runtime dependencies and the immutable ROM Hub source
archive. `requirements.lock` is the complete runtime closure with artifact
hashes; `requirements.txt` is its identical scanner-compatible mirror. Browser,
test, and build environments have separate `.in`/`.lock` files. Python 3.12+
is required by the included ROM Hub version.

Regenerate in a clean Python environment with pip-tools, reviewing changed
versions and hashes:

```bash
pip-compile --generate-hashes --resolver=backtracking --output-file=requirements.lock requirements.in
cp requirements.lock requirements.txt
pip-compile --generate-hashes --resolver=backtracking --output-file=requirements-browser.lock requirements-browser.in
pip-compile --generate-hashes --resolver=backtracking --output-file=requirements-test.lock requirements-test.in
pip-compile --generate-hashes --resolver=backtracking --output-file=requirements-build.lock requirements-build.in
```

Install the build lock first, then the intended environment with
`--no-build-isolation --require-hashes`. This prevents an sdist build from
silently fetching unpinned build dependencies. Verify both supported native
architectures and the production Python version after updating locks.

Both Dockerfiles pin the Python manifest digest and copy
`docker/debian.sources`, selecting signed Debian package indexes at a fixed
snapshot timestamp. Update the digest and timestamp together deliberately,
then rebuild and scan. Snapshot signature verification remains enabled; only
index expiry checking is disabled for the historical snapshot. Browser binaries
are selected by the exact Playwright package version.

Image validation exports the image it exercised as an artifact. Release
publication loads that artifact and publishes the same platform image, then
assembles the multi-architecture manifest from pushed digests; it does not
rebuild after testing. Publication is a separate explicit release operation.
These controls identify dependency inputs and preserve tested images; they do
not claim bit-for-bit reproducibility across different build engines.
