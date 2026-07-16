# Updating libretro-mame and libretro-fbneo

Investigation notes on how to bump these two libretro cores to a current
upstream version in this fork. Nothing here has been actioned yet — this is
a reference doc for when/if you decide to do the bump.

Both cores are Buildroot "generic packages" fetched straight from a GitHub
archive tarball via the `github` download helper
(`buildroot/package/pkg-download.mk`):

```
github = https://github.com/$(1)/$(2)/archive/$(3)
```

`$(1)`/`$(2)` are the GitHub org/repo, `$(3)` is whatever Buildroot treats as
the "version" — a tag for mame, a raw commit SHA for fbneo. Neither package
has a `.hash` file (checked — there isn't one in either package directory),
and this repo doesn't set `BR2_DOWNLOAD_FORCE_CHECK_HASHES`. Buildroot skips
checksum verification silently when a hash file is absent, so **bumping the
version is genuinely just editing the version string** — there's no
checksum to regenerate afterwards.

Buildroot also derives each package's download/extract/build directory name
from its `_VERSION` variable, so changing that string alone is enough to
force a fresh download and rebuild next time you build the package — no
`dirclean` step required (Buildroot just builds into a new versioned
directory; the old one is left behind under `output/<target>/build/` and can
be deleted manually if you want to reclaim space).

## libretro-mame

File: `package/batocera/emulators/retroarch/libretro/libretro-mame/libretro-mame.mk`

```
LIBRETRO_MAME_VERSION = lrmame0288
LIBRETRO_MAME_SITE = $(call github,libretro,mame,$(LIBRETRO_MAME_VERSION))
```

This pulls from **`libretro/mame`** — a libretro-maintained fork/mirror of
MAME, not upstream `mamedev/mame` — tagged `lrmameNNNN` where `NNNN` matches
the MAME version number (`lrmame0288` = MAME 0.288). New tags land roughly
monthly, matching upstream MAME's release cadence.

**Current status (checked 2026-07-13):** `lrmame0288` (tagged 2026-05-29) is
the newest tag in `libretro/mame` — this package is already up to date.
Nothing to bump right now. The rest of this section is the general
procedure for whenever a newer tag shows up.

To check for a newer tag: <https://github.com/libretro/mame/tags>.

To bump:
1. Edit `LIBRETRO_MAME_VERSION` to the new tag (e.g. `lrmame0289`). That's
   the only required edit — one line.
2. Build just this package to confirm it still compiles (see
   [verifying a bump](#verifying-a-bump) below).

**What can break on a bump:** three patches apply on top of the fetched
source before building, and they're pinned to specific lines/files in the
mame tree, so they're the main risk when the underlying tag moves forward:

- `000-makefile.patch` — one-line fix in the top-level `makefile`
  (`PLATFORM` vs `UNAME` check for aarch64 detection).
- `001-nopch.patch` — disables precompiled headers in
  `scripts/toolchain.lua`.
- `002-batocera-ini.patch` — adds a `batocera.ini` config layer in
  `src/frontend/mame/mameopts.cpp` (this is how per-game/batocera-wide MAME
  options get injected).

If a bump causes a patch to fail to apply, Buildroot will error out during
extraction with a clear "patch does not apply" message naming the offending
patch — refresh the patch's context lines against the new source rather
than dropping it.

**Related but separate package:** `package/batocera/emulators/mame` is a
*different*, standalone (non-libretro) MAME build based on
`antonioginer/GroovyMAME` (`MAME_VERSION = gm0288sr222d` as of this
writing), used for other MAME-based configurations in Batocera. Historically
these two get version-bumped in the same commit for number parity (see
`5533fab9f4`, "update mame's to .288", which bumped both plus `switchres`),
but they're independent packages with independent patches — bumping
libretro-mame does not require touching this one, and vice versa.

## libretro-fbneo

File: `package/batocera/emulators/retroarch/libretro/libretro-fbneo/libretro-fbneo.mk`

```
# Version: Commits on Jan 11, 2026
LIBRETRO_FBNEO_VERSION = aaecfedbb206a79d0e35a0dfe922622b921a66f7
LIBRETRO_FBNEO_SITE = $(call github,libretro,FBNeo,$(LIBRETRO_FBNEO_VERSION))
```

Unlike mame, fbneo isn't tagged — it's pinned to an arbitrary **commit SHA**
on `libretro/FBNeo`'s `master` branch, with a comment recording the date of
that commit. This matches every historical bump in this repo's git log
(e.g. `3fc4f9095e`, `e85e5d96a1`, `f077b01420`) — pick a commit, update both
the SHA and the `# Version: Commits on <date>` comment.

**Current status (checked 2026-07-13):** `libretro/FBNeo` master is at
commit `d8c273a` (2026-07-12). The pinned commit is from 2026-01-11 — about
**6 months stale**. This one is a real candidate for bumping, unlike mame.

To check for newer commits: <https://github.com/libretro/FBNeo/commits/master>.
Look for commits titled `(libretro) update files` — these appear to be sync
points where the libretro maintainer merges in upstream
`finalburnneo/FBNeo` changes and regenerates the libretro-specific glue/data
files together, so they're a more natural place to pin to than an arbitrary
mid-stream commit.

To bump:
1. Pick a commit (ideally right after a `(libretro) update files` commit),
   copy its full SHA.
2. Update `LIBRETRO_FBNEO_VERSION` to that SHA.
3. Update the `# Version: Commits on <date>` comment above it to that
   commit's date.
4. Build just this package to confirm it still compiles (see below).

No patches apply to this package (the directory only contains `Config.in`,
`libretro-fbneo.mk`, and `fbneo.libretro.core.yml`), so there's no
patch-compatibility risk here the way there is for mame — a bump is lower
risk, just a bigger jump in upstream changes given how stale the current
pin is.

## Verifying a bump

Same for both cores, using this fork's existing single-package workflow
(see `AGENTS.md`):

```
make x86_64-arcade-pkg PKG=libretro-mame     # or libretro-fbneo
```

This builds just that package in isolation inside the normal Docker build
environment — much faster than a full image build, and enough to catch:
- a failed patch application (mame only)
- a compile error introduced by the new upstream version
- missing new dependencies the new version might have picked up upstream
  (would show up as a configure/build failure; if so, check the upstream
  `.mk`/build instructions for new required libraries and add them to
  `LIBRETRO_MAME_DEPENDENCIES` / `LIBRETRO_FBNEO_DEPENDENCIES`)

Once the isolated package build succeeds, a full
`make x86_64-arcade-build` confirms the core links and shows up correctly
in the built image before committing the version bump.
