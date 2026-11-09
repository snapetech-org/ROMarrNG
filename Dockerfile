# ROMarr -- the *arr for games.
#
# Keep compiler headers in the builder, and use Debian in both stages so
# the supported AMD64 and ARM64 targets use compatible manylinux wheels.

FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS builder

# Build tools stay out of the runtime image. libseccomp-dev is what pyseccomp
# compiles against -- the sandbox ROM Hub confines plugins with.
# libffi-dev lets CFFI compile when pip has no wheel for the target Python/arch.
COPY docker/debian.sources /etc/apt/sources.list.d/debian.sources
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libseccomp-dev libffi-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.lock requirements-build.lock /tmp/
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements-build.lock \
 && pip install --no-cache-dir --no-build-isolation --require-hashes --prefix=/install -r /tmp/requirements.lock


FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f

ARG TARGETARCH

# gosu is su-exec's Debian twin; the shared entrypoint uses the same uid:gid
# command form on both images. tzdata makes TZ work.
#
# libarchive-tools provides bsdtar, which is what reads .7z and .rar. It is
# not optional cargo: the disc platforms this image now supports ship almost
# entirely as .7z, so without it every PlayStation, PS2 and Wii import fails
# on a format it cannot open. Alpine's busybox `tar` is not a substitute and
# is deliberately not accepted -- see romarr/library.py::_bsdtar.
# libseccomp is the runtime half of the sandbox pyseccomp was built against.
# ROM Hub installs catalogue plugins from pinned repository refs, so git is a
# runtime dependency rather than builder cargo.
COPY docker/debian.sources /etc/apt/sources.list.d/debian.sources
RUN apt-get update \
 && apt-get install -y --no-install-recommends gosu tzdata libarchive-tools libseccomp2 git ca-certificates \
 && ln -s "$(command -v gosu)" /usr/local/bin/su-exec \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

# Every published architecture is built and exercised on a native CI runner.
RUN python -c "import rom_hub, pyseccomp; from rom_hub.sandbox import install; install()"

WORKDIR /app
COPY romarr/ /app/romarr/
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p /config /roms

# Paths chosen for the container, not the host. ROMARR_DATA is a file, so its
# directory is what gets mounted.
#
# LIBRARY_PATH is deliberately NOT set here. It has an older alias,
# ROMM_LIBRARY, and an image ENV beats the application's fallback chain -- so
# setting it here would silently ignore the ROMM_LIBRARY an existing install
# brought with it. The entrypoint defaults it only when neither name is given.
# ROM_HUB_HOME lives under /config so installed plugins survive a container
# recreation the same way settings do. The application default is a path
# inside the container filesystem, which silently loses every plugin on
# `docker compose pull`.
ENV ROMARR_DATA=/config/romarr.json \
    ROM_HUB_HOME=/config/rom-hub \
    ROMARR_HOST=0.0.0.0 \
    ROMARR_PORT=6868 \
    PUID=1000 \
    PGID=1000 \
    UMASK=002 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

VOLUME /config
EXPOSE 6868

# Python is already here, so the healthcheck needs no curl. A non-200 raises.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -m romarr.healthcheck
# The probe reads ROMARR_PORT and ROMARR_SSL_CERT/ROMARR_SSL_KEY.

LABEL org.opencontainers.image.title="ROMarrNG" \
      org.opencontainers.image.description="ROMarrNG adds a SeerrNG request and library contract to ROMarr" \
      org.opencontainers.image.source="https://github.com/snapetech-org/ROMarrNG" \
      org.opencontainers.image.licenses="MIT"

# The entrypoint prepares only /config as root, then drops to PUID:PGID before
# running the app. A fixed Docker USER would break ownership for mounted config.
# nosemgrep: dockerfile.security.missing-user-entrypoint.missing-user-entrypoint
ENTRYPOINT ["/entrypoint.sh"]
# nosemgrep: dockerfile.security.missing-user.missing-user
CMD ["python", "-m", "romarr"]
