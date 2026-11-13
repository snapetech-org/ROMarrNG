# Dependency locks and tested images

`requirements.in` selects runtime dependencies, including the pinned Playwright
client, and the immutable ROM Hub source archive. `requirements.lock` is the
complete runtime closure with artifact hashes; `requirements.txt` is its
identical scanner-compatible mirror. Test and build environments have separate
`.in`/`.lock` files. The
`requirements-runtime-base.in`/`.lock` pair pins pip and setuptools in the final
images so patched tooling replaces outdated copies shipped by the Python base
image. Python 3.12+ is required by the included ROM Hub version.

Regenerate in a clean Python environment with pip-tools, reviewing changed
versions and hashes:

```bash
pip-compile --generate-hashes --resolver=backtracking --output-file=requirements.lock requirements.in
cp requirements.lock requirements.txt
pip-compile --generate-hashes --resolver=backtracking --output-file=requirements-test.lock requirements-test.in
pip-compile --generate-hashes --resolver=backtracking --output-file=requirements-build.lock requirements-build.in
pip-compile --allow-unsafe --generate-hashes --resolver=backtracking --output-file=requirements-runtime-base.lock requirements-runtime-base.in
```

Install the build lock first, then the intended environment with
`--no-build-isolation --require-hashes`. This prevents an sdist build from
silently fetching unpinned build dependencies. The final image layer installs
`requirements-runtime-base.lock` after copying application packages, replacing
the vulnerable pip and setuptools copies that ship in the pinned base image.
Verify both supported native architectures and the production Python version
after updating locks.

The Dockerfile pins the Python manifest digest and copies
`docker/debian.sources`, selecting signed Debian package indexes at a fixed
snapshot timestamp. Update the digest and timestamp together deliberately,
then rebuild and scan. Snapshot signature verification remains enabled; only
index expiry checking is disabled for the historical snapshot. Playwright is
pinned in the runtime lock, and the image installs its matching Chromium build
and system dependencies during the image build.

Image validation exports the image it exercised as an artifact. Release
publication loads that artifact and publishes the same platform image, then
assembles the multi-architecture manifest from pushed digests; it does not
rebuild after testing. Publication is a separate explicit release operation.
These controls identify dependency inputs and preserve tested images; they do
not claim bit-for-bit reproducibility across different build engines.
