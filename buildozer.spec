[app]
title = Block Blast
package.name = blockblast
package.domain = org.vmorkva

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt

version = 0.1

requirements = python3,pygame-ce

orientation = portrait
fullscreen = 1

android.api = 31
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
android.release_artifact = apk
android.debug_artifact = apk

android.gradle_version = 7.4.2
android.enable_androidx = True

p4a.branch = v2024.01.21
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
