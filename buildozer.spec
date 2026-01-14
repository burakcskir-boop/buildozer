[app]
title = PaketlemeTakip
package.name = paketleme
package.domain = org.paketleme
source.dir = .
source.include_exts = py,kv,db
version = 0.1

requirements = python3,kivy

orientation = portrait

[buildozer]
log_level = 2

[android]
android.api = 33
android.minapi = 21
android.archs = arm64-v8a
