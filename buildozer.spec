[app]
title = Block Blast
package.name = blockblast
package.domain = org.vmorkva

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt

version = 0.1

requirements = python3==3.10.21,cython==0.29.34,pygame-ce

orientation = portrait
fullscreen = 1

android.api = 30
android.minapi = 21
android.ndk = 23b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
android.release_artifact = apk
android.debug_artifact = apk

p4a.branch = develop
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
