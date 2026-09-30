[app]
title = BlockBl
package.name = blockbl
package.domain = org.vmorkvaz
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf,so
version = 0.1

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.api = 31
android.minapi = 21
android.ndk = 23b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
